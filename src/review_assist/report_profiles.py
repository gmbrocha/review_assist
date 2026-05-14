"""Report profile loading and project default resolution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .projects import ProjectManifest
from .source_catalog import repo_root


REPORT_PROFILES_PATH = Path("config/report_profiles.json")


class ReportProfileError(RuntimeError):
    """Raised when report profile configuration is missing or invalid."""


@dataclass(frozen=True)
class ReportProfile:
    profile_id: str
    name: str
    description: str
    required_categories: list[str]
    optional_categories: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportProfile":
        profile_id = _required_string(data, "profile_id", "report profile")
        required = _string_list(data, "required_categories", profile_id)
        optional = _string_list(data, "optional_categories", profile_id)
        overlap = sorted(set(required).intersection(optional))
        if overlap:
            raise ReportProfileError(f"Report profile '{profile_id}' has categories marked required and optional: {', '.join(overlap)}")
        return cls(
            profile_id=profile_id,
            name=_required_string(data, "name", profile_id),
            description=str(data.get("description", "")),
            required_categories=required,
            optional_categories=optional,
        )


@dataclass(frozen=True)
class ReportProfileConfig:
    profile_version: str
    project_type_defaults: dict[str, str]
    profiles: dict[str, ReportProfile]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportProfileConfig":
        raw_defaults = data.get("project_type_defaults", {})
        if not isinstance(raw_defaults, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in raw_defaults.items()):
            raise ReportProfileError("Report profile config 'project_type_defaults' must be an object of strings.")

        raw_profiles = data.get("profiles", [])
        if not isinstance(raw_profiles, list) or not raw_profiles:
            raise ReportProfileError("Report profile config requires a non-empty list field named 'profiles'.")

        profiles: dict[str, ReportProfile] = {}
        for item in raw_profiles:
            if not isinstance(item, dict):
                raise ReportProfileError("Each report profile entry must be an object.")
            profile = ReportProfile.from_dict(item)
            if profile.profile_id in profiles:
                raise ReportProfileError(f"Duplicate report profile id: {profile.profile_id}")
            profiles[profile.profile_id] = profile

        missing_defaults = sorted({profile_id for profile_id in raw_defaults.values() if profile_id not in profiles})
        if missing_defaults:
            raise ReportProfileError(f"Project type defaults reference unknown report profile(s): {', '.join(missing_defaults)}")

        return cls(
            profile_version=str(data.get("profile_version", "")),
            project_type_defaults=dict(raw_defaults),
            profiles=profiles,
        )


def load_report_profile_config(path: Path | None = None) -> ReportProfileConfig:
    config_file = path or repo_root() / REPORT_PROFILES_PATH
    if not config_file.exists():
        raise ReportProfileError(f"Missing report profile config: {config_file}")
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportProfileError(f"Invalid report profile JSON: {config_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReportProfileError(f"Report profile config must be a JSON object: {config_file}")
    return ReportProfileConfig.from_dict(data)


def resolve_report_profile(manifest: ProjectManifest, config: ReportProfileConfig | None = None) -> ReportProfile:
    config = config or load_report_profile_config()
    profile_id = manifest.report_profile or config.project_type_defaults.get(manifest.project_type)
    if not profile_id:
        raise ReportProfileError(f"No report profile configured for project type '{manifest.project_type}'.")
    profile = config.profiles.get(profile_id)
    if profile is None:
        raise ReportProfileError(f"Unknown report profile '{profile_id}' for project '{manifest.project_id}'.")
    return profile


def _required_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReportProfileError(f"{context} requires a non-empty '{key}'.")
    return value


def _string_list(data: dict[str, Any], key: str, context: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ReportProfileError(f"Report profile '{context}' requires string list '{key}'.")
    return list(value)
