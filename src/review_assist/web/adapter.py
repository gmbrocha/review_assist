"""Service adapter for the local Review Assist web UI.

This module is intentionally thin: it reads stable Sprint 1-3 artifacts and
calls existing services for mutation/export. It does not reinterpret raw GIS,
evidence, matrix, or report assembly internals.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from werkzeug.utils import secure_filename

from review_assist.comparison_units import COMPARISON_UNITS_METADATA_PATH
from review_assist.deliverable import DEMO_DELIVERABLE_MANIFEST_PATH
from review_assist.deliverable_items import DELIVERABLE_ITEMS_PATH, RENDER_POLICY_FIELDS
from review_assist.deliverable_figures import DeliverableFigureError, load_deliverable_figures
from review_assist.export_report import (
    EXPORT_MANIFEST_PATH,
    ExportGateError,
    ExportQAError,
    ExportReportError,
    export_report,
)
from review_assist.figure_style_model import (
    FIGURE_RECIPES_PATH,
    FIGURE_RENDER_JOBS_PATH,
    FIGURE_STYLE_OVERRIDES_PATH,
    FIGURE_VERSIONS_PATH,
    FigureStyleModelError,
    active_style_override,
    build_analysis_snapshot,
    build_figure_recipe,
    figure_recipe_for,
    load_figure_style_artifacts,
    reset_project_style_override,
    save_project_style_override,
)
from review_assist.gpt_interpretive_assist import (
    GptInterpretiveAssistError,
    draft_section_candidates,
    gpt_interpretive_assist_status,
)
from review_assist.input_package import (
    DOCUMENT_EXTENSIONS,
    IMAGERY_EXTENSIONS,
    INPUT_PACKAGE_PATH,
    PROJECT_GEOMETRY_EXTENSIONS,
    SOURCE_LAYER_EXTENSIONS,
    InputPackageError,
    classify_input_package,
)
from review_assist.populate_for_review import POPULATE_FOR_REVIEW_PATH, PopulateForReviewError, populate_for_review
from review_assist.project_area import PROJECT_AREA_PATH
from review_assist.project_context import PROJECT_CONTEXT_PATH
from review_assist.projects import MANIFEST_PATH, ProjectInput, ProjectManifest, ProjectManifestError, load_project_manifest, save_project_manifest
from review_assist.review_queue import REVIEW_QUEUE_PATH, ReviewQueueError, load_review_queue, update_review_item
from review_assist.review_queue_reset import ReviewQueueResetError, reset_review_queue
from review_assist.source_status import SOURCE_STATUS_PATH


RAW_LEGACY_ITEM_TYPES = {
    "draft_finding",
    "spatial_relationship",
    "comparison_table",
    "source_inventory_note",
    "source_status_note",
    "no_mapped_relationships",
    "validation_issue",
    "missing_data_placeholder",
}
REPORT_ROLE_LABELS = {
    "include_body": "Report body",
    "table_figure_only": "Table/Figure support",
    "attachment_status": "Attachment/support",
    "needs_reviewer_decision": "Reviewer decision needed",
    "blocked_missing_source": "Source/status review",
    "blocked_manual_or_restricted_source": "Manual/restricted source",
    "custom_project_required": "Custom project content",
    "audit_only": "Audit only",
}
OUTPUT_DESTINATION_LABELS = {
    "report_body": "Report body",
    "tables_figures": "Table/Figure support",
    "attachments": "Attachment/support",
    "review_status": "Review/status item",
    "audit_evidence": "Audit evidence",
}
TERMINAL_STATUSES = {"accepted", "edited", "replaced", "declined"}
BLOCKING_STATUSES = {"draft", "needs_review", "needs_verification"}
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}
DRAFT_PROJECT_PATH = Path("config/project_draft.json")
STAGING_UPLOADS_DIR = Path("staging/uploads")
INPUTS_DIR = Path("inputs")
WEB_RUN_STATUS_PATH = Path("web_runs/latest_run.json")
ALLOWED_UPLOAD_EXTENSIONS = PROJECT_GEOMETRY_EXTENSIONS | SOURCE_LAYER_EXTENSIONS | DOCUMENT_EXTENSIONS | IMAGERY_EXTENSIONS
FIGURE_REPLACEMENTS_DIR = Path("review_queue/figure_replacements")
FIGURE_REPLACEMENT_EXTENSIONS = {".png", ".jpg", ".jpeg"}
REVIEW_TABLE_PREVIEW_LIMIT = 5


class WebAdapterError(RuntimeError):
    """Raised when the web adapter cannot satisfy a UI request safely."""


@dataclass(frozen=True)
class ProjectRef:
    """A project workspace listed for the UI."""

    project_key: str
    project_id: str
    name: str
    path: str
    modified_at: str
    status: str
    review_gate_status: str
    is_draft: bool = False
    error: str = ""


def project_root_path(project_root: str | Path | None = None) -> Path:
    """Return the configured project workspace root."""

    return Path(project_root or Path.cwd() / "projects").resolve()


def list_projects(project_root: str | Path | None = None) -> list[ProjectRef]:
    """List existing project workspaces under the configured root."""

    root = project_root_path(project_root)
    if not root.exists():
        return []
    projects: list[ProjectRef] = []
    for child in sorted((item for item in root.iterdir() if item.is_dir()), key=lambda item: item.name.lower()):
        manifest_path = child / MANIFEST_PATH
        draft_path = child / DRAFT_PROJECT_PATH
        if not manifest_path.exists() and not draft_path.exists():
            continue
        error = ""
        project_id = child.name
        name = child.name
        is_draft = not manifest_path.exists()
        if manifest_path.exists():
            try:
                manifest = load_project_manifest(child)
                project_id = manifest.project_id
                name = manifest.name
            except ProjectManifestError as exc:
                error = str(exc)
        elif draft_path.exists():
            draft = _load_json(draft_path)
            project_id = str(draft.get("project_id") or child.name)
            name = str(draft.get("name") or child.name)
        projects.append(
            ProjectRef(
                project_key=child.name,
                project_id=project_id,
                name=name,
                path=_project_relative(root, child),
                modified_at=_modified_at(child),
                status=_project_pipeline_status(child),
                review_gate_status=_manifest_gate_status(child),
                is_draft=is_draft,
                error=error,
            )
        )
    return projects


def create_draft_project(
    project_root: str | Path | None,
    *,
    project_id: str,
    name: str,
    description: str = "",
) -> dict[str, Any]:
    """Create a draft workspace without writing config/project.json."""

    key = validate_project_key(project_id)
    project_name = str(name or "").strip()
    if not project_name:
        raise WebAdapterError("Project name is required.")
    root = project_root_path(project_root)
    project_dir = (root / key).resolve()
    if not _is_relative_to(project_dir, root):
        raise WebAdapterError("Project path escapes the configured project root.")
    if project_dir.exists():
        raise WebAdapterError("A project with this id already exists.")

    now = _utc_now()
    (project_dir / "config").mkdir(parents=True, exist_ok=False)
    (project_dir / STAGING_UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
    (project_dir / INPUTS_DIR).mkdir(parents=True, exist_ok=True)
    (project_dir / WEB_RUN_STATUS_PATH.parent).mkdir(parents=True, exist_ok=True)
    draft = {
        "project_id": key,
        "name": project_name,
        "description": str(description or ""),
        "project_type": "alternatives_review",
        "assumptions": {
            "default_buffer_feet": 100,
            "input_crs": "EPSG:4326",
        },
        "status": "draft_setup",
        "created_at": now,
        "updated_at": now,
    }
    _write_json(project_dir / DRAFT_PROJECT_PATH, draft)
    return {
        "project_key": key,
        "project_dir": str(project_dir),
        "draft_path": str(project_dir / DRAFT_PROJECT_PATH),
        "draft": draft,
    }


def validate_project_key(value: str) -> str:
    """Validate and return a project root child name."""

    key = str(value or "").strip()
    if not key:
        raise WebAdapterError("Project id is required.")
    if key in {".", ".."} or key.startswith(".") or key.endswith("."):
        raise WebAdapterError("Project id cannot be hidden, relative, or end with a dot.")
    if "/" in key or "\\" in key or Path(key).is_absolute():
        raise WebAdapterError("Project id cannot contain path separators.")
    if not PROJECT_ID_RE.fullmatch(key):
        raise WebAdapterError("Project id may use only letters, numbers, dot, dash, and underscore.")
    _reject_reserved_name(key, "Project id")
    return key


def resolve_project_dir(project_root: str | Path | None, project_key: str) -> Path:
    """Resolve a selected project key to a direct child of project_root."""

    try:
        key = validate_project_key(project_key)
    except WebAdapterError as exc:
        raise WebAdapterError("Invalid project id.") from exc
    root = project_root_path(project_root)
    project_dir = (root / key).resolve()
    if not _is_relative_to(project_dir, root):
        raise WebAdapterError("Project path escapes the configured project root.")
    if not project_dir.is_dir():
        raise WebAdapterError("Project does not exist.")
    if not (project_dir / MANIFEST_PATH).exists() and not (project_dir / DRAFT_PROJECT_PATH).exists():
        raise WebAdapterError("Project manifest or draft metadata is missing.")
    return project_dir


def project_summary(project_dir: Path) -> dict[str, Any]:
    """Return compact project and populate/source status for the Overview page."""

    manifest = _manifest_summary(project_dir)
    input_package = _load_json(project_dir / INPUT_PACKAGE_PATH)
    project_area = _load_json(project_dir / PROJECT_AREA_PATH)
    comparison_units = _load_json(project_dir / COMPARISON_UNITS_METADATA_PATH)
    source_status = _load_json(project_dir / SOURCE_STATUS_PATH)
    populate_manifest = _load_json(project_dir / POPULATE_FOR_REVIEW_PATH)
    context = _load_json(project_dir / PROJECT_CONTEXT_PATH)

    source_rows = _source_status_rows(source_status)
    validation_issues = [
        *_issue_rows(input_package, "input_package"),
        *_issue_rows(project_area, "project_area"),
        *_issue_rows(comparison_units, "comparison_units"),
        *_issue_rows(source_status, "source_status"),
        *_issue_rows(populate_manifest, "populate"),
    ]

    return {
        "manifest": manifest,
        "input_package": {
            "status": _artifact_status(input_package),
            "input_count": len(_dict_list(input_package.get("inputs", []))),
            "validation_issue_count": len(_dict_list(input_package.get("validation_issues", []))),
        },
        "project_area": {
            "status": _artifact_status(project_area),
            "county_names": _string_list(project_area.get("county_names", [])),
            "bbox": project_area.get("bbox") if isinstance(project_area, dict) else None,
            "basemap_rendering_status": project_area.get("basemap_rendering_status") if isinstance(project_area, dict) else None,
        },
        "comparison_units": {
            "status": _artifact_status(comparison_units),
            "comparison_unit_count": comparison_units.get("comparison_unit_count", 0) if isinstance(comparison_units, dict) else 0,
            "expected_count_status": comparison_units.get("expected_count_status") if isinstance(comparison_units, dict) else None,
        },
        "source_status": {
            "status": _artifact_status(source_status),
            "rows": source_rows,
            "status_counts": dict(Counter(row.get("status", "unknown") for row in source_rows)),
        },
        "populate": {
            "status": populate_manifest.get("status", "not_run") if isinstance(populate_manifest, dict) else "not_run",
            "started_at": populate_manifest.get("started_at") if isinstance(populate_manifest, dict) else None,
            "completed_at": populate_manifest.get("completed_at") if isinstance(populate_manifest, dict) else None,
            "review_queue_item_count": populate_manifest.get("review_queue_item_count", 0) if isinstance(populate_manifest, dict) else 0,
            "warnings": _dict_list(populate_manifest.get("warnings", [])) if isinstance(populate_manifest, dict) else [],
            "critical_error": populate_manifest.get("critical_error") if isinstance(populate_manifest, dict) else None,
            "steps": _dict_list(populate_manifest.get("steps", [])) if isinstance(populate_manifest, dict) else [],
        },
        "context": {
            "status": _artifact_status(context),
            "project_type": context.get("project_type") if isinstance(context, dict) else None,
            "report_profile": context.get("report_profile") if isinstance(context, dict) else None,
        },
        "setup": setup_status(project_dir),
        "workflow_readiness": workflow_readiness(project_dir),
        "latest_run": latest_run_status(project_dir),
        "gpt_interpretive_assist": gpt_interpretive_assist_status(project_dir),
        "validation_issues": validation_issues,
    }


def run_populate(project_dir: Path) -> dict[str, Any]:
    """Run the existing populate-for-review service with conservative defaults."""

    _write_run_status(project_dir, action="populate_for_review", status="started", message="Create Review Queue started.")
    try:
        result = populate_for_review(
            project_dir,
            materialize_local_sources=True,
            materialize_naip_basemap=True,
            gpt_drafting=False,
        )
    except PopulateForReviewError as exc:
        _write_run_status(
            project_dir,
            action="populate_for_review",
            status="failed",
            message="Create Review Queue failed.",
            error=str(exc),
        )
        raise WebAdapterError(str(exc)) from exc
    _write_run_status(
        project_dir,
        action="populate_for_review",
        status="completed",
        message=f"Create Review Queue completed with {result.get('review_queue_item_count', 0)} review items.",
        artifact_path=str(result.get("output_path") or ""),
    )
    return result


def reset_generated_review_queue(
    project_dir: Path,
    *,
    include_evidence: bool = False,
    include_exports: bool = False,
) -> dict[str, Any]:
    """Run the developer/test refresh for generated review artifacts."""

    _write_run_status(project_dir, action="reset_review_queue", status="started", message="Review artifact refresh started.")
    try:
        result = reset_review_queue(
            project_dir,
            regenerate=True,
            dry_run=False,
            include_evidence=include_evidence,
            include_exports=include_exports,
        )
    except ReviewQueueResetError as exc:
        _write_run_status(
            project_dir,
            action="reset_review_queue",
            status="failed",
            message="Review artifact refresh failed.",
            error=str(exc),
        )
        raise WebAdapterError(str(exc)) from exc
    after = result.get("after", {}) if isinstance(result.get("after"), dict) else {}
    _write_run_status(
        project_dir,
        action="reset_review_queue",
        status="completed",
        message=f"Review artifacts refreshed and queue rebuilt with {after.get('review_queue_item_count', 0)} review items.",
        artifact_path=str(project_dir / REVIEW_QUEUE_PATH),
    )
    return result


def run_gpt_interpretive_assist(
    project_dir: Path,
    *,
    sections: list[str] | None = None,
    max_calls: int = 5,
    dry_run: bool = False,
    skip_existing: bool = True,
    source_backed_only: bool = True,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Run the explicit GPT Interpretive Assist service from the Overview UI."""

    _write_run_status(project_dir, action="gpt_interpretive_assist", status="started", message="GPT Interpretive Assist started.")
    try:
        result = draft_section_candidates(
            project_dir,
            sections=sections,
            max_calls=max_calls,
            dry_run=dry_run,
            skip_existing=skip_existing,
            source_backed_only=source_backed_only,
            force_refresh=force_refresh,
        )
    except GptInterpretiveAssistError as exc:
        _write_run_status(
            project_dir,
            action="gpt_interpretive_assist",
            status="failed",
            message="GPT Interpretive Assist failed.",
            error=str(exc),
        )
        raise WebAdapterError(str(exc)) from exc
    _write_run_status(
        project_dir,
        action="gpt_interpretive_assist",
        status="completed",
        message=(
            f"GPT Interpretive Assist completed with {result.get('accepted_gpt_draft_count', 0)} "
            f"accepted draft candidate(s) and {result.get('rejected_gpt_draft_count', 0)} rejected output(s)."
        ),
        artifact_path=str(result.get("output_path") or ""),
    )
    return result


def setup_status(project_dir: Path) -> dict[str, Any]:
    """Return draft/staged input readiness for setup screens."""

    draft = _load_json(project_dir / DRAFT_PROJECT_PATH)
    manifest_exists = (project_dir / MANIFEST_PATH).exists()
    input_package = _load_json(project_dir / INPUT_PACKAGE_PATH)
    staged = get_staged_inputs(project_dir)
    classification = classification_summary(project_dir)
    blockers: list[dict[str, str]] = []
    if not manifest_exists:
        blockers.append({"code": "project_manifest_missing", "message": "Commit at least one staged input to create config/project.json."})
    if not manifest_exists and not staged:
        blockers.append({"code": "staged_input_missing", "message": "Upload at least one KMZ/KML project input before creating the review queue."})
    if manifest_exists and input_package and not input_package.get("required_kmz_present", False):
        blockers.append({"code": "required_kmz_missing", "message": "At least one committed KMZ project-geometry input is required."})
    return {
        "is_draft": not manifest_exists,
        "manifest_exists": manifest_exists,
        "draft": draft,
        "staged_inputs": staged,
        "staged_input_count": len(staged),
        "committed_input_count": _manifest_summary(project_dir).get("input_count", 0),
        "committed_inputs": committed_inputs(project_dir),
        "classification": classification,
        "input_package_status": _artifact_status(input_package),
        "required_kmz_present": bool(input_package.get("required_kmz_present", False)) if input_package else False,
        "latest_run": latest_run_status(project_dir),
        "blockers": blockers,
    }


def committed_inputs(project_dir: Path) -> list[dict[str, Any]]:
    """Return configured input rows with compact classification status."""

    try:
        manifest = load_project_manifest(project_dir)
    except ProjectManifestError:
        return []
    input_package = _load_json(project_dir / INPUT_PACKAGE_PATH)
    classified_by_path = {
        str(record.get("path") or ""): record
        for record in _dict_list(input_package.get("inputs", []))
    }
    rows: list[dict[str, Any]] = []
    for project_input in manifest.inputs:
        relative_path = str(project_input.path)
        classified = classified_by_path.get(relative_path, {})
        try:
            safe_path = _safe_relative_path(project_dir, relative_path)
            exists = (project_dir.resolve() / safe_path).exists()
        except WebAdapterError:
            safe_path = Path(relative_path)
            exists = False
        rows.append(
            {
                "path": safe_path.as_posix(),
                "role": project_input.role,
                "description": project_input.description,
                "classification": str(classified.get("classification") or "not_classified"),
                "confidence": str(classified.get("confidence") or ""),
                "exists": bool(classified.get("exists", exists)) if classified else exists,
                "requires_reviewer_confirmation": bool(classified.get("requires_reviewer_confirmation", False)),
                "issue_count": len(_dict_list(classified.get("validation_issues", []))),
            }
        )
    return rows


def classification_summary(project_dir: Path) -> dict[str, Any]:
    """Return compact input-package classification status for setup screens."""

    input_package = _load_json(project_dir / INPUT_PACKAGE_PATH)
    if not isinstance(input_package, dict) or not input_package:
        return {
            "status": "missing",
            "input_count": 0,
            "required_kmz_present": False,
            "project_geometry_input_count": 0,
            "source_layer_input_count": 0,
            "unknown_input_count": 0,
            "requires_confirmation_count": 0,
            "validation_issue_count": 0,
            "output_path": "",
        }
    inputs = _dict_list(input_package.get("inputs", []))
    return {
        "status": "available",
        "input_count": _int_value(input_package.get("input_count"), len(inputs)),
        "required_kmz_present": bool(input_package.get("required_kmz_present", False)),
        "project_geometry_input_count": _int_value(input_package.get("project_geometry_input_count")),
        "source_layer_input_count": _int_value(input_package.get("source_layer_input_count")),
        "unknown_input_count": _int_value(input_package.get("unknown_input_count")),
        "requires_confirmation_count": sum(1 for item in inputs if item.get("requires_reviewer_confirmation")),
        "validation_issue_count": len(_dict_list(input_package.get("validation_issues", []))),
        "output_path": _project_relative_path(project_dir, str(input_package.get("output_path") or "")),
    }


def workflow_readiness(project_dir: Path) -> list[dict[str, str]]:
    """Return display-only readiness steps for the main local workflow."""

    manifest = _manifest_summary(project_dir)
    classification = classification_summary(project_dir)
    project_area = _load_json(project_dir / PROJECT_AREA_PATH)
    comparison_units = _load_json(project_dir / COMPARISON_UNITS_METADATA_PATH)
    source_status = _load_json(project_dir / SOURCE_STATUS_PATH)
    rows: list[dict[str, str]] = []

    if manifest.get("manifest_status") == "valid":
        rows.append(_workflow_step("Project Manifest", "ready", f"{manifest.get('input_count', 0)} configured input(s).", MANIFEST_PATH))
    elif manifest.get("manifest_status") == "draft":
        rows.append(_workflow_step("Project Manifest", "blocked", "Draft workspace only; commit staged inputs to create config/project.json.", MANIFEST_PATH))
    else:
        rows.append(_workflow_step("Project Manifest", "blocked", str(manifest.get("error") or "config/project.json is missing."), MANIFEST_PATH))

    if classification["status"] == "missing":
        rows.append(_workflow_step("Input Classification", "missing", "Run classification after committing project inputs.", INPUT_PACKAGE_PATH))
    elif classification["required_kmz_present"]:
        message = f"{classification['input_count']} input(s), {classification['project_geometry_input_count']} project geometry input(s)."
        rows.append(_workflow_step("Input Classification", "ready", message, INPUT_PACKAGE_PATH))
    else:
        rows.append(_workflow_step("Input Classification", "blocked", "At least one committed project-geometry KMZ input is required.", INPUT_PACKAGE_PATH))

    if isinstance(project_area, dict) and project_area:
        counties = _string_list(project_area.get("county_names", []))
        county_text = ", ".join(counties[:3]) if counties else "project area recorded"
        rows.append(_workflow_step("Project Area", "ready", county_text, PROJECT_AREA_PATH))
    else:
        rows.append(_workflow_step("Project Area", "missing", "Created by Create Review Queue/populate.", PROJECT_AREA_PATH))

    if isinstance(comparison_units, dict) and comparison_units:
        count = _int_value(comparison_units.get("comparison_unit_count"))
        status = "ready" if count else "warning"
        rows.append(_workflow_step("Comparison Units", status, f"{count} comparison unit(s) recorded.", COMPARISON_UNITS_METADATA_PATH))
    else:
        rows.append(_workflow_step("Comparison Units", "missing", "Created by Create Review Queue/populate.", COMPARISON_UNITS_METADATA_PATH))

    if isinstance(source_status, dict) and source_status:
        source_rows = _source_status_rows(source_status)
        status_counts = Counter(row.get("status", "unknown") for row in source_rows)
        message = ", ".join(f"{key}: {value}" for key, value in sorted(status_counts.items())) or f"{len(source_rows)} source status row(s)."
        rows.append(_workflow_step("Source Status", "ready", message, SOURCE_STATUS_PATH))
    else:
        rows.append(_workflow_step("Source Status", "missing", "Created by Create Review Queue/populate.", SOURCE_STATUS_PATH))

    if (project_dir / REVIEW_QUEUE_PATH).exists():
        try:
            queue = load_review_queue(project_dir)
        except ReviewQueueError as exc:
            rows.append(_workflow_step("Standard Review Queue", "warning", str(exc), REVIEW_QUEUE_PATH))
        else:
            if queue.get("queue_mode") == "deliverable_items":
                rows.append(_workflow_step("Standard Review Queue", "ready", f"{len(_dict_list(queue.get('items', [])))} bounded review item(s).", REVIEW_QUEUE_PATH))
            else:
                rows.append(_workflow_step("Standard Review Queue", "warning", "A legacy/audit queue exists; create the bounded standard queue for the UI workflow.", REVIEW_QUEUE_PATH))
    else:
        rows.append(_workflow_step("Standard Review Queue", "missing", "Run Create Review Queue after setup blockers are cleared.", REVIEW_QUEUE_PATH))

    return rows


def get_staged_inputs(project_dir: Path) -> list[dict[str, Any]]:
    """List staged uploads under staging/uploads without recursive browsing."""

    staging_dir = _safe_project_subdir(project_dir, STAGING_UPLOADS_DIR)
    if not staging_dir.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted((item for item in staging_dir.iterdir() if item.is_file()), key=lambda item: item.name.lower()):
        rows.append(
            {
                "filename": path.name,
                "relative_path": path.relative_to(project_dir.resolve()).as_posix(),
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "proposed_role": _default_input_role(path.name),
            }
        )
    return rows


def stage_upload(project_dir: Path, upload: Any) -> dict[str, Any]:
    """Save one uploaded file into the selected project's staging area."""

    filename = _safe_upload_filename(getattr(upload, "filename", ""))
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise WebAdapterError(f"Unsupported upload type '{extension}'.")
    staging_dir = _safe_project_subdir(project_dir, STAGING_UPLOADS_DIR)
    staging_dir.mkdir(parents=True, exist_ok=True)
    target = (staging_dir / filename).resolve()
    if not _is_relative_to(target, staging_dir):
        raise WebAdapterError("Upload path escapes the staging directory.")
    if target.exists():
        raise WebAdapterError(f"Upload already exists in staging: {filename}")
    committed_target = (project_dir.resolve() / INPUTS_DIR / filename).resolve()
    if committed_target.exists():
        raise WebAdapterError(f"An input with this filename already exists: {filename}")
    upload.save(target)
    return {
        "filename": filename,
        "relative_path": target.relative_to(project_dir.resolve()).as_posix(),
        "size_bytes": target.stat().st_size,
        "proposed_role": _default_input_role(filename),
    }


def commit_staged_inputs(project_dir: Path) -> dict[str, Any]:
    """Move staged uploads into inputs/ and write a valid project manifest."""

    staged = get_staged_inputs(project_dir)
    if not staged:
        raise WebAdapterError("No staged inputs are available to commit.")
    draft = _load_json(project_dir / DRAFT_PROJECT_PATH)
    existing_manifest: ProjectManifest | None = None
    if (project_dir / MANIFEST_PATH).exists():
        try:
            existing_manifest = load_project_manifest(project_dir)
        except ProjectManifestError as exc:
            raise WebAdapterError(str(exc)) from exc
    project_id = str((existing_manifest.project_id if existing_manifest else draft.get("project_id")) or project_dir.name)
    name = str((existing_manifest.name if existing_manifest else draft.get("name")) or project_id)
    description = str((existing_manifest.description if existing_manifest else draft.get("description")) or "")
    project_type = str((existing_manifest.project_type if existing_manifest else draft.get("project_type")) or "alternatives_review")
    assumptions = (
        dict(existing_manifest.assumptions)
        if existing_manifest
        else dict(draft.get("assumptions", {"default_buffer_feet": 100, "input_crs": "EPSG:4326"}))
    )
    inputs = list(existing_manifest.inputs) if existing_manifest else []

    staging_dir = _safe_project_subdir(project_dir, STAGING_UPLOADS_DIR)
    inputs_dir = _safe_project_subdir(project_dir, INPUTS_DIR)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    moves: list[tuple[Path, Path, ProjectInput]] = []
    for staged_input in staged:
        filename = _safe_upload_filename(staged_input["filename"])
        source = (staging_dir / filename).resolve()
        destination = (inputs_dir / filename).resolve()
        if not _is_relative_to(source, staging_dir) or not source.exists():
            raise WebAdapterError(f"Staged upload is missing or unsafe: {filename}")
        if not _is_relative_to(destination, inputs_dir):
            raise WebAdapterError("Committed input path escapes the inputs directory.")
        if destination.exists():
            raise WebAdapterError(f"Committed input already exists: {filename}")
        input_record = ProjectInput(
            path=f"{INPUTS_DIR.as_posix()}/{filename}",
            role=_default_input_role(filename),
            description=f"Uploaded via local web UI: {filename}",
        )
        moves.append((source, destination, input_record))

    for source, destination, input_record in moves:
        shutil.move(str(source), str(destination))
        inputs.append(input_record)

    manifest = ProjectManifest(
        project_id=project_id,
        name=name,
        description=description,
        project_type=project_type,
        inputs=inputs,
        assumptions=assumptions,
        special_reviewer_instructions=existing_manifest.special_reviewer_instructions if existing_manifest else "",
        report_profile=existing_manifest.report_profile if existing_manifest else None,
    )
    save_project_manifest(project_dir, manifest)
    if draft:
        draft["status"] = "manifest_created"
        draft["updated_at"] = _utc_now()
        _write_json(project_dir / DRAFT_PROJECT_PATH, draft)
    input_package = classify_project_inputs(project_dir)
    return {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "committed_count": len(moves),
        "manifest_path": str(project_dir / MANIFEST_PATH),
        "input_package_path": input_package.get("output_path"),
        "input_package": input_package,
    }


def classify_project_inputs(project_dir: Path) -> dict[str, Any]:
    """Run the existing input package classifier for committed manifest inputs."""

    _write_run_status(project_dir, action="classify_inputs", status="started", message="Input classification started.")
    try:
        result = classify_input_package(project_dir)
    except InputPackageError as exc:
        _write_run_status(
            project_dir,
            action="classify_inputs",
            status="failed",
            message="Input classification failed.",
            error=str(exc),
        )
        raise WebAdapterError(str(exc)) from exc
    _write_run_status(
        project_dir,
        action="classify_inputs",
        status="completed",
        message=f"Input classification completed with {result.get('input_count', 0)} configured inputs.",
        artifact_path=str(result.get("output_path") or ""),
    )
    return result


def latest_run_status(project_dir: Path) -> dict[str, Any]:
    """Load the latest lightweight web run status."""

    return _load_json(project_dir / WEB_RUN_STATUS_PATH)


def review_queue_summary(project_dir: Path) -> dict[str, Any]:
    """Return bounded standard review queue rows for the Review page."""

    queue = _load_standard_queue(project_dir)
    items = [_queue_row(item) for item in _dict_list(queue.get("items", [])) if str(item.get("type", "")) not in RAW_LEGACY_ITEM_TYPES]
    status_counts = dict(Counter(item["status"] for item in items))
    type_counts = dict(Counter(item["type"] for item in items))
    return {
        "project_id": queue.get("project_id"),
        "project_name": queue.get("project_name"),
        "queue_mode": queue.get("queue_mode"),
        "item_count": len(items),
        "status_counts": status_counts,
        "type_counts": type_counts,
        "remaining_count": _remaining_review_count(items),
        "items": items,
        "validation_issues": _dict_list(queue.get("validation_issues", [])),
        "output_path": queue.get("output_path"),
    }


def review_item_detail(project_dir: Path, item_id: str) -> dict[str, Any]:
    """Return one bounded review item with previews and references only."""

    queue = _load_standard_queue(project_dir)
    item = _find_review_item(queue, item_id)
    if str(item.get("type", "")) in RAW_LEGACY_ITEM_TYPES:
        raise WebAdapterError("Raw audit review items are not part of the standard UI workflow.")
    assumptions = item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {}
    row_preview = _dict_list(item.get("rows_preview", [])) or _dict_list(assumptions.get("rows_preview", []))
    columns = _string_list(item.get("columns", [])) or _string_list(assumptions.get("columns", []))
    image_path = _effective_figure_image_path(item, assumptions)
    caption = _effective_figure_caption(item, assumptions)
    return {
        **_queue_row(item),
        "is_figure": _is_figure_item(item),
        "generated_content": _review_body_text(item.get("generated_content")),
        "edited_content": str(item.get("edited_content") or ""),
        "replacement_content": str(item.get("replacement_content") or ""),
        "table_preview": {
            "table_id": str(item.get("table_id") or ""),
            "columns": columns,
            "rows": row_preview[:REVIEW_TABLE_PREVIEW_LIMIT],
            "preview_count": min(len(row_preview), REVIEW_TABLE_PREVIEW_LIMIT),
            "row_count": item.get("row_count") if item.get("row_count") is not None else assumptions.get("row_count"),
            "is_limited": bool(row_preview and len(row_preview) > REVIEW_TABLE_PREVIEW_LIMIT),
        },
        "figure": {
            "figure_id": str(item.get("figure_id") or ""),
            "image_path": _project_relative_path(project_dir, image_path),
            "artifact_link_path": _artifact_link_path(project_dir, image_path),
            "caption": caption,
            "source_note": item.get("source_note") or assumptions.get("source_note"),
            "method_note": item.get("method_note") or assumptions.get("method_note"),
            "caption_source": _figure_caption_source(item),
            "image_source": _figure_image_source(item),
        },
        "provenance": _provenance_summary(item.get("provenance", {})),
        "source_refs": _string_list(item.get("source_refs", [])),
        "manual_material": _manual_material_fields(item),
        "comparison_unit_ids": _string_list(item.get("comparison_unit_ids", [])),
        "reviewer_notes": _dict_list(item.get("reviewer_notes", [])),
        "validation_issues": _dict_list(item.get("validation_issues", [])),
        "uncertainty_flags": _string_list(item.get("uncertainty_flags", [])),
        "assumptions": _compact_assumptions(assumptions),
    }


def figure_style_editor_context(project_dir: Path, item_id: str) -> dict[str, Any]:
    """Return presentation-only figure style editor context for one figure item."""

    project_dir = project_dir.resolve()
    queue = _load_standard_queue(project_dir)
    item = _find_review_item(queue, item_id)
    if not _is_figure_item(item):
        raise WebAdapterError("Figure style editor is only available for figure review items.")
    figure_id = str(item.get("figure_id") or item_id)
    try:
        figures_artifact = load_deliverable_figures(project_dir)
    except DeliverableFigureError as exc:
        raise WebAdapterError(str(exc)) from exc
    figure = _find_deliverable_figure(figures_artifact, figure_id)
    artifacts = load_figure_style_artifacts(project_dir)
    recipes_artifact = artifacts.get("recipes", {}) if isinstance(artifacts.get("recipes"), dict) else {}
    model_initialized = bool(recipes_artifact.get("recipes"))
    if model_initialized:
        try:
            recipe = figure_recipe_for(recipes_artifact, figure_id)
        except FigureStyleModelError as exc:
            raise WebAdapterError(str(exc)) from exc
    else:
        snapshot = build_analysis_snapshot(project_dir, figures_artifact)
        recipe = build_figure_recipe(
            project_dir,
            figure,
            snapshot["analysis_snapshot_id"],
            project_id=str(figures_artifact.get("project_id") or ""),
        )
    overrides_artifact = artifacts.get("style_overrides", {}) if isinstance(artifacts.get("style_overrides"), dict) else {}
    active_override = active_style_override(overrides_artifact, figure_id) if overrides_artifact else None
    versions = [
        version
        for version in _dict_list((artifacts.get("versions") or {}).get("versions", []) if isinstance(artifacts.get("versions"), dict) else [])
        if str(version.get("figure_id") or "") == figure_id
    ]
    render_jobs = [
        job
        for job in _dict_list((artifacts.get("render_jobs") or {}).get("render_jobs", []) if isinstance(artifacts.get("render_jobs"), dict) else [])
        if str(job.get("figure_id") or "") == figure_id
    ]
    assumptions = item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {}
    image_path = _effective_figure_image_path(item, assumptions)
    return {
        "item_id": item_id,
        "figure_id": figure_id,
        "title": str(item.get("title") or figure.get("title") or figure_id),
        "status": str(item.get("status") or ""),
        "preview": {
            "image_path": _project_relative_path(project_dir, image_path),
            "artifact_link_path": _artifact_link_path(project_dir, image_path),
        },
        "model_initialized": model_initialized,
        "style_model_paths": _figure_style_model_paths(project_dir),
        "recipe": recipe,
        "layers": _style_editor_layers(recipe, active_override),
        "active_override": active_override or {},
        "version_summary": {
            "version_count": len(versions),
            "latest_version": _latest_by_timestamp(versions),
            "approved_version": next((version for version in versions if str(version.get("approval_state") or "") == "approved"), None),
        },
        "render_job_summary": {
            "render_job_count": len(render_jobs),
            "latest_render_job": _latest_by_timestamp(render_jobs),
        },
        "deferred_actions": {
            "save_and_regenerate": "Deferred to Sprint 6.5.",
            "approve_figure": "Deferred to Sprint 6.6.",
        },
    }


def save_figure_style_form(project_dir: Path, item_id: str, form: Any) -> dict[str, Any]:
    """Persist a sparse draft figure style override from the editor form."""

    queue = _load_standard_queue(project_dir)
    item = _find_review_item(queue, item_id)
    if not _is_figure_item(item):
        raise WebAdapterError("Figure style editor actions can only be used for figure review items.")
    figure_id = str(item.get("figure_id") or item_id)
    action = str(form.get("style_action") or "").strip()
    try:
        if action == "reset_default":
            return reset_project_style_override(project_dir, figure_id, actor="local_reviewer")
        if action == "save_draft":
            return save_project_style_override(
                project_dir,
                figure_id,
                _style_layers_from_form(form),
                actor="local_reviewer",
            )
    except FigureStyleModelError as exc:
        raise WebAdapterError(str(exc)) from exc
    raise WebAdapterError("Unsupported figure style action.")


def save_review_action(
    project_dir: Path,
    item_id: str,
    *,
    status: str,
    note: str | None = None,
    edited_content: str | None = None,
    replacement_content: str | None = None,
    export_eligible: bool | None = None,
) -> dict[str, Any]:
    """Persist a review decision through the existing review queue service."""

    try:
        return update_review_item(
            project_dir,
            item_id,
            status=status,
            note=note,
            edited_content=edited_content,
            replacement_content=replacement_content,
            export_eligible=export_eligible,
        )
    except ReviewQueueError as exc:
        raise WebAdapterError(str(exc)) from exc


def save_figure_review_action(
    project_dir: Path,
    item_id: str,
    *,
    caption: str | None,
    replacement_file: Any | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Accept a figure item with optional caption override and replacement image."""

    queue = _load_standard_queue(project_dir)
    existing = _find_review_item(queue, item_id)
    if not _is_figure_item(existing):
        raise WebAdapterError("Figure review actions can only be used for figure review items.")

    assumptions = existing.get("assumptions", {}) if isinstance(existing.get("assumptions"), dict) else {}
    generated_caption = _generated_figure_caption(existing, assumptions)
    final_caption = str(caption or "").strip() or generated_caption or str(existing.get("title") or existing.get("figure_id") or "")
    replacement_path = _store_figure_replacement(project_dir, existing, replacement_file)
    caption_changed = bool(final_caption.strip()) and final_caption.strip() != generated_caption.strip()
    status = "replaced" if replacement_path else ("edited" if caption_changed else "accepted")

    try:
        update_review_item(
            project_dir,
            item_id,
            status=status,
            note=note,
            edited_content=final_caption if caption_changed else "",
            replacement_content=replacement_path,
        )
    except ReviewQueueError as exc:
        raise WebAdapterError(str(exc)) from exc

    queue = load_review_queue(project_dir)
    item = _find_review_item(queue, item_id)
    current_assumptions = item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {}
    generated_image = str(current_assumptions.get("image_path") or "").strip()
    final_image = replacement_path or str(item.get("image_path") or generated_image or "").strip()
    item["caption"] = final_caption
    item["image_path"] = final_image
    item["figure_review"] = {
        "caption": final_caption,
        "caption_source": "edited_caption" if caption_changed else "generated_caption",
        "image_path": final_image,
        "image_source": "replacement_figure" if replacement_path else "generated_figure",
        "generated_image_path": generated_image,
        "replacement_figure_path": replacement_path,
        "reviewer_note_internal_only": bool(str(note or "").strip()),
    }
    _write_json(Path(queue["output_path"]), queue)
    return item


def export_readiness(project_dir: Path) -> dict[str, Any]:
    """Return export readiness from bounded queue state and existing manifests."""

    try:
        queue = _load_standard_queue(project_dir)
    except WebAdapterError as exc:
        return {
            "review_gate_status": "blocked",
            "message": str(exc),
            "queue_mode": "missing",
            "review_item_count": 0,
            "terminal_review_item_count": 0,
            "unreviewed_item_count": 0,
            "declined_item_count": 0,
            "blockers": [],
            "status_counts": {},
            "can_export": False,
            "compactness_budget": {},
            "final_verification": {},
            "export_qa": {},
            "export_qa_status": "not_run",
            "preview_mode": False,
            "latest_run": latest_run_status(project_dir),
        }
    items = _dict_list(queue.get("items", []))
    standard_items = [item for item in items if str(item.get("type", "")) not in RAW_LEGACY_ITEM_TYPES]
    blockers = [_readiness_blocker(item) for item in standard_items]
    blockers = [item for item in blockers if item]
    terminal_count = sum(1 for item in standard_items if _is_terminal_or_export_includable(item))
    manifest = _load_json(project_dir / EXPORT_MANIFEST_PATH)
    return {
        "review_gate_status": "passed" if not blockers and standard_items else "blocked",
        "message": "Reviewed export is ready." if not blockers and standard_items else "Reviewed export is blocked until standard review items are terminal or explicitly export-ready.",
        "queue_mode": queue.get("queue_mode"),
        "review_item_count": len(standard_items),
        "terminal_review_item_count": terminal_count,
        "unreviewed_item_count": len(blockers),
        "declined_item_count": sum(1 for item in standard_items if _status(item) == "declined"),
        "blockers": blockers[:10],
        "status_counts": dict(Counter(_status(item) for item in standard_items)),
        "can_export": bool(standard_items) and not blockers,
        "compactness_budget": manifest.get("compactness_budget", {}) if isinstance(manifest, dict) else {},
        "final_verification": manifest.get("final_verification", {}) if isinstance(manifest, dict) else {},
        "export_qa": manifest.get("export_qa", {}) if isinstance(manifest, dict) else {},
        "export_qa_status": str(manifest.get("export_qa_status") or "not_run") if isinstance(manifest, dict) else "not_run",
        "preview_mode": bool(manifest.get("preview_mode", False)) if isinstance(manifest, dict) else False,
        "last_export_manifest": _manifest_summary_row(project_dir, EXPORT_MANIFEST_PATH, manifest),
        "latest_run": latest_run_status(project_dir),
    }


def run_export(project_dir: Path, *, preview: bool) -> dict[str, Any]:
    """Run preview or reviewed export through the existing export service."""

    action = "preview_export" if preview else "reviewed_export"
    _write_run_status(
        project_dir,
        action=action,
        status="started",
        message="Internal preview export started." if preview else "Reviewed export started.",
    )
    try:
        result = export_report(project_dir, include_draft=preview, output_format="both")
    except ExportGateError as exc:
        _write_run_status(
            project_dir,
            action=action,
            status="failed",
            message="Export is blocked by the review-complete gate." if not preview else "Internal preview export failed.",
            error=str(exc),
        )
        raise WebAdapterError(str(exc)) from exc
    except ExportQAError as exc:
        _write_run_status(
            project_dir,
            action=action,
            status="failed",
            message="Reviewed export is blocked by export QA." if not preview else "Internal preview export failed export QA.",
            error=str(exc),
        )
        raise WebAdapterError(str(exc)) from exc
    except ExportReportError as exc:
        _write_run_status(
            project_dir,
            action=action,
            status="failed",
            message="Export failed.",
            error=str(exc),
        )
        raise WebAdapterError(str(exc)) from exc
    _write_run_status(
        project_dir,
        action=action,
        status="completed",
        message="Internal preview export completed." if preview else "Reviewed export completed.",
        artifact_path=str(result.get("output_path") or ""),
    )
    return result


def package_outputs(project_dir: Path) -> dict[str, Any]:
    """Return generated export/package artifacts without exposing arbitrary files."""

    export_manifest = _load_json(project_dir / EXPORT_MANIFEST_PATH)
    package_manifest = _load_json(project_dir / DEMO_DELIVERABLE_MANIFEST_PATH)
    return {
        "export_manifest": _manifest_summary_row(project_dir, EXPORT_MANIFEST_PATH, export_manifest),
        "package_manifest": _manifest_summary_row(project_dir, DEMO_DELIVERABLE_MANIFEST_PATH, package_manifest),
        "artifacts": _allowed_artifact_rows(project_dir),
        "compactness_budget": export_manifest.get("compactness_budget", {}) if isinstance(export_manifest, dict) else {},
        "final_verification": export_manifest.get("final_verification", {}) if isinstance(export_manifest, dict) else {},
        "export_qa": export_manifest.get("export_qa", {}) if isinstance(export_manifest, dict) else {},
        "export_qa_status": str(export_manifest.get("export_qa_status") or "not_run") if isinstance(export_manifest, dict) else "not_run",
        "package_final_verification": package_manifest.get("final_verification", {}) if isinstance(package_manifest, dict) else {},
    }


def resolve_artifact_path(project_dir: Path, relative_path: str) -> Path:
    """Resolve a known safe artifact path for serving from the local UI."""

    requested = _safe_relative_path(project_dir, relative_path)
    allowed = {row["relative_path"] for row in _allowed_artifact_rows(project_dir)}
    if requested.as_posix() not in allowed:
        raise WebAdapterError("Artifact is not exposed by the standard UI.")
    path = (project_dir / requested).resolve()
    if not _is_relative_to(path, project_dir.resolve()) or not path.is_file():
        raise WebAdapterError("Artifact path is invalid.")
    return path


def _load_standard_queue(project_dir: Path) -> dict[str, Any]:
    try:
        queue = load_review_queue(project_dir)
    except ReviewQueueError as exc:
        raise WebAdapterError(str(exc)) from exc
    if queue.get("queue_mode") != "deliverable_items":
        raise WebAdapterError("The standard UI requires the matrix-bounded deliverable review queue.")
    return queue


def _manifest_summary(project_dir: Path) -> dict[str, Any]:
    try:
        manifest = load_project_manifest(project_dir)
    except ProjectManifestError as exc:
        draft = _load_json(project_dir / DRAFT_PROJECT_PATH)
        if draft:
            return {
                "project_id": draft.get("project_id") or project_dir.name,
                "name": draft.get("name") or project_dir.name,
                "description": draft.get("description") or "",
                "project_type": draft.get("project_type") or "alternatives_review",
                "input_count": 0,
                "assumptions": draft.get("assumptions", {}) if isinstance(draft.get("assumptions"), dict) else {},
                "report_profile": None,
                "manifest_status": "draft",
                "error": "",
            }
        return {
            "project_id": project_dir.name,
            "name": project_dir.name,
            "description": "",
            "project_type": "",
            "input_count": 0,
            "assumptions": {},
            "manifest_status": "missing",
            "error": str(exc),
        }
    return {
        "project_id": manifest.project_id,
        "name": manifest.name,
        "description": manifest.description,
        "project_type": manifest.project_type,
        "input_count": len(manifest.inputs),
        "assumptions": manifest.assumptions,
        "report_profile": manifest.report_profile,
        "manifest_status": "valid",
        "error": "",
    }


def _find_review_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    requested = str(item_id or "")
    for item in _dict_list(queue.get("items", [])):
        if requested in {str(item.get("id", "")), str(item.get("target_id", "")), str(item.get("deliverable_item_id", ""))}:
            return item
    raise WebAdapterError("Review item does not exist.")


def _queue_row(item: dict[str, Any]) -> dict[str, Any]:
    table_id = str(item.get("table_id") or "")
    figure_id = str(item.get("figure_id") or "")
    attachment_id = str(item.get("attachment_id") or "")
    related_table_ids = _string_list(item.get("related_table_ids", []))
    related_figure_ids = _string_list(item.get("related_figure_ids", []))
    related_attachment_ids = _string_list(item.get("related_attachment_ids", []))
    render_policy = _render_policy_fields(item)
    manual_material = _manual_material_fields(item)
    return {
        "id": str(item.get("id") or item.get("deliverable_item_id") or item.get("target_id") or ""),
        "deliverable_item_id": str(item.get("deliverable_item_id") or ""),
        "target_id": str(item.get("target_id") or ""),
        "title": str(item.get("title") or ""),
        "type": str(item.get("type") or ""),
        "status": _status(item),
        "export_eligible": bool(item.get("export_eligible", False)),
        "section_order": item.get("section_order"),
        "heading_level": item.get("heading_level"),
        "table_id": table_id,
        "figure_id": figure_id,
        "attachment_id": attachment_id,
        "related_table_ids": related_table_ids,
        "related_figure_ids": related_figure_ids,
        "related_attachment_ids": related_attachment_ids,
        "related_finding_ids": _string_list(item.get("related_finding_ids", [])),
        "related_constraint_ids": _string_list(item.get("related_constraint_ids", [])),
        "evidence_refs": _string_list(item.get("evidence_refs", [])),
        "display_table_refs": [table_id] if table_id else related_table_ids,
        "display_figure_refs": [figure_id] if figure_id else related_figure_ids,
        "display_attachment_refs": [attachment_id] if attachment_id else related_attachment_ids,
        "comparison_unit_ids": _string_list(item.get("comparison_unit_ids", [])),
        "validation_issue_count": len(_dict_list(item.get("validation_issues", []))),
        "manual_material": manual_material,
        "updated_at": item.get("updated_at"),
        **render_policy,
        "render_policy": render_policy,
    }


def _readiness_blocker(item: dict[str, Any]) -> dict[str, str] | None:
    status = _status(item)
    if status in BLOCKING_STATUSES:
        return _blocker(item, f"status_{status}")
    if status == "replaced" and not str(item.get("replacement_content") or "").strip():
        return _blocker(item, "replacement_content_missing")
    if status == "unable_to_verify":
        if not item.get("export_eligible"):
            return _blocker(item, "unable_to_verify_not_export_eligible")
        if not _best_review_content(item):
            return _blocker(item, "unable_to_verify_missing_content")
    if status not in TERMINAL_STATUSES and status != "unable_to_verify":
        return _blocker(item, f"status_{status or 'unknown'}")
    return None


def _blocker(item: dict[str, Any], reason: str) -> dict[str, str]:
    return {
        "id": str(item.get("id") or item.get("deliverable_item_id") or item.get("target_id") or ""),
        "title": str(item.get("title") or ""),
        "status": _status(item),
        "reason": reason,
    }


def _is_terminal_or_export_includable(item: dict[str, Any]) -> bool:
    status = _status(item)
    if status == "declined":
        return True
    if status in {"accepted", "edited"}:
        return True
    if status == "replaced":
        return bool(str(item.get("replacement_content") or "").strip())
    if status == "unable_to_verify":
        return bool(item.get("export_eligible")) and bool(_best_review_content(item))
    return False


def _status(item: dict[str, Any]) -> str:
    status = str(item.get("status") or "").strip()
    return "declined" if status == "rejected" else status


def _is_figure_item(item: dict[str, Any]) -> bool:
    return str(item.get("type") or "") in {"figure", "map_figure"} or bool(str(item.get("figure_id") or "").strip())


def _effective_figure_caption(item: dict[str, Any], assumptions: dict[str, Any]) -> str:
    figure_review = item.get("figure_review", {}) if isinstance(item.get("figure_review"), dict) else {}
    reviewed = str(figure_review.get("caption") or "").strip()
    if reviewed:
        return reviewed
    edited = str(item.get("edited_content") or "").strip()
    if _is_figure_item(item) and edited:
        return edited
    return _generated_figure_caption(item, assumptions)


def _generated_figure_caption(item: dict[str, Any], assumptions: dict[str, Any]) -> str:
    return str(item.get("caption") or assumptions.get("caption") or "").strip()


def _effective_figure_image_path(item: dict[str, Any], assumptions: dict[str, Any]) -> str:
    figure_review = item.get("figure_review", {}) if isinstance(item.get("figure_review"), dict) else {}
    reviewed = str(figure_review.get("image_path") or "").strip()
    if reviewed:
        return reviewed
    replacement = str(item.get("replacement_content") or "").strip()
    if _is_figure_item(item) and Path(replacement).suffix.lower() in FIGURE_REPLACEMENT_EXTENSIONS:
        return replacement
    return str(item.get("image_path") or assumptions.get("image_path") or "").strip()


def _figure_caption_source(item: dict[str, Any]) -> str:
    figure_review = item.get("figure_review", {}) if isinstance(item.get("figure_review"), dict) else {}
    if figure_review.get("caption_source"):
        return str(figure_review["caption_source"])
    if _is_figure_item(item) and str(item.get("edited_content") or "").strip():
        return "edited_caption"
    return "generated_caption"


def _figure_image_source(item: dict[str, Any]) -> str:
    figure_review = item.get("figure_review", {}) if isinstance(item.get("figure_review"), dict) else {}
    if figure_review.get("image_source"):
        return str(figure_review["image_source"])
    if _is_figure_item(item) and Path(str(item.get("replacement_content") or "")).suffix.lower() in FIGURE_REPLACEMENT_EXTENSIONS:
        return "replacement_figure"
    return "generated_figure"


def _store_figure_replacement(project_dir: Path, item: dict[str, Any], upload: Any | None) -> str:
    filename = str(getattr(upload, "filename", "") or "").strip()
    if not filename:
        return ""
    safe_name = _safe_upload_filename(filename)
    if Path(safe_name).suffix.lower() not in FIGURE_REPLACEMENT_EXTENSIONS:
        allowed = ", ".join(sorted(FIGURE_REPLACEMENT_EXTENSIONS))
        raise WebAdapterError(f"Replacement figure must be one of: {allowed}.")
    item_key = _safe_filename_component(str(item.get("id") or item.get("figure_id") or "figure"))
    destination_dir = _safe_project_subdir(project_dir, FIGURE_REPLACEMENTS_DIR / item_key)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = (destination_dir / safe_name).resolve()
    if not _is_relative_to(destination, project_dir.resolve()):
        raise WebAdapterError("Replacement figure path escapes the selected project.")
    try:
        upload.save(destination)
    except OSError as exc:
        raise WebAdapterError(f"Replacement figure could not be saved: {exc}") from exc
    return destination.relative_to(project_dir.resolve()).as_posix()


def _safe_filename_component(value: str) -> str:
    component = secure_filename(re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or ""))).strip("._-")
    return component or "figure"


def _best_review_content(item: dict[str, Any]) -> str:
    return str(item.get("replacement_content") or item.get("edited_content") or item.get("generated_content") or "").strip()


def _remaining_review_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if not _is_terminal_or_export_includable(item))


def _source_status_rows(source_status: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(source_status, dict):
        return rows
    for item in _dict_list(source_status.get("statuses", [])):
        rows.append(
            {
                "category": str(item.get("category") or ""),
                "status": str(item.get("status") or ""),
                "requirement": str(item.get("requirement") or ""),
                "source_ids": _string_list(item.get("source_ids", []))[:5],
                "notes": str(item.get("notes") or ""),
            }
        )
    return rows


def _issue_rows(data: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        return rows
    for issue in _dict_list(data.get("validation_issues", [])):
        details = issue.get("details", {})
        if not isinstance(details, dict):
            details = {}
        rows.append(
            {
                "stage": stage,
                "severity": str(issue.get("severity") or ""),
                "code": str(issue.get("code") or ""),
                "message": str(issue.get("message") or ""),
                "details": details,
                "details_summary": str(details.get("summary") or ""),
            }
        )
    return rows


def _workflow_step(label: str, status: str, message: str, artifact_path: Path) -> dict[str, str]:
    return {
        "label": label,
        "status": status,
        "message": message,
        "artifact_path": artifact_path.as_posix(),
    }


def _artifact_status(data: Any) -> str:
    return "available" if isinstance(data, dict) and data else "missing"


def _manifest_gate_status(project_dir: Path) -> str:
    manifest = _load_json(project_dir / EXPORT_MANIFEST_PATH)
    if isinstance(manifest, dict) and manifest:
        return str(manifest.get("review_gate_status") or "unknown")
    return "not_exported"


def _project_pipeline_status(project_dir: Path) -> str:
    if not (project_dir / MANIFEST_PATH).exists() and (project_dir / DRAFT_PROJECT_PATH).exists():
        return "draft_setup"
    populate_manifest = _load_json(project_dir / POPULATE_FOR_REVIEW_PATH)
    if isinstance(populate_manifest, dict) and populate_manifest:
        return str(populate_manifest.get("status") or "unknown")
    if (project_dir / REVIEW_QUEUE_PATH).exists():
        return "review_queue_ready"
    if (project_dir / DELIVERABLE_ITEMS_PATH).exists():
        return "deliverable_items_ready"
    return "not_populated"


def _manifest_summary_row(project_dir: Path, relative_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    path = project_dir / relative_path
    return {
        "exists": path.exists(),
        "relative_path": relative_path.as_posix(),
        "status": str(manifest.get("package_status") or manifest.get("status") or "") if isinstance(manifest, dict) else "",
        "review_gate_status": str(manifest.get("review_gate_status") or "") if isinstance(manifest, dict) else "",
        "preview_mode": bool(manifest.get("preview_mode", False)) if isinstance(manifest, dict) else False,
        "final_verification_status": _nested_string(manifest, "final_verification", "status"),
        "modified_at": _modified_at(path) if path.exists() else "",
    }


def _allowed_artifact_rows(project_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    export_manifest = _load_json(project_dir / EXPORT_MANIFEST_PATH)
    package_manifest = _load_json(project_dir / DEMO_DELIVERABLE_MANIFEST_PATH)
    for label, manifest, path_keys in (
        ("Export manifest", export_manifest, ("output_path", "markdown_path", "docx_path")),
        ("Package manifest", package_manifest, ("output_path", "export_manifest_path", "markdown_path", "docx_path")),
    ):
        if not isinstance(manifest, dict):
            continue
        for key in path_keys:
            rel = _artifact_link_path(project_dir, str(manifest.get(key) or ""))
            if rel:
                rows.append(
                    {
                        "label": f"{label}: {key}",
                        "relative_path": rel,
                        "kind": key,
                    }
                )
    try:
        queue = _load_standard_queue(project_dir)
    except WebAdapterError:
        queue = {}
    for item in _dict_list(queue.get("items", [])):
        if item.get("type") != "figure":
            continue
        assumptions = item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {}
        rel = _artifact_link_path(project_dir, _effective_figure_image_path(item, assumptions))
        if rel:
            rows.append(
                {
                    "label": f"Figure asset: {item.get('figure_id') or item.get('id')}",
                    "relative_path": rel,
                    "kind": "figure_image",
                }
            )
    deduped: dict[str, dict[str, str]] = {}
    for row in rows:
        path = row["relative_path"]
        if path and (project_dir / path).exists():
            deduped[path] = row
    return sorted(deduped.values(), key=lambda item: item["relative_path"])


def _artifact_link_path(project_dir: Path, value: str) -> str:
    if not value:
        return ""
    try:
        rel = _safe_relative_path(project_dir, value)
    except WebAdapterError:
        return ""
    return rel.as_posix()


def _project_relative_path(project_dir: Path, value: str) -> str:
    if not value:
        return ""
    try:
        return _safe_relative_path(project_dir, value).as_posix()
    except WebAdapterError:
        return str(value)


def _safe_relative_path(project_dir: Path, value: str) -> Path:
    if not value:
        raise WebAdapterError("Missing artifact path.")
    root = project_dir.resolve()
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    if not _is_relative_to(candidate, root):
        raise WebAdapterError("Artifact path escapes the selected project.")
    relative = candidate.relative_to(root)
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise WebAdapterError("Invalid artifact path.")
    return relative


def _safe_project_subdir(project_dir: Path, relative_path: Path) -> Path:
    root = project_dir.resolve()
    path = (root / relative_path).resolve()
    if not _is_relative_to(path, root):
        raise WebAdapterError("Project subdirectory escapes the selected project.")
    return path


def _safe_upload_filename(value: str) -> str:
    original = str(value or "").strip()
    if not original:
        raise WebAdapterError("Upload filename is required.")
    if "/" in original or "\\" in original or Path(original).is_absolute():
        raise WebAdapterError("Upload filename cannot contain path separators.")
    if original in {".", ".."} or original.startswith("."):
        raise WebAdapterError("Upload filename cannot be hidden or relative.")
    safe = secure_filename(original)
    if not safe or safe in {".", ".."} or safe.startswith("."):
        raise WebAdapterError("Upload filename is not safe.")
    if safe != original:
        raise WebAdapterError("Upload filename contains unsupported characters.")
    _reject_reserved_name(safe, "Upload filename")
    return safe


def _default_input_role(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension in PROJECT_GEOMETRY_EXTENSIONS:
        return "alternatives"
    if extension in SOURCE_LAYER_EXTENSIONS:
        return "source_layer"
    if extension in DOCUMENT_EXTENSIONS:
        return "supporting_report"
    if extension in IMAGERY_EXTENSIONS:
        return "imagery_or_basemap"
    return "unknown"


def _reject_reserved_name(value: str, label: str) -> None:
    stem = Path(value).stem.upper()
    if stem in WINDOWS_RESERVED_NAMES:
        raise WebAdapterError(f"{label} uses a reserved Windows name.")


def _write_run_status(
    project_dir: Path,
    *,
    action: str,
    status: str,
    message: str,
    artifact_path: str = "",
    error: str = "",
) -> dict[str, Any]:
    now = _utc_now()
    existing = latest_run_status(project_dir)
    started_at = existing.get("started_at") if existing.get("action") == action and existing.get("status") == "started" else now
    record = {
        "action": action,
        "status": status,
        "started_at": started_at,
        "completed_at": now if status in {"completed", "failed"} else "",
        "message": message,
        "artifact_path": artifact_path,
        "error": _short_error(error),
    }
    _write_json(project_dir / WEB_RUN_STATUS_PATH, record)
    return record


def _short_error(value: str) -> str:
    text = " ".join(str(value or "").split())
    return text[:500]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _compact_assumptions(assumptions: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "resource_category",
        "target_type",
        "section_order",
        "heading_level",
        "row_count",
        "columns",
        "matrix_target",
        "source_gap_status",
        "render_policy",
    }
    return {key: value for key, value in assumptions.items() if key in allowed}


def _render_policy_fields(item: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "policy_inclusion_status": "default",
        "policy_activation_condition": "always",
        "policy_review_requirement": "standard_review",
        "policy_comparison_unit_expansion": "none",
        "render_decision": "include_body",
        "render_destination": "report_body",
        "render_decision_reason": "No render gating applies.",
        "report_body_eligible": True,
    }
    result: dict[str, Any] = {}
    for key in RENDER_POLICY_FIELDS:
        value = item.get(key, defaults[key])
        result[key] = _coerce_bool(value) if key == "report_body_eligible" else str(value)
    result["report_role_label"] = REPORT_ROLE_LABELS.get(result["render_decision"], _title_from_enum(result["render_decision"]))
    result["output_destination_label"] = OUTPUT_DESTINATION_LABELS.get(
        result["render_destination"],
        _title_from_enum(result["render_destination"]),
    )
    return result


def _title_from_enum(value: str) -> str:
    return str(value or "").replace("_", " ").replace("-", " ").title()


def _manual_material_fields(item: dict[str, Any]) -> dict[str, Any]:
    record = item.get("manual_material", {}) if isinstance(item.get("manual_material"), dict) else {}
    return {
        "material_type": str(record.get("material_type") or "none"),
        "material_status": str(record.get("material_status") or "not_used"),
        "export_behavior": str(record.get("export_behavior") or "do_not_export"),
        "reviewer_action": str(record.get("reviewer_action") or ""),
        "source_refs": _string_list(item.get("source_refs", [])) or _string_list(record.get("source_refs", [])),
        "source_categories": _string_list(record.get("source_categories", [])),
        "internal_note_only": bool(record.get("internal_note_only", False)),
    }


def _find_deliverable_figure(figures_artifact: dict[str, Any], figure_id: str) -> dict[str, Any]:
    for figure in [*_dict_list(figures_artifact.get("figures", [])), *_dict_list(figures_artifact.get("attachment_supporting_figures", []))]:
        if str(figure.get("figure_id") or "") == figure_id:
            return figure
    raise WebAdapterError(f"Figure artifact is not available for '{figure_id}'.")


def _style_editor_layers(recipe: dict[str, Any], active_override: dict[str, Any] | None) -> list[dict[str, Any]]:
    override_by_layer = {
        str(layer.get("layer_id") or ""): layer
        for layer in _dict_list((active_override or {}).get("overrides", []))
    }
    rows: list[dict[str, Any]] = []
    for index, layer in enumerate(_dict_list(recipe.get("layers", []))):
        layer_id = str(layer.get("layer_id") or "")
        override = override_by_layer.get(layer_id, {})
        default_style = layer.get("default_style") if isinstance(layer.get("default_style"), dict) else {}
        label_fields = _string_list(layer.get("allowed_label_fields", [])) or _string_list(layer.get("label_fields", []))
        rows.append(
            {
                "index": index,
                "layer_id": layer_id,
                "layer_type": str(layer.get("layer_type") or ""),
                "source_id": str(layer.get("source_id") or ""),
                "feature_count": _int_value(layer.get("feature_count")),
                "geometry_type_counts": layer.get("geometry_type_counts") if isinstance(layer.get("geometry_type_counts"), dict) else {},
                "label_fields": label_fields,
                "defaults": {
                    "visible": bool(layer.get("default_visible", True)),
                    "z_index": _int_value(layer.get("default_z_index"), index),
                    "display_name": str(layer.get("default_display_name") or layer_id),
                    "fill_color": str(default_style.get("fill_color") or ""),
                    "fill_opacity": default_style.get("fill_opacity") if default_style.get("fill_opacity") is not None else "",
                    "stroke_color": str(default_style.get("stroke_color") or ""),
                    "stroke_width": default_style.get("stroke_width") if default_style.get("stroke_width") is not None else "",
                    "point_size": default_style.get("point_size") if default_style.get("point_size") is not None else "",
                    "label_visible": False,
                    "label_field": "",
                },
                "current": {
                    "visible": override.get("visible", bool(layer.get("default_visible", True))),
                    "z_index": override.get("z_index", _int_value(layer.get("default_z_index"), index)),
                    "display_name": override.get("display_name", str(layer.get("default_display_name") or layer_id)),
                    "fill_color": override.get("fill_color", str(default_style.get("fill_color") or "")),
                    "fill_opacity": override.get("fill_opacity", default_style.get("fill_opacity") if default_style.get("fill_opacity") is not None else ""),
                    "stroke_color": override.get("stroke_color", str(default_style.get("stroke_color") or "")),
                    "stroke_width": override.get("stroke_width", default_style.get("stroke_width") if default_style.get("stroke_width") is not None else ""),
                    "point_size": override.get("point_size", default_style.get("point_size") if default_style.get("point_size") is not None else ""),
                    "label_visible": override.get("label_visible", False),
                    "label_field": override.get("label_field", ""),
                },
                "override": override,
            }
        )
    return rows


def _style_layers_from_form(form: Any) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    layer_ids = [str(value) for value in form.getlist("layer_id") if str(value).strip()]
    fields = (
        "visible",
        "z_index",
        "display_name",
        "fill_color",
        "fill_opacity",
        "stroke_color",
        "stroke_width",
        "point_size",
        "label_visible",
        "label_field",
    )
    for index, layer_id in enumerate(layer_ids):
        layer: dict[str, Any] = {"layer_id": layer_id}
        for field in fields:
            key = f"layer_{index}_{field}"
            if key not in form:
                continue
            layer[field] = str(form.get(key) or "").strip()
        layers.append(layer)
    return layers


def _latest_by_timestamp(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    return sorted(records, key=lambda item: str(item.get("updated_at") or item.get("completed_at") or item.get("created_at") or ""))[-1]


def _figure_style_model_paths(project_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        "recipes": _style_model_path_row(project_dir, FIGURE_RECIPES_PATH),
        "style_overrides": _style_model_path_row(project_dir, FIGURE_STYLE_OVERRIDES_PATH),
        "versions": _style_model_path_row(project_dir, FIGURE_VERSIONS_PATH),
        "render_jobs": _style_model_path_row(project_dir, FIGURE_RENDER_JOBS_PATH),
    }


def _style_model_path_row(project_dir: Path, relative_path: Path) -> dict[str, Any]:
    path = project_dir / relative_path
    return {
        "relative_path": relative_path.as_posix(),
        "exists": path.exists(),
        "modified_at": _modified_at(path) if path.exists() else "",
    }


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _provenance_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    gpt = value.get("gpt_interpretive_assist", {}) if isinstance(value.get("gpt_interpretive_assist"), dict) else {}
    fingerprint = gpt.get("fingerprint", {}) if isinstance(gpt.get("fingerprint"), dict) else {}
    fallback = (
        value.get("gpt_interpretive_assist_fallback", {})
        if isinstance(value.get("gpt_interpretive_assist_fallback"), dict)
        else {}
    )
    fallback_fingerprint = fallback.get("fingerprint", {}) if isinstance(fallback.get("fingerprint"), dict) else {}
    return {
        "artifact": value.get("artifact"),
        "artifact_path": value.get("artifact_path"),
        "deliverable_item_id": value.get("deliverable_item_id"),
        "target_id": value.get("target_id"),
        "review_before_export": value.get("review_before_export"),
        "gpt_interpretive_assist": {
            "enabled": bool(gpt),
            "draft_provider": gpt.get("draft_provider", ""),
            "model": gpt.get("model", ""),
            "prompt_version": gpt.get("prompt_version", ""),
            "cached": bool(gpt.get("cached", False)),
            "generated_at": gpt.get("generated_at", ""),
            "review_before_export": bool(gpt.get("review_before_export", False)),
            "source_refs_used": _string_list(gpt.get("source_refs_used", [])),
            "table_refs_used": _string_list(gpt.get("table_refs_used", [])),
            "figure_refs_used": _string_list(gpt.get("figure_refs_used", [])),
            "token_usage": _token_usage_summary(gpt.get("token_usage", {})),
            "evidence_payload_hash": str(fingerprint.get("evidence_payload_hash", ""))[:12],
            "section_policy_hash": str(fingerprint.get("section_policy_hash", ""))[:12],
            "prompt_contract_hash": str(fingerprint.get("prompt_contract_hash", ""))[:12],
            "style_context_hash": str(fingerprint.get("style_context_hash", ""))[:12],
        },
        "gpt_interpretive_assist_fallback": {
            "enabled": bool(fallback),
            "reason": str(fallback.get("reason", "")),
            "reason_code": str(fallback.get("reason_code", "")),
            "draft_provider": str(fallback.get("draft_provider", "")),
            "model": str(fallback.get("model", "")),
            "prompt_version": str(fallback.get("prompt_version", "")),
            "generated_at": str(fallback.get("generated_at", "")),
            "review_before_export": bool(fallback.get("review_before_export", False)),
            "deterministic_content_retained": bool(fallback.get("deterministic_content_retained", False)),
            "source_refs_used": _string_list(fallback.get("source_refs_used", [])),
            "table_refs_used": _string_list(fallback.get("table_refs_used", [])),
            "figure_refs_used": _string_list(fallback.get("figure_refs_used", [])),
            "token_usage": _token_usage_summary(fallback.get("token_usage", {})),
            "evidence_payload_hash": str(fallback_fingerprint.get("evidence_payload_hash", ""))[:12],
            "section_policy_hash": str(fallback_fingerprint.get("section_policy_hash", ""))[:12],
            "prompt_contract_hash": str(fallback_fingerprint.get("prompt_contract_hash", ""))[:12],
            "style_context_hash": str(fallback_fingerprint.get("style_context_hash", ""))[:12],
            "validation_issues": _dict_list(fallback.get("validation_issues", [])),
        },
    }


def _token_usage_summary(value: Any) -> dict[str, int]:
    usage = value if isinstance(value, dict) else {}
    return {
        key: int(usage.get(key, 0))
        for key in ("input_tokens", "output_tokens", "total_tokens")
        if isinstance(usage.get(key), int) and int(usage.get(key, 0)) > 0
    }


def _review_body_text(value: Any) -> str:
    return str(value or "").strip()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _nested_string(data: dict[str, Any], *keys: str) -> str:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return str(current or "")


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _modified_at(path: Path) -> str:
    try:
        timestamp = path.stat().st_mtime
    except OSError:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _project_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
