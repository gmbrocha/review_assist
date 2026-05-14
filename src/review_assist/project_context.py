"""Project context artifact generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .inspection import ProjectInspectionError, inspect_project
from .projects import ProjectManifestError, load_project_manifest
from .report_profiles import ReportProfileError, resolve_report_profile


PROJECT_CONTEXT_PATH = Path("context/project_context.json")


class ProjectContextError(RuntimeError):
    """Raised when project context generation cannot complete."""


def generate_project_context(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        report_profile = resolve_report_profile(manifest)
        inspection = inspect_project(project_dir)
    except (ProjectManifestError, ReportProfileError, ProjectInspectionError) as exc:
        raise ProjectContextError(str(exc)) from exc

    context_path = project_dir / PROJECT_CONTEXT_PATH
    context_path.parent.mkdir(parents=True, exist_ok=True)

    context = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_type": manifest.project_type,
        "description": manifest.description,
        "project_dir": str(project_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "context_path": str(context_path),
        "report_profile": {
            "profile_id": report_profile.profile_id,
            "name": report_profile.name,
            "required_categories": report_profile.required_categories,
            "optional_categories": report_profile.optional_categories,
        },
        "assumptions": manifest.assumptions,
        "special_reviewer_instructions": manifest.special_reviewer_instructions,
        "project_extent_wgs84": _combined_bounds(inspection["inputs"]),
        "input_roles": sorted({item["role"] for item in inspection["inputs"]}),
        "detected_inputs": inspection["inputs"],
        "detected_alternatives": _detected_alternatives(inspection["inputs"]),
        "validation_issues": _validation_issues(inspection["inputs"]),
        "geometry_summary_path": inspection["summary_path"],
    }
    context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
    return context


def load_project_context(project_dir: Path) -> dict[str, Any]:
    context_file = project_dir / PROJECT_CONTEXT_PATH
    if not context_file.exists():
        raise ProjectContextError(f"Missing project context artifact: {context_file}")
    try:
        data = json.loads(context_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectContextError(f"Invalid project context JSON: {context_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectContextError(f"Project context must be a JSON object: {context_file}")
    return data


def _combined_bounds(inputs: list[dict[str, Any]]) -> dict[str, float] | None:
    bounds = [item.get("bounds_wgs84") for item in inputs if isinstance(item.get("bounds_wgs84"), dict)]
    if not bounds:
        return None
    return {
        "west": min(float(item["west"]) for item in bounds),
        "south": min(float(item["south"]) for item in bounds),
        "east": max(float(item["east"]) for item in bounds),
        "north": max(float(item["north"]) for item in bounds),
    }


def _detected_alternatives(inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alternatives: list[dict[str, Any]] = []
    for item in inputs:
        role = str(item.get("role", ""))
        if "alternative" not in role:
            continue
        labels = item.get("candidate_labels", [])
        alternatives.append(
            {
                "input_path": item.get("input_path"),
                "role": role,
                "feature_count": item.get("feature_count"),
                "geometry_type_counts": item.get("geometry_type_counts", {}),
                "candidate_labels": labels if isinstance(labels, list) else [],
                "needs_reviewer_labeling": not bool(labels),
            }
        )
    return alternatives


def _validation_issues(inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for item in inputs:
        input_path = str(item.get("input_path", ""))
        for issue in item.get("validation_issues", []):
            if isinstance(issue, dict):
                copied = dict(issue)
                copied["input_path"] = input_path
                issues.append(copied)
    return issues
