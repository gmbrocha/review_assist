"""Demo deliverable package orchestration."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .data_lineage import build_data_lineage, mvp_blocking_issues
from .export_report import EXPORT_DIR, ExportGateError, ExportReportError, export_report
from .populate_for_review import PopulateForReviewError, populate_for_review
from .review_queue import ReviewQueueError, load_review_queue


DEMO_DELIVERABLE_MANIFEST_PATH = EXPORT_DIR / "deliverable_package_manifest.json"


class DemoDeliverableError(RuntimeError):
    """Raised when demo deliverable package generation cannot complete."""


class MvpDeliverableError(RuntimeError):
    """Raised when real-data MVP deliverable package generation cannot complete."""


def build_demo_deliverable(
    project_dir: Path,
    *,
    prepare_sources: bool = False,
    include_optional_sources: bool = False,
    materialize_local_sources: bool = False,
    output_format: str = "both",
    gpt_drafting: bool | None = None,
    gpt_model: str | None = None,
) -> dict[str, Any]:
    """Run the draft pipeline and export an internal preview package without changing review statuses."""

    project_dir = project_dir.resolve()
    try:
        populate_manifest = populate_for_review(
            project_dir,
            prepare_sources=prepare_sources,
            include_optional_sources=include_optional_sources,
            materialize_local_sources=materialize_local_sources,
            gpt_drafting=gpt_drafting,
            gpt_model=gpt_model,
        )
        export_manifest = export_report(project_dir, include_draft=True, output_format=output_format)
        queue = load_review_queue(project_dir)
    except (PopulateForReviewError, ExportReportError, ReviewQueueError) as exc:
        raise DemoDeliverableError(str(exc)) from exc

    items = [item for item in queue.get("items", []) if isinstance(item, dict)]
    manifest_path = project_dir / DEMO_DELIVERABLE_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "project_id": export_manifest.get("project_id") or populate_manifest.get("project_id"),
        "project_name": export_manifest.get("project_name") or populate_manifest.get("project_name"),
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "package_status": "internal_preview",
        "prepare_sources": prepare_sources,
        "include_optional_sources": include_optional_sources if prepare_sources else False,
        "materialize_local_sources": materialize_local_sources,
        "source_materialization_path": populate_manifest.get("artifact_paths", {}).get("source_materialization")
        if isinstance(populate_manifest.get("artifact_paths"), dict)
        else None,
        "source_materialization_count": populate_manifest.get("source_materialization_count", 0),
        "output_format": output_format,
        "output_formats": export_manifest.get("output_formats", []),
        "populate_manifest_path": populate_manifest.get("output_path"),
        "export_manifest_path": export_manifest.get("output_path"),
        "markdown_path": export_manifest.get("markdown_path"),
        "docx_path": export_manifest.get("docx_path"),
        "review_queue_path": queue.get("output_path"),
        "review_queue_item_count": len(items),
        "review_queue_status_counts": dict(Counter(str(item.get("status", "")) for item in items)),
        **_review_gate_fields(export_manifest),
        "included_count": export_manifest.get("included_count", 0),
        "skipped_count": export_manifest.get("skipped_count", 0),
        "data_lineage": export_manifest.get("data_lineage", {}),
        "mvp_quality": export_manifest.get("mvp_quality", {}),
        "evidence_package_path": export_manifest.get("evidence_package_path"),
        "gpt_drafting": export_manifest.get("gpt_drafting", populate_manifest.get("gpt_drafting", {})),
        "validation_issues": export_manifest.get("validation_issues", []),
        "warnings": populate_manifest.get("warnings", []),
        "output_path": str(manifest_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_mvp_deliverable(
    project_dir: Path,
    *,
    include_optional_sources: bool = False,
    fail_on_no_downloaded_sources: bool = True,
    materialize_local_sources: bool = False,
    output_format: str = "both",
    gpt_drafting: bool | None = None,
    gpt_model: str | None = None,
) -> dict[str, Any]:
    """Run source-backed populate-for-review and export an internal MVP preview package."""

    project_dir = project_dir.resolve()
    try:
        populate_manifest = populate_for_review(
            project_dir,
            prepare_sources=True,
            include_optional_sources=include_optional_sources,
            materialize_local_sources=materialize_local_sources,
            gpt_drafting=gpt_drafting,
            gpt_model=gpt_model,
        )
        queue = load_review_queue(project_dir)
    except (PopulateForReviewError, ReviewQueueError) as exc:
        raise MvpDeliverableError(str(exc)) from exc

    items = [item for item in queue.get("items", []) if isinstance(item, dict)]
    data_lineage = build_data_lineage(project_dir, included_items=[item for item in items if item.get("status") not in {"rejected", "declined"}])
    blocking_issues = mvp_blocking_issues(
        data_lineage,
        fail_on_no_downloaded_sources=fail_on_no_downloaded_sources,
    )
    if blocking_issues:
        messages = "; ".join(str(issue.get("message", issue.get("code", "MVP deliverable blocked."))) for issue in blocking_issues)
        raise MvpDeliverableError(messages)

    try:
        try:
            export_manifest = export_report(project_dir, include_draft=False, output_format=output_format)
        except ExportGateError:
            export_manifest = export_report(project_dir, include_draft=True, output_format=output_format)
        queue = load_review_queue(project_dir)
    except (ExportReportError, ReviewQueueError) as exc:
        raise MvpDeliverableError(str(exc)) from exc

    items = [item for item in queue.get("items", []) if isinstance(item, dict)]
    manifest_path = project_dir / DEMO_DELIVERABLE_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "project_id": export_manifest.get("project_id") or populate_manifest.get("project_id"),
        "project_name": export_manifest.get("project_name") or populate_manifest.get("project_name"),
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "package_status": "internal_preview_real_data_mvp" if export_manifest.get("preview_mode") else "reviewed_content_real_data_mvp",
        "prepare_sources": True,
        "include_optional_sources": include_optional_sources,
        "materialize_local_sources": materialize_local_sources,
        "source_materialization_path": populate_manifest.get("artifact_paths", {}).get("source_materialization")
        if isinstance(populate_manifest.get("artifact_paths"), dict)
        else None,
        "source_materialization_count": populate_manifest.get("source_materialization_count", 0),
        "fail_on_no_downloaded_sources": fail_on_no_downloaded_sources,
        "output_format": output_format,
        "output_formats": export_manifest.get("output_formats", []),
        "populate_manifest_path": populate_manifest.get("output_path"),
        "export_manifest_path": export_manifest.get("output_path"),
        "markdown_path": export_manifest.get("markdown_path"),
        "docx_path": export_manifest.get("docx_path"),
        "review_queue_path": queue.get("output_path"),
        "review_queue_item_count": len(items),
        "review_queue_status_counts": dict(Counter(str(item.get("status", "")) for item in items)),
        **_review_gate_fields(export_manifest),
        "included_count": export_manifest.get("included_count", 0),
        "skipped_count": export_manifest.get("skipped_count", 0),
        "data_lineage": export_manifest.get("data_lineage", data_lineage),
        "mvp_quality": export_manifest.get("mvp_quality", {}),
        "evidence_package_path": export_manifest.get("evidence_package_path"),
        "gpt_drafting": export_manifest.get("gpt_drafting", populate_manifest.get("gpt_drafting", {})),
        "validation_issues": export_manifest.get("validation_issues", []),
        "warnings": populate_manifest.get("warnings", []),
        "output_path": str(manifest_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _review_gate_fields(export_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_gate_status": export_manifest.get("review_gate_status"),
        "preview_mode": export_manifest.get("preview_mode", False),
        "review_item_count": export_manifest.get("review_item_count"),
        "terminal_review_item_count": export_manifest.get("terminal_review_item_count"),
        "unreviewed_item_count": export_manifest.get("unreviewed_item_count"),
        "declined_item_count": export_manifest.get("declined_item_count"),
        "deliverable_matrix_version": export_manifest.get("deliverable_matrix_version"),
        "expected_deliverable_item_count": export_manifest.get("expected_deliverable_item_count"),
        "actual_deliverable_item_count": export_manifest.get("actual_deliverable_item_count"),
        "included_table_ids": export_manifest.get("included_table_ids", []),
        "included_figure_ids": export_manifest.get("included_figure_ids", []),
        "included_attachment_ids": export_manifest.get("included_attachment_ids", []),
        "stub_item_count": export_manifest.get("stub_item_count"),
        "unreviewed_items_preview": export_manifest.get("unreviewed_items_preview", []),
        "compactness_budget": export_manifest.get("compactness_budget", {}),
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
