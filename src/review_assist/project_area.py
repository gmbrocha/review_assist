"""Project area context and NAIP/MARIS basemap provenance artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import geopandas as gpd

from .input_package import InputPackageError, classify_input_package
from .project_context import BOUNDARY_CONTEXT_SOURCE_IDS, ProjectContextError, load_project_context
from .project_geometry import (
    PROJECT_ANALYSIS_BOUNDS_PATH,
    PROJECT_GEOMETRY_PATH,
    ProjectGeometryError,
    build_project_geometry,
    load_project_geometry,
)
from .projects import ProjectManifestError, load_project_manifest
from .source_catalog import SourceCatalogError, load_project_source_registry, repo_root, resolve_project_source_path
from .spatial_analysis import SpatialAnalysisError, _default_buffer_feet


PROJECT_AREA_PATH = Path("context/project_area.json")
AERIAL_BASEMAP_ROOT = Path("sources/aerial_base_maps/maris_naip_2025")

RENDERABLE_EXTENSIONS = {".tif", ".tiff", ".png"}


class ProjectAreaError(RuntimeError):
    """Raised when project area generation cannot complete."""


def build_project_area(project_dir: Path) -> dict[str, Any]:
    """Build context/project_area.json for the project workspace."""

    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        input_package = classify_input_package(project_dir)
        project_geometry = _load_or_build_project_geometry(project_dir)
        default_buffer_feet = float(project_geometry.get("default_buffer_feet", _default_buffer_feet(manifest.assumptions)))
    except (ProjectManifestError, InputPackageError, ProjectGeometryError, SpatialAnalysisError) as exc:
        raise ProjectAreaError(str(exc)) from exc

    analysis_crs = str(project_geometry.get("analysis_crs") or "EPSG:3857")
    bounds_wgs84, bounds_analysis = _load_bounds(project_dir, analysis_crs)
    bbox_wgs84 = _bbox(bounds_wgs84)
    bbox_analysis_crs = _bbox(bounds_analysis)

    validation_issues: list[dict[str, Any]] = []
    context, context_issues = _load_optional_project_context(project_dir)
    validation_issues.extend(context_issues)

    basemap_root = _resolved_basemap_root()
    basemap_candidates = index_maris_naip_basemaps(basemap_root)
    if not basemap_root.exists():
        validation_issues.append(
            _issue(
                "warning",
                "aerial_basemap_root_missing",
                "Local MARIS/NAIP aerial basemap root is not available.",
                str(basemap_root),
            )
        )

    county_names, county_detection_method, county_detection_sources, county_issues = _detect_counties(
        project_dir,
        bounds_wgs84,
        context,
        basemap_candidates,
    )
    validation_issues.extend(county_issues)

    selected_candidates = _selected_basemap_candidates(county_names, basemap_candidates)
    selected_basemap_paths = _flatten_paths(selected_candidates, "sid_paths")
    renderable_basemap_paths = _flatten_paths(selected_candidates, "renderable_sidecar_paths")
    basemap_rendering_status = _basemap_rendering_status(
        selected_candidates,
        selected_basemap_paths,
        renderable_basemap_paths,
    )
    if county_names and not selected_candidates and basemap_root.exists():
        validation_issues.append(
            _issue(
                "warning",
                "aerial_basemap_county_unavailable",
                "Detected county names do not match available MARIS/NAIP county folders.",
                str(basemap_root),
            )
        )

    warnings = [issue for issue in validation_issues if issue.get("severity") == "warning"]
    if basemap_rendering_status == "selected_not_renderable":
        warnings.append(
            _issue(
                "warning",
                "aerial_basemap_selected_not_renderable",
                "Selected MARIS/NAIP imagery is available as MrSID source data but no renderable sidecar is available.",
                str(basemap_root),
            )
        )

    output_path = project_dir / PROJECT_AREA_PATH
    artifact = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "analysis_crs": analysis_crs,
        "default_buffer_feet": default_buffer_feet,
        "bbox_wgs84": bbox_wgs84,
        "bbox_analysis_crs": bbox_analysis_crs,
        "county_names": county_names,
        "county_detection_method": county_detection_method,
        "county_detection_sources": county_detection_sources,
        "aerial_basemap_source": "maris_naip_2025" if basemap_root.exists() else None,
        "aerial_basemap_root": str(basemap_root),
        "aerial_basemap_candidates": basemap_candidates,
        "selected_basemap_paths": selected_basemap_paths,
        "renderable_basemap_paths": renderable_basemap_paths,
        "basemap_rendering_status": basemap_rendering_status,
        "warnings": _dedupe_issues(warnings),
        "validation_issues": _dedupe_issues(validation_issues),
        "provenance": {
            "input_package_path": input_package.get("output_path"),
            "project_geometry_path": project_geometry.get("output_path"),
            "analysis_bounds_path": str(project_dir / PROJECT_ANALYSIS_BOUNDS_PATH),
            "county_detection_priority": [
                "maris_boundary_context",
                "project_context",
                "naip_maris_metadata_extent",
            ],
            "basemap_source_role": "source_provenance_and_renderability_only",
        },
        "output_path": str(output_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact


def load_project_area(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / PROJECT_AREA_PATH
    if not path.exists():
        raise ProjectAreaError(f"Missing project area artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectAreaError(f"Invalid project area JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectAreaError(f"Project area artifact must be a JSON object: {path}")
    return data


def index_maris_naip_basemaps(root: Path | None = None) -> list[dict[str, Any]]:
    """Index local MARIS/NAIP county basemap folders without reading MrSID rasters."""

    basemap_root = _resolved_basemap_root(root)
    if not basemap_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for county_dir in sorted((path for path in basemap_root.iterdir() if path.is_dir()), key=lambda item: item.name.lower()):
        files = sorted((path for path in county_dir.rglob("*") if path.is_file()), key=lambda item: str(item).lower())
        sid_paths = [path for path in files if path.suffix.lower() == ".sid"]
        metadata_paths = [
            path
            for path in files
            if path.suffix.lower() in {".xml", ".txt"} or path.name.lower().endswith(".sid.aux.xml")
        ]
        world_file_paths = [path for path in files if path.suffix.lower() == ".sdw"]
        renderable_sidecar_paths = [path for path in files if path.suffix.lower() in RENDERABLE_EXTENSIONS]
        imagery_dir = _imagery_dir(county_dir, files)
        record = {
            "county_name": _format_county_name(county_dir.name),
            "county_dir": str(county_dir),
            "imagery_dir": str(imagery_dir),
            "sid_paths": [str(path) for path in sid_paths],
            "metadata_paths": [str(path) for path in metadata_paths],
            "world_file_paths": [str(path) for path in world_file_paths],
            "renderable_sidecar_paths": [str(path) for path in renderable_sidecar_paths],
            "metadata_bbox_wgs84": _first_metadata_bbox(metadata_paths),
            "status": _candidate_status(sid_paths, renderable_sidecar_paths, metadata_paths),
        }
        records.append(record)
    return records


def _load_or_build_project_geometry(project_dir: Path) -> dict[str, Any]:
    bounds_path = project_dir / PROJECT_ANALYSIS_BOUNDS_PATH
    try:
        if bounds_path.exists() and (project_dir / PROJECT_GEOMETRY_PATH).exists():
            return load_project_geometry(project_dir)
    except ProjectGeometryError:
        pass
    return build_project_geometry(project_dir)


def _load_bounds(project_dir: Path, analysis_crs: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    bounds_path = project_dir / PROJECT_ANALYSIS_BOUNDS_PATH
    if not bounds_path.exists():
        raise ProjectAreaError(f"Missing project analysis bounds artifact: {bounds_path}")
    try:
        bounds = gpd.read_file(bounds_path)
    except Exception as exc:  # noqa: BLE001 - geopandas driver exceptions vary.
        raise ProjectAreaError(f"Unable to read project analysis bounds: {bounds_path}: {exc}") from exc
    if bounds.empty:
        raise ProjectAreaError(f"Project analysis bounds artifact contains no features: {bounds_path}")
    if bounds.crs is None:
        bounds = bounds.set_crs("EPSG:4326", allow_override=True)
    return bounds.to_crs("EPSG:4326"), bounds.to_crs(analysis_crs)


def _bbox(gdf: gpd.GeoDataFrame) -> dict[str, float]:
    west, south, east, north = gdf.total_bounds
    return {
        "west": float(west),
        "south": float(south),
        "east": float(east),
        "north": float(north),
    }


def _load_optional_project_context(project_dir: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    path = project_dir / "context" / "project_context.json"
    if not path.exists():
        return None, []
    try:
        return load_project_context(project_dir), []
    except ProjectContextError as exc:
        return None, [
            _issue(
                "warning",
                "project_context_unavailable",
                f"Existing project context could not be loaded for project area county detection: {exc}",
                str(path),
            )
        ]


def _detect_counties(
    project_dir: Path,
    bounds_wgs84: gpd.GeoDataFrame,
    context: dict[str, Any] | None,
    basemap_candidates: list[dict[str, Any]],
) -> tuple[list[str], str, list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []

    boundary_source, boundary_issues = _boundary_context_counties(project_dir, bounds_wgs84)
    issues.extend(boundary_issues)
    if boundary_source:
        sources.append(boundary_source)

    context_source = _project_context_counties(context)
    if context_source:
        sources.append(context_source)

    naip_source = _naip_metadata_counties(bounds_wgs84, basemap_candidates)
    if naip_source:
        sources.append(naip_source)

    preferred = next((source for source in sources if source.get("county_names")), None)
    county_names = list(preferred.get("county_names", [])) if preferred else []
    method = str(preferred.get("method")) if preferred else "unavailable"

    non_empty_sets = {
        tuple(str(name).lower() for name in source.get("county_names", []))
        for source in sources
        if source.get("county_names")
    }
    if len(non_empty_sets) > 1:
        issues.append(
            _issue(
                "warning",
                "county_source_disagreement",
                "County detection sources produced different county name sets; preferred source order was applied.",
                str(project_dir),
            )
        )
    if not county_names:
        issues.append(
            _issue(
                "warning",
                "county_detection_unavailable",
                "No county names could be detected from boundary context, existing context, or NAIP/MARIS metadata extents.",
                str(project_dir),
            )
        )
    return county_names, method, sources, issues


def _boundary_context_counties(project_dir: Path, bounds_wgs84: gpd.GeoDataFrame) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    try:
        registry = load_project_source_registry(project_dir)
    except SourceCatalogError as exc:
        return None, [
            _issue(
                "warning",
                "county_boundary_registry_unavailable",
                f"Unable to load project source registry for county detection: {exc}",
                str(project_dir / "config" / "sources.json"),
            )
        ]

    issues: list[dict[str, Any]] = []
    for source_id in BOUNDARY_CONTEXT_SOURCE_IDS:
        source = registry.by_source_id().get(source_id)
        if source is None or not source.enabled or source.access_method != "local_file":
            continue
        source_path = resolve_project_source_path(project_dir, source)
        if source_path is None or not source_path.exists():
            continue
        try:
            county_names = _county_names_from_boundary_layer(source_path, bounds_wgs84)
        except Exception as exc:  # noqa: BLE001 - optional context should not block project area.
            issues.append(
                _issue(
                    "warning",
                    "county_boundary_context_unreadable",
                    f"Unable to read county boundary context from {source_id}: {exc}",
                    str(source_path),
                    source_id=source_id,
                )
            )
            continue
        if county_names:
            return {
                "method": "maris_boundary_context",
                "county_names": county_names,
                "source_id": source_id,
                "source_path": str(source_path),
                "confidence": "high",
            }, issues
    return None, issues


def _county_names_from_boundary_layer(source_path: Path, bounds_wgs84: gpd.GeoDataFrame) -> list[str]:
    source = gpd.read_file(source_path)
    if source.empty:
        return []
    if source.crs is None:
        source = source.set_crs("EPSG:4326", allow_override=True)
    source = source.to_crs(bounds_wgs84.crs)
    county_layer = _filter_county_layer(source)
    if county_layer.empty:
        return []
    bounds_union = bounds_wgs84.geometry.union_all()
    county_layer = county_layer[county_layer.geometry.intersects(bounds_union)]
    names = {
        _format_county_name(_first_row_value(row, ["review_assist_county_name", "CONAME", "County", "COUNTY_NAME"]))
        for _, row in county_layer.iterrows()
    }
    return sorted(name for name in names if name)


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


def _project_context_counties(context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not context:
        return None
    areas = context.get("administrative_areas", {})
    if not isinstance(areas, dict):
        return None
    counties = areas.get("counties", [])
    if not isinstance(counties, list):
        return None
    names = sorted(
        {
            _format_county_name(str(item.get("name", "")))
            for item in counties
            if isinstance(item, dict) and item.get("name")
        }
    )
    if not names:
        return None
    return {
        "method": "project_context",
        "county_names": names,
        "source_id": areas.get("source_id"),
        "source_path": areas.get("source_path"),
        "confidence": "medium",
    }


def _naip_metadata_counties(bounds_wgs84: gpd.GeoDataFrame, basemap_candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    project_bbox = _bbox(bounds_wgs84)
    matched: list[dict[str, Any]] = []
    for candidate in basemap_candidates:
        metadata_bbox = candidate.get("metadata_bbox_wgs84")
        if not isinstance(metadata_bbox, dict):
            continue
        if _bboxes_intersect(project_bbox, metadata_bbox):
            matched.append(candidate)
    if not matched:
        return None
    return {
        "method": "naip_maris_metadata_extent",
        "county_names": sorted(_format_county_name(str(candidate["county_name"])) for candidate in matched),
        "source_id": "maris_naip_2025",
        "source_path": _common_root([str(candidate["county_dir"]) for candidate in matched]),
        "candidate_count": len(matched),
        "confidence": "medium",
    }


def _selected_basemap_candidates(county_names: list[str], basemap_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    county_keys = {_county_key(name) for name in county_names}
    if not county_keys:
        return []
    return [candidate for candidate in basemap_candidates if _county_key(str(candidate.get("county_name", ""))) in county_keys]


def _flatten_paths(records: list[dict[str, Any]], key: str) -> list[str]:
    paths: list[str] = []
    for record in records:
        values = record.get(key, [])
        if isinstance(values, list):
            paths.extend(str(value) for value in values)
    return sorted(paths)


def _basemap_rendering_status(
    selected_candidates: list[dict[str, Any]],
    selected_basemap_paths: list[str],
    renderable_basemap_paths: list[str],
) -> str:
    if renderable_basemap_paths:
        return "renderable_sidecar_available"
    if selected_basemap_paths:
        return "selected_not_renderable"
    if selected_candidates:
        return "not_available"
    return "not_available"


def _imagery_dir(county_dir: Path, files: list[Path]) -> Path:
    for file_path in files:
        try:
            relative = file_path.relative_to(county_dir)
        except ValueError:
            continue
        if len(relative.parts) > 1:
            return county_dir / relative.parts[0]
    return county_dir


def _candidate_status(sid_paths: list[Path], renderable_paths: list[Path], metadata_paths: list[Path]) -> str:
    if renderable_paths:
        return "renderable_sidecar_available"
    if sid_paths:
        return "selected_not_renderable"
    if metadata_paths:
        return "metadata_only"
    return "empty"


def _first_metadata_bbox(metadata_paths: list[Path]) -> dict[str, float] | None:
    for path in metadata_paths:
        if path.suffix.lower() != ".xml":
            continue
        bbox = _metadata_bbox(path)
        if bbox is not None:
            return bbox
    return None


def _metadata_bbox(path: Path) -> dict[str, float] | None:
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None
    keys = {
        "westBoundLongitude": "west",
        "eastBoundLongitude": "east",
        "southBoundLatitude": "south",
        "northBoundLatitude": "north",
    }
    values: dict[str, float] = {}
    for element in root.iter():
        key = keys.get(_local_name(element.tag))
        if key is None:
            continue
        value = _first_float_descendant(element)
        if value is not None:
            values[key] = value
    if set(values) != {"west", "east", "south", "north"}:
        return None
    return values


def _first_float_descendant(element: ET.Element) -> float | None:
    for child in element.iter():
        if child.text is None:
            continue
        text = child.text.strip()
        if not text:
            continue
        try:
            return float(text)
        except ValueError:
            continue
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _bboxes_intersect(left: dict[str, Any], right: dict[str, Any]) -> bool:
    try:
        return not (
            float(left["east"]) < float(right["west"])
            or float(left["west"]) > float(right["east"])
            or float(left["north"]) < float(right["south"])
            or float(left["south"]) > float(right["north"])
        )
    except (KeyError, TypeError, ValueError):
        return False


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
    if name.lower().endswith(" co"):
        name = name[:-3].strip()
    return f"{name} County"


def _county_key(name: str) -> str:
    normalized = _format_county_name(name).lower()
    if normalized.endswith(" county"):
        normalized = normalized[: -len(" county")]
    return "".join(character for character in normalized if character.isalnum())


def _common_root(paths: list[str]) -> str | None:
    if not paths:
        return None
    try:
        return str(Path(paths[0]).parent if len(paths) == 1 else Path(paths[0]).parents[1])
    except IndexError:
        return str(paths[0])


def _resolved_basemap_root(root: Path | None = None) -> Path:
    path = root or AERIAL_BASEMAP_ROOT
    if path.is_absolute():
        return path
    return (repo_root() / path).resolve()


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, Any]] = []
    for issue in issues:
        key = (str(issue.get("code", "")), str(issue.get("location", "")), str(issue.get("message", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result


def _issue(
    severity: str,
    code: str,
    message: str,
    location: str,
    *,
    source_id: str | None = None,
) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "location": location,
    }
    if source_id:
        issue["source_id"] = source_id
    return issue


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
