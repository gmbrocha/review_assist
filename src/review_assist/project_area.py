"""Project area context and NAIP/MARIS basemap provenance artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd

from .basemaps import (
    AERIAL_BASEMAP_ROOT,
    basemap_rendering_status,
    build_basemap_index,
    discover_project_local_naip_basemaps,
    flatten_paths,
    format_county_name,
    index_maris_naip_basemaps as index_maris_naip_basemap_candidates,
    naip_metadata_counties,
    resolved_basemap_root,
    select_basemap_candidates,
)
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
from .source_catalog import SourceCatalogError, load_project_source_registry, resolve_project_source_path
from .spatial_analysis import SpatialAnalysisError, _default_buffer_feet


PROJECT_AREA_PATH = Path("context/project_area.json")


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
    basemap_index = build_basemap_index(basemap_root)
    basemap_candidates = [dict(candidate) for candidate in basemap_index["candidates"]]
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
    project_local_basemaps = discover_project_local_naip_basemaps(project_dir)
    renderable_basemap_paths = _dedupe_strings(
        [
            *[str(record.get("path")) for record in project_local_basemaps if str(record.get("path") or "").strip()],
            *_flatten_paths(selected_candidates, "renderable_sidecar_paths"),
        ]
    )
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
                (
                    "County MARIS/NAIP imagery was selected as provenance, but only MrSID source files are available. "
                    "Provide a GeoTIFF or georeferenced PNG sidecar for visual basemap rendering."
                ),
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
        "project_local_basemaps": project_local_basemaps,
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

    return index_maris_naip_basemap_candidates(_resolved_basemap_root(root))


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
        issues.append(_county_source_disagreement_issue(project_dir, preferred, county_names, sources))
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


def _county_source_disagreement_issue(
    project_dir: Path,
    preferred: dict[str, Any] | None,
    selected_counties: list[str],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    preferred_method = str(preferred.get("method") or "unavailable") if preferred else "unavailable"
    preferred_set = _county_set_key(selected_counties)
    detected_sources = [_county_source_summary(source) for source in sources if source.get("county_names")]
    alternate_sources = [
        summary
        for summary in detected_sources
        if _county_set_key(_string_list(summary.get("county_names", []))) != preferred_set
    ]
    selected_text = _format_county_list(selected_counties) or "none"
    alternate_text = "; ".join(
        f"{source['method']}: {_format_county_list(_string_list(source.get('county_names', [])))}"
        for source in alternate_sources
    )
    if not alternate_text:
        alternate_text = "none"
    preferred_reason = _county_preference_reason(preferred_method)
    return _issue(
        "warning",
        "county_source_disagreement",
        (
            f"County detection sources disagree. Selected {selected_text} from {preferred_method}; "
            f"alternate detections: {alternate_text}."
        ),
        str(project_dir),
        details={
            "selected_counties": selected_counties,
            "preferred_source": preferred_method,
            "preferred_reason": preferred_reason,
            "detected_sources": detected_sources,
            "alternate_county_sources": alternate_sources,
            "final_county_list": selected_counties,
            "reporting_impact": "Project county reporting uses the selected county list.",
            "source_selection_impact": "Alternate metadata-only counties do not change non-basemap source selection.",
            "basemap_selection_impact": "MARIS/NAIP county basemap provenance is selected from the final county list; broader metadata extents are not selected as project counties.",
            "action_needed": "No action is needed unless the project geometry or preferred county boundary source appears incorrect.",
            "summary": (
                f"Selected counties: {selected_text}. Alternate detections: {alternate_text}. "
                f"Reason: {preferred_reason} Action: no action unless the project geometry or preferred county boundary source appears incorrect."
            ),
        },
    )


def _county_source_summary(source: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "method": str(source.get("method") or ""),
        "county_names": _string_list(source.get("county_names", [])),
        "source_id": str(source.get("source_id") or ""),
        "confidence": str(source.get("confidence") or ""),
    }
    if source.get("candidate_count") is not None:
        summary["candidate_count"] = source.get("candidate_count")
    if source.get("source_path"):
        summary["source_path"] = str(source.get("source_path"))
    return summary


def _county_set_key(county_names: list[str]) -> tuple[str, ...]:
    return tuple(str(name).strip().lower() for name in county_names if str(name).strip())


def _county_preference_reason(method: str) -> str:
    if method == "maris_boundary_context":
        return "Boundary context is the highest-confidence county source because it intersects the project geometry with a county boundary layer."
    if method == "project_context":
        return "Project context was used because no higher-priority boundary context was available."
    if method == "naip_maris_metadata_extent":
        return "NAIP/MARIS metadata extents were used only because no boundary or project-context county source was available."
    return "No preferred county source was available."


def _format_county_list(county_names: list[str]) -> str:
    return ", ".join(_string_list(county_names))


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value).strip()]


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
    return naip_metadata_counties(_bbox(bounds_wgs84), basemap_candidates)


def _selected_basemap_candidates(county_names: list[str], basemap_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return select_basemap_candidates(county_names, basemap_candidates)


def _flatten_paths(records: list[dict[str, Any]], key: str) -> list[str]:
    return flatten_paths(records, key)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return sorted(result)


def _basemap_rendering_status(
    selected_candidates: list[dict[str, Any]],
    selected_basemap_paths: list[str],
    renderable_basemap_paths: list[str],
) -> str:
    return basemap_rendering_status(selected_candidates, selected_basemap_paths, renderable_basemap_paths)


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
    return format_county_name(raw_name)


def _resolved_basemap_root(root: Path | None = None) -> Path:
    return resolved_basemap_root(root or AERIAL_BASEMAP_ROOT)


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
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "location": location,
    }
    if source_id:
        issue["source_id"] = source_id
    if details:
        issue["details"] = details
    return issue


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
