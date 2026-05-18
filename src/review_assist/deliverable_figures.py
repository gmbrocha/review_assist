"""Matrix-backed deliverable figure generation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyproj import CRS, Transformer
from shapely.geometry import box

from .basemaps import MARIS_NAIP_SOURCE_ID, MARIS_NAIP_SOURCE_NAME
from .comparison_units import ComparisonUnitError, build_comparison_units, load_comparison_units
from .deliverable_constraints import (
    COMPARISON_UNIT_CONSTRAINTS_PATH,
    ComparisonUnitConstraintError,
    analyze_comparison_unit_constraints,
    load_comparison_unit_constraints,
)
from .deliverable_matrix import REQUIRED_STUB_TEXT, DeliverableMatrixError, FigureTarget, load_deliverable_matrix
from .maps import FIGURES_DIR, MAP_ELEMENT_BASELINE, PROJECT_COLORS, SOURCE_CATEGORY_COLORS
from .project_area import PROJECT_AREA_PATH, ProjectAreaError, build_project_area, load_project_area
from .projects import ProjectManifestError, load_project_manifest
from .source_catalog import SourceCatalogError, load_source_catalog
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set


DELIVERABLE_FIGURES_PATH = Path("deliverable/figures.json")
SUPPORTED_REVIEW_STATUSES = {
    "draft",
    "needs_review",
    "accepted",
    "edited",
    "rejected",
    "needs_verification",
    "unable_to_verify",
}
USABLE_SOURCE_STATUSES = {
    "analyzed",
    "analyzed_empty",
    "downloaded",
    "local_materialized",
    "provided_in_input",
    "registered_local",
}
UNIMPLEMENTED_SOURCE_STATUSES = {"unimplemented", "manual", "stubbed"}
MISSING_SOURCE_STATUSES = {
    "missing",
    "source_missing",
    "source_unreadable",
    "failed",
    "downloadable",
    "optional",
    "gated",
    "restricted",
    "unsupported_download",
    "needs_review",
    "selected_not_renderable",
}
RESTRICTED_CULTURAL_SOURCE_ID = "mdah_restricted_archaeology"
PUBLIC_CULTURAL_SOURCE_IDS = {"maris_public_cultural_context", "mdah_public_historic_resources"}
RENDERABLE_BASEMAP_SUFFIXES = {".tif", ".tiff", ".png"}
PANEL_ASPECT_THRESHOLD = 2.75
MAX_PANEL_COUNT = 6


class DeliverableFigureError(RuntimeError):
    """Raised when deliverable figure generation or loading cannot complete."""


@dataclass(frozen=True)
class TargetFigureSpec:
    source_ids: tuple[str, ...]
    filter_tokens: tuple[str, ...] = ()
    source_unimplemented_note: str = ""
    prefer_basemap: bool = False


TARGET_SPECS: dict[str, TargetFigureSpec] = {
    "figure-wetlands-waterbodies": TargetFigureSpec(
        ("usfws_nwi_wetlands", "usgs_nhd_hydrography"),
        prefer_basemap=True,
    ),
    "figure-fema-flood-zones": TargetFigureSpec(
        ("fema_nfhl_flood_hazard",),
        prefer_basemap=True,
    ),
    "figure-streams-impaired-waters": TargetFigureSpec(
        ("usgs_nhd_hydrography",),
        source_unimplemented_note="303(d) impaired-water layer rendering is not implemented for Sprint 2.3; hydrography is shown when available.",
    ),
    "figure-cultural-resources": TargetFigureSpec(
        ("maris_public_cultural_context", "mdah_public_historic_resources"),
    ),
    "figure-fire-ems-stations": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure"),
        ("fire", "ems", "emergency", "rescue"),
    ),
    "figure-government-offices": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure"),
        ("government", "courthouse", "city hall", "town hall", "municipal", "county", "office", "civic"),
    ),
    "figure-schools-childcare": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure", "census_tiger_acs"),
        ("school", "childcare", "child care", "daycare", "day care", "education", "college", "university"),
    ),
    "figure-health-care-facilities": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure"),
        ("hospital", "clinic", "health", "medical", "urgent care", "nursing"),
    ),
    "figure-places-of-worship": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure"),
        ("worship", "church", "synagogue", "mosque", "temple", "chapel"),
    ),
    "figure-public-water-supply-wells": TargetFigureSpec(
        ("mdeq_public_water_supply_wells",),
    ),
    "figure-energy-infrastructure": TargetFigureSpec(
        ("local_utility_infrastructure",),
        ("electric", "transmission", "substation", "pipeline", "power", "energy", "utility"),
    ),
    "figure-hazardous-waste-sites": TargetFigureSpec(
        ("epa_envirofacts_echo", "mdeq_environmental_context", "mississippi_oil_gas_wells"),
    ),
    "figure-census-tracts": TargetFigureSpec(
        ("census_tiger_acs",),
    ),
}


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
    _validate_deliverable_figures(result, str(output_path))
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
    _validate_deliverable_figures(data, str(path))
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

    basemap = _load_basemap(project_area, analysis_crs) if spec.prefer_basemap else {"layer": None, "issues": [], "flags": [], "shown_layer": None}
    validation_issues.extend(_dict_list(basemap.get("issues", [])))
    uncertainty_flags.update(_string_list(basemap.get("flags", [])))

    image_path = figures_dir / f"{target.target_id}.png"
    source_note = _source_note(layer_records, basemap)
    method_note = _method_note(analysis_crs, include_basemap=bool(basemap.get("layer")))
    try:
        _render_map(
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
        *[_source_shown_layer(layer) for layer in layer_records],
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
        "source_note": "Source data unavailable or unsupported for automated draft figure rendering.",
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
        "map_elements": MAP_ELEMENT_BASELINE,
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


def _load_basemap(project_area: dict[str, Any], analysis_crs: str) -> dict[str, Any]:
    selected_paths = _string_list(project_area.get("selected_basemap_paths", []))
    renderable_paths = [path for path in _string_list(project_area.get("renderable_basemap_paths", [])) if Path(path).suffix.lower() in RENDERABLE_BASEMAP_SUFFIXES]
    if not selected_paths and not renderable_paths:
        return {"layer": None, "issues": [], "flags": ["vector_only_no_basemap"], "shown_layer": None, "source_ref": None}
    if selected_paths and not renderable_paths:
        return {
            "layer": None,
            "issues": [
                _issue(
                    "warning",
                    "basemap_selected_not_renderable",
                    "Selected MARIS/NAIP imagery is MrSID provenance only; no renderable sidecar was selected for figure rendering.",
                    str(project_area.get("output_path") or ""),
                    source_id=MARIS_NAIP_SOURCE_ID,
                )
            ],
            "flags": ["source_selected_not_renderable", "renderable_sidecar_missing", "vector_only_no_basemap"],
            "shown_layer": {
                "layer_type": "basemap_provenance",
                "source_id": MARIS_NAIP_SOURCE_ID,
                "label": MARIS_NAIP_SOURCE_NAME,
                "selected_paths": selected_paths,
                "renderable": False,
            },
            "source_ref": MARIS_NAIP_SOURCE_ID,
            "selected_paths": selected_paths,
            "renderable_paths": renderable_paths,
        }
    for path_text in renderable_paths:
        path = Path(path_text)
        if not path.exists():
            continue
        layer, issue = _read_basemap_layer(path, project_area, analysis_crs)
        if layer is not None:
            return {
                "layer": layer,
                "issues": [],
                "flags": ["basemap_sidecar_rendered"],
                "shown_layer": {
                    "layer_type": "basemap",
                    "source_id": MARIS_NAIP_SOURCE_ID,
                    "label": MARIS_NAIP_SOURCE_NAME,
                    "path": str(path),
                    "selected_paths": selected_paths,
                    "renderable": True,
                },
                "source_ref": MARIS_NAIP_SOURCE_ID,
                "selected_paths": selected_paths,
                "renderable_paths": renderable_paths,
            }
        if issue is not None:
            return {
                "layer": None,
                "issues": [issue],
                "flags": ["basemap_render_failed", "vector_only_no_basemap"],
                "shown_layer": {
                    "layer_type": "basemap_provenance",
                    "source_id": MARIS_NAIP_SOURCE_ID,
                    "label": MARIS_NAIP_SOURCE_NAME,
                    "path": str(path),
                    "selected_paths": selected_paths,
                    "renderable": False,
                },
                "source_ref": MARIS_NAIP_SOURCE_ID,
                "selected_paths": selected_paths,
                "renderable_paths": renderable_paths,
            }
    return {
        "layer": None,
        "issues": [
            _issue(
                "warning",
                "basemap_render_failed",
                "Selected MARIS/NAIP renderable sidecar path is unavailable or unusable.",
                str(project_area.get("output_path") or ""),
                source_id=MARIS_NAIP_SOURCE_ID,
            )
        ],
        "flags": ["basemap_render_failed", "vector_only_no_basemap"],
        "shown_layer": None,
        "source_ref": MARIS_NAIP_SOURCE_ID,
        "selected_paths": selected_paths,
        "renderable_paths": renderable_paths,
    }


def _read_basemap_layer(path: Path, project_area: dict[str, Any], analysis_crs: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    suffix = path.suffix.lower()
    if suffix == ".png":
        bbox = _metadata_bbox_for_path(path, project_area)
        if bbox is None:
            return None, _issue(
                "warning",
                "basemap_render_failed",
                "PNG basemap sidecar lacks usable WGS84 metadata extent; falling back to vector-only rendering.",
                str(path),
                source_id=MARIS_NAIP_SOURCE_ID,
            )
        try:
            image = plt.imread(path)
            extent = _bbox_to_crs_extent(bbox, analysis_crs)
        except Exception as exc:  # pragma: no cover - image backends vary.
            return None, _issue(
                "warning",
                "basemap_render_failed",
                f"PNG basemap sidecar could not be read: {exc}",
                str(path),
                source_id=MARIS_NAIP_SOURCE_ID,
            )
        return {"image": image, "extent": extent, "path": str(path)}, None

    try:
        import rasterio
    except ImportError:
        return None, _issue(
            "warning",
            "basemap_render_failed",
            "GeoTIFF basemap sidecar was selected, but rasterio is not installed; falling back to vector-only rendering.",
            str(path),
            source_id=MARIS_NAIP_SOURCE_ID,
        )
    try:
        with rasterio.open(path) as dataset:
            indexes = [1, 2, 3] if dataset.count >= 3 else [1]
            data = dataset.read(indexes)
            if len(indexes) == 1:
                image: Any = data[0]
            else:
                image = data.transpose(1, 2, 0)
            if dataset.crs is None:
                bbox = _metadata_bbox_for_path(path, project_area)
                if bbox is None:
                    raise ValueError("GeoTIFF has no CRS and no metadata bbox is available.")
                extent = _bbox_to_crs_extent(bbox, analysis_crs)
            else:
                west, south, east, north = dataset.bounds
                transformer = Transformer.from_crs(dataset.crs, analysis_crs, always_xy=True)
                xs, ys = transformer.transform([west, east], [south, north])
                extent = (min(xs), max(xs), min(ys), max(ys))
    except Exception as exc:  # pragma: no cover - raster drivers vary.
        return None, _issue(
            "warning",
            "basemap_render_failed",
            f"GeoTIFF basemap sidecar could not be read: {exc}",
            str(path),
            source_id=MARIS_NAIP_SOURCE_ID,
        )
    return {"image": image, "extent": extent, "path": str(path)}, None


def _metadata_bbox_for_path(path: Path, project_area: dict[str, Any]) -> dict[str, float] | None:
    for candidate in _dict_list(project_area.get("aerial_basemap_candidates", [])):
        paths = set(_string_list(candidate.get("renderable_sidecar_paths", [])))
        paths.update(_string_list(candidate.get("sid_paths", [])))
        if str(path) not in paths:
            continue
        bbox = candidate.get("metadata_bbox_wgs84")
        if isinstance(bbox, dict) and {"west", "south", "east", "north"}.issubset(bbox):
            try:
                return {key: float(bbox[key]) for key in ("west", "south", "east", "north")}
            except (TypeError, ValueError):
                return None
    return None


def _bbox_to_crs_extent(bbox: dict[str, float], analysis_crs: str) -> tuple[float, float, float, float]:
    transformer = Transformer.from_crs("EPSG:4326", analysis_crs, always_xy=True)
    west, south = transformer.transform(float(bbox["west"]), float(bbox["south"]))
    east, north = transformer.transform(float(bbox["east"]), float(bbox["north"]))
    return min(west, east), max(west, east), min(south, north), max(south, north)


def _render_map(
    *,
    output_path: Path,
    title: str,
    unit_gdf: gpd.GeoDataFrame,
    analysis_crs: str,
    source_layers: list[dict[str, Any]],
    basemap: dict[str, Any] | None,
    method_note: str,
    source_note: str,
    focus_bounds: Any | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 4.25), dpi=180)
    try:
        handles: list[Any] = []
        plotted: list[gpd.GeoDataFrame] = []
        if basemap and isinstance(basemap.get("layer"), dict):
            layer = basemap["layer"]
            ax.imshow(layer["image"], extent=layer["extent"], alpha=0.78, zorder=0)

        handles.extend(_plot_gdf(ax, unit_gdf, color=PROJECT_COLORS[0], label="Comparison units", is_project=True))
        plotted.append(unit_gdf)
        for index, layer in enumerate(source_layers):
            gdf = layer["gdf"]
            color = SOURCE_CATEGORY_COLORS.get(str(layer.get("source_category", "")), _source_color(index))
            label = str(layer.get("source_name") or layer.get("source_id") or "Source layer")
            handles.extend(_plot_gdf(ax, gdf, color=color, label=label, is_project=False))
            if not gdf.empty:
                plotted.append(gdf)

        if focus_bounds is not None:
            _set_bounds(ax, focus_bounds)
        else:
            _set_extent(ax, plotted)
        ax.set_title(title, fontsize=10, pad=7)
        ax.set_axis_off()
        if handles:
            ax.legend(handles=_dedupe_handles(handles), loc="upper left", frameon=True, framealpha=0.94, fontsize=6.2, title="Mapped layers", title_fontsize=6.4)
        _add_north_arrow(ax)
        _add_scale_bar(ax, analysis_crs)
        if source_note:
            ax.text(
                0.01,
                0.01,
                source_note,
                transform=ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=5.8,
                color="#333333",
                bbox={"facecolor": "white", "edgecolor": "#D0D0D0", "alpha": 0.9, "pad": 2},
            )
        ax.text(
            0.99,
            0.01,
            "Draft / Pre-Review\n" + method_note,
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=5.8,
            color="#333333",
            bbox={"facecolor": "white", "edgecolor": "#BDBDBD", "alpha": 0.9, "pad": 2},
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    finally:
        plt.close(fig)


def _plot_gdf(ax: Any, gdf: gpd.GeoDataFrame, *, color: str, label: str, is_project: bool) -> list[Any]:
    if gdf.empty:
        return []
    handles: list[Any] = []
    polygon_gdf = gdf[gdf.geometry.geom_type.str.contains("Polygon", na=False)]
    line_gdf = gdf[gdf.geometry.geom_type.str.contains("LineString", na=False)]
    point_gdf = gdf[gdf.geometry.geom_type.str.contains("Point", na=False)]
    if not polygon_gdf.empty:
        if is_project:
            polygon_gdf.plot(ax=ax, facecolor="none", edgecolor=color, linewidth=1.5, zorder=5)
            handles.append(Patch(facecolor="none", edgecolor=color, label=label))
        else:
            polygon_gdf.plot(ax=ax, facecolor=color, edgecolor=color, linewidth=0.6, alpha=0.32, zorder=3)
            handles.append(Patch(facecolor=color, edgecolor=color, alpha=0.32, label=label))
    if not line_gdf.empty:
        width = 2.0 if is_project else 1.1
        line_gdf.plot(ax=ax, color=color, linewidth=width, alpha=0.94 if is_project else 0.7, zorder=6 if is_project else 4)
        handles.append(Line2D([0], [0], color=color, lw=width, label=label))
    if not point_gdf.empty:
        size = 34 if is_project else 20
        point_gdf.plot(ax=ax, color=color, markersize=size, alpha=0.94 if is_project else 0.72, zorder=7 if is_project else 5)
        handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markersize=5.5, label=label))
    return handles[:1]


def _set_extent(ax: Any, layers: list[gpd.GeoDataFrame]) -> None:
    non_empty = [layer for layer in layers if not layer.empty]
    if not non_empty:
        return
    bounds = [layer.total_bounds for layer in non_empty]
    west = min(float(bound[0]) for bound in bounds)
    south = min(float(bound[1]) for bound in bounds)
    east = max(float(bound[2]) for bound in bounds)
    north = max(float(bound[3]) for bound in bounds)
    _set_bounds(ax, (west, south, east, north))


def _set_bounds(ax: Any, bounds: Any) -> None:
    west, south, east, north = [float(value) for value in bounds]
    width = east - west
    height = north - south
    pad_x = width * 0.08 if width > 0 else 250
    pad_y = height * 0.08 if height > 0 else 250
    ax.set_xlim(west - pad_x, east + pad_x)
    ax.set_ylim(south - pad_y, north + pad_y)
    ax.set_aspect("equal", adjustable="box")


def _add_north_arrow(ax: Any) -> None:
    ax.annotate(
        "N",
        xy=(0.94, 0.90),
        xytext=(0.94, 0.79),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "color": "#2B2B2B", "lw": 1.0},
        bbox={"facecolor": "white", "edgecolor": "#BDBDBD", "alpha": 0.9, "pad": 1.5},
    )


def _add_scale_bar(ax: Any, analysis_crs: str) -> None:
    feet_per_unit = _feet_per_crs_unit(analysis_crs)
    if feet_per_unit is None:
        return
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    width = abs(x_max - x_min)
    height = abs(y_max - y_min)
    if width <= 0 or height <= 0:
        return
    target_feet = width * feet_per_unit * 0.18
    scale_feet = _nice_scale_feet(target_feet)
    scale_units = scale_feet / feet_per_unit
    x0 = x_min + width * 0.08
    y0 = y_min + height * 0.08
    ax.plot([x0, x0 + scale_units], [y0, y0], color="#2B2B2B", linewidth=2.0, solid_capstyle="butt")
    label = f"{scale_feet / 5280:g} mi" if scale_feet >= 5280 else f"{int(scale_feet):,} ft"
    ax.text(
        x0 + scale_units / 2,
        y0 + height * 0.018,
        label,
        ha="center",
        va="bottom",
        fontsize=5.8,
        color="#2B2B2B",
        bbox={"facecolor": "white", "edgecolor": "#D0D0D0", "alpha": 0.9, "pad": 1.5},
    )


def _feet_per_crs_unit(analysis_crs: str) -> float | None:
    try:
        crs = CRS.from_user_input(analysis_crs)
    except Exception:
        return None
    if not crs.axis_info:
        return None
    unit_name = str(crs.axis_info[0].unit_name or "").lower()
    if "metre" in unit_name or "meter" in unit_name:
        return 3.280839895
    if "foot" in unit_name or "feet" in unit_name:
        return 1.0
    return None


def _nice_scale_feet(target_feet: float) -> float:
    candidates = [100, 250, 500, 1000, 2000, 5280, 10000, 26400, 52800, 105600]
    valid = [candidate for candidate in candidates if candidate <= target_feet]
    return float(valid[-1] if valid else candidates[0])


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
    panels = _panel_bounds((west, south, east, north), panel_count)
    basemap = _load_basemap(project_area, analysis_crs)
    records: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for index, bounds in enumerate(panels, start=1):
        panel_id = f"attachment-a-panel-{index:03d}"
        image_path = figures_dir / f"{panel_id}.png"
        try:
            _render_map(
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
                "caption": f"Supporting panel map {index} for elongated project extent. Draft/pre-review context only.",
                "source_note": _source_note(source_layers, basemap),
                "method_note": _method_note(analysis_crs, include_basemap=bool(basemap.get("layer"))),
                "map_elements": MAP_ELEMENT_BASELINE,
                "figure_group": "attachment_supporting_figures",
                "shown_layers": [
                    _comparison_units_shown_layer(unit_gdf),
                    *[_source_shown_layer(layer) for layer in source_layers],
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


def _panel_bounds(bounds: tuple[float, float, float, float], panel_count: int) -> list[tuple[float, float, float, float]]:
    west, south, east, north = bounds
    width = east - west
    height = north - south
    panels: list[tuple[float, float, float, float]] = []
    if width >= height:
        step = width / panel_count
        for index in range(panel_count):
            left = west + step * index
            right = east if index == panel_count - 1 else west + step * (index + 1)
            panels.append((left, south, right, north))
    else:
        step = height / panel_count
        for index in range(panel_count):
            bottom = south + step * index
            top = north if index == panel_count - 1 else south + step * (index + 1)
            panels.append((west, bottom, east, top))
    return panels


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
            "source_id": MARIS_NAIP_SOURCE_ID,
            "selected_paths": _string_list(basemap.get("selected_paths", [])),
            "renderable_paths": _string_list(basemap.get("renderable_paths", [])),
            "rendered_path": basemap.get("shown_layer", {}).get("path") if isinstance(basemap.get("shown_layer"), dict) else None,
        }
    return provenance


def _caption(target: FigureTarget) -> str:
    return f"{target.title}. Draft desktop-screening figure for reviewer verification before export."


def _method_note(analysis_crs: str, *, include_basemap: bool) -> str:
    method = "Vector and selected renderable basemap sidecar" if include_basemap else "Vector-only"
    return f"{method} desktop screening map. Analysis CRS: {analysis_crs}."


def _source_note(source_layers: list[dict[str, Any]], basemap: dict[str, Any] | None) -> str:
    labels = []
    for layer in source_layers:
        count = int(len(layer["gdf"]))
        labels.append(f"{layer.get('source_name') or layer.get('source_id')} ({count} features)")
    if basemap and basemap.get("shown_layer"):
        shown = basemap["shown_layer"]
        label = MARIS_NAIP_SOURCE_NAME
        if shown.get("renderable"):
            labels.append(f"{label} renderable sidecar")
        else:
            labels.append(f"{label} provenance only")
    if not labels:
        return ""
    text = "Sources: " + "; ".join(labels)
    return text if len(text) <= 190 else text[:187].rstrip() + "..."


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
    }


def _source_shown_layer(layer: dict[str, Any]) -> dict[str, Any]:
    gdf = layer["gdf"]
    return {
        "layer_type": "source_layer",
        "source_id": layer.get("source_id"),
        "label": layer.get("source_name") or layer.get("source_id"),
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


def _dedupe_handles(handles: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for handle in handles:
        label = str(handle.get_label())
        if label in seen:
            continue
        seen.add(label)
        result.append(handle)
    return result


def _source_color(index: int) -> str:
    colors = ["#6BAA75", "#E45E5E", "#7A6FF0", "#D99A2B", "#3A8D8F", "#A35C9F"]
    return colors[index % len(colors)]


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


def _validate_deliverable_figures(data: dict[str, Any], location: str) -> None:
    figures = data.get("figures")
    if not isinstance(figures, list):
        raise DeliverableFigureError(f"Deliverable figures artifact requires a list field named 'figures': {location}")
    if data.get("figure_count") != len(figures):
        raise DeliverableFigureError(f"Deliverable figures artifact figure_count does not match figures: {location}")
    if len(figures) != 13:
        raise DeliverableFigureError(f"Deliverable figures artifact must contain exactly 13 main figures: {location}")
    if not isinstance(data.get("attachment_supporting_figures", []), list):
        raise DeliverableFigureError(f"Deliverable figures artifact attachment_supporting_figures must be a list: {location}")
    if data.get("attachment_supporting_figure_count", 0) != len(data.get("attachment_supporting_figures", [])):
        raise DeliverableFigureError(f"Attachment supporting figure count does not match records: {location}")
    if not isinstance(data.get("validation_issues", []), list):
        raise DeliverableFigureError(f"Deliverable figures artifact validation_issues must be a list: {location}")

    seen_ids: set[str] = set()
    required = {
        "figure_id",
        "type",
        "figure_type",
        "figure_number",
        "title",
        "section_target_id",
        "image_path",
        "file_format",
        "caption",
        "source_note",
        "method_note",
        "map_elements",
        "figure_group",
        "related_resource_categories",
        "shown_layers",
        "source_refs",
        "layer_refs",
        "related_constraint_ids",
        "comparison_unit_ids",
        "provenance",
        "uncertainty_flags",
        "is_stub",
        "stub_text",
        "review_status",
        "validation_issues",
    }
    for figure in figures:
        if not isinstance(figure, dict):
            raise DeliverableFigureError(f"Each deliverable figure must be an object: {location}")
        missing = sorted(required - set(figure))
        if missing:
            raise DeliverableFigureError(f"Deliverable figure is missing required fields {missing}: {location}")
        figure_id = figure["figure_id"]
        if not isinstance(figure_id, str) or not figure_id.strip():
            raise DeliverableFigureError(f"Deliverable figure requires a non-empty figure_id: {location}")
        if figure_id in seen_ids:
            raise DeliverableFigureError(f"Duplicate deliverable figure id '{figure_id}': {location}")
        seen_ids.add(figure_id)
        if figure["file_format"] != "png":
            raise DeliverableFigureError(f"Deliverable figure '{figure_id}' file_format must be png: {location}")
        if figure["review_status"] not in SUPPORTED_REVIEW_STATUSES:
            raise DeliverableFigureError(f"Deliverable figure '{figure_id}' has unsupported review_status: {location}")
        if not isinstance(figure["is_stub"], bool):
            raise DeliverableFigureError(f"Deliverable figure '{figure_id}' is_stub must be boolean: {location}")
        if figure["is_stub"]:
            if figure.get("stub_text") != REQUIRED_STUB_TEXT:
                raise DeliverableFigureError(f"Deliverable figure '{figure_id}' stub_text does not match required stub text: {location}")
        else:
            image_path = str(figure.get("image_path", ""))
            if not image_path:
                raise DeliverableFigureError(f"Deliverable figure '{figure_id}' requires image_path when not a stub: {location}")
            if not Path(image_path).exists():
                raise DeliverableFigureError(f"Deliverable figure '{figure_id}' image_path does not exist: {image_path}")
        if not isinstance(figure["provenance"], dict):
            raise DeliverableFigureError(f"Deliverable figure '{figure_id}' provenance must be an object: {location}")
        for list_field in (
            "map_elements",
            "related_resource_categories",
            "shown_layers",
            "source_refs",
            "layer_refs",
            "related_constraint_ids",
            "comparison_unit_ids",
            "uncertainty_flags",
            "validation_issues",
        ):
            if not isinstance(figure[list_field], list):
                raise DeliverableFigureError(f"Deliverable figure '{figure_id}' field '{list_field}' must be a list: {location}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
