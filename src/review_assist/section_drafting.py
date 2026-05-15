"""Section drafting providers for deterministic and GPT-backed report copy."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from .env_config import GptConfigurationError, openai_api_key_required, resolve_gpt_model


PROMPT_VERSION = "report-section-drafting-v1"
OUTPUT_SCHEMA_VERSION = "report-section-draft-schema-v1"
PROHIBITED_PATTERNS = {
    "preferred alternative": r"\bpreferred alternative\b",
    "best alternative": r"\bbest (route|trail|alternative|option)\b",
    "worst alternative": r"\bworst (route|trail|alternative|option)\b",
    "ranking": r"\brank(?:ed|ing)?\b",
    "score": r"\bscor(?:e|ed|ing)\b",
    "reject": r"\breject(?:ed|s|ing)?\b",
    "select": r"\bselect(?:ed|s|ing)?\b",
    "final determination": r"\bfinal determination\b",
    "jurisdictional certainty": r"\bjurisdictional\b",
    "field verified": r"\bfield[- ]verified\b",
}


class SectionDraftingError(RuntimeError):
    """Raised when GPT-backed section drafting cannot complete."""


@dataclass(frozen=True)
class SectionDraftRequest:
    section_id: str
    section_type: str
    title: str
    purpose: str
    resource_category: str
    deterministic_content: str
    related_finding_ids: list[str] = field(default_factory=list)
    related_table_ids: list[str] = field(default_factory=list)
    related_figure_ids: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    visual_slots: list[str] = field(default_factory=list)
    table_slots: list[str] = field(default_factory=list)
    evidence_bundle: dict[str, Any] = field(default_factory=dict)
    validation_issues: list[dict[str, Any]] = field(default_factory=list)
    project_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SectionDraftResult:
    content: str
    provenance: dict[str, Any]
    validation_issues: list[dict[str, Any]] = field(default_factory=list)


class SectionDraftProvider(Protocol):
    provider_id: str

    def draft(self, request: SectionDraftRequest) -> SectionDraftResult:
        """Return draft section content for review."""


class DeterministicSectionDraftProvider:
    provider_id = "deterministic"

    def draft(self, request: SectionDraftRequest) -> SectionDraftResult:
        return SectionDraftResult(
            content=request.deterministic_content,
            provenance={
                "draft_provider": self.provider_id,
                "prompt_version": "",
                "model": "",
                "response_schema_version": "",
            },
        )


class OpenAISectionDraftProvider:
    provider_id = "openai_responses"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        response_create: Callable[..., Any] | None = None,
    ) -> None:
        self.model = resolve_gpt_model(model)
        self._api_key = api_key
        self._response_create = response_create

    def draft(self, request: SectionDraftRequest) -> SectionDraftResult:
        payload = _request_payload(request)
        raw_output = self._create_response(payload)
        parsed = _parse_response_payload(raw_output)
        content = str(parsed.get("draft_content") or "").strip()
        if not content:
            return _rejected_result(
                request,
                provider_id=self.provider_id,
                model=self.model,
                input_payload=payload,
                output_payload=parsed,
                issue_code="gpt_empty_output",
                message="GPT returned no draft_content; deterministic content was retained.",
            )

        validation_issues = _validate_gpt_output(request, parsed, content)
        if any(issue.get("severity") == "error" for issue in validation_issues):
            return _rejected_result(
                request,
                provider_id=self.provider_id,
                model=self.model,
                input_payload=payload,
                output_payload=parsed,
                issue_code="gpt_output_rejected",
                message="GPT output was rejected by citation or language guardrails; deterministic content was retained.",
                extra_issues=validation_issues,
            )

        return SectionDraftResult(
            content=content,
            provenance=_gpt_provenance(
                provider_id=self.provider_id,
                model=self.model,
                input_payload=payload,
                output_payload=parsed,
                output_content=content,
                accepted=True,
            ),
            validation_issues=validation_issues,
        )

    def _create_response(self, payload: dict[str, Any]) -> Any:
        if self._response_create is not None:
            return self._response_create(model=self.model, payload=payload, schema=_output_schema())

        api_key = self._api_key or openai_api_key_required()
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise SectionDraftingError("GPT drafting requires the openai package to be installed.") from exc

        client = OpenAI(api_key=api_key)
        try:
            return client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": json.dumps(payload, sort_keys=True)},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "review_assist_report_section_draft",
                        "schema": _output_schema(),
                        "strict": True,
                    }
                },
            )
        except Exception as exc:  # pragma: no cover - API errors vary by SDK/service.
            raise SectionDraftingError(f"GPT section drafting failed: {exc}") from exc


def default_section_draft_provider() -> SectionDraftProvider:
    return DeterministicSectionDraftProvider()


def openai_section_draft_provider(*, model: str | None = None) -> SectionDraftProvider:
    return OpenAISectionDraftProvider(model=model)


def _request_payload(request: SectionDraftRequest) -> dict[str, Any]:
    return {
        "prompt_version": PROMPT_VERSION,
        "section": {
            "section_id": request.section_id,
            "section_type": request.section_type,
            "title": request.title,
            "purpose": request.purpose,
            "resource_category": request.resource_category,
        },
        "project": {
            "project_id": request.project_context.get("project_id"),
            "project_name": request.project_context.get("project_name"),
            "project_type": request.project_context.get("project_type"),
            "report_profile": request.project_context.get("report_profile", {}),
            "special_reviewer_instructions": request.project_context.get("special_reviewer_instructions", ""),
        },
        "deterministic_baseline": request.deterministic_content,
        "related_ids": {
            "finding_ids": request.related_finding_ids,
            "table_ids": request.related_table_ids,
            "figure_ids": request.related_figure_ids,
            "source_refs": request.source_refs,
        },
        "slots": {
            "visual_slots": request.visual_slots,
            "table_slots": request.table_slots,
        },
        "evidence": request.evidence_bundle,
        "validation_issues": request.validation_issues,
        "constraints": [
            "Draft pre-review report copy only.",
            "Use only the structured evidence provided in this request.",
            "Cite IDs that appear in related_ids or the evidence bundle.",
            "Do not rank, score, select, reject, recommend, or identify a preferred alternative.",
            "Do not state field verification, jurisdictional determinations, or final conclusions.",
            "Preserve missing, gated, failed, and manual-source caveats.",
        ],
    }


def _system_prompt() -> str:
    return (
        "You draft pre-review environmental constraints report sections from structured evidence. "
        "Do not invent facts. Do not recommend, rank, select, reject, or identify a preferred alternative. "
        "Keep language objective, screening-level, and reviewer-editable. Return only valid JSON."
    )


def _output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "draft_content",
            "cited_finding_ids",
            "cited_table_ids",
            "cited_figure_ids",
            "cited_source_refs",
            "caveats",
        ],
        "properties": {
            "draft_content": {"type": "string"},
            "cited_finding_ids": {"type": "array", "items": {"type": "string"}},
            "cited_table_ids": {"type": "array", "items": {"type": "string"}},
            "cited_figure_ids": {"type": "array", "items": {"type": "string"}},
            "cited_source_refs": {"type": "array", "items": {"type": "string"}},
            "caveats": {"type": "array", "items": {"type": "string"}},
        },
    }


def _parse_response_payload(raw_output: Any) -> dict[str, Any]:
    if isinstance(raw_output, dict):
        if "draft_content" in raw_output:
            return raw_output
        if isinstance(raw_output.get("output"), dict):
            return _parse_response_payload(raw_output["output"])
        if isinstance(raw_output.get("output_text"), str):
            return _json_object(raw_output["output_text"])
    output_text = getattr(raw_output, "output_text", None)
    if isinstance(output_text, str):
        return _json_object(output_text)
    output = getattr(raw_output, "output", None)
    text = _response_output_text(output)
    if text:
        return _json_object(text)
    raise SectionDraftingError("GPT response did not contain parseable structured output.")


def _json_object(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SectionDraftingError(f"GPT response was not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SectionDraftingError("GPT response JSON must be an object.")
    return data


def _response_output_text(output: Any) -> str:
    if not isinstance(output, list):
        return ""
    parts: list[str] = []
    for item in output:
        content = getattr(item, "content", None)
        if content is None and isinstance(item, dict):
            content = item.get("content")
        if not isinstance(content, list):
            continue
        for piece in content:
            text = getattr(piece, "text", None)
            if text is None and isinstance(piece, dict):
                text = piece.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def _validate_gpt_output(request: SectionDraftRequest, parsed: dict[str, Any], content: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    citation_checks = [
        ("cited_finding_ids", set(request.related_finding_ids), "unknown_finding_id"),
        ("cited_table_ids", set(request.related_table_ids), "unknown_table_id"),
        ("cited_figure_ids", set(request.related_figure_ids), "unknown_figure_id"),
        ("cited_source_refs", set(request.source_refs), "unknown_source_ref"),
    ]
    for field_name, allowed_values, code in citation_checks:
        for value in _string_list(parsed.get(field_name, [])):
            if allowed_values and value not in allowed_values:
                issues.append(_issue("error", code, f"GPT cited {field_name} value '{value}' that was not in the evidence bundle."))
            elif not allowed_values and value:
                issues.append(_issue("error", code, f"GPT cited {field_name} value '{value}' but no values were supplied."))

    lowered = content.lower()
    for label, pattern in PROHIBITED_PATTERNS.items():
        if re.search(pattern, lowered):
            issues.append(_issue("error", "prohibited_gpt_language", f"GPT output included prohibited {label} language."))
    return issues


def _rejected_result(
    request: SectionDraftRequest,
    *,
    provider_id: str,
    model: str,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
    issue_code: str,
    message: str,
    extra_issues: list[dict[str, Any]] | None = None,
) -> SectionDraftResult:
    issues = [_issue("warning", issue_code, message)]
    issues.extend(extra_issues or [])
    return SectionDraftResult(
        content=request.deterministic_content,
        provenance=_gpt_provenance(
            provider_id=provider_id,
            model=model,
            input_payload=input_payload,
            output_payload=output_payload,
            output_content=request.deterministic_content,
            accepted=False,
        ),
        validation_issues=issues,
    )


def _gpt_provenance(
    *,
    provider_id: str,
    model: str,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
    output_content: str,
    accepted: bool,
) -> dict[str, Any]:
    return {
        "draft_provider": provider_id,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "response_schema_version": OUTPUT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_digest": _digest(input_payload),
        "output_digest": _digest({"content": output_content, "structured": output_payload}),
        "gpt_output_accepted": accepted,
    }


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _issue(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}
