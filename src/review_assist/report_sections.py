"""Deterministic draft report section generation."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .findings import FINDINGS_PATH, FindingGenerationError, generate_draft_findings, load_draft_findings
from .maps import MAP_MANIFEST_PATH, MapGenerationError, load_map_manifest
from .project_context import ProjectContextError, generate_project_context, load_project_context
from .env_config import GptConfigurationError, gpt_drafting_enabled, gpt_drafting_workers, resolve_gpt_model
from .evidence_package import EvidencePackageError, build_evidence_package, section_evidence_for
from .source_catalog import repo_root
from .source_inventory import SOURCE_INVENTORY_PATH, SourceInventoryError, generate_source_inventory, load_source_inventory
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set
from .section_drafting import (
    SectionDraftingError,
    SectionDraftRequest,
    default_section_draft_provider,
    openai_section_draft_provider,
)
from .tables import TABLES_PATH, TableGenerationError, generate_comparison_tables, load_comparison_tables


REPORT_SECTION_TEMPLATES_PATH = Path("config/report_section_templates.json")
REPORT_SECTIONS_PATH = Path("drafts/report_sections.json")
SUPPORTED_SECTION_REVIEW_STATUSES = {
    "draft",
    "needs_review",
    "accepted",
    "edited",
    "rejected",
    "needs_verification",
    "unable_to_verify",
}
REQUIRED_SECTION_FIELDS = {
    "section_id",
    "project_id",
    "type",
    "title",
    "section_order",
    "export_group",
    "resource_category",
    "generated_content",
    "visual_slots",
    "table_slots",
    "related_finding_ids",
    "related_table_ids",
    "related_figure_ids",
    "source_refs",
    "assumptions",
    "provenance",
    "uncertainty_flags",
    "review_status",
    "validation_issues",
}
DEFERRED_SOURCE_STATUSES = {"missing", "downloadable", "needs_review", "failed"}
VERIFICATION_SOURCE_STATUSES = {"gated", "stubbed"}
RESOURCE_SECTION_TYPES = {"resource_section"}


class ReportSectionTemplateError(RuntimeError):
    """Raised when report section template configuration is invalid."""


class ReportSectionGenerationError(RuntimeError):
    """Raised when deterministic report section generation cannot complete."""


@dataclass(frozen=True)
class ReportSectionTemplate:
    section_id: str
    section_type: str
    title: str
    section_order: int
    export_group: str
    resource_category: str
    purpose: str
    visual_slots: list[str]
    table_slots: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportSectionTemplate":
        section_id = _required_string(data, "section_id", "report section template")
        raw_order = data.get("section_order")
        if not _is_integer(raw_order):
            raise ReportSectionTemplateError(f"Report section template '{section_id}' requires integer 'section_order'.")
        return cls(
            section_id=section_id,
            section_type=_required_string(data, "type", section_id),
            title=_required_string(data, "title", section_id),
            section_order=raw_order,
            export_group=str(data.get("export_group") or _default_export_group(str(data.get("type", "")))),
            resource_category=_required_string(data, "resource_category", section_id),
            purpose=_required_string(data, "purpose", section_id),
            visual_slots=_optional_string_list(data.get("visual_slots", []), "visual_slots", section_id),
            table_slots=_optional_string_list(data.get("table_slots", []), "table_slots", section_id),
        )


@dataclass(frozen=True)
class ReportSectionTemplateConfig:
    template_version: str
    sections: list[ReportSectionTemplate]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportSectionTemplateConfig":
        raw_sections = data.get("sections", [])
        if not isinstance(raw_sections, list) or not raw_sections:
            raise ReportSectionTemplateError("Report section template config requires a non-empty list field named 'sections'.")

        sections: list[ReportSectionTemplate] = []
        seen_ids: set[str] = set()
        for item in raw_sections:
            if not isinstance(item, dict):
                raise ReportSectionTemplateError("Each report section template entry must be an object.")
            template = ReportSectionTemplate.from_dict(item)
            if template.section_id in seen_ids:
                raise ReportSectionTemplateError(f"Duplicate report section template id: {template.section_id}")
            seen_ids.add(template.section_id)
            sections.append(template)
        return cls(
            template_version=str(data.get("template_version", "")),
            sections=sorted(sections, key=lambda section: (section.section_order, section.section_id)),
        )


def load_report_section_template_config(path: Path | None = None) -> ReportSectionTemplateConfig:
    config_file = path or repo_root() / REPORT_SECTION_TEMPLATES_PATH
    if not config_file.exists():
        raise ReportSectionTemplateError(f"Missing report section template config: {config_file}")
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportSectionTemplateError(f"Invalid report section template JSON: {config_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReportSectionTemplateError(f"Report section template config must be a JSON object: {config_file}")
    return ReportSectionTemplateConfig.from_dict(data)


def generate_report_sections(
    project_dir: Path,
    *,
    gpt_drafting: bool | None = None,
    gpt_model: str | None = None,
) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        context = _load_or_generate_context(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
        source_inventory = _load_or_generate_source_inventory(project_dir)
        draft_findings = _load_or_generate_findings(project_dir)
        comparison_tables = _load_or_generate_tables(project_dir)
        map_manifest = _load_optional_map_manifest(project_dir)
        evidence_package = build_evidence_package(project_dir)
        templates = load_report_section_template_config()
        use_gpt_drafting = gpt_drafting_enabled() if gpt_drafting is None else gpt_drafting
        model = resolve_gpt_model(gpt_model) if use_gpt_drafting else ""
    except (
        ProjectContextError,
        SourceStatusError,
        SourceInventoryError,
        FindingGenerationError,
        TableGenerationError,
        MapGenerationError,
        EvidencePackageError,
        GptConfigurationError,
        ReportSectionTemplateError,
    ) as exc:
        raise ReportSectionGenerationError(str(exc)) from exc

    now = _utc_now()
    draft_provider = openai_section_draft_provider(model=model) if use_gpt_drafting else default_section_draft_provider()
    workers = gpt_drafting_workers() if use_gpt_drafting else 1
    sections = _section_records(
        templates.sections,
        context=context,
        source_status=source_status,
        source_inventory=source_inventory,
        draft_findings=draft_findings,
        comparison_tables=comparison_tables,
        map_manifest=map_manifest,
        evidence_package=evidence_package,
        draft_provider=draft_provider,
        workers=workers,
        parallel=use_gpt_drafting,
    )
    validation_issues = _artifact_validation_issues(sections)

    output_path = project_dir / REPORT_SECTIONS_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "project_id": context["project_id"],
        "project_name": context["project_name"],
        "project_dir": str(project_dir),
        "created_at": now,
        "template_version": templates.template_version,
        "upstream_artifacts": {
            "project_context_path": context.get("context_path"),
            "source_status_path": source_status.get("output_path"),
            "source_inventory_path": source_inventory.get("output_path"),
            "draft_findings_path": draft_findings.get("output_path"),
            "comparison_tables_path": comparison_tables.get("output_path"),
            "map_manifest_path": map_manifest.get("output_path") if map_manifest else None,
            "evidence_package_path": evidence_package.get("output_path"),
        },
        "gpt_drafting": _gpt_drafting_summary(sections, enabled=use_gpt_drafting, model=model, workers=workers),
        "section_count": len(sections),
        "sections": sections,
        "validation_issues": validation_issues,
        "output_path": str(output_path),
    }
    _validate_report_sections_artifact(result, str(output_path))
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_report_sections(project_dir: Path) -> dict[str, Any]:
    sections_path = project_dir.resolve() / REPORT_SECTIONS_PATH
    if not sections_path.exists():
        raise ReportSectionGenerationError(f"Missing report sections artifact: {sections_path}")
    try:
        data = json.loads(sections_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportSectionGenerationError(f"Invalid report sections JSON: {sections_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReportSectionGenerationError(f"Report sections artifact must be a JSON object: {sections_path}")
    _validate_report_sections_artifact(data, str(sections_path))
    return data


def _load_or_generate_context(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_context(project_dir)
    except ProjectContextError:
        return generate_project_context(project_dir)


def _load_or_generate_source_status(project_dir: Path) -> dict[str, Any]:
    source_status_path = project_dir / SOURCE_STATUS_PATH
    if source_status_path.exists():
        try:
            data = json.loads(source_status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SourceStatusError(f"Invalid source status JSON: {source_status_path}: {exc}") from exc
        if isinstance(data, dict):
            return data
        raise SourceStatusError(f"Source status artifact must be a JSON object: {source_status_path}")
    return resolve_source_status_set(project_dir)


def _load_or_generate_source_inventory(project_dir: Path) -> dict[str, Any]:
    inventory_path = project_dir / SOURCE_INVENTORY_PATH
    if inventory_path.exists():
        return load_source_inventory(project_dir)
    return generate_source_inventory(project_dir)


def _load_or_generate_findings(project_dir: Path) -> dict[str, Any]:
    findings_path = project_dir / FINDINGS_PATH
    if findings_path.exists():
        return load_draft_findings(project_dir)
    return generate_draft_findings(project_dir)


def _load_or_generate_tables(project_dir: Path) -> dict[str, Any]:
    tables_path = project_dir / TABLES_PATH
    if tables_path.exists():
        return load_comparison_tables(project_dir)
    return generate_comparison_tables(project_dir)


def _load_optional_map_manifest(project_dir: Path) -> dict[str, Any] | None:
    map_path = project_dir / MAP_MANIFEST_PATH
    if not map_path.exists():
        return None
    return load_map_manifest(project_dir)


def _section_records(
    templates: list[ReportSectionTemplate],
    *,
    context: dict[str, Any],
    source_status: dict[str, Any],
    source_inventory: dict[str, Any],
    draft_findings: dict[str, Any],
    comparison_tables: dict[str, Any],
    map_manifest: dict[str, Any] | None,
    evidence_package: dict[str, Any],
    draft_provider: Any,
    workers: int,
    parallel: bool,
) -> list[dict[str, Any]]:
    kwargs = {
        "context": context,
        "source_status": source_status,
        "source_inventory": source_inventory,
        "draft_findings": draft_findings,
        "comparison_tables": comparison_tables,
        "map_manifest": map_manifest,
        "evidence_package": evidence_package,
        "draft_provider": draft_provider,
    }
    if not parallel or workers <= 1:
        return [_section_record(template=template, **kwargs) for template in templates]

    ordered: list[dict[str, Any] | None] = [None] * len(templates)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_section_record, template=template, **kwargs): (index, template.section_id)
            for index, template in enumerate(templates)
        }
        for future in as_completed(futures):
            index, section_id = futures[future]
            try:
                ordered[index] = future.result()
            except ReportSectionGenerationError as exc:
                raise ReportSectionGenerationError(f"Report section '{section_id}' failed: {exc}") from exc
            except Exception as exc:
                raise ReportSectionGenerationError(f"Report section '{section_id}' failed: {exc}") from exc
    return [section for section in ordered if section is not None]


def _section_record(
    *,
    template: ReportSectionTemplate,
    context: dict[str, Any],
    source_status: dict[str, Any],
    source_inventory: dict[str, Any],
    draft_findings: dict[str, Any],
    comparison_tables: dict[str, Any],
    map_manifest: dict[str, Any] | None,
    evidence_package: dict[str, Any],
    draft_provider: Any,
) -> dict[str, Any]:
    category = template.resource_category
    related_findings = _findings_for_category(draft_findings, category)
    related_tables = _tables_for_category(comparison_tables, category, template.section_type)
    source_refs = _source_refs_for_category(source_status, source_inventory, related_findings, category)
    related_figures = _figures_for_section(map_manifest, source_refs, template.section_type)
    validation_issues = _validation_issues_for_section(
        template=template,
        context=context,
        source_status=source_status,
        source_inventory=source_inventory,
        map_manifest=map_manifest,
        source_refs=source_refs,
    )
    status_record = _status_for_category(source_status, category)
    uncertainty_flags = _uncertainty_flags_for_section(
        source_status=source_status,
        status_record=status_record,
        inventory_records=_inventory_for_category(source_inventory, category),
        findings=related_findings,
        tables=related_tables,
        figures=related_figures,
        validation_issues=validation_issues,
        map_manifest=map_manifest,
        template=template,
    )
    review_status = _section_review_status(
        template,
        source_status,
        status_record,
        validation_issues,
        uncertainty_flags,
        related_findings,
        map_manifest,
    )
    deterministic_content = _section_content(
        template=template,
        context=context,
        source_status=source_status,
        source_inventory=source_inventory,
        draft_findings=draft_findings,
        comparison_tables=comparison_tables,
        map_manifest=map_manifest,
        related_findings=related_findings,
        related_tables=related_tables,
        related_figures=related_figures,
        source_refs=source_refs,
        validation_issues=validation_issues,
    )
    evidence_bundle = section_evidence_for(evidence_package, template.section_id)
    try:
        draft_result = draft_provider.draft(
            SectionDraftRequest(
                section_id=template.section_id,
                section_type=template.section_type,
                title=template.title,
                purpose=template.purpose,
                resource_category=category,
                deterministic_content=deterministic_content,
                related_finding_ids=[str(finding.get("finding_id")) for finding in related_findings if finding.get("finding_id")],
                related_table_ids=[str(table.get("table_id")) for table in related_tables if table.get("table_id")],
                related_figure_ids=[str(figure.get("figure_id")) for figure in related_figures if figure.get("figure_id")],
                source_refs=source_refs,
                visual_slots=list(template.visual_slots),
                table_slots=list(template.table_slots),
                evidence_bundle=evidence_bundle,
                validation_issues=validation_issues,
                project_context=context,
            )
        )
    except (SectionDraftingError, GptConfigurationError) as exc:
        raise ReportSectionGenerationError(str(exc)) from exc
    section_validation_issues = validation_issues + draft_result.validation_issues
    provenance = {
        "artifact": "report_sections",
        "template_id": template.section_id,
        "template_type": template.section_type,
        "export_group": template.export_group,
        "draft_provider": draft_result.provenance.get("draft_provider", getattr(draft_provider, "provider_id", "unknown")),
        "drafting": draft_result.provenance,
        "evidence_package_path": evidence_package.get("output_path"),
        "upstream_artifacts": {
            "project_context_path": context.get("context_path"),
            "source_status_path": source_status.get("output_path"),
            "source_inventory_path": source_inventory.get("output_path"),
            "draft_findings_path": draft_findings.get("output_path"),
            "comparison_tables_path": comparison_tables.get("output_path"),
            "map_manifest_path": map_manifest.get("output_path") if map_manifest else None,
            "evidence_package_path": evidence_package.get("output_path"),
        },
    }
    if draft_result.provenance.get("model"):
        provenance["gpt_model"] = draft_result.provenance["model"]
    if draft_result.provenance.get("prompt_version"):
        provenance["prompt_version"] = draft_result.provenance["prompt_version"]
    if draft_result.provenance.get("response_schema_version"):
        provenance["response_schema_version"] = draft_result.provenance["response_schema_version"]
    if draft_result.provenance.get("input_digest"):
        provenance["input_digest"] = draft_result.provenance["input_digest"]
    if draft_result.provenance.get("output_digest"):
        provenance["output_digest"] = draft_result.provenance["output_digest"]
    if draft_result.provenance.get("generated_at"):
        provenance["generated_at"] = draft_result.provenance["generated_at"]
    if draft_result.provenance.get("gpt_output_accepted") is not None:
        provenance["gpt_output_accepted"] = draft_result.provenance["gpt_output_accepted"]
    content = draft_result.content
    uncertainty_with_draft = list(uncertainty_flags)
    if draft_result.provenance.get("draft_provider") == "openai_responses":
        uncertainty_with_draft = sorted(set(uncertainty_with_draft + ["gpt_drafted_pre_review"]))
    if any(issue.get("code") in {"gpt_output_rejected", "gpt_empty_output"} for issue in draft_result.validation_issues):
        uncertainty_with_draft = sorted(set(uncertainty_with_draft + ["gpt_draft_rejected"]))
    return {
        "section_id": template.section_id,
        "project_id": context["project_id"],
        "type": template.section_type,
        "title": template.title,
        "section_order": template.section_order,
        "export_group": template.export_group,
        "resource_category": category,
        "generated_content": content,
        "visual_slots": list(template.visual_slots),
        "table_slots": list(template.table_slots),
        "related_finding_ids": [str(finding.get("finding_id")) for finding in related_findings if finding.get("finding_id")],
        "related_table_ids": [str(table.get("table_id")) for table in related_tables if table.get("table_id")],
        "related_figure_ids": [str(figure.get("figure_id")) for figure in related_figures if figure.get("figure_id")],
        "source_refs": source_refs,
        "assumptions": {
            "purpose": template.purpose,
            "desktop_screening_only": True,
            "report_profile": context.get("report_profile", {}),
            "project_assumptions": context.get("assumptions", {}),
        },
        "provenance": provenance,
        "uncertainty_flags": uncertainty_with_draft,
        "review_status": review_status,
        "validation_issues": section_validation_issues,
    }


def _section_content(
    *,
    template: ReportSectionTemplate,
    context: dict[str, Any],
    source_status: dict[str, Any],
    source_inventory: dict[str, Any],
    draft_findings: dict[str, Any],
    comparison_tables: dict[str, Any],
    map_manifest: dict[str, Any] | None,
    related_findings: list[dict[str, Any]],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    source_refs: list[str],
    validation_issues: list[dict[str, Any]],
) -> str:
    if template.section_type == "front_matter":
        return _front_matter_content(template, context)
    if template.section_type == "executive_summary":
        return _executive_summary_content(context, source_status, draft_findings, comparison_tables, map_manifest)
    if template.section_type == "introduction":
        return _introduction_content(context, validation_issues)
    if template.section_type == "study_area":
        return _study_area_content(context, related_figures, validation_issues)
    if template.section_type == "project_overview":
        return _project_overview_content(context, validation_issues)
    if template.section_type == "methodology":
        return _methodology_content(context, source_status, source_inventory, draft_findings, comparison_tables, map_manifest)
    if template.section_type == "analysis_procedures":
        return _analysis_procedures_content(context, map_manifest)
    if template.section_type == "limitations":
        return _limitations_content(source_status, related_findings, related_tables, related_figures, validation_issues)
    if template.section_type == "constraints_inventory":
        return _constraints_inventory_content(draft_findings, comparison_tables, map_manifest)
    if template.section_type in RESOURCE_SECTION_TYPES:
        return _resource_content(template, source_status, related_findings, related_tables, related_figures, source_refs, validation_issues)
    if template.section_type == "comparison_summary":
        return _comparison_content(comparison_tables)
    if template.section_type == "maps_and_figures":
        return _maps_content(map_manifest)
    if template.section_type == "reviewer_follow_up":
        return _reviewer_follow_up_content(source_status, validation_issues)
    if template.section_type == "conclusion":
        return _conclusion_content(source_status, draft_findings, map_manifest)
    if template.section_type == "attachments":
        return _attachments_content(template, map_manifest)
    return _generic_content(template, related_findings, related_tables, related_figures, source_refs)


def _artifact_validation_issues(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for section in sections:
        for issue in _dict_list(section.get("validation_issues", [])):
            code = str(issue.get("code", ""))
            if not (code.startswith("gpt_") or code.startswith("unknown_") or code == "prohibited_gpt_language"):
                continue
            message = str(issue.get("message", ""))
            key = (str(section.get("section_id", "")), code, message)
            if key in seen:
                continue
            seen.add(key)
            normalized = dict(issue)
            normalized["section_id"] = section.get("section_id")
            issues.append(normalized)
    return issues


def _gpt_drafting_summary(sections: list[dict[str, Any]], *, enabled: bool, model: str, workers: int) -> dict[str, Any]:
    provider_counts = Counter(
        str(section.get("provenance", {}).get("draft_provider", "unknown"))
        for section in sections
        if isinstance(section.get("provenance"), dict)
    )
    accepted_count = 0
    rejected_count = 0
    for section in sections:
        provenance = section.get("provenance", {}) if isinstance(section.get("provenance"), dict) else {}
        if provenance.get("draft_provider") != "openai_responses":
            continue
        if provenance.get("gpt_output_accepted") is False:
            rejected_count += 1
        else:
            accepted_count += 1
    return {
        "enabled": enabled,
        "model": model,
        "workers": workers if enabled else 0,
        "provider_counts": dict(provider_counts),
        "gpt_section_count": int(provider_counts.get("openai_responses", 0)),
        "accepted_gpt_section_count": accepted_count,
        "rejected_gpt_section_count": rejected_count,
    }


def _project_overview_content(context: dict[str, Any], validation_issues: list[dict[str, Any]]) -> str:
    alternatives = _dict_list(context.get("detected_alternatives", []))
    detected_inputs = _dict_list(context.get("detected_inputs", []))
    labels = [
        str(label)
        for alternative in alternatives
        for label in alternative.get("candidate_labels", [])
        if str(label).strip()
    ]
    extent = context.get("project_extent_wgs84")
    extent_text = "not available"
    if isinstance(extent, dict):
        extent_text = (
            f"west {extent.get('west')}, south {extent.get('south')}, "
            f"east {extent.get('east')}, north {extent.get('north')}"
        )
    lines = [
        f"{context.get('project_name')} is represented in this workspace as a pre-review desktop screening project.",
        f"The current report profile is {context.get('report_profile', {}).get('name', 'not specified')}.",
        f"The workspace includes {len(detected_inputs)} project input file(s) and {len(alternatives)} detected alternative input group(s).",
        f"The combined project extent in WGS84 is {extent_text}.",
    ]
    if labels:
        lines.append(f"Candidate alternative labels detected from the inputs include: {', '.join(sorted(set(labels)))}.")
    else:
        lines.append("Alternative or feature labels should be reviewed because the input labels may be incomplete or absent.")
    if validation_issues:
        lines.append(f"{len(validation_issues)} input validation issue(s) require reviewer attention before this overview is used.")
    lines.append("This section is draft/pre-review language and should not be treated as a final project description.")
    return "\n\n".join(lines)


def _front_matter_content(template: ReportSectionTemplate, context: dict[str, Any]) -> str:
    profile = context.get("report_profile", {}) if isinstance(context.get("report_profile"), dict) else {}
    lines = [
        f"# {context.get('project_name', 'Project')}",
        "",
        "Environmental Constraints Report",
        "",
        f"Project type: {context.get('project_type', 'not specified')}",
        f"Report profile: {profile.get('name', 'not specified')}",
        "Date: [Reviewer to confirm]",
        "Project/client identifiers: [Reviewer to add if applicable]",
        "",
        "This front matter is a draft placeholder for the editable export package.",
    ]
    if template.visual_slots:
        lines.append(f"Visual slots expected later in report: {', '.join(template.visual_slots)}.")
    if template.table_slots:
        lines.append(f"Table slots expected later in report: {', '.join(template.table_slots)}.")
    return "\n".join(lines)


def _executive_summary_content(
    context: dict[str, Any],
    source_status: dict[str, Any],
    draft_findings: dict[str, Any],
    comparison_tables: dict[str, Any],
    map_manifest: dict[str, Any] | None,
) -> str:
    required_gaps = [
        item
        for item in _dict_list(source_status.get("statuses", []))
        if item.get("requirement") == "required" and str(item.get("status")) in DEFERRED_SOURCE_STATUSES.union(VERIFICATION_SOURCE_STATUSES)
    ]
    return "\n\n".join(
        [
            f"This draft executive summary covers {context.get('project_name', 'the project')} as a desktop environmental constraints screening package.",
            (
                f"The current artifact set includes {draft_findings.get('finding_count', 0)} draft finding(s), "
                f"{comparison_tables.get('table_count', 0)} table artifact(s), and "
                f"{map_manifest.get('figure_count', 0) if map_manifest else 0} draft map figure(s)."
            ),
            (
                f"{len(required_gaps)} required source categor(ies) remain unavailable, gated, deferred, or needing review."
                if required_gaps
                else "No unresolved required source category was identified in the current source status set."
            ),
            "This summary must remain objective: it presents constraints and follow-up needs only, without choosing, ranking, or rejecting any project feature.",
        ]
    )


def _introduction_content(context: dict[str, Any], validation_issues: list[dict[str, Any]]) -> str:
    lines = [
        f"This report supports early constraints review for {context.get('project_name', 'the project')}.",
        "The report presents objective desktop-screening constraints only and does not choose, rank, reject, or recommend project features.",
        f"The workspace project type is {context.get('project_type', 'not specified')}.",
    ]
    instructions = str(context.get("special_reviewer_instructions", "")).strip()
    if instructions:
        lines.append(f"Special reviewer instructions: {instructions}")
    if validation_issues:
        lines.append(f"{len(validation_issues)} project input validation issue(s) should be resolved or acknowledged by the reviewer.")
    return "\n\n".join(lines)


def _study_area_content(
    context: dict[str, Any],
    related_figures: list[dict[str, Any]],
    validation_issues: list[dict[str, Any]],
) -> str:
    extent = context.get("project_extent_wgs84")
    extent_text = "not available"
    if isinstance(extent, dict):
        extent_text = (
            f"west {extent.get('west')}, south {extent.get('south')}, "
            f"east {extent.get('east')}, north {extent.get('north')}"
        )
    lines = [
        f"The study area is represented by the project input geometry with WGS84 extent: {extent_text}.",
        "The project overview map should be reviewed before this study area text is exported.",
    ]
    county_text = _county_context_text(context)
    if county_text:
        lines.insert(1, county_text)
    if related_figures:
        lines.append(f"Related figure references: {', '.join(str(figure.get('figure_id')) for figure in related_figures)}.")
    if validation_issues:
        lines.append(f"{len(validation_issues)} study-area-related validation issue(s) require reviewer attention.")
    return "\n\n".join(lines)


def _county_context_text(context: dict[str, Any]) -> str:
    administrative_areas = context.get("administrative_areas", {})
    if not isinstance(administrative_areas, dict):
        return ""
    counties = administrative_areas.get("counties", [])
    if not isinstance(counties, list):
        return ""
    names: list[str] = []
    for county in counties:
        if not isinstance(county, dict):
            continue
        name = str(county.get("name", "")).strip()
        if name and name not in names:
            names.append(name)
    if not names:
        return ""
    source_id = str(administrative_areas.get("source_id", "")).strip()
    source_text = f" from {source_id}" if source_id else ""
    return f"Materialized county-boundary context{source_text} places the analysis bounds in {_format_list(names)}."


def _format_list(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _methodology_content(
    context: dict[str, Any],
    source_status: dict[str, Any],
    source_inventory: dict[str, Any],
    draft_findings: dict[str, Any],
    comparison_tables: dict[str, Any],
    map_manifest: dict[str, Any] | None,
) -> str:
    assumptions = context.get("assumptions", {})
    buffer_feet = assumptions.get("default_buffer_feet") if isinstance(assumptions, dict) else None
    map_text = "Draft vector map figures were generated." if map_manifest else "Draft vector map figures have not been generated for this section set."
    return "\n\n".join(
        [
            "The workflow uses deterministic desktop screening artifacts to prepare reviewable draft report language.",
            (
                f"The selected report profile is {source_status.get('report_profile', {}).get('name', 'not specified')}. "
                f"Source status resolution produced {len(_dict_list(source_status.get('statuses', [])))} category status record(s), "
                f"and the source inventory produced {source_inventory.get('record_count', 0)} source record(s)."
            ),
            (
                f"Draft findings produced {draft_findings.get('finding_count', 0)} finding record(s), and comparison table generation "
                f"produced {comparison_tables.get('table_count', 0)} table artifact(s). {map_text}"
            ),
            (
                f"The current default review buffer assumption is {buffer_feet} feet."
                if buffer_feet is not None
                else "No default review buffer assumption was found in the project manifest."
            ),
            "All measurements, relationships, maps, and draft language are desktop screening only and require human review before export or final use.",
        ]
    )


def _analysis_procedures_content(
    context: dict[str, Any],
    map_manifest: dict[str, Any] | None,
) -> str:
    geometry_role = "not available"
    detected_inputs = _dict_list(context.get("detected_inputs", []))
    if detected_inputs:
        geometry_types: set[str] = set()
        for item in detected_inputs:
            counts = item.get("geometry_type_counts", {})
            if isinstance(counts, dict):
                geometry_types.update(str(key) for key in counts)
        if geometry_types:
            geometry_role = ", ".join(sorted(geometry_types))
    return "\n\n".join(
        [
            "Mapping and analysis procedures use normalized project geometry, project analysis bounds, registered or downloaded source layers, and deterministic spatial relationships.",
            f"Input geometry types detected for mapping context: {geometry_role}.",
            (
                f"{map_manifest.get('figure_count', 0)} draft figure artifact(s) are currently available for analysis review."
                if map_manifest
                else "No map manifest was available when this section was generated."
            ),
            "All procedures are desktop-screening methods and do not replace field delineation, agency consultation, engineering design, or professional judgment.",
        ]
    )


def _limitations_content(
    source_status: dict[str, Any],
    related_findings: list[dict[str, Any]],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    validation_issues: list[dict[str, Any]],
) -> str:
    deferred = [
        item
        for item in _dict_list(source_status.get("statuses", []))
        if str(item.get("status", "")) in DEFERRED_SOURCE_STATUSES.union(VERIFICATION_SOURCE_STATUSES)
    ]
    issue_count = len(validation_issues)
    lines = [
        "This draft package is based on available desktop data and should preserve uncertainty until reviewed by a qualified human reviewer.",
        f"{len(deferred)} source categor(ies) are missing, downloadable, gated, stubbed, or otherwise require review.",
    ]
    if deferred:
        lines.append("Source categories requiring attention:")
        lines.extend(
            f"- {item.get('category')}: {item.get('status')} ({item.get('notes', 'review required')})"
            for item in deferred
        )
    else:
        lines.append("No missing, gated, stubbed, downloadable, or needs-review source categories were identified in the current source status set.")
    if issue_count:
        lines.append(f"{issue_count} validation issue(s) should be checked before any report export.")
    if related_findings:
        lines.append(f"Related finding references: {', '.join(str(finding.get('finding_id')) for finding in related_findings if finding.get('finding_id'))}.")
    if related_tables:
        lines.append(f"Related table references: {', '.join(str(table.get('table_id')) for table in related_tables if table.get('table_id'))}.")
    if related_figures:
        lines.append(f"Related figure references: {', '.join(str(figure.get('figure_id')) for figure in related_figures if figure.get('figure_id'))}.")
    lines.append("Unavailable or restricted data should create caveat language rather than unsupported conclusions.")
    return "\n".join(lines)


def _constraints_inventory_content(
    draft_findings: dict[str, Any],
    comparison_tables: dict[str, Any],
    map_manifest: dict[str, Any] | None,
) -> str:
    categories = sorted(
        {
            str(finding.get("resource_category"))
            for finding in _dict_list(draft_findings.get("findings", []))
            if str(finding.get("resource_category", "")).strip()
        }
    )
    lines = [
        "The environmental constraints inventory summarizes source-backed and source-gap findings by resource category.",
        f"Draft finding categories represented: {', '.join(categories) if categories else 'none'}."
    ]
    table_ids = [str(table.get("table_id")) for table in _dict_list(comparison_tables.get("tables", [])) if table.get("table_id")]
    figure_ids = [str(figure.get("figure_id")) for figure in _dict_list(map_manifest.get("figures", []))] if map_manifest else []
    lines.append(f"Comparison table artifacts available: {comparison_tables.get('table_count', 0)}.")
    if table_ids:
        lines.append(f"Inventory table references: {', '.join(table_ids)}.")
    lines.append(f"Draft map figures available: {map_manifest.get('figure_count', 0) if map_manifest else 0}.")
    if figure_ids:
        lines.append(f"Inventory figure references: {', '.join(figure_ids)}.")
    lines.append("Inventory text should remain objective and should not identify a preferred project feature.")
    return "\n\n".join(lines)


def _resource_content(
    template: ReportSectionTemplate,
    source_status: dict[str, Any],
    related_findings: list[dict[str, Any]],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    source_refs: list[str],
    validation_issues: list[dict[str, Any]],
) -> str:
    status_record = _status_for_category(source_status, template.resource_category)
    lines = [
        f"This draft section addresses {template.title.lower()} for desktop screening and reviewer follow-up.",
        _source_status_sentence(template.resource_category, status_record),
    ]
    if related_findings:
        lines.append("Draft finding inputs:")
        for finding in related_findings[:6]:
            summary = str(finding.get("summary", "")).strip()
            implication = str(finding.get("implication", "")).strip()
            lines.append(f"- {finding.get('title')}: {summary} Implication: {implication}")
        if len(related_findings) > 6:
            lines.append(f"- {len(related_findings) - 6} additional draft finding(s) are available in the finding register.")
    else:
        lines.append(
            "No source-backed draft finding was generated for this category in the current artifacts. "
            "This should be reviewed as a data gap or no-current-record condition, not as proof that no resource is present."
        )
    if related_tables:
        lines.append(f"Related table artifact(s): {', '.join(str(table.get('table_id')) for table in related_tables)}.")
    if related_figures:
        lines.append(f"Related draft figure(s): {', '.join(str(figure.get('figure_id')) for figure in related_figures)}.")
    if source_refs:
        lines.append(f"Source reference id(s): {', '.join(source_refs)}.")
    if validation_issues:
        lines.append(f"{len(validation_issues)} validation issue(s) require reviewer attention for this section.")
    lines.append("This language is draft/pre-review only; final determinations may require field verification, agency coordination, or reviewer edits.")
    return "\n".join(lines)


def _conclusion_content(
    source_status: dict[str, Any],
    draft_findings: dict[str, Any],
    map_manifest: dict[str, Any] | None,
) -> str:
    unresolved = [
        item
        for item in _dict_list(source_status.get("statuses", []))
        if item.get("requirement") == "required" and str(item.get("status")) in DEFERRED_SOURCE_STATUSES.union(VERIFICATION_SOURCE_STATUSES)
    ]
    lines = [
        "This draft conclusion summarizes objective constraints and follow-up needs only.",
        f"The current package includes {draft_findings.get('finding_count', 0)} draft finding(s) and {map_manifest.get('figure_count', 0) if map_manifest else 0} draft figure(s).",
    ]
    if unresolved:
        lines.append(f"{len(unresolved)} required source categor(ies) require additional review, source acquisition, or caveat language.")
    lines.append("Future planning, design, agency coordination, field verification, and human decision-making occur outside the automated tool.")
    return "\n\n".join(lines)


def _attachments_content(template: ReportSectionTemplate, map_manifest: dict[str, Any] | None) -> str:
    lines = [
        "Attachment placeholders for the editable export package:",
        "- Attachment A: Project Maps.",
        "- Attachment B: Hazardous Materials Report, when available or reviewer-provided.",
        "- Attachment C: Agency Consultation Letters or reviewer-provided coordination records.",
    ]
    if map_manifest:
        lines.append(f"Map figure artifacts currently available for Attachment A: {map_manifest.get('figure_count', 0)}.")
    if template.visual_slots:
        lines.append(f"Expected visual attachment slots: {', '.join(template.visual_slots)}.")
    if template.table_slots:
        lines.append(f"Expected table attachment slots: {', '.join(template.table_slots)}.")
    return "\n".join(lines)


def _comparison_content(comparison_tables: dict[str, Any]) -> str:
    tables = _dict_list(comparison_tables.get("tables", []))
    lines = [
        "Generated comparison tables describe review profiles and source-backed records without ranking alternatives or identifying a preferred option.",
        f"{len(tables)} comparison table artifact(s) are available for reviewer inspection.",
    ]
    for table in tables:
        lines.append(f"- {table.get('title')}: {table.get('row_count', 0)} row(s). {table.get('description', '')}")
    lines.append("Table contents should be checked for source completeness, assumptions, and wording before export.")
    return "\n".join(lines)


def _maps_content(map_manifest: dict[str, Any] | None) -> str:
    if map_manifest is None:
        return "\n".join(
            [
                "Draft map figures have not been generated or were not available when this section was created.",
                "The reviewer should generate and review map figures before relying on map references in exported report materials.",
                "This placeholder keeps the map section visible instead of leaving the draft package blank.",
            ]
        )
    figures = _dict_list(map_manifest.get("figures", []))
    lines = [
        "Generated map figures are draft/pre-review visual aids and should be checked before export.",
        f"{len(figures)} figure artifact(s) are available in the map manifest.",
    ]
    for figure in figures:
        lines.append(f"- {figure.get('title')}: {figure.get('image_path')} ({figure.get('type')}).")
    lines.append("Current map generation is vector-only and does not include imagery or basemap tiles.")
    return "\n".join(lines)


def _reviewer_follow_up_content(
    source_status: dict[str, Any],
    validation_issues: list[dict[str, Any]],
) -> str:
    status_items = [
        item
        for item in _dict_list(source_status.get("statuses", []))
        if str(item.get("status", "")) in DEFERRED_SOURCE_STATUSES.union(VERIFICATION_SOURCE_STATUSES)
    ]
    lines = ["Reviewer follow-up should focus on unresolved source status, validation issues, and draft language fitness for export."]
    if status_items:
        lines.append("Source status follow-up:")
        lines.extend(f"- {item.get('category')}: {item.get('status')}." for item in status_items)
    if validation_issues:
        lines.append("Validation follow-up:")
        for issue in validation_issues[:12]:
            lines.append(f"- {issue.get('code', 'validation_issue')}: {issue.get('message', 'Review required.')}")
    else:
        lines.append("No validation issues were present in the current workflow artifacts.")
    lines.append("Accepted export content should come only from review queue items that have been accepted or explicitly included with caveat language.")
    return "\n".join(lines)


def _generic_content(
    template: ReportSectionTemplate,
    related_findings: list[dict[str, Any]],
    related_tables: list[dict[str, Any]],
    related_figures: list[dict[str, Any]],
    source_refs: list[str],
) -> str:
    return "\n".join(
        [
            f"This draft section is reserved for {template.title}.",
            f"Related findings: {len(related_findings)}. Related tables: {len(related_tables)}. Related figures: {len(related_figures)}.",
            f"Source refs: {', '.join(source_refs) if source_refs else 'none'}.",
            "This content requires reviewer confirmation before export.",
        ]
    )


def _source_status_sentence(category: str, status_record: dict[str, Any] | None) -> str:
    if status_record is None:
        return f"No source status record was resolved for category '{category}'. Reviewer attention is required."
    return (
        f"Source status for '{category}' is {status_record.get('status')} "
        f"({status_record.get('requirement')}). {status_record.get('notes', '')}"
    ).strip()


def _findings_for_category(draft_findings: dict[str, Any], category: str) -> list[dict[str, Any]]:
    if category in {
        "comparison_summary",
        "maps",
        "methodology",
        "project_overview",
        "front_matter",
        "executive_summary",
        "introduction",
        "study_area",
        "constraints_inventory",
        "conclusion",
        "attachments",
        "review_notes",
    }:
        return []
    if category == "assumptions_caveats":
        return [
            finding
            for finding in _dict_list(draft_findings.get("findings", []))
            if str(finding.get("type", "")) == "source_unavailable_or_deferred"
        ]
    return [
        finding
        for finding in _dict_list(draft_findings.get("findings", []))
        if str(finding.get("resource_category", "")) == category
    ]


def _tables_for_category(comparison_tables: dict[str, Any], category: str, section_type: str) -> list[dict[str, Any]]:
    tables = _dict_list(comparison_tables.get("tables", []))
    if section_type == "comparison_summary":
        return tables
    if section_type == "constraints_inventory":
        inventory_table_ids = {
            "constraint-summary",
            "grouped-constraint-summary",
            "hydrography-crossing-summary",
            "flood-hazard-summary",
            "critical-habitat-summary",
            "regulated-facility-summary",
            "soil-mapunit-summary",
            "spatial-relationship-summary",
            "draft-finding-summary",
        }
        return [table for table in tables if str(table.get("table_id", "")) in inventory_table_ids]
    if section_type == "limitations":
        limitation_table_ids = {"source-status-matrix", "draft-finding-summary"}
        return [table for table in tables if str(table.get("table_id", "")) in limitation_table_ids]
    if section_type in {
        "front_matter",
        "executive_summary",
        "introduction",
        "study_area",
        "project_overview",
        "methodology",
        "analysis_procedures",
        "maps_and_figures",
        "conclusion",
        "attachments",
        "reviewer_follow_up",
    }:
        return []
    related: list[dict[str, Any]] = []
    for table in tables:
        for row in _dict_list(table.get("rows", [])):
            if category in {str(row.get("category", "")), str(row.get("resource_category", "")), str(row.get("source_category", ""))}:
                related.append(table)
                break
    return related


def _figures_for_section(map_manifest: dict[str, Any] | None, source_refs: list[str], section_type: str) -> list[dict[str, Any]]:
    if map_manifest is None:
        return []
    figures = _dict_list(map_manifest.get("figures", []))
    if section_type in {"maps_and_figures", "study_area", "constraints_inventory", "attachments"}:
        return figures
    source_ref_set = set(source_refs)
    if not source_ref_set:
        return []
    return [
        figure
        for figure in figures
        if source_ref_set.intersection(_string_list(figure.get("source_refs", [])))
    ]


def _source_refs_for_category(
    source_status: dict[str, Any],
    source_inventory: dict[str, Any],
    findings: list[dict[str, Any]],
    category: str,
) -> list[str]:
    refs: set[str] = set()
    status_record = _status_for_category(source_status, category)
    if status_record:
        refs.update(_status_source_ids(status_record))
    for record in _inventory_for_category(source_inventory, category):
        source_id = str(record.get("source_id", ""))
        if source_id:
            refs.add(source_id)
    for finding in findings:
        refs.update(_string_list(finding.get("source_refs", [])))
        refs.update(_string_list(finding.get("source_ids", [])))
    return sorted(refs)


def _status_source_ids(status_record: dict[str, Any]) -> list[str]:
    return _string_list(status_record.get("source_ids", [])) or _string_list(status_record.get("registered_source_ids", []))


def _status_for_category(source_status: dict[str, Any], category: str) -> dict[str, Any] | None:
    for item in _dict_list(source_status.get("statuses", [])):
        if str(item.get("category", "")) == category:
            return item
    return None


def _inventory_for_category(source_inventory: dict[str, Any], category: str) -> list[dict[str, Any]]:
    return [
        record
        for record in _dict_list(source_inventory.get("records", []))
        if str(record.get("category", "")) == category
    ]


def _validation_issues_for_section(
    *,
    template: ReportSectionTemplate,
    context: dict[str, Any],
    source_status: dict[str, Any],
    source_inventory: dict[str, Any],
    map_manifest: dict[str, Any] | None,
    source_refs: list[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if template.section_type in {"front_matter", "executive_summary", "introduction", "study_area", "project_overview"}:
        issues.extend(_dict_list(context.get("validation_issues", [])))
    if template.section_type in {"limitations", "conclusion", "reviewer_follow_up"}:
        issues.extend(_dict_list(context.get("validation_issues", [])))
        issues.extend(_dict_list(source_status.get("validation_issues", [])))
        issues.extend(_dict_list(source_inventory.get("validation_issues", [])))
        if map_manifest:
            issues.extend(_dict_list(map_manifest.get("validation_issues", [])))
    else:
        refs = set(source_refs)
        for record in _inventory_for_category(source_inventory, template.resource_category):
            issues.extend(_dict_list(record.get("validation_issues", [])))
        for issue in _dict_list(source_status.get("validation_issues", [])):
            if str(issue.get("source_id", "")) in refs:
                issues.append(issue)
        if map_manifest:
            for issue in _dict_list(map_manifest.get("validation_issues", [])):
                if not refs or str(issue.get("source_id", "")) in refs:
                    if template.section_type == "maps_and_figures" or str(issue.get("source_id", "")) in refs:
                        issues.append(issue)
    if template.section_type in {"maps_and_figures", "attachments"} and map_manifest is None:
        issues.append(
            {
                "severity": "warning",
                "code": "missing_map_manifest",
                "message": "Map manifest was not available when draft report sections were generated.",
            }
        )
    return issues


def _uncertainty_flags_for_section(
    *,
    source_status: dict[str, Any],
    status_record: dict[str, Any] | None,
    inventory_records: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    figures: list[dict[str, Any]],
    validation_issues: list[dict[str, Any]],
    map_manifest: dict[str, Any] | None,
    template: ReportSectionTemplate,
) -> list[str]:
    flags: set[str] = {"desktop_screening_only", "draft_pre_review"}
    if status_record:
        flags.update(_string_list(status_record.get("uncertainty_flags", [])))
        source_state = str(status_record.get("status", ""))
        if source_state in DEFERRED_SOURCE_STATUSES.union(VERIFICATION_SOURCE_STATUSES):
            flags.add(source_state)
    if template.section_type in {"limitations", "conclusion", "reviewer_follow_up"}:
        for item in _dict_list(source_status.get("statuses", [])):
            source_state = str(item.get("status", ""))
            if source_state in DEFERRED_SOURCE_STATUSES.union(VERIFICATION_SOURCE_STATUSES):
                flags.add(source_state)
                flags.update(_string_list(item.get("uncertainty_flags", [])))
    for record in inventory_records:
        flags.update(_string_list(record.get("uncertainty_flags", [])))
    for finding in findings:
        flags.update(_string_list(finding.get("uncertainty_flags", [])))
    for table in tables:
        flags.update(_string_list(table.get("uncertainty_flags", [])))
    for figure in figures:
        flags.update(_string_list(figure.get("uncertainty_flags", [])))
    flags.update(str(issue.get("code")) for issue in validation_issues if issue.get("code"))
    if template.section_type in {"maps_and_figures", "attachments"} and map_manifest is None:
        flags.add("missing_map_manifest")
    return sorted(flag for flag in flags if flag)


def _section_review_status(
    template: ReportSectionTemplate,
    source_status: dict[str, Any],
    status_record: dict[str, Any] | None,
    validation_issues: list[dict[str, Any]],
    uncertainty_flags: list[str],
    related_findings: list[dict[str, Any]],
    map_manifest: dict[str, Any] | None,
) -> str:
    source_state = str(status_record.get("status", "")) if status_record else ""
    if template.section_type in {"limitations", "conclusion", "reviewer_follow_up"}:
        states = {str(item.get("status", "")) for item in _dict_list(source_status.get("statuses", []))}
        if states.intersection(VERIFICATION_SOURCE_STATUSES):
            return "needs_verification"
        if states.intersection(DEFERRED_SOURCE_STATUSES):
            return "needs_review"
    finding_statuses = {str(finding.get("review_status", "")) for finding in related_findings}
    if source_state in VERIFICATION_SOURCE_STATUSES or "restricted_source_required" in uncertainty_flags:
        return "needs_verification"
    if template.resource_category == "cultural_historic" and source_state in {"gated", "stubbed", "needs_review"}:
        return "needs_verification"
    if "needs_verification" in finding_statuses:
        return "needs_verification"
    if validation_issues or source_state in DEFERRED_SOURCE_STATUSES or "needs_review" in finding_statuses:
        return "needs_review"
    if template.section_type in {"maps_and_figures", "attachments"} and map_manifest is None:
        return "needs_review"
    return "draft"


def _validate_report_sections_artifact(data: dict[str, Any], location: str) -> None:
    sections = data.get("sections")
    if not isinstance(sections, list):
        raise ReportSectionGenerationError(f"Report sections artifact requires a list field named 'sections': {location}")
    section_count = data.get("section_count")
    if section_count is not None and section_count != len(sections):
        raise ReportSectionGenerationError(f"Report sections artifact section_count does not match sections: {location}")
    if not isinstance(data.get("validation_issues", []), list):
        raise ReportSectionGenerationError(f"Report sections artifact validation_issues must be a list: {location}")
    seen_ids: set[str] = set()
    for section in sections:
        if not isinstance(section, dict):
            raise ReportSectionGenerationError(f"Each report section must be an object: {location}")
        missing = sorted(REQUIRED_SECTION_FIELDS - set(section))
        if missing:
            raise ReportSectionGenerationError(f"Report section is missing required fields {missing}: {location}")
        section_id = section["section_id"]
        if not isinstance(section_id, str) or not section_id.strip():
            raise ReportSectionGenerationError(f"Report section requires a non-empty section_id: {location}")
        if section_id in seen_ids:
            raise ReportSectionGenerationError(f"Duplicate report section id '{section_id}': {location}")
        seen_ids.add(section_id)
        if not _is_integer(section["section_order"]):
            raise ReportSectionGenerationError(f"Report section '{section_id}' section_order must be an integer: {location}")
        if section["review_status"] not in SUPPORTED_SECTION_REVIEW_STATUSES:
            raise ReportSectionGenerationError(f"Report section '{section_id}' has unsupported review_status: {location}")
        for list_field in (
            "visual_slots",
            "table_slots",
            "related_finding_ids",
            "related_table_ids",
            "related_figure_ids",
            "source_refs",
            "uncertainty_flags",
            "validation_issues",
        ):
            if not isinstance(section[list_field], list):
                raise ReportSectionGenerationError(f"Report section '{section_id}' field '{list_field}' must be a list: {location}")
        for object_field in ("assumptions", "provenance"):
            if not isinstance(section[object_field], dict):
                raise ReportSectionGenerationError(f"Report section '{section_id}' field '{object_field}' must be an object: {location}")


def _required_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReportSectionTemplateError(f"{context} requires a non-empty '{key}'.")
    return value


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _optional_string_list(value: Any, field_name: str, context: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ReportSectionTemplateError(f"Report section template '{context}' field '{field_name}' must be a list of strings.")
    return list(value)


def _default_export_group(section_type: str) -> str:
    if section_type == "front_matter":
        return "front_matter"
    if section_type == "executive_summary":
        return "executive_summary"
    if section_type in {"introduction", "study_area", "project_overview"}:
        return "introduction"
    if section_type in {"methodology", "analysis_procedures", "limitations"}:
        return "methodology"
    if section_type in {"constraints_inventory", "comparison_summary", "maps_and_figures"}:
        return "constraints_inventory"
    if section_type == "resource_section":
        return "resource_sections"
    if section_type == "conclusion":
        return "conclusion"
    if section_type in {"attachments", "reviewer_follow_up"}:
        return "attachments"
    return "resource_sections"


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
