"""Section drafting providers for deterministic and GPT-backed report copy."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from .env_config import GptConfigurationError, gpt_draft_max_payload_bytes, openai_api_key_required, resolve_gpt_model


PROMPT_VERSION = "report-section-drafting-v2"
OUTPUT_SCHEMA_VERSION = "report-section-draft-schema-v1"
MAX_GPT_STRING_LENGTH = 2000
MAX_GPT_LIST_ITEMS = 20
COMPACT_FINDING_LIMIT = 4
COMPACT_TABLE_ROW_LIMIT = 2
COMPACT_FIGURE_LIMIT = 4
DISALLOWED_PAYLOAD_KEYS = {
    "geometry",
    "coordinates",
    "features",
    "feature",
    "featurecollection",
    "geojson",
    "raw_geojson",
    "raw_features",
    "__geo_interface__",
}
BULK_SOURCE_EXTENSIONS = (
    ".shp",
    ".shx",
    ".dbf",
    ".prj",
    ".cpg",
    ".qix",
    ".sbn",
    ".sbx",
    ".gdb",
    ".tif",
    ".tiff",
    ".zip",
)
PROHIBITED_PATTERNS = {
    "preferred alternative": r"\bpreferred alternative\b",
    "best alternative": r"\bbest (route|trail|alternative|option)\b",
    "worst alternative": r"\bworst (route|trail|alternative|option)\b",
    "ranking": r"\brank(?:ed|ing)?\b",
    "score": r"\bscor(?:e|ed|ing)\b",
    "reject": r"\breject(?:ed|s|ing)?\b",
    "select": r"\bselect(?:ed|s|ing)?\b",
    "final determination": r"\bfinal (determination|finding|conclusion)\b",
    "jurisdictional certainty": r"\b(jurisdictionally determined|jurisdictional determination|jurisdictional certainty|jurisdictional evidence)\b",
    "field verified": r"\b(field[- ]verified|field verification (?:was )?(?:completed|conducted|confirmed))\b",
    "no impact conclusion": r"\bno impacts?\b",
    "cleared conclusion": r"\bcleared\b",
    "approval conclusion": r"\bapproved\b",
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
    payload = {
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
            "Mirror the environmental constraints report shape with concise paragraphs, not standalone duplicate headings.",
            "Cite IDs that appear in related_ids or the evidence bundle.",
            "Mention related finding, table, figure, and source IDs only when they are supplied.",
            "Do not rank, score, select, reject, recommend, or identify a preferred alternative.",
            "Do not state field verification, jurisdictional determinations, approvals, no-impact conclusions, or final conclusions.",
            "Preserve missing, gated, failed, and manual-source caveats.",
        ],
    }
    return _bounded_payload(payload)


def _system_prompt() -> str:
    return (
        "You draft pre-review environmental constraints report sections from structured evidence. "
        "Do not invent facts. Do not recommend, rank, select, reject, or identify a preferred alternative. "
        "Do not include duplicate section headings. Keep language objective, screening-level, and reviewer-editable. "
        "Return only valid JSON."
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


def _bounded_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = _sanitize_for_gpt(payload)
    if _payload_size(sanitized) <= gpt_draft_max_payload_bytes():
        return sanitized
    compact = _compact_payload(sanitized)
    if _payload_size(compact) <= gpt_draft_max_payload_bytes():
        return compact
    raise SectionDraftingError(
        "GPT section drafting payload exceeds GPT_DRAFT_MAX_PAYLOAD_BYTES after safe compaction."
    )


def _sanitize_for_gpt(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.strip().lower() in DISALLOWED_PAYLOAD_KEYS:
                continue
            clean[key_text] = _sanitize_for_gpt(item)
        return clean
    if isinstance(value, list):
        return [_sanitize_for_gpt(item) for item in value[:MAX_GPT_LIST_ITEMS]]
    if isinstance(value, str):
        return _safe_string(value)
    return value


def _safe_string(value: str) -> str:
    stripped = value.strip()
    if _looks_like_local_source_path(stripped):
        return "[local source path withheld]"
    if len(stripped) > MAX_GPT_STRING_LENGTH:
        return stripped[:MAX_GPT_STRING_LENGTH].rstrip() + "..."
    return stripped


def _looks_like_local_source_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    lowered = normalized.lower()
    if "/sources/" in lowered or lowered.startswith("sources/"):
        return True
    if lowered.startswith(("http://", "https://")):
        return False
    path_like = ":/" in lowered or "/" in lowered or "\\" in value
    return path_like and any(lowered.endswith(extension) for extension in BULK_SOURCE_EXTENSIONS)


def _compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    compact = dict(payload)
    evidence = compact.get("evidence")
    if isinstance(evidence, dict):
        compact["evidence"] = _compact_evidence(evidence)
    return compact


def _compact_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "section_id": evidence.get("section_id"),
        "resource_category": evidence.get("resource_category"),
        "evidence_classes": evidence.get("evidence_classes", []),
        "source_refs": evidence.get("source_refs", []),
        "sources": evidence.get("sources", []),
        "validation_issues": evidence.get("validation_issues", [])[:10]
        if isinstance(evidence.get("validation_issues"), list)
        else [],
    }
    findings = evidence.get("findings", [])
    if isinstance(findings, list):
        compact["findings"] = [
            {
                "finding_id": finding.get("finding_id"),
                "title": finding.get("title"),
                "finding_type": finding.get("finding_type"),
                "source_refs": finding.get("source_refs", []),
                "content": _safe_string(str(finding.get("content", "")))[:600],
            }
            for finding in findings[:COMPACT_FINDING_LIMIT]
            if isinstance(finding, dict)
        ]
    tables = evidence.get("tables", [])
    if isinstance(tables, list):
        compact["tables"] = [
            {
                "table_id": table.get("table_id"),
                "title": table.get("title"),
                "table_type": table.get("table_type"),
                "row_count": table.get("row_count", 0),
                "columns": table.get("columns", []),
                "rows_preview": table.get("rows_preview", [])[:COMPACT_TABLE_ROW_LIMIT]
                if isinstance(table.get("rows_preview"), list)
                else [],
            }
            for table in tables
            if isinstance(table, dict)
        ]
    figures = evidence.get("figures", [])
    if isinstance(figures, list):
        compact["figures"] = [
            {
                "figure_id": figure.get("figure_id"),
                "title": figure.get("title"),
                "figure_type": figure.get("figure_type"),
                "source_refs": figure.get("source_refs", []),
                "has_image": figure.get("has_image", False),
            }
            for figure in figures[:COMPACT_FIGURE_LIMIT]
            if isinstance(figure, dict)
        ]
    deliverable_tables = evidence.get("deliverable_tables", [])
    if isinstance(deliverable_tables, list):
        compact["deliverable_tables"] = [
            {
                "table_id": table.get("table_id"),
                "table_number": table.get("table_number"),
                "title": table.get("title"),
                "row_count": table.get("row_count", 0),
                "columns": table.get("columns", []),
                "rows_preview": table.get("rows_preview", [])[:COMPACT_TABLE_ROW_LIMIT]
                if isinstance(table.get("rows_preview"), list)
                else [],
                "is_stub": table.get("is_stub", False),
                "source_refs": table.get("source_refs", []),
            }
            for table in deliverable_tables
            if isinstance(table, dict)
        ]
    deliverable_figures = evidence.get("deliverable_figures", [])
    if isinstance(deliverable_figures, list):
        compact["deliverable_figures"] = [
            {
                "figure_id": figure.get("figure_id"),
                "figure_number": figure.get("figure_number"),
                "title": figure.get("title"),
                "has_image": figure.get("has_image", False),
                "is_stub": figure.get("is_stub", False),
                "source_refs": figure.get("source_refs", []),
                "review_status": figure.get("review_status"),
            }
            for figure in deliverable_figures[:COMPACT_FIGURE_LIMIT]
            if isinstance(figure, dict)
        ]
    if isinstance(evidence.get("row_summaries"), list):
        compact["row_summaries"] = evidence["row_summaries"][:COMPACT_TABLE_ROW_LIMIT]
    if isinstance(evidence.get("figure_availability"), dict):
        compact["figure_availability"] = evidence["figure_availability"]
    if isinstance(evidence.get("source_gap_status"), list):
        compact["source_gap_status"] = evidence["source_gap_status"][:8]
    return _sanitize_for_gpt(compact)


def _payload_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


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
    allowed_table_ids = set(request.related_table_ids)
    allowed_table_ids.update(_evidence_ids(request.evidence_bundle, ("tables", "deliverable_tables"), "table_id"))
    allowed_figure_ids = set(request.related_figure_ids)
    allowed_figure_ids.update(_evidence_ids(request.evidence_bundle, ("figures", "deliverable_figures"), "figure_id"))
    allowed_source_refs = set(request.source_refs)
    allowed_source_refs.update(_evidence_source_refs(request.evidence_bundle))
    citation_checks = [
        ("cited_finding_ids", set(request.related_finding_ids), "unknown_finding_id"),
        ("cited_table_ids", allowed_table_ids, "unknown_table_id"),
        ("cited_figure_ids", allowed_figure_ids, "unknown_figure_id"),
        ("cited_source_refs", allowed_source_refs, "unknown_source_ref"),
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


def _evidence_ids(evidence: dict[str, Any], keys: tuple[str, ...], id_field: str) -> set[str]:
    ids: set[str] = set()
    if not isinstance(evidence, dict):
        return ids
    for key in keys:
        value = evidence.get(key, [])
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, dict) and item.get(id_field):
                ids.add(str(item[id_field]))
    return ids


def _evidence_source_refs(evidence: dict[str, Any]) -> set[str]:
    refs = set(_string_list(evidence.get("source_refs", []))) if isinstance(evidence, dict) else set()
    if not isinstance(evidence, dict):
        return refs
    for key in ("sources", "tables", "figures", "deliverable_tables", "deliverable_figures"):
        value = evidence.get(key, [])
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, dict):
                refs.update(_string_list(item.get("source_refs", [])))
                refs.update(_string_list(item.get("source_ids", [])))
    return refs


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
