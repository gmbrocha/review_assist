"""Explicit, cached GPT Interpretive Assist for review queue candidates."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .deliverable_matrix import load_deliverable_matrix, load_report_prompt_config
from .env_config import GptConfigurationError, gpt_drafting_enabled, load_project_env, openai_api_key_required, resolve_gpt_model
from .evidence_package import EvidencePackageError, load_evidence_package, section_evidence_for
from .project_context import ProjectContextError, load_project_context
from .report_section_policy import (
    GPT_ELIGIBLE_DRAFTING_MODES,
    GPT_READY_VALUES,
    ReportSectionPolicy,
    load_report_section_policy,
)
from .review_queue import REVIEW_QUEUE_PATH, ReviewQueueError, load_review_queue
from .section_drafting import (
    PROMPT_VERSION,
    SectionDraftRequest,
    SectionDraftingError,
    SectionDraftResult,
    OpenAISectionDraftProvider,
)
from .source_catalog import repo_root


GPT_INTERPRETIVE_CACHE_PATH = Path("drafts/gpt_interpretive_assist_cache.json")
GPT_INTERPRETIVE_RUN_PATH = Path("drafts/gpt_interpretive_assist_run.json")
DEFAULT_STYLE_CONTEXT_PATH = Path("config/report_style_context/environmental_constraints_report_style.md")
CACHE_SCHEMA_VERSION = "gpt-interpretive-assist-cache-v1"
RUN_SCHEMA_VERSION = "gpt-interpretive-assist-run-v1"
STYLE_CONTEXT_SCHEMA_VERSION = "report-style-context-v1"
TERMINAL_REVIEW_STATUSES = {"accepted", "edited", "replaced", "declined", "unable_to_verify"}
DEFAULT_MAX_CALLS = 5


class GptInterpretiveAssistError(RuntimeError):
    """Raised when explicit GPT Interpretive Assist cannot run safely."""


def load_report_style_context(path: Path | None = None) -> dict[str, Any]:
    """Load curated report style guidance as non-evidence context."""

    style_path = _resolve_style_context_path(path)
    if not style_path.exists():
        raise GptInterpretiveAssistError(f"Missing report style context: {style_path}")
    content = style_path.read_text(encoding="utf-8").strip()
    if not content:
        raise GptInterpretiveAssistError(f"Report style context is empty: {style_path}")
    lowered = content.lower()
    required_markers = ("style guidance only", "not project evidence", "must not be cited")
    missing = [marker for marker in required_markers if marker not in lowered]
    if missing:
        raise GptInterpretiveAssistError(
            "Report style context must explicitly state it is style-only non-evidence: "
            + ", ".join(missing)
        )
    return {
        "schema_version": STYLE_CONTEXT_SCHEMA_VERSION,
        "kind": "style_guidance_only",
        "not_project_evidence": True,
        "must_not_be_cited": True,
        "source_path": _style_context_display_path(style_path),
        "content": content,
        "sections": _style_context_sections(content),
        "content_hash": _digest({"content": content, "schema_version": STYLE_CONTEXT_SCHEMA_VERSION}),
    }


def gpt_interpretive_assist_status(
    project_dir: Path,
    *,
    model: str | None = None,
    style_context_path: Path | None = None,
) -> dict[str, Any]:
    """Return UI-safe GPT readiness and planned call status without calling GPT."""

    project_dir = project_dir.resolve()
    load_project_env()
    env_enabled = gpt_drafting_enabled()
    api_key_configured = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    resolved_model = resolve_gpt_model(model)
    if not env_enabled:
        status = "disabled"
        message = "Set GPT_DRAFTING=1 to enable explicit GPT Interpretive Assist."
    elif not api_key_configured:
        status = "env_not_configured"
        message = "GPT_DRAFTING is enabled but OPENAI_API_KEY is not configured."
    else:
        status = "ready"
        message = "GPT Interpretive Assist is ready for explicit draft generation."

    try:
        plan = plan_gpt_section_drafts(project_dir, model=resolved_model, style_context_path=style_context_path)
    except GptInterpretiveAssistError as exc:
        plan = {
            "style_context_path": str(_style_context_display_path(_resolve_style_context_path(style_context_path))),
            "eligible_sections": [],
            "planned_sections": [],
            "planned_call_count": 0,
            "skipped_sections": [{"reason": "planning_unavailable", "title": str(exc), "section_id": "", "target_id": ""}],
        }
    last_run = _load_optional_json(project_dir / GPT_INTERPRETIVE_RUN_PATH)
    return {
        "status": status,
        "message": message,
        "env_enabled": env_enabled,
        "api_key_configured": api_key_configured,
        "model": resolved_model,
        "style_context_path": str(plan.get("style_context_path", "")),
        "eligible_count": len(plan.get("eligible_sections", [])),
        "planned_call_count": int(plan.get("planned_call_count", 0)),
        "completed_call_count": int(last_run.get("completed_call_count", 0)) if isinstance(last_run, dict) else 0,
        "accepted_gpt_draft_count": int(last_run.get("accepted_gpt_draft_count", 0)) if isinstance(last_run, dict) else 0,
        "rejected_gpt_draft_count": int(last_run.get("rejected_gpt_draft_count", 0)) if isinstance(last_run, dict) else 0,
        "deterministic_fallback_count": int(last_run.get("deterministic_fallback_count", 0)) if isinstance(last_run, dict) else 0,
        "cache_hit_count": int(last_run.get("cache_hit_count", 0)) if isinstance(last_run, dict) else 0,
        "planned_sections": plan.get("planned_sections", []),
        "eligible_sections": plan.get("eligible_sections", []),
        "skipped_sections": plan.get("skipped_sections", []),
        "last_run": last_run if isinstance(last_run, dict) else {},
    }


def plan_gpt_section_drafts(
    project_dir: Path,
    *,
    model: str | None = None,
    sections: list[str] | None = None,
    max_calls: int | None = DEFAULT_MAX_CALLS,
    skip_existing: bool = True,
    source_backed_only: bool = True,
    style_context_path: Path | None = None,
) -> dict[str, Any]:
    """Plan eligible GPT draft calls without calling GPT or mutating the queue."""

    project_dir = project_dir.resolve()
    bundle = _load_planning_bundle(project_dir, model=model, style_context_path=style_context_path)
    records = _candidate_records(
        project_dir=project_dir,
        bundle=bundle,
        sections=sections,
        skip_existing=skip_existing,
        source_backed_only=source_backed_only,
    )
    eligible = [record for record in records if record["eligible"]]
    call_limit = _bounded_max_calls(max_calls)
    planned = eligible[:call_limit]
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "project_id": bundle["queue"].get("project_id"),
        "project_name": bundle["queue"].get("project_name"),
        "model": bundle["model"],
        "style_context_path": bundle["style_context"].get("source_path"),
        "eligible_sections": [_plan_row(record) for record in eligible],
        "skipped_sections": [_skip_row(record) for record in records if not record["eligible"]],
        "planned_sections": [_plan_row(record) for record in planned],
        "planned_call_count": len(planned),
        "max_calls": call_limit,
        "dry_run": True,
        "output_path": "",
    }


def draft_section_candidates(
    project_dir: Path,
    *,
    provider: str = "gpt",
    model: str | None = None,
    sections: list[str] | None = None,
    max_calls: int | None = DEFAULT_MAX_CALLS,
    dry_run: bool = False,
    skip_existing: bool = True,
    source_backed_only: bool = True,
    force_refresh: bool = False,
    style_context_path: Path | None = None,
    response_create: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Generate explicit GPT review candidates and keep all items unaccepted."""

    if provider != "gpt":
        raise GptInterpretiveAssistError("Only provider='gpt' is supported for GPT Interpretive Assist.")
    project_dir = project_dir.resolve()
    plan = plan_gpt_section_drafts(
        project_dir,
        model=model,
        sections=sections,
        max_calls=max_calls,
        skip_existing=False if force_refresh else skip_existing,
        source_backed_only=source_backed_only,
        style_context_path=style_context_path,
    )
    if dry_run:
        result = {
            **plan,
            "dry_run": True,
            "created_at": _utc_now(),
            "sections_drafted": [],
            "sections_rejected": [],
            "sections_reused_from_cache": [],
            "sections_skipped_existing": [
                item
                for item in plan["skipped_sections"]
                if item.get("reason") == "existing_gpt_draft_current"
            ],
            "completed_call_count": 0,
            "accepted_gpt_draft_count": 0,
            "rejected_gpt_draft_count": 0,
            "deterministic_fallback_count": 0,
            "cache_hit_count": 0,
            "token_usage": {},
            "output_path": str(project_dir / GPT_INTERPRETIVE_RUN_PATH),
        }
        _write_json(project_dir / GPT_INTERPRETIVE_RUN_PATH, result)
        return result

    if not gpt_drafting_enabled() and response_create is None:
        raise GptInterpretiveAssistError("Set GPT_DRAFTING=1 before running GPT Interpretive Assist.")
    if response_create is None:
        try:
            openai_api_key_required()
        except GptConfigurationError as exc:
            raise GptInterpretiveAssistError(str(exc)) from exc

    bundle = _load_planning_bundle(project_dir, model=model, style_context_path=style_context_path)
    records = _candidate_records(
        project_dir=project_dir,
        bundle=bundle,
        sections=sections,
        skip_existing=False if force_refresh else skip_existing,
        source_backed_only=source_backed_only,
    )
    selected = [record for record in records if record["eligible"]][:_bounded_max_calls(max_calls)]
    provider_instance = OpenAISectionDraftProvider(
        model=bundle["model"],
        response_create=response_create,
    )
    cache = _load_cache(project_dir)
    queue = bundle["queue"]
    cache_hits: list[dict[str, Any]] = []
    drafted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    fallbacks: list[dict[str, Any]] = []
    token_usage = _empty_token_usage()
    cached_token_usage = _empty_token_usage()
    completed_calls = 0

    for record in selected:
        request: SectionDraftRequest = record["request"]
        fingerprint = record["fingerprint"]
        cached = _cache_entry_for(cache, request.target_id, fingerprint)
        if cached and not force_refresh:
            _apply_gpt_result_to_queue_item(
                record["item"],
                generated_content=str(cached.get("generated_content", request.deterministic_content)),
                provenance=cached.get("provenance", {}) if isinstance(cached.get("provenance"), dict) else {},
                validation_issues=_dict_list(cached.get("validation_issues", [])),
                fingerprint=fingerprint,
                cached=True,
            )
            cache_hits.append(_result_row(record, status="cache_hit"))
            _add_token_usage(cached_token_usage, _token_usage_from_provenance(cached.get("provenance", {})))
            continue

        try:
            result = provider_instance.draft(request)
        except SectionDraftingError as exc:
            result = SectionDraftResult(
                content=request.deterministic_content,
                provenance={
                    "draft_provider": "openai_responses",
                    "model": bundle["model"],
                    "prompt_version": PROMPT_VERSION,
                    "gpt_output_accepted": False,
                    "warnings": ["gpt_call_failed"],
                },
                validation_issues=[
                    {
                        "severity": "warning",
                        "code": "gpt_call_failed",
                        "message": str(exc),
                    }
                ],
            )
        completed_calls += 1
        accepted = bool(result.provenance.get("gpt_output_accepted"))
        entry = _cache_entry(record, result, fingerprint, accepted=accepted)
        _set_cache_entry(cache, request.target_id, entry)
        _add_token_usage(token_usage, _token_usage_from_provenance(result.provenance))
        if accepted:
            _apply_gpt_result_to_queue_item(
                record["item"],
                generated_content=result.content,
                provenance=result.provenance,
                validation_issues=result.validation_issues,
                fingerprint=fingerprint,
                cached=False,
            )
            drafted.append(_result_row(record, status="drafted"))
        else:
            rejected.append(_result_row(record, status="rejected", validation_issues=result.validation_issues))
            fallbacks.append(_result_row(record, status="deterministic_fallback"))

    _write_cache(project_dir, cache)
    _write_queue(project_dir, queue)
    result = {
        "schema_version": RUN_SCHEMA_VERSION,
        "project_id": queue.get("project_id"),
        "project_name": queue.get("project_name"),
        "created_at": _utc_now(),
        "model": bundle["model"],
        "style_context_path": bundle["style_context"].get("source_path"),
        "dry_run": False,
        "max_calls": _bounded_max_calls(max_calls),
        "eligible_sections": [_plan_row(record) for record in selected],
        "skipped_sections": [_skip_row(record) for record in records if not record["eligible"]],
        "planned_sections": [_plan_row(record) for record in selected],
        "planned_call_count": len(selected),
        "completed_call_count": completed_calls,
        "accepted_gpt_draft_count": len(drafted) + len(cache_hits),
        "rejected_gpt_draft_count": len(rejected),
        "deterministic_fallback_count": len(fallbacks),
        "cache_hit_count": len(cache_hits),
        "sections_drafted": drafted,
        "sections_rejected": rejected,
        "sections_reused_from_cache": cache_hits,
        "sections_skipped_existing": [
            _skip_row(record)
            for record in records
            if not record["eligible"] and record.get("skip_reason") == "existing_gpt_draft_current"
        ],
        "token_usage": _clean_token_usage(token_usage),
        "cached_token_usage": _clean_token_usage(cached_token_usage),
        "output_path": str(project_dir / GPT_INTERPRETIVE_RUN_PATH),
    }
    _write_json(project_dir / GPT_INTERPRETIVE_RUN_PATH, result)
    return result


def _load_planning_bundle(project_dir: Path, *, model: str | None, style_context_path: Path | None) -> dict[str, Any]:
    try:
        queue = load_review_queue(project_dir)
        evidence = load_evidence_package(project_dir)
        context = load_project_context(project_dir)
    except (ReviewQueueError, EvidencePackageError, ProjectContextError) as exc:
        raise GptInterpretiveAssistError(str(exc)) from exc
    if queue.get("queue_mode") != "deliverable_items":
        raise GptInterpretiveAssistError("GPT Interpretive Assist requires the standard deliverable_items review queue.")
    policy = load_report_section_policy()
    matrix = load_deliverable_matrix()
    prompts = load_report_prompt_config()
    return {
        "queue": queue,
        "evidence": evidence,
        "context": context,
        "policy": policy,
        "matrix": matrix,
        "prompts": prompts,
        "model": resolve_gpt_model(model),
        "style_context": load_report_style_context(style_context_path),
    }


def _candidate_records(
    *,
    project_dir: Path,
    bundle: dict[str, Any],
    sections: list[str] | None,
    skip_existing: bool,
    source_backed_only: bool,
) -> list[dict[str, Any]]:
    requested = {value for value in (sections or []) if value}
    policies = bundle["policy"].by_section_id()
    prompt_by_key = bundle["prompts"].by_prompt_key()
    global_prompt = prompt_by_key.get(bundle["prompts"].global_prompt_key)
    cache = _load_cache(project_dir)
    records: list[dict[str, Any]] = []
    for item in _dict_list(bundle["queue"].get("items", [])):
        target_id = str(item.get("target_id") or item.get("id") or "")
        if requested and target_id not in requested and str(item.get("id", "")) not in requested:
            continue
        policy_id = _policy_id_for_target(target_id)
        policy = policies.get(policy_id)
        record: dict[str, Any] = {
            "item": item,
            "target_id": target_id,
            "section_id": policy_id,
            "title": str(item.get("title") or target_id),
            "policy": policy,
            "eligible": False,
            "skip_reason": "",
        }
        skip_reason = _eligibility_skip_reason(item, policy, source_backed_only=source_backed_only)
        if skip_reason:
            record["skip_reason"] = skip_reason
            records.append(record)
            continue
        prompt_key = _prompt_key_for_item(item)
        prompt = prompt_by_key.get(prompt_key)
        evidence = _evidence_for_item(bundle["evidence"], item, policy_id)
        request = _draft_request_for_item(
            item=item,
            policy=policy,
            evidence=evidence,
            context=bundle["context"],
            prompt=prompt,
            global_prompt=global_prompt,
            style_context=bundle["style_context"],
        )
        fingerprint = _fingerprint_for_request(
            request=request,
            policy=policy,
            style_context=bundle["style_context"],
            model=bundle["model"],
        )
        if skip_existing and _item_has_current_gpt_draft(item, fingerprint):
            record["skip_reason"] = "existing_gpt_draft_current"
            records.append(record)
            continue
        record.update(
            {
                "eligible": True,
                "request": request,
                "fingerprint": fingerprint,
                "cache_available": _cache_entry_for(cache, request.target_id, fingerprint) is not None,
            }
        )
        records.append(record)
    return records


def _eligibility_skip_reason(
    item: dict[str, Any],
    policy: ReportSectionPolicy | None,
    *,
    source_backed_only: bool,
) -> str:
    if str(item.get("type") or "") != "section_text":
        return "not_section_text"
    if str(item.get("status") or "") in TERMINAL_REVIEW_STATUSES:
        return "human_review_state_preserved"
    if policy is None:
        return "missing_section_policy"
    if policy.manual_or_reviewer_supplied:
        return "manual_or_reviewer_supplied"
    if _coerce_bool(item.get("report_body_eligible", True)) is False:
        return f"render_{str(item.get('render_decision') or 'body_ineligible')}_not_body_eligible"
    if policy.drafting_mode not in GPT_ELIGIBLE_DRAFTING_MODES or policy.gpt_readiness not in GPT_READY_VALUES:
        return "policy_not_gpt_ready"
    if "deliverable_item_stub" in _string_list(item.get("uncertainty_flags", [])) or bool(item.get("is_stub", False)):
        return "stub_or_missing_source"
    if str(item.get("analysis_extent_type") or "") == "presentation_only":
        return "presentation_only_extent"
    if source_backed_only and not _item_is_source_backed(item):
        return "not_source_backed"
    return ""


def _item_is_source_backed(item: dict[str, Any]) -> bool:
    source_refs = [
        ref
        for ref in _string_list(item.get("source_refs", []))
        if "naip" not in ref.lower() and "basemap" not in ref.lower() and "imagery" not in ref.lower()
    ]
    if source_refs:
        return True
    assumptions = item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {}
    source_gap = _dict_list(assumptions.get("source_gap_status", []))
    statuses = {str(record.get("status", "")) for record in source_gap}
    return bool(statuses.intersection({"provided_locally", "local_materialized", "downloaded", "available"}))


def _draft_request_for_item(
    *,
    item: dict[str, Any],
    policy: ReportSectionPolicy,
    evidence: dict[str, Any],
    context: dict[str, Any],
    prompt: Any,
    global_prompt: Any,
    style_context: dict[str, Any],
) -> SectionDraftRequest:
    return SectionDraftRequest(
        section_id=_policy_id_for_target(str(item.get("target_id") or item.get("id") or "")),
        target_id=str(item.get("target_id") or item.get("id") or ""),
        section_type=str(item.get("target_type") or item.get("type") or "section_text"),
        title=str(item.get("title") or item.get("id") or ""),
        purpose=str(_prompt_value(prompt, "section_instruction") or "Draft a bounded report section candidate."),
        resource_category=str(item.get("resource_category") or policy.source_category),
        deterministic_content=str(item.get("generated_content") or ""),
        related_finding_ids=_string_list(item.get("related_finding_ids", [])),
        related_table_ids=_string_list(item.get("related_table_ids", [])),
        related_figure_ids=_string_list(item.get("related_figure_ids", [])),
        source_refs=_string_list(item.get("source_refs", [])),
        evidence_bundle=evidence,
        extent_metadata=_extent_metadata_from_item(item),
        validation_issues=_dict_list(item.get("validation_issues", [])),
        project_context=context,
        matrix_target=item.get("assumptions", {}).get("matrix_target", {}) if isinstance(item.get("assumptions"), dict) else {},
        prompt_key=_prompt_key_for_item(item),
        prompt=_prompt_summary(prompt),
        global_prompt=_prompt_summary(global_prompt),
        allowed_inputs=_dedupe([*_prompt_list(global_prompt, "allowed_inputs"), *_prompt_list(prompt, "allowed_inputs")]),
        citation_policy={
            "global": _prompt_value(global_prompt, "citation_policy") or {},
            "section": _prompt_value(prompt, "citation_policy") or {},
        },
        section_policy=asdict(policy),
        style_context=style_context,
    )


def _evidence_for_item(evidence_package: dict[str, Any], item: dict[str, Any], policy_id: str) -> dict[str, Any]:
    for ref in _string_list(item.get("evidence_refs", [])):
        if not ref.startswith("section_evidence:"):
            continue
        evidence = section_evidence_for(evidence_package, ref.split(":", 1)[1])
        if evidence:
            return evidence
    for section_id in (str(item.get("target_id") or ""), policy_id):
        evidence = section_evidence_for(evidence_package, section_id)
        if evidence:
            return evidence
    return {}


def _fingerprint_for_request(
    *,
    request: SectionDraftRequest,
    policy: ReportSectionPolicy,
    style_context: dict[str, Any],
    model: str,
) -> dict[str, str]:
    evidence_payload = {
        "section_id": request.section_id,
        "target_id": request.target_id,
        "related_ids": {
            "finding_ids": request.related_finding_ids,
            "table_ids": request.related_table_ids,
            "figure_ids": request.related_figure_ids,
            "source_refs": request.source_refs,
        },
        "extent_metadata": request.extent_metadata,
        "evidence": request.evidence_bundle,
    }
    prompt_contract = {
        "prompt": request.prompt,
        "global_prompt": request.global_prompt,
        "allowed_inputs": request.allowed_inputs,
        "citation_policy": request.citation_policy,
        "purpose": request.purpose,
        "prompt_key": request.prompt_key,
    }
    prompt_contract_hash = _digest(prompt_contract)
    return {
        "fingerprint_key": _digest(
            {
                "section_id": request.section_id,
                "evidence": evidence_payload,
                "section_policy": asdict(policy),
                "prompt_contract_hash": prompt_contract_hash,
                "style_context_hash": style_context.get("content_hash"),
                "prompt_version": PROMPT_VERSION,
                "model": model,
            }
        ),
        "evidence_payload_hash": _digest(evidence_payload),
        "section_policy_hash": _digest(asdict(policy)),
        "prompt_contract_hash": prompt_contract_hash,
        "style_context_hash": str(style_context.get("content_hash") or ""),
        "prompt_version": PROMPT_VERSION,
        "model": model,
    }


def _apply_gpt_result_to_queue_item(
    item: dict[str, Any],
    *,
    generated_content: str,
    provenance: dict[str, Any],
    validation_issues: list[dict[str, Any]],
    fingerprint: dict[str, str],
    cached: bool,
) -> None:
    now = _utc_now()
    item["generated_content"] = generated_content
    item["status"] = "needs_review"
    item["export_eligible"] = False
    item["updated_at"] = now
    item["uncertainty_flags"] = _dedupe([*_string_list(item.get("uncertainty_flags", [])), "gpt_interpretive_assist"])
    item["validation_issues"] = _dedupe_issues([*_dict_list(item.get("validation_issues", [])), *validation_issues])
    item.setdefault("provenance", {})
    if not isinstance(item["provenance"], dict):
        item["provenance"] = {}
    item["provenance"]["gpt_interpretive_assist"] = {
        "draft_provider": provenance.get("draft_provider", "openai_responses"),
        "model": provenance.get("model", fingerprint["model"]),
        "prompt_version": provenance.get("prompt_version", PROMPT_VERSION),
        "gpt_output_accepted": True,
        "cached": cached,
        "fingerprint": fingerprint,
        "source_refs_used": provenance.get("source_refs_used", []),
        "table_refs_used": provenance.get("table_refs_used", []),
        "figure_refs_used": provenance.get("figure_refs_used", []),
        "token_usage": _token_usage_from_provenance(provenance),
        "generated_at": provenance.get("generated_at", now),
        "review_before_export": True,
    }


def _cache_entry(
    record: dict[str, Any],
    result: SectionDraftResult,
    fingerprint: dict[str, str],
    *,
    accepted: bool,
) -> dict[str, Any]:
    provenance = dict(result.provenance)
    return {
        "section_id": record["request"].section_id,
        "target_id": record["target_id"],
        "title": record["title"],
        "fingerprint": fingerprint,
        "fingerprint_key": fingerprint["fingerprint_key"],
        "evidence_payload_hash": fingerprint["evidence_payload_hash"],
        "section_policy_hash": fingerprint["section_policy_hash"],
        "prompt_contract_hash": fingerprint["prompt_contract_hash"],
        "style_context_hash": fingerprint["style_context_hash"],
        "prompt_version": fingerprint["prompt_version"],
        "model": fingerprint["model"],
        "generated_content": result.content,
        "validation_status": "accepted" if accepted else "rejected",
        "validation_issues": result.validation_issues,
        "warnings": provenance.get("warnings", []),
        "source_refs_used": provenance.get("source_refs_used", []),
        "table_refs_used": provenance.get("table_refs_used", []),
        "figure_refs_used": provenance.get("figure_refs_used", []),
        "token_usage": _token_usage_from_provenance(provenance),
        "provenance": provenance,
        "created_at": _utc_now(),
    }


def _load_cache(project_dir: Path) -> dict[str, Any]:
    cache_path = project_dir / GPT_INTERPRETIVE_CACHE_PATH
    if not cache_path.exists():
        return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}, "rejected_entries": {}, "updated_at": ""}
    data = _load_optional_json(cache_path)
    if data.get("schema_version") != CACHE_SCHEMA_VERSION or not isinstance(data.get("entries"), dict):
        return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}, "rejected_entries": {}, "updated_at": ""}
    if not isinstance(data.get("rejected_entries"), dict):
        data["rejected_entries"] = {}
    return data


def _write_cache(project_dir: Path, cache: dict[str, Any]) -> None:
    cache["schema_version"] = CACHE_SCHEMA_VERSION
    cache["updated_at"] = _utc_now()
    _write_json(project_dir / GPT_INTERPRETIVE_CACHE_PATH, cache)


def _cache_entry_for(cache: dict[str, Any], section_id: str, fingerprint: dict[str, str]) -> dict[str, Any] | None:
    entries = cache.get("entries", {})
    if not isinstance(entries, dict):
        return None
    entry = entries.get(section_id)
    if not isinstance(entry, dict):
        return None
    if entry.get("fingerprint_key") != fingerprint.get("fingerprint_key"):
        return None
    if entry.get("validation_status") != "accepted":
        return None
    return entry


def _set_cache_entry(cache: dict[str, Any], section_id: str, entry: dict[str, Any]) -> None:
    if entry.get("validation_status") == "accepted":
        entries = cache.setdefault("entries", {})
        if isinstance(entries, dict):
            entries[section_id] = entry
        return
    rejected_entries = cache.setdefault("rejected_entries", {})
    if not isinstance(rejected_entries, dict):
        return
    records = rejected_entries.setdefault(section_id, [])
    if not isinstance(records, list):
        records = []
    records.insert(0, entry)
    rejected_entries[section_id] = records[:10]


def _item_has_current_gpt_draft(item: dict[str, Any], fingerprint: dict[str, str]) -> bool:
    provenance = item.get("provenance", {}) if isinstance(item.get("provenance"), dict) else {}
    gpt = provenance.get("gpt_interpretive_assist", {}) if isinstance(provenance.get("gpt_interpretive_assist"), dict) else {}
    current = gpt.get("fingerprint", {}) if isinstance(gpt.get("fingerprint"), dict) else {}
    return current.get("fingerprint_key") == fingerprint.get("fingerprint_key")


def _plan_row(record: dict[str, Any]) -> dict[str, Any]:
    fingerprint = record.get("fingerprint", {}) if isinstance(record.get("fingerprint"), dict) else {}
    return {
        "section_id": record.get("section_id", ""),
        "target_id": record.get("target_id", ""),
        "title": record.get("title", ""),
        "extent_policy": getattr(record.get("policy"), "extent_policy", ""),
        "visual_extent_class": getattr(record.get("policy"), "visual_extent_class", ""),
        "source_refs": _string_list(record.get("item", {}).get("source_refs", [])) if isinstance(record.get("item"), dict) else [],
        "cache_available": bool(record.get("cache_available", False)),
        "fingerprint_key": fingerprint.get("fingerprint_key", ""),
    }


def _skip_row(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "section_id": record.get("section_id", ""),
        "target_id": record.get("target_id", ""),
        "title": record.get("title", ""),
        "reason": record.get("skip_reason", ""),
    }


def _result_row(
    record: dict[str, Any],
    *,
    status: str,
    validation_issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    row = _plan_row(record)
    row["status"] = status
    row["validation_issues"] = validation_issues or []
    return row


def _policy_id_for_target(target_id: str) -> str:
    if target_id.startswith("wetlands-waterbodies-") and target_id != "wetlands-waterbodies-alternative-detail":
        return "wetlands-waterbodies-alternative-detail"
    return target_id


def _prompt_key_for_item(item: dict[str, Any]) -> str:
    assumptions = item.get("assumptions", {}) if isinstance(item.get("assumptions"), dict) else {}
    prompt = assumptions.get("prompt_contract", {}) if isinstance(assumptions.get("prompt_contract"), dict) else {}
    matrix_target = assumptions.get("matrix_target", {}) if isinstance(assumptions.get("matrix_target"), dict) else {}
    return str(prompt.get("prompt_key") or matrix_target.get("prompt_key") or "")


def _extent_metadata_from_item(item: dict[str, Any]) -> dict[str, Any]:
    extent_fields = (
        "query_extent_type",
        "query_distance",
        "query_units",
        "analysis_extent_type",
        "table_extent_type",
        "list_extent_type",
        "figure_extent_type",
        "render_extent_type",
        "render_extent_is_presentation_only",
        "interpretation_scope_label",
        "source_selection_reason",
        "extent_policy_version",
    )
    return {key: item[key] for key in extent_fields if key in item}


def _prompt_summary(prompt: Any) -> dict[str, Any]:
    if prompt is None:
        return {}
    if is_dataclass(prompt):
        return {
            "prompt_key": getattr(prompt, "prompt_key", ""),
            "target_ids": list(getattr(prompt, "target_ids", [])),
            "section_instruction": getattr(prompt, "section_instruction", ""),
            "allowed_inputs": list(getattr(prompt, "allowed_inputs", [])),
            "citation_policy": dict(getattr(prompt, "citation_policy", {})),
            "prohibited_claims": list(getattr(prompt, "prohibited_claims", [])),
            "output_style": dict(getattr(prompt, "output_style", {})),
        }
    return dict(prompt) if isinstance(prompt, dict) else {}


def _prompt_value(prompt: Any, key: str) -> Any:
    if prompt is None:
        return None
    if isinstance(prompt, dict):
        return prompt.get(key)
    return getattr(prompt, key, None)


def _prompt_list(prompt: Any, key: str) -> list[str]:
    return _string_list(_prompt_value(prompt, key))


def _write_queue(project_dir: Path, queue: dict[str, Any]) -> None:
    queue["updated_at"] = _utc_now()
    queue["item_count"] = len(_dict_list(queue.get("items", [])))
    output_path = Path(str(queue.get("output_path") or project_dir / REVIEW_QUEUE_PATH))
    output_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")


def _resolve_style_context_path(path: Path | None) -> Path:
    if path is None:
        return (repo_root() / DEFAULT_STYLE_CONTEXT_PATH).resolve()
    return path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()


def _style_context_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return str(path)


def _style_context_sections(content: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_title = "General"
    current_lines: list[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append({"title": current_title, "guidance": "\n".join(current_lines).strip()})
            current_title = line[3:].strip()
            current_lines = []
        elif line.strip() and not line.startswith("# "):
            current_lines.append(line)
    if current_lines:
        sections.append({"title": current_title, "guidance": "\n".join(current_lines).strip()})
    return sections[:20]


def _bounded_max_calls(value: int | None) -> int:
    if value is None:
        return DEFAULT_MAX_CALLS
    return max(0, min(25, int(value)))


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GptInterpretiveAssistError(f"Invalid JSON artifact: {path}: {exc}") from exc
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for issue in issues:
        key = (str(issue.get("severity", "")), str(issue.get("code", "")), str(issue.get("message", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result


def _empty_token_usage() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def _token_usage_from_provenance(value: Any) -> dict[str, int]:
    provenance = value if isinstance(value, dict) else {}
    usage = provenance.get("token_usage", {})
    if not isinstance(usage, dict):
        return {}
    result: dict[str, int] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        token_count = usage.get(key)
        if isinstance(token_count, int) and token_count >= 0:
            result[key] = token_count
    return result


def _add_token_usage(total: dict[str, int], usage: dict[str, int]) -> None:
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        total[key] = int(total.get(key, 0)) + int(usage.get(key, 0))


def _clean_token_usage(usage: dict[str, int]) -> dict[str, int]:
    return {key: value for key, value in usage.items() if value}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
