"""Demo deliverable package orchestration."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .export_report import EXPORT_DIR, ExportReportError, export_report
from .populate_for_review import PopulateForReviewError, populate_for_review
from .review_queue import ReviewQueueError, load_review_queue


DEMO_DELIVERABLE_MANIFEST_PATH = EXPORT_DIR / "deliverable_package_manifest.json"


class DemoDeliverableError(RuntimeError):
    """Raised when demo deliverable package generation cannot complete."""


def build_demo_deliverable(
    project_dir: Path,
    *,
    prepare_sources: bool = False,
    include_optional_sources: bool = False,
    output_format: str = "both",
) -> dict[str, Any]:
    """Run the draft pipeline and export an internal preview package without changing review statuses."""

    project_dir = project_dir.resolve()
    try:
        populate_manifest = populate_for_review(
            project_dir,
            prepare_sources=prepare_sources,
            include_optional_sources=include_optional_sources,
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
        "output_format": output_format,
        "output_formats": export_manifest.get("output_formats", []),
        "populate_manifest_path": populate_manifest.get("output_path"),
        "export_manifest_path": export_manifest.get("output_path"),
        "markdown_path": export_manifest.get("markdown_path"),
        "docx_path": export_manifest.get("docx_path"),
        "review_queue_path": queue.get("output_path"),
        "review_queue_item_count": len(items),
        "review_queue_status_counts": dict(Counter(str(item.get("status", "")) for item in items)),
        "included_count": export_manifest.get("included_count", 0),
        "skipped_count": export_manifest.get("skipped_count", 0),
        "validation_issues": export_manifest.get("validation_issues", []),
        "warnings": populate_manifest.get("warnings", []),
        "output_path": str(manifest_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
