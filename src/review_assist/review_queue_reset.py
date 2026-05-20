"""Developer/test reset for generated deliverable review candidates."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .deliverable import DEMO_DELIVERABLE_MANIFEST_PATH
from .deliverable_figures import DELIVERABLE_FIGURES_PATH
from .deliverable_items import DELIVERABLE_ITEMS_PATH
from .deliverable_tables import DELIVERABLE_TABLES_PATH
from .evidence_package import EVIDENCE_PACKAGE_PATH
from .export_report import (
    EXPORT_DOCX_PATH,
    EXPORT_FIGURE_ASSETS_DIR,
    EXPORT_MANIFEST_PATH,
    EXPORT_MARKDOWN_PATH,
)
from .maps import MAP_MANIFEST_PATH
from .populate_for_review import PopulateForReviewError, populate_for_review
from .report_sections import REPORT_SECTIONS_PATH
from .review_queue import REVIEW_QUEUE_PATH


RESET_WARNING = (
    "This developer/test reset removes generated deliverable review candidates "
    "and refreshes deterministic upstream review artifacts before rebuilding the standard review queue. "
    "It does not acquire sources, materialize NAIP imagery, run GPT drafting, or delete source data."
)
PROCESS_LANGUAGE_PATTERNS = (
    "draft review candidate",
    "related table status",
    "reviewer focus",
    "this content is draft/pre-review",
    "pre-review",
    "reviewer verification",
)
DEFAULT_RESET_PATHS = (DELIVERABLE_ITEMS_PATH, REVIEW_QUEUE_PATH)
EXPORT_RESET_PATHS = (
    EXPORT_MANIFEST_PATH,
    DEMO_DELIVERABLE_MANIFEST_PATH,
    EXPORT_MARKDOWN_PATH,
    EXPORT_DOCX_PATH,
    EXPORT_FIGURE_ASSETS_DIR,
)


class ReviewQueueResetError(RuntimeError):
    """Raised when the developer review queue reset cannot complete."""


def reset_review_queue(
    project_dir: Path,
    *,
    regenerate: bool = True,
    dry_run: bool = False,
    include_evidence: bool = False,
    include_exports: bool = False,
) -> dict[str, Any]:
    """Remove generated review candidates and optionally rebuild review artifacts.

    This is intentionally a developer/testing helper. Regeneration runs the
    deterministic populate pipeline without source acquisition, local source
    materialization, NAIP materialization, or GPT drafting so review candidates
    are rebuilt from current local project inputs and registered source layers.
    """

    project_dir = project_dir.resolve()
    before = _artifact_counts(project_dir)
    reset_paths = [*DEFAULT_RESET_PATHS]
    if include_evidence:
        reset_paths.append(EVIDENCE_PACKAGE_PATH)
    if include_exports:
        reset_paths.extend(EXPORT_RESET_PATHS)

    existing_targets = [_path_record(project_dir, relative_path) for relative_path in reset_paths if (project_dir / relative_path).exists()]
    result: dict[str, Any] = {
        "project_dir": str(project_dir),
        "warning": RESET_WARNING,
        "dry_run": dry_run,
        "include_evidence": include_evidence,
        "include_exports": include_exports,
        "refresh_upstream_artifacts": bool(regenerate),
        "regenerate": regenerate,
        "before": before,
        "would_delete": existing_targets,
        "would_refresh": _refreshed_artifacts() if regenerate else [],
        "deleted": [],
        "regenerated": [],
        "after": before if dry_run else {},
        "process_language": {
            "before": _process_language_summary(project_dir),
            "after": {},
        },
        "preserved_by_default": _preserved_artifacts(),
    }
    if dry_run:
        result["after"] = _artifact_counts(project_dir)
        result["process_language"]["after"] = _process_language_summary(project_dir)
        return result

    deleted: list[dict[str, str]] = []
    for record in existing_targets:
        relative_path = Path(record["relative_path"])
        target = project_dir / relative_path
        _delete_target(target)
        deleted.append(record)
    result["deleted"] = deleted

    regenerated: list[dict[str, Any]] = []
    if regenerate:
        try:
            populate = populate_for_review(
                project_dir,
                prepare_sources=False,
                include_optional_sources=False,
                materialize_local_sources=False,
                materialize_naip_basemap=False,
                gpt_drafting=False,
            )
            regenerated.extend(_populate_regenerated_records(populate))
        except PopulateForReviewError as exc:
            raise ReviewQueueResetError(str(exc)) from exc
    result["regenerated"] = regenerated
    result["after"] = _artifact_counts(project_dir)
    result["process_language"]["after"] = _process_language_summary(project_dir)
    return result


def _delete_target(target: Path) -> None:
    if target.is_dir():
        shutil.rmtree(target)
    elif target.exists():
        target.unlink()


def _path_record(project_dir: Path, relative_path: Path) -> dict[str, str]:
    target = project_dir / relative_path
    kind = "directory" if target.is_dir() else "file"
    return {"relative_path": relative_path.as_posix(), "kind": kind}


def _regenerated_record(kind: str, artifact: dict[str, Any]) -> dict[str, Any]:
    path = str(artifact.get("output_path") or "")
    count = artifact.get("item_count", artifact.get("evidence_record_count", artifact.get("section_count")))
    return {"artifact": kind, "output_path": path, "item_count": count}


def _populate_regenerated_records(populate: dict[str, Any]) -> list[dict[str, Any]]:
    paths = populate.get("artifact_paths", {}) if isinstance(populate.get("artifact_paths"), dict) else {}
    counts = {
        "comparison_unit_constraints": populate.get("comparison_unit_constraint_count"),
        "deliverable_tables": populate.get("deliverable_table_count"),
        "deliverable_figures": populate.get("deliverable_figure_count"),
        "deliverable_items": populate.get("deliverable_item_count"),
        "review_queue": populate.get("review_queue_item_count"),
    }
    artifacts = [
        "input_package",
        "project_geometry",
        "project_area",
        "comparison_units",
        "project_context",
        "source_status",
        "source_inventory",
        "constraint_results",
        "comparison_unit_constraints",
        "draft_findings",
        "comparison_tables",
        "deliverable_tables",
        "deliverable_figures",
        "map_manifest",
        "evidence_package",
        "report_sections",
        "deliverable_items",
        "review_queue",
    ]
    return [
        {
            "artifact": artifact,
            "output_path": str(paths.get(artifact) or ""),
            "item_count": counts.get(artifact),
        }
        for artifact in artifacts
    ]


def _artifact_counts(project_dir: Path) -> dict[str, Any]:
    deliverable_items = _read_json(project_dir / DELIVERABLE_ITEMS_PATH)
    review_queue = _read_json(project_dir / REVIEW_QUEUE_PATH)
    evidence = _read_json(project_dir / EVIDENCE_PACKAGE_PATH)
    deliverable_tables = _read_json(project_dir / DELIVERABLE_TABLES_PATH)
    deliverable_figures = _read_json(project_dir / DELIVERABLE_FIGURES_PATH)
    map_manifest = _read_json(project_dir / MAP_MANIFEST_PATH)
    report_sections = _read_json(project_dir / REPORT_SECTIONS_PATH)
    return {
        "deliverable_items_exists": bool(deliverable_items),
        "deliverable_item_count": _count_value(deliverable_items),
        "review_queue_exists": bool(review_queue),
        "review_queue_item_count": _count_value(review_queue),
        "deliverable_tables_exists": bool(deliverable_tables),
        "deliverable_table_count": _count_value(deliverable_tables),
        "deliverable_figures_exists": bool(deliverable_figures),
        "deliverable_figure_count": _count_value(deliverable_figures),
        "map_manifest_exists": bool(map_manifest),
        "map_figure_count": _count_value(map_manifest),
        "evidence_package_exists": bool(evidence),
        "evidence_item_count": _count_value(evidence),
        "report_sections_exists": bool(report_sections),
        "report_section_count": _count_value(report_sections),
        "export_manifest_exists": (project_dir / EXPORT_MANIFEST_PATH).exists(),
        "deliverable_package_manifest_exists": (project_dir / DEMO_DELIVERABLE_MANIFEST_PATH).exists(),
    }


def _count_value(data: dict[str, Any]) -> int:
    for key in ("item_count", "record_count", "evidence_record_count", "table_count", "figure_count"):
        value = data.get(key)
        if isinstance(value, int):
            return value
    items = data.get("items")
    if isinstance(items, list):
        return len(items)
    records = data.get("records")
    if isinstance(records, list):
        return len(records)
    return 0


def _process_language_summary(project_dir: Path) -> dict[str, Any]:
    summaries = {
        "deliverable_items": _scan_process_language(project_dir / DELIVERABLE_ITEMS_PATH),
        "review_queue": _scan_process_language(project_dir / REVIEW_QUEUE_PATH),
    }
    return {
        "has_process_language": any(summary["has_process_language"] for summary in summaries.values()),
        "artifacts": summaries,
    }


def _scan_process_language(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "has_process_language": False, "matches": []}
    text = path.read_text(encoding="utf-8").lower()
    matches = [pattern for pattern in PROCESS_LANGUAGE_PATTERNS if pattern in text]
    return {"exists": True, "has_process_language": bool(matches), "matches": matches}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewQueueResetError(f"Invalid JSON artifact: {path}: {exc}") from exc
    if isinstance(data, dict):
        return data
    raise ReviewQueueResetError(f"Expected JSON object artifact: {path}")


def _preserved_artifacts() -> list[str]:
    return [
        "config/sources.json",
        "layers/",
        "source_acquisition/",
        "source_materialization/",
        "basemaps/",
        "exports/ unless --include-exports is used",
    ]


def _refreshed_artifacts() -> list[str]:
    return [
        "context/input_package.json",
        "context/project_context.json",
        "context/project_area.json",
        "intermediate/project_geometry.json",
        "intermediate/comparison_units.json",
        "source_status/source_status_set.json",
        "source_inventory/source_inventory.json",
        "constraints/constraint_results.json",
        "constraints/comparison_unit_constraints.json",
        "findings/draft_findings.json",
        "tables/comparison_tables.json",
        "deliverable/tables.json",
        "deliverable/figures.json",
        "maps/map_manifest.json",
        "evidence/evidence_package.json",
        "drafts/report_sections.json",
        "deliverable/deliverable_items.json",
        "review_queue/review_queue.json",
    ]
