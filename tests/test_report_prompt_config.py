from __future__ import annotations

import copy
import json

import pytest

from review_assist.cli import main
from review_assist.deliverable_matrix import (
    DELIVERABLE_MATRIX_PATH,
    REPORT_PROMPTS_PATH,
    REQUIRED_STUB_TEXT,
    DeliverableMatrixConfig,
    DeliverableMatrixError,
    ReportPromptConfigError,
    ReportPromptConfig,
    _validate_matrix_prompt_refs,
    load_deliverable_matrix,
    load_report_prompt_config,
    validate_deliverable_contract,
)
from review_assist.source_catalog import repo_root


def _default_matrix_data() -> dict[str, object]:
    return json.loads((repo_root() / DELIVERABLE_MATRIX_PATH).read_text(encoding="utf-8"))


def _default_prompt_data() -> dict[str, object]:
    return json.loads((repo_root() / REPORT_PROMPTS_PATH).read_text(encoding="utf-8"))


def test_report_prompt_config_loads_default_config() -> None:
    prompts = load_report_prompt_config()

    assert prompts.profile_id == "environmental_constraints_example"
    assert prompts.required_stub_text == REQUIRED_STUB_TEXT
    assert prompts.global_prompt_key == "global"
    assert len(prompts.prompts) == 45


def test_every_matrix_prompt_key_exists_in_prompt_config() -> None:
    matrix = validate_deliverable_contract()
    prompts = load_report_prompt_config()
    prompt_keys = set(prompts.by_prompt_key())

    assert {target.prompt_key for target in matrix.section_targets}.issubset(prompt_keys)


def test_prompt_target_refs_are_valid() -> None:
    matrix = load_deliverable_matrix()
    prompts = load_report_prompt_config()
    section_ids = set(matrix.by_section_id())

    for prompt in prompts.prompts:
        for target_id in prompt.target_ids:
            assert target_id == "global" or target_id in section_ids


def test_global_prompt_has_required_guardrails() -> None:
    prompts = load_report_prompt_config()
    global_prompt = prompts.by_prompt_key()["global"]
    guardrails = " ".join(global_prompt.prohibited_claims).lower()

    for term in [
        "ranking",
        "scoring",
        "preferred alternative",
        "alternative selection",
        "alternative rejection",
        "field verification",
        "jurisdictional",
        "agency approval",
        "agency clearance",
        "unsupported facts",
        "example-project fact reuse",
        "final determination",
    ]:
        assert term in guardrails


def test_contract_rejects_missing_prompt_key() -> None:
    matrix_data = copy.deepcopy(_default_matrix_data())
    prompt_data = copy.deepcopy(_default_prompt_data())
    matrix_data["section_targets"][0]["prompt_key"] = "missing-prompt"  # type: ignore[index]
    matrix = DeliverableMatrixConfig.from_dict(matrix_data)
    prompts = ReportPromptConfig.from_dict(prompt_data)

    with pytest.raises(DeliverableMatrixError, match="missing report prompt key"):
        _validate_matrix_prompt_refs(matrix, prompts)


def test_contract_rejects_unknown_prompt_target_ref() -> None:
    matrix_data = copy.deepcopy(_default_matrix_data())
    prompt_data = copy.deepcopy(_default_prompt_data())
    prompt_data["prompts"][1]["target_ids"] = ["missing-target"]  # type: ignore[index]
    matrix = DeliverableMatrixConfig.from_dict(matrix_data)
    prompts = ReportPromptConfig.from_dict(prompt_data)

    with pytest.raises(ReportPromptConfigError, match="unknown matrix target"):
        _validate_matrix_prompt_refs(matrix, prompts)


def test_validate_deliverable_matrix_cli_json(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["validate-deliverable-matrix", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["profile_id"] == "environmental_constraints_example"
    assert payload["section_target_count"] == 44
    assert payload["table_target_count"] == 4
    assert payload["figure_target_count"] == 15
    assert payload["attachment_target_count"] == 3
    assert payload["prompt_count"] == 45


def test_validate_report_prompts_cli_json(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["validate-report-prompts", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["profile_id"] == "environmental_constraints_example"
    assert payload["prompt_version"] == "2026-05-17"
    assert payload["prompt_count"] == 45
