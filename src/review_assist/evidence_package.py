"""Evidence confidence package generation for report drafting."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constraints import CONSTRAINT_RESULTS_PATH, ConstraintAnalysisError, analyze_constraints
from .data_lineage import build_data_lineage
from .deliverable_figures import DELIVERABLE_FIGURES_PATH, DeliverableFigureError, generate_deliverable_figures, load_deliverable_figures
from .deliverable_tables import DELIVERABLE_TABLES_PATH, DeliverableTableError, generate_deliverable_tables, load_deliverable_tables
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
SOURCE_ID_CATEGORY_HINTS = {
    "usfws_nwi_wetlands": "wetlands_waterbodies",
    "usgs_nhd_hydrography": "hydrography_crossings",
    "fema_nfhl_flood_hazard": "flood_hazard",
    "maris_public_cultural_context": "cultural_historic",
    "mdah_public_historic_resources": "cultural_historic",
    "mdah_restricted_archaeology": "cultural_historic",
    "maris_community_facilities": "community_socioeconomic",
    "hifld_community_infrastructure": "community_socioeconomic",
    "census_tiger_acs": "community_socioeconomic",
    "mdeq_public_water_supply_wells": "transportation_utilities",
    "local_utility_infrastructure": "transportation_utilities",
    "epa_envirofacts_echo": "regulated_facilities",
    "mdeq_environmental_context": "regulated_facilities",
    "mississippi_oil_gas_wells": "regulated_facilities",
    "maris_naip_2025_imagery": "imagery_basemaps",
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
        deliverable_tables = _load_or_generate_deliverable_tables(project_dir)
        deliverable_figures = _load_or_generate_deliverable_figures(project_dir)
        map_manifest = _load_optional_map_manifest(project_dir)
    except (
        ProjectContextError,
        SourceStatusError,
        SourceInventoryError,
        ConstraintAnalysisError,
        FindingGenerationError,
        TableGenerationError,
        DeliverableTableError,
        DeliverableFigureError,
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
        deliverable_tables=deliverable_tables,
        deliverable_figures=deliverable_figures,
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
        "deliverable_tables_path": deliverable_tables.get("output_path"),
        "deliverable_figures_path": deliverable_figures.get("output_path"),
        "map_manifest_path": map_manifest.get("output_path") if map_manifest else None,
        "constraint_count": constraints.get("constraint_count", 0),
        "deliverable_table_count": deliverable_tables.get("table_count", 0),
        "deliverable_figure_count": deliverable_figures.get("figure_count", 0),
        "deliverable_figure_stub_count": sum(1 for figure in _dict_list(deliverable_figures.get("figures", [])) if figure.get("is_stub")),
        "source_backed_constraint_count": data_lineage.get("source_backed_constraint_count", 0),
        "real_source_count": data_lineage.get("real_source_count", 0),
        "stub_count": data_lineage.get("stub_count", 0),
        "test_or_mock_count": data_lineage.get("test_or_mock_count", 0),
        "evidence_class_counts": {key: int(evidence_class_counts.get(key, 0)) for key in sorted(EVIDENCE_CLASSES)},
        "section_evidence": section_bundles,
        "raw_artifact_paths": {
            "source_status": source_status.get("output_path"),
            "source_inventory": source_inventory.get("output_path"),
            "constraint_results": constraints.get("output_path"),
            "draft_findings": draft_findings.get("output_path"),
            "comparison_tables": comparison_tables.get("output_path"),
            "deliverable_tables": deliverable_tables.get("output_path"),
            "deliverable_figures": deliverable_figures.get("output_path"),
            "map_manifest": map_manifest.get("output_path") if map_manifest else None,
        },
        "validation_issues": _validation_issues(
            data_lineage,
            source_acquisition,
            constraints,
            source_status,
            deliverable_tables,
            deliverable_figures,
        ),
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


def _load_or_generate_deliverable_tables(project_dir: Path) -> dict[str, Any]:
    if (project_dir / DELIVERABLE_TABLES_PATH).exists():
        return load_deliverable_tables(project_dir)
    return generate_deliverable_tables(project_dir)


def _load_or_generate_deliverable_figures(project_dir: Path) -> dict[str, Any]:
    if (project_dir / DELIVERABLE_FIGURES_PATH).exists():
        return load_deliverable_figures(project_dir)
    return generate_deliverable_figures(project_dir)


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
    deliverable_tables: dict[str, Any],
    deliverable_figures: dict[str, Any],
    map_manifest: dict[str, Any] | None,
    data_lineage: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    categories = _categories(source_status, draft_findings, constraints, deliverable_tables, deliverable_figures)
    bundles: dict[str, dict[str, Any]] = {}
    for section_id, category in categories.items():
        findings = _findings_for_category(draft_findings, category)
        tables = _tables_for_category(comparison_tables, category)
        deliverable_section_tables = _deliverable_tables_for_section(deliverable_tables, section_id, category)
        deliverable_section_figures = _deliverable_figures_for_section(deliverable_figures, section_id, category)
        source_refs = sorted(
            {
                ref
                for ref in [
                    *[ref for finding in findings for ref in _string_list(finding.get("source_refs", []))],
                    *[ref for table in deliverable_section_tables for ref in _string_list(table.get("source_refs", []))],
                    *[ref for figure in deliverable_section_figures for ref in _string_list(figure.get("source_refs", []))],
                ]
                if ref
            }
        )
        deliverable_table_summaries = [_deliverable_table_summary(table) for table in deliverable_section_tables]
        deliverable_figure_summaries = [_deliverable_figure_summary(figure) for figure in deliverable_section_figures]
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
            "deliverable_table_ids": [str(table.get("table_id")) for table in deliverable_section_tables if table.get("table_id")],
            "deliverable_tables": deliverable_table_summaries,
            "row_summaries": _row_summaries(deliverable_table_summaries),
            "deliverable_figure_ids": [str(figure.get("figure_id")) for figure in deliverable_section_figures if figure.get("figure_id")],
            "deliverable_figures": deliverable_figure_summaries,
            "figure_availability": _figure_availability(deliverable_figure_summaries),
            "figures": _figures_for_refs(map_manifest, source_refs),
            "comparison_unit_summaries": _comparison_unit_summaries(deliverable_section_tables, deliverable_section_figures, constraints, category),
            "constraint_summaries": _constraint_summaries(constraints, category, source_refs),
            "source_gap_status": _source_gap_status(source_status, category),
            "raw_artifact_paths": _section_raw_artifact_paths(
                constraints=constraints,
                comparison_tables=comparison_tables,
                deliverable_tables=deliverable_tables,
                deliverable_figures=deliverable_figures,
                map_manifest=map_manifest,
            ),
            "validation_issues": _validation_issues_for_category(source_status, category)
            + _deliverable_validation_issues(deliverable_section_tables, deliverable_section_figures),
        }
    return bundles


def _categories(
    source_status: dict[str, Any],
    draft_findings: dict[str, Any],
    constraints: dict[str, Any],
    deliverable_tables: dict[str, Any],
    deliverable_figures: dict[str, Any],
) -> dict[str, str]:
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
    for table in _dict_list(deliverable_tables.get("tables", [])):
        section_id = str(table.get("section_target_id", ""))
        if section_id:
            category = _first_string(table.get("related_resource_categories")) or _first_source_category_from_refs(source_status, table.get("source_refs", []))
            categories.setdefault(section_id, category or "overall")
    for figure in _dict_list(deliverable_figures.get("figures", [])):
        section_id = str(figure.get("section_target_id", ""))
        if section_id:
            category = _first_string(figure.get("related_resource_categories")) or _first_source_category_from_refs(source_status, figure.get("source_refs", []))
            categories.setdefault(section_id, category or "overall")
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
                "has_local_path": bool(inventory_lookup.get(source_id, {}).get("path")),
                "source_url": inventory_lookup.get(source_id, {}).get("source_url"),
                "access_date": inventory_lookup.get(source_id, {}).get("access_date"),
            }
            for source_id in _string_list(record.get("source_ids", []))
        ]
    return records


def _source_ids_for_status(status: dict[str, Any]) -> list[str]:
    return _string_list(status.get("source_ids", [])) or _string_list(status.get("registered_source_ids", []))


def _first_string(value: Any) -> str:
    values = _string_list(value)
    return values[0] if values else ""


def _first_source_category_from_refs(source_status: dict[str, Any], refs: Any) -> str:
    ref_set = set(_string_list(refs))
    if not ref_set:
        return ""
    for item in _dict_list(source_status.get("statuses", [])):
        source_ids = set(_source_ids_for_status(item))
        for detail in _dict_list(item.get("source_details", [])):
            source_id = str(detail.get("source_id", ""))
            if source_id:
                source_ids.add(source_id)
        if source_ids.intersection(ref_set):
            return str(item.get("category", ""))
    categories = _source_categories_from_refs(sorted(ref_set))
    return categories[0] if categories else ""


def _source_categories_from_refs(refs: list[str]) -> list[str]:
    return sorted({SOURCE_ID_CATEGORY_HINTS.get(ref, "") for ref in refs if SOURCE_ID_CATEGORY_HINTS.get(ref, "")})


def _nested_value(record: dict[str, Any], object_key: str, value_key: str) -> Any:
    nested = record.get(object_key, {})
    if not isinstance(nested, dict):
        return []
    return nested.get(value_key, [])


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in row.items():
        key_text = str(key)
        if key_text.lower() in {"geometry", "coordinates", "geojson", "raw_features", "__geo_interface__"}:
            continue
        if isinstance(value, (dict, list)):
            compact[key_text] = _truncate(json.dumps(value, sort_keys=True, default=str), 300)
        else:
            compact[key_text] = value
    return compact


def _safe_provenance_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    blocked_tokens = ("path", "geojson", "geometry", "feature")
    summary: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        lowered = key_text.lower()
        if any(token in lowered for token in blocked_tokens):
            continue
        if isinstance(item, (str, int, float, bool)) or item is None:
            summary[key_text] = item
        elif isinstance(item, list):
            summary[key_text] = [entry for entry in item[:8] if isinstance(entry, (str, int, float, bool))]
    return summary


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
                    "has_image": bool(figure.get("image_path")),
                    "source_refs": _string_list(figure.get("source_refs", [])),
                }
            )
    return figures[:8]


def _deliverable_tables_for_section(deliverable_tables: dict[str, Any], section_id: str, category: str) -> list[dict[str, Any]]:
    tables = _dict_list(deliverable_tables.get("tables", []))
    if category == "overall":
        return tables[:8]
    result = [table for table in tables if table.get("section_target_id") == section_id]
    if result:
        return result
    return [
        table
        for table in tables
        if category in _string_list(_nested_value(table, "provenance", "source_categories"))
        or category in _source_categories_from_refs(_string_list(table.get("source_refs", [])))
    ]


def _deliverable_figures_for_section(deliverable_figures: dict[str, Any], section_id: str, category: str) -> list[dict[str, Any]]:
    figures = _dict_list(deliverable_figures.get("figures", []))
    if category == "overall":
        return figures[:8]
    result = [figure for figure in figures if figure.get("section_target_id") == section_id]
    if result:
        return result
    return [
        figure
        for figure in figures
        if category in _string_list(figure.get("related_resource_categories", []))
        or category in _source_categories_from_refs(_string_list(figure.get("source_refs", [])))
    ]


def _deliverable_table_summary(table: dict[str, Any]) -> dict[str, Any]:
    rows = _dict_list(table.get("rows", []))
    return {
        "table_id": table.get("table_id"),
        "table_number": table.get("table_number"),
        "title": table.get("title"),
        "section_target_id": table.get("section_target_id"),
        "row_count": table.get("row_count", len(rows)),
        "columns": _string_list(table.get("columns", [])),
        "rows_preview": [_compact_row(row) for row in rows[:5]],
        "source_refs": _string_list(table.get("source_refs", [])),
        "comparison_unit_ids": _string_list(table.get("comparison_unit_ids", [])),
        "related_constraint_ids": _string_list(table.get("related_constraint_ids", []))[:20],
        "is_stub": bool(table.get("is_stub", False)),
        "stub_text": table.get("stub_text", "") if table.get("is_stub") else "",
        "review_status": table.get("review_status"),
        "uncertainty_flags": _string_list(table.get("uncertainty_flags", [])),
    }


def _deliverable_figure_summary(figure: dict[str, Any]) -> dict[str, Any]:
    return {
        "figure_id": figure.get("figure_id"),
        "figure_number": figure.get("figure_number"),
        "title": figure.get("title"),
        "section_target_id": figure.get("section_target_id"),
        "has_image": bool(figure.get("image_path")) and not bool(figure.get("is_stub", False)),
        "is_stub": bool(figure.get("is_stub", False)),
        "stub_text": figure.get("stub_text", "") if figure.get("is_stub") else "",
        "source_refs": _string_list(figure.get("source_refs", [])),
        "shown_layer_count": len(_dict_list(figure.get("shown_layers", []))),
        "comparison_unit_ids": _string_list(figure.get("comparison_unit_ids", [])),
        "related_constraint_ids": _string_list(figure.get("related_constraint_ids", []))[:20],
        "review_status": figure.get("review_status"),
        "uncertainty_flags": _string_list(figure.get("uncertainty_flags", [])),
        "validation_issue_codes": sorted({str(issue.get("code")) for issue in _dict_list(figure.get("validation_issues", [])) if issue.get("code")}),
    }


def _row_summaries(deliverable_table_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for table in deliverable_table_summaries:
        for row in _dict_list(table.get("rows_preview", [])):
            summaries.append(
                {
                    "table_id": table.get("table_id"),
                    "values": row,
                }
            )
    return summaries[:12]


def _figure_availability(deliverable_figure_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "figure_count": len(deliverable_figure_summaries),
        "available_count": sum(1 for figure in deliverable_figure_summaries if figure.get("has_image")),
        "stub_count": sum(1 for figure in deliverable_figure_summaries if figure.get("is_stub")),
        "figures": [
            {
                "figure_id": figure.get("figure_id"),
                "has_image": figure.get("has_image"),
                "is_stub": figure.get("is_stub"),
                "review_status": figure.get("review_status"),
            }
            for figure in deliverable_figure_summaries
        ],
    }


def _comparison_unit_summaries(
    deliverable_tables: list[dict[str, Any]],
    deliverable_figures: list[dict[str, Any]],
    constraints: dict[str, Any],
    category: str,
) -> list[dict[str, Any]]:
    unit_ids: set[str] = set()
    for item in [*deliverable_tables, *deliverable_figures]:
        unit_ids.update(_string_list(item.get("comparison_unit_ids", [])))
    constraints_by_unit: dict[str, list[dict[str, Any]]] = {}
    for constraint in _dict_list(constraints.get("constraints", [])):
        if category != "overall" and constraint.get("source_category") != category:
            continue
        unit_id = str(constraint.get("comparison_unit_id", ""))
        if unit_id:
            unit_ids.add(unit_id)
            constraints_by_unit.setdefault(unit_id, []).append(constraint)
    summaries = []
    for unit_id in sorted(unit_ids):
        unit_constraints = constraints_by_unit.get(unit_id, [])
        names = sorted({str(item.get("comparison_unit_name", "")) for item in unit_constraints if item.get("comparison_unit_name")})
        summaries.append(
            {
                "comparison_unit_id": unit_id,
                "comparison_unit_name": names[0] if names else "",
                "source_backed_constraint_count": len(unit_constraints),
                "source_refs": sorted({str(item.get("source_id")) for item in unit_constraints if item.get("source_id")}),
            }
        )
    return summaries[:20]


def _constraint_summaries(constraints: dict[str, Any], category: str, source_refs: list[str]) -> list[dict[str, Any]]:
    source_ref_set = set(source_refs)
    summaries: list[dict[str, Any]] = []
    for constraint in _dict_list(constraints.get("constraints", [])):
        if category != "overall" and constraint.get("source_category") != category and str(constraint.get("source_id", "")) not in source_ref_set:
            continue
        summaries.append(
            {
                "constraint_id": constraint.get("constraint_id"),
                "comparison_unit_id": constraint.get("comparison_unit_id"),
                "comparison_unit_name": constraint.get("comparison_unit_name"),
                "source_id": constraint.get("source_id"),
                "source_category": constraint.get("source_category"),
                "source_feature_label": constraint.get("source_feature_label"),
                "source_feature_type": constraint.get("source_feature_type"),
                "relationship_type": constraint.get("relationship_type"),
                "measurements": constraint.get("measurements", {}) if isinstance(constraint.get("measurements"), dict) else {},
                "uncertainty_flags": _string_list(constraint.get("uncertainty_flags", [])),
            }
        )
    return summaries[:12]


def _source_gap_status(source_status: dict[str, Any], category: str) -> list[dict[str, Any]]:
    records = []
    for item in _dict_list(source_status.get("statuses", [])):
        if category != "overall" and item.get("category") != category:
            continue
        records.append(
            {
                "category": item.get("category"),
                "status": item.get("status"),
                "source_ids": _source_ids_for_status(item),
                "notes": item.get("notes", ""),
                "uncertainty_flags": _string_list(item.get("uncertainty_flags", [])),
            }
        )
    return records[:12]


def _section_raw_artifact_paths(
    *,
    constraints: dict[str, Any],
    comparison_tables: dict[str, Any],
    deliverable_tables: dict[str, Any],
    deliverable_figures: dict[str, Any],
    map_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "constraint_results": constraints.get("output_path"),
        "comparison_tables": comparison_tables.get("output_path"),
        "deliverable_tables": deliverable_tables.get("output_path"),
        "deliverable_figures": deliverable_figures.get("output_path"),
        "map_manifest": map_manifest.get("output_path") if map_manifest else None,
    }


def _deliverable_validation_issues(tables: list[dict[str, Any]], figures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for table in tables:
        if table.get("is_stub"):
            issues.append(
                {
                    "severity": "warning",
                    "code": "deliverable_table_created_as_stub",
                    "message": "Required matrix-backed deliverable table is an explicit stub pending source data or implementation.",
                    "table_id": table.get("table_id"),
                }
            )
    for figure in figures:
        issues.extend(_dict_list(figure.get("validation_issues", [])))
    return issues


def _finding_summary(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_id": finding.get("finding_id"),
        "title": finding.get("title"),
        "finding_type": finding.get("finding_type"),
        "source_category": finding.get("source_category"),
        "source_refs": _string_list(finding.get("source_refs", [])),
        "content": _truncate(str(finding.get("generated_content", "")), 900),
        "uncertainty_flags": _string_list(finding.get("uncertainty_flags", [])),
        "provenance": _safe_provenance_summary(finding.get("provenance", {})),
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
    deliverable_tables: dict[str, Any],
    deliverable_figures: dict[str, Any],
) -> list[dict[str, Any]]:
    issues = list(_dict_list(data_lineage.get("validation_issues", [])))
    issues.extend(_dict_list(source_acquisition.get("validation_issues", [])))
    issues.extend(_dict_list(constraints.get("validation_issues", [])))
    issues.extend(_dict_list(deliverable_tables.get("validation_issues", [])))
    issues.extend(_dict_list(deliverable_figures.get("validation_issues", [])))
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
