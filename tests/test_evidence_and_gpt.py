from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from review_assist import section_drafting
from review_assist.cli import main
from review_assist.deliverable import build_mvp_deliverable
from review_assist.env_config import GptConfigurationError, gpt_drafting_enabled, openai_api_key_required, resolve_gpt_model
from review_assist.evidence_package import build_evidence_package
from review_assist.populate_for_review import populate_for_review
from review_assist.report_sections import ReportSectionGenerationError, generate_report_sections

from test_export_report import add_supported_real_source_inputs, docx_text, write_project


def fake_gpt_response(self: section_drafting.OpenAISectionDraftProvider, payload: dict[str, Any]) -> dict[str, Any]:
    section = payload["section"]
    return {
        "draft_content": f"GPT draft for {section['title']} using only the provided evidence bundle.",
        "cited_finding_ids": [],
        "cited_table_ids": [],
        "cited_figure_ids": [],
        "cited_source_refs": [],
        "caveats": ["Draft section requires reviewer approval before export."],
    }


def rejected_gpt_response(self: section_drafting.OpenAISectionDraftProvider, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_content": "This is the preferred alternative based on field-verified jurisdictional evidence.",
        "cited_finding_ids": ["missing-finding-id"],
        "cited_table_ids": [],
        "cited_figure_ids": [],
        "cited_source_refs": [],
        "caveats": [],
    }


def test_gpt_env_parsing_and_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("1", "true", "yes", "on", "TRUE"):
        monkeypatch.setenv("GPT_DRAFTING", value)
        assert gpt_drafting_enabled() is True

    for value in ("", "0", "false", "no", "off", "unexpected"):
        monkeypatch.setenv("GPT_DRAFTING", value)
        assert gpt_drafting_enabled() is False

    monkeypatch.setenv("OPENAI_INTERPRETER_MODEL", "gpt-test-model")
    assert resolve_gpt_model() == "gpt-test-model"
    assert resolve_gpt_model("cli-model") == "cli-model"

    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(GptConfigurationError, match="OPENAI_API_KEY"):
        openai_api_key_required()


def test_build_evidence_package_classifies_stubs_and_real_sources(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    stub_package = build_evidence_package(project_dir)

    assert stub_package["stub_count"] > 0
    assert stub_package["real_source_count"] == 0
    assert stub_package["evidence_class_counts"]["stub_or_manual"] > 0
    assert (project_dir / "evidence" / "evidence_package.json").exists()

    real_project_dir = write_project(tmp_path / "real")
    add_supported_real_source_inputs(real_project_dir)
    populate_for_review(real_project_dir, prepare_sources=True, gpt_drafting=False)
    real_package = build_evidence_package(real_project_dir)

    assert real_package["real_source_count"] >= 4
    assert real_package["source_backed_constraint_count"] > 0
    assert real_package["evidence_class_counts"]["source_backed"] > 0


def test_cli_build_evidence_package_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["build-evidence-package", str(project_dir), "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["project_id"] == "test_project"
    assert payload["output_path"].endswith("evidence_package.json")


def test_report_sections_use_mocked_gpt_provider_and_record_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setenv("GPT_DRAFTING", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_INTERPRETER_MODEL", "gpt-test")
    monkeypatch.setattr(section_drafting.OpenAISectionDraftProvider, "_create_response", fake_gpt_response)

    result = generate_report_sections(project_dir)
    front_matter = next(section for section in result["sections"] if section["section_id"] == "front-matter")

    assert result["gpt_drafting"]["enabled"] is True
    assert result["gpt_drafting"]["gpt_section_count"] == result["section_count"]
    assert result["gpt_drafting"]["model"] == "gpt-test"
    assert "GPT draft for" in front_matter["generated_content"]
    assert front_matter["provenance"]["draft_provider"] == "openai_responses"
    assert front_matter["provenance"]["gpt_model"] == "gpt-test"
    assert front_matter["provenance"]["input_digest"]
    assert "gpt_drafted_pre_review" in front_matter["uncertainty_flags"]


def test_report_sections_reject_invalid_gpt_citations_and_language(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setenv("GPT_DRAFTING", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(section_drafting.OpenAISectionDraftProvider, "_create_response", rejected_gpt_response)

    result = generate_report_sections(project_dir, gpt_model="gpt-test")
    codes = {issue["code"] for issue in result["validation_issues"]}
    front_matter = next(section for section in result["sections"] if section["section_id"] == "front-matter")

    assert result["gpt_drafting"]["rejected_gpt_section_count"] > 0
    assert "unknown_finding_id" in codes
    assert "prohibited_gpt_language" in codes
    assert "preferred alternative" not in front_matter["generated_content"].lower()
    assert front_matter["provenance"]["gpt_output_accepted"] is False
    assert "gpt_draft_rejected" in front_matter["uncertainty_flags"]


def test_gpt_enabled_without_key_fails_clearly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setenv("GPT_DRAFTING", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    with pytest.raises(ReportSectionGenerationError, match="OPENAI_API_KEY"):
        generate_report_sections(project_dir)


def test_cli_no_gpt_drafting_overrides_enabled_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setenv("GPT_DRAFTING", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    assert main(["generate-report-sections", str(project_dir), "--no-gpt-drafting", "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["gpt_drafting"]["enabled"] is False


def test_build_mvp_deliverable_records_evidence_and_gpt_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    add_supported_real_source_inputs(project_dir)
    monkeypatch.setenv("GPT_DRAFTING", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(section_drafting.OpenAISectionDraftProvider, "_create_response", fake_gpt_response)

    manifest = build_mvp_deliverable(project_dir, output_format="both", gpt_drafting=True, gpt_model="gpt-test")
    text = docx_text(manifest["docx_path"])

    assert manifest["evidence_package_path"].endswith("evidence_package.json")
    assert manifest["gpt_drafting"]["enabled"] is True
    assert manifest["gpt_drafting"]["models"] == ["gpt-test"]
    assert "GPT draft for" in text
