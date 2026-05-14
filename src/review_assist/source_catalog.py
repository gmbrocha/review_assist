"""Source catalog and project source registry helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .projects import ProjectManifestError, load_project_manifest


CATALOG_PATH = Path("config/source_catalog.json")
PROJECT_SOURCES_PATH = Path("config/sources.json")
ALLOWED_SOURCE_METADATA_KEYS = {
    "citation",
    "license_or_terms",
    "attribution",
    "published_date",
    "metadata_date",
    "access_date",
    "source_url",
    "review_notes",
}


class SourceCatalogError(RuntimeError):
    """Raised when source catalog or registry data is invalid."""


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    name: str
    category: str
    publisher: str
    tier: str
    priority: str
    access_methods: list[str]
    public_or_restricted: str
    geometry_type: str = ""
    url: str = ""
    known_limitations: str = ""
    notes: str = ""
    spatial_relationships: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceDefinition":
        source_id = _required_string(data, "source_id", "source definition")
        name = _required_string(data, "name", source_id)
        category = _required_string(data, "category", source_id)
        publisher = _required_string(data, "publisher", source_id)
        access_methods = data.get("access_methods", [])
        if not isinstance(access_methods, list) or not all(isinstance(item, str) for item in access_methods):
            raise SourceCatalogError(f"Source '{source_id}' requires string list 'access_methods'.")

        relationships = data.get("spatial_relationships", [])
        if not isinstance(relationships, list) or not all(isinstance(item, str) for item in relationships):
            raise SourceCatalogError(f"Source '{source_id}' requires string list 'spatial_relationships'.")

        return cls(
            source_id=source_id,
            name=name,
            category=category,
            publisher=publisher,
            tier=str(data.get("tier", "")),
            priority=str(data.get("priority", "")),
            access_methods=access_methods,
            public_or_restricted=str(data.get("public_or_restricted", "")),
            geometry_type=str(data.get("geometry_type", "")),
            url=str(data.get("url", "")),
            known_limitations=str(data.get("known_limitations", "")),
            notes=str(data.get("notes", "")),
            spatial_relationships=relationships,
        )


@dataclass(frozen=True)
class SourceCatalog:
    catalog_version: str
    categories: list[dict[str, Any]]
    sources: dict[str, SourceDefinition]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceCatalog":
        raw_sources = data.get("sources", [])
        if not isinstance(raw_sources, list):
            raise SourceCatalogError("Source catalog requires a list field named 'sources'.")

        sources: dict[str, SourceDefinition] = {}
        for item in raw_sources:
            if not isinstance(item, dict):
                raise SourceCatalogError("Each source catalog entry must be an object.")
            source = SourceDefinition.from_dict(item)
            if source.source_id in sources:
                raise SourceCatalogError(f"Duplicate source_id in source catalog: {source.source_id}")
            sources[source.source_id] = source

        categories = data.get("categories", [])
        if not isinstance(categories, list):
            raise SourceCatalogError("Source catalog 'categories' must be a list when present.")
        for item in categories:
            if not isinstance(item, dict):
                raise SourceCatalogError("Each source catalog category entry must be an object.")

        return cls(
            catalog_version=str(data.get("catalog_version", "")),
            categories=[dict(item) for item in categories],
            sources=sources,
        )

    def sorted_sources(self) -> list[SourceDefinition]:
        return sorted(self.sources.values(), key=lambda item: (item.category, item.source_id))


@dataclass(frozen=True)
class ProjectSource:
    source_id: str
    enabled: bool = False
    access_method: str = "local_file"
    path: str | None = None
    role: str = "context"
    buffer_feet: float | None = None
    notes: str = ""
    status: str = "candidate"
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectSource":
        source_id = _required_string(data, "source_id", "project source")
        enabled = data.get("enabled", False)
        if not isinstance(enabled, bool):
            raise SourceCatalogError(f"Project source '{source_id}' enabled must be true or false.")

        path = data.get("path")
        if path is not None and not isinstance(path, str):
            raise SourceCatalogError(f"Project source '{source_id}' path must be a string or null.")
        if isinstance(path, str) and not path.strip():
            raise SourceCatalogError(f"Project source '{source_id}' path must not be blank.")

        access_method = data.get("access_method", "local_file")
        if not isinstance(access_method, str) or not access_method.strip():
            raise SourceCatalogError(f"Project source '{source_id}' requires a non-empty access_method.")

        buffer_feet = data.get("buffer_feet")
        if buffer_feet is not None:
            if isinstance(buffer_feet, bool):
                raise SourceCatalogError(f"Project source '{source_id}' buffer_feet must be numeric.")
            try:
                buffer_feet = float(buffer_feet)
            except (TypeError, ValueError) as exc:
                raise SourceCatalogError(f"Project source '{source_id}' buffer_feet must be numeric.") from exc
            if buffer_feet < 0:
                raise SourceCatalogError(f"Project source '{source_id}' buffer_feet must be zero or greater.")

        metadata = data.get("metadata", {})
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise SourceCatalogError(f"Project source '{source_id}' metadata must be an object when present.")
        unsupported_metadata = sorted(str(key) for key in metadata if key not in ALLOWED_SOURCE_METADATA_KEYS)
        if unsupported_metadata:
            raise SourceCatalogError(
                f"Project source '{source_id}' metadata has unsupported keys: {', '.join(unsupported_metadata)}."
            )
        clean_metadata: dict[str, str] = {}
        for key, value in metadata.items():
            if value is None:
                clean_metadata[str(key)] = ""
            elif isinstance(value, str):
                clean_metadata[str(key)] = value
            else:
                raise SourceCatalogError(f"Project source '{source_id}' metadata value '{key}' must be a string or null.")

        return cls(
            source_id=source_id,
            enabled=enabled,
            access_method=access_method,
            path=path,
            role=str(data.get("role", "context")),
            buffer_feet=buffer_feet,
            notes=str(data.get("notes", "")),
            status=str(data.get("status", "candidate")),
            metadata=clean_metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "enabled": self.enabled,
            "access_method": self.access_method,
            "path": self.path,
            "role": self.role,
            "buffer_feet": self.buffer_feet,
            "notes": self.notes,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ProjectSourceRegistry:
    project_id: str
    sources: list[ProjectSource]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectSourceRegistry":
        project_id = _required_string(data, "project_id", "project source registry")
        raw_sources = data.get("sources", [])
        if not isinstance(raw_sources, list):
            raise SourceCatalogError("Project source registry requires a list field named 'sources'.")
        sources: list[ProjectSource] = []
        seen_source_ids: set[str] = set()
        for item in raw_sources:
            if not isinstance(item, dict):
                raise SourceCatalogError("Each project source registry entry must be an object.")
            source = ProjectSource.from_dict(item)
            if source.source_id in seen_source_ids:
                raise SourceCatalogError(f"Duplicate source_id in project source registry: {source.source_id}")
            seen_source_ids.add(source.source_id)
            sources.append(source)
        return cls(
            project_id=project_id,
            sources=sources,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "sources": [source.to_dict() for source in self.sources],
        }

    def by_source_id(self) -> dict[str, ProjectSource]:
        return {source.source_id: source for source in self.sources}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_source_catalog(path: Path | None = None) -> SourceCatalog:
    catalog_file = path or repo_root() / CATALOG_PATH
    if not catalog_file.exists():
        raise SourceCatalogError(f"Missing source catalog: {catalog_file}")
    try:
        data = json.loads(catalog_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceCatalogError(f"Invalid source catalog JSON: {catalog_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceCatalogError(f"Source catalog must be a JSON object: {catalog_file}")
    return SourceCatalog.from_dict(data)


def load_project_source_registry(project_dir: Path) -> ProjectSourceRegistry:
    project_id = _project_id(project_dir)
    registry_file = project_dir / PROJECT_SOURCES_PATH
    if not registry_file.exists():
        return ProjectSourceRegistry(project_id=project_id, sources=[])
    try:
        data = json.loads(registry_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceCatalogError(f"Invalid project source registry JSON: {registry_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceCatalogError(f"Project source registry must be a JSON object: {registry_file}")
    registry = ProjectSourceRegistry.from_dict(data)
    if registry.project_id != project_id:
        raise SourceCatalogError(
            f"Project source registry id '{registry.project_id}' does not match project manifest id '{project_id}'."
        )
    return registry


def save_project_source_registry(project_dir: Path, registry: ProjectSourceRegistry) -> Path:
    registry_file = project_dir / PROJECT_SOURCES_PATH
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text(json.dumps(registry.to_dict(), indent=2) + "\n", encoding="utf-8")
    return registry_file


def register_local_source(project_dir: Path, source_id: str, source_path: Path, catalog: SourceCatalog | None = None) -> ProjectSourceRegistry:
    project_dir = project_dir.resolve()
    source_path = source_path.resolve()
    catalog = catalog or load_source_catalog()
    if source_id not in catalog.sources:
        raise SourceCatalogError(f"Unknown source_id '{source_id}'.")
    if not source_path.exists():
        raise SourceCatalogError(f"Missing source file: {source_path}")

    registry = load_project_source_registry(project_dir)
    existing = registry.by_source_id()
    old_source = existing.get(source_id)
    path_value = _display_path(source_path, project_dir)
    updated = ProjectSource(
        source_id=source_id,
        enabled=True,
        access_method="local_file",
        path=path_value,
        role=old_source.role if old_source else "context",
        buffer_feet=old_source.buffer_feet if old_source else None,
        notes=old_source.notes if old_source else "Registered local source layer.",
        status="local_registered",
        metadata=old_source.metadata if old_source else {},
    )

    sources: list[ProjectSource] = []
    replaced = False
    for source in registry.sources:
        if source.source_id == source_id:
            sources.append(updated)
            replaced = True
        else:
            sources.append(source)
    if not replaced:
        sources.append(updated)

    saved = ProjectSourceRegistry(project_id=registry.project_id, sources=sources)
    save_project_source_registry(project_dir, saved)
    return saved


def resolve_project_source_path(project_dir: Path, source: ProjectSource) -> Path | None:
    if not source.path:
        return None
    path = Path(source.path)
    if path.is_absolute():
        return path
    return (project_dir / path).resolve()


def _required_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SourceCatalogError(f"{context} requires a non-empty '{key}'.")
    return value


def _project_id(project_dir: Path) -> str:
    try:
        return load_project_manifest(project_dir).project_id
    except ProjectManifestError as exc:
        raise SourceCatalogError(str(exc)) from exc


def _display_path(path: Path, project_dir: Path) -> str:
    try:
        return path.relative_to(project_dir).as_posix()
    except ValueError:
        return str(path)
