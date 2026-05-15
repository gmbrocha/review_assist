"""Populate-for-review orchestration service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constraints import ConstraintAnalysisError, analyze_constraints
from .findings import FindingGenerationError, generate_draft_findings
from .maps import MapGenerationError, generate_maps
from .project_geometry import ProjectGeometryError, build_project_geometry
from .project_context import ProjectContextError, generate_project_context
from .report_sections import ReportSectionGenerationError, generate_report_sections
from .review_queue import ReviewQueueError, generate_review_queue
from .source_acquisition import SourceAcquisitionError, prepare_sources as prepare_project_sources
from .source_inventory import SourceInventoryError, generate_source_inventory
from .source_status import SourceStatusError, resolve_source_status_set
from .tables import TableGenerationError, generate_comparison_tables


POPULATE_FOR_REVIEW_PATH = Path("populate_for_review/populate_for_review_run.json")


class PopulateForReviewError(RuntimeError):
    """Raised when populate-for-review orchestration cannot complete."""


def populate_for_review(project_dir: Path, *, prepare_sources: bool = False) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    started_at = _utc_now()
    steps: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    critical_error: str | None = None
    context: dict[str, Any] | None = None
    project_geometry: dict[str, Any] | None = None
    source_acquisition: dict[str, Any] | None = None
    source_status: dict[str, Any] | None = None
    source_inventory: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None
    draft_findings: dict[str, Any] | None = None
    comparison_tables: dict[str, Any] | None = None
    map_manifest: dict[str, Any] | None = None
    report_sections: dict[str, Any] | None = None
    review_queue: dict[str, Any] | None = None

    try:
        context = generate_project_context(project_dir)
        steps.append(_step("project_context", "completed", artifact_path=context.get("context_path")))

        project_geometry = build_project_geometry(project_dir)
        steps.append(_step("project_geometry", "completed", artifact_path=project_geometry.get("output_path")))

        if prepare_sources:
            source_acquisition = prepare_project_sources(project_dir)
            steps.append(_step("source_acquisition", "completed", artifact_path=source_acquisition.get("output_path")))
            warnings.extend(_issue_warnings("source_acquisition", source_acquisition.get("validation_issues", [])))

        source_status = resolve_source_status_set(project_dir)
        steps.append(_step("source_status", "completed", artifact_path=source_status.get("output_path")))
        warnings.extend(_issue_warnings("source_status", source_status.get("validation_issues", [])))

        source_inventory = generate_source_inventory(project_dir)
        steps.append(_step("source_inventory", "completed", artifact_path=source_inventory.get("output_path")))
        warnings.extend(_issue_warnings("source_inventory", source_inventory.get("validation_issues", [])))

        constraints = analyze_constraints(project_dir, tolerate_source_errors=True)
        steps.append(_step("constraint_analysis", "completed", artifact_path=constraints.get("output_path")))
        warnings.extend(_issue_warnings("constraint_analysis", constraints.get("validation_issues", [])))
        for source in constraints.get("sources", []):
            if isinstance(source, dict):
                warnings.extend(_issue_warnings("constraint_analysis", source.get("validation_issues", []), source_id=source.get("source_id")))

        draft_findings = generate_draft_findings(project_dir)
        steps.append(_step("draft_findings", "completed", artifact_path=draft_findings.get("output_path")))
        warnings.extend(_issue_warnings("draft_findings", draft_findings.get("validation_issues", [])))

        comparison_tables = generate_comparison_tables(project_dir)
        steps.append(_step("comparison_tables", "completed", artifact_path=comparison_tables.get("output_path")))
        warnings.extend(_issue_warnings("comparison_tables", comparison_tables.get("validation_issues", [])))

        map_manifest = generate_maps(project_dir)
        steps.append(_step("map_generation", "completed", artifact_path=map_manifest.get("output_path")))
        warnings.extend(_issue_warnings("map_generation", map_manifest.get("validation_issues", [])))

        report_sections = generate_report_sections(project_dir)
        steps.append(_step("report_sections", "completed", artifact_path=report_sections.get("output_path")))
        warnings.extend(_issue_warnings("report_sections", report_sections.get("validation_issues", [])))

        review_queue = generate_review_queue(project_dir)
        steps.append(_step("review_queue", "completed", artifact_path=review_queue.get("output_path")))
    except (
        ProjectContextError,
        ProjectGeometryError,
        SourceAcquisitionError,
        SourceStatusError,
        SourceInventoryError,
        ConstraintAnalysisError,
        FindingGenerationError,
        TableGenerationError,
        MapGenerationError,
        ReportSectionGenerationError,
        ReviewQueueError,
    ) as exc:
        critical_error = str(exc)
        steps.append(
            _step(
                _failed_step_name(
                    context,
                    project_geometry,
                    source_acquisition,
                    prepare_sources,
                    source_status,
                    source_inventory,
                    constraints,
                    draft_findings,
                    comparison_tables,
                    map_manifest,
                    report_sections,
                    review_queue,
                ),
                "failed",
                message=critical_error,
            )
        )

    manifest = {
        "project_id": _first_value(
            "project_id",
            context,
            project_geometry,
            source_status,
            source_acquisition,
            source_inventory,
            constraints,
            draft_findings,
            comparison_tables,
            map_manifest,
            report_sections,
            review_queue,
        ),
        "project_name": _first_value(
            "project_name",
            context,
            project_geometry,
            source_status,
            source_acquisition,
            source_inventory,
            constraints,
            draft_findings,
            comparison_tables,
            map_manifest,
            report_sections,
            review_queue,
        ),
        "project_dir": str(project_dir),
        "started_at": started_at,
        "completed_at": _utc_now(),
        "status": "failed" if critical_error else "completed",
        "steps": steps,
        "artifact_paths": {
            "project_context": context.get("context_path") if context else None,
            "project_geometry": project_geometry.get("output_path") if project_geometry else None,
            "project_features": project_geometry.get("project_features_path") if project_geometry else None,
            "analysis_bounds": project_geometry.get("analysis_bounds_path") if project_geometry else None,
            "source_acquisition": source_acquisition.get("output_path") if source_acquisition else None,
            "source_status": source_status.get("output_path") if source_status else None,
            "source_inventory": source_inventory.get("output_path") if source_inventory else None,
            "constraint_results": constraints.get("output_path") if constraints else None,
            "draft_findings": draft_findings.get("output_path") if draft_findings else None,
            "comparison_tables": comparison_tables.get("output_path") if comparison_tables else None,
            "map_manifest": map_manifest.get("output_path") if map_manifest else None,
            "report_sections": report_sections.get("output_path") if report_sections else None,
            "review_queue": review_queue.get("output_path") if review_queue else None,
        },
        "constraint_count": constraints.get("constraint_count") if constraints else 0,
        "source_acquisition_download_count": source_acquisition.get("download_count") if source_acquisition else 0,
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
    project_geometry: dict[str, Any] | None,
    source_acquisition: dict[str, Any] | None,
    source_acquisition_expected: bool,
    source_status: dict[str, Any] | None,
    source_inventory: dict[str, Any] | None,
    constraints: dict[str, Any] | None,
    draft_findings: dict[str, Any] | None,
    comparison_tables: dict[str, Any] | None,
    map_manifest: dict[str, Any] | None,
    report_sections: dict[str, Any] | None,
    review_queue: dict[str, Any] | None,
) -> str:
    if context is None:
        return "project_context"
    if project_geometry is None:
        return "project_geometry"
    if source_acquisition_expected and source_acquisition is None:
        return "source_acquisition"
    if source_status is None:
        return "source_status"
    if source_inventory is None:
        return "source_inventory"
    if constraints is None:
        return "constraint_analysis"
    if draft_findings is None:
        return "draft_findings"
    if comparison_tables is None:
        return "comparison_tables"
    if map_manifest is None:
        return "map_generation"
    if report_sections is None:
        return "report_sections"
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
