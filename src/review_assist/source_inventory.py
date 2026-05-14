"""Source inventory and provenance artifact generation."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd

from .projects import ProjectManifestError, load_project_manifest
from .source_catalog import (
    ProjectSource,
    SourceCatalogError,
    SourceDefinition,
    load_project_source_registry,
    load_source_catalog,
    resolve_project_source_path,
)
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set


SOURCE_INVENTORY_PATH = Path("source_inventory/source_inventory.json")
REQUIRED_INVENTORY_RECORD_FIELDS = {
    "source_id",
    "name",
    "category",
    "publisher",
    "catalog",
    "project_registry",
    "source_status",
    "local_metadata",
    "metadata",
    "validation_issues",
    "uncertainty_flags",
}


class SourceInventoryError(RuntimeError):
    """Raised when source inventory generation or loading cannot complete."""


def generate_source_inventory(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        catalog = load_source_catalog()
        registry = load_project_source_registry(project_dir)
        source_status = _load_or_generate_source_status(project_dir)
    except (ProjectManifestError, SourceCatalogError, SourceStatusError) as exc:
        raise SourceInventoryError(str(exc)) from exc

    project_sources = registry.by_source_id()
    status_by_category = {
        str(item.get("category", "")): item
        for item in source_status.get("statuses", [])
        if isinstance(item, dict) and item.get("category")
    }
    source_ids = _inventory_source_ids(source_status, project_sources)
    records = [
        _inventory_record(
            project_dir=project_dir,
            source_id=source_id,
            source_definition=catalog.sources.get(source_id),
            project_source=project_sources.get(source_id),
            status_by_category=status_by_category,
        )
        for source_id in source_ids
    ]
    validation_issues = [
        issue
        for record in records
        for issue in record.get("validation_issues", [])
        if isinstance(issue, dict)
    ]

    output_path = project_dir / SOURCE_INVENTORY_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_status_path": source_status.get("output_path"),
        "record_count": len(records),
        "records": records,
        "validation_issues": validation_issues,
        "output_path": str(output_path),
    }
    _validate_source_inventory(result, str(output_path))
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_source_inventory(project_dir: Path) -> dict[str, Any]:
    inventory_path = project_dir.resolve() / SOURCE_INVENTORY_PATH
    if not inventory_path.exists():
        raise SourceInventoryError(f"Missing source inventory artifact: {inventory_path}")
    try:
        data = json.loads(inventory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceInventoryError(f"Invalid source inventory JSON: {inventory_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceInventoryError(f"Source inventory artifact must be a JSON object: {inventory_path}")
    _validate_source_inventory(data, str(inventory_path))
    return data


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


def _inventory_source_ids(source_status: dict[str, Any], project_sources: dict[str, ProjectSource]) -> list[str]:
    source_ids: set[str] = set(project_sources)
    for status_record in source_status.get("statuses", []):
        if not isinstance(status_record, dict):
            continue
        raw_source_ids = status_record.get("source_ids", [])
        if isinstance(raw_source_ids, list):
            source_ids.update(str(source_id) for source_id in raw_source_ids if str(source_id).strip())
    return sorted(source_ids)


def _inventory_record(
    *,
    project_dir: Path,
    source_id: str,
    source_definition: SourceDefinition | None,
    project_source: ProjectSource | None,
    status_by_category: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    category = source_definition.category if source_definition else ""
    status_record = status_by_category.get(category, {})
    local_metadata, validation_issues = _local_metadata(project_dir, project_source)
    uncertainty_flags = _string_list(status_record.get("uncertainty_flags", []))
    uncertainty_flags.extend(issue["code"] for issue in validation_issues if issue.get("code"))
    return {
        "source_id": source_id,
        "name": source_definition.name if source_definition else source_id,
        "category": category,
        "publisher": source_definition.publisher if source_definition else "",
        "catalog": {
            "tier": source_definition.tier if source_definition else "",
            "priority": source_definition.priority if source_definition else "",
            "access_methods": source_definition.access_methods if source_definition else [],
            "public_or_restricted": source_definition.public_or_restricted if source_definition else "",
            "geometry_type": source_definition.geometry_type if source_definition else "",
            "url": source_definition.url if source_definition else "",
            "known_limitations": source_definition.known_limitations if source_definition else "",
            "notes": source_definition.notes if source_definition else "",
        },
        "project_registry": _project_registry_metadata(project_source),
        "source_status": {
            "category_status": status_record.get("status", "not_required_for_profile") if status_record else "not_required_for_profile",
            "requirement": status_record.get("requirement", "") if status_record else "",
            "notes": status_record.get("notes", "") if status_record else "",
            "registered_source_ids": _string_list(status_record.get("registered_source_ids", [])) if status_record else [],
            "local_paths": _string_list(status_record.get("local_paths", [])) if status_record else [],
        },
        "local_metadata": local_metadata,
        "metadata": project_source.metadata if project_source else {},
        "validation_issues": validation_issues,
        "uncertainty_flags": sorted(set(uncertainty_flags)),
    }


def _project_registry_metadata(project_source: ProjectSource | None) -> dict[str, Any]:
    if project_source is None:
        return {
            "registered": False,
            "enabled": False,
            "access_method": "",
            "path": None,
            "role": "",
            "buffer_feet": None,
            "notes": "",
            "status": "not_registered",
        }
    return {
        "registered": True,
        "enabled": project_source.enabled,
        "access_method": project_source.access_method,
        "path": project_source.path,
        "role": project_source.role,
        "buffer_feet": project_source.buffer_feet,
        "notes": project_source.notes,
        "status": project_source.status,
    }


def _local_metadata(project_dir: Path, project_source: ProjectSource | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metadata = {
        "path": None,
        "exists": False,
        "readable": False,
        "crs": None,
        "bounds_wgs84": None,
        "feature_count": 0,
        "geometry_type_counts": {},
        "columns": [],
    }
    issues: list[dict[str, Any]] = []
    if project_source is None or project_source.access_method != "local_file" or not project_source.path:
        return metadata, issues

    path = resolve_project_source_path(project_dir, project_source)
    metadata["path"] = str(path) if path else project_source.path
    if path is None or not path.exists():
        if project_source.enabled:
            issues.append(_issue("warning", "missing_local_source_file", f"Missing local source file for '{project_source.source_id}'.", str(path or project_source.path)))
        return metadata, issues

    metadata["exists"] = True
    try:
        gdf = gpd.read_file(path)
    except Exception as exc:  # pragma: no cover - driver-specific exception types vary.
        if project_source.enabled:
            issues.append(
                _issue(
                    "warning",
                    "unreadable_local_source_file",
                    f"Unable to read local source file for '{project_source.source_id}': {exc}",
                    str(path),
                )
            )
        return metadata, issues

    metadata["readable"] = True
    metadata["crs"] = gdf.crs.to_string() if gdf.crs is not None else None
    metadata["columns"] = [str(column) for column in gdf.columns if str(column) != "geometry"]
    if gdf.crs is None:
        issues.append(_issue("warning", "missing_source_crs", "Source layer CRS is missing; assuming EPSG:4326 for inventory bounds.", str(path)))
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)

    gdf = gdf[~gdf.geometry.isna()]
    gdf = gdf[~gdf.geometry.is_empty]
    metadata["feature_count"] = int(len(gdf))
    metadata["geometry_type_counts"] = dict(Counter(str(geom_type) for geom_type in gdf.geometry.geom_type))
    if not gdf.empty:
        bounds = gdf.to_crs("EPSG:4326").total_bounds
        metadata["bounds_wgs84"] = {
            "west": float(bounds[0]),
            "south": float(bounds[1]),
            "east": float(bounds[2]),
            "north": float(bounds[3]),
        }
    return metadata, issues


def _issue(severity: str, code: str, message: str, location: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "location": location,
    }


def _validate_source_inventory(data: dict[str, Any], location: str) -> None:
    records = data.get("records")
    if not isinstance(records, list):
        raise SourceInventoryError(f"Source inventory requires a list field named 'records': {location}")
    seen_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise SourceInventoryError(f"Each source inventory record must be an object: {location}")
        missing = sorted(REQUIRED_INVENTORY_RECORD_FIELDS - set(record))
        if missing:
            raise SourceInventoryError(f"Source inventory record is missing required fields {missing}: {location}")
        source_id = record["source_id"]
        if not isinstance(source_id, str) or not source_id.strip():
            raise SourceInventoryError(f"Source inventory record requires a non-empty source_id: {location}")
        if source_id in seen_ids:
            raise SourceInventoryError(f"Duplicate source inventory record id '{source_id}': {location}")
        seen_ids.add(source_id)
        for object_field in ("catalog", "project_registry", "source_status", "local_metadata", "metadata"):
            if not isinstance(record[object_field], dict):
                raise SourceInventoryError(f"Source inventory field '{object_field}' must be an object: {location}")
        for list_field in ("validation_issues", "uncertainty_flags"):
            if not isinstance(record[list_field], list):
                raise SourceInventoryError(f"Source inventory field '{list_field}' must be a list: {location}")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
