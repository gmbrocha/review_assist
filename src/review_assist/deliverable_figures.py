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
from .deliverable_figure_rendering import comparison_unit_style_records, panel_bounds, render_map, source_layer_style_record
from .deliverable_figure_specs import (
    MAX_PANEL_COUNT,
    MISSING_SOURCE_STATUSES,
    PANEL_ASPECT_THRESHOLD,
    PUBLIC_CULTURAL_SOURCE_IDS,
    RESTRICTED_CULTURAL_SOURCE_ID,
    TARGET_SPECS,
    UNIMPLEMENTED_SOURCE_STATUSES,
    USABLE_SOURCE_STATUSES,
    TargetFigureSpec,
)
from .deliverable_constraints import (
    COMPARISON_UNIT_CONSTRAINTS_PATH,
    ComparisonUnitConstraintError,
    analyze_comparison_unit_constraints,
    load_comparison_unit_constraints,
)
from .deliverable_matrix import REQUIRED_STUB_TEXT, DeliverableMatrixError, FigureTarget, load_deliverable_matrix
from .maps import FIGURES_DIR
from .project_area import PROJECT_AREA_PATH, ProjectAreaError, build_project_area, load_project_area
from .projects import ProjectManifestError, load_project_manifest
from .source_catalog import SourceCatalogError, load_source_catalog
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set


DELIVERABLE_FIGURES_PATH = Path("deliverable/figures.json")
DELIVERABLE_MAP_ELEMENT_BASELINE = ["legend", "north_arrow", "scale_bar"]


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
        )
        figures.append(figure)
        validation_issues.extend(_dict_list(figure.get("validation_issues", [])))
        if not figure.get("is_stub"):
            for layer in _target_source_layers(target, source_layers):
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
    for source in _dict_list(comparison_unit_constraints.get("sources", [])):
        source_id = str(source.get("source_id", ""))
        if not source_id or source_id == RESTRICTED_CULTURAL_SOURCE_ID:
            continue
        if str(source.get("status", "")) not in USABLE_SOURCE_STATUSES:
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
) -> dict[str, Any]:
    spec = TARGET_SPECS.get(target.target_id, TargetFigureSpec(_target_source_refs(source_context, target.source_categories)))
    target_source_ids = list(spec.source_ids) or _target_source_refs(source_context, target.source_categories)
    public_source_ids = [source_id for source_id in target_source_ids if source_id != RESTRICTED_CULTURAL_SOURCE_ID]
    validation_issues = _source_availability_issues(target, public_source_ids, source_context)
    uncertainty_flags: set[str] = {"draft_pre_review", "desktop_screening_only"}

    layer_records = _target_source_layers(target, source_layers)
    layer_records = [_filtered_layer(layer, spec.filter_tokens) for layer in layer_records]
    layer_records = [layer for layer in layer_records if layer["source_id"] != RESTRICTED_CULTURAL_SOURCE_ID]
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

    available_source_ids = {str(layer["source_id"]) for layer in layer_records}
    if not available_source_ids:
        return _stub_figure(
            target=target,
            matrix_version=matrix_version,
            public_source_ids=public_source_ids,
            comparison_unit_ids=_comparison_unit_ids(unit_gdf),
            comparison_unit_constraints=comparison_unit_constraints,
            source_status=source_status,
            uncertainty_flags=sorted(uncertainty_flags | {"source_unavailable"}),
            validation_issues=validation_issues,
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
            )

    basemap = load_basemap(project_area, analysis_crs) if spec.prefer_basemap else {"layer": None, "issues": [], "flags": [], "shown_layer": None}
    validation_issues.extend(_dict_list(basemap.get("issues", [])))
    uncertainty_flags.update(_string_list(basemap.get("flags", [])))

    image_path = figures_dir / f"{target.target_id}.png"
    source_note = _source_note(layer_records, basemap)
    method_note = _method_note(analysis_crs, include_basemap=bool(basemap.get("layer")))
    try:
        render_map(
            output_path=image_path,
            title=target.title,
            unit_gdf=unit_gdf,
            analysis_crs=analysis_crs,
            source_layers=layer_records,
            basemap=basemap,
            method_note=method_note,
            source_note=source_note,
            focus_bounds=analysis_bounds.total_bounds,
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
        )

    related_constraints = _related_constraint_ids(constraints, public_source_ids, spec.filter_tokens)
    source_refs = sorted(available_source_ids)
    if basemap.get("source_ref"):
        source_refs.append(str(basemap["source_ref"]))
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
        ),
        validation_issues=_dedupe_issues(validation_issues),
    )


def _target_source_layers(target: FigureTarget, source_layers: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    spec = TARGET_SPECS.get(target.target_id, TargetFigureSpec(()))
    layers: list[dict[str, Any]] = []
    for source_id in spec.source_ids:
        layers.extend(dict(layer) for layer in source_layers.get(source_id, []))
    return layers


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
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    details = source_context.get("details_by_id", {})
    for source_id in source_ids:
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
        "provenance": _provenance(
            target=target,
            matrix_version=matrix_version,
            comparison_unit_constraints=comparison_unit_constraints,
            source_status=source_status,
            method="matrix_stub_for_unavailable_figure_source",
            analysis_crs=str(comparison_unit_constraints.get("analysis_crs", "")),
            project_area=None,
            basemap=None,
        ),
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
    basemap = load_basemap(project_area, analysis_crs)
    records: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for index, bounds in enumerate(panels, start=1):
        panel_id = f"attachment-a-panel-{index:03d}"
        image_path = figures_dir / f"{panel_id}.png"
        try:
            render_map(
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
                ],
                "source_refs": sorted({str(layer.get("source_id")) for layer in source_layers if layer.get("source_id")}),
                "provenance": {
                    "matrix_version": matrix_version,
                    "attachment_target_id": "attachment-environmental-constraints-maps",
                    "method": "long_axis_panel_slice",
                    "analysis_crs": analysis_crs,
                    "panel_index": index,
                    "panel_count": panel_count,
                    "comparison_unit_constraints_path": comparison_unit_constraints.get("output_path"),
                    "source_status_path": source_status.get("output_path"),
                    "review_before_export": True,
                    "desktop_screening_only": True,
                },
                "uncertainty_flags": ["draft_pre_review", "desktop_screening_only"],
                "review_status": "draft",
                "validation_issues": [],
            }
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
) -> dict[str, Any]:
    provenance = {
        "matrix_version": matrix_version,
        "figure_target_id": target.target_id,
        "section_target_id": target.section_target_id,
        "method": method,
        "comparison_unit_constraints_path": comparison_unit_constraints.get("output_path"),
        "source_status_path": source_status.get("output_path"),
        "project_area_path": project_area.get("output_path") if project_area else None,
        "source_categories": list(target.source_categories),
        "analysis_crs": analysis_crs,
        "review_before_export": True,
        "desktop_screening_only": True,
    }
    if basemap:
        provenance["basemap"] = {
            "source_id": str(basemap.get("source_ref") or MARIS_NAIP_SOURCE_ID),
            "selected_paths": _string_list(basemap.get("selected_paths", [])),
            "renderable_paths": _string_list(basemap.get("renderable_paths", [])),
            "rendered_path": basemap.get("shown_layer", {}).get("path") if isinstance(basemap.get("shown_layer"), dict) else None,
        }
    return provenance


def _caption(target: FigureTarget) -> str:
    return str(target.title)


def _method_note(analysis_crs: str, *, include_basemap: bool) -> str:
    method = "Vector and selected renderable basemap sidecar" if include_basemap else "Vector-only"
    return f"{method} screening map. Analysis CRS: {analysis_crs}."


def _source_note(source_layers: list[dict[str, Any]], basemap: dict[str, Any] | None) -> str:
    labels = []
    for layer in source_layers:
        count = int(len(layer["gdf"]))
        labels.append(f"{layer.get('source_name') or layer.get('source_id')} ({count} features)")
    if basemap and basemap.get("shown_layer"):
        shown = basemap["shown_layer"]
        label = str(shown.get("label") or MARIS_NAIP_SOURCE_NAME)
        if shown.get("renderable"):
            labels.append(f"{label} rendered from sidecar")
        else:
            labels.append(f"{label} provenance only; no visual basemap sidecar")
    if not labels:
        return ""
    return "Sources: " + "; ".join(labels)


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
