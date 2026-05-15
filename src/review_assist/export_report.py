"""Editable report export package generation from reviewed queue items."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .review_queue import ReviewQueueError, generate_review_queue, load_review_queue
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set


EXPORT_DIR = Path("exports")
EXPORT_MANIFEST_PATH = EXPORT_DIR / "export_manifest.json"
EXPORT_MARKDOWN_PATH = EXPORT_DIR / "environmental_constraints_report.md"

EXPORT_GROUP_ORDER = [
    "front_matter",
    "executive_summary",
    "introduction",
    "methodology",
    "constraints_inventory",
    "resource_sections",
    "conclusion",
    "attachments",
]
EXPORT_GROUP_TITLES = {
    "front_matter": "Front Matter",
    "executive_summary": "Executive Summary",
    "introduction": "Introduction",
    "methodology": "Methodology",
    "constraints_inventory": "Environmental Constraints Inventory",
    "resource_sections": "Resource Sections",
    "conclusion": "Conclusion and Next Steps",
    "attachments": "Attachments",
}
UNRESOLVED_REQUIRED_SOURCE_STATUSES = {"missing", "downloadable", "needs_review", "gated", "stubbed", "failed"}


class ExportReportError(RuntimeError):
    """Raised when editable report export generation cannot complete."""


def export_report(project_dir: Path, *, include_draft: bool = False) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        queue = _load_or_generate_queue(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
    except (ReviewQueueError, SourceStatusError) as exc:
        raise ExportReportError(str(exc)) from exc

    output_dir = project_dir / EXPORT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = project_dir / EXPORT_MARKDOWN_PATH
    manifest_path = project_dir / EXPORT_MANIFEST_PATH
    now = _utc_now()

    items = _dict_list(queue.get("items", []))
    included, skipped = _partition_export_items(items, include_draft=include_draft)
    included = sorted(included, key=_export_sort_key)
    validation_issues = _export_validation_issues(included, source_status, include_draft=include_draft)

    markdown = _markdown_report(
        queue=queue,
        included=included,
        validation_issues=validation_issues,
        include_draft=include_draft,
    )
    markdown_path.write_text(markdown, encoding="utf-8")

    manifest = {
        "project_id": queue.get("project_id"),
        "project_name": queue.get("project_name"),
        "project_dir": str(project_dir),
        "created_at": now,
        "include_draft": include_draft,
        "review_queue_path": queue.get("output_path"),
        "source_status_path": source_status.get("output_path"),
        "markdown_path": str(markdown_path),
        "included_count": len(included),
        "skipped_count": len(skipped),
        "status_counts": dict(Counter(str(item.get("status", "")) for item in items)),
        "included_status_counts": dict(Counter(item["status"] for item in included)),
        "skipped_status_counts": dict(Counter(item["status"] for item in skipped)),
        "included_type_counts": dict(Counter(item["type"] for item in included)),
        "skipped_type_counts": dict(Counter(item["type"] for item in skipped)),
        "included_items": included,
        "skipped_items": skipped,
        "validation_issues": validation_issues,
        "output_path": str(manifest_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _load_or_generate_queue(project_dir: Path) -> dict[str, Any]:
    try:
        return load_review_queue(project_dir)
    except ReviewQueueError:
        return generate_review_queue(project_dir)


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


def _include_item(item: dict[str, Any], *, include_draft: bool) -> bool:
    status = str(item.get("status", ""))
    if include_draft:
        return status != "rejected"
    if status in {"accepted", "edited"}:
        return bool(item.get("export_eligible", False))
    if status == "unable_to_verify":
        return bool(item.get("export_eligible", False))
    return False


def _partition_export_items(
    items: list[dict[str, Any]],
    *,
    include_draft: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for item in items:
        if _include_item(item, include_draft=include_draft):
            included.append(_export_item(item))
        else:
            skipped.append(_skipped_item(item, include_draft=include_draft))
    return included, skipped


def _export_item(item: dict[str, Any]) -> dict[str, Any]:
    content = str(item.get("edited_content") or "").strip() or str(item.get("generated_content") or "").strip()
    assumptions = item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {}
    provenance = item.get("provenance", {}) if isinstance(item.get("provenance"), dict) else {}
    return {
        "id": str(item.get("id", "")),
        "type": str(item.get("type", "")),
        "title": str(item.get("title", "")),
        "status": str(item.get("status", "")),
        "export_group": str(item.get("export_group") or _default_export_group(item)),
        "export_section": str(item.get("export_section", "")),
        "section_order": _optional_int(item.get("section_order") or assumptions.get("section_order")),
        "content": content,
        "content_source": "edited_content" if str(item.get("edited_content") or "").strip() else "generated_content",
        "source_refs": _string_list(item.get("source_refs", [])),
        "uncertainty_flags": _string_list(item.get("uncertainty_flags", [])),
        "visual_slots": _string_list(assumptions.get("visual_slots", [])),
        "table_slots": _string_list(assumptions.get("table_slots", [])),
        "related_figure_ids": _string_list(item.get("related_figure_ids", [])),
        "related_table_ids": _string_list(item.get("related_table_ids", [])),
        "image_path": item.get("image_path"),
        "table_id": item.get("table_id"),
        "row_count": item.get("row_count"),
        "artifact_path": provenance.get("artifact_path"),
        "provenance": provenance,
    }


def _skipped_item(item: dict[str, Any], *, include_draft: bool) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")),
        "type": str(item.get("type", "")),
        "title": str(item.get("title", "")),
        "status": str(item.get("status", "")),
        "export_group": str(item.get("export_group") or _default_export_group(item)),
        "reason": _skip_reason(item, include_draft=include_draft),
    }


def _skip_reason(item: dict[str, Any], *, include_draft: bool) -> str:
    status = str(item.get("status", ""))
    if include_draft and status == "rejected":
        return "rejected"
    if status in {"accepted", "edited", "unable_to_verify"} and not item.get("export_eligible", False):
        return "not_export_eligible"
    return f"status_{status or 'unknown'}"


def _export_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    group = str(item.get("export_group", ""))
    group_index = EXPORT_GROUP_ORDER.index(group) if group in EXPORT_GROUP_ORDER else len(EXPORT_GROUP_ORDER)
    item_type = str(item.get("type", ""))
    type_index = 0 if item_type == "report_section" else 1
    section_order = item.get("section_order")
    order = int(section_order) if isinstance(section_order, int) else 9999
    return (group_index, type_index, order, str(item.get("title", "")))


def _export_validation_issues(
    included: list[dict[str, Any]],
    source_status: dict[str, Any],
    *,
    include_draft: bool,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not include_draft and not any(item["type"] == "report_section" for item in included):
        issues.append(_issue("warning", "no_accepted_report_sections", "No accepted or edited report sections were available for export."))
    if not include_draft and not any(item["type"] == "map_figure" for item in included):
        issues.append(_issue("warning", "no_accepted_maps", "No accepted or edited map figures were available for export."))
    unresolved = [
        item
        for item in _dict_list(source_status.get("statuses", []))
        if item.get("requirement") == "required" and str(item.get("status")) in UNRESOLVED_REQUIRED_SOURCE_STATUSES
    ]
    if unresolved:
        categories = ", ".join(str(item.get("category")) for item in unresolved)
        issues.append(
            _issue(
                "warning",
                "unresolved_required_source_gaps",
                f"Required source categories remain unresolved or require review: {categories}.",
            )
        )
    return issues


def _markdown_report(
    *,
    queue: dict[str, Any],
    included: list[dict[str, Any]],
    validation_issues: list[dict[str, Any]],
    include_draft: bool,
) -> str:
    lines = [
        f"# {queue.get('project_name', 'Environmental Constraints Report')}",
        "",
        "Environmental Constraints Report",
        "",
    ]
    if include_draft:
        lines.extend(
            [
                "> INTERNAL PREVIEW EXPORT: this file includes draft or unaccepted review queue items and is not ready for external use.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "> Reviewed-content export: this file includes only accepted, edited, or explicitly export-eligible reviewed items.",
                "",
            ]
        )
    if validation_issues:
        lines.append("## Export Caveats")
        lines.extend(f"- {issue.get('code')}: {issue.get('message')}" for issue in validation_issues)
        lines.append("")
    if not included:
        lines.extend(["## No Exported Content", "", "No review queue items met the export criteria.", ""])
        return "\n".join(lines)

    current_group = ""
    for item in included:
        group = str(item.get("export_group", "resource_sections"))
        if group != current_group:
            current_group = group
            lines.extend([f"## {EXPORT_GROUP_TITLES.get(group, group.replace('_', ' ').title())}", ""])
        lines.extend(_markdown_item(item))
    return "\n".join(lines).rstrip() + "\n"


def _markdown_item(item: dict[str, Any]) -> list[str]:
    lines = [f"### {item.get('title')}", ""]
    content = str(item.get("content", "")).strip()
    if content:
        lines.extend([content, ""])
    if item.get("type") == "map_figure" and item.get("image_path"):
        lines.extend([f"Map file: `{item['image_path']}`", ""])
    if item.get("type") == "comparison_table":
        details = []
        if item.get("table_id"):
            details.append(f"table id `{item['table_id']}`")
        if item.get("row_count") is not None:
            details.append(f"{item['row_count']} row(s)")
        if item.get("artifact_path"):
            details.append(f"artifact `{item['artifact_path']}`")
        if details:
            lines.extend([f"Table reference: {', '.join(details)}.", ""])
    visual_slots = _string_list(item.get("visual_slots", []))
    related_figures = _string_list(item.get("related_figure_ids", []))
    missing_visuals = visual_slots if visual_slots and not related_figures else []
    if missing_visuals:
        lines.extend(["Visual needed:", *[f"- {slot}" for slot in missing_visuals], ""])
    table_slots = _string_list(item.get("table_slots", []))
    related_tables = _string_list(item.get("related_table_ids", []))
    missing_tables = table_slots if table_slots and not related_tables else []
    if missing_tables:
        lines.extend(["Table needed:", *[f"- {slot}" for slot in missing_tables], ""])
    if item.get("source_refs"):
        lines.extend([f"Source refs: {', '.join(item['source_refs'])}.", ""])
    if item.get("uncertainty_flags"):
        lines.extend([f"Uncertainty flags: {', '.join(item['uncertainty_flags'])}.", ""])
    return lines


def _default_export_group(item: dict[str, Any]) -> str:
    item_type = str(item.get("type", ""))
    if item_type == "report_section":
        assumptions = item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {}
        value = assumptions.get("export_group")
        if isinstance(value, str) and value.strip():
            return value
    if item_type in {"map_figure", "comparison_table", "draft_finding", "spatial_relationship", "no_mapped_relationships"}:
        return "constraints_inventory"
    if item_type in {"missing_data_placeholder", "source_inventory_note", "source_status_note"}:
        return "methodology"
    return "attachments"


def _issue(severity: str, code: str, message: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
    }


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
