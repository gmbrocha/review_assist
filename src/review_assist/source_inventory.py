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
from .source_acquisition import SOURCE_ACQUISITION_PATH
from .source_materialization import SOURCE_MATERIALIZATION_PATH
from .source_status import SOURCE_STATUS_PATH, SourceStatusError, resolve_source_status_set


SOURCE_INVENTORY_PATH = Path("source_inventory/source_inventory.json")
REQUIRED_INVENTORY_RECORD_FIELDS = {
    "source_id",
    "name",
    "category",
    "publisher",
    "catalog",
    "project_registry",
    "acquisition",
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
        source_acquisition = _load_optional_source_acquisition(project_dir)
        source_materialization = _load_optional_source_materialization(project_dir)
    except (ProjectManifestError, SourceCatalogError, SourceStatusError) as exc:
        raise SourceInventoryError(str(exc)) from exc

    project_sources = registry.by_source_id()
    acquisition_by_source = _acquisition_by_source_id(source_acquisition)
    materialization_by_source = _materialization_by_source_id(source_materialization)
    status_by_category = {
        str(item.get("category", "")): item
        for item in source_status.get("statuses", [])
        if isinstance(item, dict) and item.get("category")
    }
    source_detail_by_id = _source_detail_by_id(source_status)
    source_ids = _inventory_source_ids(source_status, project_sources)
    records = [
        _inventory_record(
            project_dir=project_dir,
            source_id=source_id,
            source_definition=catalog.sources.get(source_id),
            project_source=project_sources.get(source_id),
            source_acquisition=acquisition_by_source.get(source_id),
            source_materialization=materialization_by_source.get(source_id),
            status_by_category=status_by_category,
            source_detail=source_detail_by_id.get(source_id),
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
        "source_acquisition_path": source_acquisition.get("output_path") if source_acquisition else None,
        "source_materialization_path": source_materialization.get("output_path") if source_materialization else None,
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


def _source_detail_by_id(source_status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    for status_record in source_status.get("statuses", []):
        if not isinstance(status_record, dict):
            continue
        raw_details = status_record.get("source_details", [])
        if not isinstance(raw_details, list):
            continue
        for detail in raw_details:
            if not isinstance(detail, dict):
                continue
            source_id = str(detail.get("source_id") or "")
            if source_id:
                details[source_id] = detail
    return details


def _inventory_record(
    *,
    project_dir: Path,
    source_id: str,
    source_definition: SourceDefinition | None,
    project_source: ProjectSource | None,
    source_acquisition: dict[str, Any] | None,
    source_materialization: dict[str, Any] | None,
    status_by_category: dict[str, dict[str, Any]],
    source_detail: dict[str, Any] | None,
) -> dict[str, Any]:
    category = source_definition.category if source_definition else ""
    status_record = status_by_category.get(category, {})
    local_metadata, validation_issues = _local_metadata(project_dir, project_source)
    uncertainty_flags = _string_list(status_record.get("uncertainty_flags", []))
    if source_detail:
        uncertainty_flags.extend(_string_list(source_detail.get("uncertainty_flags", [])))
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
        "acquisition": _acquisition_metadata(source_acquisition),
        "materialization": _materialization_metadata(source_materialization),
        "source_status": {
            "category_status": status_record.get("status", "not_required_for_profile") if status_record else "not_required_for_profile",
            "requirement": status_record.get("requirement", "") if status_record else "",
            "notes": status_record.get("notes", "") if status_record else "",
            "registered_source_ids": _string_list(status_record.get("registered_source_ids", [])) if status_record else [],
            "local_paths": _string_list(status_record.get("local_paths", [])) if status_record else [],
            "detail_status": source_detail.get("status", "") if source_detail else "",
            "detail_notes": source_detail.get("notes", "") if source_detail else "",
            "source_need_class": source_detail.get("source_need_class", "") if source_detail else "",
            "source_need_reason": source_detail.get("source_need_reason", "") if source_detail else "",
            "satisfied_by_source_ids": _string_list(source_detail.get("satisfied_by_source_ids", [])) if source_detail else [],
        },
        "local_metadata": local_metadata,
        "metadata": project_source.metadata if project_source else {},
        "validation_issues": validation_issues,
        "uncertainty_flags": sorted(set(uncertainty_flags)),
    }


def _load_optional_source_acquisition(project_dir: Path) -> dict[str, Any] | None:
    path = project_dir / SOURCE_ACQUISITION_PATH
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceCatalogError(f"Invalid source acquisition manifest JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceCatalogError(f"Source acquisition manifest must be a JSON object: {path}")
    return data


def _load_optional_source_materialization(project_dir: Path) -> dict[str, Any] | None:
    path = project_dir / SOURCE_MATERIALIZATION_PATH
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceCatalogError(f"Invalid source materialization manifest JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceCatalogError(f"Source materialization manifest must be a JSON object: {path}")
    return data


def _acquisition_by_source_id(source_acquisition: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not source_acquisition:
        return {}
    downloads = source_acquisition.get("downloads", [])
    if not isinstance(downloads, list):
        return {}
    by_source: dict[str, dict[str, Any]] = {}
    for download in downloads:
        if not isinstance(download, dict):
            continue
        source_id = str(download.get("source_id") or "")
        if source_id:
            by_source[source_id] = download
    return by_source


def _materialization_by_source_id(source_materialization: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not source_materialization:
        return {}
    sources = source_materialization.get("sources", [])
    if not isinstance(sources, list):
        return {}
    by_source: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("source_id") or "")
        if source_id:
            by_source[source_id] = source
    return by_source


def _acquisition_metadata(source_acquisition: dict[str, Any] | None) -> dict[str, Any]:
    if not source_acquisition:
        return {
            "status": "not_acquired",
            "source_url": "",
            "service_url": "",
            "layer_id": None,
            "layers": [],
            "access_date": "",
            "output_path": None,
            "feature_count": 0,
            "checksum_sha256": "",
            "source_limitations": "",
            "warnings": [],
        }
    return {
        "status": source_acquisition.get("status", ""),
        "source_url": source_acquisition.get("source_url", ""),
        "service_url": source_acquisition.get("service_url", ""),
        "layer_id": source_acquisition.get("layer_id"),
        "layers": _string_list_of_objects(source_acquisition.get("layers", [])),
        "access_date": source_acquisition.get("access_date", ""),
        "output_path": source_acquisition.get("output_path"),
        "feature_count": source_acquisition.get("feature_count", 0),
        "checksum_sha256": source_acquisition.get("checksum_sha256", ""),
        "source_limitations": source_acquisition.get("source_limitations", ""),
        "warnings": _string_list_of_objects(source_acquisition.get("warnings", []))
        + _string_list_of_objects(source_acquisition.get("validation_issues", [])),
    }


def _materialization_metadata(source_materialization: dict[str, Any] | None) -> dict[str, Any]:
    if not source_materialization:
        return {
            "status": "not_materialized",
            "access_method": "",
            "output_path": None,
            "feature_count": 0,
            "checksum_sha256": "",
            "layers": [],
            "warnings": [],
        }
    return {
        "status": source_materialization.get("status", ""),
        "access_method": source_materialization.get("access_method", ""),
        "output_path": source_materialization.get("output_path"),
        "feature_count": source_materialization.get("feature_count", 0),
        "checksum_sha256": source_materialization.get("checksum_sha256", ""),
        "layers": _materialization_layer_summaries(source_materialization.get("layers", [])),
        "warnings": _string_list_of_objects(source_materialization.get("warnings", []))
        + _string_list_of_objects(source_materialization.get("validation_issues", [])),
    }


def _materialization_layer_summaries(value: Any) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for layer in _string_list_of_objects(value):
        summaries.append(
            {
                "source_layer_id": layer.get("source_layer_id", ""),
                "source_layer_name": layer.get("source_layer_name", ""),
                "layer": layer.get("layer"),
                "status": layer.get("status", ""),
                "source_feature_count": layer.get("source_feature_count", 0),
                "clipped_feature_count": layer.get("clipped_feature_count", 0),
                "crs": layer.get("crs", ""),
            }
        )
    return summaries


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
    record_count = data.get("record_count")
    if record_count is not None and record_count != len(records):
        raise SourceInventoryError(f"Source inventory record_count does not match records: {location}")
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
        record.setdefault("materialization", _materialization_metadata(None))
        for object_field in ("catalog", "project_registry", "acquisition", "materialization", "source_status", "local_metadata", "metadata"):
            if not isinstance(record[object_field], dict):
                raise SourceInventoryError(f"Source inventory field '{object_field}' must be an object: {location}")
        for list_field in ("validation_issues", "uncertainty_flags"):
            if not isinstance(record[list_field], list):
                raise SourceInventoryError(f"Source inventory field '{list_field}' must be a list: {location}")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _string_list_of_objects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]
