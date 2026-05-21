from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from review_assist.deliverable_matrix import load_deliverable_matrix
from review_assist.extent_policy import target_extent_metadata
from review_assist.report_section_policy import (
    GPT_ELIGIBLE_DRAFTING_MODES,
    GPT_READY_VALUES,
    REPORT_SECTION_POLICY_PATH,
    ReportSectionPolicyConfig,
    ReportSectionPolicyError,
    load_report_section_policy,
)
from review_assist.source_catalog import repo_root


def _default_policy_data() -> dict[str, object]:
    return json.loads((repo_root() / REPORT_SECTION_POLICY_PATH).read_text(encoding="utf-8"))


def test_report_section_policy_loads_and_validates_against_matrix() -> None:
    matrix = load_deliverable_matrix()
    policy = load_report_section_policy()

    policy.validate_against_matrix(matrix)

    assert policy.profile_id == matrix.profile_id
    assert len(policy.section_policies) == len(matrix.section_targets)
    assert len(policy.figure_policies) == len(matrix.figure_targets)


def test_every_matrix_section_has_policy_or_explicit_exemption() -> None:
    matrix = load_deliverable_matrix()
    policy = load_report_section_policy()
    policy_ids = set(policy.by_section_id())
    exemptions = set(policy.explicit_exemptions)

    assert {target.target_id for target in matrix.section_targets}.issubset(policy_ids | exemptions)
    assert {target.figure_refs[0] for target in matrix.section_targets if len(target.figure_refs) == 1}.intersection(policy.by_figure_id())


def test_demographic_characteristics_uses_county_regional_policy() -> None:
    policy = load_report_section_policy().by_section_id()["demographic-characteristics"]
    metadata = target_extent_metadata(
        target_id="demographic-characteristics",
        target_type="subsection",
        resource_category="community_socioeconomic",
        source_categories=["community_socioeconomic"],
    )

    assert policy.extent_policy == "county_or_regional_context"
    assert policy.visual_extent_class == "county_regional"
    assert metadata["analysis_extent_type"] == "county_or_regional_context_extent"
    assert "for county or regional context" in metadata["interpretation_scope_label"]


def test_oil_wells_direct_check_with_context_figure_policy_is_explicit() -> None:
    config = load_report_section_policy()
    policy = config.by_section_id()["oil-wells"]
    figure_policy = config.by_figure_id()["figure-oil-gas-wells"]
    section_metadata = target_extent_metadata(
        target_id="oil-wells",
        target_type="subsection",
        resource_category="regulated_facilities",
        source_categories=["regulated_facilities"],
    )
    figure_metadata = target_extent_metadata(
        target_id="figure-oil-gas-wells",
        target_type="figure",
        source_categories=["regulated_facilities"],
    )

    assert policy.extent_policy == "direct_check_with_context_figure"
    assert policy.drafting_mode == "gpt_allowed_source_backed_only"
    assert policy.gpt_readiness == "gpt_ready_after_extent_metadata_verification"
    assert "direct_check_and_context_figure_are_distinct" in policy.required_caveats
    assert section_metadata["analysis_extent_type"] == "direct_intersection_extent"
    assert figure_policy.extent_policy == "nearby_context"
    assert figure_metadata["figure_extent_type"] == "nearby_context_extent"


def test_pel_relationship_policy_is_manual_conditional_and_non_gpt() -> None:
    policy = load_report_section_policy().by_section_id()["relationship-with-pel-study"]

    assert policy.inclusion_status == "conditional"
    assert policy.activation_condition == "reviewer_supplied_parent_study"
    assert policy.review_requirement == "manual_review"
    assert policy.manual_or_reviewer_supplied is True
    assert policy.drafting_mode == "manual_reviewer_supplied_only"
    assert policy.gpt_readiness == "manual_reviewer_supplied_only"
    assert "reviewer_supplied_parent_study_required" in policy.required_caveats


def test_wetlands_dynamic_child_policy_preserved_pending_render_gating() -> None:
    parent = load_report_section_policy().by_section_id()["wetlands-and-waterbodies"]
    dynamic_child = load_report_section_policy().by_section_id()["wetlands-waterbodies-alternative-detail"]

    assert parent.comparison_unit_expansion_policy == "narrative_children"
    assert dynamic_child.comparison_unit_expansion_policy == "narrative_children"
    assert dynamic_child.activation_condition == "dynamic_comparison_units"


def test_county_regional_figure_policy_keeps_visual_class_distinct() -> None:
    figure_policy = load_report_section_policy().by_figure_id()["figure-census-tracts"]
    figure_metadata = target_extent_metadata(
        target_id="figure-census-tracts",
        target_type="figure",
        source_categories=["community_socioeconomic"],
    )

    assert figure_policy.extent_policy == "county_or_regional_context"
    assert figure_policy.visual_extent_class == "county_regional"
    assert figure_policy.rendering_extent_class == "medium_context"
    assert figure_metadata["figure_extent_type"] == "county_or_regional_context_extent"


def test_gpt_eligible_sections_have_bounded_sources_caveats_and_prohibitions() -> None:
    policy = load_report_section_policy()
    eligible = [
        item
        for item in policy.section_policies
        if item.drafting_mode in GPT_ELIGIBLE_DRAFTING_MODES or item.gpt_readiness in GPT_READY_VALUES
    ]

    assert eligible
    for item in eligible:
        assert item.required_caveats
        assert item.prohibited_claims
        assert item.allowed_source_categories or item.allowed_source_refs or item.allowed_table_refs or item.allowed_figure_refs
        assert item.manual_or_reviewer_supplied is False


def test_manual_reviewer_supplied_sections_are_not_gpt_ready_by_default() -> None:
    manual = [item for item in load_report_section_policy().section_policies if item.manual_or_reviewer_supplied]

    assert manual
    assert all(item.drafting_mode == "manual_reviewer_supplied_only" for item in manual)
    assert all(item.gpt_readiness == "manual_reviewer_supplied_only" for item in manual)


def test_presentation_only_extent_cannot_be_interpretation_policy(tmp_path: Path) -> None:
    data = copy.deepcopy(_default_policy_data())
    data["section_policies"][0]["extent_policy"] = "presentation_only"  # type: ignore[index]
    path = tmp_path / "report_section_policy.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ReportSectionPolicyError, match="extent_policy"):
        ReportSectionPolicyConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("inclusion_status", "sometimes"),
        ("activation_condition", "auto_magic"),
        ("review_requirement", "skip_review"),
    ],
)
def test_section_activation_fields_are_validated(field: str, value: str) -> None:
    data = copy.deepcopy(_default_policy_data())
    data["section_policies"][0][field] = value  # type: ignore[index]

    with pytest.raises(ReportSectionPolicyError, match=field):
        ReportSectionPolicyConfig.from_dict(data)


def test_unknown_required_caveat_is_rejected() -> None:
    data = copy.deepcopy(_default_policy_data())
    data["section_policies"][0]["required_caveats"] = ["not_a_registered_caveat"]  # type: ignore[index]

    with pytest.raises(ReportSectionPolicyError, match="unknown required_caveats"):
        ReportSectionPolicyConfig.from_dict(data)


def test_unknown_source_refs_and_categories_are_rejected_against_catalog() -> None:
    matrix = load_deliverable_matrix()

    source_ref_data = copy.deepcopy(_default_policy_data())
    source_ref_data["section_policies"][0]["allowed_source_refs"] = ["not_a_source_id"]  # type: ignore[index]
    with pytest.raises(ReportSectionPolicyError, match="unknown source ref"):
        ReportSectionPolicyConfig.from_dict(source_ref_data).validate_against_matrix(matrix)

    source_category_data = copy.deepcopy(_default_policy_data())
    source_category_data["section_policies"][0]["allowed_source_categories"] = ["not_a_source_category"]  # type: ignore[index]
    with pytest.raises(ReportSectionPolicyError, match="unknown source category"):
        ReportSectionPolicyConfig.from_dict(source_category_data).validate_against_matrix(matrix)
