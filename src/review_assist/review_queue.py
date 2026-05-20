"""JSON-backed review queue services."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constraints import CONSTRAINT_RESULTS_PATH, ConstraintAnalysisError, load_constraint_results
from .deliverable_items import DELIVERABLE_ITEMS_PATH, DeliverableItemsError, generate_deliverable_items, load_deliverable_items
from .extent_policy import EXTENT_FIELD_NAMES, apply_extent_metadata, merge_extent_metadata, target_extent_metadata
from .findings import FINDINGS_PATH, FindingGenerationError, load_draft_findings
from .maps import MAP_MANIFEST_PATH, MapGenerationError, load_map_manifest
from .project_context import ProjectContextError, generate_project_context, load_project_context
from .report_sections import REPORT_SECTIONS_PATH, ReportSectionGenerationError, load_report_sections
from .source_inventory import SOURCE_INVENTORY_PATH, SourceInventoryError, load_source_inventory
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set
from .tables import TABLES_PATH, TableGenerationError, load_comparison_tables


REVIEW_QUEUE_PATH = Path("review_queue/review_queue.json")
SPATIAL_RELATIONSHIPS_PATH = Path("intermediate/spatial_relationships.json")
SUPPORTED_STATUSES = {
    "draft",
    "needs_review",
    "accepted",
    "edited",
    "rejected",
    "replaced",
    "declined",
    "needs_verification",
    "unable_to_verify",
}
EXPORT_TRUE_STATUSES = {"accepted", "edited", "replaced", "unable_to_verify"}
MISSING_DATA_STATUSES = {"missing", "gated", "stubbed", "needs_review", "downloadable", "failed"}
REQUIRED_ITEM_FIELDS = {
    "id",
    "project_id",
    "type",
    "deliverable_item_id",
    "target_id",
    "title",
    "generated_content",
    "edited_content",
    "replacement_content",
    "status",
    "export_eligible",
    "export_section",
    "export_group",
    "section_order",
    "heading_level",
    "table_id",
    "figure_id",
    "attachment_id",
    "comparison_unit_ids",
    "related_finding_ids",
    "related_constraint_ids",
    "related_table_ids",
    "related_figure_ids",
    "evidence_refs",
    "assumptions",
    "provenance",
    "source_refs",
    "uncertainty_flags",
    "reviewer_notes",
    "validation_issues",
    "created_at",
    "updated_at",
    *EXTENT_FIELD_NAMES,
    "extent_policy_version",
}


class ReviewQueueError(RuntimeError):
    """Raised when review queue generation or updates cannot complete."""


def generate_review_queue(
    project_dir: Path,
    *,
    include_source_inventory: bool = False,
    include_legacy_artifacts: bool = False,
) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    now = _utc_now()
    context = _load_or_generate_context(project_dir)
    existing = _load_existing_queue(project_dir)
    legacy_mode = include_legacy_artifacts or include_source_inventory
    deliverable_items = _load_or_generate_deliverable_items(project_dir) if not legacy_mode else None

    if legacy_mode:
        source_status = _load_or_generate_source_status(project_dir)
        source_inventory = _load_optional_source_inventory(project_dir)
        constraints = _load_optional_constraint_results(project_dir)
        spatial = _load_optional_spatial_relationships(project_dir)
        draft_findings = _load_optional_draft_findings(project_dir)
        comparison_tables = _load_optional_comparison_tables(project_dir)
        map_manifest = _load_optional_map_manifest(project_dir)
        report_sections = _load_optional_report_sections(project_dir)
        items = _build_legacy_review_items(
            project_id=str(context["project_id"]),
            now=now,
            context=context,
            source_status=source_status,
            source_inventory=source_inventory,
            constraints=constraints,
            spatial=spatial,
            draft_findings=draft_findings,
            comparison_tables=comparison_tables,
            map_manifest=map_manifest,
            report_sections=report_sections,
            include_source_inventory=include_source_inventory,
        )
        upstream_artifacts = {
            "project_context_path": context.get("context_path"),
            "source_status_path": source_status.get("output_path"),
            "source_inventory_path": source_inventory.get("output_path") if source_inventory else None,
            "constraint_results_path": constraints.get("output_path") if constraints else None,
            "spatial_relationships_path": spatial.get("output_path") if spatial else None,
            "draft_findings_path": draft_findings.get("output_path") if draft_findings else None,
            "comparison_tables_path": comparison_tables.get("output_path") if comparison_tables else None,
            "map_manifest_path": map_manifest.get("output_path") if map_manifest else None,
            "report_sections_path": report_sections.get("output_path") if report_sections else None,
            "evidence_package_path": _nested_value(report_sections, "upstream_artifacts", "evidence_package_path") if report_sections else None,
            "deliverable_items_path": None,
        }
        validation_issues: list[dict[str, Any]] = []
    else:
        items = _build_deliverable_review_items(
            project_id=str(context["project_id"]),
            now=now,
            deliverable_items=deliverable_items or {},
        )
        upstream = deliverable_items.get("upstream_artifacts", {}) if isinstance(deliverable_items, dict) else {}
        upstream_artifacts = {
            "project_context_path": context.get("context_path"),
            "deliverable_items_path": deliverable_items.get("output_path") if deliverable_items else None,
            "deliverable_tables_path": upstream.get("deliverable_tables_path") if isinstance(upstream, dict) else None,
            "deliverable_figures_path": upstream.get("deliverable_figures_path") if isinstance(upstream, dict) else None,
            "evidence_package_path": upstream.get("evidence_package_path") if isinstance(upstream, dict) else None,
            "report_sections_path": None,
            "source_status_path": None,
            "source_inventory_path": None,
            "constraint_results_path": None,
            "spatial_relationships_path": None,
            "draft_findings_path": None,
            "comparison_tables_path": None,
            "map_manifest_path": None,
        }
        validation_issues = _dict_list(deliverable_items.get("validation_issues", [])) if deliverable_items else []
    if existing is not None:
        existing_items = _existing_item_lookup(existing)
        items = [_merge_existing_review_state(item, existing_items, now) for item in items]

    output_path = project_dir / REVIEW_QUEUE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    queue = {
        "project_id": context["project_id"],
        "project_name": context["project_name"],
        "project_dir": str(project_dir),
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
        "queue_mode": "legacy_audit" if legacy_mode else "deliverable_items",
        "upstream_artifacts": upstream_artifacts,
        "item_count": len(items),
        "items": items,
        "validation_issues": _queue_validation_issues(items, validation_issues),
        "output_path": str(output_path),
    }
    _validate_queue(queue)
    output_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    return queue


def load_review_queue(project_dir: Path) -> dict[str, Any]:
    queue_path = project_dir.resolve() / REVIEW_QUEUE_PATH
    if not queue_path.exists():
        raise ReviewQueueError(f"Missing review queue artifact: {queue_path}")
    try:
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewQueueError(f"Invalid review queue JSON: {queue_path}: {exc}") from exc
    _normalize_queue_compat(queue)
    _validate_queue(queue)
    return queue


def summarize_review_queue(project_dir: Path) -> dict[str, Any]:
    queue = load_review_queue(project_dir)
    return {
        "project_id": queue["project_id"],
        "project_name": queue["project_name"],
        "item_count": queue["item_count"],
        "status_counts": dict(Counter(item["status"] for item in queue["items"])),
        "type_counts": dict(Counter(item["type"] for item in queue["items"])),
        "items": [
            {
                "id": item["id"],
                "type": item["type"],
                "title": item["title"],
                "status": item["status"],
                "export_eligible": item["export_eligible"],
            }
            for item in queue["items"]
        ],
        "output_path": queue["output_path"],
    }


def update_review_item(
    project_dir: Path,
    item_id: str,
    *,
    status: str,
    note: str | None = None,
    export_eligible: bool | None = None,
    edited_content: str | None = None,
    replacement_content: str | None = None,
) -> dict[str, Any]:
    status = _normalize_status(status)
    if status not in SUPPORTED_STATUSES:
        raise ReviewQueueError(f"Unsupported review status '{status}'.")

    queue = load_review_queue(project_dir)
    item = _find_item(queue, item_id)
    now = _utc_now()

    if export_eligible is True and status not in EXPORT_TRUE_STATUSES:
        allowed = ", ".join(sorted(EXPORT_TRUE_STATUSES))
        raise ReviewQueueError(f"Only these statuses may be export eligible: {allowed}.")

    item["status"] = status
    if edited_content is not None:
        item["edited_content"] = edited_content
    if replacement_content is not None:
        item["replacement_content"] = replacement_content
    if export_eligible is None:
        item["export_eligible"] = _default_export_eligible(status)
    else:
        item["export_eligible"] = bool(export_eligible)
    if status == "declined":
        item["export_eligible"] = False
    if status == "replaced" and not str(item.get("replacement_content", "")).strip():
        item["export_eligible"] = False
        item["validation_issues"] = _with_replacement_issue(_dict_list(item.get("validation_issues", [])), item_id)
    else:
        item["validation_issues"] = _without_replacement_issue(_dict_list(item.get("validation_issues", [])))

    if note is not None and note.strip():
        item["reviewer_notes"].append({"created_at": now, "note": note.strip()})
    item["updated_at"] = now
    queue["updated_at"] = now
    queue["validation_issues"] = _queue_validation_issues(_dict_list(queue.get("items", [])), _dict_list(queue.get("validation_issues", [])))
    _validate_queue(queue)
    Path(queue["output_path"]).write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    return item


def _load_or_generate_context(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_context(project_dir)
    except ProjectContextError:
        try:
            return generate_project_context(project_dir)
        except ProjectContextError as exc:
            raise ReviewQueueError(str(exc)) from exc


def _load_or_generate_source_status(project_dir: Path) -> dict[str, Any]:
    source_status_path = project_dir / SOURCE_STATUS_PATH
    if source_status_path.exists():
        try:
            data = json.loads(source_status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReviewQueueError(f"Invalid source status JSON: {source_status_path}: {exc}") from exc
        if isinstance(data, dict):
            return data
        raise ReviewQueueError(f"Source status artifact must be a JSON object: {source_status_path}")
    try:
        return resolve_source_status_set(project_dir)
    except SourceStatusError as exc:
        raise ReviewQueueError(str(exc)) from exc


def _load_optional_spatial_relationships(project_dir: Path) -> dict[str, Any] | None:
    spatial_path = project_dir / SPATIAL_RELATIONSHIPS_PATH
    if not spatial_path.exists():
        return None
    try:
        data = json.loads(spatial_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewQueueError(f"Invalid spatial relationships JSON: {spatial_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReviewQueueError(f"Spatial relationships artifact must be a JSON object: {spatial_path}")
    return data


def _load_optional_source_inventory(project_dir: Path) -> dict[str, Any] | None:
    inventory_path = project_dir / SOURCE_INVENTORY_PATH
    if not inventory_path.exists():
        return None
    try:
        return load_source_inventory(project_dir)
    except SourceInventoryError as exc:
        raise ReviewQueueError(str(exc)) from exc


def _load_optional_constraint_results(project_dir: Path) -> dict[str, Any] | None:
    constraint_path = project_dir / CONSTRAINT_RESULTS_PATH
    if not constraint_path.exists():
        return None
    try:
        return load_constraint_results(project_dir)
    except ConstraintAnalysisError as exc:
        raise ReviewQueueError(str(exc)) from exc


def _load_optional_draft_findings(project_dir: Path) -> dict[str, Any] | None:
    findings_path = project_dir / FINDINGS_PATH
    if not findings_path.exists():
        return None
    try:
        return load_draft_findings(project_dir)
    except FindingGenerationError as exc:
        raise ReviewQueueError(str(exc)) from exc


def _load_optional_comparison_tables(project_dir: Path) -> dict[str, Any] | None:
    tables_path = project_dir / TABLES_PATH
    if not tables_path.exists():
        return None
    try:
        return load_comparison_tables(project_dir)
    except TableGenerationError as exc:
        raise ReviewQueueError(str(exc)) from exc


def _load_optional_map_manifest(project_dir: Path) -> dict[str, Any] | None:
    map_path = project_dir / MAP_MANIFEST_PATH
    if not map_path.exists():
        return None
    try:
        return load_map_manifest(project_dir)
    except MapGenerationError as exc:
        raise ReviewQueueError(str(exc)) from exc


def _load_optional_report_sections(project_dir: Path) -> dict[str, Any] | None:
    sections_path = project_dir / REPORT_SECTIONS_PATH
    if not sections_path.exists():
        return None
    try:
        return load_report_sections(project_dir)
    except ReportSectionGenerationError as exc:
        raise ReviewQueueError(str(exc)) from exc


def _load_existing_queue(project_dir: Path) -> dict[str, Any] | None:
    queue_path = project_dir / REVIEW_QUEUE_PATH
    if not queue_path.exists():
        return None
    return load_review_queue(project_dir)


def _load_or_generate_deliverable_items(project_dir: Path) -> dict[str, Any]:
    try:
        if (project_dir / DELIVERABLE_ITEMS_PATH).exists():
            return load_deliverable_items(project_dir)
        return generate_deliverable_items(project_dir, gpt_drafting=False)
    except DeliverableItemsError as exc:
        raise ReviewQueueError(str(exc)) from exc


def _build_deliverable_review_items(
    *,
    project_id: str,
    now: str,
    deliverable_items: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _deliverable_review_item(project_id, now, deliverable_items, item)
        for item in _dict_list(deliverable_items.get("items", []))
    ]


def _deliverable_review_item(
    project_id: str,
    now: str,
    deliverable_items: dict[str, Any],
    deliverable_item: dict[str, Any],
) -> dict[str, Any]:
    item_id = str(deliverable_item.get("deliverable_item_id") or deliverable_item.get("target_id") or "deliverable-item")
    status = _normalize_status(str(deliverable_item.get("review_status", "draft")))
    extent_metadata = _review_extent_from_deliverable(deliverable_item)
    return _review_item(
        item_id=item_id,
        project_id=project_id,
        item_type=str(deliverable_item.get("review_item_type") or deliverable_item.get("target_type") or "deliverable_item"),
        title=str(deliverable_item.get("title") or item_id),
        generated_content=str(deliverable_item.get("generated_content", "")),
        status=status,
        export_section=str(deliverable_item.get("target_id") or item_id),
        export_group=str(deliverable_item.get("export_group") or "resource_sections"),
        assumptions={
            **(deliverable_item.get("assumptions", {}) if isinstance(deliverable_item.get("assumptions"), dict) else {}),
            "section_order": deliverable_item.get("section_order"),
            "heading_level": deliverable_item.get("heading_level"),
            "resource_category": deliverable_item.get("resource_category"),
            "target_type": deliverable_item.get("target_type"),
            "extent_policy": extent_metadata,
        },
        provenance={
            "artifact": "deliverable_items",
            "artifact_path": deliverable_items.get("output_path"),
            "deliverable_item_id": item_id,
            "target_id": deliverable_item.get("target_id"),
            "deliverable_item_provenance": deliverable_item.get("provenance", {}),
            "extent_policy": extent_metadata,
            "review_before_export": True,
        },
        source_refs=_string_list(deliverable_item.get("source_refs", [])),
        uncertainty_flags=_string_list(deliverable_item.get("uncertainty_flags", [])),
        now=now,
        extra={
            "deliverable_item_id": item_id,
            "target_id": str(deliverable_item.get("target_id") or item_id),
            "section_order": deliverable_item.get("section_order"),
            "heading_level": deliverable_item.get("heading_level"),
            "resource_category": deliverable_item.get("resource_category"),
            "table_id": str(deliverable_item.get("table_id") or ""),
            "figure_id": str(deliverable_item.get("figure_id") or ""),
            "attachment_id": str(deliverable_item.get("attachment_id") or ""),
            "comparison_unit_ids": _string_list(deliverable_item.get("comparison_unit_ids", [])),
            "related_finding_ids": _string_list(deliverable_item.get("related_finding_ids", [])),
            "related_constraint_ids": _string_list(deliverable_item.get("related_constraint_ids", [])),
            "related_table_ids": _string_list(deliverable_item.get("related_table_ids", [])),
            "related_figure_ids": _string_list(deliverable_item.get("related_figure_ids", [])),
            "evidence_refs": _string_list(deliverable_item.get("evidence_refs", [])),
            "validation_issues": _dict_list(deliverable_item.get("validation_issues", [])),
            **extent_metadata,
        },
    )


def _build_legacy_review_items(
    *,
    project_id: str,
    now: str,
    context: dict[str, Any],
    source_status: dict[str, Any],
    source_inventory: dict[str, Any] | None,
    constraints: dict[str, Any] | None,
    spatial: dict[str, Any] | None,
    draft_findings: dict[str, Any] | None,
    comparison_tables: dict[str, Any] | None,
    map_manifest: dict[str, Any] | None,
    report_sections: dict[str, Any] | None,
    include_source_inventory: bool,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if include_source_inventory and source_inventory is not None:
        for record in _dict_list(source_inventory.get("records", [])):
            items.append(_source_inventory_item(project_id, now, source_inventory, record))

    if draft_findings is not None:
        for finding in _dict_list(draft_findings.get("findings", [])):
            items.append(_draft_finding_item(project_id, now, draft_findings, finding))

    if comparison_tables is not None:
        for table in _dict_list(comparison_tables.get("tables", [])):
            items.append(_comparison_table_item(project_id, now, comparison_tables, table))

    if map_manifest is not None:
        for figure in _dict_list(map_manifest.get("figures", [])):
            items.append(_map_figure_item(project_id, now, map_manifest, figure))
        for issue_index, issue in enumerate(_dict_list(map_manifest.get("validation_issues", [])), start=1):
            items.append(_validation_issue_item(project_id, now, "map_generation", issue_index, map_manifest.get("output_path"), issue))

    if report_sections is not None:
        for section in _dict_list(report_sections.get("sections", [])):
            items.append(_report_section_item(project_id, now, report_sections, section))
        for issue_index, issue in enumerate(_dict_list(report_sections.get("validation_issues", [])), start=1):
            items.append(
                _validation_issue_item(project_id, now, "report_sections", issue_index, report_sections.get("output_path"), issue)
            )

    for status_record in _dict_list(source_status.get("statuses", [])):
        if status_record.get("status") in MISSING_DATA_STATUSES:
            items.append(_missing_data_item(project_id, now, source_status, status_record))

    for issue_index, issue in enumerate(_dict_list(context.get("validation_issues", [])), start=1):
        items.append(_validation_issue_item(project_id, now, "project_context", issue_index, context.get("context_path"), issue))

    for issue_index, issue in enumerate(_dict_list(source_status.get("validation_issues", [])), start=1):
        items.append(_validation_issue_item(project_id, now, "source_status", issue_index, source_status.get("output_path"), issue))

    if constraints is not None:
        for source in _dict_list(constraints.get("sources", [])):
            for issue_index, issue in enumerate(_dict_list(source.get("validation_issues", [])), start=1):
                origin = f"constraint_source_{_slug(str(source.get('source_id', 'source')))}"
                items.append(_validation_issue_item(project_id, now, origin, issue_index, constraints.get("output_path"), issue))
        for issue_index, issue in enumerate(_dict_list(constraints.get("validation_issues", [])), start=1):
            items.append(_validation_issue_item(project_id, now, "constraint_analysis", issue_index, constraints.get("output_path"), issue))

    if spatial is not None and constraints is None:
        for relationship in _dict_list(spatial.get("relationships", [])):
            items.append(_spatial_relationship_item(project_id, now, spatial, relationship))
        for source in _dict_list(spatial.get("sources", [])):
            if source.get("status") == "analyzed" and _int_count(source.get("relationship_count", 0)) == 0:
                items.append(_no_mapped_relationships_item(project_id, now, spatial, source))
            for issue_index, issue in enumerate(_dict_list(source.get("validation_issues", [])), start=1):
                origin = f"spatial_source_{_slug(str(source.get('source_id', 'source')))}"
                items.append(_validation_issue_item(project_id, now, origin, issue_index, spatial.get("output_path"), issue))
        for issue_index, issue in enumerate(_dict_list(spatial.get("validation_issues", [])), start=1):
            items.append(_validation_issue_item(project_id, now, "spatial_analysis", issue_index, spatial.get("output_path"), issue))

    return items


def _source_inventory_item(
    project_id: str,
    now: str,
    source_inventory: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    source_id = str(record.get("source_id", "unknown_source"))
    source_status = record.get("source_status", {}) if isinstance(record.get("source_status"), dict) else {}
    category_status = str(source_status.get("category_status", "needs_review"))
    validation_issues = record.get("validation_issues", [])
    status = "needs_review" if validation_issues or category_status in MISSING_DATA_STATUSES else "draft"
    if category_status in {"gated", "stubbed"}:
        status = "needs_verification"
    source_name = str(record.get("name") or source_id)
    publisher = str(record.get("publisher") or "")
    return _review_item(
        item_id=f"source-inventory-{_slug(source_id)}",
        project_id=project_id,
        item_type="source_inventory_note",
        title=f"Source inventory: {source_name}",
        generated_content=(
            f"Source '{source_name}' is cataloged under '{record.get('category', '')}' with status "
            f"'{category_status}'. Publisher: {publisher or 'not specified'}."
        ),
        status=status,
        export_section="source_inventory",
        export_group="methodology",
        assumptions={
            "category_status": category_status,
            "project_registry": record.get("project_registry", {}),
            "local_metadata": record.get("local_metadata", {}),
            "metadata": record.get("metadata", {}),
        },
        provenance={
            "artifact": "source_inventory",
            "artifact_path": source_inventory.get("output_path"),
            "source_id": source_id,
            "source_inventory_record": record,
        },
        source_refs=[source_id],
        uncertainty_flags=_string_list(record.get("uncertainty_flags", [])),
        now=now,
    )


def _draft_finding_item(
    project_id: str,
    now: str,
    draft_findings: dict[str, Any],
    finding: dict[str, Any],
) -> dict[str, Any]:
    finding_id = str(finding.get("finding_id", "finding"))
    summary = str(finding.get("summary", "")).strip()
    details = str(finding.get("details", "")).strip()
    implication = str(finding.get("implication", "")).strip()
    content_parts = [part for part in (summary, details, f"Implication: {implication}" if implication else "") if part]
    status = str(finding.get("review_status", "draft"))
    if status not in SUPPORTED_STATUSES:
        status = "needs_review"
    return _review_item(
        item_id=f"draft-finding-{_slug(finding_id)}",
        project_id=project_id,
        item_type="draft_finding",
        title=str(finding.get("title") or finding_id),
        generated_content="\n\n".join(content_parts),
        status=status,
        export_section=str(finding.get("resource_category", "findings")),
        export_group="constraints_inventory",
        assumptions=dict(finding.get("assumptions", {})) if isinstance(finding.get("assumptions"), dict) else {},
        provenance={
            "artifact": "draft_findings",
            "artifact_path": draft_findings.get("output_path"),
            "finding_id": finding_id,
            "finding_type": finding.get("type"),
            "evidence_class": finding.get("evidence_class"),
            "data_authenticity": _nested_string(finding.get("provenance", {}), "data_authenticity") or _finding_data_authenticity(finding),
            "finding_provenance": finding.get("provenance", {}),
        },
        source_refs=_string_list(finding.get("source_ids", [])),
        uncertainty_flags=_string_list(finding.get("uncertainty_flags", [])),
        now=now,
        extra={
            "finding_id": finding_id,
            "related_record_ids": _string_list(finding.get("related_record_ids", [])),
        },
    )


def _comparison_table_item(
    project_id: str,
    now: str,
    comparison_tables: dict[str, Any],
    table: dict[str, Any],
) -> dict[str, Any]:
    table_id = str(table.get("table_id", "table"))
    row_count = _int_count(table.get("row_count", 0))
    title = str(table.get("title") or table_id)
    status = str(table.get("review_status", "draft"))
    if status not in SUPPORTED_STATUSES:
        status = "needs_review"
    return _review_item(
        item_id=f"comparison-table-{_slug(table_id)}",
        project_id=project_id,
        item_type="comparison_table",
        title=title,
        generated_content=(
            f"Generated descriptive comparison table '{title}' with {row_count} rows. "
            "This table does not rank alternatives or identify a preferred option."
        ),
        status=status,
        export_section="tables",
        export_group="constraints_inventory",
        assumptions={"description": table.get("description", "")},
        provenance={
            "artifact": "comparison_tables",
            "artifact_path": comparison_tables.get("output_path"),
            "table_id": table_id,
            "table_type": table.get("type"),
            "table_provenance": table.get("provenance", {}),
        },
        source_refs=_string_list(table.get("source_refs", [])),
        uncertainty_flags=_string_list(table.get("uncertainty_flags", [])),
        now=now,
        extra={
            "table_id": table_id,
            "columns": _string_list(table.get("columns", [])),
            "row_count": row_count,
            "rows_preview": table.get("rows", [])[:5] if isinstance(table.get("rows", []), list) else [],
        },
    )


def _map_figure_item(
    project_id: str,
    now: str,
    map_manifest: dict[str, Any],
    figure: dict[str, Any],
) -> dict[str, Any]:
    figure_id = str(figure.get("figure_id", "figure"))
    title = str(figure.get("title") or figure_id)
    status = str(figure.get("review_status", "draft"))
    if status not in SUPPORTED_STATUSES:
        status = "needs_review"
    return _review_item(
        item_id=f"map-figure-{_slug(figure_id)}",
        project_id=project_id,
        item_type="map_figure",
        title=title,
        generated_content=(
            f"Generated draft map figure '{title}' as a vector-only PNG. "
            "Review visible layers, labels, source notes, and cartographic fit before export."
        ),
        status=status,
        export_section="maps",
        export_group="constraints_inventory",
        assumptions={
            "figure_type": figure.get("type"),
            "figure_group": figure.get("figure_group"),
            "shown_layers": figure.get("shown_layers", []),
            "map_elements": figure.get("map_elements", []),
            "draft_pre_review": True,
        },
        provenance={
            "artifact": "map_manifest",
            "artifact_path": map_manifest.get("output_path"),
            "figure_id": figure_id,
            "figure_provenance": figure.get("provenance", {}),
        },
        source_refs=_string_list(figure.get("source_refs", [])),
        uncertainty_flags=_string_list(figure.get("uncertainty_flags", [])),
        now=now,
        extra={
            "figure_id": figure_id,
            "image_path": figure.get("image_path"),
            "figure_type": figure.get("type"),
            "caption": figure.get("caption"),
            "source_note": figure.get("source_note"),
            "method_note": figure.get("method_note"),
            "map_elements": figure.get("map_elements", []),
            "figure_group": figure.get("figure_group"),
            "related_resource_categories": figure.get("related_resource_categories", []),
            "shown_layers": figure.get("shown_layers", []),
        },
    )


def _report_section_item(
    project_id: str,
    now: str,
    report_sections: dict[str, Any],
    section: dict[str, Any],
) -> dict[str, Any]:
    section_id = str(section.get("section_id", "section"))
    title = str(section.get("title") or section_id)
    status = str(section.get("review_status", "draft"))
    if status not in SUPPORTED_STATUSES:
        status = "needs_review"
    return _review_item(
        item_id=f"report-section-{_slug(section_id)}",
        project_id=project_id,
        item_type="report_section",
        title=title,
        generated_content=str(section.get("generated_content", "")),
        status=status,
        export_section="report_sections",
        export_group=str(section.get("export_group") or _default_export_group("report_section", str(section.get("resource_category", "")))),
        assumptions={
            "section_order": section.get("section_order"),
            "export_group": section.get("export_group"),
            "resource_category": section.get("resource_category"),
            "visual_slots": section.get("visual_slots", []),
            "table_slots": section.get("table_slots", []),
            "section_assumptions": section.get("assumptions", {}),
        },
        provenance={
            "artifact": "report_sections",
            "artifact_path": report_sections.get("output_path"),
            "section_id": section_id,
            "section_type": section.get("type"),
            "section_provenance": section.get("provenance", {}),
        },
        source_refs=_string_list(section.get("source_refs", [])),
        uncertainty_flags=_string_list(section.get("uncertainty_flags", [])),
        now=now,
        extra={
            "section_id": section_id,
            "section_order": section.get("section_order"),
            "resource_category": section.get("resource_category"),
            "related_finding_ids": _string_list(section.get("related_finding_ids", [])),
            "related_table_ids": _string_list(section.get("related_table_ids", [])),
            "related_figure_ids": _string_list(section.get("related_figure_ids", [])),
        },
    )


def _missing_data_item(
    project_id: str,
    now: str,
    source_status: dict[str, Any],
    status_record: dict[str, Any],
) -> dict[str, Any]:
    category = str(status_record.get("category", "unknown_category"))
    source_state = str(status_record.get("status", "needs_review"))
    item_status = "needs_verification" if source_state in {"gated", "stubbed"} else "needs_review"
    return _review_item(
        item_id=f"missing-data-{_slug(category)}",
        project_id=project_id,
        item_type="missing_data_placeholder",
        title=f"Review required: {category}",
        generated_content=(
            f"Source category '{category}' is not ready for direct use and has status '{source_state}'. "
            "Reviewer confirmation or additional source material may be required before export."
        ),
        status=item_status,
        export_section="assumptions_caveats",
        export_group="methodology",
        assumptions={"source_status": source_state, "requirement": status_record.get("requirement")},
        provenance={
            "artifact": "source_status_set",
            "artifact_path": source_status.get("output_path"),
            "category": category,
            "source_status": source_state,
            "data_authenticity": "stub",
        },
        source_refs=_string_list(status_record.get("source_ids", [])),
        uncertainty_flags=_string_list(status_record.get("uncertainty_flags", [])),
        now=now,
    )


def _spatial_relationship_item(
    project_id: str,
    now: str,
    spatial: dict[str, Any],
    relationship: dict[str, Any],
) -> dict[str, Any]:
    relationship_id = str(relationship.get("relationship_id", _slug(str(len(spatial.get("relationships", []))))))
    source_name = str(relationship.get("source_name", "source layer"))
    spatial_relationship = str(relationship.get("spatial_relationship", "relationship"))
    project_label = str(relationship.get("project_feature_label") or relationship.get("project_feature_index", "project feature"))
    source_label = str(relationship.get("source_feature_label") or relationship.get("source_feature_index", "source feature"))
    return _review_item(
        item_id=f"spatial-relationship-{_slug(relationship_id)}",
        project_id=project_id,
        item_type="spatial_relationship",
        title=f"Spatial relationship: {spatial_relationship} with {source_name}",
        generated_content=(
            f"Detected '{spatial_relationship}' between project feature '{project_label}' and "
            f"source feature '{source_label}' from {source_name}."
        ),
        status="draft",
        export_section=str(relationship.get("source_category", "spatial_relationships")),
        export_group="constraints_inventory",
        assumptions={
            "buffer_feet": relationship.get("buffer_feet"),
            "measurements": relationship.get("measurements", {}),
        },
        provenance={
            "artifact": "spatial_relationships",
            "artifact_path": spatial.get("output_path"),
            "relationship_id": relationship_id,
            "method": relationship.get("method"),
            "analysis_crs": relationship.get("analysis_crs"),
            "spatial_relationship": spatial_relationship,
        },
        source_refs=[str(relationship.get("source_id", ""))] if relationship.get("source_id") else [],
        uncertainty_flags=[],
        now=now,
    )


def _no_mapped_relationships_item(
    project_id: str,
    now: str,
    spatial: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    source_id = str(source.get("source_id", "unknown_source"))
    source_name = str(source.get("source_name", source_id))
    return _review_item(
        item_id=f"no-mapped-relationships-{_slug(source_id)}",
        project_id=project_id,
        item_type="no_mapped_relationships",
        title=f"No mapped relationships: {source_name}",
        generated_content=(
            f"No mapped spatial relationships were identified for analyzed source '{source_name}' "
            "within the configured project review buffer."
        ),
        status="draft",
        export_section=str(source.get("source_category", "spatial_relationships")),
        export_group="constraints_inventory",
        assumptions={"buffer_feet": source.get("buffer_feet")},
        provenance={
            "artifact": "spatial_relationships",
            "artifact_path": spatial.get("output_path"),
            "source_id": source_id,
            "method": "geopandas_shapely_local_spatial_check",
            "analysis_crs": source.get("analysis_crs"),
        },
        source_refs=[source_id],
        uncertainty_flags=[],
        now=now,
    )


def _validation_issue_item(
    project_id: str,
    now: str,
    origin: str,
    issue_index: int,
    artifact_path: Any,
    issue: dict[str, Any],
) -> dict[str, Any]:
    code = str(issue.get("code", "validation_issue"))
    message = str(issue.get("message", "Validation issue requires review."))
    return _review_item(
        item_id=f"validation-{_slug(origin)}-{issue_index:03d}-{_slug(code)}",
        project_id=project_id,
        item_type="validation_issue",
        title=f"Validation issue: {code}",
        generated_content=message,
        status="needs_review",
        export_section="review_notes",
        export_group="attachments",
        assumptions={},
        provenance={
            "artifact": origin,
            "artifact_path": artifact_path,
            "issue": issue,
        },
        source_refs=[str(issue["source_id"])] if issue.get("source_id") else [],
        uncertainty_flags=[code],
        now=now,
    )


def _review_item(
    *,
    item_id: str,
    project_id: str,
    item_type: str,
    title: str,
    generated_content: str,
    status: str,
    export_section: str,
    export_group: str | None,
    assumptions: dict[str, Any],
    provenance: dict[str, Any],
    source_refs: list[str],
    uncertainty_flags: list[str],
    now: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra = dict(extra or {})
    status = _normalize_status(status)
    extent_metadata = _review_item_extent_metadata(
        item_id=item_id,
        item_type=item_type,
        assumptions=assumptions,
        provenance=provenance,
        extra=extra,
    )
    item = {
        "id": item_id,
        "project_id": project_id,
        "type": item_type,
        "deliverable_item_id": str(extra.get("deliverable_item_id", "")),
        "target_id": str(extra.get("target_id", "")),
        "title": title,
        "generated_content": generated_content,
        "edited_content": "",
        "replacement_content": "",
        "status": status,
        "export_eligible": _default_export_eligible(status),
        "export_section": export_section,
        "export_group": export_group or _default_export_group(item_type, export_section),
        "section_order": extra.get("section_order"),
        "heading_level": extra.get("heading_level"),
        "table_id": str(extra.get("table_id", "")),
        "figure_id": str(extra.get("figure_id", "")),
        "attachment_id": str(extra.get("attachment_id", "")),
        "comparison_unit_ids": _string_list(extra.get("comparison_unit_ids", [])),
        "related_finding_ids": _string_list(extra.get("related_finding_ids", [])),
        "related_constraint_ids": _string_list(extra.get("related_constraint_ids", [])),
        "related_table_ids": _string_list(extra.get("related_table_ids", [])),
        "related_figure_ids": _string_list(extra.get("related_figure_ids", [])),
        "evidence_refs": _string_list(extra.get("evidence_refs", [])),
        "assumptions": assumptions,
        "provenance": provenance,
        "source_refs": source_refs,
        "uncertainty_flags": uncertainty_flags,
        "reviewer_notes": [],
        "validation_issues": _dict_list(extra.get("validation_issues", [])),
        "created_at": now,
        "updated_at": now,
    }
    item = apply_extent_metadata(item, extent_metadata)
    for key, value in extra.items():
        if key not in item:
            item[key] = value
    return item


def _review_extent_from_deliverable(deliverable_item: dict[str, Any]) -> dict[str, Any]:
    records = [{field: deliverable_item[field] for field in EXTENT_FIELD_NAMES if field in deliverable_item}]
    provenance = deliverable_item.get("provenance", {})
    assumptions = deliverable_item.get("assumptions", {})
    if isinstance(provenance, dict) and isinstance(provenance.get("extent_policy"), dict):
        records.append(provenance["extent_policy"])
    if isinstance(assumptions, dict) and isinstance(assumptions.get("extent_policy"), dict):
        records.append(assumptions["extent_policy"])
    fallback = target_extent_metadata(
        target_id=str(deliverable_item.get("target_id") or deliverable_item.get("deliverable_item_id") or ""),
        target_type=str(deliverable_item.get("target_type") or deliverable_item.get("review_item_type") or ""),
        resource_category=str(deliverable_item.get("resource_category") or ""),
    )
    return merge_extent_metadata(records, fallback=fallback)


def _review_item_extent_metadata(
    *,
    item_id: str,
    item_type: str,
    assumptions: dict[str, Any],
    provenance: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    records = [{field: extra[field] for field in EXTENT_FIELD_NAMES if field in extra}]
    if isinstance(assumptions.get("extent_policy"), dict):
        records.append(assumptions["extent_policy"])
    if isinstance(provenance.get("extent_policy"), dict):
        records.append(provenance["extent_policy"])
    fallback = target_extent_metadata(
        target_id=str(extra.get("target_id") or item_id),
        target_type=str(extra.get("target_type") or item_type),
        resource_category=str(extra.get("resource_category") or ""),
    )
    return merge_extent_metadata(records, fallback=fallback)


def _existing_item_lookup(queue: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in _dict_list(queue.get("items", [])):
        for key in (
            str(item.get("id", "")),
            str(item.get("deliverable_item_id", "")),
            str(item.get("target_id", "")),
        ):
            if key and key not in lookup:
                lookup[key] = item
    return lookup


def _merge_existing_review_state(item: dict[str, Any], existing_items: dict[str, dict[str, Any]], now: str) -> dict[str, Any]:
    existing = (
        existing_items.get(str(item.get("id", "")))
        or existing_items.get(str(item.get("deliverable_item_id", "")))
        or existing_items.get(str(item.get("target_id", "")))
    )
    if existing is None:
        return item
    item["created_at"] = existing.get("created_at", item["created_at"])
    if _should_preserve_existing_review_state(existing, item):
        item["status"] = _normalize_status(existing.get("status", item["status"]))
        item["export_eligible"] = bool(existing.get("export_eligible", item["export_eligible"]))
        item["edited_content"] = str(existing.get("edited_content", ""))
        item["replacement_content"] = str(existing.get("replacement_content", ""))
        item["reviewer_notes"] = existing.get("reviewer_notes", []) if isinstance(existing.get("reviewer_notes"), list) else []
        if item["status"] == "replaced" and not item["replacement_content"].strip():
            item["export_eligible"] = False
            item["validation_issues"] = _with_replacement_issue(_dict_list(item.get("validation_issues", [])), item["id"])
        else:
            item["validation_issues"] = _without_replacement_issue(_dict_list(item.get("validation_issues", [])))
    item["updated_at"] = now
    return item


def _should_preserve_existing_review_state(existing: dict[str, Any], regenerated: dict[str, Any]) -> bool:
    if existing.get("reviewer_notes"):
        return True
    if str(existing.get("edited_content", "")).strip():
        return True
    if str(existing.get("replacement_content", "")).strip():
        return True
    if existing.get("export_eligible") is True:
        return True
    existing_status = _normalize_status(existing.get("status", ""))
    regenerated_status = str(regenerated.get("status", ""))
    if existing_status in {"accepted", "edited", "replaced", "declined", "unable_to_verify"}:
        return True
    if existing_status == "needs_verification" and regenerated_status in {"draft", "needs_review"}:
        return True
    if existing_status == "needs_review" and regenerated_status == "draft":
        return True
    return False


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    for item in queue["items"]:
        identifiers = {
            str(item.get("id", "")),
            str(item.get("deliverable_item_id", "")),
            str(item.get("target_id", "")),
        }
        if item_id in identifiers:
            return item
    raise ReviewQueueError(f"Review item not found: {item_id}")


def _validate_queue(queue: dict[str, Any]) -> None:
    if not isinstance(queue, dict):
        raise ReviewQueueError("Review queue must be a JSON object.")
    items = queue.get("items")
    if not isinstance(items, list):
        raise ReviewQueueError("Review queue requires an 'items' list.")
    if queue.get("item_count") != len(items):
        raise ReviewQueueError("Review queue item_count does not match items.")
    if not isinstance(queue.get("validation_issues", []), list):
        raise ReviewQueueError("Review queue validation_issues must be a list.")
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ReviewQueueError("Each review queue item must be an object.")
        missing = sorted(REQUIRED_ITEM_FIELDS - set(item))
        if missing:
            raise ReviewQueueError(f"Review item is missing required fields: {missing}")
        item_id = item["id"]
        if not isinstance(item_id, str) or not item_id.strip():
            raise ReviewQueueError("Review item requires a non-empty string id.")
        if item_id in seen_ids:
            raise ReviewQueueError(f"Duplicate review item id: {item_id}")
        seen_ids.add(item_id)
        status = item["status"]
        if status not in SUPPORTED_STATUSES:
            raise ReviewQueueError(f"Unsupported review status '{status}' for item '{item_id}'.")
        if not isinstance(item["export_eligible"], bool):
            raise ReviewQueueError(f"Review item '{item_id}' export_eligible must be true or false.")
        if item["export_eligible"] and status not in EXPORT_TRUE_STATUSES:
            raise ReviewQueueError(f"Review item '{item_id}' cannot be export eligible with status '{status}'.")
        if status == "replaced" and not str(item.get("replacement_content", "")).strip() and item["export_eligible"]:
            raise ReviewQueueError(f"Review item '{item_id}' cannot be export eligible as replaced without replacement_content.")
        if not isinstance(item["export_group"], str) or not item["export_group"].strip():
            raise ReviewQueueError(f"Review item '{item_id}' export_group must be a non-empty string.")
        if not isinstance(item["reviewer_notes"], list):
            raise ReviewQueueError(f"Review item '{item_id}' reviewer_notes must be a list.")
        if not isinstance(item["comparison_unit_ids"], list):
            raise ReviewQueueError(f"Review item '{item_id}' comparison_unit_ids must be a list.")
        if not isinstance(item["related_finding_ids"], list):
            raise ReviewQueueError(f"Review item '{item_id}' related_finding_ids must be a list.")
        if not isinstance(item["related_constraint_ids"], list):
            raise ReviewQueueError(f"Review item '{item_id}' related_constraint_ids must be a list.")
        if not isinstance(item["related_table_ids"], list):
            raise ReviewQueueError(f"Review item '{item_id}' related_table_ids must be a list.")
        if not isinstance(item["related_figure_ids"], list):
            raise ReviewQueueError(f"Review item '{item_id}' related_figure_ids must be a list.")
        if not isinstance(item["evidence_refs"], list):
            raise ReviewQueueError(f"Review item '{item_id}' evidence_refs must be a list.")
        if not isinstance(item["validation_issues"], list):
            raise ReviewQueueError(f"Review item '{item_id}' validation_issues must be a list.")


def _normalize_queue_compat(queue: Any) -> None:
    if not isinstance(queue, dict):
        return
    queue.setdefault("validation_issues", [])
    queue.setdefault("queue_mode", "legacy_audit")
    items = queue.get("items")
    if not isinstance(items, list):
        return
    queue["item_count"] = len(items)
    for item in items:
        if not isinstance(item, dict):
            continue
        item["status"] = _normalize_status(item.get("status", "draft"))
        if not isinstance(item.get("export_group"), str) or not str(item.get("export_group")).strip():
            item["export_group"] = _default_export_group(str(item.get("type", "")), str(item.get("export_section", "")))
        item.setdefault("deliverable_item_id", "")
        item.setdefault("target_id", item.get("deliverable_item_id") or "")
        item.setdefault("replacement_content", "")
        item.setdefault("section_order", None)
        item.setdefault("heading_level", None)
        item.setdefault("table_id", "")
        item.setdefault("figure_id", "")
        item.setdefault("attachment_id", "")
        item.setdefault("comparison_unit_ids", [])
        item.setdefault("related_finding_ids", [])
        item.setdefault("related_constraint_ids", [])
        item.setdefault("related_table_ids", [])
        item.setdefault("related_figure_ids", [])
        item.setdefault("evidence_refs", [])
        item.setdefault("validation_issues", [])
        item.setdefault("edited_content", "")
        item.setdefault("reviewer_notes", [])
        extent = _review_item_extent_metadata(
            item_id=str(item.get("id") or ""),
            item_type=str(item.get("type") or ""),
            assumptions=item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {},
            provenance=item.get("provenance", {}) if isinstance(item.get("provenance"), dict) else {},
            extra=item,
        )
        apply_extent_metadata(item, extent)


def _default_export_eligible(status: str) -> bool:
    return status in {"accepted", "edited", "replaced"}


def _default_export_group(item_type: str, export_section: str) -> str:
    if export_section in {
        "front_matter",
        "executive_summary",
        "introduction",
        "methodology",
        "constraints_inventory",
        "resource_sections",
        "conclusion",
        "attachments",
    }:
        return export_section
    if item_type in {"map_figure", "comparison_table", "draft_finding", "spatial_relationship", "no_mapped_relationships", "figure", "table"}:
        return "constraints_inventory"
    if item_type in {"source_inventory_note", "source_status_note", "missing_data_placeholder"}:
        return "methodology"
    if item_type == "validation_issue":
        return "attachments"
    return "resource_sections"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalize_status(value: Any) -> str:
    status = str(value or "draft")
    if status == "rejected":
        return "declined"
    return status


def _queue_validation_issues(items: list[dict[str, Any]], existing: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    issues = [issue for issue in _dict_list(existing or []) if issue.get("code") != "replacement_content_missing"]
    for item in items:
        issues.extend(_dict_list(item.get("validation_issues", [])))
        if item.get("status") == "replaced" and not str(item.get("replacement_content", "")).strip():
            issues.append(_replacement_issue(str(item.get("id", ""))))
    return _dedupe_issues(issues)


def _with_replacement_issue(issues: list[dict[str, Any]], item_id: str) -> list[dict[str, Any]]:
    return _dedupe_issues([*_without_replacement_issue(issues), _replacement_issue(item_id)])


def _without_replacement_issue(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [issue for issue in issues if issue.get("code") != "replacement_content_missing"]


def _replacement_issue(item_id: str) -> dict[str, str]:
    return {
        "severity": "warning",
        "code": "replacement_content_missing",
        "message": f"Review item '{item_id}' is marked replaced but has no replacement_content.",
        "location": str(REVIEW_QUEUE_PATH),
        "item_id": item_id,
    }


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        key = (
            str(issue.get("code", "")),
            str(issue.get("location", "")),
            str(issue.get("message", "")),
            str(issue.get("item_id", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result


def _nested_string(value: Any, key: str) -> str:
    if not isinstance(value, dict):
        return ""
    item = value.get(key)
    return str(item) if isinstance(item, str) and item.strip() else ""


def _nested_value(value: Any, parent_key: str, child_key: str) -> Any:
    if not isinstance(value, dict):
        return None
    parent = value.get(parent_key)
    if not isinstance(parent, dict):
        return None
    return parent.get(child_key)


def _finding_data_authenticity(finding: dict[str, Any]) -> str:
    if str(finding.get("type", "")) == "source_unavailable_or_deferred":
        return "stub"
    if finding.get("source_ids"):
        return "real"
    return "unknown"


def _int_count(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
