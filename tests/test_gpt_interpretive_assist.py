from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from review_assist.cli import main
from review_assist.deliverable_items import generate_deliverable_items
from review_assist.evidence_package import build_evidence_package
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
from review_assist.review_queue import generate_review_queue
from review_assist.review_queue import load_review_queue
from review_assist.review_queue import update_review_item
from review_assist.section_drafting import SectionDraftRequest

from test_export_report import add_source_input, add_supported_real_source_inputs, write_project


def _source_backed_project(tmp_path: Path) -> Path:
    project_dir = write_project(tmp_path)
    add_supported_real_source_inputs(project_dir)
    add_source_input(
        project_dir,
        "fema_nfhl_flood_hazard",
        "provided_fema_flood_hazard.geojson",
        {
            "type": "Polygon",
            "coordinates": [[[-90.001, 31.999], [-89.998, 31.999], [-89.998, 32.001], [-90.001, 32.001], [-90.001, 31.999]]],
        },
    )
    populate_for_review(project_dir, prepare_sources=True, gpt_drafting=False)
    return project_dir


def _add_stale_nwi_acquisition_failure(project_dir: Path) -> None:
    path = project_dir / "source_acquisition" / "source_acquisition_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    downloads = [item for item in data.get("downloads", []) if isinstance(item, dict)]
    validation_issues = [item for item in data.get("validation_issues", []) if isinstance(item, dict)]
    downloads.append(
        {
            "source_id": "usfws_nwi_wetlands",
            "source_name": "National Wetlands Inventory",
            "source_category": "wetlands_waterbodies",
            "status": "failed",
            "output_path": str(project_dir / "source_acquisition" / "downloads" / "usfws_nwi_wetlands.geojson"),
        }
    )
    validation_issues.append(
        {
            "severity": "warning",
            "code": "source_download_failed",
            "message": "Unable to download National Wetlands Inventory source.",
            "source_id": "usfws_nwi_wetlands",
        }
    )
    data.update(
        {
            "output_path": str(path),
            "downloads": downloads,
            "download_count": len(downloads),
            "validation_issues": validation_issues,
        }
    )
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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


def _benign_selected_source_response(*, model: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_content": (
            "The selected NWI and NHD source datasets support early desktop screening for mapped wetlands, "
            "streams, ponds, and drainage features. Table 1 and Figure 1 should be used to compare planning "
            "constraints while recognizing that these data do not define jurisdictional wetland or waterbody "
            "limits. Site-specific delineation and agency coordination would be needed before final design or "
            "permitting decisions."
        ),
        "cited_finding_ids": [],
        "cited_table_ids": payload["related_ids"]["table_ids"][:1],
        "cited_figure_ids": payload["related_ids"]["figure_ids"][:1],
        "cited_source_refs": payload["related_ids"]["source_refs"][:2],
        "caveats": payload["section_policy"]["required_caveats"],
        "usage": {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30},
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


def test_gpt_planning_skips_body_ineligible_render_items(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)

    plan = plan_gpt_section_drafts(project_dir, max_calls=None)
    skipped = {row["target_id"]: row["reason"] for row in plan["skipped_sections"]}
    eligible = {row["target_id"] for row in plan["eligible_sections"]}
    planned_or_skipped = {row["target_id"] for row in [*plan["planned_sections"], *plan["eligible_sections"], *plan["skipped_sections"]]}

    assert "floodplains-and-floodways" in eligible
    assert "floodplains-and-floodways" not in skipped
    assert skipped["relationship-with-pel-study"] == "manual_or_reviewer_supplied"
    assert skipped["community-resources"] == "umbrella_section_deterministic_only"
    assert skipped["environmental-constraints-inventory"] == "umbrella_section_deterministic_only"
    assert "natural-and-ecological-resources" not in planned_or_skipped


def test_floodplains_gpt_payload_includes_fema_table_figure_extent_and_caveats(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)
    captured: dict[str, Any] = {}

    def capture_response(*, model: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        captured["payload"] = payload
        return _safe_gpt_response(model=model, payload=payload, schema=schema)

    result = draft_section_candidates(
        project_dir,
        sections=["floodplains-and-floodways"],
        max_calls=1,
        response_create=capture_response,
    )

    payload = captured["payload"]
    assert result["accepted_gpt_draft_count"] == 1
    assert payload["section_policy"]["section_id"] == "floodplains-and-floodways"
    assert "fema_nfhl_flood_hazard" in payload["related_ids"]["source_refs"]
    assert payload["related_ids"]["table_ids"] == ["table-fema-flood-zones"]
    assert payload["related_ids"]["figure_ids"] == ["figure-fema-flood-zones"]
    assert payload["related_labels"]["tables"][0]["label"] == "Table 2"
    assert payload["related_labels"]["figures"][0]["label"] == "Figure 2"
    assert payload["related_labels"]["sources"][0]["label"] != "fema_nfhl_flood_hazard"
    assert payload["extent_metadata"]["analysis_extent_type"] == "direct_intersection_extent"
    assert payload["extent_metadata"]["interpretation_scope_label"] == "within the project area"
    assert "not_final_floodplain_determination" in payload["section_policy"]["required_caveats"]


def test_gpt_planning_skips_manual_and_restricted_source_need_sections(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)

    plan = plan_gpt_section_drafts(project_dir, max_calls=None)
    skipped = {row["target_id"]: row["reason"] for row in plan["skipped_sections"]}
    eligible = {row["target_id"] for row in plan["eligible_sections"]}

    assert "wetlands-and-waterbodies" in eligible
    assert "cultural-and-historic-resources" not in eligible
    assert skipped["cultural-and-historic-resources"] == "section_source_needs_restricted_review_needed"
    assert "hazardous-materials-sites" not in eligible
    assert skipped["hazardous-materials-sites"] == "section_source_needs_manual_review_needed"


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
    _add_stale_nwi_acquisition_failure(project_dir)
    build_evidence_package(project_dir)
    generate_deliverable_items(project_dir, gpt_drafting=False)
    generate_review_queue(project_dir)
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
    assert "Drafting mode: section_rollup." in captured["payload"]["constraints"]
    assert any("not as an evidence manifest" in item for item in captured["payload"]["constraints"])
    assert "source_not_downloaded" not in json.dumps(captured["payload"])
    assert "source_download_failed" not in json.dumps(captured["payload"])


def test_wetlands_comparison_unit_payload_uses_comparison_unit_narrative_mode(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)
    captured: dict[str, Any] = {}

    def capture_response(*, model: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        captured["payload"] = payload
        return _safe_gpt_response(model=model, payload=payload, schema=schema)

    result = draft_section_candidates(
        project_dir,
        sections=["wetlands-waterbodies-comparison-unit-00001"],
        max_calls=1,
        response_create=capture_response,
    )

    payload = captured["payload"]
    assert result["accepted_gpt_draft_count"] == 1
    assert payload["section_policy"]["section_id"] == "wetlands-waterbodies-alternative-detail"
    assert payload["prompt_contract"]["section_prompt"]["output_style"]["drafting_mode"] == "comparison_unit_narrative"
    assert "Drafting mode: comparison_unit_narrative." in payload["constraints"]
    assert any("Do not invent right-of-way" in item for item in payload["constraints"])


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
    fallback = item["provenance"]["gpt_interpretive_assist_fallback"]
    assert fallback["attempted"] is True
    assert fallback["deterministic_content_retained"] is True
    assert fallback["reason_code"] == "gpt_output_rejected"
    assert "style_context_cited_as_evidence" in {issue["code"] for issue in fallback["validation_issues"]}
    assert "gpt_interpretive_assist_fallback" in item["uncertainty_flags"]
    assert "style_context_cited_as_evidence" in {
        issue["code"] for issue in result["sections_rejected"][0]["validation_issues"]
    }


def test_benign_selected_source_wording_is_not_rejected_as_alternative_selection(tmp_path: Path) -> None:
    project_dir = _source_backed_project(tmp_path)

    result = draft_section_candidates(
        project_dir,
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        response_create=_benign_selected_source_response,
    )
    item = next(item for item in load_review_queue(project_dir)["items"] if item["id"] == "wetlands-and-waterbodies")

    assert result["accepted_gpt_draft_count"] == 1
    assert result["rejected_gpt_draft_count"] == 0
    assert "The selected NWI and NHD source datasets" in item["generated_content"]
    assert "gpt_interpretive_assist" in item["provenance"]
    assert "gpt_interpretive_assist_fallback" not in item["provenance"]


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
