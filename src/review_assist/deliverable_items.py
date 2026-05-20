"""Matrix-backed deliverable item generation."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .comparison_units import ComparisonUnitError, build_comparison_units, load_comparison_units
from .deliverable_figures import DELIVERABLE_FIGURES_PATH, DeliverableFigureError, generate_deliverable_figures, load_deliverable_figures
from .deliverable_matrix import (
    REQUIRED_STUB_TEXT,
    AttachmentTarget,
    DeliverableMatrixError,
    FigureTarget,
    ReportPrompt,
    SectionTarget,
    TableTarget,
    load_deliverable_matrix,
    load_report_prompt_config,
)
from .deliverable_tables import DELIVERABLE_TABLES_PATH, DeliverableTableError, generate_deliverable_tables, load_deliverable_tables
from .env_config import GptConfigurationError, gpt_drafting_enabled, gpt_drafting_workers, resolve_gpt_model
from .evidence_package import EVIDENCE_PACKAGE_PATH, EvidencePackageError, build_evidence_package, load_evidence_package, section_evidence_for
from .extent_policy import (
    COMMUNITY_CONTEXT_EXTENT,
    COUNTY_OR_REGIONAL_CONTEXT_EXTENT,
    DIRECT_TARGET_IDS,
    EXTENT_FIELD_NAMES,
    NEARBY_CONTEXT_EXTENT,
    WATERSHED_CONTEXT_EXTENT,
    apply_extent_metadata,
    extent_wording_for_scope,
    merge_extent_metadata,
    target_extent_metadata,
)
from .project_context import ProjectContextError, generate_project_context, load_project_context
from .projects import ProjectManifestError, load_project_manifest
from .section_drafting import (
    SectionDraftingError,
    SectionDraftRequest,
    default_section_draft_provider,
    openai_section_draft_provider,
)


DELIVERABLE_ITEMS_PATH = Path("deliverable/deliverable_items.json")
STATIC_SECTION_TARGET_TYPES = {"front_matter", "section", "subsection", "attachment"}
GENERATED_CONTENT_WARNING_CHAR_LIMIT = 4_000
SUPPORTED_REVIEW_STATUSES = {
    "draft",
    "needs_review",
    "needs_verification",
    "accepted",
    "edited",
    "replaced",
    "declined",
    "unable_to_verify",
}
VERIFICATION_SOURCE_STATES = {"gated", "restricted", "manual", "stubbed"}
REVIEW_SOURCE_STATES = {"missing", "downloadable", "failed", "needs_review", "source_missing", "unimplemented"}
AVAILABLE_SOURCE_STATES = {"provided_locally", "local_materialized", "downloaded", "available"}
FIRST_PASS_REPORT_STYLE_SECTION_IDS = {
    "wetlands-and-waterbodies",
    "cultural-and-historic-resources",
    "community-resources",
    "utility-and-infrastructure-considerations",
    "utility-infrastructure",
    "energy-infrastructure",
    "contamination-risks",
    "hazardous-materials-sites",
    "oil-wells",
}
SOURCE_DISPLAY_NAMES = {
    "usfws_nwi_wetlands": "U.S. Fish and Wildlife Service National Wetlands Inventory",
    "usgs_nhd_hydrography": "U.S. Geological Survey National Hydrography Dataset",
    "usgs_nhd_flowlines": "U.S. Geological Survey NHD flowlines",
    "usgs_nhd_waterbodies": "U.S. Geological Survey NHD waterbodies",
    "usgs_nhd_other_areas": "U.S. Geological Survey NHD other areas",
    "fema_nfhl_flood_hazard": "FEMA National Flood Hazard Layer",
    "usfws_critical_habitat": "U.S. Fish and Wildlife Service critical habitat",
    "maris_public_cultural_context": "MARIS public cultural context",
    "mdot_transportation_context": "Mississippi transportation context",
    "epa_envirofacts_echo": "EPA ECHO regulated facilities",
    "epa_frs_facilities_ms": "EPA Facility Registry Service facilities",
    "maris_brownfields": "MARIS brownfields",
    "maris_npdes_facilities": "MARIS NPDES facilities",
    "maris_solid_waste_landfills": "MARIS solid waste landfills",
    "maris_superfund_sites": "MARIS Superfund sites",
    "maris_tri_facilities": "MARIS TRI facilities",
    "maris_underground_storage_tanks": "MARIS underground storage tanks",
    "mississippi_oil_gas_wells": "Mississippi Oil and Gas Board wells",
    "usfws_national_wildlife_refuges": "U.S. Fish and Wildlife Service national wildlife refuges",
    "usda_nrcs_easements": "USDA NRCS easements",
}
CONTEXT_ONLY_SOURCE_REF_FRAGMENTS = ("naip", "imagery_basemap", "aerial_basemap")
REQUIRED_TOP_LEVEL_FIELDS = {
    "project_id",
    "project_name",
    "created_at",
    "matrix_version",
    "profile_id",
    "item_count",
    "expected_item_count",
    "items",
    "validation_issues",
    "upstream_artifacts",
    "output_path",
}
REQUIRED_ITEM_FIELDS = {
    "deliverable_item_id",
    "target_id",
    "target_type",
    "review_item_type",
    "title",
    "section_number",
    "section_order",
    "heading_level",
    "export_group",
    "resource_category",
    "generated_content",
    "replacement_content",
    "table_id",
    "figure_id",
    "attachment_id",
    "source_refs",
    "related_finding_ids",
    "related_constraint_ids",
    "related_table_ids",
    "related_figure_ids",
    "evidence_refs",
    "comparison_unit_ids",
    "provenance",
    "assumptions",
    "uncertainty_flags",
    "is_stub",
    "stub_text",
    "review_status",
    "export_eligible",
    "validation_issues",
    *EXTENT_FIELD_NAMES,
    "extent_policy_version",
}


class DeliverableItemsError(RuntimeError):
    """Raised when deliverable item generation or loading cannot complete."""


def generate_deliverable_items(
    project_dir: Path,
    *,
    gpt_drafting: bool | None = None,
    gpt_model: str | None = None,
) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        context = _load_or_generate_context(project_dir)
        matrix = load_deliverable_matrix()
        prompts = load_report_prompt_config()
        comparison_units = _load_or_build_comparison_units(project_dir)
        tables = _load_or_generate_tables(project_dir)
        figures = _load_or_generate_figures(project_dir)
        evidence_package = _load_or_generate_evidence_package(project_dir)
        unit_records = _comparison_unit_records(comparison_units)
        use_gpt_drafting = gpt_drafting_enabled() if gpt_drafting is None else gpt_drafting
        model = resolve_gpt_model(gpt_model) if use_gpt_drafting else ""
    except (
        ProjectManifestError,
        ProjectContextError,
        DeliverableMatrixError,
        ComparisonUnitError,
        DeliverableTableError,
        DeliverableFigureError,
        EvidencePackageError,
        GptConfigurationError,
    ) as exc:
        raise DeliverableItemsError(str(exc)) from exc

    prompt_by_key = prompts.by_prompt_key()
    draft_provider = openai_section_draft_provider(model=model) if use_gpt_drafting else default_section_draft_provider()
    workers = gpt_drafting_workers() if use_gpt_drafting else 1
    now = _utc_now()
    output_path = project_dir / DELIVERABLE_ITEMS_PATH
    section_items = _section_items(
        matrix=matrix,
        prompts=prompts,
        prompt_by_key=prompt_by_key,
        context=context,
        comparison_units=unit_records,
        tables=tables,
        figures=figures,
        evidence_package=evidence_package,
        draft_provider=draft_provider,
        workers=workers,
        parallel=use_gpt_drafting,
    )
    table_items = [_table_item(target, tables, matrix.matrix_version, output_path) for target in matrix.table_targets]
    figure_items = [_figure_item(target, figures, matrix.matrix_version, output_path) for target in matrix.figure_targets]
    attachment_items = [_attachment_item(target, figures, matrix.matrix_version, output_path) for target in matrix.attachment_targets]
    items = [*section_items, *table_items, *figure_items, *attachment_items]
    validation_issues = _dedupe_issues([*_artifact_validation_issues(items), *_dict_list(evidence_package.get("validation_issues", []))])
    expected_item_count = _expected_item_count(matrix.section_targets, matrix.table_targets, matrix.figure_targets, matrix.attachment_targets, unit_records)
    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": now,
        "matrix_version": matrix.matrix_version,
        "profile_id": matrix.profile_id,
        "item_count": len(items),
        "expected_item_count": expected_item_count,
        "items": items,
        "validation_issues": validation_issues,
        "upstream_artifacts": {
            "deliverable_matrix_path": "config/deliverable_section_matrix.json",
            "report_generation_prompts_path": "config/report_generation_prompts.json",
            "project_context_path": context.get("context_path"),
            "comparison_units_metadata_path": comparison_units.get("output_path"),
            "comparison_units_path": comparison_units.get("comparison_units_path"),
            "deliverable_tables_path": tables.get("output_path"),
            "deliverable_figures_path": figures.get("output_path"),
            "evidence_package_path": evidence_package.get("output_path"),
        },
        "gpt_drafting": _gpt_drafting_summary(items, enabled=use_gpt_drafting, model=model, workers=workers),
        "output_path": str(output_path),
    }
    validate_deliverable_items(result, str(output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_deliverable_items(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / DELIVERABLE_ITEMS_PATH
    if not path.exists():
        raise DeliverableItemsError(f"Missing deliverable items artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeliverableItemsError(f"Invalid deliverable items JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DeliverableItemsError(f"Deliverable items artifact must be a JSON object: {path}")
    _normalize_deliverable_items_compat(data)
    validate_deliverable_items(data, str(path))
    return data


def _normalize_deliverable_items_compat(data: dict[str, Any]) -> None:
    items = data.get("items")
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        provenance = item.get("provenance", {}) if isinstance(item.get("provenance"), dict) else {}
        assumptions = item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {}
        extent = _item_extent_metadata(
            target_id=str(item.get("target_id") or item.get("deliverable_item_id") or ""),
            target_type=str(item.get("target_type") or ""),
            resource_category=str(item.get("resource_category") or ""),
            provenance=provenance,
            assumptions=assumptions,
        )
        apply_extent_metadata(item, extent)


def validate_deliverable_items(data: dict[str, Any], location: str) -> None:
    missing_top = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(data))
    if missing_top:
        raise DeliverableItemsError(f"Deliverable items artifact is missing required fields {missing_top}: {location}")
    items = data.get("items")
    if not isinstance(items, list):
        raise DeliverableItemsError(f"Deliverable items artifact requires a list field named 'items': {location}")
    if data.get("item_count") != len(items):
        raise DeliverableItemsError(f"Deliverable items artifact item_count does not match items: {location}")
    if data.get("expected_item_count") != len(items):
        raise DeliverableItemsError(f"Deliverable items artifact expected_item_count does not match items: {location}")
    if not isinstance(data.get("validation_issues"), list):
        raise DeliverableItemsError(f"Deliverable items artifact validation_issues must be a list: {location}")
    if not isinstance(data.get("upstream_artifacts"), dict):
        raise DeliverableItemsError(f"Deliverable items artifact upstream_artifacts must be an object: {location}")

    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise DeliverableItemsError(f"Each deliverable item must be an object: {location}")
        missing = sorted(REQUIRED_ITEM_FIELDS - set(item))
        if missing:
            raise DeliverableItemsError(f"Deliverable item is missing required fields {missing}: {location}")
        item_id = item["deliverable_item_id"]
        if not isinstance(item_id, str) or not item_id.strip():
            raise DeliverableItemsError(f"Deliverable item requires a non-empty deliverable_item_id: {location}")
        if item_id in seen_ids:
            raise DeliverableItemsError(f"Duplicate deliverable item id '{item_id}': {location}")
        seen_ids.add(item_id)
        if item["target_id"] != item_id:
            raise DeliverableItemsError(f"Deliverable item '{item_id}' target_id must match deliverable_item_id: {location}")
        if item["review_status"] not in SUPPORTED_REVIEW_STATUSES:
            raise DeliverableItemsError(f"Deliverable item '{item_id}' has unsupported review_status: {location}")
        if not isinstance(item["export_eligible"], bool):
            raise DeliverableItemsError(f"Deliverable item '{item_id}' export_eligible must be boolean: {location}")
        if not isinstance(item["is_stub"], bool):
            raise DeliverableItemsError(f"Deliverable item '{item_id}' is_stub must be boolean: {location}")
        if item["is_stub"]:
            if item["stub_text"] != REQUIRED_STUB_TEXT:
                raise DeliverableItemsError(f"Deliverable item '{item_id}' stub_text must use the canonical stub text: {location}")
            if not isinstance(item["generated_content"], str) or not item["generated_content"].strip():
                raise DeliverableItemsError(f"Deliverable item '{item_id}' stub generated_content must be non-empty: {location}")
        if item["export_eligible"] and item["review_status"] not in {"accepted", "edited", "replaced", "unable_to_verify"}:
            raise DeliverableItemsError(f"Deliverable item '{item_id}' cannot be export eligible with status '{item['review_status']}': {location}")
        for list_field in (
            "source_refs",
            "related_finding_ids",
            "related_constraint_ids",
            "related_table_ids",
            "related_figure_ids",
            "evidence_refs",
            "comparison_unit_ids",
            "uncertainty_flags",
            "validation_issues",
        ):
            if not isinstance(item[list_field], list):
                raise DeliverableItemsError(f"Deliverable item '{item_id}' field '{list_field}' must be a list: {location}")
        for object_field in ("provenance", "assumptions"):
            if not isinstance(item[object_field], dict):
                raise DeliverableItemsError(f"Deliverable item '{item_id}' field '{object_field}' must be an object: {location}")


def _load_or_generate_context(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_context(project_dir)
    except ProjectContextError:
        return generate_project_context(project_dir)


def _load_or_build_comparison_units(project_dir: Path) -> dict[str, Any]:
    try:
        return load_comparison_units(project_dir)
    except ComparisonUnitError:
        return build_comparison_units(project_dir)


def _load_or_generate_tables(project_dir: Path) -> dict[str, Any]:
    if (project_dir / DELIVERABLE_TABLES_PATH).exists():
        return load_deliverable_tables(project_dir)
    return generate_deliverable_tables(project_dir)


def _load_or_generate_figures(project_dir: Path) -> dict[str, Any]:
    if (project_dir / DELIVERABLE_FIGURES_PATH).exists():
        return load_deliverable_figures(project_dir)
    return generate_deliverable_figures(project_dir)


def _load_or_generate_evidence_package(project_dir: Path) -> dict[str, Any]:
    if (project_dir / EVIDENCE_PACKAGE_PATH).exists():
        return load_evidence_package(project_dir)
    return build_evidence_package(project_dir)


def _comparison_unit_records(comparison_units: dict[str, Any]) -> list[dict[str, Any]]:
    path = Path(str(comparison_units.get("comparison_units_path", "")))
    if not path.exists():
        raise DeliverableItemsError(f"Missing comparison units GeoJSON artifact: {path}")
    import geopandas as gpd

    gdf = gpd.read_file(path)
    records: list[dict[str, Any]] = []
    for index, row in gdf.iterrows():
        unit_id = _row_string(row, "comparison_unit_id", f"comparison-unit-{index + 1}")
        records.append(
            {
                "comparison_unit_id": unit_id,
                "comparison_unit_name": _row_string(row, "comparison_unit_name", unit_id),
                "comparison_unit_group": _row_string(row, "comparison_unit_group", ""),
                "comparison_unit_type": _row_string(row, "comparison_unit_type", ""),
            }
        )
    return records


def _section_items(
    *,
    matrix: Any,
    prompts: Any,
    prompt_by_key: dict[str, ReportPrompt],
    context: dict[str, Any],
    comparison_units: list[dict[str, Any]],
    tables: dict[str, Any],
    figures: dict[str, Any],
    evidence_package: dict[str, Any],
    draft_provider: Any,
    workers: int,
    parallel: bool,
) -> list[dict[str, Any]]:
    target_records = _expanded_section_targets(matrix.section_targets, comparison_units)
    kwargs = {
        "matrix_version": matrix.matrix_version,
        "prompt_version": prompts.prompt_version,
        "global_prompt": prompt_by_key.get(prompts.global_prompt_key),
        "prompt_by_key": prompt_by_key,
        "context": context,
        "tables": tables,
        "figures": figures,
        "evidence_package": evidence_package,
        "draft_provider": draft_provider,
    }
    if not parallel or workers <= 1:
        return [_section_item(target_record=target_record, **kwargs) for target_record in target_records]

    ordered: list[dict[str, Any] | None] = [None] * len(target_records)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_section_item, target_record=target_record, **kwargs): (index, target_record["target"].target_id)
            for index, target_record in enumerate(target_records)
        }
        for future in as_completed(futures):
            index, target_id = futures[future]
            try:
                ordered[index] = future.result()
            except DeliverableItemsError:
                raise
            except Exception as exc:
                raise DeliverableItemsError(f"Deliverable item section target '{target_id}' failed: {exc}") from exc
    return [item for item in ordered if item is not None]


def _expanded_section_targets(section_targets: list[SectionTarget], comparison_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {target.target_id: target for target in section_targets}
    records: list[dict[str, Any]] = []
    for target in section_targets:
        if target.target_type == "dynamic_subsection_template":
            continue
        records.append({"target": target, "template_target": None, "comparison_unit": None, "dynamic": False})
        if not target.dynamic_children:
            continue
        template_id = str(target.dynamic_children.get("template_target_id", ""))
        template = by_id.get(template_id)
        if template is None:
            raise DeliverableItemsError(f"Dynamic target '{target.target_id}' references missing template '{template_id}'.")
        for index, unit in enumerate(comparison_units, start=1):
            records.append(
                {
                    "target": _dynamic_target(template, target.dynamic_children, unit, index),
                    "template_target": template,
                    "comparison_unit": unit,
                    "dynamic": True,
                }
            )
    return records


def _dynamic_target(
    template: SectionTarget,
    dynamic_config: dict[str, Any],
    comparison_unit: dict[str, Any],
    index: int,
) -> SectionTarget:
    unit_id = str(comparison_unit.get("comparison_unit_id", "")).strip() or f"comparison-unit-{index}"
    unit_name = str(comparison_unit.get("comparison_unit_name", "")).strip() or unit_id
    substitutions = {
        "index": str(index),
        "comparison_unit_id": unit_id,
        "comparison_unit_name": unit_name,
    }
    return SectionTarget(
        target_id=_format_pattern(dynamic_config.get("target_id_pattern"), substitutions, f"{template.target_id}-{unit_id}"),
        target_type="subsection",
        section_number=_format_pattern(dynamic_config.get("section_number_pattern"), substitutions, template.section_number or ""),
        title=_format_pattern(dynamic_config.get("title_pattern"), substitutions, unit_name),
        heading_level=template.heading_level,
        section_order=float(template.section_order) + (index / 1000.0),
        export_group=template.export_group,
        resource_category=template.resource_category,
        required=template.required,
        prompt_key=template.prompt_key,
        source_categories=list(template.source_categories),
        table_refs=list(template.table_refs),
        figure_refs=list(template.figure_refs),
        attachment_refs=list(template.attachment_refs),
        dynamic_children=None,
        stub_when_missing=template.stub_when_missing,
        review_item_type=template.review_item_type,
    )


def _section_item(
    *,
    target_record: dict[str, Any],
    matrix_version: str,
    prompt_version: str,
    global_prompt: ReportPrompt | None,
    prompt_by_key: dict[str, ReportPrompt],
    context: dict[str, Any],
    tables: dict[str, Any],
    figures: dict[str, Any],
    evidence_package: dict[str, Any],
    draft_provider: Any,
) -> dict[str, Any]:
    target: SectionTarget = target_record["target"]
    template_target: SectionTarget | None = target_record.get("template_target")
    comparison_unit = target_record.get("comparison_unit") if isinstance(target_record.get("comparison_unit"), dict) else None
    prompt = prompt_by_key.get(target.prompt_key)
    if prompt is None:
        raise DeliverableItemsError(f"Missing report prompt for deliverable target '{target.target_id}': {target.prompt_key}")

    evidence = _section_evidence(evidence_package, target, template_target, comparison_unit)
    related_tables = _related_table_records(tables, target.table_refs)
    related_figures = _related_figure_records(figures, target.figure_refs)
    related_table_ids = [str(table.get("table_id")) for table in related_tables if table.get("table_id")]
    related_figure_ids = [str(figure.get("figure_id")) for figure in related_figures if figure.get("figure_id")]
    source_refs = _dedupe(
        [
            *_string_list(evidence.get("source_refs", [])),
            *[ref for table in related_tables for ref in _string_list(table.get("source_refs", []))],
            *[ref for figure in related_figures for ref in _string_list(figure.get("source_refs", []))],
        ]
    )
    comparison_unit_ids = [str(comparison_unit["comparison_unit_id"])] if comparison_unit else _evidence_comparison_unit_ids(evidence, related_tables, related_figures)
    validation_issues = _target_validation_issues(evidence, related_tables, related_figures, target)
    evidence_refs = _evidence_refs(evidence)
    source_gap_status = _dict_list(evidence.get("source_gap_status", []))
    extent_metadata = _section_extent_metadata(target, evidence, related_tables, related_figures)
    is_stub = _section_is_stub(target, evidence, related_tables, related_figures, source_gap_status, comparison_unit)
    generated_content = _stub_section_content(target, source_gap_status, related_tables, related_figures, validation_issues) if is_stub else _section_content(
        target=target,
        context=context,
        evidence=evidence,
        related_tables=related_tables,
        related_figures=related_figures,
        comparison_unit=comparison_unit,
        extent_metadata=extent_metadata,
    )
    uncertainty_flags = _dedupe(
        [
            "draft_pre_review",
            "desktop_screening_only",
            *[str(issue.get("code")) for issue in validation_issues if issue.get("code")],
            *[str(flag) for status in source_gap_status for flag in _string_list(status.get("uncertainty_flags", []))],
            *[flag for table in related_tables for flag in _string_list(table.get("uncertainty_flags", []))],
            *[flag for figure in related_figures for flag in _string_list(figure.get("uncertainty_flags", []))],
        ]
    )
    if is_stub:
        uncertainty_flags = _dedupe([*uncertainty_flags, "deliverable_item_stub"])
    review_status = _review_status(target, is_stub, source_gap_status, validation_issues, related_tables, related_figures)

    try:
        draft_result = draft_provider.draft(
            SectionDraftRequest(
                section_id=target.target_id,
                target_id=target.target_id,
                section_type=target.target_type,
                title=target.title,
                purpose=prompt.section_instruction,
                resource_category=target.resource_category,
                deterministic_content=generated_content,
                related_finding_ids=_evidence_finding_ids(evidence),
                related_table_ids=related_table_ids,
                related_figure_ids=related_figure_ids,
                source_refs=source_refs,
                evidence_bundle=evidence,
                extent_metadata=extent_metadata,
                validation_issues=validation_issues,
                project_context=context,
                matrix_target=_matrix_target_summary(target, template_target=template_target, comparison_unit=comparison_unit),
                prompt_key=target.prompt_key,
                prompt=_prompt_summary(prompt),
                global_prompt=_prompt_summary(global_prompt),
                allowed_inputs=_dedupe([*(global_prompt.allowed_inputs if global_prompt else []), *prompt.allowed_inputs]),
                citation_policy={"global": global_prompt.citation_policy if global_prompt else {}, "section": prompt.citation_policy},
            )
        )
    except (SectionDraftingError, GptConfigurationError) as exc:
        raise DeliverableItemsError(str(exc)) from exc

    validation_issues = validation_issues + draft_result.validation_issues
    if draft_result.provenance.get("draft_provider") == "openai_responses":
        uncertainty_flags = _dedupe([*uncertainty_flags, "gpt_drafted_pre_review"])
    if any(issue.get("code") in {"gpt_output_rejected", "gpt_empty_output"} for issue in draft_result.validation_issues):
        uncertainty_flags = _dedupe([*uncertainty_flags, "gpt_draft_rejected"])
    content = generated_content if is_stub else draft_result.content

    return _base_item(
        deliverable_item_id=target.target_id,
        target_id=target.target_id,
        target_type=target.target_type,
        review_item_type=target.review_item_type,
        title=target.title,
        section_number=target.section_number,
        section_order=target.section_order,
        heading_level=target.heading_level,
        export_group=target.export_group,
        resource_category=target.resource_category,
        generated_content=content,
        table_id="",
        figure_id="",
        attachment_id="",
        source_refs=source_refs,
        related_finding_ids=_evidence_finding_ids(evidence),
        related_constraint_ids=_evidence_constraint_ids(evidence),
        related_table_ids=related_table_ids,
        related_figure_ids=related_figure_ids,
        evidence_refs=evidence_refs,
        comparison_unit_ids=comparison_unit_ids,
        provenance={
            "artifact": "deliverable_items",
            "matrix_version": matrix_version,
            "prompt_version": prompt_version,
            "target_id": target.target_id,
            "template_target_id": template_target.target_id if template_target else "",
            "prompt_key": target.prompt_key,
            "draft_provider": draft_result.provenance.get("draft_provider", getattr(draft_provider, "provider_id", "unknown")),
            "drafting": draft_result.provenance,
            "evidence_package_path": evidence_package.get("output_path"),
            "extent_policy": extent_metadata,
            "review_before_export": True,
            "desktop_screening_only": True,
        },
        assumptions={
            "matrix_target": _matrix_target_summary(target, template_target=template_target, comparison_unit=comparison_unit),
            "prompt_contract": _prompt_summary(prompt),
            "source_gap_status": source_gap_status,
            "extent_policy": extent_metadata,
        },
        uncertainty_flags=uncertainty_flags,
        is_stub=is_stub,
        review_status=review_status,
        validation_issues=validation_issues,
    )


def _table_item(target: TableTarget, tables: dict[str, Any], matrix_version: str, output_path: Path) -> dict[str, Any]:
    table = _table_lookup(tables).get(target.target_id, {})
    is_stub = bool(table.get("is_stub", True))
    content = _stub_table_content(target, table) if is_stub else _generated_table_content(target, table)
    extent_metadata = _record_extent_metadata(
        table,
        fallback=target_extent_metadata(target_id=target.target_id, target_type="table", source_categories=target.source_categories),
    )
    return _base_item(
        deliverable_item_id=target.target_id,
        target_id=target.target_id,
        target_type="table",
        review_item_type=target.review_item_type,
        title=str(table.get("title") or target.title),
        section_number=None,
        section_order=10_000 + target.table_number,
        heading_level=None,
        export_group="tables",
        resource_category=_first_string(target.source_categories) or "tables",
        generated_content=content,
        table_id=target.target_id,
        figure_id="",
        attachment_id="",
        source_refs=_string_list(table.get("source_refs", [])),
        related_finding_ids=[],
        related_constraint_ids=_string_list(table.get("related_constraint_ids", [])),
        related_table_ids=[],
        related_figure_ids=[],
        evidence_refs=[],
        comparison_unit_ids=_string_list(table.get("comparison_unit_ids", [])),
        provenance={
            "artifact": "deliverable_tables",
            "artifact_path": tables.get("output_path"),
            "matrix_version": matrix_version,
            "table_id": target.target_id,
            "section_target_id": target.section_target_id,
            "table_provenance": table.get("provenance", {}),
            "extent_policy": extent_metadata,
            "review_before_export": True,
        },
        assumptions={
            "columns": _string_list(table.get("columns", [])),
            "row_count": table.get("row_count", 0),
            "rows_preview": _dict_list(table.get("rows", []))[:5],
            "extent_policy": extent_metadata,
        },
        uncertainty_flags=_dedupe(["draft_pre_review", *_string_list(table.get("uncertainty_flags", []))]),
        is_stub=is_stub,
        review_status=_normalized_review_status(table.get("review_status", "needs_review" if is_stub else "draft")),
        validation_issues=_dict_list(table.get("validation_issues", [])) + _missing_upstream_issue(table, target.target_id, output_path, "table"),
    )


def _figure_item(target: FigureTarget, figures: dict[str, Any], matrix_version: str, output_path: Path) -> dict[str, Any]:
    figure = _figure_lookup(figures).get(target.target_id, {})
    is_stub = bool(figure.get("is_stub", True))
    content = _stub_figure_content(target, figure) if is_stub else _generated_figure_content(target, figure)
    extent_metadata = _record_extent_metadata(
        figure,
        fallback=target_extent_metadata(target_id=target.target_id, target_type="figure", source_categories=target.source_categories),
    )
    return _base_item(
        deliverable_item_id=target.target_id,
        target_id=target.target_id,
        target_type="figure",
        review_item_type=target.review_item_type,
        title=str(figure.get("title") or target.title),
        section_number=None,
        section_order=20_000 + target.figure_number,
        heading_level=None,
        export_group="figures",
        resource_category=_first_string(target.source_categories) or "figures",
        generated_content=content,
        table_id="",
        figure_id=target.target_id,
        attachment_id="",
        source_refs=_string_list(figure.get("source_refs", [])),
        related_finding_ids=[],
        related_constraint_ids=_string_list(figure.get("related_constraint_ids", [])),
        related_table_ids=[],
        related_figure_ids=[],
        evidence_refs=[],
        comparison_unit_ids=_string_list(figure.get("comparison_unit_ids", [])),
        provenance={
            "artifact": "deliverable_figures",
            "artifact_path": figures.get("output_path"),
            "matrix_version": matrix_version,
            "figure_id": target.target_id,
            "section_target_id": target.section_target_id,
            "figure_provenance": figure.get("provenance", {}),
            "extent_policy": extent_metadata,
            "review_before_export": True,
        },
        assumptions={
            "image_path": figure.get("image_path", ""),
            "caption": figure.get("caption", ""),
            "source_note": figure.get("source_note", ""),
            "method_note": figure.get("method_note", ""),
            "extent_policy": extent_metadata,
        },
        uncertainty_flags=_dedupe(["draft_pre_review", *_string_list(figure.get("uncertainty_flags", []))]),
        is_stub=is_stub,
        review_status=_normalized_review_status(figure.get("review_status", "needs_review" if is_stub else "draft")),
        validation_issues=_dict_list(figure.get("validation_issues", [])) + _missing_upstream_issue(figure, target.target_id, output_path, "figure"),
    )


def _attachment_item(target: AttachmentTarget, figures: dict[str, Any], matrix_version: str, output_path: Path) -> dict[str, Any]:
    related_figure_ids: list[str] = []
    validation_issues: list[dict[str, Any]] = []
    if target.target_id == "attachment-environmental-constraints-maps":
        related_figure_ids = [
            str(figure.get("figure_id"))
            for figure in [*_dict_list(figures.get("figures", [])), *_dict_list(figures.get("attachment_supporting_figures", []))]
            if figure.get("figure_id")
        ]
        if not related_figure_ids:
            validation_issues.append(_issue("warning", "attachment_source_missing", "Attachment A has no generated figure artifacts.", str(output_path), target.target_id))
    else:
        validation_issues.append(_issue("warning", "attachment_source_missing", "Required attachment support is not supplied by the automated Sprint 3.1 workflow.", str(output_path), target.target_id))
    is_stub = target.target_id != "attachment-environmental-constraints-maps" or not related_figure_ids
    content = _stub_attachment_content(target, validation_issues) if is_stub else _generated_attachment_content(target, related_figure_ids)
    extent_metadata = target_extent_metadata(target_id=target.target_id, target_type="attachment", resource_category="attachments")
    return _base_item(
        deliverable_item_id=target.target_id,
        target_id=target.target_id,
        target_type="attachment",
        review_item_type=target.review_item_type,
        title=target.title,
        section_number=f"Attachment {target.attachment_letter}",
        section_order=30_000 + ord(target.attachment_letter[0]),
        heading_level=None,
        export_group="attachments",
        resource_category="attachments",
        generated_content=content,
        table_id="",
        figure_id="",
        attachment_id=target.target_id,
        source_refs=[],
        related_finding_ids=[],
        related_constraint_ids=[],
        related_table_ids=[],
        related_figure_ids=related_figure_ids,
        evidence_refs=[],
        comparison_unit_ids=[],
        provenance={
            "artifact": "deliverable_items",
            "matrix_version": matrix_version,
            "attachment_id": target.target_id,
            "section_target_id": target.section_target_id,
            "deliverable_figures_path": figures.get("output_path"),
            "extent_policy": extent_metadata,
            "review_before_export": True,
        },
        assumptions={"required_attachment": True, "extent_policy": extent_metadata},
        uncertainty_flags=_dedupe(["draft_pre_review", "desktop_screening_only", *[str(issue.get("code")) for issue in validation_issues]]),
        is_stub=is_stub,
        review_status="needs_review",
        validation_issues=validation_issues,
    )


def _base_item(
    *,
    deliverable_item_id: str,
    target_id: str,
    target_type: str,
    review_item_type: str,
    title: str,
    section_number: str | None,
    section_order: float,
    heading_level: int | None,
    export_group: str,
    resource_category: str,
    generated_content: str,
    table_id: str,
    figure_id: str,
    attachment_id: str,
    source_refs: list[str],
    related_finding_ids: list[str],
    related_constraint_ids: list[str],
    related_table_ids: list[str],
    related_figure_ids: list[str],
    evidence_refs: list[str],
    comparison_unit_ids: list[str],
    provenance: dict[str, Any],
    assumptions: dict[str, Any],
    uncertainty_flags: list[str],
    is_stub: bool,
    review_status: str,
    validation_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    status = _normalized_review_status(review_status)
    issues = list(validation_issues)
    extent_metadata = _item_extent_metadata(
        target_id=target_id,
        target_type=target_type,
        resource_category=resource_category,
        provenance=provenance,
        assumptions=assumptions,
    )
    if len(generated_content) > GENERATED_CONTENT_WARNING_CHAR_LIMIT:
        issues.append(
            _issue(
                "warning",
                "deliverable_item_content_over_budget",
                (
                    f"Deliverable item '{deliverable_item_id}' generated content is {len(generated_content)} characters; "
                    f"compact report sections should stay under {GENERATED_CONTENT_WARNING_CHAR_LIMIT} characters unless reviewed."
                ),
                str(DELIVERABLE_ITEMS_PATH),
                target_id,
            )
        )
    item = {
        "deliverable_item_id": deliverable_item_id,
        "target_id": target_id,
        "target_type": target_type,
        "review_item_type": review_item_type,
        "title": title,
        "section_number": section_number,
        "section_order": section_order,
        "heading_level": heading_level,
        "export_group": export_group,
        "resource_category": resource_category,
        "generated_content": generated_content,
        "replacement_content": "",
        "table_id": table_id,
        "figure_id": figure_id,
        "attachment_id": attachment_id,
        "source_refs": _dedupe(source_refs),
        "related_finding_ids": _dedupe(related_finding_ids),
        "related_constraint_ids": _dedupe(related_constraint_ids),
        "related_table_ids": _dedupe(related_table_ids),
        "related_figure_ids": _dedupe(related_figure_ids),
        "evidence_refs": _dedupe(evidence_refs),
        "comparison_unit_ids": _dedupe(comparison_unit_ids),
        "provenance": provenance,
        "assumptions": assumptions,
        "uncertainty_flags": _dedupe(uncertainty_flags),
        "is_stub": is_stub,
        "stub_text": REQUIRED_STUB_TEXT if is_stub else "",
        "review_status": status,
        "export_eligible": status in {"accepted", "edited", "replaced", "unable_to_verify"},
        "validation_issues": _dedupe_issues(issues),
    }
    return apply_extent_metadata(item, extent_metadata)


def _section_evidence(
    evidence_package: dict[str, Any],
    target: SectionTarget,
    template_target: SectionTarget | None,
    comparison_unit: dict[str, Any] | None,
) -> dict[str, Any]:
    for section_id in (target.target_id, template_target.target_id if template_target else ""):
        evidence = section_evidence_for(evidence_package, section_id)
        if evidence:
            if comparison_unit:
                return _comparison_unit_evidence(evidence, comparison_unit)
            return evidence

    if target.target_type == "attachment" and target.attachment_refs:
        return {}

    category_candidates: list[dict[str, Any]] = []
    for category in target.source_categories:
        for section_id in (category.replace("_", "-"), category):
            evidence = section_evidence_for(evidence_package, section_id)
            if evidence:
                category_candidates.append(evidence)
    if target.source_categories:
        evidence = section_evidence_for(evidence_package, target.resource_category.replace("_", "-"))
        if evidence:
            category_candidates.append(evidence)

    sections = evidence_package.get("section_evidence", {})
    if isinstance(sections, dict) and target.source_categories:
        source_categories = {target.resource_category, *target.source_categories}
        for evidence in sections.values():
            if isinstance(evidence, dict) and evidence.get("resource_category") in source_categories:
                category_candidates.append(evidence)
    if category_candidates:
        evidence = _best_section_evidence(category_candidates)
        if comparison_unit:
            return _comparison_unit_evidence(evidence, comparison_unit)
        return evidence
    return {}


def _best_section_evidence(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.get("section_id") or candidate.get("resource_category") or id(candidate))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return sorted(enumerate(deduped), key=lambda item: (_section_evidence_score(item[1]), item[0]))[0][1]


def _section_evidence_score(evidence: dict[str, Any]) -> int:
    statuses = {str(status.get("status", "")) for status in _dict_list(evidence.get("source_gap_status", []))}
    if statuses.intersection({"provided_locally", "local_materialized", "downloaded", "available"}):
        return 0
    evidence_classes = set(_string_list(evidence.get("evidence_classes", [])))
    if evidence_classes and not evidence_classes.issubset({"failed_or_missing", "stub_or_manual"}):
        return 1
    if statuses and statuses.issubset(VERIFICATION_SOURCE_STATES | REVIEW_SOURCE_STATES):
        return 3
    return 2


def _comparison_unit_evidence(evidence: dict[str, Any], comparison_unit: dict[str, Any]) -> dict[str, Any]:
    unit_id = str(comparison_unit.get("comparison_unit_id", ""))
    unit_name = str(comparison_unit.get("comparison_unit_name", ""))
    compact = dict(evidence)
    compact["comparison_unit"] = {
        "comparison_unit_id": unit_id,
        "comparison_unit_name": unit_name,
        "comparison_unit_type": comparison_unit.get("comparison_unit_type", ""),
    }
    compact["comparison_unit_summaries"] = [
        summary
        for summary in _dict_list(evidence.get("comparison_unit_summaries", []))
        if unit_id in _string_list(summary.get("comparison_unit_ids", [])) or unit_name == str(summary.get("comparison_unit_name", ""))
    ] or [{"comparison_unit_id": unit_id, "comparison_unit_name": unit_name, "source_refs": evidence.get("source_refs", [])}]
    return compact


def _section_is_stub(
    target: SectionTarget,
    evidence: dict[str, Any],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    source_gap_status: list[dict[str, Any]],
    comparison_unit: dict[str, Any] | None,
) -> bool:
    if not target.stub_when_missing:
        return False
    if target.target_type in {"front_matter", "section"} and not target.source_categories and not comparison_unit:
        return False
    if target.resource_category in {"methodology", "introduction", "assumptions_caveats", "constraints_inventory", "conclusion", "front_matter", "executive_summary"}:
        return False
    if related_tables and any(not table.get("is_stub") for table in related_tables):
        return False
    if related_figures and any(not figure.get("is_stub") for figure in related_figures):
        return False
    if target.source_categories:
        evidence_classes = set(_string_list(evidence.get("evidence_classes", [])))
        if evidence_classes and evidence_classes.issubset({"failed_or_missing", "stub_or_manual"}):
            return True
        source_states = {str(status.get("status", "")) for status in source_gap_status}
        if source_states and source_states.issubset(VERIFICATION_SOURCE_STATES | REVIEW_SOURCE_STATES):
            return True
    return False


def _stub_section_content(
    target: SectionTarget,
    source_gap_status: list[dict[str, Any]],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    validation_issues: list[dict[str, Any]],
) -> str:
    lines = [_title_line(target)]
    lines.append(
        "This section is an explicit source/data gap because required source data, table output, or figure output is not available for source-backed report text."
    )
    if source_gap_status:
        lines.append("Unavailable or deferred source status: " + _source_gap_summary(source_gap_status) + ".")
    if related_tables:
        lines.append("Related table limitation: " + _artifact_stub_summary(related_tables, "table_id") + ".")
    if related_figures:
        lines.append("Related figure limitation: " + _artifact_stub_summary(related_figures, "figure_id") + ".")
    reason = _issue_summary(validation_issues)
    if reason:
        lines.append("Blocking issue summary: " + reason + ".")
    lines.append(_stub_reviewer_action(target.source_categories, _source_refs_from_status(source_gap_status)))
    lines.append("This source-gap text does not rank alternatives or make determinations.")
    return "\n".join(line for line in lines if line)


def _stub_table_content(target: TableTarget, table: dict[str, Any]) -> str:
    source_refs = _string_list(table.get("source_refs", []))
    flags = _string_list(table.get("uncertainty_flags", []))
    lines = [str(table.get("title") or target.title)]
    lines.append("This required deliverable table is an explicit source/data stub because no bounded table rows could be generated from the currently registered sources.")
    if source_refs:
        lines.append("Expected source refs: " + ", ".join(source_refs) + ".")
    if flags:
        lines.append("Source/data flags: " + ", ".join(flags) + ".")
    lines.append(_stub_reviewer_action(target.source_categories, source_refs))
    lines.append("This table limitation does not rank alternatives or make determinations.")
    return "\n".join(lines)


def _generated_table_content(target: TableTarget, table: dict[str, Any]) -> str:
    row_count = int(table.get("row_count") or 0)
    rows_preview = _dict_list(table.get("rows", []))[:5]
    columns = _string_list(table.get("columns", []))
    lines = [str(table.get("title") or target.title)]
    lines.append(f"This table summarizes {row_count} bounded row(s) from the available screening artifacts.")
    if columns:
        lines.append("Columns: " + ", ".join(columns[:8]) + ".")
    source_refs = _string_list(table.get("source_refs", []))
    if source_refs:
        lines.append("Source refs: " + ", ".join(source_refs) + ".")
    comparison_unit_ids = _string_list(table.get("comparison_unit_ids", []))
    if comparison_unit_ids:
        lines.append("Comparison units represented: " + _limited_join(comparison_unit_ids, limit=6) + ".")
    if rows_preview:
        lines.append(
            f"Body preview is limited to {len(rows_preview)} row(s); full bounded table rows remain in deliverable/tables.json."
        )
    lines.append("Source attribution, row classifications, and caveats are recorded in the table artifact.")
    lines.append("This table summary does not rank alternatives or make determinations.")
    return "\n".join(lines)


def _stub_figure_content(target: FigureTarget, figure: dict[str, Any]) -> str:
    source_refs = _string_list(figure.get("source_refs", []))
    issues = _dict_list(figure.get("validation_issues", []))
    lines = [str(figure.get("title") or target.title)]
    lines.append("This required deliverable figure could not be generated because the source layer or rendering path is not available.")
    if source_refs:
        lines.append("Expected source refs: " + ", ".join(source_refs) + ".")
    reason = _issue_summary(issues)
    if reason:
        lines.append("Blocking issue summary: " + reason + ".")
    if source_refs:
        lines.append("Required source data should be provided or the missing figure should be carried as an explicit limitation.")
    elif target.source_categories:
        lines.append("Source data for " + ", ".join(target.source_categories) + " should be provided or the missing figure should be carried as an explicit limitation.")
    else:
        lines.append("Required figure support should be provided or the missing figure should be carried as an explicit limitation.")
    lines.append("This content does not rank alternatives or make determinations.")
    return "\n".join(lines)


def _generated_figure_content(target: FigureTarget, figure: dict[str, Any]) -> str:
    lines = [str(figure.get("title") or target.title)]
    caption = str(figure.get("caption") or "").strip()
    source_note = str(figure.get("source_note") or "").strip()
    method_note = str(figure.get("method_note") or "").strip()
    if caption:
        lines.append("Caption: " + caption)
    source_refs = _string_list(figure.get("source_refs", []))
    if source_refs:
        lines.append("Source refs: " + ", ".join(source_refs) + ".")
    if source_note:
        lines.append("Source note: " + source_note)
    if method_note:
        lines.append("Method note: " + method_note)
    issue_summary = _issue_summary(_dict_list(figure.get("validation_issues", [])))
    if issue_summary:
        lines.append("Validation issue summary: " + issue_summary + ".")
    lines.append("This content does not rank alternatives or make determinations.")
    return "\n".join(lines)


def _stub_attachment_content(target: AttachmentTarget, validation_issues: list[dict[str, Any]]) -> str:
    lines = [f"Attachment {target.attachment_letter} {target.title}"]
    lines.append("This required attachment is an explicit attachment stub because the supporting attachment material is not present in the current project workspace.")
    if target.target_id == "attachment-hazardous-materials-report":
        lines.append("The hazardous materials support report is not present in the current project workspace.")
    elif target.target_id == "attachment-agency-consultation-letters":
        lines.append("Agency consultation letters are not present in the current project workspace.")
    else:
        lines.append("Required supporting attachment material is not present in the current project workspace.")
    reason = _issue_summary(validation_issues)
    if reason:
        lines.append("Blocking issue summary: " + reason + ".")
    lines.append("This attachment limitation does not rank alternatives or make determinations.")
    return "\n".join(lines)


def _generated_attachment_content(target: AttachmentTarget, related_figure_ids: list[str]) -> str:
    main_figures = [figure_id for figure_id in related_figure_ids if not figure_id.startswith("attachment-a-panel")]
    panel_figures = [figure_id for figure_id in related_figure_ids if figure_id.startswith("attachment-a-panel")]
    lines = [f"Attachment {target.attachment_letter} {target.title}"]
    lines.append("The map package references generated report figures and supporting panel maps.")
    if main_figures:
        lines.append(f"Main figure targets included: {_limited_join(main_figures, limit=15)}.")
    if panel_figures:
        lines.append(f"Supporting panel maps included: {len(panel_figures)} panel figure(s).")
    lines.append("Figure and panel completeness is tracked through the accepted figure items and attachment package.")
    lines.append("This attachment summary does not rank alternatives or make determinations.")
    return "\n".join(lines)


def _source_gap_summary(source_gap_status: list[dict[str, Any]]) -> str:
    parts = []
    for status in source_gap_status[:6]:
        category = str(status.get("category", "source"))
        state = str(status.get("status", "unknown"))
        source_refs = _string_list(status.get("source_ids", []))
        suffix = f" ({', '.join(source_refs)})" if source_refs else ""
        parts.append(f"{category}={state}{suffix}")
    return ", ".join(parts)


def _source_refs_from_status(source_gap_status: list[dict[str, Any]]) -> list[str]:
    return _dedupe([ref for status in source_gap_status for ref in _string_list(status.get("source_ids", []))])


def _artifact_stub_summary(records: list[dict[str, Any]], id_field: str) -> str:
    parts = []
    for record in records:
        artifact_id = str(record.get(id_field, "artifact"))
        if record.get("is_stub"):
            status = "stub"
        elif id_field == "table_id":
            status = f"generated ({int(record.get('row_count') or 0)} row(s))"
        elif id_field == "figure_id":
            status = "generated image" if record.get("image_path") else "generated"
        else:
            status = "generated"
        parts.append(f"{artifact_id}={status}")
    return ", ".join(parts)


def _issue_summary(issues: list[dict[str, Any]]) -> str:
    messages = []
    for issue in issues:
        message = str(issue.get("message", "")).strip()
        code = str(issue.get("code", "")).strip()
        if message:
            messages.append(message)
        elif code:
            messages.append(code)
    return "; ".join(_dedupe(messages)[:3])


def _stub_reviewer_action(source_categories: list[str], source_refs: list[str]) -> str:
    if source_refs:
        return "Listed source data are not available in the current workspace; carry this item as an explicit limitation unless the source data are supplied."
    if source_categories:
        return "Source data for " + ", ".join(source_categories) + " are not available in the current workspace; carry this item as an explicit limitation unless the source data are supplied."
    return "Required supporting material is not available in the current workspace; carry this item as an explicit limitation unless the material is supplied."


def _evidence_reference_summary(evidence: dict[str, Any]) -> str:
    parts = []
    constraint_count = len(_dict_list(evidence.get("constraint_summaries", [])))
    finding_count = len(_dict_list(evidence.get("findings", [])))
    row_summary_count = len(_dict_list(evidence.get("row_summaries", [])))
    figure_count = len(_dict_list(evidence.get("deliverable_figures", [])))
    if constraint_count:
        parts.append(f"{constraint_count} compact constraint summary record(s)")
    if finding_count:
        parts.append(f"{finding_count} finding/evidence record(s)")
    if row_summary_count:
        parts.append(f"{row_summary_count} table row summary record(s)")
    if figure_count:
        parts.append(f"{figure_count} figure availability record(s)")
    if not parts:
        return ""
    return "Evidence available: " + ", ".join(parts) + "."


def _attachment_wrapper_content(target: SectionTarget) -> str:
    refs = ", ".join(target.attachment_refs)
    if target.target_id == "attachment-a-project-maps":
        return (
            f"Attachment A map package target(s) {refs} are tracked as separate figure and supporting-panel deliverables. "
            "Accepted figures and supporting panels form the attachment map package."
        )
    if target.target_id == "attachment-b-hazardous-materials-report":
        return (
            f"Attachment B support target(s) {refs} identify hazardous materials support material expected from reviewer-supplied or manual sources. "
            "If the support report is unavailable, carry the absence as a limitation."
        )
    if target.target_id == "attachment-c-agency-consultation-letters":
        return (
            f"Attachment C support target(s) {refs} identify agency consultation materials expected from reviewer-supplied or manual sources. "
            "If consultation letters are unavailable, carry the absence as a limitation."
        )
    return f"This attachment wrapper references matrix attachment target(s): {refs}."


def _limited_join(values: list[str], *, limit: int = 5) -> str:
    clean = [value for value in _dedupe(values) if value]
    if len(clean) <= limit:
        return ", ".join(clean)
    return ", ".join(clean[:limit]) + f", and {len(clean) - limit} more"


def _source_backed_report_style(target: SectionTarget, evidence: dict[str, Any], related_tables: list[dict[str, Any]], related_figures: list[dict[str, Any]]) -> bool:
    if not target.source_categories:
        return False
    targeted = target.target_id in FIRST_PASS_REPORT_STYLE_SECTION_IDS or target.resource_category == "wetlands_waterbodies"
    if _dict_list(evidence.get("constraint_summaries", [])):
        return True
    if any(not table.get("is_stub") for table in related_tables):
        return True
    if any(not figure.get("is_stub") for figure in related_figures):
        return True
    if targeted and _string_list(evidence.get("source_refs", [])):
        return True
    source_states = {str(status.get("status", "")) for status in _dict_list(evidence.get("source_gap_status", []))}
    return targeted and bool(source_states.intersection(AVAILABLE_SOURCE_STATES))


def _section_lead_sentence(target: SectionTarget, comparison_unit: dict[str, Any] | None, extent_metadata: dict[str, Any] | None = None) -> str:
    unit_name = str((comparison_unit or {}).get("comparison_unit_name") or "").strip()
    scope_phrase = extent_wording_for_scope(extent_metadata or {})
    if target.resource_category == "wetlands_waterbodies":
        subject = "Mapped wetland and waterbody features"
    elif target.resource_category == "cultural_historic":
        subject = "Public cultural and historic resource context"
    elif target.resource_category == "community_socioeconomic":
        subject = "Mapped community resource and socioeconomic context"
    elif target.resource_category == "transportation_utilities":
        subject = "Mapped utility, transportation, and energy infrastructure context"
    elif target.resource_category == "regulated_facilities":
        subject = "Mapped regulated facility and contamination-risk context"
    else:
        subject = f"{target.title} evidence"
    verb = "are" if target.resource_category == "wetlands_waterbodies" else "is"
    if unit_name:
        return f"{subject} for {unit_name} {verb} summarized from the available source-backed screening evidence."
    return f"{subject} {verb} summarized from the available source-backed screening evidence {scope_phrase}."


def _source_display_name(source_ref: str) -> str:
    if source_ref in SOURCE_DISPLAY_NAMES:
        return SOURCE_DISPLAY_NAMES[source_ref]
    return source_ref.replace("_", " ").replace("-", " ").title()


def _source_reference_sentence(source_refs: list[str]) -> str:
    narrative_refs = [ref for ref in _dedupe(source_refs) if not _context_only_source_ref(ref)]
    if not narrative_refs:
        return ""
    return "Mapped-source evidence for this section comes from " + _limited_join([_source_display_name(ref) for ref in narrative_refs], limit=6) + "."


def _context_only_source_ref(source_ref: str) -> bool:
    lowered = source_ref.lower()
    return any(fragment in lowered for fragment in CONTEXT_ONLY_SOURCE_REF_FRAGMENTS)


def _artifact_label(record: dict[str, Any], id_field: str, kind: str) -> str:
    number_field = "table_number" if id_field == "table_id" else "figure_number"
    number = record.get(number_field)
    artifact_id = str(record.get(id_field, "")).strip()
    title = str(record.get("title", "")).strip()
    if number:
        label = f"{kind} {number}"
    elif artifact_id:
        label = f"{kind} {artifact_id}"
    else:
        label = kind
    if title and title != label:
        label += f" ({title})"
    return label


def _artifact_reference_sentence(related_tables: list[dict[str, Any]], related_figures: list[dict[str, Any]]) -> str:
    table_labels = [_artifact_label(table, "table_id", "Table") for table in related_tables if table.get("table_id")]
    figure_labels = [_artifact_label(figure, "figure_id", "Figure") for figure in related_figures if figure.get("figure_id")]
    generated_tables = [label for label, table in zip(table_labels, related_tables) if not table.get("is_stub")]
    generated_figures = [label for label, figure in zip(figure_labels, related_figures) if not figure.get("is_stub")]
    parts = []
    if generated_tables:
        parts.append("summarized in " + _limited_join(generated_tables, limit=3))
    if generated_figures:
        parts.append("shown on " + _limited_join(generated_figures, limit=3))
    if not parts:
        return ""
    return "Supporting evidence is " + " and ".join(parts) + "."


def _constraint_summary_sentence(evidence: dict[str, Any], comparison_unit: dict[str, Any] | None, extent_metadata: dict[str, Any] | None = None) -> str:
    constraints = _dict_list(evidence.get("constraint_summaries", []))
    if not constraints:
        return "The current evidence package does not include a compact mapped-overlap summary for this section."
    unit_name = str((comparison_unit or {}).get("comparison_unit_name") or "").strip()
    if not unit_name:
        names = [str(item.get("comparison_unit_name", "")).strip() for item in constraints if item.get("comparison_unit_name")]
        unit_phrase = " across the comparison units" if len(set(names)) > 1 else f" {extent_wording_for_scope(extent_metadata or {})}"
    else:
        unit_phrase = f" for {unit_name}"
    relationships = _relationship_counts(constraints)
    relationship_word = "relationship" if len(constraints) == 1 else "relationships"
    if relationships:
        return f"The evidence package includes {len(constraints)} compact source-backed mapped {relationship_word}{unit_phrase}: {relationships}."
    return f"The evidence package includes {len(constraints)} compact source-backed mapped {relationship_word}{unit_phrase}."


def _relationship_counts(constraints: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for constraint in constraints:
        relationship = str(constraint.get("relationship_type") or "mapped relationship").replace("_", " ")
        counts[relationship] = counts.get(relationship, 0) + 1
    parts = [f"{count} {label}" for label, count in sorted(counts.items())[:4]]
    return ", ".join(parts)


def _table_row_sentence(related_tables: list[dict[str, Any]]) -> str:
    generated = [table for table in related_tables if not table.get("is_stub")]
    if not generated:
        return ""
    parts = []
    for table in generated[:3]:
        label = _artifact_label(table, "table_id", "Table")
        row_count = int(table.get("row_count") or 0)
        parts.append(f"{label} contains {row_count} bounded row(s)")
    return "; ".join(parts) + "."


def _comparison_unit_sentence(evidence: dict[str, Any], comparison_unit: dict[str, Any] | None) -> str:
    if comparison_unit:
        unit_id = str(comparison_unit.get("comparison_unit_id", "")).strip()
        unit_name = str(comparison_unit.get("comparison_unit_name", "")).strip() or unit_id
        return f"This subsection addresses comparison unit {unit_name}."
    summaries = _dict_list(evidence.get("comparison_unit_summaries", []))
    unit_names = _dedupe([str(item.get("comparison_unit_name", "")).strip() for item in summaries if item.get("comparison_unit_name")])
    if unit_names:
        return "The summarized evidence is organized for " + _limited_join(unit_names, limit=6) + "."
    unit_ids = _dedupe([*_string_list(evidence.get("comparison_unit_ids", [])), *[str(item.get("comparison_unit_id")) for item in summaries if item.get("comparison_unit_id")]])
    if not unit_ids:
        return ""
    unit_word = "comparison unit" if len(unit_ids) == 1 else "comparison units"
    return f"The summarized evidence is organized by {len(unit_ids)} {unit_word}."


def _source_limitation_sentence(
    target: SectionTarget,
    evidence: dict[str, Any],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    extent_metadata: dict[str, Any] | None = None,
) -> str:
    limitations: list[str] = []
    if target.resource_category == "wetlands_waterbodies":
        limitations.append(
            "NWI and hydrography data are suitable for early screening but do not define jurisdictional wetland boundaries; site-specific delineation and agency coordination may be needed before design or permitting decisions."
        )
    elif target.resource_category == "cultural_historic":
        limitations.append(
            "Public cultural resource data are screening context only; sensitive records, eligibility, effects, and consultation requirements require qualified review and appropriate agency coordination."
        )
    elif target.resource_category == "community_socioeconomic":
        limitations.append(
            "Community-resource datasets may omit recent facility changes and should be checked against local knowledge before use in outreach or design decisions."
        )
    elif target.resource_category == "transportation_utilities":
        limitations.append(
            "Utility and infrastructure datasets are screening context only and do not replace owner coordination, field locating, or engineering verification."
        )
    elif target.resource_category == "regulated_facilities":
        limitations.append(
            "Regulated facility datasets are screening context only and do not establish contamination extent, liability, or cleanup obligations."
        )
    extent_limitation = _extent_limitation_sentence(extent_metadata or {})
    if extent_limitation:
        limitations.append(extent_limitation)
    limiting_status = _limiting_source_gap_status(_dict_list(evidence.get("source_gap_status", [])))
    if limiting_status:
        limitations.append("Unavailable or deferred source categories remain limitations: " + _source_gap_summary(limiting_status) + ".")
    artifact_issues = _issue_summary(
        [
            *[issue for table in related_tables for issue in _dict_list(table.get("validation_issues", []))],
            *[issue for figure in related_figures for issue in _dict_list(figure.get("validation_issues", []))],
        ]
    )
    if artifact_issues:
        limitations.append("Artifact limitations include: " + artifact_issues + ".")
    return " ".join(_dedupe(limitations))


def _extent_limitation_sentence(extent_metadata: dict[str, Any]) -> str:
    analysis_extent_type = str(extent_metadata.get("analysis_extent_type", ""))
    source_selection_reason = str(extent_metadata.get("source_selection_reason", "")).strip()
    if analysis_extent_type in {"nearby_context_extent", "community_context_extent"}:
        return "Context records should not be interpreted as direct project impacts unless a direct project-area relationship is separately documented."
    if analysis_extent_type == "watershed_context_extent":
        return "Watershed and impaired-water context is broader than direct project-feature intersection; current automated watershed context remains limited where source acquisition is deferred."
    if source_selection_reason and "until" in source_selection_reason:
        return source_selection_reason
    return ""


def _limiting_source_gap_status(source_gap_status: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [status for status in source_gap_status if str(status.get("status", "")) not in AVAILABLE_SOURCE_STATES]


def _general_section_content(
    target: SectionTarget,
    context: dict[str, Any],
    evidence: dict[str, Any],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    comparison_unit: dict[str, Any] | None,
    extent_metadata: dict[str, Any] | None = None,
) -> str:
    extent_metadata = extent_metadata or {}
    lines = [_title_line(target)]
    project_name = str(context.get("project_name") or "the project").strip()
    if comparison_unit:
        lines.append(_section_lead_sentence(target, comparison_unit, extent_metadata))
    elif target.resource_category in {"executive_summary", "constraints_inventory", "natural_ecological"}:
        lines.append(f"This section summarizes the available screening evidence for {project_name} and points to the resource sections, tables, figures, and limitations that support the report.")
    elif target.resource_category in {"introduction", "study_area"}:
        lines.append(f"This section describes {project_name}, the project area, and the submitted project features used for screening.")
    elif target.resource_category in {"methodology", "assumptions_caveats"}:
        lines.append("This section describes the desktop screening workflow, source status, assumptions, and limitations used to prepare the reviewable report materials.")
    elif target.resource_category == "conclusion":
        lines.append("This section summarizes screening themes and remaining review needs without ranking alternatives or making final determinations.")
    elif target.source_categories:
        lines.append(
            f"This section identifies {target.title.lower()} considerations {extent_wording_for_scope(extent_metadata)} based on currently available source status and limitations."
        )
    else:
        lines.append(_section_lead_sentence(target, comparison_unit, extent_metadata))
    for sentence in (
        _source_reference_sentence(_string_list(evidence.get("source_refs", []))),
        _artifact_reference_sentence(related_tables, related_figures),
        _constraint_summary_sentence(evidence, comparison_unit, extent_metadata) if _dict_list(evidence.get("constraint_summaries", [])) else "",
        _source_limitation_sentence(target, evidence, related_tables, related_figures, extent_metadata),
    ):
        if sentence:
            lines.append(sentence)
    return "\n".join(line for line in lines if line)


def _section_content(
    *,
    target: SectionTarget,
    context: dict[str, Any],
    evidence: dict[str, Any],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    comparison_unit: dict[str, Any] | None,
    extent_metadata: dict[str, Any] | None = None,
) -> str:
    extent_metadata = extent_metadata or {}
    if target.target_type == "front_matter":
        return "\n".join([_title_line(target), _front_matter_content(target, context, related_tables, related_figures)])
    if target.target_type == "attachment":
        if target.attachment_refs:
            return "\n".join([_title_line(target), _attachment_wrapper_content(target)])
        return "\n".join([_title_line(target), "This attachment section identifies supporting materials expected for the report package."])
    if not _source_backed_report_style(target, evidence, related_tables, related_figures):
        return _general_section_content(target, context, evidence, related_tables, related_figures, comparison_unit, extent_metadata)

    lines = [_title_line(target)]
    for sentence in (
        _section_lead_sentence(target, comparison_unit, extent_metadata),
        _source_reference_sentence(_dedupe([*_string_list(evidence.get("source_refs", [])), *[ref for table in related_tables for ref in _string_list(table.get("source_refs", []))], *[ref for figure in related_figures for ref in _string_list(figure.get("source_refs", []))]])),
        _artifact_reference_sentence(related_tables, related_figures),
        _table_row_sentence(related_tables),
        _comparison_unit_sentence(evidence, comparison_unit),
        _constraint_summary_sentence(evidence, comparison_unit, extent_metadata),
        _source_limitation_sentence(target, evidence, related_tables, related_figures, extent_metadata),
    ):
        if sentence:
            lines.append(sentence)
    return "\n".join(line for line in lines if line)


def _front_matter_content(target: SectionTarget, context: dict[str, Any], related_tables: list[dict[str, Any]], related_figures: list[dict[str, Any]]) -> str:
    if target.target_id == "cover-title":
        return f"{context.get('project_name', 'Project')} Environmental Constraints Report."
    if target.target_id == "list-of-figures":
        return "The figure list reflects matrix-backed figure items in matrix order."
    if target.target_id == "list-of-tables":
        return "The table list reflects matrix-backed table items in matrix order."
    if target.target_id == "list-of-attachments":
        return "The attachment list reflects Attachment A, Attachment B, and Attachment C targets."
    return f"Front-matter content for {target.title}."


def _review_status(
    target: SectionTarget,
    is_stub: bool,
    source_gap_status: list[dict[str, Any]],
    validation_issues: list[dict[str, Any]],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
) -> str:
    if is_stub:
        if any(str(status.get("status", "")) in VERIFICATION_SOURCE_STATES for status in source_gap_status):
            return "needs_verification"
        return "needs_review"
    child_statuses = {str(item.get("review_status", "")) for item in [*related_tables, *related_figures]}
    source_states = {str(status.get("status", "")) for status in source_gap_status}
    issue_codes = {str(issue.get("code", "")) for issue in validation_issues}
    if child_statuses.intersection({"needs_verification"}) or source_states.intersection(VERIFICATION_SOURCE_STATES):
        return "needs_verification"
    if child_statuses.intersection({"needs_review"}) or source_states.intersection(REVIEW_SOURCE_STATES) or issue_codes:
        return "needs_review"
    if target.target_type == "attachment":
        return "needs_review"
    return "draft"


def _target_validation_issues(
    evidence: dict[str, Any],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    target: SectionTarget,
) -> list[dict[str, Any]]:
    issues = _dict_list(evidence.get("validation_issues", []))
    for table in related_tables:
        issues.extend(_dict_list(table.get("validation_issues", [])))
        if table.get("is_stub"):
            issues.append(_issue("warning", "deliverable_table_stub", f"Related deliverable table '{table.get('table_id')}' is a stub.", "deliverable/tables.json", target.target_id))
    for figure in related_figures:
        issues.extend(_dict_list(figure.get("validation_issues", [])))
        if figure.get("is_stub"):
            issues.append(_issue("warning", "deliverable_figure_stub", f"Related deliverable figure '{figure.get('figure_id')}' is a stub.", "deliverable/figures.json", target.target_id))
    return _dedupe_issues(issues)


def _table_lookup(tables: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(table.get("table_id")): table for table in _dict_list(tables.get("tables", [])) if table.get("table_id")}


def _figure_lookup(figures: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(figure.get("figure_id")): figure for figure in _dict_list(figures.get("figures", [])) if figure.get("figure_id")}


def _related_table_records(tables: dict[str, Any], table_refs: list[str]) -> list[dict[str, Any]]:
    lookup = _table_lookup(tables)
    return [lookup[table_ref] for table_ref in table_refs if table_ref in lookup]


def _related_figure_records(figures: dict[str, Any], figure_refs: list[str]) -> list[dict[str, Any]]:
    lookup = _figure_lookup(figures)
    return [lookup[figure_ref] for figure_ref in figure_refs if figure_ref in lookup]


def _missing_upstream_issue(record: dict[str, Any], target_id: str, output_path: Path, target_type: str) -> list[dict[str, Any]]:
    if record:
        return []
    return [_issue("warning", f"deliverable_{target_type}_missing", f"Required deliverable {target_type} '{target_id}' was not found in upstream artifact.", str(output_path), target_id)]


def _artifact_validation_issues(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for item in items:
        issues.extend(_dict_list(item.get("validation_issues", [])))
        if item.get("is_stub"):
            issues.append(
                _issue(
                    "warning",
                    "deliverable_item_created_as_stub",
                    f"Deliverable item '{item.get('deliverable_item_id')}' was created as an explicit stub.",
                    str(DELIVERABLE_ITEMS_PATH),
                    str(item.get("target_id", "")),
                )
            )
    return _dedupe_issues(issues)


def _expected_item_count(
    section_targets: list[SectionTarget],
    table_targets: list[TableTarget],
    figure_targets: list[FigureTarget],
    attachment_targets: list[AttachmentTarget],
    comparison_units: list[dict[str, Any]],
) -> int:
    static_sections = sum(1 for target in section_targets if target.target_type in STATIC_SECTION_TARGET_TYPES)
    dynamic_children = sum(len(comparison_units) for target in section_targets if target.dynamic_children)
    return static_sections + dynamic_children + len(table_targets) + len(figure_targets) + len(attachment_targets)


def _evidence_finding_ids(evidence: dict[str, Any]) -> list[str]:
    return _dedupe([str(item.get("finding_id")) for item in _dict_list(evidence.get("findings", [])) if item.get("finding_id")])


def _evidence_constraint_ids(evidence: dict[str, Any]) -> list[str]:
    return _dedupe([str(item.get("constraint_id")) for item in _dict_list(evidence.get("constraint_summaries", [])) if item.get("constraint_id")])


def _evidence_refs(evidence: dict[str, Any]) -> list[str]:
    section_id = str(evidence.get("section_id") or "").strip()
    if not section_id:
        return []
    return [f"section_evidence:{section_id}"]


def _section_extent_metadata(
    target: SectionTarget,
    evidence: dict[str, Any],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
) -> dict[str, Any]:
    fallback = target_extent_metadata(
        target_id=target.target_id,
        target_type=target.target_type,
        resource_category=target.resource_category,
        source_categories=target.source_categories,
    )
    return _prefer_target_scope_for_context_targets(
        merge_extent_metadata([evidence, *related_tables, *related_figures], fallback=fallback),
        fallback,
        force_target_scope=target.target_id in DIRECT_TARGET_IDS,
    )


def _record_extent_metadata(record: dict[str, Any], *, fallback: dict[str, Any]) -> dict[str, Any]:
    extent = {field: record[field] for field in EXTENT_FIELD_NAMES if field in record}
    if extent:
        return merge_extent_metadata([extent], fallback=fallback)
    provenance = record.get("provenance", {}) if isinstance(record, dict) else {}
    if isinstance(provenance, dict) and isinstance(provenance.get("extent_policy"), dict):
        return merge_extent_metadata([provenance["extent_policy"]], fallback=fallback)
    return fallback


def _item_extent_metadata(
    *,
    target_id: str,
    target_type: str,
    resource_category: str,
    provenance: dict[str, Any],
    assumptions: dict[str, Any],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    if isinstance(provenance.get("extent_policy"), dict):
        records.append(provenance["extent_policy"])
    if isinstance(assumptions.get("extent_policy"), dict):
        records.append(assumptions["extent_policy"])
    fallback = target_extent_metadata(target_id=target_id, target_type=target_type, resource_category=resource_category)
    return merge_extent_metadata(records, fallback=fallback)


def _prefer_target_scope_for_context_targets(metadata: dict[str, Any], fallback: dict[str, Any], *, force_target_scope: bool = False) -> dict[str, Any]:
    target_scope = str(fallback.get("analysis_extent_type", ""))
    if not force_target_scope and target_scope not in {WATERSHED_CONTEXT_EXTENT, COUNTY_OR_REGIONAL_CONTEXT_EXTENT, COMMUNITY_CONTEXT_EXTENT, NEARBY_CONTEXT_EXTENT}:
        return metadata
    result = dict(metadata)
    result["analysis_extent_type"] = target_scope
    if fallback.get("list_extent_type"):
        result["list_extent_type"] = fallback["list_extent_type"]
    result["interpretation_scope_label"] = fallback.get("interpretation_scope_label", result.get("interpretation_scope_label", ""))
    reason = str(fallback.get("source_selection_reason", "")).strip()
    existing = str(result.get("source_selection_reason", "")).strip()
    if reason and reason not in existing:
        result["source_selection_reason"] = (existing + " " + reason).strip()
    return result


def _evidence_comparison_unit_ids(
    evidence: dict[str, Any],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
) -> list[str]:
    values = [
        *[unit_id for item in _dict_list(evidence.get("comparison_unit_summaries", [])) for unit_id in _string_list(item.get("comparison_unit_ids", []))],
        *[unit_id for table in related_tables for unit_id in _string_list(table.get("comparison_unit_ids", []))],
        *[unit_id for figure in related_figures for unit_id in _string_list(figure.get("comparison_unit_ids", []))],
    ]
    return _dedupe(values)


def _matrix_target_summary(
    target: SectionTarget,
    *,
    template_target: SectionTarget | None = None,
    comparison_unit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "target_id": target.target_id,
        "target_type": target.target_type,
        "section_number": target.section_number,
        "title": target.title,
        "heading_level": target.heading_level,
        "section_order": target.section_order,
        "export_group": target.export_group,
        "resource_category": target.resource_category,
        "required": target.required,
        "prompt_key": target.prompt_key,
        "source_categories": list(target.source_categories),
        "table_refs": list(target.table_refs),
        "figure_refs": list(target.figure_refs),
        "attachment_refs": list(target.attachment_refs),
        "review_item_type": target.review_item_type,
        "stub_when_missing": target.stub_when_missing,
    }
    if template_target:
        summary["template_target_id"] = template_target.target_id
    if comparison_unit:
        summary["comparison_unit"] = {
            "comparison_unit_id": comparison_unit.get("comparison_unit_id"),
            "comparison_unit_name": comparison_unit.get("comparison_unit_name"),
        }
    return summary


def _prompt_summary(prompt: ReportPrompt | None) -> dict[str, Any]:
    if prompt is None:
        return {}
    return {
        "prompt_key": prompt.prompt_key,
        "target_ids": list(prompt.target_ids),
        "section_instruction": prompt.section_instruction,
        "allowed_inputs": list(prompt.allowed_inputs),
        "citation_policy": dict(prompt.citation_policy),
        "prohibited_claims": list(prompt.prohibited_claims),
        "output_style": dict(prompt.output_style),
    }


def _gpt_drafting_summary(
    items: list[dict[str, Any]],
    *,
    enabled: bool,
    model: str,
    workers: int,
) -> dict[str, Any]:
    section_items = [item for item in items if item.get("review_item_type") == "section_text"]
    gpt_items = [
        item
        for item in section_items
        if isinstance(item.get("provenance"), dict)
        and isinstance(item["provenance"].get("drafting"), dict)
        and item["provenance"]["drafting"].get("draft_provider") == "openai_responses"
    ]
    rejected = [
        item
        for item in gpt_items
        if isinstance(item.get("provenance"), dict)
        and isinstance(item["provenance"].get("drafting"), dict)
        and item["provenance"]["drafting"].get("gpt_output_accepted") is False
    ]
    return {
        "enabled": enabled,
        "model": model,
        "workers": workers,
        "section_item_count": len(section_items),
        "gpt_item_count": len(gpt_items),
        "accepted_gpt_item_count": len(gpt_items) - len(rejected),
        "rejected_gpt_item_count": len(rejected),
    }


def _normalized_review_status(value: Any) -> str:
    status = str(value or "draft")
    if status == "rejected":
        return "declined"
    return status if status in SUPPORTED_REVIEW_STATUSES else "needs_review"


def _title_line(target: SectionTarget) -> str:
    if target.section_number:
        return f"{target.section_number} {target.title}"
    return target.title


def _format_pattern(value: Any, substitutions: dict[str, str], fallback: str) -> str:
    text = str(value or fallback)
    for key, replacement in substitutions.items():
        text = text.replace("{" + key + "}", replacement)
    return text


def _row_string(row: Any, column: str, default: str) -> str:
    if column not in row.index:
        return default
    value = row[column]
    if value is None:
        return default
    text = str(value).strip()
    return default if not text or text.lower() == "nan" else text


def _first_string(values: list[str]) -> str:
    return values[0] if values else ""


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _issue(severity: str, code: str, message: str, location: str, target_id: str = "") -> dict[str, str]:
    issue = {"severity": severity, "code": code, "message": message, "location": location}
    if target_id:
        issue["target_id"] = target_id
    return issue


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[dict[str, Any]] = []
    for issue in issues:
        key = (
            str(issue.get("code", "")),
            str(issue.get("location", "")),
            str(issue.get("message", "")),
            str(issue.get("target_id", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
