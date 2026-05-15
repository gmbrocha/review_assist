"""Source status set resolution for workflow-driven projects."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .project_context import ProjectContextError, generate_project_context
from .projects import ProjectManifestError, load_project_manifest
from .report_profiles import ReportProfileError, resolve_report_profile
from .source_catalog import (
    ProjectSource,
    SourceCatalog,
    SourceCatalogError,
    SourceDefinition,
    load_project_source_registry,
    load_source_catalog,
    resolve_project_source_path,
)


SOURCE_STATUS_PATH = Path("source_status/source_status_set.json")
SOURCE_ACQUISITION_PATH = Path("source_acquisition/source_acquisition_manifest.json")


class SourceStatusError(RuntimeError):
    """Raised when source status resolution cannot complete."""


def resolve_source_status_set(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        report_profile = resolve_report_profile(manifest)
        catalog = load_source_catalog()
        registry = load_project_source_registry(project_dir)
        project_context = generate_project_context(project_dir)
    except (ProjectManifestError, ReportProfileError, SourceCatalogError, ProjectContextError) as exc:
        raise SourceStatusError(str(exc)) from exc

    output_path = project_dir / SOURCE_STATUS_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    categories = list(report_profile.required_categories) + [
        category for category in report_profile.optional_categories if category not in report_profile.required_categories
    ]
    catalog_by_category = _catalog_by_category(catalog)
    project_sources = registry.by_source_id()
    latest_download_status = _latest_download_status(_load_download_records(project_dir))
    validation_issues = _unknown_project_sources(project_sources, catalog)

    statuses = [
        _category_status(
            project_dir=project_dir,
            category=category,
            requirement="required" if category in report_profile.required_categories else "optional",
            catalog_sources=catalog_by_category.get(category, []),
            project_sources=project_sources,
            latest_download_status=latest_download_status,
        )
        for category in categories
    ]

    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "report_profile": {
            "profile_id": report_profile.profile_id,
            "name": report_profile.name,
        },
        "project_context_path": project_context["context_path"],
        "statuses": statuses,
        "validation_issues": validation_issues,
        "output_path": str(output_path),
    }
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _category_status(
    *,
    project_dir: Path,
    category: str,
    requirement: str,
    catalog_sources: list[SourceDefinition],
    project_sources: dict[str, ProjectSource],
    latest_download_status: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_ids = [source.source_id for source in catalog_sources]
    download_status = latest_download_status or {}
    registered = [project_sources[source_id] for source_id in source_ids if source_id in project_sources]
    local_ready = [source for source in registered if _has_existing_local_path(project_dir, source)]
    downloaded = [source for source in local_ready if source.status == "downloaded" or source.access_method == "downloaded"]
    missing_local = [source for source in registered if _is_enabled_local_source(source) and not _has_existing_local_path(project_dir, source)]

    if downloaded:
        status = "downloaded"
        flags: list[str] = []
        notes = "Downloaded source data is available in the workspace."
    elif local_ready:
        status = "provided_locally"
        flags = []
        notes = "Local source data is available in the workspace."
    elif missing_local:
        status = "needs_review"
        flags = ["local_source_missing"]
        notes = "A local source is configured but the referenced path is unavailable."
    elif any(download_status.get(source_id) == "failed" for source_id in source_ids):
        status = "failed"
        flags = ["source_download_failed", "source_unavailable"]
        notes = "The latest supported public download attempt failed; the workflow can continue with a caveat."
    elif requirement == "optional":
        status = "optional"
        flags = []
        notes = "Optional source category is not required for this profile."
    elif _has_public_download_candidate(catalog_sources):
        status = "downloadable"
        flags = ["source_not_downloaded"]
        notes = "Public source data appears to be a future download candidate."
    elif _has_gated_candidate(catalog_sources):
        status = "gated"
        flags = ["restricted_source_required", "manual_review_required"]
        notes = "Source category requires restricted, sensitive, or qualified-access review."
    elif _has_manual_candidate(catalog_sources):
        status = "stubbed"
        flags = ["manual_review_required", "source_unavailable"]
        notes = "Source category requires manual or reviewer-supplied data."
    else:
        status = "missing"
        flags = ["source_unavailable"]
        notes = "No source candidate is currently available for this required category."

    return {
        "category": category,
        "requirement": requirement,
        "status": status,
        "source_ids": source_ids,
        "source_names": [source.name for source in catalog_sources],
        "registered_source_ids": [source.source_id for source in registered],
        "local_paths": _local_paths(project_dir, local_ready),
        "uncertainty_flags": flags,
        "notes": notes,
    }


def _catalog_by_category(catalog: SourceCatalog) -> dict[str, list[SourceDefinition]]:
    grouped: dict[str, list[SourceDefinition]] = defaultdict(list)
    for source in catalog.sources.values():
        grouped[source.category].append(source)
    return {category: sorted(items, key=lambda source: source.source_id) for category, items in grouped.items()}


def _unknown_project_sources(project_sources: dict[str, ProjectSource], catalog: SourceCatalog) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for source_id in sorted(project_sources):
        if source_id not in catalog.sources:
            issues.append(
                {
                    "severity": "warning",
                    "code": "unknown_project_source",
                    "message": f"Project source '{source_id}' is not present in the source catalog.",
                    "source_id": source_id,
                }
            )
    return issues


def _load_download_records(project_dir: Path) -> list[dict[str, Any]]:
    manifest_path = project_dir / SOURCE_ACQUISITION_PATH
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict) or not isinstance(data.get("downloads", []), list):
        return []
    return [item for item in data["downloads"] if isinstance(item, dict)]


def _latest_download_status(downloads: list[dict[str, Any]]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for download in downloads:
        source_id = str(download.get("source_id") or "")
        status = str(download.get("status") or "")
        if source_id and status:
            statuses[source_id] = status
    return statuses


def _is_enabled_local_source(source: ProjectSource) -> bool:
    return source.enabled and source.access_method == "local_file" and bool(source.path)


def _has_existing_local_path(project_dir: Path, source: ProjectSource) -> bool:
    if not _is_enabled_local_source(source):
        return False
    path = resolve_project_source_path(project_dir, source)
    return bool(path and path.exists())


def _local_paths(project_dir: Path, sources: list[ProjectSource]) -> list[str]:
    paths: list[str] = []
    for source in sources:
        path = resolve_project_source_path(project_dir, source)
        if path is not None:
            paths.append(str(path))
    return paths


def _has_public_download_candidate(sources: list[SourceDefinition]) -> bool:
    return any("future_download" in source.access_methods and "public" in source.public_or_restricted for source in sources)


def _has_gated_candidate(sources: list[SourceDefinition]) -> bool:
    gated_markers = ("restricted", "sensitive")
    return any(
        any(marker in source.public_or_restricted for marker in gated_markers) or "restricted" in source.tier
        for source in sources
    )


def _has_manual_candidate(sources: list[SourceDefinition]) -> bool:
    manual_methods = {"manual_document", "manual_lookup", "manual_download", "reviewer_supplied"}
    return any(bool(manual_methods.intersection(source.access_methods)) for source in sources)
