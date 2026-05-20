"""Deliverable matrix and report prompt contract loading."""

from __future__ import annotations

import json
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .source_catalog import repo_root


DELIVERABLE_MATRIX_PATH = Path("config/deliverable_section_matrix.json")
REPORT_PROMPTS_PATH = Path("config/report_generation_prompts.json")
REQUIRED_STUB_TEXT = "Empty stub for future implements whenever source data is accessible."
SUPPORTED_SECTION_TARGET_TYPES = {
    "front_matter",
    "section",
    "subsection",
    "dynamic_subsection_template",
    "attachment",
}
CANONICAL_GLOBAL_GUARDRAILS = {
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
}


class DeliverableMatrixError(RuntimeError):
    """Raised when the deliverable matrix is missing or invalid."""


class ReportPromptConfigError(RuntimeError):
    """Raised when the report prompt config is missing or invalid."""


class ReportSectionPolicyConfigError(RuntimeError):
    """Raised when report section policy config is missing or invalid."""


@dataclass(frozen=True)
class SectionTarget:
    target_id: str
    target_type: str
    section_number: str | None
    title: str
    heading_level: int | None
    section_order: float
    export_group: str
    resource_category: str
    required: bool
    prompt_key: str
    source_categories: list[str]
    table_refs: list[str]
    figure_refs: list[str]
    attachment_refs: list[str]
    dynamic_children: dict[str, Any] | None
    stub_when_missing: bool
    review_item_type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SectionTarget":
        target_id = _required_string(data, "target_id", "section target", DeliverableMatrixError)
        target_type = _required_string(data, "target_type", target_id, DeliverableMatrixError)
        if target_type not in SUPPORTED_SECTION_TARGET_TYPES:
            raise DeliverableMatrixError(f"Section target '{target_id}' has unsupported target_type '{target_type}'.")

        heading_level = _optional_int(data.get("heading_level"), "heading_level", target_id)
        if heading_level is not None and heading_level not in {1, 2, 3, 4}:
            raise DeliverableMatrixError(f"Section target '{target_id}' heading_level must be 1 through 4 or null.")

        dynamic_children = data.get("dynamic_children")
        if dynamic_children is not None and not isinstance(dynamic_children, dict):
            raise DeliverableMatrixError(f"Section target '{target_id}' dynamic_children must be an object or null.")

        return cls(
            target_id=target_id,
            target_type=target_type,
            section_number=_optional_string(data.get("section_number"), "section_number", target_id, DeliverableMatrixError),
            title=_required_string(data, "title", target_id, DeliverableMatrixError),
            heading_level=heading_level,
            section_order=_required_number(data, "section_order", target_id, DeliverableMatrixError),
            export_group=_required_string(data, "export_group", target_id, DeliverableMatrixError),
            resource_category=_required_string(data, "resource_category", target_id, DeliverableMatrixError),
            required=_required_bool(data, "required", target_id, DeliverableMatrixError),
            prompt_key=_required_string(data, "prompt_key", target_id, DeliverableMatrixError),
            source_categories=_string_list(data.get("source_categories", []), "source_categories", target_id, DeliverableMatrixError),
            table_refs=_string_list(data.get("table_refs", []), "table_refs", target_id, DeliverableMatrixError),
            figure_refs=_string_list(data.get("figure_refs", []), "figure_refs", target_id, DeliverableMatrixError),
            attachment_refs=_string_list(data.get("attachment_refs", []), "attachment_refs", target_id, DeliverableMatrixError),
            dynamic_children=dynamic_children,
            stub_when_missing=_required_bool(data, "stub_when_missing", target_id, DeliverableMatrixError),
            review_item_type=_required_string(data, "review_item_type", target_id, DeliverableMatrixError),
        )


@dataclass(frozen=True)
class TableTarget:
    target_id: str
    table_number: int
    title: str
    section_target_id: str
    columns: list[str]
    required: bool
    source_categories: list[str]
    stub_when_missing: bool
    review_item_type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], table_number: int) -> "TableTarget":
        target_id = _required_string(data, "target_id", "table target", DeliverableMatrixError)
        return cls(
            target_id=target_id,
            table_number=table_number,
            title=_required_string(data, "title", target_id, DeliverableMatrixError),
            section_target_id=_required_string(data, "section_target_id", target_id, DeliverableMatrixError),
            columns=_string_list(data.get("columns", []), "columns", target_id, DeliverableMatrixError, allow_empty=False),
            required=_required_bool(data, "required", target_id, DeliverableMatrixError),
            source_categories=_string_list(data.get("source_categories", []), "source_categories", target_id, DeliverableMatrixError),
            stub_when_missing=_required_bool(data, "stub_when_missing", target_id, DeliverableMatrixError),
            review_item_type=_required_string(data, "review_item_type", target_id, DeliverableMatrixError),
        )


@dataclass(frozen=True)
class FigureTarget:
    target_id: str
    figure_number: int
    title: str
    section_target_id: str
    source_categories: list[str]
    required: bool
    stub_when_missing: bool
    review_item_type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], figure_number: int) -> "FigureTarget":
        target_id = _required_string(data, "target_id", "figure target", DeliverableMatrixError)
        return cls(
            target_id=target_id,
            figure_number=figure_number,
            title=_required_string(data, "title", target_id, DeliverableMatrixError),
            section_target_id=_required_string(data, "section_target_id", target_id, DeliverableMatrixError),
            source_categories=_string_list(data.get("source_categories", []), "source_categories", target_id, DeliverableMatrixError),
            required=_required_bool(data, "required", target_id, DeliverableMatrixError),
            stub_when_missing=_required_bool(data, "stub_when_missing", target_id, DeliverableMatrixError),
            review_item_type=_required_string(data, "review_item_type", target_id, DeliverableMatrixError),
        )


@dataclass(frozen=True)
class AttachmentTarget:
    target_id: str
    attachment_letter: str
    title: str
    section_target_id: str
    required: bool
    stub_when_missing: bool
    review_item_type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], attachment_letter: str) -> "AttachmentTarget":
        target_id = _required_string(data, "target_id", "attachment target", DeliverableMatrixError)
        return cls(
            target_id=target_id,
            attachment_letter=attachment_letter,
            title=_required_string(data, "title", target_id, DeliverableMatrixError),
            section_target_id=_required_string(data, "section_target_id", target_id, DeliverableMatrixError),
            required=_required_bool(data, "required", target_id, DeliverableMatrixError),
            stub_when_missing=_required_bool(data, "stub_when_missing", target_id, DeliverableMatrixError),
            review_item_type=_required_string(data, "review_item_type", target_id, DeliverableMatrixError),
        )


@dataclass(frozen=True)
class DeliverableMatrixConfig:
    matrix_version: str
    profile_id: str
    title: str
    description: str
    source_documents: list[str]
    stub_text: str
    section_targets: list[SectionTarget]
    table_targets: list[TableTarget]
    figure_targets: list[FigureTarget]
    attachment_targets: list[AttachmentTarget]
    numbering_policy: dict[str, Any]
    review_policy: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeliverableMatrixConfig":
        stub_text = _required_string(data, "stub_text", "deliverable matrix", DeliverableMatrixError)
        if stub_text != REQUIRED_STUB_TEXT:
            raise DeliverableMatrixError("Deliverable matrix stub_text does not match the canonical required stub text.")

        raw_sections = _object_list(data.get("section_targets"), "section_targets", "deliverable matrix", DeliverableMatrixError)
        raw_tables = _object_list(data.get("table_targets"), "table_targets", "deliverable matrix", DeliverableMatrixError)
        raw_figures = _object_list(data.get("figure_targets"), "figure_targets", "deliverable matrix", DeliverableMatrixError)
        raw_attachments = _object_list(data.get("attachment_targets"), "attachment_targets", "deliverable matrix", DeliverableMatrixError)

        sections = sorted([SectionTarget.from_dict(item) for item in raw_sections], key=lambda item: (item.section_order, item.target_id))
        tables = [TableTarget.from_dict(item, index) for index, item in enumerate(raw_tables, start=1)]
        figures = [FigureTarget.from_dict(item, index) for index, item in enumerate(raw_figures, start=1)]
        letters = string.ascii_uppercase
        attachments = [AttachmentTarget.from_dict(item, letters[index - 1]) for index, item in enumerate(raw_attachments, start=1)]

        config = cls(
            matrix_version=_required_string(data, "matrix_version", "deliverable matrix", DeliverableMatrixError),
            profile_id=_required_string(data, "profile_id", "deliverable matrix", DeliverableMatrixError),
            title=_required_string(data, "title", "deliverable matrix", DeliverableMatrixError),
            description=str(data.get("description", "")),
            source_documents=_string_list(data.get("source_documents", []), "source_documents", "deliverable matrix", DeliverableMatrixError),
            stub_text=stub_text,
            section_targets=sections,
            table_targets=tables,
            figure_targets=figures,
            attachment_targets=attachments,
            numbering_policy=_dict_field(data.get("numbering_policy"), "numbering_policy", DeliverableMatrixError),
            review_policy=_dict_field(data.get("review_policy"), "review_policy", DeliverableMatrixError),
        )
        config._validate()
        return config

    def by_section_id(self) -> dict[str, SectionTarget]:
        return {target.target_id: target for target in self.section_targets}

    def by_table_id(self) -> dict[str, TableTarget]:
        return {target.target_id: target for target in self.table_targets}

    def by_figure_id(self) -> dict[str, FigureTarget]:
        return {target.target_id: target for target in self.figure_targets}

    def by_attachment_id(self) -> dict[str, AttachmentTarget]:
        return {target.target_id: target for target in self.attachment_targets}

    def _validate(self) -> None:
        _ensure_unique([target.target_id for target in self.section_targets], "section target", DeliverableMatrixError)
        _ensure_unique([target.target_id for target in self.table_targets], "table target", DeliverableMatrixError)
        _ensure_unique([target.target_id for target in self.figure_targets], "figure target", DeliverableMatrixError)
        _ensure_unique([target.target_id for target in self.attachment_targets], "attachment target", DeliverableMatrixError)
        _ensure_unique(
            [
                *[target.target_id for target in self.section_targets],
                *[target.target_id for target in self.table_targets],
                *[target.target_id for target in self.figure_targets],
                *[target.target_id for target in self.attachment_targets],
            ],
            "deliverable target",
            DeliverableMatrixError,
        )

        if len(self.table_targets) != 4:
            raise DeliverableMatrixError("Deliverable matrix must define exactly 4 table targets.")
        if len(self.figure_targets) != 15:
            raise DeliverableMatrixError("Deliverable matrix must define exactly 15 figure targets.")
        if len(self.attachment_targets) != 3:
            raise DeliverableMatrixError("Deliverable matrix must define exactly 3 attachment targets.")

        section_ids = set(self.by_section_id())
        table_ids = set(self.by_table_id())
        figure_ids = set(self.by_figure_id())
        attachment_ids = set(self.by_attachment_id())

        for target in self.section_targets:
            if target.required and not target.stub_when_missing:
                raise DeliverableMatrixError(f"Required section target '{target.target_id}' must define stub_when_missing.")
            for table_ref in target.table_refs:
                if table_ref not in table_ids:
                    raise DeliverableMatrixError(f"Section target '{target.target_id}' references unknown table target '{table_ref}'.")
            for figure_ref in target.figure_refs:
                if figure_ref not in figure_ids:
                    raise DeliverableMatrixError(f"Section target '{target.target_id}' references unknown figure target '{figure_ref}'.")
            for attachment_ref in target.attachment_refs:
                if attachment_ref not in attachment_ids:
                    raise DeliverableMatrixError(f"Section target '{target.target_id}' references unknown attachment target '{attachment_ref}'.")

        for table in self.table_targets:
            if table.section_target_id not in section_ids:
                raise DeliverableMatrixError(f"Table target '{table.target_id}' references unknown section target '{table.section_target_id}'.")
            if table.required and not table.stub_when_missing:
                raise DeliverableMatrixError(f"Required table target '{table.target_id}' must define stub_when_missing.")

        for figure in self.figure_targets:
            if figure.section_target_id not in section_ids:
                raise DeliverableMatrixError(f"Figure target '{figure.target_id}' references unknown section target '{figure.section_target_id}'.")
            if figure.required and not figure.stub_when_missing:
                raise DeliverableMatrixError(f"Required figure target '{figure.target_id}' must define stub_when_missing.")

        for attachment in self.attachment_targets:
            if attachment.section_target_id not in section_ids:
                raise DeliverableMatrixError(f"Attachment target '{attachment.target_id}' references unknown section target '{attachment.section_target_id}'.")
            if attachment.required and not attachment.stub_when_missing:
                raise DeliverableMatrixError(f"Required attachment target '{attachment.target_id}' must define stub_when_missing.")

        dynamic = self.by_section_id().get("wetlands-waterbodies-alternative-detail")
        if dynamic is None or dynamic.target_type != "dynamic_subsection_template":
            raise DeliverableMatrixError("Deliverable matrix requires dynamic wetlands/waterbodies comparison-unit subsection template.")


@dataclass(frozen=True)
class ReportPrompt:
    prompt_key: str
    target_ids: list[str]
    system_prompt: str
    section_instruction: str
    allowed_inputs: list[str]
    required_stub_text: str
    prohibited_claims: list[str]
    citation_policy: dict[str, Any]
    output_style: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportPrompt":
        prompt_key = _required_string(data, "prompt_key", "report prompt", ReportPromptConfigError)
        required_stub_text = _required_string(data, "required_stub_text", prompt_key, ReportPromptConfigError)
        if required_stub_text != REQUIRED_STUB_TEXT:
            raise ReportPromptConfigError(f"Report prompt '{prompt_key}' does not use the canonical required stub text.")
        return cls(
            prompt_key=prompt_key,
            target_ids=_string_list(data.get("target_ids", []), "target_ids", prompt_key, ReportPromptConfigError, allow_empty=False),
            system_prompt=_required_string(data, "system_prompt", prompt_key, ReportPromptConfigError),
            section_instruction=_required_string(data, "section_instruction", prompt_key, ReportPromptConfigError),
            allowed_inputs=_string_list(data.get("allowed_inputs", []), "allowed_inputs", prompt_key, ReportPromptConfigError, allow_empty=False),
            required_stub_text=required_stub_text,
            prohibited_claims=_string_list(data.get("prohibited_claims", []), "prohibited_claims", prompt_key, ReportPromptConfigError, allow_empty=False),
            citation_policy=_dict_field(data.get("citation_policy"), "citation_policy", ReportPromptConfigError),
            output_style=_dict_field(data.get("output_style"), "output_style", ReportPromptConfigError),
        )


@dataclass(frozen=True)
class ReportPromptConfig:
    prompt_version: str
    profile_id: str
    required_stub_text: str
    global_prompt_key: str
    prompts: list[ReportPrompt]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportPromptConfig":
        required_stub_text = _required_string(data, "required_stub_text", "report prompt config", ReportPromptConfigError)
        if required_stub_text != REQUIRED_STUB_TEXT:
            raise ReportPromptConfigError("Report prompt config required_stub_text does not match the canonical required stub text.")
        raw_prompts = _object_list(data.get("prompts"), "prompts", "report prompt config", ReportPromptConfigError)
        prompts = [ReportPrompt.from_dict(item) for item in raw_prompts]
        config = cls(
            prompt_version=_required_string(data, "prompt_version", "report prompt config", ReportPromptConfigError),
            profile_id=_required_string(data, "profile_id", "report prompt config", ReportPromptConfigError),
            required_stub_text=required_stub_text,
            global_prompt_key=_required_string(data, "global_prompt_key", "report prompt config", ReportPromptConfigError),
            prompts=prompts,
        )
        config._validate()
        return config

    def by_prompt_key(self) -> dict[str, ReportPrompt]:
        return {prompt.prompt_key: prompt for prompt in self.prompts}

    def _validate(self) -> None:
        _ensure_unique([prompt.prompt_key for prompt in self.prompts], "report prompt", ReportPromptConfigError)
        prompts = self.by_prompt_key()
        global_prompt = prompts.get(self.global_prompt_key)
        if global_prompt is None:
            raise ReportPromptConfigError(f"Report prompt config global_prompt_key '{self.global_prompt_key}' is missing.")
        if global_prompt.target_ids != ["global"]:
            raise ReportPromptConfigError("Global report prompt must target only 'global'.")
        global_guardrails = " ".join(global_prompt.prohibited_claims).lower()
        missing_guardrails = sorted(guardrail for guardrail in CANONICAL_GLOBAL_GUARDRAILS if guardrail not in global_guardrails)
        if missing_guardrails:
            raise ReportPromptConfigError(f"Global report prompt is missing guardrail(s): {', '.join(missing_guardrails)}")


def load_deliverable_matrix(path: Path | None = None) -> DeliverableMatrixConfig:
    config_file = path or repo_root() / DELIVERABLE_MATRIX_PATH
    data = _load_json_object(config_file, "deliverable matrix", DeliverableMatrixError)
    return DeliverableMatrixConfig.from_dict(data)


def load_report_prompt_config(path: Path | None = None) -> ReportPromptConfig:
    config_file = path or repo_root() / REPORT_PROMPTS_PATH
    data = _load_json_object(config_file, "report prompt config", ReportPromptConfigError)
    return ReportPromptConfig.from_dict(data)


def validate_deliverable_contract(
    matrix_path: Path | None = None,
    prompt_path: Path | None = None,
) -> DeliverableMatrixConfig:
    matrix = load_deliverable_matrix(matrix_path)
    prompts = load_report_prompt_config(prompt_path)
    _validate_matrix_prompt_refs(matrix, prompts)
    _validate_report_section_policy_refs(matrix)
    return matrix


def table_targets(config: DeliverableMatrixConfig) -> list[TableTarget]:
    return list(config.table_targets)


def figure_targets(config: DeliverableMatrixConfig) -> list[FigureTarget]:
    return list(config.figure_targets)


def attachment_targets(config: DeliverableMatrixConfig) -> list[AttachmentTarget]:
    return list(config.attachment_targets)


def _validate_matrix_prompt_refs(matrix: DeliverableMatrixConfig, prompts: ReportPromptConfig) -> None:
    prompt_by_key = prompts.by_prompt_key()
    missing_prompt_keys = sorted({target.prompt_key for target in matrix.section_targets if target.prompt_key not in prompt_by_key})
    if missing_prompt_keys:
        raise DeliverableMatrixError(f"Deliverable matrix references missing report prompt key(s): {', '.join(missing_prompt_keys)}")

    section_ids = set(matrix.by_section_id())
    invalid_target_refs: list[str] = []
    for prompt in prompts.prompts:
        for target_id in prompt.target_ids:
            if target_id != "global" and target_id not in section_ids:
                invalid_target_refs.append(f"{prompt.prompt_key}->{target_id}")
    if invalid_target_refs:
        raise ReportPromptConfigError(f"Report prompts reference unknown matrix target(s): {', '.join(sorted(invalid_target_refs))}")


def _validate_report_section_policy_refs(matrix: DeliverableMatrixConfig) -> None:
    from .report_section_policy import ReportSectionPolicyError, validate_report_section_policy

    try:
        validate_report_section_policy(matrix=matrix)
    except ReportSectionPolicyError as exc:
        raise ReportSectionPolicyConfigError(str(exc)) from exc


def _load_json_object(path: Path, label: str, error_type: type[RuntimeError]) -> dict[str, Any]:
    if not path.exists():
        raise error_type(f"Missing {label}: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise error_type(f"Invalid {label} JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise error_type(f"{label.title()} must be a JSON object: {path}")
    return data


def _required_string(data: dict[str, Any], key: str, context: str, error_type: type[RuntimeError]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise error_type(f"{context} requires a non-empty '{key}'.")
    return value


def _optional_string(value: Any, key: str, context: str, error_type: type[RuntimeError]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise error_type(f"{context} requires '{key}' to be a string or null.")
    return value


def _required_bool(data: dict[str, Any], key: str, context: str, error_type: type[RuntimeError]) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise error_type(f"{context} requires boolean '{key}'.")
    return value


def _optional_int(value: Any, key: str, context: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise DeliverableMatrixError(f"{context} requires integer '{key}' or null.")
    return value


def _required_number(data: dict[str, Any], key: str, context: str, error_type: type[RuntimeError]) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise error_type(f"{context} requires numeric '{key}'.")
    return value


def _string_list(
    value: Any,
    key: str,
    context: str,
    error_type: type[RuntimeError],
    *,
    allow_empty: bool = True,
) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise error_type(f"{context} requires string list '{key}'.")
    if not allow_empty and not value:
        raise error_type(f"{context} requires non-empty string list '{key}'.")
    return list(value)


def _object_list(value: Any, key: str, context: str, error_type: type[RuntimeError]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise error_type(f"{context} requires a non-empty list field named '{key}'.")
    if not all(isinstance(item, dict) for item in value):
        raise error_type(f"{context} field '{key}' must contain only objects.")
    return list(value)


def _dict_field(value: Any, key: str, error_type: type[RuntimeError]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise error_type(f"Config requires object field '{key}'.")
    return dict(value)


def _ensure_unique(values: list[str], label: str, error_type: type[RuntimeError]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise error_type(f"Duplicate {label} id(s): {', '.join(sorted(duplicates))}")
