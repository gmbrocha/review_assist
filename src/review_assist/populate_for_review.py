"""Populate-for-review orchestration service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .project_context import ProjectContextError, generate_project_context
from .review_queue import ReviewQueueError, generate_review_queue
from .source_status import SourceStatusError, resolve_source_status_set
from .spatial_analysis import SpatialAnalysisError, analyze_project


POPULATE_FOR_REVIEW_PATH = Path("populate_for_review/populate_for_review_run.json")


class PopulateForReviewError(RuntimeError):
    """Raised when populate-for-review orchestration cannot complete."""


def populate_for_review(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    started_at = _utc_now()
    steps: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    critical_error: str | None = None
    context: dict[str, Any] | None = None
    source_status: dict[str, Any] | None = None
    spatial: dict[str, Any] | None = None
    review_queue: dict[str, Any] | None = None

    try:
        context = generate_project_context(project_dir)
        steps.append(_step("project_context", "completed", artifact_path=context.get("context_path")))

        source_status = resolve_source_status_set(project_dir)
        steps.append(_step("source_status", "completed", artifact_path=source_status.get("output_path")))
        warnings.extend(_issue_warnings("source_status", source_status.get("validation_issues", [])))

        spatial = analyze_project(project_dir, tolerate_source_errors=True)
        steps.append(_step("spatial_analysis", "completed", artifact_path=spatial.get("output_path")))
        warnings.extend(_issue_warnings("spatial_analysis", spatial.get("validation_issues", [])))
        for source in spatial.get("sources", []):
            if isinstance(source, dict):
                warnings.extend(_issue_warnings("spatial_analysis", source.get("validation_issues", []), source_id=source.get("source_id")))

        review_queue = generate_review_queue(project_dir)
        steps.append(_step("review_queue", "completed", artifact_path=review_queue.get("output_path")))
    except (ProjectContextError, SourceStatusError, SpatialAnalysisError, ReviewQueueError) as exc:
        critical_error = str(exc)
        steps.append(_step(_failed_step_name(context, source_status, spatial, review_queue), "failed", message=critical_error))

    manifest = {
        "project_id": _first_value("project_id", context, source_status, spatial, review_queue),
        "project_name": _first_value("project_name", context, source_status, spatial, review_queue),
        "project_dir": str(project_dir),
        "started_at": started_at,
        "completed_at": _utc_now(),
        "status": "failed" if critical_error else "completed",
        "steps": steps,
        "artifact_paths": {
            "project_context": context.get("context_path") if context else None,
            "source_status": source_status.get("output_path") if source_status else None,
            "spatial_relationships": spatial.get("output_path") if spatial else None,
            "review_queue": review_queue.get("output_path") if review_queue else None,
        },
        "review_queue_item_count": review_queue.get("item_count") if review_queue else 0,
        "warnings": warnings,
        "critical_error": critical_error,
    }
    output_path = project_dir / POPULATE_FOR_REVIEW_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest["output_path"] = str(output_path)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if critical_error:
        raise PopulateForReviewError(critical_error)
    return manifest


def _step(name: str, status: str, *, artifact_path: Any = None, message: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "artifact_path": artifact_path,
        "message": message,
    }


def _issue_warnings(stage: str, issues: Any, *, source_id: Any = None) -> list[dict[str, Any]]:
    if not isinstance(issues, list):
        return []
    warnings: list[dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        warning = dict(issue)
        warning["stage"] = stage
        if source_id and not warning.get("source_id"):
            warning["source_id"] = source_id
        warnings.append(warning)
    return warnings


def _failed_step_name(
    context: dict[str, Any] | None,
    source_status: dict[str, Any] | None,
    spatial: dict[str, Any] | None,
    review_queue: dict[str, Any] | None,
) -> str:
    if context is None:
        return "project_context"
    if source_status is None:
        return "source_status"
    if spatial is None:
        return "spatial_analysis"
    if review_queue is None:
        return "review_queue"
    return "populate_for_review"


def _first_value(key: str, *items: dict[str, Any] | None) -> Any:
    for item in items:
        if item and item.get(key):
            return item[key]
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
