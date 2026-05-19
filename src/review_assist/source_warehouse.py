"""Local seeded source warehouse manifest helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .source_catalog import repo_root


SOURCE_WAREHOUSE_MANIFEST_PATH = Path("sources/source_warehouse_manifest.json")
SOURCE_MANIFEST_NAME = "source_manifest.json"


class SourceWarehouseError(RuntimeError):
    """Raised when source warehouse manifests are invalid."""


def source_warehouse_root(index_path: Path | None = None) -> Path:
    path = (index_path or repo_root() / SOURCE_WAREHOUSE_MANIFEST_PATH).resolve()
    return path.parent


def load_source_warehouse_manifest(path: Path | None = None) -> dict[str, Any]:
    """Load and lightly validate the root source warehouse manifest."""

    manifest_path = (path or repo_root() / SOURCE_WAREHOUSE_MANIFEST_PATH).resolve()
    if not manifest_path.exists():
        raise SourceWarehouseError(f"Missing source warehouse manifest: {manifest_path}")
    data = _read_json(manifest_path)
    if not isinstance(data, dict):
        raise SourceWarehouseError(f"Source warehouse manifest must be a JSON object: {manifest_path}")
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise SourceWarehouseError(f"Source warehouse manifest requires a sources list: {manifest_path}")
    seen: set[str] = set()
    for item in sources:
        if not isinstance(item, dict):
            raise SourceWarehouseError(f"Each warehouse source entry must be an object: {manifest_path}")
        source_id = _required_string(item, "source_id", str(manifest_path))
        if source_id in seen:
            raise SourceWarehouseError(f"Duplicate warehouse source_id '{source_id}': {manifest_path}")
        seen.add(source_id)
        _required_string(item, "manifest_path", source_id)
    return data


def load_seed_source_manifest(source_id: str, *, index_path: Path | None = None) -> dict[str, Any]:
    """Load a source-specific warehouse manifest by stable source id."""

    index = load_source_warehouse_manifest(index_path)
    root = source_warehouse_root(index_path)
    manifest_rel = None
    for item in index["sources"]:
        if item.get("source_id") == source_id:
            manifest_rel = _required_string(item, "manifest_path", source_id)
            break
    if manifest_rel is None:
        raise SourceWarehouseError(f"Warehouse source_id is not indexed: {source_id}")
    manifest_path = (root / manifest_rel).resolve()
    data = _read_json(manifest_path)
    _validate_seed_source_manifest(data, manifest_path, expected_source_id=source_id)
    return data


def indexed_source_ids(*, index_path: Path | None = None) -> set[str]:
    """Return stable source IDs listed by the root warehouse manifest."""

    return {str(item.get("source_id")) for item in load_source_warehouse_manifest(index_path)["sources"]}


def source_manifest_path(source_id: str, *, index_path: Path | None = None) -> Path:
    index = load_source_warehouse_manifest(index_path)
    root = source_warehouse_root(index_path)
    for item in index["sources"]:
        if item.get("source_id") == source_id:
            return (root / _required_string(item, "manifest_path", source_id)).resolve()
    raise SourceWarehouseError(f"Warehouse source_id is not indexed: {source_id}")


def raw_paths_exist(source_id: str, *, index_path: Path | None = None) -> list[dict[str, Any]]:
    """Report source-manifest raw path existence without reading bulk GIS data."""

    manifest = load_seed_source_manifest(source_id, index_path=index_path)
    manifest_dir = source_manifest_path(source_id, index_path=index_path).parent
    results: list[dict[str, Any]] = []
    for raw_path in _string_list(manifest.get("raw_paths", [])):
        path = (manifest_dir / raw_path).resolve()
        results.append({"raw_path": raw_path, "path": str(path), "exists": path.exists()})
    return results


def maybe_load_seed_source_manifest(source_id: str, *, index_path: Path | None = None) -> dict[str, Any] | None:
    """Load a seed source manifest if the warehouse index is available and contains the source."""

    try:
        return load_seed_source_manifest(source_id, index_path=index_path)
    except SourceWarehouseError:
        return None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SourceWarehouseError(f"Invalid source warehouse JSON: {path}: {exc}") from exc


def _validate_seed_source_manifest(data: Any, path: Path, *, expected_source_id: str) -> None:
    if not isinstance(data, dict):
        raise SourceWarehouseError(f"Source manifest must be a JSON object: {path}")
    source_id = _required_string(data, "source_id", str(path))
    if source_id != expected_source_id:
        raise SourceWarehouseError(f"Source manifest id '{source_id}' does not match index id '{expected_source_id}': {path}")
    for key in ("display_name", "category", "authority", "warehouse_group", "raw_paths", "acquisition_method"):
        if key == "raw_paths":
            if not _string_list(data.get(key, [])):
                raise SourceWarehouseError(f"Source manifest '{source_id}' requires non-empty raw_paths: {path}")
            continue
        _required_string(data, key, source_id)
    for key in ("analysis_ready", "renderable"):
        if not isinstance(data.get(key), bool):
            raise SourceWarehouseError(f"Source manifest '{source_id}' field '{key}' must be boolean: {path}")


def _required_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SourceWarehouseError(f"{context} requires a non-empty '{key}'.")
    return value.strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
