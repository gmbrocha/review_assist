"""Matrix-backed deliverable figure generation."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import box

from .basemaps import MARIS_NAIP_SOURCE_ID, MARIS_NAIP_SOURCE_NAME
from .comparison_units import ComparisonUnitError, build_comparison_units, load_comparison_units
from .deliverable_figure_basemaps import load_basemap
from .deliverable_figure_contract import DeliverableFigureError, validate_deliverable_figures
from .deliverable_figure_rendering import (
    comparison_unit_style_records,
    panel_bounds,
    plan_render_layout_for_map,
    render_map,
    source_layer_style_record,
)
from .deliverable_figure_specs import (
    MAX_PANEL_COUNT,
    MISSING_SOURCE_STATUSES,
    PANEL_ASPECT_THRESHOLD,
    PUBLIC_CULTURAL_SOURCE_IDS,
    RESTRICTED_CULTURAL_SOURCE_ID,
    TARGET_SPECS,
    UNIMPLEMENTED_SOURCE_STATUSES,
    USABLE_SOURCE_STATUSES,
    WBD_HUC12_SOURCE_IDS,
    TargetFigureSpec,
)
from .deliverable_constraints import (
    COMPARISON_UNIT_CONSTRAINTS_PATH,
    ComparisonUnitConstraintError,
    analyze_comparison_unit_constraints,
    load_comparison_unit_constraints,
)
from .deliverable_matrix import REQUIRED_STUB_TEXT, DeliverableMatrixError, FigureTarget, load_deliverable_matrix
from .extent_policy import (
    COMMUNITY_CONTEXT_EXTENT,
    COUNTY_OR_REGIONAL_CONTEXT_EXTENT,
    DIRECT_INTERSECTION_EXTENT,
    NEARBY_CONTEXT_EXTENT,
    SCREENING_BUFFER_EXTENT,
    WATERSHED_CONTEXT_EXTENT,
    apply_extent_metadata,
    extent_policy_summary,
    render_extent_metadata,
    target_extent_metadata,
)
from .maps import FIGURES_DIR
from .project_area import PROJECT_AREA_PATH, ProjectAreaError, build_project_area, load_project_area
from .projects import ProjectManifestError, load_project_manifest
from .report_section_policy import FigurePolicy, default_report_section_policy
from .source_catalog import SourceCatalogError, load_project_source_registry, load_source_catalog, resolve_project_source_path
from .source_status import LOGICAL_ROLLUP_SATISFIERS, SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set


DELIVERABLE_FIGURES_PATH = Path("deliverable/figures.json")
FIGURE_EXTENT_PLAN_PATH = Path("maps/figure_extent_plan.json")
DELIVERABLE_MAP_ELEMENT_BASELINE = ["legend", "north_arrow", "scale_bar"]
FIGURE_EXTENT_PLAN_VERSION = "figure-extent-plan-v1"
SMALL_DIRECT_EXTENT_CLASS = "small_direct"
MEDIUM_CONTEXT_EXTENT_CLASS = "medium_context"
LARGE_WATERSHED_EXTENT_CLASS = "large_watershed"
COUNTY_REGIONAL_EXTENT_CLASS = "county_regional"
PLANNED_FIGURE_STATUSES = {"planned", "planned_current_project_area_context", "planned_watershed_context"}


def generate_deliverable_figures(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        matrix = load_deliverable_matrix()
        source_catalog = load_source_catalog()
        comparison_units = _load_or_build_comparison_units(project_dir)
        project_area = _load_or_build_project_area(project_dir)
        comparison_unit_constraints = _load_or_generate_comparison_unit_constraints(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
        unit_gdf = _comparison_unit_gdf(comparison_units)
    except (
        ProjectManifestError,
        DeliverableMatrixError,
        SourceCatalogError,
        ComparisonUnitError,
        ComparisonUnitConstraintError,
        SourceStatusError,
        ProjectAreaError,
    ) as exc:
        raise DeliverableFigureError(str(exc)) from exc

    analysis_crs = str(
        comparison_unit_constraints.get("analysis_crs")
        or project_area.get("analysis_crs")
        or _analysis_crs(unit_gdf)
    )
    unit_gdf = _clean_gdf(unit_gdf, analysis_crs)
    analysis_bounds = _analysis_bounds(project_dir, analysis_crs, unit_gdf)
    figures_dir = project_dir / FIGURES_DIR
    figures_dir.mkdir(parents=True, exist_ok=True)

    source_context = _source_context(source_status, comparison_unit_constraints, source_catalog.sources)
    source_layers = _load_source_layers(
        project_dir=project_dir,
        comparison_unit_constraints=comparison_unit_constraints,
        source_catalog=source_catalog.sources,
        analysis_crs=analysis_crs,
        analysis_bounds=analysis_bounds,
    )
    figure_extent_plan = generate_figure_extent_plan(project_dir)
    figure_plan_by_id = {
        str(record.get("figure_id")): record for record in _dict_list(figure_extent_plan.get("figures", [])) if record.get("figure_id")
    }
    constraints = [item for item in comparison_unit_constraints.get("constraints", []) if isinstance(item, dict)]

    figures: list[dict[str, Any]] = []
    all_public_source_layers: list[dict[str, Any]] = []
    validation_issues: list[dict[str, Any]] = []
    for target in matrix.figure_targets:
        figure = _figure_for_target(
            project_dir=project_dir,
            figures_dir=figures_dir,
            target=target,
            matrix_version=matrix.matrix_version,
            unit_gdf=unit_gdf,
            analysis_bounds=analysis_bounds,
            analysis_crs=analysis_crs,
            project_area=project_area,
            source_context=source_context,
            source_layers=source_layers,
            constraints=constraints,
            comparison_unit_constraints=comparison_unit_constraints,
            source_status=source_status,
            figure_plan=figure_plan_by_id.get(target.target_id),
        )
        figures.append(figure)
        validation_issues.extend(_dict_list(figure.get("validation_issues", [])))
        if not figure.get("is_stub"):
            spec = _target_spec(target, source_context)
            for layer in _target_source_layers(target, source_layers, spec):
                if layer["source_id"] != RESTRICTED_CULTURAL_SOURCE_ID:
                    all_public_source_layers.append(layer)

    attachment_supporting_figures, panel_issues = _attachment_supporting_figures(
        figures_dir=figures_dir,
        unit_gdf=unit_gdf,
        source_layers=_dedupe_source_layers(all_public_source_layers),
        analysis_crs=analysis_crs,
        project_area=project_area,
        matrix_version=matrix.matrix_version,
        comparison_unit_constraints=comparison_unit_constraints,
        source_status=source_status,
    )
    validation_issues.extend(panel_issues)

    output_path = project_dir / DELIVERABLE_FIGURES_PATH
    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "matrix_version": matrix.matrix_version,
        "extent_policy": extent_policy_summary(),
        "figure_count": len(figures),
        "figures": figures,
        "attachment_supporting_figure_count": len(attachment_supporting_figures),
        "attachment_supporting_figures": attachment_supporting_figures,
        "validation_issues": _dedupe_issues(validation_issues),
        "upstream_artifacts": {
            "deliverable_matrix_path": "config/deliverable_section_matrix.json",
            "comparison_units_metadata_path": comparison_units.get("output_path"),
            "comparison_units_path": comparison_units.get("comparison_units_path"),
            "comparison_unit_constraints_path": comparison_unit_constraints.get("output_path"),
            "figure_extent_plan_path": figure_extent_plan.get("output_path"),
            "source_status_path": source_status.get("output_path"),
            "project_area_path": project_area.get("output_path"),
        },
        "output_path": str(output_path),
    }
    validate_deliverable_figures(result, str(output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_deliverable_figures(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / DELIVERABLE_FIGURES_PATH
    if not path.exists():
        raise DeliverableFigureError(f"Missing deliverable figures artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeliverableFigureError(f"Invalid deliverable figures JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DeliverableFigureError(f"Deliverable figures artifact must be a JSON object: {path}")
    validate_deliverable_figures(data, str(path))
    return data


def generate_figure_extent_plan(project_dir: Path) -> dict[str, Any]:
    """Plan presentation-only render extents before figure/basemap generation."""

    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        matrix = load_deliverable_matrix()
        source_catalog = load_source_catalog()
        comparison_units = _load_or_build_comparison_units(project_dir)
        project_area = _load_or_build_project_area(project_dir)
        comparison_unit_constraints = _load_or_generate_comparison_unit_constraints(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
        unit_gdf = _comparison_unit_gdf(comparison_units)
    except (
        ProjectManifestError,
        DeliverableMatrixError,
        SourceCatalogError,
        ComparisonUnitError,
        ComparisonUnitConstraintError,
        SourceStatusError,
        ProjectAreaError,
    ) as exc:
        raise DeliverableFigureError(str(exc)) from exc

    analysis_crs = str(
        comparison_unit_constraints.get("analysis_crs")
        or project_area.get("analysis_crs")
        or _analysis_crs(unit_gdf)
    )
    unit_gdf = _clean_gdf(unit_gdf, analysis_crs)
    analysis_bounds = _analysis_bounds(project_dir, analysis_crs, unit_gdf)
    source_context = _source_context(source_status, comparison_unit_constraints, source_catalog.sources)
    source_layers = _load_source_layers(
        project_dir=project_dir,
        comparison_unit_constraints=comparison_unit_constraints,
        source_catalog=source_catalog.sources,
        analysis_crs=analysis_crs,
        analysis_bounds=analysis_bounds,
    )

    records: list[dict[str, Any]] = []
    validation_issues: list[dict[str, Any]] = []
    for target in matrix.figure_targets:
        record, issues = _figure_extent_plan_record(
            project_dir=project_dir,
            target=target,
            unit_gdf=unit_gdf,
            analysis_bounds=analysis_bounds,
            source_context=source_context,
            source_layers=source_layers,
            comparison_unit_constraints=comparison_unit_constraints,
        )
        records.append(record)
        validation_issues.extend(issues)

    groups = _basemap_materialization_groups(records, analysis_crs)
    output_path = project_dir / FIGURE_EXTENT_PLAN_PATH
    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "plan_version": FIGURE_EXTENT_PLAN_VERSION,
        "analysis_crs": analysis_crs,
        "extent_policy": extent_policy_summary(),
        "figure_count": len(records),
        "figures": records,
        "basemap_materialization_groups": groups,
        "validation_issues": _dedupe_issues(validation_issues),
        "upstream_artifacts": {
            "deliverable_matrix_path": "config/deliverable_section_matrix.json",
            "comparison_units_metadata_path": comparison_units.get("output_path"),
            "comparison_units_path": comparison_units.get("comparison_units_path"),
            "comparison_unit_constraints_path": comparison_unit_constraints.get("output_path"),
            "source_status_path": source_status.get("output_path"),
            "project_area_path": project_area.get("output_path"),
        },
        "output_path": str(output_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_figure_extent_plan(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / FIGURE_EXTENT_PLAN_PATH
    if not path.exists():
        raise DeliverableFigureError(f"Missing figure extent plan artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeliverableFigureError(f"Invalid figure extent plan JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DeliverableFigureError(f"Figure extent plan artifact must be a JSON object: {path}")
    return data


def load_or_generate_figure_extent_plan(project_dir: Path) -> dict[str, Any]:
    try:
        return load_figure_extent_plan(project_dir)
    except DeliverableFigureError:
        return generate_figure_extent_plan(project_dir)


def _load_or_build_comparison_units(project_dir: Path) -> dict[str, Any]:
    try:
        return load_comparison_units(project_dir)
    except ComparisonUnitError:
        return build_comparison_units(project_dir)


def _load_or_generate_comparison_unit_constraints(project_dir: Path) -> dict[str, Any]:
    if (project_dir / COMPARISON_UNIT_CONSTRAINTS_PATH).exists():
        return load_comparison_unit_constraints(project_dir)
    return analyze_comparison_unit_constraints(project_dir, tolerate_source_errors=True)


def _load_or_generate_source_status(project_dir: Path) -> dict[str, Any]:
    path = project_dir / SOURCE_STATUS_PATH
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SourceStatusError(f"Invalid source status JSON: {path}: {exc}") from exc
        if isinstance(data, dict):
            return data
        raise SourceStatusError(f"Source status artifact must be a JSON object: {path}")
    return resolve_source_status_set(project_dir)


def _load_or_build_project_area(project_dir: Path) -> dict[str, Any]:
    if (project_dir / PROJECT_AREA_PATH).exists():
        return load_project_area(project_dir)
    return build_project_area(project_dir)


def _comparison_unit_gdf(comparison_units: dict[str, Any]) -> gpd.GeoDataFrame:
    path = Path(str(comparison_units.get("comparison_units_path", "")))
    if not path.exists():
        raise DeliverableFigureError(f"Missing comparison units GeoJSON artifact: {path}")
    try:
        gdf = gpd.read_file(path)
    except Exception as exc:  # pragma: no cover - geopandas driver exception types vary.
        raise DeliverableFigureError(f"Unable to read comparison units: {path}: {exc}") from exc
    if gdf.empty:
        raise DeliverableFigureError(f"Comparison units artifact contains no features: {path}")
    return gdf


def _analysis_crs(gdf: gpd.GeoDataFrame) -> str:
    if gdf.crs is not None:
        try:
            estimated = gdf.estimate_utm_crs()
        except RuntimeError:
            estimated = None
        if estimated is not None:
            return estimated.to_string()
        return gdf.crs.to_string()
    return "EPSG:3857"


def _clean_gdf(gdf: gpd.GeoDataFrame, analysis_crs: str) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    gdf = gdf[~gdf.geometry.isna()]
    gdf = gdf[~gdf.geometry.is_empty]
    return gdf.to_crs(analysis_crs)


def _analysis_bounds(project_dir: Path, analysis_crs: str, fallback_units: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    path = project_dir / "intermediate" / "analysis_bounds.geojson"
    if path.exists():
        try:
            bounds = gpd.read_file(path)
            if bounds.crs is None:
                bounds = bounds.set_crs("EPSG:4326", allow_override=True)
            bounds = bounds[~bounds.geometry.isna()]
            bounds = bounds[~bounds.geometry.is_empty]
            if not bounds.empty:
                return bounds.to_crs(analysis_crs)
        except Exception:
            pass
    return gpd.GeoDataFrame({"geometry": [box(*fallback_units.total_bounds)]}, geometry="geometry", crs=analysis_crs)


def _source_context(
    source_status: dict[str, Any],
    comparison_unit_constraints: dict[str, Any],
    source_definitions: dict[str, Any],
) -> dict[str, Any]:
    details_by_id: dict[str, dict[str, Any]] = {}
    ids_by_category: dict[str, set[str]] = {}
    flags_by_id: dict[str, set[str]] = {}
    category_records: dict[str, dict[str, Any]] = {}

    for source_id, definition in source_definitions.items():
        ids_by_category.setdefault(str(definition.category), set()).add(source_id)
        details_by_id.setdefault(
            source_id,
            {
                "source_id": source_id,
                "source_name": definition.name,
                "category": definition.category,
                "status": "",
                "uncertainty_flags": [],
            },
        )

    for record in _dict_list(source_status.get("statuses", [])):
        category = str(record.get("category", ""))
        if category:
            category_records[category] = record
            ids_by_category.setdefault(category, set()).update(_string_list(record.get("source_ids", [])))
        for detail in _dict_list(record.get("source_details", [])):
            source_id = str(detail.get("source_id", ""))
            if not source_id:
                continue
            details_by_id[source_id] = {
                "source_id": source_id,
                "source_name": detail.get("source_name") or details_by_id.get(source_id, {}).get("source_name") or source_id,
                "category": category or details_by_id.get(source_id, {}).get("category", ""),
                "status": detail.get("status"),
                "uncertainty_flags": _string_list(detail.get("uncertainty_flags", [])),
                "notes": detail.get("notes", ""),
                "local_path": detail.get("local_path"),
            }
            flags_by_id.setdefault(source_id, set()).update(_string_list(detail.get("uncertainty_flags", [])))

    for source in _dict_list(comparison_unit_constraints.get("sources", [])):
        source_id = str(source.get("source_id", ""))
        if not source_id:
            continue
        status = str(source.get("status", ""))
        existing = details_by_id.setdefault(source_id, {"source_id": source_id})
        existing.update(
            {
                "source_name": source.get("source_name") or existing.get("source_name") or source_id,
                "category": source.get("source_category") or existing.get("category", ""),
                "status": status or existing.get("status", ""),
                "path": source.get("path") or existing.get("path") or existing.get("local_path"),
            }
        )
        if source.get("source_category"):
            ids_by_category.setdefault(str(source.get("source_category")), set()).add(source_id)

    return {
        "details_by_id": details_by_id,
        "ids_by_category": {key: sorted(value) for key, value in ids_by_category.items()},
        "flags_by_id": {key: sorted(value) for key, value in flags_by_id.items()},
        "category_records": category_records,
    }


def _load_source_layers(
    *,
    project_dir: Path,
    comparison_unit_constraints: dict[str, Any],
    source_catalog: dict[str, Any],
    analysis_crs: str,
    analysis_bounds: gpd.GeoDataFrame,
) -> dict[str, list[dict[str, Any]]]:
    layers: dict[str, list[dict[str, Any]]] = {}
    bounds_union = analysis_bounds.geometry.union_all()
    for source in _renderable_source_records(
        project_dir=project_dir,
        comparison_unit_constraints=comparison_unit_constraints,
        source_catalog=source_catalog,
    ):
        source_id = str(source.get("source_id", ""))
        if not source_id or source_id == RESTRICTED_CULTURAL_SOURCE_ID:
            continue
        source_path = _resolve_source_path(project_dir, source.get("path"))
        if source_path is None or not source_path.exists():
            continue
        try:
            gdf = gpd.read_file(source_path)
        except Exception:
            continue
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        gdf = gdf[~gdf.geometry.isna()]
        gdf = gdf[~gdf.geometry.is_empty]
        if not gdf.empty:
            gdf = gdf.to_crs(analysis_crs)
            if bool(source.get("clip_to_analysis_bounds", True)):
                gdf = gdf[gdf.geometry.intersects(bounds_union)].copy()
        definition = source_catalog.get(source_id)
        layers.setdefault(source_id, []).append(
            {
                "source_id": source_id,
                "source_name": source.get("source_name") or getattr(definition, "name", "") or source_id,
                "source_category": source.get("source_category") or getattr(definition, "category", ""),
                "path": str(source_path),
                "status": source.get("status"),
                "gdf": gdf,
            }
        )
    return layers


def _renderable_source_records(
    *,
    project_dir: Path,
    comparison_unit_constraints: dict[str, Any],
    source_catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    try:
        registry = load_project_source_registry(project_dir)
    except SourceCatalogError:
        registry = None

    if registry is not None:
        for project_source in registry.sources:
            source_id = str(project_source.source_id or "")
            if not source_id or source_id == RESTRICTED_CULTURAL_SOURCE_ID or not project_source.enabled:
                continue
            source_path = resolve_project_source_path(project_dir, project_source)
            if source_path is None or not source_path.exists():
                continue
            key = (source_id, str(source_path))
            if key in seen:
                continue
            definition = source_catalog.get(source_id)
            records.append(
                {
                    "source_id": source_id,
                    "source_name": getattr(definition, "name", "") or source_id,
                    "source_category": getattr(project_source, "source_category", "") or getattr(definition, "category", ""),
                    "path": str(source_path),
                    "status": project_source.status or "registered_local",
                    "clip_to_analysis_bounds": str(project_source.status or "") != "local_materialized",
                }
            )
            seen.add(key)

    for source in _dict_list(comparison_unit_constraints.get("sources", [])):
        source_id = str(source.get("source_id", ""))
        if not source_id or str(source.get("status", "")) not in USABLE_SOURCE_STATUSES:
            continue
        source_path = _resolve_source_path(project_dir, source.get("path"))
        key = (source_id, str(source_path or source.get("path") or ""))
        if key in seen:
            continue
        record = dict(source)
        record["clip_to_analysis_bounds"] = True
        records.append(record)
        seen.add(key)
    return records


def _figure_extent_plan_record(
    *,
    project_dir: Path,
    target: FigureTarget,
    unit_gdf: gpd.GeoDataFrame,
    analysis_bounds: gpd.GeoDataFrame,
    source_context: dict[str, Any],
    source_layers: dict[str, list[dict[str, Any]]],
    comparison_unit_constraints: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    extent = target_extent_metadata(
        target_id=target.target_id,
        target_type="figure",
        source_categories=target.source_categories,
        query_distance=comparison_unit_constraints.get("default_buffer_feet"),
        query_units="feet",
    )
    extent_class = _extent_class_for_figure(extent)
    core_bounds = _core_bounds_for_extent_class(extent_class, analysis_bounds.total_bounds)
    issues: list[dict[str, Any]] = []
    status = "planned"
    status_reason = "Figure render extent is planned from current project geometry and available source layers."

    spec = _target_spec(target, source_context)
    target_source_ids = list(spec.source_ids) or _target_source_refs(source_context, target.source_categories)
    required_source_ids = list(spec.required_source_ids) or list(target_source_ids)
    public_source_ids = [source_id for source_id in target_source_ids if source_id != RESTRICTED_CULTURAL_SOURCE_ID]
    required_public_source_ids = [source_id for source_id in required_source_ids if source_id != RESTRICTED_CULTURAL_SOURCE_ID]
    layer_records = _target_source_layers(target, source_layers, spec)
    layer_records = [_filtered_layer(layer, spec.filter_tokens) for layer in layer_records]
    layer_records = [layer for layer in layer_records if layer["source_id"] != RESTRICTED_CULTURAL_SOURCE_ID]
    if target.target_id == "figure-cultural-resources":
        layer_records = [layer for layer in layer_records if layer["source_id"] in PUBLIC_CULTURAL_SOURCE_IDS]
    available_source_ids = {str(layer.get("source_id")) for layer in layer_records if layer.get("source_id")}
    required_available_source_ids = available_source_ids.intersection(required_public_source_ids)

    if extent_class == LARGE_WATERSHED_EXTENT_CLASS:
        if available_source_ids.intersection(WBD_HUC12_SOURCE_IDS):
            status = "planned_watershed_context"
            status_reason = "Materialized HUC-12 watershed/subwatershed polygons are available and used for watershed context rendering."
            core_bounds = _bounds_for_source_ids(layer_records, set(WBD_HUC12_SOURCE_IDS), fallback=core_bounds)
        else:
            status = "planned_current_project_area_context" if required_available_source_ids else "deferred_watershed_context"
            status_reason = (
                "HUC-12 watershed/subwatershed render context is not materialized; available source layers are rendered "
                "with the current project-area presentation extent and are not treated as watershed context."
                if required_available_source_ids
                else "HUC-12 watershed/subwatershed render context is not materialized; this plan does not use "
                "project-area bounds as a substitute for watershed context."
            )
            issues.append(
                _issue(
                    "warning",
                    "figure_extent_context_deferred",
                    status_reason,
                    str(project_dir / FIGURE_EXTENT_PLAN_PATH),
                    target_id=target.target_id,
                )
            )
    elif not required_available_source_ids:
        status = "source_unavailable_stub"
        status_reason = "Usable public source layers are not available, so no NAIP sidecar is needed for this figure target."
    elif extent_class in {MEDIUM_CONTEXT_EXTENT_CLASS, COUNTY_REGIONAL_EXTENT_CLASS}:
        status = "planned_current_project_area_context"
        if extent_class == COUNTY_REGIONAL_EXTENT_CLASS:
            status_reason = (
                "County/regional figure semantics are preserved in metadata; current rendering uses "
                "the medium/context presentation extent behavior until county/regional query extents are implemented."
            )
        else:
            status_reason = (
                "Medium/context figure uses a broader presentation extent for visual context only; "
                "automated evidence remains bounded by the current project-area source contracts."
            )

    layout = plan_render_layout_for_map(
        unit_gdf=unit_gdf,
        source_layers=layer_records,
        focus_bounds=core_bounds,
    )
    group = (
        _basemap_group_for_extent_class(extent_class)
        if extent_class != LARGE_WATERSHED_EXTENT_CLASS and status in PLANNED_FIGURE_STATUSES and spec.prefer_basemap and required_available_source_ids
        else ""
    )
    record = {
        "figure_id": target.target_id,
        "section_target_id": target.section_target_id,
        "title": target.title,
        "extent_class": extent_class,
        "status": status,
        "status_reason": status_reason,
        "source_refs": sorted(set(public_source_ids)),
        "available_source_refs": sorted({str(layer.get("source_id")) for layer in layer_records if layer.get("source_id")}),
        "source_scope": _source_scope_record(spec, available_source_ids),
        "core_extent_type": extent.get("figure_extent_type") or extent.get("analysis_extent_type"),
        "core_bounds": [float(value) for value in core_bounds],
        "core_bounds_crs": str(analysis_bounds.crs or ""),
        "render_layout": layout,
        "full_render_bounds": [float(value) for value in layout.get("expanded_bounds", [])],
        "collar_bounds": [float(value) for value in layout.get("collar_bounds", [])],
        "collar_side": str(layout.get("legend_side") or "none"),
        "layout_strategy": str(layout.get("layout_strategy") or ""),
        "map_furniture": _map_furniture_estimates(layout),
        "render_extent_type": layout.get("render_extent_type"),
        "render_extent_is_presentation_only": True,
        "presentation_extent_type": layout.get("presentation_extent_type") or "",
        "basemap_materialization_group": group,
        "basemap_materialization_required": bool(group),
    }
    return record, issues


def _extent_class_for_figure(extent: dict[str, Any]) -> str:
    scope = str(extent.get("figure_extent_type") or extent.get("analysis_extent_type") or "")
    if scope == WATERSHED_CONTEXT_EXTENT:
        return LARGE_WATERSHED_EXTENT_CLASS
    if scope == COUNTY_OR_REGIONAL_CONTEXT_EXTENT:
        return COUNTY_REGIONAL_EXTENT_CLASS
    if scope in {NEARBY_CONTEXT_EXTENT, COMMUNITY_CONTEXT_EXTENT}:
        return MEDIUM_CONTEXT_EXTENT_CLASS
    if scope in {DIRECT_INTERSECTION_EXTENT, SCREENING_BUFFER_EXTENT}:
        return SMALL_DIRECT_EXTENT_CLASS
    return SMALL_DIRECT_EXTENT_CLASS


def _core_bounds_for_extent_class(extent_class: str, analysis_bounds: Any) -> tuple[float, float, float, float]:
    bounds = _clean_bounds_tuple(analysis_bounds)
    if extent_class in {MEDIUM_CONTEXT_EXTENT_CLASS, COUNTY_REGIONAL_EXTENT_CLASS}:
        return _pad_bounds(bounds, 0.2)
    return bounds


def _bounds_for_source_ids(
    layer_records: list[dict[str, Any]],
    source_ids: set[str],
    *,
    fallback: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    bounds: list[Any] = []
    for layer in layer_records:
        if str(layer.get("source_id") or "") not in source_ids:
            continue
        gdf = layer.get("gdf")
        if isinstance(gdf, gpd.GeoDataFrame) and not gdf.empty:
            bounds.append(gdf.total_bounds)
    if not bounds:
        return fallback
    return _clean_bounds_tuple(
        (
            min(float(bound[0]) for bound in bounds),
            min(float(bound[1]) for bound in bounds),
            max(float(bound[2]) for bound in bounds),
            max(float(bound[3]) for bound in bounds),
        )
    )


def _basemap_group_for_extent_class(extent_class: str) -> str:
    if extent_class == COUNTY_REGIONAL_EXTENT_CLASS:
        return MEDIUM_CONTEXT_EXTENT_CLASS
    return extent_class


def _basemap_materialization_groups(records: list[dict[str, Any]], analysis_crs: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        group_id = str(record.get("basemap_materialization_group") or "")
        if not group_id:
            continue
        full_bounds = _clean_bounds_tuple(record.get("full_render_bounds", []))
        core_bounds = _clean_bounds_tuple(record.get("core_bounds", []))
        group = grouped.setdefault(
            group_id,
            {
                "group_id": group_id,
                "extent_class": group_id,
                "analysis_crs": analysis_crs,
                "figure_ids": [],
                "core_extent": list(core_bounds),
                "full_render_extent": list(full_bounds),
                "render_extent_is_presentation_only": True,
                "collar_sides": [],
                "status": "planned",
            },
        )
        group["figure_ids"].append(str(record.get("figure_id")))
        group["core_extent"] = list(_merge_bounds(group["core_extent"], core_bounds))
        group["full_render_extent"] = list(_merge_bounds(group["full_render_extent"], full_bounds))
        collar_side = str(record.get("collar_side") or "")
        if collar_side and collar_side not in group["collar_sides"]:
            group["collar_sides"].append(collar_side)
    return [grouped[key] for key in sorted(grouped)]


def _map_furniture_estimates(layout: dict[str, Any]) -> dict[str, Any]:
    side = str(layout.get("legend_side") or "none")
    bbox = layout.get("legend_bbox_axes") if isinstance(layout.get("legend_bbox_axes"), list) else []
    collar = layout.get("collar_bounds") if isinstance(layout.get("collar_bounds"), list) else []
    in_collar = bool(collar and side in {"right", "left", "top", "bottom"})
    return {
        "legend": {
            "label_count": int(layout.get("legend_label_count") or 0),
            "bbox_axes": bbox,
            "placement": "presentation_collar" if in_collar else "map_frame",
        },
        "north_arrow": {
            "placement": "presentation_collar" if in_collar else "map_frame",
        },
        "scale_bar": {
            "placement": "presentation_collar" if in_collar else "map_frame",
        },
    }


def _clean_bounds_tuple(bounds: Any) -> tuple[float, float, float, float]:
    west, south, east, north = [float(value) for value in bounds]
    if west > east:
        west, east = east, west
    if south > north:
        south, north = north, south
    return (west, south, east, north)


def _pad_bounds(bounds: tuple[float, float, float, float], fraction: float) -> tuple[float, float, float, float]:
    west, south, east, north = bounds
    width = max(east - west, 1.0)
    height = max(north - south, 1.0)
    return (
        west - width * fraction,
        south - height * fraction,
        east + width * fraction,
        north + height * fraction,
    )


def _merge_bounds(left: Any, right: Any) -> tuple[float, float, float, float]:
    lw, ls, le, ln = _clean_bounds_tuple(left)
    rw, rs, re, rn = _clean_bounds_tuple(right)
    return (min(lw, rw), min(ls, rs), max(le, re), max(ln, rn))


def _resolve_source_path(project_dir: Path, value: Any) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    return project_dir / path


def _figure_for_target(
    *,
    project_dir: Path,
    figures_dir: Path,
    target: FigureTarget,
    matrix_version: str,
    unit_gdf: gpd.GeoDataFrame,
    analysis_bounds: gpd.GeoDataFrame,
    analysis_crs: str,
    project_area: dict[str, Any],
    source_context: dict[str, Any],
    source_layers: dict[str, list[dict[str, Any]]],
    constraints: list[dict[str, Any]],
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
    figure_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = _target_spec(target, source_context)
    target_source_ids = list(spec.source_ids) or _target_source_refs(source_context, target.source_categories)
    required_source_ids = list(spec.required_source_ids) or list(target_source_ids)
    public_source_ids = [source_id for source_id in target_source_ids if source_id != RESTRICTED_CULTURAL_SOURCE_ID]
    required_public_source_ids = [source_id for source_id in required_source_ids if source_id != RESTRICTED_CULTURAL_SOURCE_ID]
    validation_issues: list[dict[str, Any]] = []
    uncertainty_flags: set[str] = {"draft_pre_review", "desktop_screening_only"}

    layer_records = _target_source_layers(target, source_layers, spec)
    layer_records = [_filtered_layer(layer, spec.filter_tokens) for layer in layer_records]
    layer_records = [layer for layer in layer_records if layer["source_id"] != RESTRICTED_CULTURAL_SOURCE_ID]
    available_source_ids = {str(layer["source_id"]) for layer in layer_records}
    required_available_source_ids = available_source_ids.intersection(required_public_source_ids)
    validation_issues.extend(_source_availability_issues(target, required_public_source_ids, source_context, available_source_ids))
    if target.target_id == "figure-cultural-resources" and _restricted_cultural_present(source_context):
        validation_issues.append(
            _issue(
                "warning",
                "restricted_source_not_mapped",
                "Restricted archaeological source status is present, but restricted locations are not rendered or exposed in deliverable figures.",
                str(project_dir / DELIVERABLE_FIGURES_PATH),
                source_id=RESTRICTED_CULTURAL_SOURCE_ID,
                target_id=target.target_id,
            )
        )
        uncertainty_flags.add("restricted_source_not_mapped")

    if spec.source_unimplemented_note:
        validation_issues.append(
            _issue(
                "warning",
                "figure_source_unimplemented",
                spec.source_unimplemented_note,
                str(project_dir / DELIVERABLE_FIGURES_PATH),
                target_id=target.target_id,
            )
        )
        uncertainty_flags.add("source_unimplemented")

    if isinstance(figure_plan, dict) and str(figure_plan.get("status") or "") in {
        "deferred_watershed_context",
        "planned_current_project_area_context",
    }:
        validation_issues.append(
            _issue(
                "warning",
                "figure_extent_context_deferred",
                str(
                    figure_plan.get("status_reason")
                    or "HUC-12 watershed/subwatershed context is not materialized for this figure target."
                ),
                str(project_dir / FIGURE_EXTENT_PLAN_PATH),
                target_id=target.target_id,
            )
        )
        if str(figure_plan.get("status") or "") == "deferred_watershed_context" and not required_available_source_ids:
            return _stub_figure(
                target=target,
                matrix_version=matrix_version,
                public_source_ids=required_public_source_ids,
                comparison_unit_ids=_comparison_unit_ids(unit_gdf),
                comparison_unit_constraints=comparison_unit_constraints,
                source_status=source_status,
                uncertainty_flags=sorted(uncertainty_flags | {"figure_extent_context_deferred"}),
                validation_issues=validation_issues,
                figure_plan=figure_plan,
                source_scope=_source_scope_record(spec, available_source_ids),
            )
        uncertainty_flags.add("figure_extent_context_deferred")

    if not required_available_source_ids:
        return _stub_figure(
            target=target,
            matrix_version=matrix_version,
            public_source_ids=required_public_source_ids,
            comparison_unit_ids=_comparison_unit_ids(unit_gdf),
            comparison_unit_constraints=comparison_unit_constraints,
            source_status=source_status,
            uncertainty_flags=sorted(uncertainty_flags | {"source_unavailable"}),
            validation_issues=validation_issues,
            figure_plan=figure_plan,
            source_scope=_source_scope_record(spec, available_source_ids),
        )

    if target.target_id == "figure-cultural-resources":
        available_source_ids = available_source_ids.intersection(PUBLIC_CULTURAL_SOURCE_IDS)
        layer_records = [layer for layer in layer_records if layer["source_id"] in PUBLIC_CULTURAL_SOURCE_IDS]
        if not layer_records:
            return _stub_figure(
                target=target,
                matrix_version=matrix_version,
                public_source_ids=sorted(PUBLIC_CULTURAL_SOURCE_IDS),
                comparison_unit_ids=_comparison_unit_ids(unit_gdf),
                comparison_unit_constraints=comparison_unit_constraints,
                source_status=source_status,
                uncertainty_flags=sorted(uncertainty_flags | {"source_unavailable"}),
                validation_issues=validation_issues,
                figure_plan=figure_plan,
                source_scope=_source_scope_record(spec, available_source_ids),
            )

    planned_layout = figure_plan.get("render_layout") if isinstance(figure_plan, dict) and isinstance(figure_plan.get("render_layout"), dict) else None
    required_render_bounds = planned_layout.get("expanded_bounds") if isinstance(planned_layout, dict) else None
    basemap_group = str(figure_plan.get("basemap_materialization_group") or "") if isinstance(figure_plan, dict) else ""
    basemap = (
        load_basemap(
            project_area,
            analysis_crs,
            required_bounds=required_render_bounds,
            required_bounds_crs=analysis_crs,
            extent_class=basemap_group or None,
        )
        if spec.prefer_basemap
        else {"layer": None, "issues": [], "flags": [], "shown_layer": None}
    )
    validation_issues.extend(_dict_list(basemap.get("issues", [])))
    uncertainty_flags.update(_string_list(basemap.get("flags", [])))

    image_path = figures_dir / f"{target.target_id}.png"
    source_note = _source_note(layer_records, basemap, target_id=target.target_id, figure_plan=figure_plan)
    method_note = _method_note(analysis_crs, include_basemap=bool(basemap.get("layer")))
    try:
        render_layout = render_map(
            output_path=image_path,
            title=target.title,
            unit_gdf=unit_gdf,
            analysis_crs=analysis_crs,
            source_layers=layer_records,
            basemap=basemap,
            method_note=method_note,
            source_note=source_note,
            focus_bounds=figure_plan.get("core_bounds") if isinstance(figure_plan, dict) else analysis_bounds.total_bounds,
            render_layout=planned_layout,
        )
    except Exception as exc:  # pragma: no cover - rendering failures are backend dependent.
        validation_issues.append(
            _issue(
                "warning",
                "basemap_render_failed",
                f"Deliverable figure rendering failed; a stub was created instead: {exc}",
                str(image_path),
                target_id=target.target_id,
            )
        )
        return _stub_figure(
            target=target,
            matrix_version=matrix_version,
            public_source_ids=public_source_ids,
            comparison_unit_ids=_comparison_unit_ids(unit_gdf),
            comparison_unit_constraints=comparison_unit_constraints,
            source_status=source_status,
            uncertainty_flags=sorted(uncertainty_flags | {"basemap_render_failed"}),
            validation_issues=validation_issues,
            figure_plan=figure_plan,
            source_scope=_source_scope_record(spec, available_source_ids),
        )

    related_constraints = _related_constraint_ids(constraints, required_public_source_ids, spec.filter_tokens)
    source_refs = sorted(available_source_ids)
    source_refs.extend(_basemap_source_refs(basemap))
    shown_layers = [
        _comparison_units_shown_layer(unit_gdf),
        *[_source_shown_layer(layer, index) for index, layer in enumerate(layer_records)],
    ]
    if basemap.get("shown_layer"):
        shown_layers.append(dict(basemap["shown_layer"]))
    return _deliverable_figure(
        target=target,
        matrix_version=matrix_version,
        image_path=image_path,
        caption=_caption(target),
        source_note=source_note,
        method_note=method_note,
        shown_layers=shown_layers,
        source_refs=sorted(set(source_refs)),
        related_constraint_ids=related_constraints,
        comparison_unit_ids=_comparison_unit_ids(unit_gdf),
        uncertainty_flags=sorted(uncertainty_flags),
        provenance=_provenance(
            target=target,
            matrix_version=matrix_version,
            comparison_unit_constraints=comparison_unit_constraints,
            source_status=source_status,
            method="geopandas_matplotlib_matrix_deliverable_figure",
            analysis_crs=analysis_crs,
            project_area=project_area,
            basemap=basemap,
            render_layout=render_layout,
            figure_plan=figure_plan,
            source_scope=_source_scope_record(spec, available_source_ids),
        ),
        validation_issues=_dedupe_issues(validation_issues),
    )


def _target_spec(target: FigureTarget, source_context: dict[str, Any]) -> TargetFigureSpec:
    return TARGET_SPECS.get(target.target_id, TargetFigureSpec(_target_source_refs(source_context, target.source_categories)))


def _target_source_layers(
    target: FigureTarget,
    source_layers: dict[str, list[dict[str, Any]]],
    spec: TargetFigureSpec | None = None,
) -> list[dict[str, Any]]:
    spec = spec or TARGET_SPECS.get(target.target_id, TargetFigureSpec(()))
    layers: list[dict[str, Any]] = []
    excluded = set(spec.excluded_source_ids)
    for source_id in spec.source_ids:
        if source_id in excluded:
            continue
        layers.extend(dict(layer) for layer in source_layers.get(source_id, []))
    return layers


def _source_scope_record(spec: TargetFigureSpec, rendered_source_ids: set[str]) -> dict[str, Any]:
    required = [source_id for source_id in spec.required_source_ids if source_id != RESTRICTED_CULTURAL_SOURCE_ID]
    optional = [source_id for source_id in spec.optional_source_ids if source_id != RESTRICTED_CULTURAL_SOURCE_ID]
    excluded = [source_id for source_id in spec.excluded_source_ids if source_id != RESTRICTED_CULTURAL_SOURCE_ID]
    rendered = sorted(source_id for source_id in rendered_source_ids if source_id != RESTRICTED_CULTURAL_SOURCE_ID)
    missing_required = sorted(source_id for source_id in required if source_id not in rendered_source_ids)
    return {
        "required_source_ids": required,
        "optional_source_ids": optional,
        "excluded_source_ids": excluded,
        "allowed_source_ids": list(spec.source_ids),
        "rendered_source_ids": rendered,
        "missing_required_source_ids": missing_required,
    }


def _filtered_layer(layer: dict[str, Any], tokens: tuple[str, ...]) -> dict[str, Any]:
    if not tokens:
        return layer
    gdf = layer["gdf"]
    if gdf.empty:
        return dict(layer)
    mask = gdf.apply(lambda row: any(token in _row_text(row) for token in tokens), axis=1)
    filtered = gdf[mask].copy()
    result = dict(layer)
    result["gdf"] = filtered
    return result


def _row_text(row: Any) -> str:
    values: list[str] = []
    for column in row.index:
        if column == "geometry":
            continue
        value = row[column]
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            values.append(text.lower())
    return " ".join(values)


def _source_availability_issues(
    target: FigureTarget,
    source_ids: list[str],
    source_context: dict[str, Any],
    available_source_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    details = source_context.get("details_by_id", {})
    available = available_source_ids or set()
    rollup_satisfied_children: set[str] = set()
    if isinstance(details, dict):
        for rollup_id, child_ids in LOGICAL_ROLLUP_SATISFIERS.items():
            if rollup_id in source_ids and str(details.get(rollup_id, {}).get("status", "")) == "logical_rollup_satisfied":
                rollup_satisfied_children.update(child_ids)
    for source_id in source_ids:
        if source_id in available or source_id in rollup_satisfied_children:
            continue
        detail = details.get(source_id, {}) if isinstance(details, dict) else {}
        status = str(detail.get("status", ""))
        if status in UNIMPLEMENTED_SOURCE_STATUSES:
            issues.append(
                _issue(
                    "warning",
                    "figure_source_unimplemented",
                    f"Source '{source_id}' is not implemented for automated figure rendering.",
                    str(DELIVERABLE_FIGURES_PATH),
                    source_id=source_id,
                    target_id=target.target_id,
                )
            )
        elif not status or status in MISSING_SOURCE_STATUSES:
            issues.append(
                _issue(
                    "warning",
                    "figure_source_missing",
                    f"Source '{source_id}' is not available for this deliverable figure.",
                    str(DELIVERABLE_FIGURES_PATH),
                    source_id=source_id,
                    target_id=target.target_id,
                )
            )
    return issues


def _stub_figure(
    *,
    target: FigureTarget,
    matrix_version: str,
    public_source_ids: list[str],
    comparison_unit_ids: list[str],
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
    uncertainty_flags: list[str],
    validation_issues: list[dict[str, Any]],
    figure_plan: dict[str, Any] | None = None,
    source_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issues = list(validation_issues)
    issues.append(
        _issue(
            "warning",
            "figure_created_as_stub",
            "Required matrix-backed figure was created as an explicit stub because usable public source data or rendering support is unavailable.",
            str(DELIVERABLE_FIGURES_PATH),
            target_id=target.target_id,
        )
    )
    flags = sorted(set(uncertainty_flags or ["source_unavailable"]) | {"figure_stub"})
    provenance = _provenance(
        target=target,
        matrix_version=matrix_version,
        comparison_unit_constraints=comparison_unit_constraints,
        source_status=source_status,
        method="matrix_stub_for_unavailable_figure_source",
        analysis_crs=str(comparison_unit_constraints.get("analysis_crs", "")),
        project_area=None,
        basemap=None,
        figure_plan=figure_plan,
        source_scope=source_scope,
    )
    extent = _figure_extent(target, provenance)
    figure_policy = _figure_policy_summary(target)
    return {
        "figure_id": target.target_id,
        "type": "deliverable_figure",
        "figure_type": "deliverable_figure",
        "figure_number": target.figure_number,
        "title": target.title,
        "section_target_id": target.section_target_id,
        "image_path": "",
        "file_format": "png",
        "caption": _caption(target),
        "source_note": "Source data unavailable or unsupported for automated figure rendering.",
        "method_note": "Matrix-required figure placeholder. No regulatory determination is made.",
        "map_elements": [],
        "figure_group": "deliverable_main",
        "related_resource_categories": list(target.source_categories),
        "shown_layers": [],
        "source_refs": sorted(set(public_source_ids)),
        "layer_refs": [],
        "related_constraint_ids": [],
        "comparison_unit_ids": comparison_unit_ids,
        **extent,
        "figure_policy": figure_policy,
        "provenance": provenance,
        "uncertainty_flags": flags,
        "is_stub": True,
        "stub_text": REQUIRED_STUB_TEXT,
        "review_status": "needs_review",
        "validation_issues": _dedupe_issues(issues),
    }


def _deliverable_figure(
    *,
    target: FigureTarget,
    matrix_version: str,
    image_path: Path,
    caption: str,
    source_note: str,
    method_note: str,
    shown_layers: list[dict[str, Any]],
    source_refs: list[str],
    related_constraint_ids: list[str],
    comparison_unit_ids: list[str],
    uncertainty_flags: list[str],
    provenance: dict[str, Any],
    validation_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    extent = _figure_extent(target, provenance)
    figure_policy = _figure_policy_summary(target)
    return {
        "figure_id": target.target_id,
        "type": "deliverable_figure",
        "figure_type": "deliverable_figure",
        "figure_number": target.figure_number,
        "title": target.title,
        "section_target_id": target.section_target_id,
        "image_path": str(image_path),
        "file_format": "png",
        "caption": caption,
        "source_note": source_note,
        "method_note": method_note,
        "map_elements": DELIVERABLE_MAP_ELEMENT_BASELINE,
        "figure_group": "deliverable_main",
        "related_resource_categories": list(target.source_categories),
        "shown_layers": shown_layers,
        "source_refs": source_refs,
        "layer_refs": [str(layer.get("path")) for layer in shown_layers if layer.get("path")],
        "related_constraint_ids": related_constraint_ids,
        "comparison_unit_ids": comparison_unit_ids,
        **extent,
        "figure_policy": figure_policy,
        "provenance": provenance,
        "uncertainty_flags": uncertainty_flags,
        "is_stub": False,
        "stub_text": "",
        "review_status": "draft",
        "validation_issues": validation_issues,
    }


def _attachment_supporting_figures(
    *,
    figures_dir: Path,
    unit_gdf: gpd.GeoDataFrame,
    source_layers: list[dict[str, Any]],
    analysis_crs: str,
    project_area: dict[str, Any],
    matrix_version: str,
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    west, south, east, north = [float(value) for value in unit_gdf.total_bounds]
    width = east - west
    height = north - south
    if width <= 0 or height <= 0:
        return [], []
    aspect = max(width / height, height / width)
    if aspect <= PANEL_ASPECT_THRESHOLD:
        return [], []
    panel_count = min(MAX_PANEL_COUNT, max(2, int(math.ceil(aspect / PANEL_ASPECT_THRESHOLD)) + 1))
    panels = panel_bounds((west, south, east, north), panel_count)
    basemap = load_basemap(project_area, analysis_crs, extent_class=SMALL_DIRECT_EXTENT_CLASS)
    records: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for index, bounds in enumerate(panels, start=1):
        panel_id = f"attachment-a-panel-{index:03d}"
        image_path = figures_dir / f"{panel_id}.png"
        try:
            render_layout = render_map(
                output_path=image_path,
                title=f"Attachment A Supporting Panel {index}",
                unit_gdf=unit_gdf,
                analysis_crs=analysis_crs,
                source_layers=source_layers,
                basemap=basemap,
                method_note=_method_note(analysis_crs, include_basemap=bool(basemap.get("layer"))),
                source_note=_source_note(source_layers, basemap),
                focus_bounds=bounds,
            )
        except Exception as exc:  # pragma: no cover - rendering failures are backend dependent.
            issues.append(
                _issue(
                    "warning",
                    "panel_map_generation_skipped",
                    f"Attachment A panel map generation was skipped for panel {index}: {exc}",
                    str(image_path),
                )
            )
            continue
        records.append(
            apply_extent_metadata(
                {
                "figure_id": panel_id,
                "type": "attachment_supporting_figure",
                "figure_type": "attachment_panel_map",
                "title": f"Attachment A Supporting Panel {index}",
                "section_target_id": "attachment-a-project-maps",
                "image_path": str(image_path),
                "file_format": "png",
                "caption": f"Supporting panel map {index} for elongated project extent.",
                "source_note": _source_note(source_layers, basemap),
                "method_note": _method_note(analysis_crs, include_basemap=bool(basemap.get("layer"))),
                "map_elements": DELIVERABLE_MAP_ELEMENT_BASELINE,
                "figure_group": "attachment_supporting_figures",
                "shown_layers": [
                    _comparison_units_shown_layer(unit_gdf),
                    *[_source_shown_layer(layer, source_index) for source_index, layer in enumerate(source_layers)],
                    *([dict(basemap["shown_layer"])] if basemap.get("shown_layer") else []),
                ],
                "source_refs": sorted({str(layer.get("source_id")) for layer in source_layers if layer.get("source_id")} | set(_basemap_source_refs(basemap))),
                "provenance": {
                    "matrix_version": matrix_version,
                    "attachment_target_id": "attachment-environmental-constraints-maps",
                    "method": "long_axis_panel_slice",
                    "analysis_crs": analysis_crs,
                    "panel_index": index,
                    "panel_count": panel_count,
                    "comparison_unit_constraints_path": comparison_unit_constraints.get("output_path"),
                    "source_status_path": source_status.get("output_path"),
                    "basemap": {
                        "source_id": str(basemap.get("source_ref") or MARIS_NAIP_SOURCE_ID),
                        "selected_paths": _string_list(basemap.get("selected_paths", [])),
                        "renderable_paths": _string_list(basemap.get("renderable_paths", [])),
                        "rendered_path": basemap.get("shown_layer", {}).get("path") if isinstance(basemap.get("shown_layer"), dict) else None,
                    },
                    "render_layout": render_layout,
                    "review_before_export": True,
                    "desktop_screening_only": True,
                },
                "uncertainty_flags": sorted({"draft_pre_review", "desktop_screening_only", *_string_list(basemap.get("flags", []))}),
                "review_status": "draft",
                "validation_issues": _dict_list(basemap.get("issues", [])),
            },
                render_extent_metadata(render_layout),
            )
        )
    return records, _dedupe_issues(issues)


def _related_constraint_ids(constraints: list[dict[str, Any]], source_ids: list[str], tokens: tuple[str, ...]) -> list[str]:
    source_id_set = set(source_ids)
    result: set[str] = set()
    for constraint in constraints:
        if str(constraint.get("source_id", "")) not in source_id_set:
            continue
        if tokens and not any(token in _constraint_text(constraint) for token in tokens):
            continue
        constraint_id = str(constraint.get("constraint_id", ""))
        if constraint_id:
            result.add(constraint_id)
    return sorted(result)


def _constraint_text(constraint: dict[str, Any]) -> str:
    values = [
        constraint.get("source_name"),
        constraint.get("source_layer"),
        constraint.get("source_feature_label"),
        constraint.get("source_feature_type"),
        constraint.get("source_feature_subtype"),
    ]
    feature_values = constraint.get("source_feature_values", {})
    if isinstance(feature_values, dict):
        values.extend(feature_values.values())
    return " ".join(str(value).lower() for value in values if str(value).strip())


def _provenance(
    *,
    target: FigureTarget,
    matrix_version: str,
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
    method: str,
    analysis_crs: str,
    project_area: dict[str, Any] | None,
    basemap: dict[str, Any] | None,
    render_layout: dict[str, Any] | None = None,
    figure_plan: dict[str, Any] | None = None,
    source_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extent = target_extent_metadata(
        target_id=target.target_id,
        target_type="figure",
        source_categories=target.source_categories,
        query_distance=comparison_unit_constraints.get("default_buffer_feet"),
        query_units="feet",
    )
    if render_layout:
        render_extent = render_extent_metadata(render_layout)
        extent["render_extent_type"] = render_extent["render_extent_type"]
        extent["render_extent_is_presentation_only"] = render_extent["render_extent_is_presentation_only"]
        if render_extent.get("presentation_extent_type"):
            extent["presentation_extent_type"] = render_extent["presentation_extent_type"]
    if isinstance(figure_plan, dict) and str(figure_plan.get("status") or "") == "planned_watershed_context":
        extent["source_selection_reason"] = (
            "Materialized HUC-12 watershed/subwatershed polygons are available for watershed context. "
            "Watershed context remains broader than direct project-feature intersection."
        )
    provenance = {
        "matrix_version": matrix_version,
        "figure_target_id": target.target_id,
        "section_target_id": target.section_target_id,
        "method": method,
        "comparison_unit_constraints_path": comparison_unit_constraints.get("output_path"),
        "source_status_path": source_status.get("output_path"),
        "project_area_path": project_area.get("output_path") if project_area else None,
        "source_categories": list(target.source_categories),
        "figure_policy": _figure_policy_summary(target),
        "analysis_crs": analysis_crs,
        "extent_policy": extent,
        "review_before_export": True,
        "desktop_screening_only": True,
    }
    if basemap:
        provenance["basemap"] = {
            "source_id": str(basemap.get("source_ref") or MARIS_NAIP_SOURCE_ID),
            "selected_paths": _string_list(basemap.get("selected_paths", [])),
            "renderable_paths": _string_list(basemap.get("renderable_paths", [])),
            "rendered_path": basemap.get("shown_layer", {}).get("path") if isinstance(basemap.get("shown_layer"), dict) else None,
            "extent_class": basemap.get("shown_layer", {}).get("extent_class") if isinstance(basemap.get("shown_layer"), dict) else None,
        }
    if isinstance(figure_plan, dict):
        provenance["figure_extent_plan"] = {
            "plan_path": str(FIGURE_EXTENT_PLAN_PATH),
            "plan_version": FIGURE_EXTENT_PLAN_VERSION,
            "figure_id": figure_plan.get("figure_id"),
            "extent_class": figure_plan.get("extent_class"),
            "status": figure_plan.get("status"),
            "basemap_materialization_group": figure_plan.get("basemap_materialization_group"),
            "full_render_bounds": figure_plan.get("full_render_bounds", []),
            "collar_bounds": figure_plan.get("collar_bounds", []),
            "collar_side": figure_plan.get("collar_side"),
            "render_extent_is_presentation_only": True,
        }
    if isinstance(source_scope, dict):
        provenance["source_scope"] = source_scope
    if render_layout:
        provenance["render_layout"] = render_layout
    return provenance


def _figure_extent(target: FigureTarget, provenance: dict[str, Any]) -> dict[str, Any]:
    extent = provenance.get("extent_policy")
    if not isinstance(extent, dict):
        extent = target_extent_metadata(target_id=target.target_id, target_type="figure", source_categories=target.source_categories)
    return apply_extent_metadata({}, extent)


def _figure_policy_summary(target: FigureTarget) -> dict[str, Any]:
    policy = default_report_section_policy().by_figure_id().get(target.target_id)
    if policy is None:
        return {
            "figure_id": target.target_id,
            "title": target.title,
            "extent_policy": "",
            "visual_extent_class": "",
            "rendering_extent_class": "",
            "render_extent_is_presentation_only": True,
            "allowed_source_categories": list(target.source_categories),
        }
    return _figure_policy_to_dict(policy)


def _figure_policy_to_dict(policy: FigurePolicy) -> dict[str, Any]:
    return {
        "figure_id": policy.figure_id,
        "title": policy.title,
        "extent_policy": policy.extent_policy,
        "visual_extent_class": policy.visual_extent_class,
        "rendering_extent_class": policy.rendering_extent_class,
        "render_extent_is_presentation_only": policy.render_extent_is_presentation_only,
        "allowed_source_categories": list(policy.allowed_source_categories),
    }


def _caption(target: FigureTarget) -> str:
    return str(target.title)


def _method_note(analysis_crs: str, *, include_basemap: bool) -> str:
    method = "Vector and selected renderable basemap sidecar" if include_basemap else "Vector-only"
    return f"{method} screening map. Analysis CRS: {analysis_crs}."


def _source_note(
    source_layers: list[dict[str, Any]],
    basemap: dict[str, Any] | None,
    *,
    target_id: str = "",
    figure_plan: dict[str, Any] | None = None,
) -> str:
    labels = []
    source_ids = {str(layer.get("source_id") or "") for layer in source_layers}
    for layer in source_layers:
        count = int(len(layer["gdf"]))
        labels.append(f"{layer.get('source_name') or layer.get('source_id')} ({count} features)")
    if basemap and basemap.get("shown_layer"):
        shown = basemap["shown_layer"]
        label = str(shown.get("label") or MARIS_NAIP_SOURCE_NAME)
        if shown.get("renderable"):
            labels.append(f"{label} rendered from sidecar")
        elif shown.get("renderability_status") == "materialization_failed":
            labels.append(f"{label} materialization failed; vector-only fallback used")
        elif shown.get("renderability_status") == "render_asset_missing":
            labels.append(f"{label} render asset missing; vector-only fallback used")
        else:
            labels.append(f"{label} not rendered; vector-only fallback used")
    if basemap:
        for failure in _dict_list(basemap.get("materialization_failures", [])):
            label = str(failure.get("label") or "USDA NAIP Project Basemap")
            message = f"{label} materialization failed; vector-only fallback used"
            if message not in labels:
                labels.append(message)
    if not labels:
        return ""
    notes: list[str] = []
    if target_id == "figure-public-water-supply-wells":
        notes.append(
            "Public water supply wells are mapped context only; mapped proximity is not a service impact or direct impact determination."
        )
    if target_id == "figure-streams-impaired-waters":
        if any(source_id.startswith("usgs_nhd_") for source_id in source_ids):
            notes.append("NHD hydrography is shown where project-local NHD layers are available.")
        if "mdeq_303d_impaired_waters" in source_ids:
            notes.append("MDEQ 303(d) impaired waters and TMDL-complete waters are shown where available.")
        if isinstance(figure_plan, dict) and str(figure_plan.get("extent_class") or "") == LARGE_WATERSHED_EXTENT_CLASS:
            if "usgs_wbd_huc12_subwatersheds" in source_ids and str(figure_plan.get("status") or "") == "planned_watershed_context":
                notes.append("USGS WBD HUC-12 subwatershed boundaries are shown for watershed context.")
            else:
                notes.append("Watershed/subwatershed context remains deferred and is not inferred from project-area bounds.")
    source_sentence = "Sources: " + "; ".join(labels) + "."
    return source_sentence + ((" " + " ".join(notes)) if notes else "")


def _comparison_unit_ids(unit_gdf: gpd.GeoDataFrame) -> list[str]:
    if "comparison_unit_id" not in unit_gdf.columns:
        return []
    return [str(value) for value in unit_gdf["comparison_unit_id"].tolist() if str(value).strip()]


def _comparison_units_shown_layer(unit_gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    return {
        "layer_type": "comparison_units",
        "label": "Comparison units",
        "feature_count": int(len(unit_gdf)),
        "comparison_unit_ids": _comparison_unit_ids(unit_gdf),
        "geometry_type_counts": _geometry_type_counts(unit_gdf),
        "rendered_as": "individual_comparison_units",
        "unit_styles": comparison_unit_style_records(unit_gdf),
    }


def _source_shown_layer(layer: dict[str, Any], index: int) -> dict[str, Any]:
    gdf = layer["gdf"]
    render_style = source_layer_style_record(layer, index)
    return {
        "layer_type": "source_layer",
        "source_id": layer.get("source_id"),
        "label": layer.get("source_name") or layer.get("source_id"),
        "legend_label": render_style["label"],
        "render_style": {
            "color": render_style["color"],
            "marker": render_style["marker"],
            "line_width": render_style["line_width"],
            "line_alpha": render_style["line_alpha"],
            "polygon_alpha": render_style["polygon_alpha"],
            "marker_size": render_style["marker_size"],
            "marker_edge_color": render_style["marker_edge_color"],
            "marker_edge_width": render_style["marker_edge_width"],
            "marker_halo_color": render_style["marker_halo_color"],
            "marker_halo_alpha": render_style["marker_halo_alpha"],
            "point_alpha": render_style["point_alpha"],
            "style_source": render_style["style_source"],
        },
        "path": layer.get("path"),
        "feature_count": int(len(gdf)),
        "geometry_type_counts": _geometry_type_counts(gdf),
    }


def _geometry_type_counts(gdf: gpd.GeoDataFrame) -> dict[str, int]:
    if gdf.empty:
        return {}
    counts = gdf.geometry.geom_type.value_counts().to_dict()
    return {str(key): int(value) for key, value in sorted(counts.items())}


def _target_source_refs(source_context: dict[str, Any], categories: list[str]) -> tuple[str, ...]:
    refs: set[str] = set()
    ids_by_category = source_context.get("ids_by_category", {})
    if isinstance(ids_by_category, dict):
        for category in categories:
            refs.update(_string_list(ids_by_category.get(category, [])))
    return tuple(sorted(refs))


def _restricted_cultural_present(source_context: dict[str, Any]) -> bool:
    details = source_context.get("details_by_id", {})
    if isinstance(details, dict) and RESTRICTED_CULTURAL_SOURCE_ID in details:
        status = str(details[RESTRICTED_CULTURAL_SOURCE_ID].get("status", ""))
        return bool(status)
    ids_by_category = source_context.get("ids_by_category", {})
    return isinstance(ids_by_category, dict) and RESTRICTED_CULTURAL_SOURCE_ID in _string_list(ids_by_category.get("cultural_historic", []))


def _dedupe_source_layers(layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for layer in layers:
        key = (str(layer.get("source_id", "")), str(layer.get("path", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append(layer)
    return result


def _issue(
    severity: str,
    code: str,
    message: str,
    location: str,
    *,
    source_id: str | None = None,
    target_id: str | None = None,
) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "location": location,
    }
    if source_id:
        issue["source_id"] = source_id
    if target_id:
        issue["target_id"] = target_id
    return issue


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str, str]] = set()
    result: list[dict[str, Any]] = []
    for issue in issues:
        key = (
            str(issue.get("code", "")),
            str(issue.get("location", "")),
            str(issue.get("message", "")),
            str(issue.get("source_id", "")),
            str(issue.get("target_id", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _basemap_source_refs(basemap: dict[str, Any] | None) -> list[str]:
    if not basemap:
        return []
    refs = _string_list(basemap.get("source_refs", []))
    if refs:
        return refs
    if basemap.get("source_ref"):
        return [str(basemap["source_ref"])]
    return []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
