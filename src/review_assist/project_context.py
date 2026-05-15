"""Project context artifact generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import box

from .inspection import ProjectInspectionError, inspect_project
from .project_geometry import PROJECT_ANALYSIS_BOUNDS_PATH
from .projects import ProjectManifestError, load_project_manifest
from .report_profiles import ReportProfileError, resolve_report_profile
from .source_catalog import SourceCatalogError, load_project_source_registry, resolve_project_source_path


PROJECT_CONTEXT_PATH = Path("context/project_context.json")
BOUNDARY_CONTEXT_SOURCE_IDS = ("maris_boundary_context", "maris_county_boundaries")


class ProjectContextError(RuntimeError):
    """Raised when project context generation cannot complete."""


def generate_project_context(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        report_profile = resolve_report_profile(manifest)
        inspection = inspect_project(project_dir)
    except (ProjectManifestError, ReportProfileError, ProjectInspectionError) as exc:
        raise ProjectContextError(str(exc)) from exc

    context_path = project_dir / PROJECT_CONTEXT_PATH
    context_path.parent.mkdir(parents=True, exist_ok=True)

    project_extent = _combined_bounds(inspection["inputs"])
    administrative_areas, administrative_issues = _administrative_areas(project_dir, project_extent)
    context = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_type": manifest.project_type,
        "description": manifest.description,
        "project_dir": str(project_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "context_path": str(context_path),
        "report_profile": {
            "profile_id": report_profile.profile_id,
            "name": report_profile.name,
            "required_categories": report_profile.required_categories,
            "optional_categories": report_profile.optional_categories,
        },
        "assumptions": manifest.assumptions,
        "special_reviewer_instructions": manifest.special_reviewer_instructions,
        "project_extent_wgs84": project_extent,
        "administrative_areas": administrative_areas,
        "input_roles": sorted({item["role"] for item in inspection["inputs"]}),
        "detected_inputs": inspection["inputs"],
        "provided_source_inputs": inspection.get("source_inputs", []),
        "detected_alternatives": _detected_alternatives(inspection["inputs"]),
        "validation_issues": _validation_issues(inspection["inputs"])
        + _validation_issues(inspection.get("source_inputs", []))
        + administrative_issues,
        "geometry_summary_path": inspection["summary_path"],
    }
    context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
    return context


def load_project_context(project_dir: Path) -> dict[str, Any]:
    context_file = project_dir / PROJECT_CONTEXT_PATH
    if not context_file.exists():
        raise ProjectContextError(f"Missing project context artifact: {context_file}")
    try:
        data = json.loads(context_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectContextError(f"Invalid project context JSON: {context_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectContextError(f"Project context must be a JSON object: {context_file}")
    return data


def _combined_bounds(inputs: list[dict[str, Any]]) -> dict[str, float] | None:
    bounds = [item.get("bounds_wgs84") for item in inputs if isinstance(item.get("bounds_wgs84"), dict)]
    if not bounds:
        return None
    return {
        "west": min(float(item["west"]) for item in bounds),
        "south": min(float(item["south"]) for item in bounds),
        "east": max(float(item["east"]) for item in bounds),
        "north": max(float(item["north"]) for item in bounds),
    }


def _administrative_areas(project_dir: Path, project_extent: dict[str, float] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    areas: dict[str, Any] = {"counties": []}
    bounds = _context_bounds(project_dir, project_extent)
    if bounds is None:
        return areas, issues

    try:
        registry = load_project_source_registry(project_dir)
    except SourceCatalogError as exc:
        return areas, [
            {
                "severity": "warning",
                "code": "administrative_context_registry_unavailable",
                "message": f"Unable to load project source registry for administrative context: {exc}",
                "location": str(project_dir / "config" / "sources.json"),
            }
        ]

    for source_id in BOUNDARY_CONTEXT_SOURCE_IDS:
        source = registry.by_source_id().get(source_id)
        if source is None or not source.enabled or source.access_method != "local_file":
            continue
        source_path = resolve_project_source_path(project_dir, source)
        if source_path is None or not source_path.exists():
            continue
        try:
            county_records = _county_records(source_path, bounds, source_id)
        except Exception as exc:  # noqa: BLE001 - administrative context is optional.
            issues.append(
                {
                    "severity": "warning",
                    "code": "administrative_context_unreadable",
                    "message": f"Unable to read county boundary context from {source_id}: {exc}",
                    "location": str(source_path),
                    "source_id": source_id,
                }
            )
            continue
        if county_records:
            areas["counties"] = county_records
            areas["source_id"] = source_id
            areas["source_path"] = str(source_path)
            return areas, issues
    return areas, issues


def _context_bounds(project_dir: Path, project_extent: dict[str, float] | None) -> gpd.GeoDataFrame | None:
    bounds_path = project_dir / PROJECT_ANALYSIS_BOUNDS_PATH
    if bounds_path.exists():
        bounds = gpd.read_file(bounds_path)
        if bounds.empty:
            return None
        if bounds.crs is None:
            bounds = bounds.set_crs("EPSG:4326", allow_override=True)
        return bounds.to_crs("EPSG:4326")

    if not isinstance(project_extent, dict):
        return None
    try:
        west = float(project_extent["west"])
        south = float(project_extent["south"])
        east = float(project_extent["east"])
        north = float(project_extent["north"])
    except (KeyError, TypeError, ValueError):
        return None
    if west == east or south == north:
        return None
    return gpd.GeoDataFrame([{}], geometry=[box(west, south, east, north)], crs="EPSG:4326")


def _county_records(source_path: Path, bounds: gpd.GeoDataFrame, source_id: str) -> list[dict[str, str]]:
    source = gpd.read_file(source_path)
    if source.empty:
        return []
    if source.crs is None:
        source = source.set_crs("EPSG:4326", allow_override=True)
    source = source.to_crs(bounds.crs)
    county_layer = _filter_county_layer(source)
    bounds_union = bounds.geometry.union_all()
    county_layer = county_layer[county_layer.geometry.intersects(bounds_union)]
    records: dict[str, dict[str, str]] = {}
    for _, row in county_layer.iterrows():
        raw_name = _first_row_value(row, ["review_assist_county_name", "CONAME", "County", "COUNTY_NAME"])
        if not raw_name:
            continue
        county_name = _format_county_name(raw_name)
        records[county_name.lower()] = {
            "name": county_name,
            "raw_name": raw_name,
            "county_seat": _first_row_value(row, ["review_assist_county_seat", "CO_SEAT", "county_seat"]),
            "source_id": source_id,
            "source_layer_id": _first_row_value(row, ["review_assist_layer_id"]),
            "source_layer_name": _first_row_value(row, ["review_assist_layer_name"]),
        }
    return [records[key] for key in sorted(records)]


def _filter_county_layer(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if "review_assist_layer_id" in gdf.columns:
        layer_ids = gdf["review_assist_layer_id"].astype(str).str.lower()
        filtered = gdf[layer_ids.str.contains("county", na=False)]
        if not filtered.empty:
            return filtered
    for field in ("review_assist_county_name", "CONAME", "County", "COUNTY_NAME"):
        if field in gdf.columns:
            filtered = gdf[gdf[field].notna()]
            if not filtered.empty:
                return filtered
    return gdf.iloc[0:0].copy()


def _first_row_value(row: Any, fields: list[str]) -> str:
    by_lower = {str(column).lower(): column for column in row.index}
    for field in fields:
        column = field if field in row.index else by_lower.get(str(field).lower())
        if column is None:
            continue
        value = row[column]
        if value is None:
            continue
        try:
            if value != value:
                continue
        except TypeError:
            pass
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


def _format_county_name(raw_name: str) -> str:
    name = " ".join(str(raw_name).replace("_", " ").split())
    if not name:
        return ""
    if name.lower().endswith(" county"):
        return name
    return f"{name} County"


def _detected_alternatives(inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alternatives: list[dict[str, Any]] = []
    for item in inputs:
        role = str(item.get("role", ""))
        if "alternative" not in role:
            continue
        labels = item.get("candidate_labels", [])
        alternatives.append(
            {
                "input_path": item.get("input_path"),
                "role": role,
                "feature_count": item.get("feature_count"),
                "geometry_type_counts": item.get("geometry_type_counts", {}),
                "candidate_labels": labels if isinstance(labels, list) else [],
                "needs_reviewer_labeling": not bool(labels),
            }
        )
    return alternatives


def _validation_issues(inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for item in inputs:
        input_path = str(item.get("input_path", ""))
        for issue in item.get("validation_issues", []):
            if isinstance(issue, dict):
                copied = dict(issue)
                copied["input_path"] = input_path
                issues.append(copied)
    return issues
