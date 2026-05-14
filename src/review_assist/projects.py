"""Project manifest loading and saving."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


MANIFEST_PATH = Path("config/project.json")


class ProjectManifestError(RuntimeError):
    """Raised when a project manifest cannot be loaded."""


@dataclass(frozen=True)
class ProjectInput:
    path: str
    role: str
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectInput":
        path = data.get("path")
        role = data.get("role")
        if not isinstance(path, str) or not path.strip():
            raise ProjectManifestError("Each project input requires a non-empty 'path'.")
        if not isinstance(role, str) or not role.strip():
            raise ProjectManifestError(f"Input '{path}' requires a non-empty 'role'.")
        description = data.get("description", "")
        return cls(path=path, role=role, description=str(description))


@dataclass(frozen=True)
class ProjectManifest:
    project_id: str
    name: str
    description: str
    project_type: str
    inputs: list[ProjectInput]
    assumptions: dict[str, Any] = field(default_factory=dict)
    special_reviewer_instructions: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectManifest":
        project_id = data.get("project_id")
        name = data.get("name")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ProjectManifestError("Project manifest requires a non-empty 'project_id'.")
        if not isinstance(name, str) or not name.strip():
            raise ProjectManifestError("Project manifest requires a non-empty 'name'.")

        raw_inputs = data.get("inputs", [])
        if not isinstance(raw_inputs, list) or not raw_inputs:
            raise ProjectManifestError("Project manifest requires at least one input.")
        for item in raw_inputs:
            if not isinstance(item, dict):
                raise ProjectManifestError("Each project input must be a JSON object.")

        raw_assumptions = data.get("assumptions", {})
        if not isinstance(raw_assumptions, dict):
            raise ProjectManifestError("Project manifest 'assumptions' must be a JSON object when present.")

        return cls(
            project_id=project_id,
            name=name,
            description=str(data.get("description", "")),
            project_type=str(data.get("project_type", "alternatives_review")),
            inputs=[ProjectInput.from_dict(item) for item in raw_inputs],
            assumptions=dict(raw_assumptions),
            special_reviewer_instructions=str(data.get("special_reviewer_instructions", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "inputs": [vars(item) for item in self.inputs],
            "assumptions": self.assumptions,
            "special_reviewer_instructions": self.special_reviewer_instructions,
        }


def load_project_manifest(project_dir: Path) -> ProjectManifest:
    manifest_file = project_dir / MANIFEST_PATH
    if not manifest_file.exists():
        raise ProjectManifestError(f"Missing project manifest: {manifest_file}")
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectManifestError(f"Invalid project manifest JSON: {manifest_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectManifestError(f"Project manifest must be a JSON object: {manifest_file}")
    return ProjectManifest.from_dict(data)


def save_project_manifest(project_dir: Path, manifest: ProjectManifest) -> Path:
    manifest_file = project_dir / MANIFEST_PATH
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
    return manifest_file
