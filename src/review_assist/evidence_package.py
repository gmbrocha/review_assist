"""Evidence confidence package generation for report drafting."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constraints import CONSTRAINT_RESULTS_PATH, ConstraintAnalysisError, analyze_constraints
from .data_lineage import build_data_lineage
from .findings import FINDINGS_PATH, FindingGenerationError, generate_draft_findings, load_draft_findings
from .maps import MAP_MANIFEST_PATH, MapGenerationError, load_map_manifest
from .project_context import ProjectContextError, generate_project_context, load_project_context
from .source_acquisition import SOURCE_ACQUISITION_PATH
from .source_inventory import SOURCE_INVENTORY_PATH, SourceInventoryError, generate_source_inventory, load_source_inventory
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set
from .tables import TABLES_PATH, TableGenerationError, generate_comparison_tables, load_comparison_tables


EVIDENCE_PACKAGE_PATH = Path("evidence/evidence_package.json")
EVIDENCE_CLASSES = {
    "source_backed",
    "source_available_no_overlap",
    "stub_or_manual",
    "failed_or_missing",
    "test_fixture_blocked",
}


class EvidencePackageError(RuntimeError):
    """Raised when evidence package generation cannot complete."""


def build_evidence_package(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        context = _load_or_generate_context(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
        source_inventory = _load_or_generate_source_inventory(project_dir)
        constraints = _load_or_generate_constraints(project_dir)
        draft_findings = _load_or_generate_findings(project_dir)
        comparison_tables = _load_or_generate_tables(project_dir)
        map_manifest = _load_optional_map_manifest(project_dir)
    except (
        ProjectContextError,
        SourceStatusError,
        SourceInventoryError,
        ConstraintAnalysisError,
        FindingGenerationError,
        TableGenerationError,
        MapGenerationError,
    ) as exc:
        raise EvidencePackageError(str(exc)) from exc

    data_lineage = build_data_lineage(project_dir)
    source_acquisition = _load_optional_json(project_dir / SOURCE_ACQUISITION_PATH)
    section_bundles = _section_bundles(
        source_status=source_status,
        source_inventory=source_inventory,
        constraints=constraints,
        draft_findings=draft_findings,
        comparison_tables=comparison_tables,
        map_manifest=map_manifest,
        data_lineage=data_lineage,
    )
    evidence_class_counts = Counter(
        evidence_class
        for bundle in section_bundles.values()
        for evidence_class in _string_list(bundle.get("evidence_classes", []))
        if evidence_class in EVIDENCE_CLASSES
    )
    result = {
        "project_id": context.get("project_id"),
        "project_name": context.get("project_name"),
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "data_lineage": data_lineage,
        "source_acquisition": _source_acquisition_summary(source_acquisition),
        "source_status_path": source_status.get("output_path"),
        "source_inventory_path": source_inventory.get("output_path"),
        "constraint_results_path": constraints.get("output_path"),
        "draft_findings_path": draft_findings.get("output_path"),
        "comparison_tables_path": comparison_tables.get("output_path"),
        "map_manifest_path": map_manifest.get("output_path") if map_manifest else None,
        "constraint_count": constraints.get("constraint_count", 0),
        "source_backed_constraint_count": data_lineage.get("source_backed_constraint_count", 0),
        "real_source_count": data_lineage.get("real_source_count", 0),
        "stub_count": data_lineage.get("stub_count", 0),
        "test_or_mock_count": data_lineage.get("test_or_mock_count", 0),
        "evidence_class_counts": {key: int(evidence_class_counts.get(key, 0)) for key in sorted(EVIDENCE_CLASSES)},
        "section_evidence": section_bundles,
        "validation_issues": _validation_issues(data_lineage, source_acquisition, constraints, source_status),
    }
    output_path = project_dir / EVIDENCE_PACKAGE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result["output_path"] = str(output_path)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_evidence_package(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / EVIDENCE_PACKAGE_PATH
    if not path.exists():
        raise EvidencePackageError(f"Missing evidence package artifact: {path}")
    data = _load_json(path)
    if not isinstance(data, dict):
        raise EvidencePackageError(f"Evidence package artifact must be a JSON object: {path}")
    return data


def section_evidence_for(evidence_package: dict[str, Any] | None, section_id: str) -> dict[str, Any]:
    if not evidence_package:
        return {}
    sections = evidence_package.get("section_evidence", {})
    if not isinstance(sections, dict):
        return {}
    item = sections.get(section_id)
    return item if isinstance(item, dict) else {}


def _load_or_generate_context(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_context(project_dir)
    except ProjectContextError:
        return generate_project_context(project_dir)


def _load_or_generate_source_status(project_dir: Path) -> dict[str, Any]:
    source_status_path = project_dir / SOURCE_STATUS_PATH
    if source_status_path.exists():
        data = _load_json(source_status_path)
        if isinstance(data, dict):
            return data
        raise SourceStatusError(f"Source status artifact must be a JSON object: {source_status_path}")
    return resolve_source_status_set(project_dir)


def _load_or_generate_source_inventory(project_dir: Path) -> dict[str, Any]:
    if (project_dir / SOURCE_INVENTORY_PATH).exists():
        return load_source_inventory(project_dir)
    return generate_source_inventory(project_dir)


def _load_or_generate_constraints(project_dir: Path) -> dict[str, Any]:
    constraints_path = project_dir / CONSTRAINT_RESULTS_PATH
    if constraints_path.exists():
        data = _load_json(constraints_path)
        if isinstance(data, dict):
            return data
        raise ConstraintAnalysisError(f"Constraint result artifact must be a JSON object: {constraints_path}")
    return analyze_constraints(project_dir, tolerate_source_errors=True)


def _load_or_generate_findings(project_dir: Path) -> dict[str, Any]:
    if (project_dir / FINDINGS_PATH).exists():
        return load_draft_findings(project_dir)
    return generate_draft_findings(project_dir)


def _load_or_generate_tables(project_dir: Path) -> dict[str, Any]:
    if (project_dir / TABLES_PATH).exists():
        return load_comparison_tables(project_dir)
    return generate_comparison_tables(project_dir)


def _load_optional_map_manifest(project_dir: Path) -> dict[str, Any] | None:
    if not (project_dir / MAP_MANIFEST_PATH).exists():
        return None
    return load_map_manifest(project_dir)


def _section_bundles(
    *,
    source_status: dict[str, Any],
    source_inventory: dict[str, Any],
    constraints: dict[str, Any],
    draft_findings: dict[str, Any],
    comparison_tables: dict[str, Any],
    map_manifest: dict[str, Any] | None,
    data_lineage: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    categories = _categories(source_status, draft_findings, constraints)
    bundles: dict[str, dict[str, Any]] = {}
    for section_id, category in categories.items():
        findings = _findings_for_category(draft_findings, category)
        tables = _tables_for_category(comparison_tables, category)
        source_refs = sorted({ref for finding in findings for ref in _string_list(finding.get("source_refs", []))})
        bundles[section_id] = {
            "section_id": section_id,
            "resource_category": category,
            "evidence_classes": _evidence_classes_for_category(
                category=category,
                source_status=source_status,
                constraints=constraints,
                data_lineage=data_lineage,
            ),
            "source_refs": source_refs,
            "sources": _sources_for_category(source_status, source_inventory, category, source_refs),
            "findings": [_finding_summary(finding) for finding in findings[:8]],
            "tables": [_table_summary(table, category) for table in tables],
            "figures": _figures_for_refs(map_manifest, source_refs),
            "validation_issues": _validation_issues_for_category(source_status, category),
        }
    return bundles


def _categories(source_status: dict[str, Any], draft_findings: dict[str, Any], constraints: dict[str, Any]) -> dict[str, str]:
    categories: dict[str, str] = {
        "executive-summary": "overall",
        "methodology-and-data-sources": "overall",
        "mapping-and-analysis-procedures": "overall",
        "limitations-and-missing-data": "overall",
        "environmental-constraints-inventory": "overall",
        "comparison-summary": "overall",
        "maps-and-figures": "overall",
        "conclusion-and-next-steps": "overall",
        "reviewer-follow-up": "overall",
    }
    for item in _dict_list(source_status.get("statuses", [])):
        category = str(item.get("category", ""))
        if category:
            categories[_section_id_for_category(category)] = category
    for finding in _dict_list(draft_findings.get("findings", [])):
        category = str(finding.get("source_category", ""))
        if category:
            categories.setdefault(_section_id_for_category(category), category)
    for constraint in _dict_list(constraints.get("constraints", [])):
        category = str(constraint.get("source_category", ""))
        if category:
            categories.setdefault(_section_id_for_category(category), category)
    return categories


def _section_id_for_category(category: str) -> str:
    return {
        "wetlands_waterbodies": "wetlands-and-waterbodies",
        "hydrography_crossings": "streams-hydrography-crossings",
        "land_cover_disturbance": "land-cover-disturbance",
        "soils": "soils",
        "species_habitat": "species-and-habitat",
        "cultural_historic": "cultural-and-historic",
        "regulated_facilities": "regulated-facilities",
        "transportation_utilities": "transportation-utilities",
        "community_socioeconomic": "community-socioeconomic",
        "parcels_property": "parcels-property",
        "imagery_basemaps": "imagery-basemaps",
        "flood_hazard": "flood-hazard",
    }.get(category, category.replace("_", "-"))


def _evidence_classes_for_category(
    *,
    category: str,
    source_status: dict[str, Any],
    constraints: dict[str, Any],
    data_lineage: dict[str, Any],
) -> list[str]:
    classes: set[str] = set()
    if category == "overall":
        if int(data_lineage.get("source_backed_constraint_count", 0)) > 0:
            classes.add("source_backed")
        if int(data_lineage.get("stub_count", 0)) > 0:
            classes.add("stub_or_manual")
        if int(data_lineage.get("test_or_mock_count", 0)) > 0:
            classes.add("test_fixture_blocked")
        return sorted(classes) or ["failed_or_missing"]
    if any(str(item.get("source_category")) == category for item in _dict_list(constraints.get("constraints", []))):
        classes.add("source_backed")
    source_records = [item for item in _dict_list(constraints.get("sources", [])) if item.get("source_category") == category]
    if source_records and not classes:
        classes.add("source_available_no_overlap")
    for status in _dict_list(source_status.get("statuses", [])):
        if status.get("category") != category:
            continue
        state = str(status.get("status", ""))
        if state in {"gated", "stubbed", "manual"}:
            classes.add("stub_or_manual")
        if state in {"missing", "downloadable", "failed", "needs_review", "unsupported_download"}:
            classes.add("failed_or_missing")
    return sorted(classes) or ["failed_or_missing"]


def _findings_for_category(draft_findings: dict[str, Any], category: str) -> list[dict[str, Any]]:
    findings = _dict_list(draft_findings.get("findings", []))
    if category == "overall":
        return findings
    return [finding for finding in findings if finding.get("source_category") == category]


def _tables_for_category(comparison_tables: dict[str, Any], category: str) -> list[dict[str, Any]]:
    tables = _dict_list(comparison_tables.get("tables", []))
    if category == "overall":
        return tables
    result = []
    for table in tables:
        rows = _dict_list(table.get("rows", []))
        if any(str(row.get("category") or row.get("source_category") or row.get("resource_category")) == category for row in rows):
            result.append(table)
            continue
        table_id = str(table.get("table_id", ""))
        if category == "hydrography_crossings" and "hydrography" in table_id:
            result.append(table)
        elif category == "flood_hazard" and "flood" in table_id:
            result.append(table)
        elif category == "species_habitat" and "critical-habitat" in table_id:
            result.append(table)
        elif category == "regulated_facilities" and "regulated-facility" in table_id:
            result.append(table)
    return result


def _sources_for_category(
    source_status: dict[str, Any],
    source_inventory: dict[str, Any],
    category: str,
    source_refs: list[str],
) -> list[dict[str, Any]]:
    records = []
    source_ref_set = set(source_refs)
    for item in _dict_list(source_status.get("statuses", [])):
        if category != "overall" and item.get("category") != category:
            continue
        source_ids = _source_ids_for_status(item)
        if category == "overall" or source_ref_set.intersection(source_ids):
            records.append(
                {
                    "category": item.get("category"),
                    "status": item.get("status"),
                    "source_ids": source_ids,
                    "notes": item.get("notes", ""),
                    "uncertainty_flags": _string_list(item.get("uncertainty_flags", [])),
                }
            )
    inventory_lookup = {str(item.get("source_id")): item for item in _dict_list(source_inventory.get("records", []))}
    for record in records:
        record["inventory"] = [
            {
                "source_id": source_id,
                "source_name": inventory_lookup.get(source_id, {}).get("name") or inventory_lookup.get(source_id, {}).get("source_name"),
                "status": inventory_lookup.get(source_id, {}).get("status"),
                "path": inventory_lookup.get(source_id, {}).get("path"),
                "source_url": inventory_lookup.get(source_id, {}).get("source_url"),
                "access_date": inventory_lookup.get(source_id, {}).get("access_date"),
            }
            for source_id in _string_list(record.get("source_ids", []))
        ]
    return records


def _source_ids_for_status(status: dict[str, Any]) -> list[str]:
    return _string_list(status.get("source_ids", [])) or _string_list(status.get("registered_source_ids", []))


def _figures_for_refs(map_manifest: dict[str, Any] | None, source_refs: list[str]) -> list[dict[str, Any]]:
    if map_manifest is None:
        return []
    source_ref_set = set(source_refs)
    figures = []
    for figure in _dict_list(map_manifest.get("figures", [])):
        figure_refs = set(_string_list(figure.get("source_refs", [])))
        if not source_ref_set or figure_refs.intersection(source_ref_set) or figure.get("figure_type") == "project_overview":
            figures.append(
                {
                    "figure_id": figure.get("figure_id"),
                    "title": figure.get("title"),
                    "figure_type": figure.get("figure_type"),
                    "image_path": figure.get("image_path"),
                    "source_refs": _string_list(figure.get("source_refs", [])),
                }
            )
    return figures[:8]


def _finding_summary(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_id": finding.get("finding_id"),
        "title": finding.get("title"),
        "finding_type": finding.get("finding_type"),
        "source_category": finding.get("source_category"),
        "source_refs": _string_list(finding.get("source_refs", [])),
        "content": _truncate(str(finding.get("generated_content", "")), 900),
        "uncertainty_flags": _string_list(finding.get("uncertainty_flags", [])),
        "provenance": finding.get("provenance", {}) if isinstance(finding.get("provenance"), dict) else {},
    }


def _table_summary(table: dict[str, Any], category: str) -> dict[str, Any]:
    rows = _dict_list(table.get("rows", []))
    if category != "overall":
        filtered = [
            row
            for row in rows
            if str(row.get("category") or row.get("source_category") or row.get("resource_category")) == category
        ]
        if filtered:
            rows = filtered
    return {
        "table_id": table.get("table_id"),
        "title": table.get("title"),
        "table_type": table.get("table_type"),
        "row_count": table.get("row_count", len(rows)),
        "columns": _string_list(table.get("columns", [])),
        "rows_preview": rows[:5],
    }


def _validation_issues_for_category(source_status: dict[str, Any], category: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for item in _dict_list(source_status.get("statuses", [])):
        if category != "overall" and item.get("category") != category:
            continue
        if str(item.get("status", "")) in {"missing", "failed", "gated", "stubbed", "needs_review"}:
            issues.append(
                {
                    "severity": "warning",
                    "code": f"source_{item.get('status')}",
                    "message": item.get("notes") or f"Source category {item.get('category')} is {item.get('status')}.",
                    "category": item.get("category"),
                }
            )
    return issues


def _source_acquisition_summary(source_acquisition: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_path": source_acquisition.get("output_path"),
        "download_count": source_acquisition.get("download_count", 0),
        "gap_status_counts": source_acquisition.get("gap_status_counts", {}),
        "downloads": [
            {
                "source_id": item.get("source_id"),
                "status": item.get("status"),
                "feature_count": item.get("feature_count", 0),
                "access_date": item.get("access_date"),
                "checksum_sha256": item.get("checksum_sha256", ""),
                "data_authenticity": item.get("data_authenticity", "unknown"),
            }
            for item in _dict_list(source_acquisition.get("downloads", []))
        ],
    }


def _validation_issues(
    data_lineage: dict[str, Any],
    source_acquisition: dict[str, Any],
    constraints: dict[str, Any],
    source_status: dict[str, Any],
) -> list[dict[str, Any]]:
    issues = list(_dict_list(data_lineage.get("validation_issues", [])))
    issues.extend(_dict_list(source_acquisition.get("validation_issues", [])))
    issues.extend(_dict_list(constraints.get("validation_issues", [])))
    for item in _dict_list(source_status.get("statuses", [])):
        if str(item.get("status", "")) == "failed":
            issues.append(
                {
                    "severity": "warning",
                    "code": "source_download_failed",
                    "message": item.get("notes") or "A supported source download failed.",
                    "category": item.get("category"),
                }
            )
    return issues


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = _load_json(path)
    return data if isinstance(data, dict) else {}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidencePackageError(f"Invalid JSON artifact: {path}: {exc}") from exc


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _truncate(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
