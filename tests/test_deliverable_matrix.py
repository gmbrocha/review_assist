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
from review_assist.source_catalog import repo_root


def _default_matrix_data() -> dict[str, object]:
    return json.loads((repo_root() / DELIVERABLE_MATRIX_PATH).read_text(encoding="utf-8"))


def test_deliverable_matrix_loads_default_config() -> None:
    config = load_deliverable_matrix()

    assert config.profile_id == "environmental_constraints_example"
    assert config.stub_text == REQUIRED_STUB_TEXT
    assert len(config.section_targets) == 44
    assert len(config.table_targets) == 4
    assert len(config.figure_targets) == 13
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
    assert [target.figure_number for target in config.figure_targets] == list(range(1, 14))
    assert [target.attachment_letter for target in config.attachment_targets] == ["A", "B", "C"]


def test_deliverable_matrix_has_dynamic_wetlands_template() -> None:
    config = load_deliverable_matrix()
    dynamic = config.by_section_id()["wetlands-waterbodies-alternative-detail"]

    assert dynamic.target_type == "dynamic_subsection_template"
    assert dynamic.section_number == "3.1.1.x"
    assert dynamic.prompt_key == "wetlands-waterbodies-alternative-detail"


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
