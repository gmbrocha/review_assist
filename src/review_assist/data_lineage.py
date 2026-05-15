"""Data authenticity and lineage summaries for deliverable exports."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .projects import ProjectManifestError, load_project_manifest
from .source_catalog import ProjectSource, SourceCatalogError, load_project_source_registry, resolve_project_source_path


SOURCE_ACQUISITION_PATH = Path("source_acquisition/source_acquisition_manifest.json")
SOURCE_STATUS_PATH = Path("source_status/source_status_set.json")
CONSTRAINT_RESULTS_PATH = Path("constraints/constraint_results.json")
LINEAGE_COUNT_KEYS = [
    "project_input",
    "registered_local",
    "provided_in_input",
    "downloaded_public_source",
    "manual_stub",
    "gated_stub",
    "missing_stub",
    "test_or_mock",
]
STUB_STATUS_TYPES = {
    "gated": "gated_stub",
    "stubbed": "manual_stub",
    "manual": "manual_stub",
    "missing": "missing_stub",
    "downloadable": "missing_stub",
    "unsupported_download": "missing_stub",
    "failed": "missing_stub",
    "needs_review": "missing_stub",
}


def build_data_lineage(project_dir: Path, *, included_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    records: list[dict[str, Any]] = []
    validation_issues: list[dict[str, Any]] = []

    records.extend(_project_input_records(project_dir, validation_issues))
    registry_sources = _active_registry_sources(project_dir, validation_issues)
    download_records = _download_records(project_dir, registry_sources, validation_issues)
    records.extend(download_records)
    records.extend(
        _project_registry_records(
            project_dir,
            {
                str(item.get("source_id"))
                for item in download_records
                if item.get("lineage_type") == "downloaded_public_source"
            },
            validation_issues,
            registry_sources=registry_sources,
        )
    )
    records.extend(_source_status_stub_records(project_dir, validation_issues))
    records.extend(_included_item_authenticity_records(included_items or []))

    constraint_count = _source_backed_constraint_count(project_dir, validation_issues)
    counts = Counter(str(record.get("lineage_type", "")) for record in records)
    normalized_counts = {key: int(counts.get(key, 0)) for key in LINEAGE_COUNT_KEYS}
    real_source_count = (
        normalized_counts["registered_local"]
        + normalized_counts["provided_in_input"]
        + normalized_counts["downloaded_public_source"]
    )
    lineage = {
        "version": "0.1",
        "project_dir": str(project_dir),
        "counts": normalized_counts,
        "real_source_count": real_source_count,
        "stub_count": normalized_counts["manual_stub"] + normalized_counts["gated_stub"] + normalized_counts["missing_stub"],
        "test_or_mock_count": normalized_counts["test_or_mock"],
        "source_backed_constraint_count": constraint_count,
        "has_real_source_data": real_source_count > 0,
        "has_source_backed_constraints": constraint_count > 0,
        "records": records,
        "validation_issues": validation_issues,
    }
    lineage["validation_issues"].extend(lineage_validation_issues(lineage))
    return lineage


def lineage_validation_issues(lineage: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not lineage.get("has_real_source_data"):
        issues.append(
            _issue(
                "warning",
                "no_real_source_layers",
                "No downloaded, provided-in-input, or registered local source layers were available for this export.",
            )
        )
    if int(lineage.get("test_or_mock_count", 0)) > 0:
        issues.append(
            _issue(
                "warning",
                "test_fixture_data_present",
                "One or more source records were marked as test fixtures or mock data.",
            )
        )
    return issues


def mvp_blocking_issues(lineage: dict[str, Any], *, fail_on_no_downloaded_sources: bool) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if int(lineage.get("test_or_mock_count", 0)) > 0:
        issues.append(
            _issue(
                "error",
                "test_fixture_data_present",
                "MVP deliverables must not include test fixture or mock source records.",
            )
        )
    if fail_on_no_downloaded_sources and not lineage.get("has_real_source_data") and not lineage.get("has_source_backed_constraints"):
        issues.append(
            _issue(
                "error",
                "no_real_source_data",
                "MVP deliverables require at least one downloaded, provided-in-input, or registered local source layer.",
            )
        )
    return issues


def _project_input_records(project_dir: Path, validation_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        manifest = load_project_manifest(project_dir)
    except ProjectManifestError as exc:
        validation_issues.append(_issue("warning", "project_manifest_unavailable", str(exc)))
        return []
    return [
        {
            "lineage_type": "project_input",
            "data_authenticity": "real",
            "path": project_input.path,
            "role": project_input.role,
            "source_id": project_input.source_id,
            "source_category": project_input.source_category,
        }
        for project_input in manifest.inputs
    ]


def _download_records(
    project_dir: Path,
    registry_sources: dict[str, ProjectSource],
    validation_issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    data = _load_json(project_dir / SOURCE_ACQUISITION_PATH, validation_issues, artifact="source_acquisition")
    if not data:
        return []
    records: list[dict[str, Any]] = []
    for download in _dict_list(data.get("downloads", [])):
        authenticity = _data_authenticity(download.get("data_authenticity"), default="real" if download.get("status") == "downloaded" else "unknown")
        status = str(download.get("status", ""))
        source_id = str(download.get("source_id", ""))
        if status == "downloaded":
            if not _download_is_active(project_dir, download, registry_sources):
                validation_issues.append(
                    _issue(
                        "warning",
                        "stale_download_record_ignored",
                        f"Ignored stale downloaded-source lineage for {source_id}; the current project registry does not enable that downloaded local file.",
                    )
                )
                continue
            lineage_type = "test_or_mock" if authenticity == "test_fixture" else "downloaded_public_source"
        elif status == "skipped_existing_local":
            # The registry/local source record is the real lineage record. The
            # download attempt only explains why no public download replaced it.
            continue
        elif authenticity == "test_fixture":
            lineage_type = "test_or_mock"
        else:
            lineage_type = "missing_stub"
            authenticity = "stub"
        records.append(
            {
                "lineage_type": lineage_type,
                "data_authenticity": authenticity,
                "source_id": source_id,
                "source_name": download.get("source_name"),
                "source_category": download.get("source_category"),
                "status": status,
                "source_url": download.get("source_url"),
                "service_url": download.get("service_url"),
                "access_date": download.get("access_date"),
                "output_path": download.get("output_path"),
                "feature_count": download.get("feature_count", 0),
                "checksum_sha256": download.get("checksum_sha256", ""),
                "source_limitations": download.get("source_limitations", ""),
            }
        )
    return records


def _project_registry_records(
    project_dir: Path,
    downloaded_source_ids: set[str],
    validation_issues: list[dict[str, Any]],
    *,
    registry_sources: dict[str, ProjectSource] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    sources = registry_sources if registry_sources is not None else _active_registry_sources(project_dir, validation_issues)
    for source in sources.values():
        if source.source_id in downloaded_source_ids and source.status == "downloaded":
            continue
        path = resolve_project_source_path(project_dir, source)
        if path is None or not path.exists():
            continue
        authenticity = _data_authenticity(source.metadata.get("data_authenticity"), default="real")
        if authenticity == "test_fixture":
            lineage_type = "test_or_mock"
        elif source.status == "provided_in_input":
            lineage_type = "provided_in_input"
        elif source.status == "downloaded":
            lineage_type = "downloaded_public_source"
        else:
            lineage_type = "registered_local"
        records.append(
            {
                "lineage_type": lineage_type,
                "data_authenticity": authenticity,
                "source_id": source.source_id,
                "status": source.status,
                "access_method": source.access_method,
                "path": source.path,
                "resolved_path": str(path),
            }
        )
    return records


def _active_registry_sources(project_dir: Path, validation_issues: list[dict[str, Any]]) -> dict[str, ProjectSource]:
    try:
        registry = load_project_source_registry(project_dir)
    except SourceCatalogError as exc:
        validation_issues.append(_issue("warning", "project_source_registry_unavailable", str(exc)))
        return {}
    return {source.source_id: source for source in registry.sources if source.enabled and source.path}


def _download_is_active(
    project_dir: Path,
    download: dict[str, Any],
    registry_sources: dict[str, ProjectSource],
) -> bool:
    source_id = str(download.get("source_id", ""))
    source = registry_sources.get(source_id)
    if source is None or source.status != "downloaded" or source.access_method != "local_file":
        return False
    registry_path = resolve_project_source_path(project_dir, source)
    if registry_path is None or not registry_path.exists():
        return False
    output_path = _resolved_output_path(project_dir, download.get("output_path"))
    return output_path is None or registry_path.resolve() == output_path.resolve()


def _resolved_output_path(project_dir: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (project_dir / path).resolve()


def _source_status_stub_records(project_dir: Path, validation_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    data = _load_json(project_dir / SOURCE_STATUS_PATH, validation_issues, artifact="source_status")
    if not data:
        return []
    records: list[dict[str, Any]] = []
    for status_record in _dict_list(data.get("statuses", [])):
        status = str(status_record.get("status", ""))
        requirement = str(status_record.get("requirement", ""))
        if requirement == "optional" and status == "optional":
            continue
        lineage_type = STUB_STATUS_TYPES.get(status)
        if lineage_type is None:
            continue
        records.append(
            {
                "lineage_type": lineage_type,
                "data_authenticity": "stub",
                "category": status_record.get("category"),
                "status": status,
                "requirement": requirement,
                "source_ids": _string_list(status_record.get("source_ids", [])),
                "notes": status_record.get("notes", ""),
            }
        )
    return records


def _included_item_authenticity_records(included_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in included_items:
        provenance = item.get("provenance", {}) if isinstance(item.get("provenance"), dict) else {}
        authenticity = _data_authenticity(provenance.get("data_authenticity"), default="")
        if authenticity != "test_fixture":
            continue
        records.append(
            {
                "lineage_type": "test_or_mock",
                "data_authenticity": "test_fixture",
                "item_id": item.get("id"),
                "item_type": item.get("type"),
                "title": item.get("title"),
            }
        )
    return records


def _source_backed_constraint_count(project_dir: Path, validation_issues: list[dict[str, Any]]) -> int:
    data = _load_json(project_dir / CONSTRAINT_RESULTS_PATH, validation_issues, artifact="constraint_results")
    if not data:
        return 0
    constraints = _dict_list(data.get("constraints", []))
    return len([constraint for constraint in constraints if constraint.get("source_id")])


def _load_json(path: Path, validation_issues: list[dict[str, Any]], *, artifact: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        validation_issues.append(_issue("warning", f"invalid_{artifact}_json", f"Unable to parse {path}: {exc}"))
        return {}
    if not isinstance(data, dict):
        validation_issues.append(_issue("warning", f"invalid_{artifact}_artifact", f"{path} must contain a JSON object."))
        return {}
    return data


def _data_authenticity(value: Any, *, default: str) -> str:
    text = str(value or default).strip()
    if text in {"real", "stub", "test_fixture", "unknown"}:
        return text
    return default or "unknown"


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _issue(severity: str, code: str, message: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
    }
