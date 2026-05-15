"""Deterministic draft finding generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constraints import CONSTRAINT_RESULTS_PATH, ConstraintAnalysisError, load_constraint_results
from .project_context import ProjectContextError, generate_project_context, load_project_context
from .source_catalog import repo_root
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set


FINDING_TEMPLATES_PATH = Path("config/finding_templates.json")
FINDINGS_PATH = Path("findings/draft_findings.json")
SPATIAL_RELATIONSHIPS_PATH = Path("intermediate/spatial_relationships.json")
DEFERRED_SOURCE_STATUSES = {"missing", "gated", "stubbed", "needs_review", "downloadable", "failed"}
SOURCE_REVIEW_STATUSES_REQUIRING_VERIFICATION = {"gated", "stubbed"}
SUPPORTED_FINDING_REVIEW_STATUSES = {
    "draft",
    "needs_review",
    "accepted",
    "edited",
    "rejected",
    "needs_verification",
    "unable_to_verify",
}
REQUIRED_FINDING_FIELDS = {
    "finding_id",
    "project_id",
    "type",
    "resource_category",
    "title",
    "summary",
    "details",
    "implication",
    "evidence_class",
    "source_ids",
    "related_record_ids",
    "assumptions",
    "provenance",
    "uncertainty_flags",
    "review_status",
}

CATEGORY_FINDING_TYPES = {
    "wetlands_waterbodies": "wetland_or_waterbody_relationship",
    "hydrography_crossings": "stream_or_hydrography_crossing",
    "land_cover_disturbance": "land_cover_or_disturbance_context",
    "soils": "soil_constraint_context",
    "species_habitat": "protected_species_or_critical_habitat_context",
    "regulated_facilities": "regulated_facility_context",
    "cultural_historic": "cultural_or_historic_review_required",
    "transportation_utilities": "utility_or_transportation_coordination",
    "community_socioeconomic": "community_context",
    "parcels_property": "parcel_or_property_review",
    "imagery_basemaps": "imagery_review_context",
    "flood_hazard": "flood_hazard_context",
}


class FindingTemplateError(RuntimeError):
    """Raised when finding template configuration is invalid."""


class FindingGenerationError(RuntimeError):
    """Raised when deterministic draft findings cannot be generated."""


@dataclass(frozen=True)
class FindingTemplate:
    finding_type: str
    resource_categories: list[str]
    title: str
    summary: str
    details: str
    implication: str
    evidence_class: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FindingTemplate":
        finding_type = _required_string(data, "finding_type", "finding template")
        categories = _string_list(data, "resource_categories", finding_type)
        if not categories:
            raise FindingTemplateError(f"{finding_type} requires at least one 'resource_categories' entry.")
        return cls(
            finding_type=finding_type,
            resource_categories=categories,
            title=_required_string(data, "title", finding_type),
            summary=_required_string(data, "summary", finding_type),
            details=_required_string(data, "details", finding_type),
            implication=_required_string(data, "implication", finding_type),
            evidence_class=_required_string(data, "evidence_class", finding_type),
        )


@dataclass(frozen=True)
class FindingTemplateConfig:
    template_version: str
    templates: dict[str, FindingTemplate]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FindingTemplateConfig":
        raw_templates = data.get("templates", [])
        if not isinstance(raw_templates, list) or not raw_templates:
            raise FindingTemplateError("Finding template config requires a non-empty list field named 'templates'.")

        templates: dict[str, FindingTemplate] = {}
        for item in raw_templates:
            if not isinstance(item, dict):
                raise FindingTemplateError("Each finding template entry must be an object.")
            template = FindingTemplate.from_dict(item)
            if template.finding_type in templates:
                raise FindingTemplateError(f"Duplicate finding template type: {template.finding_type}")
            templates[template.finding_type] = template
        return cls(template_version=str(data.get("template_version", "")), templates=templates)

    def require(self, finding_type: str) -> FindingTemplate:
        template = self.templates.get(finding_type)
        if template is None:
            raise FindingTemplateError(f"Missing finding template: {finding_type}")
        return template


def load_finding_template_config(path: Path | None = None) -> FindingTemplateConfig:
    config_file = path or repo_root() / FINDING_TEMPLATES_PATH
    if not config_file.exists():
        raise FindingTemplateError(f"Missing finding template config: {config_file}")
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FindingTemplateError(f"Invalid finding template JSON: {config_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise FindingTemplateError(f"Finding template config must be a JSON object: {config_file}")
    return FindingTemplateConfig.from_dict(data)


def generate_draft_findings(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        context = _load_or_generate_context(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
        constraints = _load_optional_constraint_results(project_dir)
        spatial = _load_optional_spatial_relationships(project_dir)
        templates = load_finding_template_config()
    except (ProjectContextError, SourceStatusError, ConstraintAnalysisError, FindingTemplateError) as exc:
        raise FindingGenerationError(str(exc)) from exc

    now = _utc_now()
    findings: list[dict[str, Any]] = []
    findings.extend(_source_status_findings(context, source_status, templates))
    if constraints is not None:
        findings.extend(_constraint_findings(context, constraints, templates))
        findings.extend(_no_mapped_constraint_findings(context, constraints, templates))
    elif spatial is not None:
        findings.extend(_spatial_relationship_findings(context, spatial, templates))
        findings.extend(_no_mapped_relationship_findings(context, spatial, templates))

    output_path = project_dir / FINDINGS_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "project_id": context["project_id"],
        "project_name": context["project_name"],
        "project_dir": str(project_dir),
        "created_at": now,
        "template_version": templates.template_version,
        "upstream_artifacts": {
            "project_context_path": context.get("context_path"),
            "source_status_path": source_status.get("output_path"),
            "constraint_results_path": constraints.get("output_path") if constraints else None,
            "spatial_relationships_path": spatial.get("output_path") if spatial else None,
        },
        "finding_count": len(findings),
        "findings": findings,
        "validation_issues": [],
        "output_path": str(output_path),
    }
    _validate_draft_findings_artifact(result, str(output_path))
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_draft_findings(project_dir: Path) -> dict[str, Any]:
    findings_path = project_dir.resolve() / FINDINGS_PATH
    if not findings_path.exists():
        raise FindingGenerationError(f"Missing draft findings artifact: {findings_path}")
    try:
        data = json.loads(findings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FindingGenerationError(f"Invalid draft findings JSON: {findings_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FindingGenerationError(f"Draft findings artifact must be a JSON object: {findings_path}")
    _validate_draft_findings_artifact(data, str(findings_path))
    return data


def _load_or_generate_context(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_context(project_dir)
    except ProjectContextError:
        return generate_project_context(project_dir)


def _load_or_generate_source_status(project_dir: Path) -> dict[str, Any]:
    source_status_path = project_dir / SOURCE_STATUS_PATH
    if source_status_path.exists():
        try:
            data = json.loads(source_status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SourceStatusError(f"Invalid source status JSON: {source_status_path}: {exc}") from exc
        if isinstance(data, dict):
            return data
        raise SourceStatusError(f"Source status artifact must be a JSON object: {source_status_path}")
    return resolve_source_status_set(project_dir)


def _load_optional_constraint_results(project_dir: Path) -> dict[str, Any] | None:
    constraint_path = project_dir / CONSTRAINT_RESULTS_PATH
    if not constraint_path.exists():
        return None
    return load_constraint_results(project_dir)


def _load_optional_spatial_relationships(project_dir: Path) -> dict[str, Any] | None:
    spatial_path = project_dir / SPATIAL_RELATIONSHIPS_PATH
    if not spatial_path.exists():
        return None
    try:
        data = json.loads(spatial_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FindingGenerationError(f"Invalid spatial relationships JSON: {spatial_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FindingGenerationError(f"Spatial relationships artifact must be a JSON object: {spatial_path}")
    return data


def _source_status_findings(
    context: dict[str, Any],
    source_status: dict[str, Any],
    templates: FindingTemplateConfig,
) -> list[dict[str, Any]]:
    template = templates.require("source_unavailable_or_deferred")
    findings: list[dict[str, Any]] = []
    for status_record in source_status.get("statuses", []):
        if not isinstance(status_record, dict):
            continue
        source_state = str(status_record.get("status", "needs_review"))
        if source_state not in DEFERRED_SOURCE_STATUSES:
            continue
        category = str(status_record.get("category", "unknown_category"))
        values = {
            "resource_category": category,
            "source_status": source_state,
            "source_name": _first(status_record.get("source_names"), category),
            "feature_label": category,
            "source_feature_label": category,
            "project_feature_label": context.get("project_name", ""),
            "spatial_relationship": source_state,
        }
        findings.append(
            _finding_record(
                project_id=str(context["project_id"]),
                finding_id=f"finding-source-unavailable-or-deferred-{_slug(category)}",
                finding_type=template.finding_type,
                resource_category=category,
                template=template,
                values=values,
                source_ids=_string_list(status_record.get("source_ids", [])),
                related_record_ids=[f"source-status:{category}"],
                assumptions={
                    "source_status": source_state,
                    "requirement": status_record.get("requirement"),
                    "desktop_screening_only": True,
                },
                provenance={
                    "artifact": "source_status_set",
                    "artifact_path": source_status.get("output_path"),
                    "category": category,
                    "source_status": source_state,
                },
                uncertainty_flags=_with_default_flag(status_record.get("uncertainty_flags", []), "desktop_screening_only"),
                review_status="needs_verification"
                if source_state in SOURCE_REVIEW_STATUSES_REQUIRING_VERIFICATION
                else "needs_review",
            )
        )
    return findings


def _constraint_findings(
    context: dict[str, Any],
    constraints: dict[str, Any],
    templates: FindingTemplateConfig,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for constraint in constraints.get("constraints", []):
        if not isinstance(constraint, dict):
            continue
        category = str(constraint.get("source_category", ""))
        finding_type = CATEGORY_FINDING_TYPES.get(category)
        if finding_type is None:
            continue
        template = templates.require(finding_type)
        constraint_id = str(constraint.get("constraint_id", "constraint"))
        values = _constraint_values(context, constraint)
        findings.append(
            _finding_record(
                project_id=str(context["project_id"]),
                finding_id=f"finding-{_slug(finding_type)}-{_slug(constraint_id)}",
                finding_type=finding_type,
                resource_category=category,
                template=template,
                values=values,
                source_ids=[str(constraint["source_id"])] if constraint.get("source_id") else [],
                related_record_ids=[constraint_id],
                assumptions={
                    "project_feature_id": constraint.get("project_feature_id"),
                    "project_geometry_role": constraint.get("project_geometry_role"),
                    "buffer_feet": constraint.get("buffer_feet"),
                    "measurements": constraint.get("measurements", {}),
                    "desktop_screening_only": True,
                },
                provenance={
                    "artifact": "constraint_results",
                    "artifact_path": constraints.get("output_path"),
                    "constraint_id": constraint_id,
                    "method": constraint.get("method"),
                    "analysis_crs": constraint.get("analysis_crs"),
                    "relationship_type": constraint.get("relationship_type"),
                },
                uncertainty_flags=["desktop_screening_only"],
                review_status="draft",
            )
        )
    return findings


def _spatial_relationship_findings(
    context: dict[str, Any],
    spatial: dict[str, Any],
    templates: FindingTemplateConfig,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relationship in spatial.get("relationships", []):
        if not isinstance(relationship, dict):
            continue
        category = str(relationship.get("source_category", ""))
        finding_type = CATEGORY_FINDING_TYPES.get(category)
        if finding_type is None:
            continue
        template = templates.require(finding_type)
        relationship_id = str(relationship.get("relationship_id", "relationship"))
        values = _relationship_values(context, relationship)
        findings.append(
            _finding_record(
                project_id=str(context["project_id"]),
                finding_id=f"finding-{_slug(finding_type)}-{_slug(relationship_id)}",
                finding_type=finding_type,
                resource_category=category,
                template=template,
                values=values,
                source_ids=[str(relationship["source_id"])] if relationship.get("source_id") else [],
                related_record_ids=[relationship_id],
                assumptions={
                    "buffer_feet": relationship.get("buffer_feet"),
                    "measurements": relationship.get("measurements", {}),
                    "desktop_screening_only": True,
                },
                provenance={
                    "artifact": "spatial_relationships",
                    "artifact_path": spatial.get("output_path"),
                    "relationship_id": relationship_id,
                    "method": relationship.get("method"),
                    "analysis_crs": relationship.get("analysis_crs"),
                    "spatial_relationship": relationship.get("spatial_relationship"),
                },
                uncertainty_flags=["desktop_screening_only"],
                review_status="draft",
            )
        )
    return findings


def _no_mapped_constraint_findings(
    context: dict[str, Any],
    constraints: dict[str, Any],
    templates: FindingTemplateConfig,
) -> list[dict[str, Any]]:
    template = templates.require("no_mapped_conflict_identified")
    findings: list[dict[str, Any]] = []
    for source in constraints.get("sources", []):
        if not isinstance(source, dict):
            continue
        if source.get("status") != "analyzed" or _int_count(source.get("constraint_count", 0)) != 0:
            continue
        source_id = str(source.get("source_id", "unknown_source"))
        category = str(source.get("source_category", "constraints"))
        values = {
            "resource_category": category,
            "source_status": str(source.get("status", "analyzed")),
            "source_name": str(source.get("source_name") or source_id),
            "feature_label": str(source.get("source_name") or source_id),
            "source_feature_label": str(source.get("source_name") or source_id),
            "project_feature_label": str(context.get("project_name", "")),
            "spatial_relationship": "no_mapped_constraint",
        }
        findings.append(
            _finding_record(
                project_id=str(context["project_id"]),
                finding_id=f"finding-no-mapped-conflict-identified-{_slug(source_id)}",
                finding_type=template.finding_type,
                resource_category=category,
                template=template,
                values=values,
                source_ids=[source_id],
                related_record_ids=[f"source:{source_id}"],
                assumptions={
                    "buffer_feet": source.get("buffer_feet"),
                    "desktop_screening_only": True,
                    "source_layer_screening_only": True,
                },
                provenance={
                    "artifact": "constraint_results",
                    "artifact_path": constraints.get("output_path"),
                    "source_id": source_id,
                    "method": "geopandas_shapely_constraint_overlap_check",
                    "analysis_crs": source.get("analysis_crs"),
                },
                uncertainty_flags=["desktop_screening_only", "source_layer_screening_only"],
                review_status="draft",
            )
        )
    return findings


def _no_mapped_relationship_findings(
    context: dict[str, Any],
    spatial: dict[str, Any],
    templates: FindingTemplateConfig,
) -> list[dict[str, Any]]:
    template = templates.require("no_mapped_conflict_identified")
    findings: list[dict[str, Any]] = []
    for source in spatial.get("sources", []):
        if not isinstance(source, dict):
            continue
        if source.get("status") != "analyzed" or _int_count(source.get("relationship_count", 0)) != 0:
            continue
        source_id = str(source.get("source_id", "unknown_source"))
        category = str(source.get("source_category", "spatial_relationships"))
        values = {
            "resource_category": category,
            "source_status": str(source.get("status", "analyzed")),
            "source_name": str(source.get("source_name") or source_id),
            "feature_label": str(source.get("source_name") or source_id),
            "source_feature_label": str(source.get("source_name") or source_id),
            "project_feature_label": str(context.get("project_name", "")),
            "spatial_relationship": "no_mapped_relationship",
        }
        findings.append(
            _finding_record(
                project_id=str(context["project_id"]),
                finding_id=f"finding-no-mapped-conflict-identified-{_slug(source_id)}",
                finding_type=template.finding_type,
                resource_category=category,
                template=template,
                values=values,
                source_ids=[source_id],
                related_record_ids=[f"source:{source_id}"],
                assumptions={
                    "buffer_feet": source.get("buffer_feet"),
                    "desktop_screening_only": True,
                    "source_layer_screening_only": True,
                },
                provenance={
                    "artifact": "spatial_relationships",
                    "artifact_path": spatial.get("output_path"),
                    "source_id": source_id,
                    "method": "geopandas_shapely_local_spatial_check",
                    "analysis_crs": source.get("analysis_crs"),
                },
                uncertainty_flags=["desktop_screening_only", "source_layer_screening_only"],
                review_status="draft",
            )
        )
    return findings


def _finding_record(
    *,
    project_id: str,
    finding_id: str,
    finding_type: str,
    resource_category: str,
    template: FindingTemplate,
    values: dict[str, Any],
    source_ids: list[str],
    related_record_ids: list[str],
    assumptions: dict[str, Any],
    provenance: dict[str, Any],
    uncertainty_flags: list[str],
    review_status: str,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "project_id": project_id,
        "type": finding_type,
        "resource_category": resource_category,
        "title": _render(template.title, values),
        "summary": _render(template.summary, values),
        "details": _render(template.details, values),
        "implication": _render(template.implication, values),
        "evidence_class": template.evidence_class,
        "source_ids": source_ids,
        "related_record_ids": related_record_ids,
        "assumptions": assumptions,
        "provenance": provenance,
        "uncertainty_flags": uncertainty_flags,
        "review_status": review_status,
    }


def _relationship_values(context: dict[str, Any], relationship: dict[str, Any]) -> dict[str, Any]:
    source_name = str(relationship.get("source_name") or relationship.get("source_id") or "source layer")
    project_label = str(relationship.get("project_feature_label") or relationship.get("project_feature_index") or "project feature")
    source_label = str(relationship.get("source_feature_label") or relationship.get("source_feature_index") or "source feature")
    feature_label = source_label if source_label and source_label != "source feature" else source_name
    return {
        "resource_category": str(relationship.get("source_category", "")),
        "source_status": "provided_locally",
        "source_name": source_name,
        "feature_label": feature_label,
        "source_feature_label": source_label,
        "project_feature_label": project_label or str(context.get("project_name", "")),
        "spatial_relationship": str(relationship.get("spatial_relationship", "relationship")),
    }


def _constraint_values(context: dict[str, Any], constraint: dict[str, Any]) -> dict[str, Any]:
    source_name = str(constraint.get("source_name") or constraint.get("source_id") or "source layer")
    project_label = str(constraint.get("project_feature_name") or constraint.get("project_feature_id") or "project feature")
    source_label = str(constraint.get("source_feature_label") or constraint.get("source_feature_index") or "source feature")
    feature_label = source_label if source_label and source_label != "source feature" else source_name
    return {
        "resource_category": str(constraint.get("source_category", "")),
        "source_status": "provided_locally",
        "source_name": source_name,
        "feature_label": feature_label,
        "source_feature_label": source_label,
        "project_feature_label": project_label or str(context.get("project_name", "")),
        "spatial_relationship": str(constraint.get("relationship_type", "relationship")),
    }


def _required_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FindingTemplateError(f"{context} requires a non-empty '{key}'.")
    return value


def _validate_draft_findings_artifact(data: dict[str, Any], location: str) -> None:
    findings = data.get("findings")
    if not isinstance(findings, list):
        raise FindingGenerationError(f"Draft findings artifact requires a list field named 'findings': {location}")
    seen_ids: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            raise FindingGenerationError(f"Each draft finding must be an object: {location}")
        missing = sorted(REQUIRED_FINDING_FIELDS - set(finding))
        if missing:
            raise FindingGenerationError(f"Draft finding is missing required fields {missing}: {location}")
        finding_id = finding["finding_id"]
        if not isinstance(finding_id, str) or not finding_id.strip():
            raise FindingGenerationError(f"Draft finding requires a non-empty string finding_id: {location}")
        if finding_id in seen_ids:
            raise FindingGenerationError(f"Duplicate draft finding id '{finding_id}': {location}")
        seen_ids.add(finding_id)
        if finding["review_status"] not in SUPPORTED_FINDING_REVIEW_STATUSES:
            raise FindingGenerationError(f"Unsupported draft finding review_status '{finding['review_status']}': {location}")
        for list_field in ("source_ids", "related_record_ids", "uncertainty_flags"):
            if not isinstance(finding[list_field], list):
                raise FindingGenerationError(f"Draft finding field '{list_field}' must be a list: {location}")
        for object_field in ("assumptions", "provenance"):
            if not isinstance(finding[object_field], dict):
                raise FindingGenerationError(f"Draft finding field '{object_field}' must be an object: {location}")


def _int_count(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _string_list(value: Any, key: str | None = None, context: str | None = None) -> list[str]:
    if key is not None and isinstance(value, dict):
        raw_value = value.get(key, [])
        if not isinstance(raw_value, list) or not all(isinstance(item, str) and item.strip() for item in raw_value):
            raise FindingTemplateError(f"Finding template '{context}' requires string list '{key}'.")
        return list(raw_value)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _with_default_flag(value: Any, flag: str) -> list[str]:
    flags = _string_list(value)
    if flag not in flags:
        flags.append(flag)
    return flags


def _first(value: Any, fallback: str) -> str:
    items = _string_list(value)
    return items[0] if items else fallback


def _render(template: str, values: dict[str, Any]) -> str:
    return template.format_map(_SafeFormatDict({key: "" if value is None else value for key, value in values.items()}))


class _SafeFormatDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
