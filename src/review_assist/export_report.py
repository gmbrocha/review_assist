"""Editable report export package generation from reviewed queue items."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .data_lineage import build_data_lineage
from .review_queue import ReviewQueueError, generate_review_queue, load_review_queue
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set
from .tables import TABLES_PATH, TableGenerationError, load_comparison_tables


EXPORT_DIR = Path("exports")
EXPORT_MANIFEST_PATH = EXPORT_DIR / "export_manifest.json"
EXPORT_MARKDOWN_PATH = EXPORT_DIR / "environmental_constraints_report.md"
EXPORT_DOCX_PATH = EXPORT_DIR / "environmental_constraints_report.docx"
SUPPORTED_OUTPUT_FORMATS = {"markdown", "docx", "both"}
DOCX_TABLE_ROW_LIMIT = 50

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


def export_report(project_dir: Path, *, include_draft: bool = False, output_format: str = "markdown") -> dict[str, Any]:
    project_dir = project_dir.resolve()
    formats = _output_formats(output_format)
    try:
        queue = _load_or_generate_queue(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
        comparison_tables = _load_optional_comparison_tables(project_dir)
    except (ReviewQueueError, SourceStatusError) as exc:
        raise ExportReportError(str(exc)) from exc

    output_dir = project_dir / EXPORT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = project_dir / EXPORT_MARKDOWN_PATH
    docx_path = project_dir / EXPORT_DOCX_PATH
    manifest_path = project_dir / EXPORT_MANIFEST_PATH
    now = _utc_now()

    items = _dict_list(queue.get("items", []))
    included, skipped = _partition_export_items(items, include_draft=include_draft)
    included = sorted(included, key=_export_sort_key)
    data_lineage = build_data_lineage(project_dir, included_items=included)
    unresolved_required_sources = _unresolved_required_sources(source_status)
    validation_issues = _export_validation_issues(
        included,
        unresolved_required_sources,
        include_draft=include_draft,
    )
    validation_issues.extend(_dict_list(data_lineage.get("validation_issues", [])))
    if comparison_tables:
        validation_issues.extend(_dict_list(comparison_tables.get("validation_issues", [])))

    if "markdown" in formats:
        markdown = _markdown_report(
            queue=queue,
            included=included,
            validation_issues=validation_issues,
            include_draft=include_draft,
            data_lineage=data_lineage,
        )
        markdown_path.write_text(markdown, encoding="utf-8")

    if "docx" in formats:
        _write_docx_report(
            project_dir=project_dir,
            docx_path=docx_path,
            queue=queue,
            included=included,
            validation_issues=validation_issues,
            include_draft=include_draft,
            comparison_tables=comparison_tables,
            data_lineage=data_lineage,
            output_paths={
                "markdown_report": str(markdown_path) if "markdown" in formats else None,
                "docx_report": str(docx_path),
                "export_manifest": str(manifest_path),
            },
        )

    manifest = {
        "project_id": queue.get("project_id"),
        "project_name": queue.get("project_name"),
        "project_dir": str(project_dir),
        "created_at": now,
        "include_draft": include_draft,
        "output_format": output_format,
        "output_formats": formats,
        "package_status": "internal_preview" if include_draft else "reviewed_content",
        "review_queue_path": queue.get("output_path"),
        "source_status_path": source_status.get("output_path"),
        "comparison_tables_path": comparison_tables.get("output_path") if comparison_tables else None,
        "markdown_path": str(markdown_path) if "markdown" in formats else None,
        "docx_path": str(docx_path) if "docx" in formats else None,
        "included_count": len(included),
        "skipped_count": len(skipped),
        "status_counts": dict(Counter(str(item.get("status", "")) for item in items)),
        "included_status_counts": dict(Counter(item["status"] for item in included)),
        "skipped_status_counts": dict(Counter(item["status"] for item in skipped)),
        "included_type_counts": dict(Counter(item["type"] for item in included)),
        "skipped_type_counts": dict(Counter(item["type"] for item in skipped)),
        "included_table_ids": sorted({str(item.get("table_id")) for item in included if item.get("table_id")}),
        "included_map_paths": sorted({str(item.get("image_path")) for item in included if item.get("image_path")}),
        "included_source_refs": sorted({ref for item in included for ref in _string_list(item.get("source_refs", []))}),
        "unresolved_required_sources": unresolved_required_sources,
        "data_lineage": data_lineage,
        "package_contents": _package_contents(queue, output_paths={
            "markdown_report": str(markdown_path) if "markdown" in formats else None,
            "docx_report": str(docx_path) if "docx" in formats else None,
            "export_manifest": str(manifest_path),
        }),
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


def _load_optional_comparison_tables(project_dir: Path) -> dict[str, Any] | None:
    tables_path = project_dir / TABLES_PATH
    if not tables_path.exists():
        return None
    try:
        return load_comparison_tables(project_dir)
    except TableGenerationError as exc:
        return {
            "tables": [],
            "output_path": str(tables_path),
            "validation_issues": [
                _issue(
                    "warning",
                    "comparison_tables_unavailable",
                    f"Comparison table artifact could not be loaded for export table rendering: {exc}",
                )
            ],
        }


def _output_formats(output_format: str) -> list[str]:
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        allowed = ", ".join(sorted(SUPPORTED_OUTPUT_FORMATS))
        raise ExportReportError(f"Unsupported export format '{output_format}'. Expected one of: {allowed}.")
    if output_format == "both":
        return ["markdown", "docx"]
    return [output_format]


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
        "columns": _string_list(item.get("columns", [])),
        "rows_preview": _dict_list(item.get("rows_preview", [])),
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
    unresolved_required_sources: list[dict[str, Any]],
    *,
    include_draft: bool,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not include_draft and not any(item["type"] == "report_section" for item in included):
        issues.append(_issue("warning", "no_accepted_report_sections", "No accepted or edited report sections were available for export."))
    if not include_draft and not any(item["type"] == "map_figure" for item in included):
        issues.append(_issue("warning", "no_accepted_maps", "No accepted or edited map figures were available for export."))
    if unresolved_required_sources:
        categories = ", ".join(str(item.get("category")) for item in unresolved_required_sources)
        issues.append(
            _issue(
                "warning",
                "unresolved_required_source_gaps",
                f"Required source categories remain unresolved or require review: {categories}.",
            )
        )
    return issues


def _unresolved_required_sources(source_status: dict[str, Any]) -> list[dict[str, Any]]:
    unresolved: list[dict[str, Any]] = []
    for item in _dict_list(source_status.get("statuses", [])):
        if item.get("requirement") != "required" or str(item.get("status")) not in UNRESOLVED_REQUIRED_SOURCE_STATUSES:
            continue
        unresolved.append(
            {
                "category": item.get("category"),
                "status": item.get("status"),
                "source_ids": _string_list(item.get("source_ids", [])),
                "notes": item.get("notes", ""),
                "uncertainty_flags": _string_list(item.get("uncertainty_flags", [])),
            }
        )
    return unresolved


def _markdown_report(
    *,
    queue: dict[str, Any],
    included: list[dict[str, Any]],
    validation_issues: list[dict[str, Any]],
    include_draft: bool,
    data_lineage: dict[str, Any],
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
    lines.extend(_markdown_data_lineage(data_lineage))
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
    lines.extend(_markdown_package_contents(queue))
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


def _markdown_data_lineage(data_lineage: dict[str, Any]) -> list[str]:
    lines = ["## Real Data Used", ""]
    real_records = [
        record
        for record in _dict_list(data_lineage.get("records", []))
        if record.get("lineage_type") in {"downloaded_public_source", "registered_local", "provided_in_input"}
    ]
    if real_records:
        for record in real_records:
            label = record.get("source_name") or record.get("source_id") or record.get("path") or "Real data source"
            details = []
            if record.get("status"):
                details.append(f"status `{record.get('status')}`")
            if record.get("feature_count") is not None:
                details.append(f"{record.get('feature_count')} feature(s)")
            if record.get("access_date"):
                details.append(f"accessed {record.get('access_date')}")
            lines.append(f"- {label}: {', '.join(details) if details else record.get('lineage_type')}.")
    else:
        lines.append("- No downloaded, provided-in-input, or registered local source layers were available.")
    lines.append("")
    stub_records = [
        record
        for record in _dict_list(data_lineage.get("records", []))
        if record.get("lineage_type") in {"manual_stub", "gated_stub", "missing_stub"}
    ]
    lines.extend(["## Stubs / Manual Review Needed", ""])
    if stub_records:
        for record in stub_records:
            label = record.get("category") or record.get("source_id") or "source category"
            lines.append(f"- {label}: {record.get('status', 'stub')} ({record.get('lineage_type')}).")
    else:
        lines.append("- No source stubs were recorded for this export.")
    lines.append("")
    return lines


def _markdown_package_contents(queue: dict[str, Any]) -> list[str]:
    lines = ["## Generated Package Contents", ""]
    contents = _package_contents(queue, output_paths={})
    for label, value in contents.items():
        if isinstance(value, dict):
            if not value:
                continue
            lines.append(f"- {label}:")
            for nested_label, nested_value in value.items():
                if nested_value:
                    lines.append(f"  - {nested_label}: `{nested_value}`")
        elif value:
            lines.append(f"- {label}: `{value}`")
    lines.append("")
    return lines


def _write_docx_report(
    *,
    project_dir: Path,
    docx_path: Path,
    queue: dict[str, Any],
    included: list[dict[str, Any]],
    validation_issues: list[dict[str, Any]],
    include_draft: bool,
    comparison_tables: dict[str, Any] | None,
    data_lineage: dict[str, Any],
    output_paths: dict[str, str | None],
) -> None:
    try:
        from docx import Document
        from docx.shared import Inches
    except ImportError as exc:  # pragma: no cover - dependency is declared, this guards broken environments.
        raise ExportReportError("DOCX export requires the python-docx package to be installed.") from exc

    document = Document()
    table_lookup = _tables_by_id(comparison_tables)

    title = str(queue.get("project_name") or "Environmental Constraints Report")
    document.add_heading(title, level=0)
    document.add_paragraph("Environmental Constraints Report")
    document.add_paragraph(f"Generated: {_utc_now()}")
    if include_draft:
        notice = document.add_paragraph()
        run = notice.add_run("INTERNAL PREVIEW / NOT REVIEWED")
        run.bold = True
        document.add_paragraph(
            "This package includes draft or unaccepted review queue items. It is for internal preview only and is not ready for external use."
        )
    else:
        document.add_paragraph(
            "Reviewed-content export: this package includes only accepted, edited, or explicitly export-eligible reviewed items."
        )

    if validation_issues:
        document.add_heading("Export Caveats", level=1)
        for issue in validation_issues:
            document.add_paragraph(f"{issue.get('code')}: {issue.get('message')}", style="List Bullet")

    _add_docx_data_lineage(document, data_lineage)

    if not included:
        document.add_heading("No Exported Content", level=1)
        document.add_paragraph("No review queue items met the export criteria.")
    else:
        current_group = ""
        for item in included:
            group = str(item.get("export_group", "resource_sections"))
            if group != current_group:
                current_group = group
                document.add_heading(EXPORT_GROUP_TITLES.get(group, group.replace("_", " ").title()), level=1)
            _add_docx_item(
                document=document,
                item=item,
                project_dir=project_dir,
                table_lookup=table_lookup,
                image_width=Inches(6.3),
            )

    _add_docx_package_contents(document, queue, output_paths)
    docx_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(docx_path)


def _add_docx_data_lineage(document: Any, data_lineage: dict[str, Any]) -> None:
    document.add_heading("Real Data Used", level=1)
    real_records = [
        record
        for record in _dict_list(data_lineage.get("records", []))
        if record.get("lineage_type") in {"downloaded_public_source", "registered_local", "provided_in_input"}
    ]
    if real_records:
        for record in real_records:
            label = record.get("source_name") or record.get("source_id") or record.get("path") or "Real data source"
            details = []
            if record.get("status"):
                details.append(f"status {record.get('status')}")
            if record.get("feature_count") is not None:
                details.append(f"{record.get('feature_count')} feature(s)")
            if record.get("access_date"):
                details.append(f"accessed {record.get('access_date')}")
            if record.get("checksum_sha256"):
                details.append(f"checksum {record.get('checksum_sha256')}")
            if record.get("source_limitations"):
                details.append(f"limitations: {record.get('source_limitations')}")
            document.add_paragraph(f"{label}: {'; '.join(details) if details else record.get('lineage_type')}.", style="List Bullet")
    else:
        document.add_paragraph("No downloaded, provided-in-input, or registered local source layers were available.", style="List Bullet")

    document.add_heading("Stubs / Manual Review Needed", level=1)
    stub_records = [
        record
        for record in _dict_list(data_lineage.get("records", []))
        if record.get("lineage_type") in {"manual_stub", "gated_stub", "missing_stub"}
    ]
    if stub_records:
        for record in stub_records:
            label = record.get("category") or record.get("source_id") or "source category"
            notes = str(record.get("notes") or "").strip()
            suffix = f" {notes}" if notes else ""
            document.add_paragraph(f"{label}: {record.get('status', 'stub')} ({record.get('lineage_type')}).{suffix}", style="List Bullet")
    else:
        document.add_paragraph("No source stubs were recorded for this export.", style="List Bullet")


def _add_docx_item(
    *,
    document: Any,
    item: dict[str, Any],
    project_dir: Path,
    table_lookup: dict[str, dict[str, Any]],
    image_width: Any,
) -> None:
    item_type = str(item.get("type", ""))
    heading_level = 2 if item_type == "report_section" else 3
    document.add_heading(str(item.get("title") or "Untitled Item"), level=heading_level)

    content = str(item.get("content", "")).strip()
    if content:
        _add_docx_content(document, content)
    else:
        document.add_paragraph("No generated or reviewer-edited content was available for this item.")

    if item_type == "comparison_table":
        _add_docx_comparison_table(document, item, table_lookup)
    elif item_type == "map_figure":
        _add_docx_map_figure(document, item, project_dir, image_width)
    else:
        _add_docx_missing_slots(document, item)

    if item.get("source_refs"):
        document.add_paragraph(f"Source refs: {', '.join(_string_list(item.get('source_refs', [])))}.")
    if item.get("uncertainty_flags"):
        document.add_paragraph(f"Uncertainty flags: {', '.join(_string_list(item.get('uncertainty_flags', [])))}.")


def _add_docx_content(document: Any, content: str) -> None:
    for raw_line in content.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            document.add_heading(line[4:].strip(), level=4)
        elif line.startswith("## "):
            document.add_heading(line[3:].strip(), level=3)
        elif line.startswith("# "):
            document.add_heading(line[2:].strip(), level=2)
        elif line.startswith("- "):
            document.add_paragraph(line[2:].strip(), style="List Bullet")
        else:
            document.add_paragraph(line)


def _add_docx_comparison_table(
    document: Any,
    item: dict[str, Any],
    table_lookup: dict[str, dict[str, Any]],
) -> None:
    table_id = str(item.get("table_id") or "")
    source_table = table_lookup.get(table_id)
    if source_table is None:
        document.add_paragraph(f"Table placeholder: source table artifact was not available for table id '{table_id}'.")
        return

    columns = _string_list(source_table.get("columns", []))
    rows = _dict_list(source_table.get("rows", []))
    if not columns:
        columns = sorted({str(key) for row in rows for key in row})
    if not columns:
        document.add_paragraph("Table placeholder: no columns were available for this table.")
        return
    if not rows:
        document.add_paragraph("Table placeholder: this table currently has no rows.")
        return

    rendered_rows = rows[:DOCX_TABLE_ROW_LIMIT]
    table = document.add_table(rows=1, cols=len(columns))
    table.style = "Table Grid"
    header_cells = table.rows[0].cells
    for index, column in enumerate(columns):
        header_cells[index].text = column
    for row in rendered_rows:
        cells = table.add_row().cells
        for index, column in enumerate(columns):
            cells[index].text = _docx_cell_text(row.get(column))
    if len(rows) > DOCX_TABLE_ROW_LIMIT:
        document.add_paragraph(
            f"Table preview limited to {DOCX_TABLE_ROW_LIMIT} of {len(rows)} rows. Full table data remains in the table artifact."
        )


def _add_docx_map_figure(document: Any, item: dict[str, Any], project_dir: Path, image_width: Any) -> None:
    image_value = item.get("image_path")
    if not image_value:
        document.add_paragraph("Figure placeholder: no image path was recorded for this map figure.")
        return
    image_path = Path(str(image_value))
    if not image_path.is_absolute():
        image_path = project_dir / image_path
    if not image_path.exists():
        document.add_paragraph(f"Figure placeholder: figure file was not available at {image_path}.")
        return
    try:
        document.add_picture(str(image_path), width=image_width)
    except Exception as exc:  # pragma: no cover - image backend errors vary by file.
        document.add_paragraph(f"Figure placeholder: figure could not be embedded from {image_path}: {exc}.")
        return
    document.add_paragraph(f"Figure file: {image_path}")


def _add_docx_missing_slots(document: Any, item: dict[str, Any]) -> None:
    visual_slots = _string_list(item.get("visual_slots", []))
    related_figures = _string_list(item.get("related_figure_ids", []))
    missing_visuals = visual_slots if visual_slots and not related_figures else []
    if missing_visuals:
        document.add_paragraph("Visual needed:")
        for slot in missing_visuals:
            document.add_paragraph(slot, style="List Bullet")

    table_slots = _string_list(item.get("table_slots", []))
    related_tables = _string_list(item.get("related_table_ids", []))
    missing_tables = table_slots if table_slots and not related_tables else []
    if missing_tables:
        document.add_paragraph("Table needed:")
        for slot in missing_tables:
            document.add_paragraph(slot, style="List Bullet")


def _add_docx_package_contents(document: Any, queue: dict[str, Any], output_paths: dict[str, str | None]) -> None:
    document.add_heading("Generated Package Contents", level=1)
    contents = _package_contents(queue, output_paths=output_paths)
    for label, value in contents.items():
        if isinstance(value, dict):
            document.add_paragraph(f"{label}:")
            for nested_label, nested_value in value.items():
                if nested_value:
                    document.add_paragraph(f"{nested_label}: {nested_value}", style="List Bullet")
        elif value:
            document.add_paragraph(f"{label}: {value}", style="List Bullet")


def _tables_by_id(comparison_tables: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if comparison_tables is None:
        return {}
    return {
        str(table.get("table_id")): table
        for table in _dict_list(comparison_tables.get("tables", []))
        if table.get("table_id")
    }


def _package_contents(queue: dict[str, Any], *, output_paths: dict[str, str | None]) -> dict[str, Any]:
    upstream = queue.get("upstream_artifacts", {}) if isinstance(queue.get("upstream_artifacts"), dict) else {}
    return {
        "project_dir": queue.get("project_dir"),
        "review_queue": queue.get("output_path"),
        "source_inventory": upstream.get("source_inventory_path"),
        "source_status": upstream.get("source_status_path"),
        "constraint_results": upstream.get("constraint_results_path"),
        "comparison_tables": upstream.get("comparison_tables_path"),
        "map_manifest": upstream.get("map_manifest_path"),
        "report_sections": upstream.get("report_sections_path"),
        "exports": {key: value for key, value in output_paths.items() if value},
    }


def _docx_cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True)
    else:
        text = str(value)
    return text if len(text) <= 250 else text[:247] + "..."


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
