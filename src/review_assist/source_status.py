"""Source status set resolution for workflow-driven projects."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .basemaps import MARIS_NAIP_SOURCE_ID, USDA_NAIP_SOURCE_ID, discover_project_local_naip_basemaps, select_project_basemaps
from .project_context import ProjectContextError, generate_project_context
from .projects import ProjectManifestError, load_project_manifest
from .report_profiles import ReportProfileError, resolve_report_profile
from .report_section_policy import ReportSectionPolicyError, load_report_section_policy
from .source_catalog import (
    ProjectSource,
    SourceCatalog,
    SourceCatalogError,
    SourceDefinition,
    load_project_source_registry,
    load_source_catalog,
    resolve_project_source_path,
)
from .source_warehouse import SourceWarehouseError, maybe_load_seed_source_manifest, raw_paths_exist


SOURCE_STATUS_PATH = Path("source_status/source_status_set.json")
SOURCE_ACQUISITION_PATH = Path("source_acquisition/source_acquisition_manifest.json")
CURRENT_SOURCE_STATUSES = {"downloaded", "local_materialized", "provided_in_input", "registered_local"}
SOURCE_NEED_CLASSES = {
    "available_materialized",
    "warehouse_available_not_materialized",
    "acquisition_candidate",
    "optional",
    "manual_reviewer_supplied",
    "restricted_authorized_reviewer_supplied",
    "public_coarse_screening_context",
    "deferred",
    "deprecated_legacy",
}
PUBLIC_COARSE_SCREENING_SOURCE_IDS = {
    "google_earth_visual_context",
    "maris_public_cultural_context",
    "mdah_public_historic_resources",
    MARIS_NAIP_SOURCE_ID,
    USDA_NAIP_SOURCE_ID,
}
MANUAL_RESIDUAL_SOURCE_IDS = {
    "mdeq_environmental_context",
}
LOGICAL_ROLLUP_SATISFIERS = {
    "usgs_nhd_hydrography": {
        "usgs_nhd_flowlines",
        "usgs_nhd_other_areas",
        "usgs_nhd_waterbodies",
    },
    "epa_envirofacts_echo": {
        "epa_frs_facilities_ms",
        "maris_brownfields",
        "maris_npdes_facilities",
        "maris_solid_waste_landfills",
        "maris_superfund_sites",
        "maris_tri_facilities",
        "maris_underground_storage_tanks",
        "mississippi_oil_gas_wells",
    },
}
VISUAL_CONTEXT_SATISFIERS = {
    "google_earth_visual_context": {
        MARIS_NAIP_SOURCE_ID,
        USDA_NAIP_SOURCE_ID,
    }
}


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

    catalog_by_category = _catalog_by_category(catalog)
    project_sources = registry.by_source_id()
    categories = _status_categories_for_project(report_profile, catalog, project_sources)
    latest_download_status = _latest_download_status(_load_download_records(project_dir))
    basemap_selection = select_project_basemaps(project_dir)
    validation_issues = _unknown_project_sources(project_sources, catalog)

    statuses = [
        _category_status(
            project_dir=project_dir,
            category=category,
            requirement="required" if category in report_profile.required_categories else "optional",
            catalog_sources=catalog_by_category.get(category, []),
            project_sources=project_sources,
            latest_download_status=latest_download_status,
            basemap_selection=basemap_selection,
        )
        for category in categories
    ]
    try:
        section_source_needs = _section_source_needs(
            report_profile=report_profile,
            catalog=catalog,
            statuses=statuses,
        )
    except ReportSectionPolicyError as exc:
        raise SourceStatusError(str(exc)) from exc

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
        "section_source_needs": section_source_needs,
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
    basemap_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_ids = [source.source_id for source in catalog_sources]
    download_status = latest_download_status or {}
    registered = [project_sources[source_id] for source_id in source_ids if source_id in project_sources]
    local_ready = [source for source in registered if _has_existing_local_path(project_dir, source)]
    downloaded = [source for source in local_ready if source.status == "downloaded" or source.access_method == "downloaded"]
    missing_local = [source for source in registered if _is_enabled_local_source(source) and not _has_existing_local_path(project_dir, source)]
    source_details = [
        _source_detail(
            project_dir=project_dir,
            source=source,
            requirement=requirement,
            project_source=project_sources.get(source.source_id),
            latest_download_status=download_status,
            basemap_selection=basemap_selection,
        )
        for source in catalog_sources
    ]
    source_details = _reconcile_effective_source_details(source_details)
    source_details = _annotate_source_need_details(
        source_details,
        source_by_id={source.source_id: source for source in catalog_sources},
        requirement=requirement,
    )

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
    elif any(detail["status"] in {"registered_local", "local_materialized", "provided_in_input"} for detail in source_details):
        status = "provided_locally"
        flags = []
        notes = "Local source data is available in the workspace."
    elif any(download_status.get(source_id) == "failed" for source_id in source_ids):
        status = "failed"
        flags = ["source_download_failed", "source_unavailable"]
        notes = "The latest supported public download attempt failed; the workflow can continue with a caveat."
    elif any(detail["status"] == "failed" for detail in source_details):
        status = "failed"
        flags = sorted(
            {
                flag
                for detail in source_details
                for flag in detail.get("uncertainty_flags", [])
                if flag in {"basemap_materialization_failed", "vector_only_no_basemap", "source_unavailable"}
            }
            or {"source_unavailable"}
        )
        notes = "The latest optional source materialization attempt failed; the workflow can continue with a caveat."
    elif any(detail["status"] == "restricted" for detail in source_details):
        status = "gated"
        flags = ["restricted_source_required", "manual_review_required"]
        notes = "Source category requires restricted, sensitive, or qualified-access review."
    elif any(detail["status"] == "warehouse_available" for detail in source_details):
        status = "needs_review"
        flags = ["local_warehouse_source_unmaterialized"]
        notes = "Local source warehouse data is present but has not been materialized for this project."
    elif any(detail["status"] == "present_not_materialized" for detail in source_details):
        status = "present_not_materialized"
        flags = ["source_present_not_materialized"]
        notes = "Local source warehouse data is present but not yet configured for analysis-ready materialization."
    elif requirement == "optional":
        status = "optional"
        flags = []
        notes = "Optional source category is not required for this profile."
    elif any(detail["status"] == "selected_not_renderable" for detail in source_details):
        status = "selected_not_renderable"
        flags = ["source_selected_not_renderable", "renderable_sidecar_missing"]
        notes = "A basemap source is selected as provenance, but no renderable sidecar is available."
    elif any(detail["status"] == "downloadable" for detail in source_details):
        status = "downloadable"
        flags = ["source_not_downloaded"]
        notes = "Public source data appears to be a future download candidate."
    elif any(detail["status"] in {"manual", "stubbed", "unimplemented"} for detail in source_details):
        status = "stubbed"
        flags = sorted(
            {
                flag
                for detail in source_details
                for flag in detail.get("uncertainty_flags", [])
                if flag in {"manual_review_required", "source_unavailable", "source_unimplemented", "missing_census_api_key"}
            }
            or {"manual_review_required", "source_unavailable"}
        )
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
        "source_details": source_details,
        "uncertainty_flags": flags,
        "report_caveat_flags": _effective_category_report_caveat_flags(status, flags),
        "notes": notes,
    }


def effective_source_status(project_dir: Path, source_id: str) -> dict[str, Any]:
    """Return the current effective source detail for one source ID.

    Acquisition history remains available in source acquisition manifests; this
    helper reports the effective current status used for report/GPT-facing
    caveats after local materialization and logical rollup reconciliation.
    """

    project_dir = project_dir.resolve()
    path = project_dir / SOURCE_STATUS_PATH
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SourceStatusError(f"Invalid source status JSON: {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise SourceStatusError(f"Source status artifact must be a JSON object: {path}")
    else:
        data = resolve_source_status_set(project_dir)
    for record in data.get("statuses", []):
        if not isinstance(record, dict):
            continue
        for detail in record.get("source_details", []):
            if isinstance(detail, dict) and detail.get("source_id") == source_id:
                return {
                    "source_id": source_id,
                    "category": record.get("category"),
                    "status": detail.get("status"),
                    "category_status": record.get("status"),
                    "uncertainty_flags": _string_list(detail.get("uncertainty_flags", [])),
                    "report_caveat_flags": _string_list(detail.get("report_caveat_flags", [])),
                    "notes": detail.get("notes", ""),
                    "satisfied_by_source_ids": _string_list(detail.get("satisfied_by_source_ids", [])),
                    "source_need_class": detail.get("source_need_class", ""),
                    "source_need_reason": detail.get("source_need_reason", ""),
                }
    raise SourceStatusError(f"Source ID is not present in the resolved source status set: {source_id}")


def _catalog_by_category(catalog: SourceCatalog) -> dict[str, list[SourceDefinition]]:
    grouped: dict[str, list[SourceDefinition]] = defaultdict(list)
    for source in catalog.sources.values():
        grouped[source.category].append(source)
    return {category: sorted(items, key=lambda source: source.source_id) for category, items in grouped.items()}


def _status_categories_for_project(
    report_profile: Any,
    catalog: SourceCatalog,
    project_sources: dict[str, ProjectSource],
) -> list[str]:
    categories = list(report_profile.required_categories) + [
        category for category in report_profile.optional_categories if category not in report_profile.required_categories
    ]
    seen = set(categories)
    project_registered_categories = {
        str(getattr(catalog.sources.get(source_id), "category", "") or getattr(project_source, "source_category", "") or "")
        for source_id, project_source in project_sources.items()
        if project_source.enabled and source_id in catalog.sources
    }
    for category in sorted(project_registered_categories):
        if category and category not in seen:
            categories.append(category)
            seen.add(category)
    return categories


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


def _source_detail(
    *,
    project_dir: Path,
    source: SourceDefinition,
    requirement: str,
    project_source: ProjectSource | None,
    latest_download_status: dict[str, str],
    basemap_selection: dict[str, Any] | None,
) -> dict[str, Any]:
    status, notes, flags = _source_detail_status(
        project_dir=project_dir,
        source=source,
        requirement=requirement,
        project_source=project_source,
        latest_download_status=latest_download_status,
        basemap_selection=basemap_selection,
    )
    local_path = resolve_project_source_path(project_dir, project_source) if project_source is not None else None
    return {
        "source_id": source.source_id,
        "source_name": source.name,
        "status": status,
        "requirement": requirement,
        "access_methods": source.access_methods,
        "public_or_restricted": source.public_or_restricted,
        "registered": project_source is not None,
        "local_path": str(local_path) if local_path is not None else None,
        "local_path_exists": bool(local_path and local_path.exists()),
        "uncertainty_flags": flags,
        "notes": notes,
        "source_category": source.category,
    }


def _source_detail_status(
    *,
    project_dir: Path,
    source: SourceDefinition,
    requirement: str,
    project_source: ProjectSource | None,
    latest_download_status: dict[str, str],
    basemap_selection: dict[str, Any] | None,
) -> tuple[str, str, list[str]]:
    if project_source is not None and _has_existing_local_path(project_dir, project_source):
        if project_source.status == "downloaded":
            return "downloaded", "Downloaded source data is available in the workspace.", []
        if project_source.status == "local_materialized":
            return "local_materialized", "Local warehouse source data is materialized for this workspace.", []
        if project_source.status == "provided_in_input":
            return "provided_in_input", "Project input package includes this source layer.", []
        return "registered_local", "Reviewer-supplied or locally registered source data is available in the workspace.", []
    if project_source is not None and _is_enabled_local_source(project_source):
        return "missing", "A local source is configured but the referenced path is unavailable.", ["local_source_missing"]
    if source.source_id == MARIS_NAIP_SOURCE_ID:
        return _basemap_detail_status(basemap_selection)
    if source.source_id == USDA_NAIP_SOURCE_ID:
        return _project_naip_detail_status(project_dir)
    if requirement == "optional":
        return "optional", "Optional source is not required for this profile.", []
    warehouse_status = _warehouse_detail_status(source)
    if warehouse_status is not None:
        return warehouse_status
    if latest_download_status.get(source.source_id) == "failed":
        return "failed", "The latest supported public download attempt failed; the workflow can continue with a caveat.", [
            "source_download_failed",
            "source_unavailable",
        ]
    if source.source_id == "census_tiger_acs" and not os.environ.get("CENSUS_API_KEY"):
        return "stubbed", "Census TIGER/ACS setup is configured, but CENSUS_API_KEY is not set for future ACS API calls.", [
            "missing_census_api_key",
            "source_unavailable",
        ]
    if _public_future_download(source):
        if _source_download_supported(source):
            return "downloadable", "Public source data is supported by an implemented downloader but has not been downloaded.", [
                "source_not_downloaded"
            ]
        return "unimplemented", "Public source data appears downloadable, but no downloader is implemented yet.", [
            "source_unimplemented",
            "source_unavailable",
        ]
    if _gated_source(source):
        return "restricted", "Source requires restricted, sensitive, or qualified-access handling.", [
            "restricted_source_required",
            "manual_review_required",
        ]
    if _manual_source(source):
        return "manual", "Source requires manual lookup, manual download, or reviewer-supplied material.", [
            "manual_review_required",
            "source_unavailable",
        ]
    return "missing", "No supported source path is available for this source.", ["source_unavailable"]


def _warehouse_detail_status(source: SourceDefinition) -> tuple[str, str, list[str]] | None:
    if not source.warehouse_source_ids:
        return None

    manifests: list[tuple[str, dict[str, Any]]] = []
    missing_raw: list[str] = []
    for warehouse_source_id in source.warehouse_source_ids:
        manifest = maybe_load_seed_source_manifest(warehouse_source_id)
        if manifest is None:
            continue
        manifests.append((warehouse_source_id, manifest))
        try:
            missing_raw.extend(
                f"{warehouse_source_id}:{item['raw_path']}"
                for item in raw_paths_exist(warehouse_source_id)
                if not item.get("exists")
            )
        except SourceWarehouseError:
            missing_raw.append(warehouse_source_id)

    if not manifests:
        return None
    if missing_raw:
        return None
    if any(bool(manifest.get("analysis_ready")) for _, manifest in manifests):
        return (
            "warehouse_available",
            "Local source warehouse data is present; run local source materialization to register a project-ready layer.",
            ["local_warehouse_source_unmaterialized"],
        )
    return (
        "present_not_materialized",
        "Local source warehouse data is present, but the manifest marks it as not analysis-ready for deterministic materialization.",
        ["source_present_not_materialized"],
    )


def _reconcile_effective_source_details(source_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    status_by_source = {
        str(detail.get("source_id")): str(detail.get("status"))
        for detail in source_details
        if isinstance(detail, dict) and detail.get("source_id")
    }
    current_source_ids = {
        source_id
        for source_id, status in status_by_source.items()
        if status in CURRENT_SOURCE_STATUSES
    }
    reconciled: list[dict[str, Any]] = []
    for detail in source_details:
        source_id = str(detail.get("source_id") or "")
        item = dict(detail)
        rollup_satisfied_by = sorted(LOGICAL_ROLLUP_SATISFIERS.get(source_id, set()).intersection(current_source_ids))
        visual_satisfied_by = sorted(VISUAL_CONTEXT_SATISFIERS.get(source_id, set()).intersection(current_source_ids))
        if rollup_satisfied_by:
            item["status"] = "logical_rollup_satisfied"
            item["uncertainty_flags"] = []
            item["report_caveat_flags"] = []
            item["satisfied_by_source_ids"] = rollup_satisfied_by
            item["notes"] = (
                "Logical/download rollup is satisfied for report-facing caveats by current project-local "
                f"source layer(s): {', '.join(rollup_satisfied_by)}."
            )
        elif visual_satisfied_by:
            item["status"] = "visual_context_satisfied"
            item["uncertainty_flags"] = []
            item["report_caveat_flags"] = []
            item["satisfied_by_source_ids"] = visual_satisfied_by
            item["notes"] = (
                "Optional visual-review context is not treated as required authoritative evidence because "
                f"current basemap/imagery context is available from: {', '.join(visual_satisfied_by)}."
            )
        else:
            item["report_caveat_flags"] = _string_list(item.get("uncertainty_flags", []))
        reconciled.append(item)
    return reconciled


def _effective_category_report_caveat_flags(status: str, flags: list[str]) -> list[str]:
    if status in {"downloaded", "provided_locally", "local_materialized"}:
        return []
    if status == "optional":
        return []
    return sorted(set(flags))


def _annotate_source_need_details(
    source_details: list[dict[str, Any]],
    *,
    source_by_id: dict[str, SourceDefinition],
    requirement: str,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for detail in source_details:
        source_id = str(detail.get("source_id") or "")
        source = source_by_id.get(source_id)
        source_need_class, source_need_reason = _source_need_class_and_reason(
            source=source,
            source_id=source_id,
            status=str(detail.get("status") or ""),
            requirement=requirement,
        )
        item = dict(detail)
        item["source_need_class"] = source_need_class
        item["source_need_reason"] = source_need_reason
        annotated.append(item)
    return annotated


def _source_need_class_and_reason(
    *,
    source: SourceDefinition | None,
    source_id: str,
    status: str,
    requirement: str,
) -> tuple[str, str]:
    if source_id in PUBLIC_COARSE_SCREENING_SOURCE_IDS:
        return "public_coarse_screening_context", "Source is public/coarse screening or visual context and is not treated as authoritative missing evidence."
    if source_id in MANUAL_RESIDUAL_SOURCE_IDS:
        return "manual_reviewer_supplied", "Source is a manual residual context bucket and is not satisfied by unrelated child layers."
    if status in CURRENT_SOURCE_STATUSES | {"logical_rollup_satisfied"}:
        return "available_materialized", "Current project-local, materialized, downloaded, or rollup-satisfied source is available for report-facing use."
    if status in {"warehouse_available", "present_not_materialized"}:
        return "warehouse_available_not_materialized", "Local warehouse source material is present but has not been registered as an analysis-ready project layer."
    if status == "optional" or requirement == "optional":
        return "optional", "Source is optional for the active report profile."
    if source is not None and _gated_source(source):
        return "restricted_authorized_reviewer_supplied", "Source requires restricted, sensitive, or authorized reviewer handling."
    if status == "restricted":
        return "restricted_authorized_reviewer_supplied", "Source requires restricted, sensitive, or authorized reviewer handling."
    if source is not None and _manual_source(source):
        return "manual_reviewer_supplied", "Source requires manual lookup, manual download, or reviewer-supplied material."
    if status == "manual":
        return "manual_reviewer_supplied", "Source requires manual lookup, manual download, or reviewer-supplied material."
    if status == "stubbed":
        return "deferred", "Source is represented as a review-visible stub until acquisition, credentials, or implementation are available."
    if status in {"downloadable", "failed"}:
        return "acquisition_candidate", "Source is a supported public acquisition candidate or has a report-visible failed acquisition attempt."
    if status == "unimplemented":
        return "deferred", "Source is identified but deterministic acquisition or materialization is not implemented."
    if source is not None and _public_future_download(source):
        return "acquisition_candidate" if _source_download_supported(source) else "deferred", (
            "Source is a public acquisition candidate." if _source_download_supported(source)
            else "Source appears public but acquisition is deferred because no supported downloader is implemented."
        )
    if status == "missing":
        return "deferred", "No supported current source path is available."
    return "deferred", "Source need requires later review or implementation before source-backed use."


def _section_source_needs(
    *,
    report_profile: Any,
    catalog: SourceCatalog,
    statuses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    policy_config = load_report_section_policy()
    sources_by_category = _catalog_by_category(catalog)
    status_by_category = {
        str(record.get("category") or ""): record
        for record in statuses
        if isinstance(record, dict) and record.get("category")
    }
    detail_by_source_id: dict[str, dict[str, Any]] = {}
    for status_record in statuses:
        for detail in _dict_list(status_record.get("source_details", [])):
            source_id = str(detail.get("source_id") or "")
            if source_id:
                detail_by_source_id[source_id] = detail

    required_categories = set(report_profile.required_categories)
    optional_categories = set(report_profile.optional_categories)
    records: list[dict[str, Any]] = []
    for policy in policy_config.section_policies:
        source_categories = _dedupe(policy.allowed_source_categories)
        explicit_source_refs = _dedupe(policy.allowed_source_refs)
        source_ids = _dedupe(
            [
                *[
                    source.source_id
                    for category in source_categories
                    for source in sources_by_category.get(category, [])
                ],
                *explicit_source_refs,
            ]
        )
        needs = [
            _section_source_need(
                source_id=source_id,
                source=catalog.sources.get(source_id),
                detail=detail_by_source_id.get(source_id),
                required_categories=required_categories,
                optional_categories=optional_categories,
            )
            for source_id in source_ids
        ]
        category_records = [
            _section_category_need(category, status_by_category.get(category), required_categories, optional_categories)
            for category in source_categories
        ]
        records.append(
            {
                "section_id": policy.section_id,
                "title": policy.title,
                "inclusion_status": policy.inclusion_status,
                "activation_condition": policy.activation_condition,
                "review_requirement": policy.review_requirement,
                "manual_or_reviewer_supplied": policy.manual_or_reviewer_supplied,
                "source_categories": source_categories,
                "source_refs": explicit_source_refs,
                "source_ids": source_ids,
                "source_need_classes": _dedupe([str(need.get("source_need_class")) for need in needs if need.get("source_need_class")]),
                "section_need_status": _section_need_status(policy.activation_condition, needs),
                "section_need_reason": _section_need_reason(policy.activation_condition, needs),
                "category_needs": category_records,
                "source_needs": needs,
            }
        )
    return records


def _section_source_need(
    *,
    source_id: str,
    source: SourceDefinition | None,
    detail: dict[str, Any] | None,
    required_categories: set[str],
    optional_categories: set[str],
) -> dict[str, Any]:
    category = source.category if source else str(detail.get("source_category") if detail else "")
    if detail is not None:
        return {
            "source_id": source_id,
            "source_name": detail.get("source_name", source.name if source else source_id),
            "source_category": category,
            "requirement": detail.get("requirement", _requirement_for_category(category, required_categories, optional_categories)),
            "status": detail.get("status"),
            "source_need_class": detail.get("source_need_class"),
            "source_need_reason": detail.get("source_need_reason"),
            "satisfied_by_source_ids": _string_list(detail.get("satisfied_by_source_ids", [])),
        }
    requirement = _requirement_for_category(category, required_categories, optional_categories)
    warehouse_status = _warehouse_detail_status(source) if source is not None else None
    fallback_status = warehouse_status[0] if warehouse_status is not None else "missing"
    source_need_class, source_need_reason = _source_need_class_and_reason(
        source=source,
        source_id=source_id,
        status=fallback_status,
        requirement=requirement,
    )
    return {
        "source_id": source_id,
        "source_name": source.name if source else source_id,
        "source_category": category,
        "requirement": requirement,
        "status": fallback_status,
        "source_need_class": source_need_class,
        "source_need_reason": source_need_reason,
        "satisfied_by_source_ids": [],
    }


def _section_category_need(
    category: str,
    status_record: dict[str, Any] | None,
    required_categories: set[str],
    optional_categories: set[str],
) -> dict[str, Any]:
    return {
        "category": category,
        "requirement": str(status_record.get("requirement") or _requirement_for_category(category, required_categories, optional_categories))
        if status_record
        else _requirement_for_category(category, required_categories, optional_categories),
        "status": str(status_record.get("status") or "not_required_for_profile") if status_record else "not_required_for_profile",
        "report_caveat_flags": _string_list(status_record.get("report_caveat_flags", [])) if status_record else [],
    }


def _requirement_for_category(category: str, required_categories: set[str], optional_categories: set[str]) -> str:
    if category in required_categories:
        return "required"
    if category in optional_categories:
        return "optional"
    return "not_required_for_profile"


def _section_need_status(activation_condition: str, needs: list[dict[str, Any]]) -> str:
    classes = {str(need.get("source_need_class") or "") for need in needs}
    if activation_condition in {"manual_reviewer_supplied", "reviewer_supplied_parent_study"}:
        return "manual_reviewer_supplied"
    if not needs:
        return "not_source_backed"
    if classes.intersection({"restricted_authorized_reviewer_supplied"}):
        return "restricted_review_needed"
    if classes.intersection({"manual_reviewer_supplied"}):
        return "manual_review_needed"
    if classes.intersection({"deferred"}):
        return "deferred_source"
    if classes.intersection({"warehouse_available_not_materialized", "acquisition_candidate"}):
        return "source_action_needed"
    return "source_backed_or_optional"


def _section_need_reason(activation_condition: str, needs: list[dict[str, Any]]) -> str:
    if activation_condition in {"manual_reviewer_supplied", "reviewer_supplied_parent_study"}:
        return "Section activates only from reviewer-supplied or manual context."
    if not needs:
        return "Section does not declare source-backed policy needs."
    classes = _dedupe([str(need.get("source_need_class") or "") for need in needs if need.get("source_need_class")])
    return "Resolved source need classes: " + ", ".join(classes) + "."


def _basemap_detail_status(basemap_selection: dict[str, Any] | None) -> tuple[str, str, list[str]]:
    if not basemap_selection:
        return "missing", "Basemap selection has not been resolved.", ["source_unavailable"]
    status = str(basemap_selection.get("basemap_rendering_status") or "not_available")
    if status == "renderable_sidecar_available":
        return "registered_local", "Selected MARIS/NAIP imagery has at least one renderable sidecar.", []
    if status == "selected_not_renderable":
        return "selected_not_renderable", (
            "County MARIS/NAIP imagery was selected as provenance, but only MrSID source files are available. "
            "Provide a GeoTIFF or georeferenced PNG sidecar for visual basemap rendering."
        ), [
            "source_selected_not_renderable",
            "renderable_sidecar_missing",
        ]
    issues = basemap_selection.get("validation_issues", [])
    flags = ["source_unavailable"]
    if isinstance(issues, list) and any(isinstance(issue, dict) and issue.get("code") == "project_area_unavailable_for_basemap_selection" for issue in issues):
        flags.append("basemap_selection_unresolved")
    return "missing", "No selected MARIS/NAIP basemap source is available for this project.", flags


def _project_naip_detail_status(project_dir: Path) -> tuple[str, str, list[str]]:
    basemaps = discover_project_local_naip_basemaps(project_dir)
    if basemaps:
        return "registered_local", "A project-local renderable NAIP basemap sidecar is available.", []
    materialization_status = _latest_naip_materialization_status(project_dir)
    if materialization_status == "failed":
        return "failed", "The latest NAIP basemap materialization attempt failed; vector-only fallback remains available.", [
            "basemap_materialization_failed",
            "vector_only_no_basemap",
        ]
    return "unimplemented", "NAIP basemap materialization is available as an explicit optional command but has not been run.", [
        "source_unimplemented",
        "renderable_sidecar_missing",
    ]


def _latest_naip_materialization_status(project_dir: Path) -> str | None:
    manifest_path = project_dir / "basemaps" / "naip" / "naip_basemap_materialization.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return str(data.get("status") or "") or None


def _source_download_supported(source: SourceDefinition) -> bool:
    download = source.download if isinstance(source.download, dict) else {}
    return bool(download.get("supported")) and str(download.get("downloader") or "") == "arcgis_rest_geojson"


def _public_future_download(source: SourceDefinition) -> bool:
    return "future_download" in source.access_methods and "public" in source.public_or_restricted


def _gated_source(source: SourceDefinition) -> bool:
    gated_markers = ("restricted", "sensitive")
    return any(marker in source.public_or_restricted for marker in gated_markers) or "restricted" in source.tier


def _manual_source(source: SourceDefinition) -> bool:
    manual_methods = {"manual_document", "manual_lookup", "manual_download", "reviewer_supplied"}
    return bool(manual_methods.intersection(source.access_methods))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
