"""Comparison table artifact generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constraints import CONSTRAINT_RESULTS_PATH, ConstraintAnalysisError, load_constraint_results
from .findings import FINDINGS_PATH, FindingGenerationError, generate_draft_findings, load_draft_findings
from .project_context import ProjectContextError, generate_project_context, load_project_context
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set


TABLES_PATH = Path("tables/comparison_tables.json")
SPATIAL_RELATIONSHIPS_PATH = Path("intermediate/spatial_relationships.json")
REQUIRED_TABLE_FIELDS = {
    "table_id",
    "type",
    "title",
    "description",
    "columns",
    "rows",
    "row_count",
    "provenance",
    "source_refs",
    "review_status",
    "uncertainty_flags",
}


class TableGenerationError(RuntimeError):
    """Raised when comparison table generation or loading cannot complete."""


def generate_comparison_tables(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        context = _load_or_generate_context(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
        constraints = _load_optional_constraint_results(project_dir)
        spatial = _load_optional_spatial_relationships(project_dir)
        draft_findings = _load_or_generate_findings(project_dir)
    except (ProjectContextError, SourceStatusError, ConstraintAnalysisError, FindingGenerationError) as exc:
        raise TableGenerationError(str(exc)) from exc

    output_path = project_dir / TABLES_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tables = [
        _source_status_matrix(source_status),
        _constraint_summary(constraints),
        _grouped_constraint_summary(constraints),
        _hydrography_crossing_summary(constraints),
        _flood_hazard_summary(constraints),
        _critical_habitat_summary(constraints),
        _regulated_facility_summary(constraints),
        _soil_mapunit_summary(constraints),
        _spatial_relationship_summary(spatial),
        _draft_finding_summary(draft_findings),
    ]
    result = {
        "project_id": context["project_id"],
        "project_name": context["project_name"],
        "project_dir": str(project_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "upstream_artifacts": {
            "project_context_path": context.get("context_path"),
            "source_status_path": source_status.get("output_path"),
            "constraint_results_path": constraints.get("output_path") if constraints else None,
            "spatial_relationships_path": spatial.get("output_path") if spatial else None,
            "draft_findings_path": draft_findings.get("output_path"),
        },
        "table_count": len(tables),
        "tables": tables,
        "validation_issues": [],
        "output_path": str(output_path),
    }
    _validate_comparison_tables(result, str(output_path))
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_comparison_tables(project_dir: Path) -> dict[str, Any]:
    tables_path = project_dir.resolve() / TABLES_PATH
    if not tables_path.exists():
        raise TableGenerationError(f"Missing comparison tables artifact: {tables_path}")
    try:
        data = json.loads(tables_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TableGenerationError(f"Invalid comparison tables JSON: {tables_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise TableGenerationError(f"Comparison tables artifact must be a JSON object: {tables_path}")
    _validate_comparison_tables(data, str(tables_path))
    return data


def _load_or_generate_context(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_context(project_dir)
    except ProjectContextError:
        return generate_project_context(project_dir)


def _load_or_generate_source_status(project_dir: Path) -> dict[str, Any]:
    source_status_path = project_dir / SOURCE_STATUS_PATH
    if source_status_path.exists():
        try:
            data = json.loads(source_status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SourceStatusError(f"Invalid source status JSON: {source_status_path}: {exc}") from exc
        if isinstance(data, dict):
            return data
        raise SourceStatusError(f"Source status artifact must be a JSON object: {source_status_path}")
    return resolve_source_status_set(project_dir)


def _load_optional_spatial_relationships(project_dir: Path) -> dict[str, Any] | None:
    spatial_path = project_dir / SPATIAL_RELATIONSHIPS_PATH
    if not spatial_path.exists():
        return None
    try:
        data = json.loads(spatial_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TableGenerationError(f"Invalid spatial relationships JSON: {spatial_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise TableGenerationError(f"Spatial relationships artifact must be a JSON object: {spatial_path}")
    if not isinstance(data.get("relationships", []), list):
        raise TableGenerationError(f"Spatial relationships artifact requires a list field named 'relationships': {spatial_path}")
    return data


def _load_optional_constraint_results(project_dir: Path) -> dict[str, Any] | None:
    constraint_path = project_dir / CONSTRAINT_RESULTS_PATH
    if not constraint_path.exists():
        return None
    return load_constraint_results(project_dir)


def _load_or_generate_findings(project_dir: Path) -> dict[str, Any]:
    findings_path = project_dir / FINDINGS_PATH
    if findings_path.exists():
        return load_draft_findings(project_dir)
    return generate_draft_findings(project_dir)


def _source_status_matrix(source_status: dict[str, Any]) -> dict[str, Any]:
    columns = [
        "category",
        "requirement",
        "status",
        "source_count",
        "registered_source_count",
        "local_path_count",
        "uncertainty_flags",
        "notes",
    ]
    rows: list[dict[str, Any]] = []
    source_refs: set[str] = set()
    for status_record in source_status.get("statuses", []):
        if not isinstance(status_record, dict):
            continue
        source_ids = _string_list(status_record.get("source_ids", []))
        source_refs.update(source_ids)
        rows.append(
            {
                "category": status_record.get("category", ""),
                "requirement": status_record.get("requirement", ""),
                "status": status_record.get("status", ""),
                "source_count": len(source_ids),
                "registered_source_count": len(_string_list(status_record.get("registered_source_ids", []))),
                "local_path_count": len(_string_list(status_record.get("local_paths", []))),
                "uncertainty_flags": _string_list(status_record.get("uncertainty_flags", [])),
                "notes": status_record.get("notes", ""),
            }
        )
    return _table(
        table_id="source-status-matrix",
        table_type="source_status_matrix",
        title="Source Status Matrix",
        description="Required and optional source categories with current workspace status.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "source_status_set", "artifact_path": source_status.get("output_path")},
        source_refs=sorted(source_refs),
        uncertainty_flags=[],
    )


def _constraint_summary(constraints: dict[str, Any] | None) -> dict[str, Any]:
    columns = [
        "constraint_id",
        "project_feature_id",
        "project_feature_name",
        "project_geometry_role",
        "source_category",
        "source_id",
        "source_name",
        "source_feature_label",
        "source_feature_type",
        "source_feature_subtype",
        "source_feature_original_id",
        "relationship_type",
        "buffer_feet",
        "measurements",
    ]
    rows: list[dict[str, Any]] = []
    source_refs: set[str] = set()
    if constraints is not None:
        for constraint in constraints.get("constraints", []):
            if not isinstance(constraint, dict):
                continue
            source_id = str(constraint.get("source_id", ""))
            if source_id:
                source_refs.add(source_id)
            rows.append(
                {
                    "constraint_id": constraint.get("constraint_id", ""),
                    "project_feature_id": constraint.get("project_feature_id", ""),
                    "project_feature_name": constraint.get("project_feature_name", ""),
                    "project_geometry_role": constraint.get("project_geometry_role", ""),
                    "source_category": constraint.get("source_category", ""),
                    "source_id": source_id,
                    "source_name": constraint.get("source_name", ""),
                    "source_feature_label": constraint.get("source_feature_label") or constraint.get("source_feature_index", ""),
                    "source_feature_type": constraint.get("source_feature_type", ""),
                    "source_feature_subtype": constraint.get("source_feature_subtype", ""),
                    "source_feature_original_id": constraint.get("source_feature_original_id", ""),
                    "relationship_type": constraint.get("relationship_type", ""),
                    "buffer_feet": constraint.get("buffer_feet"),
                    "measurements": constraint.get("measurements", {}),
                }
            )
    return _table(
        table_id="constraint-summary",
        table_type="constraint_summary",
        title="Constraint Summary",
        description="Objective constraint overlap and proximity records by project feature and source category.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "constraint_results", "artifact_path": constraints.get("output_path") if constraints else None},
        source_refs=sorted(source_refs),
        uncertainty_flags=["no_constraint_results_artifact"] if constraints is None else [],
    )


def _grouped_constraint_summary(constraints: dict[str, Any] | None) -> dict[str, Any]:
    columns = [
        "project_feature_id",
        "project_feature_name",
        "project_geometry_role",
        "source_category",
        "source_ids",
        "source_names",
        "relationship_types",
        "constraint_count",
        "total_intersection_length_feet",
        "total_intersection_area_acres",
        "nearest_distance_feet",
    ]
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    source_refs: set[str] = set()
    if constraints is not None:
        for constraint in constraints.get("constraints", []):
            if not isinstance(constraint, dict):
                continue
            feature_id = str(constraint.get("project_feature_id", ""))
            category = str(constraint.get("source_category", ""))
            key = (feature_id, category)
            row = grouped.setdefault(
                key,
                {
                    "project_feature_id": feature_id,
                    "project_feature_name": constraint.get("project_feature_name", ""),
                    "project_geometry_role": constraint.get("project_geometry_role", ""),
                    "source_category": category,
                    "source_ids": set(),
                    "source_names": set(),
                    "relationship_types": set(),
                    "constraint_count": 0,
                    "total_intersection_length_feet": 0.0,
                    "total_intersection_area_acres": 0.0,
                    "_distances": [],
                },
            )
            source_id = str(constraint.get("source_id", ""))
            source_name = str(constraint.get("source_name", ""))
            relationship = str(constraint.get("relationship_type", ""))
            if source_id:
                row["source_ids"].add(source_id)
                source_refs.add(source_id)
            if source_name:
                row["source_names"].add(source_name)
            if relationship:
                row["relationship_types"].add(relationship)
            row["constraint_count"] += 1
            measurements = constraint.get("measurements", {})
            if not isinstance(measurements, dict):
                continue
            row["total_intersection_length_feet"] += _float_value(measurements.get("intersection_length_feet"))
            row["total_intersection_area_acres"] += _float_value(measurements.get("intersection_area_acres"))
            distance = measurements.get("distance_feet")
            if distance is not None:
                row["_distances"].append(_float_value(distance))

    rows: list[dict[str, Any]] = []
    for row in grouped.values():
        distances = row.pop("_distances")
        row["source_ids"] = sorted(row["source_ids"])
        row["source_names"] = sorted(row["source_names"])
        row["relationship_types"] = sorted(row["relationship_types"])
        row["total_intersection_length_feet"] = round(row["total_intersection_length_feet"], 2)
        row["total_intersection_area_acres"] = round(row["total_intersection_area_acres"], 4)
        row["nearest_distance_feet"] = round(min(distances), 2) if distances else None
        rows.append(row)

    rows.sort(key=lambda item: (str(item["project_feature_id"]), str(item["source_category"])))
    return _table(
        table_id="grouped-constraint-summary",
        table_type="grouped_constraint_summary",
        title="Grouped Constraint Summary",
        description="Constraint counts and measurement totals grouped by project feature and source category.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "constraint_results", "artifact_path": constraints.get("output_path") if constraints else None},
        source_refs=sorted(source_refs),
        uncertainty_flags=["no_constraint_results_artifact"] if constraints is None else [],
    )


def _hydrography_crossing_summary(constraints: dict[str, Any] | None) -> dict[str, Any]:
    columns = [
        "project_feature_id",
        "project_feature_name",
        "source_category",
        "source_id",
        "source_feature_label",
        "source_feature_type",
        "relationship_type",
        "intersection_length_feet",
        "intersection_area_acres",
        "distance_feet",
        "buffer_feet",
    ]
    rows: list[dict[str, Any]] = []
    source_refs: set[str] = set()
    if constraints is not None:
        for constraint in constraints.get("constraints", []):
            if not isinstance(constraint, dict) or constraint.get("source_category") != "hydrography_crossings":
                continue
            source_id = str(constraint.get("source_id", ""))
            if source_id:
                source_refs.add(source_id)
            measurements = constraint.get("measurements", {})
            if not isinstance(measurements, dict):
                measurements = {}
            rows.append(
                {
                    "project_feature_id": constraint.get("project_feature_id", ""),
                    "project_feature_name": constraint.get("project_feature_name", ""),
                    "source_category": constraint.get("source_category", ""),
                    "source_id": source_id,
                    "source_feature_label": constraint.get("source_feature_label") or constraint.get("source_feature_index", ""),
                    "source_feature_type": constraint.get("source_feature_type", ""),
                    "relationship_type": constraint.get("relationship_type", ""),
                    "intersection_length_feet": measurements.get("intersection_length_feet"),
                    "intersection_area_acres": measurements.get("intersection_area_acres"),
                    "distance_feet": measurements.get("distance_feet"),
                    "buffer_feet": constraint.get("buffer_feet"),
                }
            )
    return _table(
        table_id="hydrography-crossing-summary",
        table_type="hydrography_crossing_summary",
        title="Hydrography Crossing Summary",
        description="Objective stream, river, ditch, waterbody, and hydrography relationships by project feature.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "constraint_results", "artifact_path": constraints.get("output_path") if constraints else None},
        source_refs=sorted(source_refs),
        uncertainty_flags=["no_constraint_results_artifact"] if constraints is None else [],
    )


def _flood_hazard_summary(constraints: dict[str, Any] | None) -> dict[str, Any]:
    columns = [
        "project_feature_id",
        "project_feature_name",
        "source_category",
        "source_id",
        "flood_zone",
        "zone_subtype",
        "sfha_flag",
        "static_bfe",
        "vertical_datum",
        "depth",
        "length_unit",
        "relationship_type",
        "intersection_length_feet",
        "intersection_area_acres",
        "distance_feet",
        "buffer_feet",
        "source_feature_original_id",
        "source_citation",
    ]
    rows: list[dict[str, Any]] = []
    source_refs: set[str] = set()
    if constraints is not None:
        for constraint in constraints.get("constraints", []):
            if not isinstance(constraint, dict) or constraint.get("source_category") != "flood_hazard":
                continue
            source_id = str(constraint.get("source_id", ""))
            if source_id:
                source_refs.add(source_id)
            measurements = constraint.get("measurements", {})
            if not isinstance(measurements, dict):
                measurements = {}
            values = constraint.get("source_feature_values", {})
            if not isinstance(values, dict):
                values = {}
            rows.append(
                {
                    "project_feature_id": constraint.get("project_feature_id", ""),
                    "project_feature_name": constraint.get("project_feature_name", ""),
                    "source_category": constraint.get("source_category", ""),
                    "source_id": source_id,
                    "flood_zone": values.get("flood_zone") or constraint.get("source_feature_type", ""),
                    "zone_subtype": values.get("flood_zone_subtype") or constraint.get("source_feature_subtype", ""),
                    "sfha_flag": values.get("sfha_flag") or constraint.get("source_feature_quality_flag", ""),
                    "static_bfe": values.get("static_bfe", ""),
                    "vertical_datum": values.get("vertical_datum", ""),
                    "depth": values.get("depth", ""),
                    "length_unit": values.get("length_unit", ""),
                    "relationship_type": constraint.get("relationship_type", ""),
                    "intersection_length_feet": measurements.get("intersection_length_feet"),
                    "intersection_area_acres": measurements.get("intersection_area_acres"),
                    "distance_feet": measurements.get("distance_feet"),
                    "buffer_feet": constraint.get("buffer_feet"),
                    "source_feature_original_id": constraint.get("source_feature_original_id", ""),
                    "source_citation": values.get("source_citation") or constraint.get("source_feature_source_citation", ""),
                }
            )
    return _table(
        table_id="flood-hazard-summary",
        table_type="flood_hazard_summary",
        title="FEMA Flood Hazard Summary",
        description="Effective FEMA NFHL flood hazard zone relationships by project feature.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "constraint_results", "artifact_path": constraints.get("output_path") if constraints else None},
        source_refs=sorted(source_refs),
        uncertainty_flags=["no_constraint_results_artifact"] if constraints is None else [],
    )


def _critical_habitat_summary(constraints: dict[str, Any] | None) -> dict[str, Any]:
    columns = [
        "project_feature_id",
        "project_feature_name",
        "source_category",
        "source_id",
        "species_common_name",
        "species_scientific_name",
        "critical_habitat_status",
        "listing_status",
        "critical_habitat_unit",
        "critical_habitat_subunit",
        "federal_register",
        "publication_date",
        "effective_date",
        "relationship_type",
        "intersection_length_feet",
        "intersection_area_acres",
        "distance_feet",
        "buffer_feet",
        "source_feature_original_id",
    ]
    rows: list[dict[str, Any]] = []
    source_refs: set[str] = set()
    if constraints is not None:
        for constraint in constraints.get("constraints", []):
            if not isinstance(constraint, dict) or constraint.get("source_category") != "species_habitat":
                continue
            if constraint.get("source_id") != "usfws_critical_habitat":
                continue
            source_id = str(constraint.get("source_id", ""))
            if source_id:
                source_refs.add(source_id)
            measurements = constraint.get("measurements", {})
            if not isinstance(measurements, dict):
                measurements = {}
            values = constraint.get("source_feature_values", {})
            if not isinstance(values, dict):
                values = {}
            rows.append(
                {
                    "project_feature_id": constraint.get("project_feature_id", ""),
                    "project_feature_name": constraint.get("project_feature_name", ""),
                    "source_category": constraint.get("source_category", ""),
                    "source_id": source_id,
                    "species_common_name": values.get("species_common_name") or constraint.get("source_feature_label", ""),
                    "species_scientific_name": values.get("species_scientific_name", ""),
                    "critical_habitat_status": values.get("critical_habitat_status") or constraint.get("source_feature_type", ""),
                    "listing_status": values.get("listing_status", ""),
                    "critical_habitat_unit": values.get("critical_habitat_unit", ""),
                    "critical_habitat_subunit": values.get("critical_habitat_subunit", ""),
                    "federal_register": values.get("federal_register") or constraint.get("source_feature_source_citation", ""),
                    "publication_date": values.get("publication_date", ""),
                    "effective_date": values.get("effective_date") or constraint.get("source_feature_date", ""),
                    "relationship_type": constraint.get("relationship_type", ""),
                    "intersection_length_feet": measurements.get("intersection_length_feet"),
                    "intersection_area_acres": measurements.get("intersection_area_acres"),
                    "distance_feet": measurements.get("distance_feet"),
                    "buffer_feet": constraint.get("buffer_feet"),
                    "source_feature_original_id": constraint.get("source_feature_original_id", ""),
                }
            )
    return _table(
        table_id="critical-habitat-summary",
        table_type="critical_habitat_summary",
        title="USFWS Critical Habitat Summary",
        description="USFWS final and proposed critical habitat relationships by project feature.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "constraint_results", "artifact_path": constraints.get("output_path") if constraints else None},
        source_refs=sorted(source_refs),
        uncertainty_flags=["no_constraint_results_artifact"] if constraints is None else [],
    )


def _regulated_facility_summary(constraints: dict[str, Any] | None) -> dict[str, Any]:
    columns = [
        "project_feature_id",
        "project_feature_name",
        "source_category",
        "source_id",
        "facility_name",
        "registry_id",
        "address",
        "city",
        "state",
        "program_flags",
        "active_flag",
        "major_flag",
        "current_compliance_status",
        "current_snc_flag",
        "inspection_count",
        "last_inspection_date",
        "formal_action_count",
        "informal_action_count",
        "total_penalties",
        "relationship_type",
        "distance_feet",
        "buffer_feet",
        "dfr_url",
        "collection_method",
        "accuracy_meters",
    ]
    rows: list[dict[str, Any]] = []
    source_refs: set[str] = set()
    if constraints is not None:
        for constraint in constraints.get("constraints", []):
            if not isinstance(constraint, dict) or constraint.get("source_category") != "regulated_facilities":
                continue
            source_id = str(constraint.get("source_id", ""))
            if source_id:
                source_refs.add(source_id)
            measurements = constraint.get("measurements", {})
            if not isinstance(measurements, dict):
                measurements = {}
            values = constraint.get("source_feature_values", {})
            if not isinstance(values, dict):
                values = {}
            rows.append(
                {
                    "project_feature_id": constraint.get("project_feature_id", ""),
                    "project_feature_name": constraint.get("project_feature_name", ""),
                    "source_category": constraint.get("source_category", ""),
                    "source_id": source_id,
                    "facility_name": values.get("facility_name") or constraint.get("source_feature_label", ""),
                    "registry_id": values.get("facility_registry_id") or constraint.get("source_feature_original_id", ""),
                    "address": values.get("facility_street", ""),
                    "city": values.get("facility_city", ""),
                    "state": values.get("facility_state", ""),
                    "program_flags": values.get("facility_programs") or constraint.get("source_feature_type", ""),
                    "active_flag": values.get("facility_active_flag", ""),
                    "major_flag": values.get("facility_major_flag", ""),
                    "current_compliance_status": values.get("facility_current_compliance_status", ""),
                    "current_snc_flag": values.get("facility_current_snc_flag", ""),
                    "inspection_count": values.get("facility_inspection_count", ""),
                    "last_inspection_date": values.get("facility_last_inspection_date") or constraint.get("source_feature_date", ""),
                    "formal_action_count": values.get("facility_formal_action_count", ""),
                    "informal_action_count": values.get("facility_informal_action_count", ""),
                    "total_penalties": values.get("facility_total_penalties", ""),
                    "relationship_type": constraint.get("relationship_type", ""),
                    "distance_feet": measurements.get("distance_feet"),
                    "buffer_feet": constraint.get("buffer_feet"),
                    "dfr_url": values.get("facility_dfr_url") or constraint.get("source_feature_source_citation", ""),
                    "collection_method": values.get("facility_collection_method", ""),
                    "accuracy_meters": values.get("facility_accuracy_meters", ""),
                }
            )
    return _table(
        table_id="regulated-facility-summary",
        table_type="regulated_facility_summary",
        title="EPA ECHO Regulated Facility Summary",
        description="EPA ECHO regulated facility proximity records by project feature.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "constraint_results", "artifact_path": constraints.get("output_path") if constraints else None},
        source_refs=sorted(source_refs),
        uncertainty_flags=["no_constraint_results_artifact"] if constraints is None else [],
    )


def _soil_mapunit_summary(constraints: dict[str, Any] | None) -> dict[str, Any]:
    columns = [
        "project_feature_id",
        "project_feature_name",
        "source_category",
        "source_id",
        "mapunit_symbol",
        "mapunit_key",
        "area_symbol",
        "spatial_version",
        "relationship_type",
        "intersection_length_feet",
        "intersection_area_acres",
        "distance_feet",
        "buffer_feet",
        "source_feature_label",
    ]
    rows: list[dict[str, Any]] = []
    source_refs: set[str] = set()
    if constraints is not None:
        for constraint in constraints.get("constraints", []):
            if not isinstance(constraint, dict) or constraint.get("source_category") != "soils":
                continue
            source_id = str(constraint.get("source_id", ""))
            if source_id:
                source_refs.add(source_id)
            measurements = constraint.get("measurements", {})
            if not isinstance(measurements, dict):
                measurements = {}
            values = constraint.get("source_feature_values", {})
            if not isinstance(values, dict):
                values = {}
            rows.append(
                {
                    "project_feature_id": constraint.get("project_feature_id", ""),
                    "project_feature_name": constraint.get("project_feature_name", ""),
                    "source_category": constraint.get("source_category", ""),
                    "source_id": source_id,
                    "mapunit_symbol": values.get("soil_mapunit_symbol") or constraint.get("source_feature_label", ""),
                    "mapunit_key": values.get("soil_mapunit_key") or constraint.get("source_feature_original_id", ""),
                    "area_symbol": values.get("soil_area_symbol", ""),
                    "spatial_version": values.get("soil_spatial_version", ""),
                    "relationship_type": constraint.get("relationship_type", ""),
                    "intersection_length_feet": measurements.get("intersection_length_feet"),
                    "intersection_area_acres": measurements.get("intersection_area_acres"),
                    "distance_feet": measurements.get("distance_feet"),
                    "buffer_feet": constraint.get("buffer_feet"),
                    "source_feature_label": constraint.get("source_feature_label", ""),
                }
            )
    return _table(
        table_id="soil-mapunit-summary",
        table_type="soil_mapunit_summary",
        title="SSURGO Soil Map Unit Summary",
        description="USDA NRCS SSURGO soil map unit relationships by project feature.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "constraint_results", "artifact_path": constraints.get("output_path") if constraints else None},
        source_refs=sorted(source_refs),
        uncertainty_flags=["no_constraint_results_artifact"] if constraints is None else [],
    )


def _spatial_relationship_summary(spatial: dict[str, Any] | None) -> dict[str, Any]:
    columns = [
        "relationship_id",
        "project_feature_label",
        "project_input_role",
        "source_category",
        "source_id",
        "source_name",
        "source_feature_label",
        "spatial_relationship",
        "buffer_feet",
        "measurements",
    ]
    rows: list[dict[str, Any]] = []
    source_refs: set[str] = set()
    if spatial is not None:
        for relationship in spatial.get("relationships", []):
            if not isinstance(relationship, dict):
                continue
            source_id = str(relationship.get("source_id", ""))
            if source_id:
                source_refs.add(source_id)
            rows.append(
                {
                    "relationship_id": relationship.get("relationship_id", ""),
                    "project_feature_label": relationship.get("project_feature_label") or relationship.get("project_feature_index", ""),
                    "project_input_role": relationship.get("project_input_role", ""),
                    "source_category": relationship.get("source_category", ""),
                    "source_id": source_id,
                    "source_name": relationship.get("source_name", ""),
                    "source_feature_label": relationship.get("source_feature_label") or relationship.get("source_feature_index", ""),
                    "spatial_relationship": relationship.get("spatial_relationship", ""),
                    "buffer_feet": relationship.get("buffer_feet"),
                    "measurements": relationship.get("measurements", {}),
                }
            )
    return _table(
        table_id="spatial-relationship-summary",
        table_type="spatial_relationship_summary",
        title="Spatial Relationship Summary",
        description="Deterministic spatial relationships by project feature and source category.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "spatial_relationships", "artifact_path": spatial.get("output_path") if spatial else None},
        source_refs=sorted(source_refs),
        uncertainty_flags=["no_spatial_relationship_artifact"] if spatial is None else [],
    )


def _draft_finding_summary(draft_findings: dict[str, Any]) -> dict[str, Any]:
    columns = [
        "finding_id",
        "resource_category",
        "type",
        "title",
        "review_status",
        "evidence_class",
        "source_ids",
        "uncertainty_flags",
    ]
    rows: list[dict[str, Any]] = []
    source_refs: set[str] = set()
    for finding in draft_findings.get("findings", []):
        if not isinstance(finding, dict):
            continue
        source_ids = _string_list(finding.get("source_ids", []))
        source_refs.update(source_ids)
        rows.append(
            {
                "finding_id": finding.get("finding_id", ""),
                "resource_category": finding.get("resource_category", ""),
                "type": finding.get("type", ""),
                "title": finding.get("title", ""),
                "review_status": finding.get("review_status", ""),
                "evidence_class": finding.get("evidence_class", ""),
                "source_ids": source_ids,
                "uncertainty_flags": _string_list(finding.get("uncertainty_flags", [])),
            }
        )
    return _table(
        table_id="draft-finding-summary",
        table_type="draft_finding_summary",
        title="Draft Finding Summary",
        description="Draft findings grouped by resource category, finding type, and review status.",
        columns=columns,
        rows=rows,
        provenance={"artifact": "draft_findings", "artifact_path": draft_findings.get("output_path")},
        source_refs=sorted(source_refs),
        uncertainty_flags=[],
    )


def _table(
    *,
    table_id: str,
    table_type: str,
    title: str,
    description: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    provenance: dict[str, Any],
    source_refs: list[str],
    uncertainty_flags: list[str],
) -> dict[str, Any]:
    return {
        "table_id": table_id,
        "type": table_type,
        "title": title,
        "description": description,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "provenance": provenance,
        "source_refs": source_refs,
        "review_status": "draft",
        "uncertainty_flags": uncertainty_flags,
    }


def _validate_comparison_tables(data: dict[str, Any], location: str) -> None:
    tables = data.get("tables")
    if not isinstance(tables, list):
        raise TableGenerationError(f"Comparison tables artifact requires a list field named 'tables': {location}")
    table_count = data.get("table_count")
    if table_count is not None and table_count != len(tables):
        raise TableGenerationError(f"Comparison tables artifact table_count does not match tables: {location}")
    seen_ids: set[str] = set()
    for table in tables:
        if not isinstance(table, dict):
            raise TableGenerationError(f"Each comparison table must be an object: {location}")
        missing = sorted(REQUIRED_TABLE_FIELDS - set(table))
        if missing:
            raise TableGenerationError(f"Comparison table is missing required fields {missing}: {location}")
        table_id = table["table_id"]
        if not isinstance(table_id, str) or not table_id.strip():
            raise TableGenerationError(f"Comparison table requires a non-empty table_id: {location}")
        if table_id in seen_ids:
            raise TableGenerationError(f"Duplicate comparison table id '{table_id}': {location}")
        seen_ids.add(table_id)
        if not isinstance(table["columns"], list) or not all(isinstance(column, str) and column for column in table["columns"]):
            raise TableGenerationError(f"Comparison table '{table_id}' columns must be a list of strings: {location}")
        if not isinstance(table["rows"], list) or not all(isinstance(row, dict) for row in table["rows"]):
            raise TableGenerationError(f"Comparison table '{table_id}' rows must be a list of objects: {location}")
        if table["row_count"] != len(table["rows"]):
            raise TableGenerationError(f"Comparison table '{table_id}' row_count does not match rows: {location}")
        if table["review_status"] not in {"draft", "needs_review", "accepted", "edited", "rejected", "needs_verification", "unable_to_verify"}:
            raise TableGenerationError(f"Comparison table '{table_id}' has unsupported review_status: {location}")
        if not isinstance(table["provenance"], dict):
            raise TableGenerationError(f"Comparison table '{table_id}' provenance must be an object: {location}")
        for list_field in ("source_refs", "uncertainty_flags"):
            if not isinstance(table[list_field], list):
                raise TableGenerationError(f"Comparison table '{table_id}' field '{list_field}' must be a list: {location}")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _float_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
