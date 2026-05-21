"""Section drafting providers for deterministic and GPT-backed report copy."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from .env_config import GptConfigurationError, gpt_draft_max_payload_bytes, openai_api_key_required, resolve_gpt_model
from .report_section_policy import REQUIRED_CAVEAT_TEXT_PATTERNS


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
    "final impact conclusion": r"\bfinal (?:impact|effect)s? (?:determination|finding|conclusion)\b",
    "no effect determination": r"\bno (?:adverse )?effect\b|\bnot likely to adversely affect\b|\blikely to adversely affect\b",
    "jurisdictional certainty": r"\b(jurisdictionally determined|jurisdictional determination|jurisdictional certainty|jurisdictional evidence)\b",
    "jurisdictional wetland determination": r"\bjurisdictional (?:wetland|water|waters|determination)\b|\bwaters? of the u\.?s\.?",
    "cultural clearance or eligibility": r"\b(?:cultural|historic|archaeolog)[^.]{0,80}\b(?:clearance|cleared|eligible|eligibility|effect determination|adverse effect)\b",
    "contamination determination": r"\b(?:contamination|contaminated|cleanup|liability|phase i|recognized environmental condition|rec)\b.{0,80}\b(?:present|absent|required|obligation|determination)\b",
    "permit determination": r"\b(?:permit|permits) (?:is |are |was |were |not )?(?:required|needed|necessary)\b|\brequires? (?:a )?permit\b|\bno permit\b",
    "access mitigation construction commitment": r"\b(?:access|mitigation|construction) (?:commitment|will be provided|will occur|is required|shall)\b|\bcommit(?:ted|ment) to\b",
    "demographic impact conclusion": r"\b(?:demographic|minority|low-income|environmental justice|equity)\b.{0,80}\b(?:impact|adverse effect|disproportionate|no effect|no impact|determination)\b",
    "field verified": r"\b(field[- ]verified|field verification (?:was )?(?:completed|conducted|confirmed))\b",
    "no impact conclusion": r"\bno impacts?\b",
    "cleared conclusion": r"\bcleared\b",
    "approval conclusion": r"\bapproved\b",
}
PROCESS_LANGUAGE_PATTERNS = {
    "draft review candidate": r"\bdraft review candidate\b",
    "pre-review": r"\bpre[-/ ]review\b",
    "reviewer verification": r"\breviewer verification\b|\bfor reviewer verification\b",
    "reviewer focus": r"\breviewer focus\b",
    "related table status": r"\brelated table status\b",
}
DIRECT_IMPACT_PATTERNS = {
    "direct impact": r"\bdirect (?:project )?impact\b|\bdirectly impact(?:s|ed)?\b",
    "project impact": r"\bwill impact\b|\bwould impact\b|\bimpacts the project\b",
}
CONTEXT_ONLY_DIRECT_PROJECT_PATTERNS = {
    "direct project intersection": r"\bdirect (?:project )?(?:intersection|overlap)\b",
    "within project footprint": r"\b(?:within|inside) (?:the )?(?:project area|project footprint|project limits|project corridor|submitted project)\b",
    "intersects project footprint": r"\b(?:intersects?|overlaps?|crosses) (?:the )?(?:project area|project footprint|project limits|project corridor|submitted project)\b",
    "project impact from context": r"\b(?:would|will|may) (?:affect|impact) (?:the )?project\b",
}
MAP_PRESENTATION_OVERCLAIM_PATTERNS = {
    "shown on map as evidence": r"\b(?:shown|depicted|appears) on (?:the )?(?:map|figure) (?:means|shows|confirms|establishes|indicates|proves)\b",
    "map extent as evidence": r"\b(?:map|figure|render|rendering|collar|presentation) extent (?:means|shows|confirms|establishes|indicates|proves|is evidence of)\b",
    "map presence as intersection": r"\b(?:shown|depicted|appears) on (?:the )?(?:map|figure).{0,80}\b(?:direct|intersection|intersects?|impact|within the project)\b",
}
APE_PATTERN = r"\bape\b|\barea of potential effects?\b"
POLICY_PROHIBITED_CLAIM_PATTERNS = {
    "access commitment": PROHIBITED_PATTERNS["access mitigation construction commitment"],
    "agency approval": r"\bagency approval\b|\bapproved by (?:the )?(?:agency|agencies)\b",
    "agency clearance": r"\bagency clearance\b|\bcleared by (?:the )?(?:agency|agencies)\b|\bclearance\b",
    "airspace determination": r"\bairspace determination\b|\bairspace (?:conflict|clearance)\b",
    "alternative rejection": PROHIBITED_PATTERNS["reject"],
    "alternative selection": PROHIBITED_PATTERNS["select"],
    "approval conclusion": PROHIBITED_PATTERNS["approval conclusion"],
    "construction commitment": PROHIBITED_PATTERNS["access mitigation construction commitment"],
    "cleanup obligation": r"\bcleanup obligation\b|\bobligation to clean(?:up)?\b|\brequires cleanup\b",
    "contamination determination": PROHIBITED_PATTERNS["contamination determination"],
    "cultural determination": PROHIBITED_PATTERNS["cultural clearance or eligibility"],
    "direct impact": r"\bdirect (?:project )?impact\b|\bdirectly impact(?:s|ed)?\b|\bno (?:direct )?impact\b",
    "direct impact from nearby context": r"\bdirect (?:project )?impact\b|\bdirectly impact(?:s|ed)?\b|\bnearby .* direct impact\b",
    "demographic impact": PROHIBITED_PATTERNS["demographic impact conclusion"],
    "demographic impact conclusion": PROHIBITED_PATTERNS["demographic impact conclusion"],
    "economic impact conclusion": r"\beconomic impact conclusion\b|\beconomic impacts? (?:will|would|are)\b",
    "effect determination": r"\beffect determination\b|\bno adverse effect\b|\badverse effect\b",
    "equity determination": r"\bequity determination\b|\benvironmental justice determination\b",
    "eligibility determination": r"\beligib(?:le|ility) determination\b|\b(?:eligible|not eligible) for (?:the )?(?:national register|nrhp)\b",
    "field verification claims": PROHIBITED_PATTERNS["field verified"],
    "final impact": PROHIBITED_PATTERNS["final impact conclusion"],
    "final determination": PROHIBITED_PATTERNS["final determination"],
    "jurisdictional determinations": PROHIBITED_PATTERNS["jurisdictional certainty"],
    "liability determination": r"\bliability determination\b|\bliability\b",
    "mitigation commitment": PROHIBITED_PATTERNS["access mitigation construction commitment"],
    "no concern": r"\bno concerns?\b",
    "no effect": r"\bno effect\b",
    "no impact": r"\bno (?:direct |indirect |project )?impacts?\b",
    "permit determination": PROHIBITED_PATTERNS["permit determination"],
    "permit not required": PROHIBITED_PATTERNS["permit determination"],
    "permit required": PROHIBITED_PATTERNS["permit determination"],
    "preferred alternative": PROHIBITED_PATTERNS["preferred alternative"],
    "ranking": PROHIBITED_PATTERNS["ranking"],
    "relocation requirement": r"\brelocation requirement\b|\brequires relocation\b|\brelocation (?:is|will be|would be) required\b",
    "scoring": PROHIBITED_PATTERNS["score"],
    "service impact": r"\bservice impacts?\b|\bservice disruption\b",
    "site absence": r"\bno (?:site|sites|properties|resources) (?:are|were) present\b|\babsence of (?:sites|resources)\b",
    "site eligibility determination": r"\beligib(?:le|ility) determination\b|\b(?:eligible|not eligible) for (?:the )?(?:national register|nrhp)\b",
    "unsupported facts": r"\bunsupported (?:fact|facts|claim|claims|assumption|assumptions)\b",
    "unsupported parent study facts": r"\bparent study\b.{0,80}\b(?:states|concludes|found|shows|documents)\b",
    "utility conflict determination": r"\butility conflict determination\b|\butility conflicts?\b|\bconflicts? with (?:the )?utilit",
    "wetland jurisdiction": PROHIBITED_PATTERNS["jurisdictional wetland determination"],
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
    target_id: str = ""
    related_finding_ids: list[str] = field(default_factory=list)
    related_table_ids: list[str] = field(default_factory=list)
    related_figure_ids: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    visual_slots: list[str] = field(default_factory=list)
    table_slots: list[str] = field(default_factory=list)
    evidence_bundle: dict[str, Any] = field(default_factory=dict)
    extent_metadata: dict[str, Any] = field(default_factory=dict)
    validation_issues: list[dict[str, Any]] = field(default_factory=list)
    project_context: dict[str, Any] = field(default_factory=dict)
    matrix_target: dict[str, Any] = field(default_factory=dict)
    prompt_key: str = ""
    prompt: dict[str, Any] = field(default_factory=dict)
    global_prompt: dict[str, Any] = field(default_factory=dict)
    allowed_inputs: list[str] = field(default_factory=list)
    citation_policy: dict[str, Any] = field(default_factory=dict)
    section_policy: dict[str, Any] = field(default_factory=dict)
    style_context: dict[str, Any] = field(default_factory=dict)


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
                "source_refs_used": list(request.source_refs),
                "table_refs_used": list(request.related_table_ids),
                "figure_refs_used": list(request.related_figure_ids),
                "limitation_notes": _request_limitation_notes(request),
                "warnings": _request_warning_codes(request),
                "extent_metadata": dict(request.extent_metadata),
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
        token_usage = _response_token_usage(raw_output)
        content = str(parsed.get("draft_content") or "").strip()
        if not content:
            return _rejected_result(
                request,
                provider_id=self.provider_id,
                model=self.model,
                input_payload=payload,
                output_payload=parsed,
                token_usage=token_usage,
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
                token_usage=token_usage,
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
                token_usage=token_usage,
                source_refs_used=_string_list(parsed.get("cited_source_refs", [])),
                table_refs_used=_string_list(parsed.get("cited_table_ids", [])),
                figure_refs_used=_string_list(parsed.get("cited_figure_ids", [])),
                limitation_notes=_string_list(parsed.get("caveats", [])),
                warnings=_request_warning_codes(request),
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
            "target_id": request.target_id or request.section_id,
            "section_type": request.section_type,
            "title": request.title,
            "purpose": request.purpose,
            "resource_category": request.resource_category,
            "prompt_key": request.prompt_key,
        },
        "matrix_target": request.matrix_target,
        "prompt_contract": {
            "global_prompt": request.global_prompt,
            "section_prompt": request.prompt,
            "allowed_inputs": request.allowed_inputs,
            "citation_policy": request.citation_policy,
        },
        "section_policy": request.section_policy,
        "style_context": request.style_context,
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
        "extent_metadata": request.extent_metadata,
        "validation_issues": request.validation_issues,
        "constraints": [
            "Produce review-candidate report prose only; do not include process labels such as draft review candidate, pre-review, reviewer verification, reviewer focus, or related table status in output content.",
            "Use only the structured evidence provided in this request.",
            "Mirror the environmental constraints report shape with concise paragraphs, not standalone duplicate headings.",
            "Cite IDs that appear in related_ids or the evidence bundle.",
            "Mention related finding, table, figure, and source IDs only when they are supplied.",
            "Do not rank, score, select, reject, recommend, or identify a preferred alternative.",
            "Do not state field verification, jurisdictional determinations, approvals, no-impact conclusions, or final conclusions.",
            "Preserve missing, gated, failed, and manual-source caveats.",
            "Use extent_metadata to choose within/near/watershed/county wording and do not upgrade context-only evidence into direct project impact language.",
            "Use style_context only for tone and structure. Do not cite it, treat it as evidence, or copy example-report facts or assumptions.",
            "Return required caveat IDs in the caveats array when section_policy supplies required_caveats.",
        ],
    }
    return _bounded_payload(payload)


def _system_prompt() -> str:
    return (
        "You draft environmental constraints report-section review candidates from structured evidence. "
        "Do not invent facts. Do not recommend, rank, select, reject, or identify a preferred alternative. "
        "Do not include duplicate section headings or process/status labels in the report content. "
        "Keep language objective, screening-level, and reviewer-editable. "
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
                "table_policy": table.get("table_policy", {}),
                "max_body_preview_rows": table.get("max_body_preview_rows"),
                "overflow_destination": table.get("overflow_destination"),
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
                "figure_policy": figure.get("figure_policy", {}),
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


def _response_token_usage(raw_output: Any) -> dict[str, int]:
    usage = raw_output.get("usage") if isinstance(raw_output, dict) else getattr(raw_output, "usage", None)
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        try:
            usage = usage.model_dump()
        except Exception:
            usage = None
    if usage is None and hasattr(usage, "dict"):
        try:
            usage = usage.dict()
        except Exception:
            usage = None
    if not isinstance(usage, dict):
        usage = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
        }
    aliases = {
        "input_tokens": ("input_tokens", "prompt_tokens"),
        "output_tokens": ("output_tokens", "completion_tokens"),
        "total_tokens": ("total_tokens",),
    }
    result: dict[str, int] = {}
    for key, candidates in aliases.items():
        for candidate in candidates:
            value = usage.get(candidate)
            if isinstance(value, int) and value >= 0:
                result[key] = value
                break
    if "total_tokens" not in result and {"input_tokens", "output_tokens"} <= set(result):
        result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    return result


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
    for label, pattern in PROCESS_LANGUAGE_PATTERNS.items():
        if re.search(pattern, lowered):
            issues.append(_issue("error", "process_language_in_gpt_output", f"GPT output included process/status language: {label}."))
    if _references_style_context_as_evidence(parsed, lowered):
        issues.append(_issue("error", "style_context_cited_as_evidence", "GPT output cited or treated the style context as project evidence."))
    if _imports_style_or_example_facts(request, lowered):
        issues.append(_issue("error", "style_context_fact_import", "GPT output appears to import example/style-context facts or assumptions."))
    if _contains_raw_or_unbounded_output(lowered):
        issues.append(_issue("error", "raw_or_unbounded_gpt_output", "GPT output included raw rows, coordinates, GeoJSON, or local/source paths."))
    issues.extend(_missing_required_caveat_issues(request, parsed, lowered))
    issues.extend(_policy_prohibited_claim_issues(request, lowered))
    if _misstates_public_cultural_context(request, lowered):
        issues.append(
            _issue(
                "error",
                "public_cultural_context_overclaimed",
                "GPT output treated public/coarse cultural context as authorized restricted cultural-resource records.",
            )
        )
    if _context_only_extent(request.extent_metadata):
        for label, pattern in DIRECT_IMPACT_PATTERNS.items():
            if re.search(pattern, lowered):
                issues.append(_issue("error", "direct_impact_language_for_context_extent", f"GPT output used {label} language for context-only extent metadata."))
        for label, pattern in CONTEXT_ONLY_DIRECT_PROJECT_PATTERNS.items():
            if re.search(pattern, lowered):
                issues.append(_issue("error", "direct_project_language_for_context_extent", f"GPT output used {label} language for context-only extent metadata."))
    for label, pattern in MAP_PRESENTATION_OVERCLAIM_PATTERNS.items():
        if re.search(pattern, lowered):
            issues.append(_issue("error", "map_extent_used_as_analysis_evidence", f"GPT output treated map presentation as analysis evidence: {label}."))
    if re.search(APE_PATTERN, lowered) and not _allows_ape_language(request):
        issues.append(_issue("error", "ape_language_requires_manual_cultural_context", "GPT output used APE language without reviewer-defined cultural context."))
    return issues


def _context_only_extent(extent_metadata: dict[str, Any]) -> bool:
    extent_type = str(extent_metadata.get("analysis_extent_type") or extent_metadata.get("list_extent_type") or "")
    return extent_type in {"nearby_context_extent", "community_context_extent", "watershed_context_extent", "county_or_regional_context_extent"}


def _allows_ape_language(request: SectionDraftRequest) -> bool:
    policy = request.section_policy if isinstance(request.section_policy, dict) else {}
    policy_category = str(policy.get("source_category", ""))
    section_text = " ".join([request.section_id, request.resource_category, policy_category]).lower()
    cultural_context = any(term in section_text for term in ("cultural", "historic", "archaeological"))
    manual_context = bool(policy.get("manual_or_reviewer_supplied")) or policy.get("drafting_mode") == "manual_reviewer_supplied_only"
    manual_context = manual_context or policy.get("activation_condition") in {
        "manual_reviewer_supplied",
        "reviewer_supplied_parent_study",
    }
    extent_type = str(request.extent_metadata.get("analysis_extent_type") or request.extent_metadata.get("list_extent_type") or "")
    manual_context = manual_context or extent_type == "manual_reviewer_supplied"
    return cultural_context and manual_context


def _references_style_context_as_evidence(parsed: dict[str, Any], lowered_content: str) -> bool:
    cited_refs = [
        *_string_list(parsed.get("cited_source_refs", [])),
        *_string_list(parsed.get("cited_table_ids", [])),
        *_string_list(parsed.get("cited_figure_ids", [])),
    ]
    if any("style" in ref.lower() or "example report" in ref.lower() for ref in cited_refs):
        return True
    evidence_patterns = (
        r"\bstyle context (?:source|evidence|shows|states|indicates|documents|cites)\b",
        r"\bexample report (?:source|evidence|shows|states|indicates|documents|cites)\b",
        r"\baccording to (?:the )?(?:style context|example report)\b",
    )
    return any(re.search(pattern, lowered_content) for pattern in evidence_patterns)


def _imports_style_or_example_facts(request: SectionDraftRequest, lowered_content: str) -> bool:
    if not request.style_context:
        return False
    return bool(
        re.search(r"\bplanning and environmental linkage\b|\bpel study\b", lowered_content)
        and request.section_id != "relationship-with-pel-study"
    )


def _contains_raw_or_unbounded_output(lowered_content: str) -> bool:
    raw_patterns = (
        r"\bgeojson\b",
        r"\braw rows?\b",
        r"\bcoordinates?\b",
        r"\bsource paths?\b",
        r"[a-z]:\\",
        r"\bsources[/\\]",
        r"[/\\]sources[/\\]",
        r"\.geojson\b|\.(?:shp|dbf|tif|tiff|gdb)\b",
    )
    return any(re.search(pattern, lowered_content) for pattern in raw_patterns)


def _policy_prohibited_claim_issues(
    request: SectionDraftRequest,
    lowered_content: str,
) -> list[dict[str, str]]:
    policy = request.section_policy if isinstance(request.section_policy, dict) else {}
    issues: list[dict[str, str]] = []
    seen: set[str] = set()
    for claim in _string_list(policy.get("prohibited_claims", [])):
        normalized = claim.strip().lower().replace("_", " ")
        if not normalized or normalized.startswith("inherit"):
            continue
        pattern = POLICY_PROHIBITED_CLAIM_PATTERNS.get(normalized) or _literal_claim_pattern(normalized)
        if pattern and re.search(pattern, lowered_content) and normalized not in seen:
            seen.add(normalized)
            issues.append(
                _issue(
                    "error",
                    "policy_prohibited_claim",
                    f"GPT output included section-policy prohibited claim '{claim}'.",
                )
            )
    return issues


def _literal_claim_pattern(claim: str) -> str:
    words = [word for word in re.split(r"\s+", claim) if word]
    if not words:
        return ""
    return r"\b" + r"\s+".join(re.escape(word) for word in words) + r"\b"


def _missing_required_caveat_issues(
    request: SectionDraftRequest,
    parsed: dict[str, Any],
    lowered_content: str,
) -> list[dict[str, str]]:
    policy = request.section_policy if isinstance(request.section_policy, dict) else {}
    required = _string_list(policy.get("required_caveats", []))
    if not required:
        return []
    caveat_text = " ".join(_string_list(parsed.get("caveats", []))).lower()
    missing = [
        caveat
        for caveat in required
        if caveat.lower() not in caveat_text and not _caveat_present_in_content(caveat, lowered_content)
    ]
    return [
        _issue("error", "required_caveat_omitted", f"GPT output omitted required caveat '{caveat}'.")
        for caveat in missing[:5]
    ]


def _caveat_present_in_content(caveat: str, lowered_content: str) -> bool:
    pattern = REQUIRED_CAVEAT_TEXT_PATTERNS.get(caveat)
    return bool(pattern and re.search(pattern, lowered_content))


def _misstates_public_cultural_context(request: SectionDraftRequest, lowered_content: str) -> bool:
    policy_category = str(request.section_policy.get("source_category", "")) if isinstance(request.section_policy, dict) else ""
    category = str(request.resource_category or policy_category)
    if "cultural" not in category and "cultural" not in request.section_id:
        return False
    overclaim_patterns = (
        r"\bpublic (?:sources|context|records) (?:are|serve as|provide) authorized restricted\b",
        r"\bpublic (?:sources|context|records) replace\b",
        r"\breplaces? (?:mdah|shpo|tribal|agency) review\b",
        r"\bauthorized restricted records\b",
    )
    return any(re.search(pattern, lowered_content) for pattern in overclaim_patterns)


def _request_limitation_notes(request: SectionDraftRequest) -> list[str]:
    notes: list[str] = []
    extent_type = str(request.extent_metadata.get("analysis_extent_type") or request.extent_metadata.get("list_extent_type") or "")
    if extent_type in {"nearby_context_extent", "community_context_extent", "watershed_context_extent", "county_or_regional_context_extent"}:
        notes.append(f"extent_scope={extent_type}")
    if isinstance(request.evidence_bundle, dict):
        for status in request.evidence_bundle.get("source_gap_status", []):
            if isinstance(status, dict):
                category = str(status.get("category", "source"))
                state = str(status.get("status", "unknown"))
                if state not in {"provided_locally", "local_materialized", "downloaded", "available"}:
                    notes.append(f"{category}={state}")
    return notes[:8]


def _request_warning_codes(request: SectionDraftRequest) -> list[str]:
    return [
        str(issue.get("code"))
        for issue in request.validation_issues
        if isinstance(issue, dict) and issue.get("code")
    ][:12]


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
    token_usage: dict[str, int] | None,
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
            token_usage=token_usage or {},
            source_refs_used=list(request.source_refs),
            table_refs_used=list(request.related_table_ids),
            figure_refs_used=list(request.related_figure_ids),
            limitation_notes=_request_limitation_notes(request),
            warnings=_request_warning_codes(request),
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
    token_usage: dict[str, int] | None = None,
    source_refs_used: list[str] | None = None,
    table_refs_used: list[str] | None = None,
    figure_refs_used: list[str] | None = None,
    limitation_notes: list[str] | None = None,
    warnings: list[str] | None = None,
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
        "source_refs_used": source_refs_used or [],
        "table_refs_used": table_refs_used or [],
        "figure_refs_used": figure_refs_used or [],
        "limitation_notes": limitation_notes or [],
        "warnings": warnings or [],
        "token_usage": token_usage or {},
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
