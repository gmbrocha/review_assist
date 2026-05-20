from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from review_assist.cli import main
from review_assist.export_report import ExportGateError, export_report
from review_assist.gpt_interpretive_assist import (
    GPT_INTERPRETIVE_CACHE_PATH,
    _fingerprint_for_request,
    draft_section_candidates,
    gpt_interpretive_assist_status,
    load_report_style_context,
    plan_gpt_section_drafts,
)
from review_assist.populate_for_review import populate_for_review
from review_assist.report_section_policy import load_report_section_policy
from review_assist.review_queue import load_review_queue
from review_assist.review_queue import update_review_item
from review_assist.section_drafting import SectionDraftRequest

from test_export_report import add_supported_real_source_inputs, write_project


def _source_backed_project(tmp_path: Path) -> Path:
    project_dir = write_project(tmp_path)
    add_supported_real_source_inputs(project_dir)
    populate_for_review(project_dir, prepare_sources=True, gpt_drafting=False)
    return project_dir


def _safe_gpt_response(*, model: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    policy = payload["section_policy"]
    table_ids = payload["related_ids"]["table_ids"]
    figure_ids = payload["related_ids"]["figure_ids"]
    source_refs = payload["related_ids"]["source_refs"]
    return {
        "draft_content": (
            f"{payload['section']['title']} is summarized from source-backed screening evidence. "
            "The discussion remains desktop screening context for human review."
        ),
        "cited_finding_ids": [],
        "cited_table_ids": table_ids[:1],
        "cited_figure_ids": figure_ids[:1],
        "cited_source_refs": source_refs[:1],
        "caveats": policy["required_caveats"],
        "usage": {"input_tokens": 111, "output_tokens": 22, "total_tokens": 133},
    }


def _style_context_citation_response(*, model: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_content": "According to the style context, this section is supported by example report evidence.",
        "cited_finding_ids": [],
        "cited_table_ids": [],
        "cited_figure_ids": [],
        "cited_source_refs": ["style_context"],
        "caveats": payload["section_policy"]["required_caveats"],
    }


def test_style_context_loads_as_non_evidence() -> None:
    context = load_report_style_context()

    assert context["kind"] == "style_guidance_only"
    assert context["not_project_evidence"] is True
    assert context["must_not_be_cited"] is True
    assert "trail-specific assumptions" in context["content"].lower()


def test_dry_run_reports_planned_sections_without_api_calls(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)

    result = draft_section_candidates(project_dir, dry_run=True, max_calls=2)

    assert result["dry_run"] is True
    assert result["planned_call_count"] <= 2
    assert result["completed_call_count"] == 0
    assert result["eligible_sections"]


def test_cli_draft_section_candidates_dry_run_reports_planned_sections(
    tmp_path: Path,
    capsys,
) -> None:
    project_dir = _source_backed_project(tmp_path)

    assert main(["draft-section-candidates", str(project_dir), "--dry-run", "--max-calls", "1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["dry_run"] is True
    assert payload["planned_call_count"] <= 1
    assert payload["completed_call_count"] == 0


def test_gpt_draft_updates_review_queue_as_unaccepted_candidate_and_caches(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)
    captured: dict[str, Any] = {}

    def capture_response(*, model: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        captured["payload"] = payload
        return _safe_gpt_response(model=model, payload=payload, schema=schema)

    result = draft_section_candidates(
        project_dir,
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        response_create=capture_response,
    )
    queue = load_review_queue(project_dir)
    item = next(item for item in queue["items"] if item["id"] == "wetlands-and-waterbodies")
    cache = json.loads((project_dir / GPT_INTERPRETIVE_CACHE_PATH).read_text(encoding="utf-8"))

    assert result["accepted_gpt_draft_count"] == 1
    assert result["completed_call_count"] == 1
    assert "source-backed screening evidence" in item["generated_content"]
    assert item["status"] == "needs_review"
    assert item["export_eligible"] is False
    assert "gpt_interpretive_assist" in item["uncertainty_flags"]
    assert item["provenance"]["gpt_interpretive_assist"]["review_before_export"] is True
    assert cache["entries"]["wetlands-and-waterbodies"]["validation_status"] == "accepted"
    assert cache["entries"]["wetlands-and-waterbodies"]["token_usage"]["total_tokens"] == 133
    assert result["token_usage"]["total_tokens"] == 133
    assert captured["payload"]["section_policy"]["section_id"] == "wetlands-and-waterbodies"
    assert captured["payload"]["style_context"]["not_project_evidence"] is True
    assert captured["payload"]["style_context"]["must_not_be_cited"] is True


def test_gpt_items_remain_export_gated_until_human_review(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)
    draft_section_candidates(
        project_dir,
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        response_create=_safe_gpt_response,
    )

    try:
        export_report(project_dir)
    except ExportGateError as exc:
        assert exc.details["unreviewed_item_count"] > 0
        item = next(item for item in load_review_queue(project_dir)["items"] if item["id"] == "wetlands-and-waterbodies")
        assert item["status"] == "needs_review"
    else:
        raise AssertionError("Unreviewed GPT review candidate should block default export.")

    update_review_item(project_dir, "wetlands-and-waterbodies", status="accepted")
    manifest = export_report(project_dir, include_draft=True)

    assert manifest["gpt_drafting"]["enabled"] is True
    assert manifest["gpt_drafting"]["accepted_section_count"] >= 1


def test_skip_existing_avoids_duplicate_calls_when_fingerprint_is_current(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)
    calls = 0

    def counted_response(*, model: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _safe_gpt_response(model=model, payload=payload, schema=schema)

    first = draft_section_candidates(
        project_dir,
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        response_create=counted_response,
    )
    second = draft_section_candidates(
        project_dir,
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        response_create=counted_response,
    )

    assert first["completed_call_count"] == 1
    assert second["planned_call_count"] == 0
    assert calls == 1
    assert second["sections_skipped_existing"][0]["reason"] == "existing_gpt_draft_current"


def test_prompt_contract_changes_invalidate_gpt_cache_fingerprint() -> None:
    policy = load_report_section_policy().by_section_id()["wetlands-and-waterbodies"]
    style_context = load_report_style_context()
    base = SectionDraftRequest(
        section_id="wetlands-and-waterbodies",
        target_id="wetlands-and-waterbodies",
        section_type="section_text",
        title="Wetlands and Waterbodies",
        purpose="Draft bounded wetlands context.",
        resource_category="wetlands_waterbodies",
        deterministic_content="Deterministic baseline.",
        evidence_bundle={"section_id": "wetlands-and-waterbodies", "source_refs": ["usfws_nwi_wetlands"]},
        section_policy=policy.__dict__,
        style_context=style_context,
        prompt={"prompt_key": "wetlands", "section_instruction": "First version."},
        global_prompt={"prompt_key": "global", "section_instruction": "Global."},
    )
    changed = SectionDraftRequest(
        **{
            **base.__dict__,
            "prompt": {"prompt_key": "wetlands", "section_instruction": "Updated version."},
        }
    )

    first = _fingerprint_for_request(request=base, policy=policy, style_context=style_context, model="gpt-test")
    second = _fingerprint_for_request(request=changed, policy=policy, style_context=style_context, model="gpt-test")

    assert first["prompt_contract_hash"] != second["prompt_contract_hash"]
    assert first["fingerprint_key"] != second["fingerprint_key"]


def test_force_refresh_calls_again_instead_of_reusing_cache(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)
    calls = 0

    def counted_response(*, model: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _safe_gpt_response(model=model, payload=payload, schema=schema)

    draft_section_candidates(project_dir, sections=["wetlands-and-waterbodies"], max_calls=1, response_create=counted_response)
    draft_section_candidates(
        project_dir,
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        force_refresh=True,
        response_create=counted_response,
    )

    assert calls == 2


def test_rejected_gpt_output_does_not_replace_deterministic_candidate(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)
    original = next(item for item in load_review_queue(project_dir)["items"] if item["id"] == "wetlands-and-waterbodies")[
        "generated_content"
    ]

    result = draft_section_candidates(
        project_dir,
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        response_create=_style_context_citation_response,
    )
    item = next(item for item in load_review_queue(project_dir)["items"] if item["id"] == "wetlands-and-waterbodies")

    assert result["rejected_gpt_draft_count"] == 1
    assert result["deterministic_fallback_count"] == 1
    assert item["generated_content"] == original
    assert "style_context_cited_as_evidence" in {
        issue["code"] for issue in result["sections_rejected"][0]["validation_issues"]
    }


def test_rejected_gpt_output_does_not_overwrite_accepted_cache_entry(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)
    draft_section_candidates(
        project_dir,
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        response_create=_safe_gpt_response,
    )
    accepted_cache = json.loads((project_dir / GPT_INTERPRETIVE_CACHE_PATH).read_text(encoding="utf-8"))
    accepted_key = accepted_cache["entries"]["wetlands-and-waterbodies"]["fingerprint_key"]

    draft_section_candidates(
        project_dir,
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        force_refresh=True,
        response_create=_style_context_citation_response,
    )
    cache = json.loads((project_dir / GPT_INTERPRETIVE_CACHE_PATH).read_text(encoding="utf-8"))

    assert cache["entries"]["wetlands-and-waterbodies"]["validation_status"] == "accepted"
    assert cache["entries"]["wetlands-and-waterbodies"]["fingerprint_key"] == accepted_key
    assert cache["rejected_entries"]["wetlands-and-waterbodies"][0]["validation_status"] == "rejected"


def test_source_backed_only_filters_stub_sections(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir, gpt_drafting=False)

    plan = plan_gpt_section_drafts(project_dir, source_backed_only=True)

    assert not plan["eligible_sections"]
    assert {row["reason"] for row in plan["skipped_sections"] if row["target_id"] == "wetlands-and-waterbodies"}


def test_gpt_status_reports_disabled_when_env_gate_is_off(tmp_path: Path, monkeypatch) -> None:
    project_dir = _source_backed_project(tmp_path)
    monkeypatch.setenv("GPT_DRAFTING", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    status = gpt_interpretive_assist_status(project_dir)

    assert status["status"] == "disabled"
    assert status["planned_call_count"] >= 0
