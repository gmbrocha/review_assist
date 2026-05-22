"""Machine-readable report section policy contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .source_catalog import load_source_catalog, repo_root


REPORT_SECTION_POLICY_PATH = Path("config/report_section_policy.json")
REPORT_SECTION_POLICY_VERSION = "report-section-policy-v1"

EXTENT_POLICY_SCOPES = {
    "direct_project": "direct_intersection_extent",
    "screening_buffer": "screening_buffer_extent",
    "nearby_context": "nearby_context_extent",
    "community_context": "community_context_extent",
    "watershed_context": "watershed_context_extent",
    "county_or_regional_context": "county_or_regional_context_extent",
    "direct_check_with_context_figure": "direct_intersection_extent",
    "mixed_summary": "project_area_analysis_bounds",
    "manual_reviewer_supplied": "project_area_analysis_bounds",
    "not_spatial": "project_area_analysis_bounds",
}
INTERPRETATION_EXTENT_POLICIES = set(EXTENT_POLICY_SCOPES)
VISUAL_EXTENT_CLASSES = {
    "none",
    "small_direct",
    "medium_context",
    "large_watershed",
    "county_regional",
    "mixed",
}
COMPARISON_UNIT_EXPANSION_POLICIES = {
    "none",
    "table_only",
    "narrative_children",
    "conditional",
    "context_summary_list",
    "manual_only",
}
TABLE_OVERFLOW_DESTINATIONS = {"table_artifact"}
INCLUSION_STATUSES = {
    "default",
    "conditional",
    "manual",
    "deferred",
    "required_stub",
}
ACTIVATION_CONDITIONS = {
    "always",
    "source_backed_or_stub",
    "manual_reviewer_supplied",
    "reviewer_supplied_parent_study",
    "deferred_source",
    "dynamic_comparison_units",
}
REVIEW_REQUIREMENTS = {
    "standard_review",
    "manual_review",
    "source_gap_review",
}
SECTION_ROLES = {
    "evidence_section",
    "umbrella_section",
    "structural_heading",
    "front_matter",
    "manual_item",
}
DRAFTING_MODES = {
    "deterministic_only",
    "gpt_allowed",
    "gpt_allowed_source_backed_only",
    "manual_reviewer_supplied_only",
    "disabled_deferred",
}
GPT_READINESS_VALUES = {
    "gpt_ready_now",
    "gpt_ready_after_extent_metadata_verification",
    "deterministic_only_for_now",
    "manual_reviewer_supplied_only",
    "blocked_by_missing_source_acquisition",
    "blocked_by_policy_ambiguity",
}
GPT_ELIGIBLE_DRAFTING_MODES = {"gpt_allowed", "gpt_allowed_source_backed_only"}
GPT_READY_VALUES = {"gpt_ready_now", "gpt_ready_after_extent_metadata_verification"}
MANUAL_GPT_READINESS_VALUES = {
    "manual_reviewer_supplied_only",
    "blocked_by_missing_source_acquisition",
    "blocked_by_policy_ambiguity",
}
REQUIRED_CAVEAT_GUARDRAILS = {
    "acs_source_year_and_geography_required": "ACS/Census year, geography, and source limitations must stay visible.",
    "agency_coordination_may_be_needed": "Agency coordination may be needed; no agency outcome may be inferred.",
    "comparison_unit_specific": "The statement is specific to a comparison unit or alternative.",
    "consultation_required": "Consultation or reviewer coordination is required before conclusions.",
    "county_regional_context_not_direct_project_impact": "County/regional context cannot be stated as project-level impact.",
    "desktop_screening_only": "The output is desktop screening only.",
    "direct_check_and_context_figure_are_distinct": "Direct checks and nearby/context figures are distinct evidence scopes.",
    "do_not_imply_direct_project_impact": "Context evidence must not imply direct project impact.",
    "do_not_invent_formal_study_context": "Formal parent-study facts must be reviewer supplied.",
    "eligibility_requires_review": "Eligibility requires qualified/manual review.",
    "field_locating_required": "Field locating or verification is required before final use.",
    "hazmat_report_controls_final_detail": "Hazmat report detail controls final contamination/supporting material statements.",
    "human_review_required": "Human review is required before export use.",
    "ipac_or_agency_material_required": "IPaC or agency material is required before species effect language.",
    "local_knowledge_review_needed": "Local knowledge/reviewer review is needed.",
    "missing_sources_visible": "Missing source status must remain visible.",
    "nearby_context_not_direct_impact": "Nearby context cannot be stated as direct project impact.",
    "not_contamination_extent_or_liability": "No contamination extent, cleanup, or liability conclusion.",
    "not_final_floodplain_determination": "No final floodplain/floodway determination.",
    "not_jurisdictional_delineation": "No jurisdictional delineation or field boundary conclusion.",
    "not_species_clearance": "No protected-species clearance or effect determination.",
    "owner_coordination_required": "Owner coordination is required before utility/access conclusions.",
    "public_context_only": "Public/coarse context only; not authoritative restricted-source evidence.",
    "qualified_review_required": "Qualified reviewer review is required.",
    "render_extent_is_presentation_only": "Render/collar extent is presentation support only.",
    "restricted_archaeology_not_mapped": "Restricted archaeology locations are not mapped or exposed.",
    "restricted_records_not_mapped": "Restricted records are not mapped or exposed.",
    "restricted_sources_not_mapped": "Restricted sources are not mapped or exposed.",
    "reviewed_maps_only": "Only reviewed maps should be included as attachment/report support.",
    "reviewer_supplied_consultation_material_required": "Consultation material must be reviewer supplied and reviewed.",
    "reviewer_supplied_hazmat_report_required": "Hazmat report material must be reviewer supplied and reviewed.",
    "reviewer_supplied_parent_study_required": "Parent-study material must be reviewer supplied and reviewed.",
    "screening_context_only": "The statement is screening/context only.",
    "screening_level": "The statement is screening-level and not final.",
    "source_acquisition_deferred": "Source acquisition/query implementation is deferred.",
    "source_availability_limited": "Source availability is limited.",
    "source_county_context_not_analysis_extent": "County context is source context, not analysis extent.",
    "source_specific_limitations_apply": "Source-specific limitations apply.",
    "source_status_may_be_partial": "Source status may be partial.",
    "watershed_context_deferred": "Watershed context implementation is deferred.",
}
REQUIRED_CAVEAT_TEXT_PATTERNS = {
    "acs_source_year_and_geography_required": r"\b(acs|census|source year|geograph)",
    "agency_coordination_may_be_needed": r"\b(agency|coordination|consultation)\b",
    "comparison_unit_specific": r"\b(comparison unit|alternative)\b",
    "consultation_required": r"\b(consultation|coordination)\b",
    "county_regional_context_not_direct_project_impact": r"\b(county|regional|tract|census)\b",
    "desktop_screening_only": r"\b(screening|desktop)\b",
    "direct_check_and_context_figure_are_distinct": r"\b(direct check|context figure|nearby context)\b",
    "do_not_imply_direct_project_impact": r"\b(context|not direct|direct project impact)\b",
    "do_not_invent_formal_study_context": r"\b(parent study|formal study|reviewer[- ]supplied)\b",
    "eligibility_requires_review": r"\b(eligibility|eligible|review)\b",
    "field_locating_required": r"\b(field|locat)\b",
    "hazmat_report_controls_final_detail": r"\b(hazmat|hazardous materials report|attachment b)\b",
    "human_review_required": r"\b(human review|reviewer)\b",
    "ipac_or_agency_material_required": r"\b(ipac|agency|consultation)\b",
    "local_knowledge_review_needed": r"\b(local knowledge|review)\b",
    "missing_sources_visible": r"\b(missing|unavailable|source gap)\b",
    "nearby_context_not_direct_impact": r"\b(nearby|near the project|vicinity|context area|context)\b",
    "not_contamination_extent_or_liability": r"\b(contamination extent|liability|cleanup)\b",
    "not_final_floodplain_determination": r"\b(floodplain|floodway|final|determination)\b",
    "not_jurisdictional_delineation": r"\b(jurisdictional|delineation|delineated)\b",
    "not_species_clearance": r"\b(species|clearance|effect)\b",
    "owner_coordination_required": r"\b(owner|coordination)\b",
    "public_context_only": r"\b(public|coarse|screening context)\b",
    "qualified_review_required": r"\b(qualified|review)\b",
    "render_extent_is_presentation_only": r"\b(render|presentation|map|collar)\b",
    "restricted_archaeology_not_mapped": r"\b(restricted|archaeolog|not mapped|not exposed)\b",
    "restricted_records_not_mapped": r"\b(restricted|not mapped|not exposed)\b",
    "restricted_sources_not_mapped": r"\b(restricted|not mapped|not exposed)\b",
    "reviewed_maps_only": r"\b(reviewed map|reviewed maps|reviewed figure)\b",
    "reviewer_supplied_consultation_material_required": r"\b(consultation|reviewer[- ]supplied)\b",
    "reviewer_supplied_hazmat_report_required": r"\b(hazmat|hazardous materials report|reviewer[- ]supplied)\b",
    "reviewer_supplied_parent_study_required": r"\b(parent study|reviewer[- ]supplied)\b",
    "screening_context_only": r"\b(screening|context)\b",
    "screening_level": r"\bscreening\b",
    "source_acquisition_deferred": r"\b(source acquisition|deferred|unimplemented)\b",
    "source_availability_limited": r"\b(source availability|limited|unavailable)\b",
    "source_county_context_not_analysis_extent": r"\b(county|context|analysis extent)\b",
    "source_specific_limitations_apply": r"\b(source[- ]specific|limitation)\b",
    "source_status_may_be_partial": r"\b(source status|partial)\b",
    "watershed_context_deferred": r"\b(watershed|deferred)\b",
}
FIGURE_RENDERING_CLASS_BY_VISUAL_CLASS = {
    "small_direct": "small_direct",
    "medium_context": "medium_context",
    "large_watershed": "large_watershed",
    "county_regional": "medium_context",
}


class ReportSectionPolicyError(RuntimeError):
    """Raised when report section policy config is missing or invalid."""


@dataclass(frozen=True)
class ReportSectionPolicy:
    section_id: str
    title: str
    section_family: str
    source_category: str
    section_role: str
    inclusion_status: str
    activation_condition: str
    review_requirement: str
    extent_policy: str
    visual_extent_class: str
    comparison_unit_expansion_policy: str
    evidence_pattern: list[str]
    drafting_mode: str
    expected_output_shape: str
    required_caveats: list[str]
    prohibited_claims: list[str]
    allowed_source_refs: list[str]
    allowed_source_categories: list[str]
    allowed_table_refs: list[str]
    allowed_figure_refs: list[str]
    manual_or_reviewer_supplied: bool
    gpt_readiness: str
    exempt_from_spatial_interpretation: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportSectionPolicy":
        section_id = _required_string(data, "section_id", "section policy")
        policy = cls(
            section_id=section_id,
            title=_required_string(data, "title", section_id),
            section_family=_required_string(data, "section_family", section_id),
            source_category=_required_string(data, "source_category", section_id),
            section_role=str(data.get("section_role") or "evidence_section"),
            inclusion_status=_required_string(data, "inclusion_status", section_id),
            activation_condition=_required_string(data, "activation_condition", section_id),
            review_requirement=_required_string(data, "review_requirement", section_id),
            extent_policy=_required_string(data, "extent_policy", section_id),
            visual_extent_class=_required_string(data, "visual_extent_class", section_id),
            comparison_unit_expansion_policy=_required_string(data, "comparison_unit_expansion_policy", section_id),
            evidence_pattern=_string_list(data.get("evidence_pattern"), "evidence_pattern", section_id),
            drafting_mode=_required_string(data, "drafting_mode", section_id),
            expected_output_shape=_required_string(data, "expected_output_shape", section_id),
            required_caveats=_string_list(data.get("required_caveats"), "required_caveats", section_id),
            prohibited_claims=_string_list(data.get("prohibited_claims"), "prohibited_claims", section_id),
            allowed_source_refs=_string_list(data.get("allowed_source_refs"), "allowed_source_refs", section_id),
            allowed_source_categories=_string_list(data.get("allowed_source_categories"), "allowed_source_categories", section_id),
            allowed_table_refs=_string_list(data.get("allowed_table_refs"), "allowed_table_refs", section_id),
            allowed_figure_refs=_string_list(data.get("allowed_figure_refs"), "allowed_figure_refs", section_id),
            manual_or_reviewer_supplied=_required_bool(data, "manual_or_reviewer_supplied", section_id),
            gpt_readiness=_required_string(data, "gpt_readiness", section_id),
            exempt_from_spatial_interpretation=bool(data.get("exempt_from_spatial_interpretation", False)),
        )
        _validate_section_policy(policy)
        return policy


@dataclass(frozen=True)
class FigurePolicy:
    figure_id: str
    title: str
    extent_policy: str
    visual_extent_class: str
    rendering_extent_class: str
    render_extent_is_presentation_only: bool
    allowed_source_categories: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FigurePolicy":
        figure_id = _required_string(data, "figure_id", "figure policy")
        policy = cls(
            figure_id=figure_id,
            title=_required_string(data, "title", figure_id),
            extent_policy=_required_string(data, "extent_policy", figure_id),
            visual_extent_class=_required_string(data, "visual_extent_class", figure_id),
            rendering_extent_class=_required_string(data, "rendering_extent_class", figure_id),
            render_extent_is_presentation_only=_required_bool(data, "render_extent_is_presentation_only", figure_id),
            allowed_source_categories=_string_list(data.get("allowed_source_categories"), "allowed_source_categories", figure_id),
        )
        _validate_figure_policy(policy)
        return policy


@dataclass(frozen=True)
class TablePolicy:
    table_id: str
    title: str
    extent_policy: str
    allowed_source_categories: list[str]
    max_body_preview_rows: int
    overflow_destination: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TablePolicy":
        table_id = _required_string(data, "table_id", "table policy")
        policy = cls(
            table_id=table_id,
            title=_required_string(data, "title", table_id),
            extent_policy=_required_string(data, "extent_policy", table_id),
            allowed_source_categories=_string_list(data.get("allowed_source_categories"), "allowed_source_categories", table_id),
            max_body_preview_rows=_positive_int(data.get("max_body_preview_rows"), "max_body_preview_rows", table_id),
            overflow_destination=_required_string(data, "overflow_destination", table_id),
        )
        _validate_table_policy(policy)
        return policy


@dataclass(frozen=True)
class ReportSectionPolicyConfig:
    policy_version: str
    profile_id: str
    description: str
    section_policies: list[ReportSectionPolicy]
    table_policies: list[TablePolicy]
    figure_policies: list[FigurePolicy]
    explicit_exemptions: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportSectionPolicyConfig":
        policy_version = _required_string(data, "policy_version", "report section policy")
        if policy_version != REPORT_SECTION_POLICY_VERSION:
            raise ReportSectionPolicyError(
                f"Report section policy version must be {REPORT_SECTION_POLICY_VERSION}."
            )
        raw_sections = _object_list(data.get("section_policies"), "section_policies", "report section policy")
        raw_tables = _object_list(data.get("table_policies"), "table_policies", "report section policy")
        raw_figures = _object_list(data.get("figure_policies"), "figure_policies", "report section policy")
        config = cls(
            policy_version=policy_version,
            profile_id=_required_string(data, "profile_id", "report section policy"),
            description=str(data.get("description", "")),
            section_policies=[ReportSectionPolicy.from_dict(item) for item in raw_sections],
            table_policies=[TablePolicy.from_dict(item) for item in raw_tables],
            figure_policies=[FigurePolicy.from_dict(item) for item in raw_figures],
            explicit_exemptions=_string_list(data.get("explicit_exemptions", []), "explicit_exemptions", "report section policy"),
        )
        config._validate()
        return config

    def by_section_id(self) -> dict[str, ReportSectionPolicy]:
        return {policy.section_id: policy for policy in self.section_policies}

    def by_table_id(self) -> dict[str, TablePolicy]:
        return {policy.table_id: policy for policy in self.table_policies}

    def by_figure_id(self) -> dict[str, FigurePolicy]:
        return {policy.figure_id: policy for policy in self.figure_policies}

    def _validate(self) -> None:
        _ensure_unique([policy.section_id for policy in self.section_policies], "section policy")
        _ensure_unique([policy.table_id for policy in self.table_policies], "table policy")
        _ensure_unique([policy.figure_id for policy in self.figure_policies], "figure policy")

    def validate_against_matrix(self, matrix: Any) -> None:
        section_ids = {target.target_id for target in matrix.section_targets}
        table_ids = {target.target_id for target in matrix.table_targets}
        figure_ids = {target.target_id for target in matrix.figure_targets}
        policy_section_ids = set(self.by_section_id())
        policy_table_ids = set(self.by_table_id())
        policy_figure_ids = set(self.by_figure_id())
        exemptions = set(self.explicit_exemptions)
        known_source_ids, known_source_categories = _source_catalog_ids_and_categories()

        missing_sections = sorted(section_ids - policy_section_ids - exemptions)
        if missing_sections:
            raise ReportSectionPolicyError(
                "Report section policy is missing matrix section target(s): "
                + ", ".join(missing_sections)
            )
        unknown_sections = sorted(policy_section_ids - section_ids)
        if unknown_sections:
            raise ReportSectionPolicyError(
                "Report section policy contains unknown section target(s): "
                + ", ".join(unknown_sections)
            )
        missing_tables = sorted(table_ids - policy_table_ids)
        if missing_tables:
            raise ReportSectionPolicyError(
                "Report section policy is missing table policy target(s): "
                + ", ".join(missing_tables)
            )
        unknown_tables = sorted(policy_table_ids - table_ids)
        if unknown_tables:
            raise ReportSectionPolicyError(
                "Report section policy contains unknown table policy target(s): "
                + ", ".join(unknown_tables)
            )
        missing_figures = sorted(figure_ids - policy_figure_ids)
        if missing_figures:
            raise ReportSectionPolicyError(
                "Report section policy is missing figure policy target(s): "
                + ", ".join(missing_figures)
            )
        unknown_figures = sorted(policy_figure_ids - figure_ids)
        if unknown_figures:
            raise ReportSectionPolicyError(
                "Report section policy contains unknown figure target(s): "
                + ", ".join(unknown_figures)
            )

        policies = self.by_section_id()
        for target in matrix.section_targets:
            if target.target_id in exemptions:
                continue
            policy = policies[target.target_id]
            missing_source_categories = sorted(set(target.source_categories) - set(policy.allowed_source_categories))
            if missing_source_categories and not policy.manual_or_reviewer_supplied:
                raise ReportSectionPolicyError(
                    f"Section policy '{target.target_id}' does not allow source category/categories: "
                    + ", ".join(missing_source_categories)
                )
            missing_table_refs = sorted(set(target.table_refs) - set(policy.allowed_table_refs))
            if missing_table_refs:
                raise ReportSectionPolicyError(
                    f"Section policy '{target.target_id}' does not allow table ref(s): "
                    + ", ".join(missing_table_refs)
                )
            missing_figure_refs = sorted(set(target.figure_refs) - set(policy.allowed_figure_refs))
            if missing_figure_refs:
                raise ReportSectionPolicyError(
                    f"Section policy '{target.target_id}' does not allow figure ref(s): "
                    + ", ".join(missing_figure_refs)
                )
            unknown_table_refs = sorted(set(policy.allowed_table_refs) - table_ids)
            if unknown_table_refs:
                raise ReportSectionPolicyError(
                    f"Section policy '{target.target_id}' references unknown table ref(s): "
                    + ", ".join(unknown_table_refs)
                )
            unknown_figure_refs = sorted(set(policy.allowed_figure_refs) - figure_ids)
            if unknown_figure_refs:
                raise ReportSectionPolicyError(
                    f"Section policy '{target.target_id}' references unknown figure ref(s): "
                    + ", ".join(unknown_figure_refs)
                )
            unknown_source_refs = sorted(set(policy.allowed_source_refs) - known_source_ids)
            if unknown_source_refs:
                raise ReportSectionPolicyError(
                    f"Section policy '{target.target_id}' references unknown source ref(s): "
                    + ", ".join(unknown_source_refs)
                )
            unknown_source_categories = sorted(set(policy.allowed_source_categories) - known_source_categories)
            if unknown_source_categories:
                raise ReportSectionPolicyError(
                    f"Section policy '{target.target_id}' references unknown source category/categories: "
                    + ", ".join(unknown_source_categories)
                )

        table_policies = self.by_table_id()
        for target in matrix.table_targets:
            table_policy = table_policies[target.target_id]
            missing_source_categories = sorted(set(target.source_categories) - set(table_policy.allowed_source_categories))
            if missing_source_categories:
                raise ReportSectionPolicyError(
                    f"Table policy '{target.target_id}' does not allow source category/categories: "
                    + ", ".join(missing_source_categories)
                )
            unknown_source_categories = sorted(set(table_policy.allowed_source_categories) - known_source_categories)
            if unknown_source_categories:
                raise ReportSectionPolicyError(
                    f"Table policy '{table_policy.table_id}' references unknown source category/categories: "
                    + ", ".join(unknown_source_categories)
                )

        figure_policies = self.by_figure_id()
        for target in matrix.figure_targets:
            figure_policy = figure_policies[target.target_id]
            missing_source_categories = sorted(set(target.source_categories) - set(figure_policy.allowed_source_categories))
            if missing_source_categories:
                raise ReportSectionPolicyError(
                    f"Figure policy '{target.target_id}' does not allow source category/categories: "
                    + ", ".join(missing_source_categories)
                )
            unknown_source_categories = sorted(set(figure_policy.allowed_source_categories) - known_source_categories)
            if unknown_source_categories:
                raise ReportSectionPolicyError(
                    f"Figure policy '{figure_policy.figure_id}' references unknown source category/categories: "
                    + ", ".join(unknown_source_categories)
                )


def load_report_section_policy(path: Path | None = None) -> ReportSectionPolicyConfig:
    config_file = path or repo_root() / REPORT_SECTION_POLICY_PATH
    data = _load_json_object(config_file)
    return ReportSectionPolicyConfig.from_dict(data)


@lru_cache(maxsize=1)
def default_report_section_policy() -> ReportSectionPolicyConfig:
    return load_report_section_policy()


def validate_report_section_policy(path: Path | None = None, matrix: Any | None = None) -> ReportSectionPolicyConfig:
    config = load_report_section_policy(path)
    if matrix is not None:
        config.validate_against_matrix(matrix)
    return config


def report_extent_scope_for_target(target_id: str) -> str:
    policy = _policy_record_for_target(target_id)
    if policy is None:
        return ""
    return EXTENT_POLICY_SCOPES.get(policy.extent_policy, "")


def visual_extent_class_for_figure(figure_id: str) -> str:
    policy = default_report_section_policy().by_figure_id().get(figure_id)
    return policy.visual_extent_class if policy else ""


def rendering_extent_class_for_figure(figure_id: str) -> str:
    policy = default_report_section_policy().by_figure_id().get(figure_id)
    return policy.rendering_extent_class if policy else ""


def _policy_record_for_target(target_id: str) -> ReportSectionPolicy | TablePolicy | FigurePolicy | None:
    config = default_report_section_policy()
    section = config.by_section_id().get(target_id)
    if section is not None:
        return section
    table = config.by_table_id().get(target_id)
    if table is not None:
        return table
    return config.by_figure_id().get(target_id)


def _validate_section_policy(policy: ReportSectionPolicy) -> None:
    if policy.section_role not in SECTION_ROLES:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported section_role '{policy.section_role}'."
        )
    if policy.section_role == "structural_heading":
        if policy.drafting_mode != "deterministic_only":
            raise ReportSectionPolicyError(
                f"Structural heading section policy '{policy.section_id}' must use deterministic_only drafting."
            )
        if policy.gpt_readiness in GPT_READY_VALUES:
            raise ReportSectionPolicyError(
                f"Structural heading section policy '{policy.section_id}' cannot be GPT-ready."
            )
    if policy.inclusion_status not in INCLUSION_STATUSES:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported inclusion_status '{policy.inclusion_status}'."
        )
    if policy.activation_condition not in ACTIVATION_CONDITIONS:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported activation_condition '{policy.activation_condition}'."
        )
    if policy.review_requirement not in REVIEW_REQUIREMENTS:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported review_requirement '{policy.review_requirement}'."
        )
    if policy.extent_policy not in INTERPRETATION_EXTENT_POLICIES:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported extent_policy '{policy.extent_policy}'."
        )
    if policy.extent_policy == "presentation_only":
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' cannot use presentation-only extent as interpretation scope."
        )
    if policy.visual_extent_class not in VISUAL_EXTENT_CLASSES:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported visual_extent_class '{policy.visual_extent_class}'."
        )
    if policy.comparison_unit_expansion_policy not in COMPARISON_UNIT_EXPANSION_POLICIES:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported comparison_unit_expansion_policy '{policy.comparison_unit_expansion_policy}'."
        )
    if policy.drafting_mode not in DRAFTING_MODES:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported drafting_mode '{policy.drafting_mode}'."
        )
    unknown_caveats = sorted(set(policy.required_caveats) - set(REQUIRED_CAVEAT_GUARDRAILS))
    if unknown_caveats:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' references unknown required_caveats: "
            + ", ".join(unknown_caveats)
        )
    if policy.gpt_readiness not in GPT_READINESS_VALUES:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported gpt_readiness '{policy.gpt_readiness}'."
        )
    if policy.activation_condition in {"manual_reviewer_supplied", "reviewer_supplied_parent_study"}:
        if not policy.manual_or_reviewer_supplied:
            raise ReportSectionPolicyError(
                f"Manual/reviewer-supplied section policy '{policy.section_id}' must be marked manual_or_reviewer_supplied."
            )
        if policy.review_requirement != "manual_review":
            raise ReportSectionPolicyError(
                f"Manual/reviewer-supplied section policy '{policy.section_id}' must require manual_review."
            )
    if policy.activation_condition == "deferred_source" and policy.review_requirement != "source_gap_review":
        raise ReportSectionPolicyError(
            f"Deferred-source section policy '{policy.section_id}' must require source_gap_review."
        )
    if policy.manual_or_reviewer_supplied and policy.gpt_readiness not in MANUAL_GPT_READINESS_VALUES:
        raise ReportSectionPolicyError(
            f"Manual/reviewer-supplied section policy '{policy.section_id}' cannot be GPT-ready by default."
        )
    if policy.drafting_mode in GPT_ELIGIBLE_DRAFTING_MODES or policy.gpt_readiness in GPT_READY_VALUES:
        if not policy.required_caveats:
            raise ReportSectionPolicyError(f"GPT-eligible section policy '{policy.section_id}' requires caveats.")
        if not policy.prohibited_claims:
            raise ReportSectionPolicyError(f"GPT-eligible section policy '{policy.section_id}' requires prohibited claims.")
        if not (policy.allowed_source_categories or policy.allowed_source_refs or policy.allowed_table_refs or policy.allowed_figure_refs):
            raise ReportSectionPolicyError(f"GPT-eligible section policy '{policy.section_id}' requires bounded evidence refs.")


def _validate_figure_policy(policy: FigurePolicy) -> None:
    if policy.extent_policy not in INTERPRETATION_EXTENT_POLICIES:
        raise ReportSectionPolicyError(
            f"Figure policy '{policy.figure_id}' has unsupported extent_policy '{policy.extent_policy}'."
        )
    if policy.visual_extent_class not in VISUAL_EXTENT_CLASSES - {"none", "mixed"}:
        raise ReportSectionPolicyError(
            f"Figure policy '{policy.figure_id}' has unsupported visual_extent_class '{policy.visual_extent_class}'."
        )
    expected_render_class = FIGURE_RENDERING_CLASS_BY_VISUAL_CLASS.get(policy.visual_extent_class)
    if policy.rendering_extent_class != expected_render_class:
        raise ReportSectionPolicyError(
            f"Figure policy '{policy.figure_id}' rendering_extent_class must be '{expected_render_class}'."
        )
    if not policy.render_extent_is_presentation_only:
        raise ReportSectionPolicyError(
            f"Figure policy '{policy.figure_id}' must mark render extent as presentation-only."
        )


def _validate_table_policy(policy: TablePolicy) -> None:
    if policy.extent_policy not in INTERPRETATION_EXTENT_POLICIES:
        raise ReportSectionPolicyError(
            f"Table policy '{policy.table_id}' has unsupported extent_policy '{policy.extent_policy}'."
        )
    if policy.extent_policy == "presentation_only":
        raise ReportSectionPolicyError(
            f"Table policy '{policy.table_id}' cannot use presentation-only extent as interpretation scope."
        )
    if not policy.allowed_source_categories:
        raise ReportSectionPolicyError(f"Table policy '{policy.table_id}' requires allowed_source_categories.")
    if policy.overflow_destination not in TABLE_OVERFLOW_DESTINATIONS:
        raise ReportSectionPolicyError(
            f"Table policy '{policy.table_id}' has unsupported overflow_destination '{policy.overflow_destination}'."
        )


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ReportSectionPolicyError(f"Missing report section policy: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportSectionPolicyError(f"Invalid report section policy JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReportSectionPolicyError(f"Report section policy must be a JSON object: {path}")
    return data


def _required_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReportSectionPolicyError(f"{context} requires a non-empty '{key}'.")
    return value


def _required_bool(data: dict[str, Any], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ReportSectionPolicyError(f"{context} requires boolean '{key}'.")
    return value


def _positive_int(value: Any, key: str, context: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ReportSectionPolicyError(f"{context} requires positive integer '{key}'.")
    return value


def _string_list(value: Any, key: str, context: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ReportSectionPolicyError(f"{context} requires string list '{key}'.")
    return list(value)


def _object_list(value: Any, key: str, context: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ReportSectionPolicyError(f"{context} requires a non-empty list field named '{key}'.")
    if not all(isinstance(item, dict) for item in value):
        raise ReportSectionPolicyError(f"{context} field '{key}' must contain only objects.")
    return list(value)


def _ensure_unique(values: list[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise ReportSectionPolicyError(f"Duplicate {label} id(s): {', '.join(sorted(duplicates))}")


def _source_catalog_ids_and_categories() -> tuple[set[str], set[str]]:
    catalog = load_source_catalog()
    source_ids = set(catalog.sources)
    categories = {
        str(item.get("category", "")).strip()
        for item in catalog.categories
        if str(item.get("category", "")).strip()
    }
    categories.update(source.category for source in catalog.sources.values())
    return source_ids, categories
