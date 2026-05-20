from __future__ import annotations

import copy
import json

import pytest

from review_assist.deliverable_matrix import (
    DELIVERABLE_MATRIX_PATH,
    REQUIRED_STUB_TEXT,
    DeliverableMatrixConfig,
    DeliverableMatrixError,
    load_deliverable_matrix,
)
from review_assist.extent_policy import (
    COMMUNITY_CONTEXT_EXTENT,
    COUNTY_OR_REGIONAL_CONTEXT_EXTENT,
    DIRECT_INTERSECTION_EXTENT,
    NEARBY_CONTEXT_EXTENT,
    WATERSHED_CONTEXT_EXTENT,
    target_extent_metadata,
)
from review_assist.source_catalog import repo_root


def _default_matrix_data() -> dict[str, object]:
    return json.loads((repo_root() / DELIVERABLE_MATRIX_PATH).read_text(encoding="utf-8"))


def test_deliverable_matrix_loads_default_config() -> None:
    config = load_deliverable_matrix()

    assert config.profile_id == "environmental_constraints_example"
    assert config.stub_text == REQUIRED_STUB_TEXT
    assert len(config.section_targets) == 44
    assert len(config.table_targets) == 4
    assert len(config.figure_targets) == 15
    assert len(config.attachment_targets) == 3


def test_deliverable_matrix_target_ids_are_unique() -> None:
    config = load_deliverable_matrix()

    section_ids = [target.target_id for target in config.section_targets]
    table_ids = [target.target_id for target in config.table_targets]
    figure_ids = [target.target_id for target in config.figure_targets]
    attachment_ids = [target.target_id for target in config.attachment_targets]

    assert len(section_ids) == len(set(section_ids))
    assert len(table_ids) == len(set(table_ids))
    assert len(figure_ids) == len(set(figure_ids))
    assert len(attachment_ids) == len(set(attachment_ids))


def test_deliverable_matrix_numbering_is_stable() -> None:
    config = load_deliverable_matrix()

    assert [target.table_number for target in config.table_targets] == [1, 2, 3, 4]
    assert [target.target_id for target in config.table_targets] == [
        "table-wetlands-waterbodies",
        "table-fema-flood-zones",
        "table-income-demographics",
        "table-demographic-composition",
    ]
    assert [target.figure_number for target in config.figure_targets] == list(range(1, 16))
    assert [target.attachment_letter for target in config.attachment_targets] == ["A", "B", "C"]


def test_deliverable_matrix_has_dynamic_wetlands_template() -> None:
    config = load_deliverable_matrix()
    dynamic = config.by_section_id()["wetlands-waterbodies-alternative-detail"]

    assert dynamic.target_type == "dynamic_subsection_template"
    assert dynamic.section_number == "3.1.1.x"
    assert dynamic.prompt_key == "wetlands-waterbodies-alternative-detail"


def test_deliverable_matrix_targets_resolve_extent_policy_metadata() -> None:
    config = load_deliverable_matrix()

    for target in config.section_targets:
        metadata = target_extent_metadata(
            target_id=target.target_id,
            target_type=target.target_type,
            resource_category=target.resource_category,
            source_categories=target.source_categories,
        )
        assert metadata["query_extent_type"] == "project_area_analysis_bounds"
        assert metadata["analysis_extent_type"]
        assert metadata["interpretation_scope_label"]
        if target.target_type in {"front_matter", "section", "subsection", "dynamic_subsection_template"}:
            assert metadata["list_extent_type"]

    for target in config.table_targets:
        metadata = target_extent_metadata(
            target_id=target.target_id,
            target_type="table",
            source_categories=target.source_categories,
        )
        assert metadata["query_extent_type"] == "project_area_analysis_bounds"
        assert metadata["analysis_extent_type"]
        assert metadata["interpretation_scope_label"]
        assert metadata["table_extent_type"]

    for target in config.figure_targets:
        metadata = target_extent_metadata(
            target_id=target.target_id,
            target_type="figure",
            source_categories=target.source_categories,
        )
        assert metadata["query_extent_type"] == "project_area_analysis_bounds"
        assert metadata["analysis_extent_type"]
        assert metadata["interpretation_scope_label"]
        assert metadata["figure_extent_type"]
        assert metadata["render_extent_type"] == "figure_render_extent"
        assert metadata["render_extent_is_presentation_only"] is True

    for target in config.attachment_targets:
        metadata = target_extent_metadata(
            target_id=target.target_id,
            target_type="attachment",
            resource_category="attachments",
            source_categories=[],
        )
        assert metadata["analysis_extent_type"]
        assert metadata["list_extent_type"]


def test_deliverable_matrix_extent_policy_keeps_key_scope_assignments_stable() -> None:
    config = load_deliverable_matrix()
    sections = config.by_section_id()
    figures = {target.target_id: target for target in config.figure_targets}

    def section_scope(target_id: str) -> str:
        target = sections[target_id]
        return target_extent_metadata(
            target_id=target.target_id,
            target_type=target.target_type,
            resource_category=target.resource_category,
            source_categories=target.source_categories,
        )["analysis_extent_type"]

    def figure_scope(target_id: str) -> str:
        target = figures[target_id]
        return target_extent_metadata(
            target_id=target.target_id,
            target_type="figure",
            source_categories=target.source_categories,
        )["figure_extent_type"]

    assert section_scope("wetlands-and-waterbodies") == DIRECT_INTERSECTION_EXTENT
    assert section_scope("floodplains-and-floodways") == DIRECT_INTERSECTION_EXTENT
    assert section_scope("water-quality") == WATERSHED_CONTEXT_EXTENT
    assert section_scope("cultural-and-historic-resources") == NEARBY_CONTEXT_EXTENT
    assert section_scope("health-care-facilities") == COMMUNITY_CONTEXT_EXTENT
    assert section_scope("hazardous-materials-sites") == NEARBY_CONTEXT_EXTENT
    assert section_scope("oil-wells") == DIRECT_INTERSECTION_EXTENT
    assert section_scope("demographic-characteristics") == COUNTY_OR_REGIONAL_CONTEXT_EXTENT

    assert figure_scope("figure-wetlands-waterbodies") == DIRECT_INTERSECTION_EXTENT
    assert figure_scope("figure-streams-impaired-waters") == WATERSHED_CONTEXT_EXTENT
    assert figure_scope("figure-cultural-resources") == NEARBY_CONTEXT_EXTENT
    assert figure_scope("figure-health-care-facilities") == COMMUNITY_CONTEXT_EXTENT
    assert figure_scope("figure-hazardous-waste-sites") == NEARBY_CONTEXT_EXTENT
    assert figure_scope("figure-oil-gas-wells") == NEARBY_CONTEXT_EXTENT
    assert figure_scope("figure-census-tracts") == COUNTY_OR_REGIONAL_CONTEXT_EXTENT


def test_deliverable_matrix_rejects_invalid_table_ref() -> None:
    data = copy.deepcopy(_default_matrix_data())
    data["section_targets"][0]["table_refs"] = ["missing-table"]  # type: ignore[index]

    with pytest.raises(DeliverableMatrixError, match="unknown table target"):
        DeliverableMatrixConfig.from_dict(data)


def test_deliverable_matrix_rejects_invalid_figure_ref() -> None:
    data = copy.deepcopy(_default_matrix_data())
    data["section_targets"][0]["figure_refs"] = ["missing-figure"]  # type: ignore[index]

    with pytest.raises(DeliverableMatrixError, match="unknown figure target"):
        DeliverableMatrixConfig.from_dict(data)


def test_deliverable_matrix_rejects_invalid_attachment_ref() -> None:
    data = copy.deepcopy(_default_matrix_data())
    data["section_targets"][0]["attachment_refs"] = ["missing-attachment"]  # type: ignore[index]

    with pytest.raises(DeliverableMatrixError, match="unknown attachment target"):
        DeliverableMatrixConfig.from_dict(data)


def test_deliverable_matrix_rejects_required_target_without_stub() -> None:
    data = copy.deepcopy(_default_matrix_data())
    data["section_targets"][0]["stub_when_missing"] = False  # type: ignore[index]

    with pytest.raises(DeliverableMatrixError, match="stub_when_missing"):
        DeliverableMatrixConfig.from_dict(data)
