"""Project input package classification artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .projects import ProjectInput, ProjectManifestError, load_project_manifest


INPUT_PACKAGE_PATH = Path("context/input_package.json")

PROJECT_GEOMETRY_EXTENSIONS = {".kml", ".kmz"}
SOURCE_LAYER_EXTENSIONS = {".geojson", ".gpkg", ".shp", ".zip"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
IMAGERY_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}

PROJECT_GEOMETRY_ROLE_TERMS = {
    "alternative",
    "alternatives",
    "boundary",
    "corridor",
    "footprint",
    "geometry",
    "location",
    "locations",
    "project_area",
    "project_boundary",
    "project_geometry",
    "project_location",
    "project_locations",
    "route",
    "routes",
    "service_area",
    "site",
    "study_area",
}
SOURCE_ROLE_TERMS = {"source", "layer", "constraint", "screening", "resource", "gis"}
AGENCY_DOCUMENT_TERMS = {"agency", "ipac", "consultation", "letter", "permit", "coordination"}
REVIEWER_NOTE_TERMS = {"note", "notes", "reviewer", "instruction", "comment", "comments"}


class InputPackageError(RuntimeError):
    """Raised when project input package classification cannot complete."""


def classify_input_package(project_dir: Path) -> dict[str, Any]:
    """Classify configured project inputs and write context/input_package.json."""

    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
    except ProjectManifestError as exc:
        raise InputPackageError(str(exc)) from exc

    records = [_input_record(project_dir, item) for item in manifest.inputs]
    validation_issues = _collect_issues(records)
    required_kmz_present = any(
        record["extension"] == ".kmz" and record["exists"] and record["classification"] == "project_geometry"
        for record in records
    )
    if not required_kmz_present:
        validation_issues.append(
            _issue(
                "warning",
                "required_kmz_missing",
                "At least one existing project-geometry KMZ input is required for the redirected workflow.",
                str(project_dir / "config" / "project.json"),
            )
        )

    project_kmz_records = [
        record
        for record in records
        if record["extension"] == ".kmz" and record["classification"] == "project_geometry"
    ]
    if len(project_kmz_records) > 1:
        validation_issues.append(
            _issue(
                "warning",
                "multiple_project_kmz_inputs",
                "Multiple project-geometry KMZ inputs were found; reviewer confirmation may be needed.",
                str(project_dir / "config" / "project.json"),
            )
        )
        roles = [str(record["manifest_role"]).strip().lower() for record in project_kmz_records]
        roles_disambiguate = len(set(roles)) == len(roles) and all(roles)
        if not roles_disambiguate:
            for record in project_kmz_records:
                record["requires_reviewer_confirmation"] = True
                issue = _issue(
                    "warning",
                    "multiple_project_kmz_inputs",
                    "This KMZ is one of multiple project-geometry KMZ inputs and needs reviewer confirmation.",
                    record["resolved_path"],
                )
                record["validation_issues"].append(issue)

    output_path = project_dir / INPUT_PACKAGE_PATH
    artifact = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "input_count": len(records),
        "required_kmz_present": required_kmz_present,
        "project_geometry_input_count": sum(1 for record in records if record["classification"] == "project_geometry"),
        "source_layer_input_count": sum(1 for record in records if record["classification"] == "source_layer"),
        "unknown_input_count": sum(1 for record in records if record["classification"] == "unknown"),
        "inputs": records,
        "validation_issues": _dedupe_issues(validation_issues + _collect_issues(records)),
        "output_path": str(output_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact


def load_input_package(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / INPUT_PACKAGE_PATH
    if not path.exists():
        raise InputPackageError(f"Missing input package artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputPackageError(f"Invalid input package JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputPackageError(f"Input package artifact must be a JSON object: {path}")
    return data


def _input_record(project_dir: Path, project_input: ProjectInput) -> dict[str, Any]:
    input_path = (project_dir / project_input.path).resolve()
    extension = input_path.suffix.lower()
    classification, confidence, requires_confirmation, notes = _classify(project_input, extension)
    issues: list[dict[str, Any]] = []
    if not input_path.exists():
        issues.append(
            _issue(
                "warning",
                "missing_project_input_file",
                f"Configured project input does not exist: {project_input.path}",
                str(input_path),
            )
        )
    if requires_confirmation and classification == "project_geometry" and extension in SOURCE_LAYER_EXTENSIONS:
        issues.append(
            _issue(
                "warning",
                "non_kmz_project_geometry_requires_confirmation",
                "Non-KMZ/KML project geometry input requires reviewer confirmation before it changes analysis bounds.",
                str(input_path),
            )
        )
    if classification == "unknown":
        issues.append(
            _issue(
                "warning",
                "unknown_project_input_classification",
                "Project input could not be confidently classified from manifest metadata and file type.",
                str(input_path),
            )
        )

    return {
        "path": project_input.path,
        "resolved_path": str(input_path),
        "exists": input_path.exists(),
        "extension": extension,
        "manifest_role": project_input.role,
        "description": project_input.description,
        "classification": classification,
        "source_id": project_input.source_id,
        "source_category": project_input.source_category,
        "confidence": confidence,
        "requires_reviewer_confirmation": requires_confirmation,
        "notes": notes,
        "validation_issues": issues,
    }


def _classify(project_input: ProjectInput, extension: str) -> tuple[str, str, bool, list[str]]:
    if project_input.source_id or project_input.source_category:
        return "source_layer", "high", False, ["Manifest source metadata identifies this as a source layer."]

    text = f"{project_input.role} {project_input.description}".lower().replace("-", "_")
    role_terms = _terms(text)
    notes: list[str] = []

    if extension in PROJECT_GEOMETRY_EXTENSIONS:
        return "project_geometry", "high", False, ["KMZ/KML without source metadata is treated as project geometry."]

    if extension in SOURCE_LAYER_EXTENSIONS:
        if role_terms & PROJECT_GEOMETRY_ROLE_TERMS:
            notes.append("Manifest role suggests project geometry, but reviewer confirmation is needed for non-KMZ/KML geometry.")
            return "project_geometry", "medium", True, notes
        if role_terms & SOURCE_ROLE_TERMS:
            return "source_layer", "medium", True, ["Manifest role suggests source data; reviewer confirmation is recommended."]
        return "unknown", "low", True, ["GIS-like input lacks source metadata or a clear project-geometry role."]

    if extension in DOCUMENT_EXTENSIONS:
        if role_terms & AGENCY_DOCUMENT_TERMS:
            return "agency_document", "medium", False, ["Role or description suggests an agency document."]
        if role_terms & REVIEWER_NOTE_TERMS:
            return "reviewer_notes", "medium", False, ["Role or description suggests reviewer notes."]
        if extension == ".txt" and role_terms & REVIEWER_NOTE_TERMS:
            return "reviewer_notes", "medium", False, ["Text input appears to contain reviewer notes."]
        return "supporting_report", "medium", False, ["Document input is treated as supporting report material."]

    if extension in IMAGERY_EXTENSIONS:
        return "imagery_or_basemap", "high", False, ["Raster/image input is treated as imagery or basemap context."]

    return "unknown", "low", True, ["File type and manifest metadata do not provide a confident classification."]


def _terms(value: str) -> set[str]:
    normalized = "".join(character if character.isalnum() or character == "_" else " " for character in value)
    raw_terms = set(normalized.split())
    raw_terms.add(value.strip())
    return raw_terms


def _collect_issues(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for record in records:
        for issue in record.get("validation_issues", []):
            if isinstance(issue, dict):
                copied = dict(issue)
                copied["input_path"] = record.get("path")
                issues.append(copied)
    return issues


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[dict[str, Any]] = []
    for issue in issues:
        key = (
            str(issue.get("code", "")),
            str(issue.get("location", "")),
            str(issue.get("message", "")),
            str(issue.get("input_path", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result


def _issue(severity: str, code: str, message: str, location: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "location": location,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
