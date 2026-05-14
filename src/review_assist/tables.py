"""Comparison table artifact generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
        spatial = _load_optional_spatial_relationships(project_dir)
        draft_findings = _load_or_generate_findings(project_dir)
    except (ProjectContextError, SourceStatusError, FindingGenerationError) as exc:
        raise TableGenerationError(str(exc)) from exc

    output_path = project_dir / TABLES_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tables = [
        _source_status_matrix(source_status),
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
        if not isinstance(table["provenance"], dict):
            raise TableGenerationError(f"Comparison table '{table_id}' provenance must be an object: {location}")
        for list_field in ("source_refs", "uncertainty_flags"):
            if not isinstance(table[list_field], list):
                raise TableGenerationError(f"Comparison table '{table_id}' field '{list_field}' must be a list: {location}")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
