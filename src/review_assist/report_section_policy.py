"""Machine-readable report section policy contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .source_catalog import repo_root


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
class ReportSectionPolicyConfig:
    policy_version: str
    profile_id: str
    description: str
    section_policies: list[ReportSectionPolicy]
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
        raw_figures = _object_list(data.get("figure_policies"), "figure_policies", "report section policy")
        config = cls(
            policy_version=policy_version,
            profile_id=_required_string(data, "profile_id", "report section policy"),
            description=str(data.get("description", "")),
            section_policies=[ReportSectionPolicy.from_dict(item) for item in raw_sections],
            figure_policies=[FigurePolicy.from_dict(item) for item in raw_figures],
            explicit_exemptions=_string_list(data.get("explicit_exemptions", []), "explicit_exemptions", "report section policy"),
        )
        config._validate()
        return config

    def by_section_id(self) -> dict[str, ReportSectionPolicy]:
        return {policy.section_id: policy for policy in self.section_policies}

    def by_figure_id(self) -> dict[str, FigurePolicy]:
        return {policy.figure_id: policy for policy in self.figure_policies}

    def _validate(self) -> None:
        _ensure_unique([policy.section_id for policy in self.section_policies], "section policy")
        _ensure_unique([policy.figure_id for policy in self.figure_policies], "figure policy")

    def validate_against_matrix(self, matrix: Any) -> None:
        section_ids = {target.target_id for target in matrix.section_targets}
        table_ids = {target.target_id for target in matrix.table_targets}
        figure_ids = {target.target_id for target in matrix.figure_targets}
        policy_section_ids = set(self.by_section_id())
        policy_figure_ids = set(self.by_figure_id())
        exemptions = set(self.explicit_exemptions)

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


def _policy_record_for_target(target_id: str) -> ReportSectionPolicy | FigurePolicy | None:
    config = default_report_section_policy()
    section = config.by_section_id().get(target_id)
    if section is not None:
        return section
    return config.by_figure_id().get(target_id)


def _validate_section_policy(policy: ReportSectionPolicy) -> None:
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
    if policy.gpt_readiness not in GPT_READINESS_VALUES:
        raise ReportSectionPolicyError(
            f"Section policy '{policy.section_id}' has unsupported gpt_readiness '{policy.gpt_readiness}'."
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
