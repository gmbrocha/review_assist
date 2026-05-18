"""Populate-for-review orchestration service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .comparison_units import ComparisonUnitError, build_comparison_units
from .constraints import ConstraintAnalysisError, analyze_constraints
from .evidence_package import EvidencePackageError, build_evidence_package
from .findings import FindingGenerationError, generate_draft_findings
from .input_package import InputPackageError, classify_input_package
from .maps import MapGenerationError, generate_maps
from .project_area import ProjectAreaError, build_project_area
from .project_geometry import ProjectGeometryError, build_project_geometry
from .project_context import ProjectContextError, generate_project_context
from .report_sections import ReportSectionGenerationError, generate_report_sections
from .review_queue import ReviewQueueError, generate_review_queue
from .source_acquisition import SourceAcquisitionError, prepare_sources as prepare_project_sources
from .source_inventory import SourceInventoryError, generate_source_inventory
from .source_materialization import SourceMaterializationError, materialize_local_sources as materialize_project_local_sources
from .source_status import SourceStatusError, resolve_source_status_set
from .tables import TableGenerationError, generate_comparison_tables


POPULATE_FOR_REVIEW_PATH = Path("populate_for_review/populate_for_review_run.json")


class PopulateForReviewError(RuntimeError):
    """Raised when populate-for-review orchestration cannot complete."""


def populate_for_review(
    project_dir: Path,
    *,
    prepare_sources: bool = False,
    include_optional_sources: bool = False,
    materialize_local_sources: bool = False,
    gpt_drafting: bool | None = None,
    gpt_model: str | None = None,
) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    started_at = _utc_now()
    steps: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    critical_error: str | None = None
    input_package: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    project_geometry: dict[str, Any] | None = None
    project_area: dict[str, Any] | None = None
    comparison_units: dict[str, Any] | None = None
    source_materialization: dict[str, Any] | None = None
    source_acquisition: dict[str, Any] | None = None
    source_status: dict[str, Any] | None = None
    source_inventory: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None
    draft_findings: dict[str, Any] | None = None
    comparison_tables: dict[str, Any] | None = None
    map_manifest: dict[str, Any] | None = None
    evidence_package: dict[str, Any] | None = None
    report_sections: dict[str, Any] | None = None
    review_queue: dict[str, Any] | None = None

    try:
        input_package = classify_input_package(project_dir)
        steps.append(_step("input_package", "completed", artifact_path=input_package.get("output_path")))
        warnings.extend(_issue_warnings("input_package", input_package.get("validation_issues", [])))

        project_geometry = build_project_geometry(project_dir)
        steps.append(_step("project_geometry", "completed", artifact_path=project_geometry.get("output_path")))

        project_area = build_project_area(project_dir)
        steps.append(_step("project_area", "completed", artifact_path=project_area.get("output_path")))
        warnings.extend(_issue_warnings("project_area", project_area.get("validation_issues", [])))
        warnings.extend(_issue_warnings("project_area", project_area.get("warnings", [])))

        comparison_units = build_comparison_units(project_dir)
        steps.append(_step("comparison_units", "completed", artifact_path=comparison_units.get("output_path")))
        warnings.extend(_issue_warnings("comparison_units", comparison_units.get("validation_issues", [])))

        context = generate_project_context(project_dir)
        steps.append(_step("project_context", "completed", artifact_path=context.get("context_path")))

        if materialize_local_sources:
            source_materialization = materialize_project_local_sources(project_dir)
            steps.append(_step("source_materialization", "completed", artifact_path=source_materialization.get("output_path")))
            warnings.extend(_issue_warnings("source_materialization", source_materialization.get("validation_issues", [])))
            context = generate_project_context(project_dir)
            steps.append(_step("project_context_refresh", "completed", artifact_path=context.get("context_path")))

        if prepare_sources:
            source_acquisition = prepare_project_sources(
                project_dir,
                include_optional_sources=include_optional_sources,
            )
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

        evidence_package = build_evidence_package(project_dir)
        steps.append(_step("evidence_package", "completed", artifact_path=evidence_package.get("output_path")))
        warnings.extend(
            _issue_warnings(
                "evidence_package",
                evidence_package.get("validation_issues", []),
                exclude_codes={"no_real_source_layers"},
            )
        )

        report_sections = generate_report_sections(project_dir, gpt_drafting=gpt_drafting, gpt_model=gpt_model)
        steps.append(_step("report_sections", "completed", artifact_path=report_sections.get("output_path")))
        warnings.extend(_issue_warnings("report_sections", report_sections.get("validation_issues", [])))

        review_queue = generate_review_queue(project_dir)
        steps.append(_step("review_queue", "completed", artifact_path=review_queue.get("output_path")))
    except (
        InputPackageError,
        ComparisonUnitError,
        ProjectAreaError,
        ProjectContextError,
        ProjectGeometryError,
        SourceMaterializationError,
        SourceAcquisitionError,
        SourceStatusError,
        SourceInventoryError,
        ConstraintAnalysisError,
        FindingGenerationError,
        TableGenerationError,
        MapGenerationError,
        EvidencePackageError,
        ReportSectionGenerationError,
        ReviewQueueError,
    ) as exc:
        critical_error = str(exc)
        steps.append(
            _step(
                _failed_step_name(
                    context,
                    input_package,
                    project_geometry,
                    project_area,
                    comparison_units,
                    source_materialization,
                    materialize_local_sources,
                    source_acquisition,
                    prepare_sources,
                    source_status,
                    source_inventory,
                    constraints,
                    draft_findings,
                    comparison_tables,
                    map_manifest,
                    evidence_package,
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
            input_package,
            context,
            project_geometry,
            project_area,
            comparison_units,
            source_materialization,
            source_status,
            source_acquisition,
            source_inventory,
            constraints,
            draft_findings,
            comparison_tables,
            map_manifest,
            evidence_package,
            report_sections,
            review_queue,
        ),
        "project_name": _first_value(
            "project_name",
            input_package,
            context,
            project_geometry,
            project_area,
            comparison_units,
            source_materialization,
            source_status,
            source_acquisition,
            source_inventory,
            constraints,
            draft_findings,
            comparison_tables,
            map_manifest,
            evidence_package,
            report_sections,
            review_queue,
        ),
        "project_dir": str(project_dir),
        "started_at": started_at,
        "completed_at": _utc_now(),
        "status": "failed" if critical_error else "completed",
        "steps": steps,
        "artifact_paths": {
            "input_package": input_package.get("output_path") if input_package else None,
            "project_context": context.get("context_path") if context else None,
            "project_geometry": project_geometry.get("output_path") if project_geometry else None,
            "project_features": project_geometry.get("project_features_path") if project_geometry else None,
            "analysis_bounds": project_geometry.get("analysis_bounds_path") if project_geometry else None,
            "project_area": project_area.get("output_path") if project_area else None,
            "comparison_units": comparison_units.get("comparison_units_path") if comparison_units else None,
            "comparison_units_metadata": comparison_units.get("output_path") if comparison_units else None,
            "source_materialization": source_materialization.get("output_path") if source_materialization else None,
            "source_acquisition": source_acquisition.get("output_path") if source_acquisition else None,
            "source_status": source_status.get("output_path") if source_status else None,
            "source_inventory": source_inventory.get("output_path") if source_inventory else None,
            "constraint_results": constraints.get("output_path") if constraints else None,
            "draft_findings": draft_findings.get("output_path") if draft_findings else None,
            "comparison_tables": comparison_tables.get("output_path") if comparison_tables else None,
            "map_manifest": map_manifest.get("output_path") if map_manifest else None,
            "evidence_package": evidence_package.get("output_path") if evidence_package else None,
            "report_sections": report_sections.get("output_path") if report_sections else None,
            "review_queue": review_queue.get("output_path") if review_queue else None,
        },
        "gpt_drafting": report_sections.get("gpt_drafting") if report_sections else {},
        "constraint_count": constraints.get("constraint_count") if constraints else 0,
        "comparison_unit_count": comparison_units.get("comparison_unit_count") if comparison_units else 0,
        "expected_comparison_unit_count": comparison_units.get("expected_comparison_unit_count") if comparison_units else None,
        "expected_count_status": comparison_units.get("expected_count_status") if comparison_units else None,
        "project_county_names": project_area.get("county_names") if project_area else [],
        "basemap_rendering_status": project_area.get("basemap_rendering_status") if project_area else None,
        "source_materialization_count": source_materialization.get("materialized_count") if source_materialization else 0,
        "source_materialization_enabled": materialize_local_sources,
        "source_acquisition_download_count": source_acquisition.get("download_count") if source_acquisition else 0,
        "source_acquisition_include_optional_sources": include_optional_sources if prepare_sources else False,
        "review_queue_item_count": review_queue.get("item_count") if review_queue else 0,
        "warnings": _dedupe_warnings(warnings),
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


def _issue_warnings(
    stage: str,
    issues: Any,
    *,
    source_id: Any = None,
    exclude_codes: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(issues, list):
        return []
    warnings: list[dict[str, Any]] = []
    excluded = exclude_codes or set()
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        if str(issue.get("code", "")) in excluded:
            continue
        warning = dict(issue)
        warning["stage"] = stage
        if source_id and not warning.get("source_id"):
            warning["source_id"] = source_id
        warnings.append(warning)
    return warnings


def _dedupe_warnings(warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str, str]] = set()
    result: list[dict[str, Any]] = []
    for warning in warnings:
        key = (
            str(warning.get("stage", "")),
            str(warning.get("code", "")),
            str(warning.get("location", "")),
            str(warning.get("message", "")),
            str(warning.get("source_id", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(warning)
    return result


def _failed_step_name(
    context: dict[str, Any] | None,
    input_package: dict[str, Any] | None,
    project_geometry: dict[str, Any] | None,
    project_area: dict[str, Any] | None,
    comparison_units: dict[str, Any] | None,
    source_materialization: dict[str, Any] | None,
    source_materialization_expected: bool,
    source_acquisition: dict[str, Any] | None,
    source_acquisition_expected: bool,
    source_status: dict[str, Any] | None,
    source_inventory: dict[str, Any] | None,
    constraints: dict[str, Any] | None,
    draft_findings: dict[str, Any] | None,
    comparison_tables: dict[str, Any] | None,
    map_manifest: dict[str, Any] | None,
    evidence_package: dict[str, Any] | None,
    report_sections: dict[str, Any] | None,
    review_queue: dict[str, Any] | None,
) -> str:
    if input_package is None:
        return "input_package"
    if project_geometry is None:
        return "project_geometry"
    if project_area is None:
        return "project_area"
    if comparison_units is None:
        return "comparison_units"
    if context is None:
        return "project_context"
    if source_materialization_expected and source_materialization is None:
        return "source_materialization"
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
    if evidence_package is None:
        return "evidence_package"
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
