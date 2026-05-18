"""Service adapter for the local Review Assist web UI.

This module is intentionally thin: it reads stable Sprint 1-3 artifacts and
calls existing services for mutation/export. It does not reinterpret raw GIS,
evidence, matrix, or report assembly internals.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from review_assist.comparison_units import COMPARISON_UNITS_METADATA_PATH
from review_assist.deliverable import DEMO_DELIVERABLE_MANIFEST_PATH
from review_assist.deliverable_items import DELIVERABLE_ITEMS_PATH
from review_assist.export_report import (
    EXPORT_MANIFEST_PATH,
    ExportGateError,
    ExportReportError,
    export_report,
)
from review_assist.input_package import INPUT_PACKAGE_PATH
from review_assist.populate_for_review import POPULATE_FOR_REVIEW_PATH, PopulateForReviewError, populate_for_review
from review_assist.project_area import PROJECT_AREA_PATH
from review_assist.project_context import PROJECT_CONTEXT_PATH
from review_assist.projects import MANIFEST_PATH, ProjectManifestError, load_project_manifest
from review_assist.review_queue import REVIEW_QUEUE_PATH, ReviewQueueError, load_review_queue, update_review_item
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
TERMINAL_STATUSES = {"accepted", "edited", "replaced", "declined"}
BLOCKING_STATUSES = {"draft", "needs_review", "needs_verification"}
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
REVIEW_PREVIEW_TEXT_LIMIT = 1200
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
        if not manifest_path.exists():
            continue
        error = ""
        project_id = child.name
        name = child.name
        try:
            manifest = load_project_manifest(child)
            project_id = manifest.project_id
            name = manifest.name
        except ProjectManifestError as exc:
            error = str(exc)
        projects.append(
            ProjectRef(
                project_key=child.name,
                project_id=project_id,
                name=name,
                path=_project_relative(root, child),
                modified_at=_modified_at(child),
                status=_project_pipeline_status(child),
                review_gate_status=_manifest_gate_status(child),
                error=error,
            )
        )
    return projects


def resolve_project_dir(project_root: str | Path | None, project_key: str) -> Path:
    """Resolve a selected project key to a direct child of project_root."""

    key = str(project_key or "").strip()
    if not key or not PROJECT_ID_RE.fullmatch(key) or key in {".", ".."}:
        raise WebAdapterError("Invalid project id.")
    root = project_root_path(project_root)
    project_dir = (root / key).resolve()
    if not _is_relative_to(project_dir, root):
        raise WebAdapterError("Project path escapes the configured project root.")
    if not project_dir.is_dir():
        raise WebAdapterError("Project does not exist.")
    if not (project_dir / MANIFEST_PATH).exists():
        raise WebAdapterError("Project manifest is missing.")
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
        "validation_issues": validation_issues,
    }


def run_populate(project_dir: Path) -> dict[str, Any]:
    """Run the existing populate-for-review service with conservative defaults."""

    try:
        return populate_for_review(project_dir, gpt_drafting=False)
    except PopulateForReviewError as exc:
        raise WebAdapterError(str(exc)) from exc


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
    image_path = str(item.get("image_path") or assumptions.get("image_path") or "").strip()
    return {
        **_queue_row(item),
        "generated_content": _trim_body_text(item.get("generated_content")),
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
            "caption": item.get("caption") or assumptions.get("caption"),
            "source_note": item.get("source_note") or assumptions.get("source_note"),
            "method_note": item.get("method_note") or assumptions.get("method_note"),
        },
        "provenance": _provenance_summary(item.get("provenance", {})),
        "source_refs": _string_list(item.get("source_refs", [])),
        "comparison_unit_ids": _string_list(item.get("comparison_unit_ids", [])),
        "reviewer_notes": _dict_list(item.get("reviewer_notes", [])),
        "validation_issues": _dict_list(item.get("validation_issues", [])),
        "uncertainty_flags": _string_list(item.get("uncertainty_flags", [])),
        "assumptions": _compact_assumptions(assumptions),
    }


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
            "preview_mode": False,
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
        "preview_mode": bool(manifest.get("preview_mode", False)) if isinstance(manifest, dict) else False,
        "last_export_manifest": _manifest_summary_row(project_dir, EXPORT_MANIFEST_PATH, manifest),
    }


def run_export(project_dir: Path, *, preview: bool) -> dict[str, Any]:
    """Run preview or reviewed export through the existing export service."""

    try:
        return export_report(project_dir, include_draft=preview, output_format="both")
    except ExportGateError as exc:
        raise WebAdapterError(str(exc)) from exc
    except ExportReportError as exc:
        raise WebAdapterError(str(exc)) from exc


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
        return {
            "project_id": project_dir.name,
            "name": project_dir.name,
            "description": "",
            "project_type": "",
            "input_count": 0,
            "assumptions": {},
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
        "error": "",
    }


def _find_review_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    requested = str(item_id or "")
    for item in _dict_list(queue.get("items", [])):
        if requested in {str(item.get("id", "")), str(item.get("target_id", "")), str(item.get("deliverable_item_id", ""))}:
            return item
    raise WebAdapterError("Review item does not exist.")


def _queue_row(item: dict[str, Any]) -> dict[str, Any]:
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
        "table_id": str(item.get("table_id") or ""),
        "figure_id": str(item.get("figure_id") or ""),
        "attachment_id": str(item.get("attachment_id") or ""),
        "comparison_unit_ids": _string_list(item.get("comparison_unit_ids", [])),
        "validation_issue_count": len(_dict_list(item.get("validation_issues", []))),
        "updated_at": item.get("updated_at"),
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
        rows.append(
            {
                "stage": stage,
                "severity": str(issue.get("severity") or ""),
                "code": str(issue.get("code") or ""),
                "message": str(issue.get("message") or ""),
            }
        )
    return rows


def _artifact_status(data: Any) -> str:
    return "available" if isinstance(data, dict) and data else "missing"


def _manifest_gate_status(project_dir: Path) -> str:
    manifest = _load_json(project_dir / EXPORT_MANIFEST_PATH)
    if isinstance(manifest, dict) and manifest:
        return str(manifest.get("review_gate_status") or "unknown")
    return "not_exported"


def _project_pipeline_status(project_dir: Path) -> str:
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
        rel = _artifact_link_path(project_dir, str(item.get("image_path") or assumptions.get("image_path") or ""))
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
    }
    return {key: value for key, value in assumptions.items() if key in allowed}


def _provenance_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "artifact": value.get("artifact"),
        "artifact_path": value.get("artifact_path"),
        "deliverable_item_id": value.get("deliverable_item_id"),
        "target_id": value.get("target_id"),
        "review_before_export": value.get("review_before_export"),
    }


def _trim_body_text(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) <= REVIEW_PREVIEW_TEXT_LIMIT:
        return text
    return text[:REVIEW_PREVIEW_TEXT_LIMIT].rstrip() + "\n\n[Preview limited in web UI; full reviewed content remains in the review queue artifact.]"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


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
