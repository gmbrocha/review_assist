"""Matrix-backed deliverable table generation."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .comparison_units import ComparisonUnitError, build_comparison_units, load_comparison_units
from .deliverable_constraints import (
    COMPARISON_UNIT_CONSTRAINTS_PATH,
    ComparisonUnitConstraintError,
    analyze_comparison_unit_constraints,
    load_comparison_unit_constraints,
)
from .deliverable_matrix import (
    REQUIRED_STUB_TEXT,
    DeliverableMatrixError,
    TableTarget,
    load_deliverable_matrix,
)
from .extent_policy import apply_extent_metadata, extent_policy_summary, target_extent_metadata
from .projects import ProjectManifestError, load_project_manifest
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set


DELIVERABLE_TABLES_PATH = Path("deliverable/tables.json")
SUPPORTED_REVIEW_STATUSES = {"draft", "needs_review", "accepted", "edited", "rejected", "needs_verification", "unable_to_verify"}
USABLE_SOURCE_STATUSES = {"analyzed", "analyzed_empty", "downloaded", "local_materialized", "provided_in_input", "registered_local"}
UNAVAILABLE_SOURCE_STATUSES = {
    "source_missing",
    "source_unreadable",
    "missing",
    "failed",
    "gated",
    "restricted",
    "manual",
    "stubbed",
    "unimplemented",
    "downloadable",
    "unsupported_download",
}


class DeliverableTableError(RuntimeError):
    """Raised when deliverable table generation or loading cannot complete."""


def generate_deliverable_tables(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        matrix = load_deliverable_matrix()
        comparison_units = _load_or_build_comparison_units(project_dir)
        comparison_unit_constraints = _load_or_generate_comparison_unit_constraints(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
    except (
        ProjectManifestError,
        DeliverableMatrixError,
        ComparisonUnitError,
        ComparisonUnitConstraintError,
        SourceStatusError,
    ) as exc:
        raise DeliverableTableError(str(exc)) from exc

    unit_records = _comparison_unit_records(comparison_units)
    source_context = _source_context(source_status, comparison_unit_constraints)
    constraints = [item for item in comparison_unit_constraints.get("constraints", []) if isinstance(item, dict)]

    output_path = project_dir / DELIVERABLE_TABLES_PATH
    tables = [
        _table_for_target(
            target=target,
            matrix_version=matrix.matrix_version,
            unit_records=unit_records,
            constraints=constraints,
            source_context=source_context,
            comparison_unit_constraints=comparison_unit_constraints,
            source_status=source_status,
        )
        for target in matrix.table_targets
    ]
    validation_issues = [
        issue
        for issue in comparison_unit_constraints.get("validation_issues", [])
        if isinstance(issue, dict)
    ]
    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "matrix_version": matrix.matrix_version,
        "extent_policy": extent_policy_summary(),
        "table_count": len(tables),
        "tables": tables,
        "validation_issues": validation_issues,
        "upstream_artifacts": {
            "deliverable_matrix_path": "config/deliverable_section_matrix.json",
            "comparison_units_metadata_path": comparison_units.get("output_path"),
            "comparison_units_path": comparison_units.get("comparison_units_path"),
            "comparison_unit_constraints_path": comparison_unit_constraints.get("output_path"),
            "source_status_path": source_status.get("output_path"),
        },
        "output_path": str(output_path),
    }
    _validate_deliverable_tables(result, str(output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_deliverable_tables(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / DELIVERABLE_TABLES_PATH
    if not path.exists():
        raise DeliverableTableError(f"Missing deliverable tables artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeliverableTableError(f"Invalid deliverable tables JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DeliverableTableError(f"Deliverable tables artifact must be a JSON object: {path}")
    _validate_deliverable_tables(data, str(path))
    return data


def _load_or_build_comparison_units(project_dir: Path) -> dict[str, Any]:
    try:
        return load_comparison_units(project_dir)
    except ComparisonUnitError:
        return build_comparison_units(project_dir)


def _load_or_generate_comparison_unit_constraints(project_dir: Path) -> dict[str, Any]:
    path = project_dir / COMPARISON_UNIT_CONSTRAINTS_PATH
    if path.exists():
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


def _comparison_unit_records(comparison_units: dict[str, Any]) -> list[dict[str, Any]]:
    path = Path(str(comparison_units.get("comparison_units_path", "")))
    if not path.exists():
        raise DeliverableTableError(f"Missing comparison units GeoJSON artifact: {path}")
    import geopandas as gpd

    gdf = gpd.read_file(path)
    records: list[dict[str, Any]] = []
    for index, row in gdf.iterrows():
        records.append(
            {
                "comparison_unit_id": _row_string(row, "comparison_unit_id", str(index)),
                "comparison_unit_name": _row_string(row, "comparison_unit_name", str(index)),
                "comparison_unit_group": _row_string(row, "comparison_unit_group", ""),
                "comparison_unit_type": _row_string(row, "comparison_unit_type", ""),
                "geometry_role": _row_string(row, "geometry_role", ""),
            }
        )
    return records


def _source_context(source_status: dict[str, Any], comparison_unit_constraints: dict[str, Any]) -> dict[str, Any]:
    by_category: dict[str, dict[str, Any]] = {}
    source_ids_by_category: dict[str, set[str]] = defaultdict(set)
    usable_source_ids_by_category: dict[str, set[str]] = defaultdict(set)
    flags_by_category: dict[str, set[str]] = defaultdict(set)
    source_detail_status: dict[str, str] = {}
    for record in source_status.get("statuses", []):
        if not isinstance(record, dict):
            continue
        category = str(record.get("category", ""))
        if not category:
            continue
        by_category[category] = record
        source_ids_by_category[category].update(_string_list(record.get("source_ids", [])))
        flags_by_category[category].update(_string_list(record.get("report_caveat_flags", record.get("uncertainty_flags", []))))
        for detail in record.get("source_details", []):
            if not isinstance(detail, dict):
                continue
            source_id = str(detail.get("source_id", ""))
            status = str(detail.get("status", ""))
            if source_id:
                source_detail_status[source_id] = status
            source_ids_by_category[category].add(source_id)
            flags_by_category[category].update(_string_list(detail.get("report_caveat_flags", detail.get("uncertainty_flags", []))))
            if status in USABLE_SOURCE_STATUSES:
                usable_source_ids_by_category[category].add(source_id)

    analyzed_source_status: dict[str, str] = {}
    for source in comparison_unit_constraints.get("sources", []):
        if not isinstance(source, dict):
            continue
        category = str(source.get("source_category", ""))
        source_id = str(source.get("source_id", ""))
        status = str(source.get("status", ""))
        if not category or not source_id:
            continue
        analyzed_source_status[source_id] = status
        source_ids_by_category[category].add(source_id)
        if status in USABLE_SOURCE_STATUSES:
            usable_source_ids_by_category[category].add(source_id)

    return {
        "by_category": by_category,
        "source_ids_by_category": {key: sorted(value) for key, value in source_ids_by_category.items()},
        "usable_source_ids_by_category": {key: sorted(value) for key, value in usable_source_ids_by_category.items()},
        "flags_by_category": {key: sorted(value) for key, value in flags_by_category.items()},
        "source_detail_status": source_detail_status,
        "analyzed_source_status": analyzed_source_status,
    }


def _table_for_target(
    *,
    target: TableTarget,
    matrix_version: str,
    unit_records: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    source_context: dict[str, Any],
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
) -> dict[str, Any]:
    if target.target_id == "table-wetlands-waterbodies":
        return _wetlands_waterbodies_table(target, matrix_version, unit_records, constraints, source_context, comparison_unit_constraints, source_status)
    if target.target_id == "table-fema-flood-zones":
        return _flood_zones_table(target, matrix_version, unit_records, constraints, source_context, comparison_unit_constraints, source_status)
    if target.target_id == "table-income-demographics":
        return _income_demographics_table(target, matrix_version, unit_records, constraints, source_context, comparison_unit_constraints, source_status)
    if target.target_id == "table-demographic-composition":
        return _demographic_composition_table(target, matrix_version, unit_records, constraints, source_context, comparison_unit_constraints, source_status)
    return _stub_table(
        target=target,
        matrix_version=matrix_version,
        source_context=source_context,
        comparison_unit_constraints=comparison_unit_constraints,
        source_status=source_status,
        uncertainty_flags=["source_unimplemented"],
    )


def _wetlands_waterbodies_table(
    target: TableTarget,
    matrix_version: str,
    unit_records: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    source_context: dict[str, Any],
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
) -> dict[str, Any]:
    nwi_available = _category_available(source_context, "wetlands_waterbodies")
    hydro_available = _category_available(source_context, "hydrography_crossings")
    if not nwi_available and not hydro_available:
        return _stub_table(
            target=target,
            matrix_version=matrix_version,
            source_context=source_context,
            comparison_unit_constraints=comparison_unit_constraints,
            source_status=source_status,
            uncertainty_flags=_category_flags(source_context, target.source_categories),
        )

    counts: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    crossing_counts: dict[str, set[str]] = defaultdict(set)
    related_constraints: set[str] = set()
    source_refs: set[str] = set()
    for constraint in constraints:
        category = str(constraint.get("source_category", ""))
        unit_id = str(constraint.get("comparison_unit_id", ""))
        if category == "wetlands_waterbodies":
            source_refs.add(str(constraint.get("source_id", "")))
            wetland_class = normalize_nwi_class(constraint)
            if wetland_class in {
                "Freshwater Emergent Wetland",
                "Freshwater Forested/Shrub Wetland",
                "Freshwater Pond",
            }:
                counts[unit_id][wetland_class].add(_dedupe_key(constraint))
                related_constraints.add(str(constraint.get("constraint_id", "")))
        elif category == "hydrography_crossings" and is_hydrography_crossing(constraint):
            source_refs.add(str(constraint.get("source_id", "")))
            crossing_counts[unit_id].add(_dedupe_key(constraint))
            related_constraints.add(str(constraint.get("constraint_id", "")))

    rows = [
        {
            "Alternative": unit["comparison_unit_name"],
            "Stream Crossings": len(crossing_counts.get(unit["comparison_unit_id"], set())),
            "Freshwater Emergent Wetland": len(counts.get(unit["comparison_unit_id"], {}).get("Freshwater Emergent Wetland", set())),
            "Freshwater Forested/Shrub Wetland": len(
                counts.get(unit["comparison_unit_id"], {}).get("Freshwater Forested/Shrub Wetland", set())
            ),
            "Freshwater Pond": len(counts.get(unit["comparison_unit_id"], {}).get("Freshwater Pond", set())),
        }
        for unit in unit_records
    ]
    uncertainty_flags = _category_flags(source_context, target.source_categories)
    if not nwi_available:
        uncertainty_flags.append("wetlands_source_unavailable")
    if not hydro_available:
        uncertainty_flags.append("hydrography_source_unavailable")
    return _deliverable_table(
        target=target,
        matrix_version=matrix_version,
        rows=rows,
        source_refs=sorted(item for item in source_refs if item),
        related_constraint_ids=sorted(item for item in related_constraints if item),
        comparison_unit_ids=[unit["comparison_unit_id"] for unit in unit_records],
        uncertainty_flags=sorted(set(uncertainty_flags)),
        provenance=_provenance(target, matrix_version, comparison_unit_constraints, source_status, method="deduplicated_wetland_and_hydrography_counts"),
    )


def _flood_zones_table(
    target: TableTarget,
    matrix_version: str,
    unit_records: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    source_context: dict[str, Any],
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
) -> dict[str, Any]:
    if not _category_available(source_context, "flood_hazard"):
        return _stub_table(
            target=target,
            matrix_version=matrix_version,
            source_context=source_context,
            comparison_unit_constraints=comparison_unit_constraints,
            source_status=source_status,
            uncertainty_flags=_category_flags(source_context, target.source_categories),
        )

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    source_refs: set[str] = set()
    for constraint in constraints:
        if constraint.get("source_category") != "flood_hazard":
            continue
        unit_id = str(constraint.get("comparison_unit_id", ""))
        classification = normalize_flood_zone_classification(constraint)
        row = grouped.setdefault(
            (unit_id, classification),
            {
                "comparison_unit_id": unit_id,
                "Flood Zone Classification": classification,
                "Estimated Acreage": 0.0,
                "related_constraint_ids": set(),
            },
        )
        measurements = constraint.get("measurements", {})
        if isinstance(measurements, dict):
            row["Estimated Acreage"] += _float_value(measurements.get("intersection_area_acres"))
        row["related_constraint_ids"].add(str(constraint.get("constraint_id", "")))
        source_refs.add(str(constraint.get("source_id", "")))

    rows: list[dict[str, Any]] = []
    related_constraint_ids: set[str] = set()
    for unit in unit_records:
        unit_rows = [row for (unit_id, _classification), row in grouped.items() if unit_id == unit["comparison_unit_id"]]
        if not unit_rows:
            rows.append(
                {
                    "Alternative": unit["comparison_unit_name"],
                    "Flood Zone Classification": "No mapped FEMA flood hazard intersection",
                    "Estimated Acreage": 0.0,
                }
            )
            continue
        for row in sorted(unit_rows, key=lambda item: str(item["Flood Zone Classification"])):
            related_constraint_ids.update(row["related_constraint_ids"])
            rows.append(
                {
                    "Alternative": unit["comparison_unit_name"],
                    "Flood Zone Classification": row["Flood Zone Classification"],
                    "Estimated Acreage": round(row["Estimated Acreage"], 2),
                }
            )
    return _deliverable_table(
        target=target,
        matrix_version=matrix_version,
        rows=rows,
        source_refs=sorted(item for item in source_refs if item),
        related_constraint_ids=sorted(item for item in related_constraint_ids if item),
        comparison_unit_ids=[unit["comparison_unit_id"] for unit in unit_records],
        uncertainty_flags=sorted(set(_category_flags(source_context, target.source_categories))),
        provenance=_provenance(target, matrix_version, comparison_unit_constraints, source_status, method="buffered_corridor_flood_zone_acreage"),
    )


def _income_demographics_table(
    target: TableTarget,
    matrix_version: str,
    unit_records: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    source_context: dict[str, Any],
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
) -> dict[str, Any]:
    census_constraints = _census_constraints(constraints)
    if not census_constraints:
        return _census_stub_table(target, matrix_version, source_context, comparison_unit_constraints, source_status)

    rows_by_geo: dict[str, dict[str, Any]] = {}
    source_refs: set[str] = set()
    related_constraint_ids: set[str] = set()
    comparison_unit_ids: set[str] = set()
    for constraint in census_constraints:
        values = _values(constraint)
        geography = _census_geography(constraint)
        value = _first_present(values, "population_below_poverty_line", "poverty_population")
        if not geography or value == "":
            continue
        rows_by_geo.setdefault(
            geography,
            {
                "Census Tract": geography,
                "Population Below the Poverty Line": value,
            },
        )
        source_refs.add(str(constraint.get("source_id", "")))
        related_constraint_ids.add(str(constraint.get("constraint_id", "")))
        comparison_unit_ids.add(str(constraint.get("comparison_unit_id", "")))
    if not rows_by_geo:
        return _census_stub_table(target, matrix_version, source_context, comparison_unit_constraints, source_status)
    return _deliverable_table(
        target=target,
        matrix_version=matrix_version,
        rows=[rows_by_geo[key] for key in sorted(rows_by_geo)],
        source_refs=sorted(item for item in source_refs if item),
        related_constraint_ids=sorted(item for item in related_constraint_ids if item),
        comparison_unit_ids=sorted(item for item in comparison_unit_ids if item) or [unit["comparison_unit_id"] for unit in unit_records],
        uncertainty_flags=sorted(set(_census_uncertainty_flags(source_context))),
        provenance=_provenance(target, matrix_version, comparison_unit_constraints, source_status, method="intersecting_census_acs_demographic_values"),
    )


def _demographic_composition_table(
    target: TableTarget,
    matrix_version: str,
    unit_records: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    source_context: dict[str, Any],
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
) -> dict[str, Any]:
    census_constraints = _census_constraints(constraints)
    if not census_constraints:
        return _census_stub_table(target, matrix_version, source_context, comparison_unit_constraints, source_status)

    rows_by_geo: dict[str, dict[str, Any]] = {}
    source_refs: set[str] = set()
    related_constraint_ids: set[str] = set()
    comparison_unit_ids: set[str] = set()
    for constraint in census_constraints:
        values = _values(constraint)
        geography = _census_geography(constraint)
        if not geography:
            continue
        row = {
            "Geography": geography,
            "Black or African American": _first_present(values, "black_or_african_american"),
            "Asian": _first_present(values, "asian"),
            "White": _first_present(values, "white"),
        }
        if not any(row[column] != "" for column in ("Black or African American", "Asian", "White")):
            continue
        rows_by_geo.setdefault(geography, row)
        source_refs.add(str(constraint.get("source_id", "")))
        related_constraint_ids.add(str(constraint.get("constraint_id", "")))
        comparison_unit_ids.add(str(constraint.get("comparison_unit_id", "")))
    if not rows_by_geo:
        return _census_stub_table(target, matrix_version, source_context, comparison_unit_constraints, source_status)
    return _deliverable_table(
        target=target,
        matrix_version=matrix_version,
        rows=[rows_by_geo[key] for key in sorted(rows_by_geo)],
        source_refs=sorted(item for item in source_refs if item),
        related_constraint_ids=sorted(item for item in related_constraint_ids if item),
        comparison_unit_ids=sorted(item for item in comparison_unit_ids if item) or [unit["comparison_unit_id"] for unit in unit_records],
        uncertainty_flags=sorted(set(_census_uncertainty_flags(source_context))),
        provenance=_provenance(target, matrix_version, comparison_unit_constraints, source_status, method="intersecting_census_acs_demographic_values"),
    )


def _census_stub_table(
    target: TableTarget,
    matrix_version: str,
    source_context: dict[str, Any],
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
) -> dict[str, Any]:
    flags = _census_uncertainty_flags(source_context)
    if not os.environ.get("CENSUS_API_KEY"):
        flags.append("missing_census_api_key")
    return _stub_table(
        target=target,
        matrix_version=matrix_version,
        source_context=source_context,
        comparison_unit_constraints=comparison_unit_constraints,
        source_status=source_status,
        uncertainty_flags=sorted(set(flags)),
    )


def normalize_nwi_class(constraint: dict[str, Any]) -> str:
    values = _values(constraint)
    candidates = [
        constraint.get("source_feature_type"),
        constraint.get("source_feature_subtype"),
        values.get("nwi_attribute"),
        values.get("nwi_wetland_type"),
        values.get("nwi_system"),
        values.get("nwi_class_name"),
    ]
    text = " ".join(str(candidate) for candidate in candidates if candidate).lower()
    if "pond" in text or "pub" in text:
        return "Freshwater Pond"
    if "forested" in text or "shrub" in text or "pfo" in text or "pss" in text:
        return "Freshwater Forested/Shrub Wetland"
    if "emergent" in text or "pem" in text:
        return "Freshwater Emergent Wetland"
    return "Other/Unmapped"


def is_hydrography_crossing(constraint: dict[str, Any]) -> bool:
    if constraint.get("source_category") != "hydrography_crossings":
        return False
    source_geometry_type = str(constraint.get("source_geometry_type", "")).lower()
    relationship = str(constraint.get("relationship_type", ""))
    if "polygon" in source_geometry_type:
        return False
    source_text = " ".join(
        str(constraint.get(key, ""))
        for key in ("source_feature_type", "source_feature_subtype", "source_layer", "source_feature_label")
    ).lower()
    if any(token in source_text for token in ("waterbody", "lake", "reservoir", "area", "pond")):
        return False
    if relationship == "crosses":
        return True
    return relationship == "intersects" and "line" in source_geometry_type


def normalize_flood_zone_classification(constraint: dict[str, Any]) -> str:
    values = _values(constraint)
    zone = _first_present(values, "flood_zone") or str(constraint.get("source_feature_type", "")).strip()
    subtype = _first_present(values, "flood_zone_subtype") or str(constraint.get("source_feature_subtype", "")).strip()
    if not zone:
        return "Unclassified Flood Hazard"
    if subtype:
        return f"{zone} - {subtype}"
    return zone


def _deliverable_table(
    *,
    target: TableTarget,
    matrix_version: str,
    rows: list[dict[str, Any]],
    source_refs: list[str],
    related_constraint_ids: list[str],
    comparison_unit_ids: list[str],
    uncertainty_flags: list[str],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    extent = _table_extent(target, provenance)
    return {
        "table_id": target.target_id,
        "table_number": target.table_number,
        "title": target.title,
        "section_target_id": target.section_target_id,
        "columns": list(target.columns),
        "rows": rows,
        "row_count": len(rows),
        "source_refs": source_refs,
        "related_constraint_ids": related_constraint_ids,
        "comparison_unit_ids": comparison_unit_ids,
        **extent,
        "provenance": provenance,
        "uncertainty_flags": uncertainty_flags,
        "is_stub": False,
        "stub_text": "",
        "review_status": "draft",
    }


def _stub_table(
    *,
    target: TableTarget,
    matrix_version: str,
    source_context: dict[str, Any],
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
    uncertainty_flags: list[str],
) -> dict[str, Any]:
    flags = sorted(set(uncertainty_flags or _category_flags(source_context, target.source_categories) or ["source_unavailable"]))
    provenance = _provenance(target, matrix_version, comparison_unit_constraints, source_status, method="matrix_stub_for_unavailable_source")
    extent = _table_extent(target, provenance)
    return {
        "table_id": target.target_id,
        "table_number": target.table_number,
        "title": target.title,
        "section_target_id": target.section_target_id,
        "columns": list(target.columns),
        "rows": [],
        "row_count": 0,
        "source_refs": _target_source_refs(source_context, target.source_categories),
        "related_constraint_ids": [],
        "comparison_unit_ids": [],
        **extent,
        "provenance": provenance,
        "uncertainty_flags": flags,
        "is_stub": True,
        "stub_text": REQUIRED_STUB_TEXT,
        "review_status": "needs_review",
    }


def _provenance(
    target: TableTarget,
    matrix_version: str,
    comparison_unit_constraints: dict[str, Any],
    source_status: dict[str, Any],
    *,
    method: str,
) -> dict[str, Any]:
    extent = target_extent_metadata(
        target_id=target.target_id,
        target_type="table",
        source_categories=target.source_categories,
        query_distance=comparison_unit_constraints.get("default_buffer_feet"),
        query_units="feet",
    )
    return {
        "matrix_version": matrix_version,
        "table_target_id": target.target_id,
        "section_target_id": target.section_target_id,
        "method": method,
        "comparison_unit_constraints_path": comparison_unit_constraints.get("output_path"),
        "source_status_path": source_status.get("output_path"),
        "source_categories": list(target.source_categories),
        "extent_policy": extent,
        "review_before_export": True,
        "desktop_screening_only": True,
    }


def _table_extent(target: TableTarget, provenance: dict[str, Any]) -> dict[str, Any]:
    extent = provenance.get("extent_policy")
    if not isinstance(extent, dict):
        extent = target_extent_metadata(target_id=target.target_id, target_type="table", source_categories=target.source_categories)
    return apply_extent_metadata({}, extent)


def _category_available(source_context: dict[str, Any], category: str) -> bool:
    usable = source_context.get("usable_source_ids_by_category", {})
    if isinstance(usable, dict) and usable.get(category):
        return True
    status_record = source_context.get("by_category", {}).get(category) if isinstance(source_context.get("by_category"), dict) else None
    if not isinstance(status_record, dict):
        return False
    return str(status_record.get("status", "")) in {"downloaded", "provided_locally", "local_materialized"}


def _category_flags(source_context: dict[str, Any], categories: list[str]) -> list[str]:
    flags: set[str] = set()
    by_category = source_context.get("by_category", {})
    context_flags = source_context.get("flags_by_category", {})
    for category in categories:
        if isinstance(context_flags, dict):
            flags.update(_string_list(context_flags.get(category, [])))
        if isinstance(by_category, dict):
            record = by_category.get(category)
            if isinstance(record, dict) and not _category_available(source_context, category):
                status = str(record.get("status", ""))
                if status in {"failed"}:
                    flags.add("source_download_failed")
                elif status in {"stubbed", "manual"}:
                    flags.add("manual_review_required")
                    flags.add("source_unavailable")
                elif status in {"gated", "restricted"}:
                    flags.add("restricted_source_required")
                    flags.add("manual_review_required")
                elif status in {"downloadable", "missing"}:
                    flags.add("source_unavailable")
    return sorted(flags)


def _census_uncertainty_flags(source_context: dict[str, Any]) -> list[str]:
    flags = set(_category_flags(source_context, ["community_socioeconomic"]))
    source_detail_status = source_context.get("source_detail_status", {})
    analyzed_source_status = source_context.get("analyzed_source_status", {})
    census_status = ""
    if isinstance(analyzed_source_status, dict):
        census_status = str(analyzed_source_status.get("census_tiger_acs", ""))
    if not census_status and isinstance(source_detail_status, dict):
        census_status = str(source_detail_status.get("census_tiger_acs", ""))
    if census_status in UNAVAILABLE_SOURCE_STATUSES or not census_status:
        flags.add("source_unavailable")
    if census_status == "unimplemented":
        flags.add("source_unimplemented")
    return sorted(flags)


def _target_source_refs(source_context: dict[str, Any], categories: list[str]) -> list[str]:
    refs: set[str] = set()
    source_ids = source_context.get("source_ids_by_category", {})
    if isinstance(source_ids, dict):
        for category in categories:
            refs.update(_string_list(source_ids.get(category, [])))
    return sorted(item for item in refs if item)


def _census_constraints(constraints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [constraint for constraint in constraints if constraint.get("source_id") == "census_tiger_acs"]


def _census_geography(constraint: dict[str, Any]) -> str:
    values = _values(constraint)
    return (
        _first_present(values, "census_geography")
        or str(constraint.get("source_feature_label", "")).strip()
        or _first_present(values, "census_geoid")
    )


def _values(constraint: dict[str, Any]) -> dict[str, str]:
    values = constraint.get("source_feature_values", {})
    if not isinstance(values, dict):
        return {}
    return {str(key): str(value).strip() for key, value in values.items() if str(value).strip()}


def _first_present(values: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = values.get(key, "")
        if value:
            return value
    return ""


def _dedupe_key(constraint: dict[str, Any]) -> str:
    original_id = str(constraint.get("source_feature_original_id", "")).strip()
    if original_id:
        return f"{constraint.get('source_id')}:{original_id}"
    label = str(constraint.get("source_feature_label", "")).strip()
    geometry_hash = str(constraint.get("source_feature_geometry_hash", "")).strip()
    return f"{constraint.get('source_id')}:{label}:{geometry_hash}"


def _row_string(row: Any, column: str, default: str) -> str:
    if column not in row.index:
        return default
    value = row[column]
    if value is None:
        return default
    text = str(value).strip()
    return default if not text or text.lower() == "nan" else text


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _float_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _validate_deliverable_tables(data: dict[str, Any], location: str) -> None:
    tables = data.get("tables")
    if not isinstance(tables, list):
        raise DeliverableTableError(f"Deliverable tables artifact requires a list field named 'tables': {location}")
    if data.get("table_count") != len(tables):
        raise DeliverableTableError(f"Deliverable tables artifact table_count does not match tables: {location}")
    seen_ids: set[str] = set()
    required_fields = {
        "table_id",
        "table_number",
        "title",
        "section_target_id",
        "columns",
        "rows",
        "row_count",
        "source_refs",
        "related_constraint_ids",
        "comparison_unit_ids",
        "provenance",
        "uncertainty_flags",
        "is_stub",
        "stub_text",
        "review_status",
    }
    for table in tables:
        if not isinstance(table, dict):
            raise DeliverableTableError(f"Each deliverable table must be an object: {location}")
        missing = sorted(required_fields - set(table))
        if missing:
            raise DeliverableTableError(f"Deliverable table is missing required fields {missing}: {location}")
        table_id = table["table_id"]
        if not isinstance(table_id, str) or not table_id.strip():
            raise DeliverableTableError(f"Deliverable table requires a non-empty table_id: {location}")
        if table_id in seen_ids:
            raise DeliverableTableError(f"Duplicate deliverable table id '{table_id}': {location}")
        seen_ids.add(table_id)
        if not isinstance(table["columns"], list) or not all(isinstance(column, str) and column for column in table["columns"]):
            raise DeliverableTableError(f"Deliverable table '{table_id}' columns must be a list of strings: {location}")
        if not isinstance(table["rows"], list) or not all(isinstance(row, dict) for row in table["rows"]):
            raise DeliverableTableError(f"Deliverable table '{table_id}' rows must be a list of objects: {location}")
        if table["row_count"] != len(table["rows"]):
            raise DeliverableTableError(f"Deliverable table '{table_id}' row_count does not match rows: {location}")
        if table["review_status"] not in SUPPORTED_REVIEW_STATUSES:
            raise DeliverableTableError(f"Deliverable table '{table_id}' has unsupported review_status: {location}")
        if not isinstance(table["provenance"], dict):
            raise DeliverableTableError(f"Deliverable table '{table_id}' provenance must be an object: {location}")
        if not isinstance(table["is_stub"], bool):
            raise DeliverableTableError(f"Deliverable table '{table_id}' is_stub must be boolean: {location}")
        for list_field in ("source_refs", "related_constraint_ids", "comparison_unit_ids", "uncertainty_flags"):
            if not isinstance(table[list_field], list):
                raise DeliverableTableError(f"Deliverable table '{table_id}' field '{list_field}' must be a list: {location}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
