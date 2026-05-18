"""Local source warehouse materialization into project-ready GeoJSON layers."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pyogrio

from .inspection import write_geojson
from .project_geometry import PROJECT_ANALYSIS_BOUNDS_PATH, ProjectGeometryError, build_project_geometry
from .projects import ProjectManifestError, load_project_manifest
from .source_catalog import (
    ProjectSource,
    SourceCatalog,
    SourceCatalogError,
    SourceDefinition,
    load_project_source_registry,
    load_source_catalog,
    register_materialized_source,
    repo_root,
    resolve_project_source_path,
)


LOCAL_SOURCE_MATERIALIZER_CONFIG_PATH = Path("config/local_source_materializers.json")
SOURCE_MATERIALIZATION_PATH = Path("source_materialization/local_source_materialization_manifest.json")
MATERIALIZED_LAYERS_DIR = Path("layers")


class SourceMaterializationError(RuntimeError):
    """Raised when local source materialization cannot complete."""


@dataclass(frozen=True)
class MaterializerLayer:
    path: Path
    layer: str | None
    source_layer_id: str
    source_layer_name: str


@dataclass(frozen=True)
class LocalSourceMaterializerDefinition:
    source_id: str
    output_name: str
    layers: list[MaterializerLayer]
    normalization: dict[str, list[str]] = field(default_factory=dict)


def materialize_local_source(
    project_dir: Path,
    source_id: str,
    *,
    replace: bool = False,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Materialize one configured local warehouse source into project-ready GeoJSON."""

    return _materialize(
        project_dir.resolve(),
        source_ids=[source_id],
        replace=replace,
        strict=True,
        config_path=config_path,
    )


def materialize_local_sources(
    project_dir: Path,
    *,
    replace: bool = False,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Materialize all configured local warehouse sources, preserving existing local project sources."""

    definitions = load_local_source_materializers(config_path)
    return _materialize(
        project_dir.resolve(),
        source_ids=[definition.source_id for definition in definitions],
        replace=replace,
        strict=False,
        config_path=config_path,
    )


def load_local_source_materializers(config_path: Path | None = None) -> list[LocalSourceMaterializerDefinition]:
    """Load and validate local source materializer configuration."""

    path = (config_path or repo_root() / LOCAL_SOURCE_MATERIALIZER_CONFIG_PATH).resolve()
    if not path.exists():
        raise SourceMaterializationError(f"Missing local source materializer config: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceMaterializationError(f"Invalid local source materializer config JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceMaterializationError(f"Local source materializer config must be a JSON object: {path}")

    try:
        catalog = load_source_catalog()
    except SourceCatalogError as exc:
        raise SourceMaterializationError(str(exc)) from exc

    raw_sources = data.get("sources", [])
    if not isinstance(raw_sources, list) or not raw_sources:
        raise SourceMaterializationError("Local source materializer config requires a non-empty sources list.")

    definitions: list[LocalSourceMaterializerDefinition] = []
    seen: set[str] = set()
    for raw_source in raw_sources:
        if not isinstance(raw_source, dict):
            raise SourceMaterializationError("Each local source materializer entry must be an object.")
        source_id = _required_string(raw_source, "source_id", "local source materializer")
        if source_id in seen:
            raise SourceMaterializationError(f"Duplicate local source materializer source_id: {source_id}")
        if source_id not in catalog.sources:
            raise SourceMaterializationError(f"Unknown local source materializer source_id: {source_id}")
        seen.add(source_id)
        output_name = str(raw_source.get("output_name") or source_id).strip()
        if not output_name:
            raise SourceMaterializationError(f"Local source materializer '{source_id}' requires an output_name.")
        raw_layers = raw_source.get("layers", [])
        if not isinstance(raw_layers, list) or not raw_layers:
            raise SourceMaterializationError(f"Local source materializer '{source_id}' requires a non-empty layers list.")
        layers = [_materializer_layer(item, source_id=source_id) for item in raw_layers]
        normalization = _normalization_config(raw_source.get("normalization", {}), source_id=source_id)
        definitions.append(
            LocalSourceMaterializerDefinition(
                source_id=source_id,
                output_name=output_name,
                layers=layers,
                normalization=normalization,
            )
        )
    return definitions


def _materialize(
    project_dir: Path,
    *,
    source_ids: list[str],
    replace: bool,
    strict: bool,
    config_path: Path | None,
) -> dict[str, Any]:
    try:
        manifest = load_project_manifest(project_dir)
        catalog = load_source_catalog()
        definitions = {definition.source_id: definition for definition in load_local_source_materializers(config_path)}
    except (ProjectManifestError, SourceCatalogError, SourceMaterializationError) as exc:
        raise SourceMaterializationError(str(exc)) from exc

    unknown = [source_id for source_id in source_ids if source_id not in definitions]
    if unknown:
        raise SourceMaterializationError(f"No local source materializer configured for: {', '.join(unknown)}")

    analysis_bounds = _load_or_build_analysis_bounds(project_dir)
    sources: list[dict[str, Any]] = []
    validation_issues: list[dict[str, Any]] = []
    for source_id in source_ids:
        try:
            record = _materialize_one(
                project_dir=project_dir,
                definition=definitions[source_id],
                source_definition=catalog.sources[source_id],
                analysis_bounds=analysis_bounds,
                replace=replace,
                strict=strict,
            )
        except SourceMaterializationError:
            raise
        except Exception as exc:  # noqa: BLE001 - all-source materialization is intentionally nonfatal.
            if strict:
                raise SourceMaterializationError(str(exc)) from exc
            record = _failed_record(catalog.sources[source_id], source_id, "local_source_materialization_failed", str(exc))
        sources.append(record)
        validation_issues.extend(_record_issues(record))

    status_counts: dict[str, int] = {}
    for record in sources:
        status = str(record.get("status", ""))
        status_counts[status] = status_counts.get(status, 0) + 1

    output_path = project_dir / SOURCE_MATERIALIZATION_PATH
    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "materializer_config_path": str((config_path or repo_root() / LOCAL_SOURCE_MATERIALIZER_CONFIG_PATH).resolve()),
        "analysis_bounds_path": str(project_dir / PROJECT_ANALYSIS_BOUNDS_PATH),
        "replace": replace,
        "source_count": len(sources),
        "materialized_count": len([record for record in sources if record.get("status") in {"materialized", "registered_existing_output"}]),
        "registered_existing_count": len([record for record in sources if record.get("status") == "registered_existing_output"]),
        "skipped_count": len([record for record in sources if str(record.get("status", "")).startswith("skipped")]),
        "failed_count": len([record for record in sources if record.get("status") in {"failed", "missing_warehouse_source"}]),
        "status_counts": status_counts,
        "sources": sources,
        "validation_issues": validation_issues,
        "output_path": str(output_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _materialize_one(
    *,
    project_dir: Path,
    definition: LocalSourceMaterializerDefinition,
    source_definition: SourceDefinition,
    analysis_bounds: gpd.GeoDataFrame,
    replace: bool,
    strict: bool,
) -> dict[str, Any]:
    existing_source = _existing_project_local_source(project_dir, definition.source_id)
    if existing_source is not None and not replace:
        return _skipped_existing_source_record(project_dir, source_definition, existing_source)

    output_dir = (project_dir / MATERIALIZED_LAYERS_DIR / definition.source_id).resolve()
    output_path = output_dir / f"{definition.output_name}.geojson"
    if output_path.exists() and not replace:
        return _registered_existing_output_record(project_dir, source_definition, output_path)

    frames: list[gpd.GeoDataFrame] = []
    layer_records: list[dict[str, Any]] = []
    validation_issues: list[dict[str, Any]] = []
    for layer in definition.layers:
        if not layer.path.exists():
            issue = _issue(
                "warning",
                "missing_warehouse_source_file",
                f"Local warehouse source file is missing: {layer.path}",
                str(layer.path),
                source_id=definition.source_id,
            )
            if strict:
                raise SourceMaterializationError(issue["message"])
            validation_issues.append(issue)
            layer_records.append(_layer_record(layer, status="missing", validation_issues=[issue]))
            continue
        try:
            clipped, layer_record = _materialize_layer(
                definition=definition,
                source_definition=source_definition,
                layer=layer,
                analysis_bounds=analysis_bounds,
            )
        except Exception as exc:  # noqa: BLE001 - layer failures are nonfatal in all-source mode.
            issue = _issue(
                "warning",
                "unreadable_warehouse_source_layer",
                f"Unable to materialize local warehouse layer '{layer.source_layer_name}': {exc}",
                str(layer.path),
                source_id=definition.source_id,
            )
            if strict:
                raise SourceMaterializationError(issue["message"]) from exc
            validation_issues.append(issue)
            layer_records.append(_layer_record(layer, status="failed", validation_issues=[issue]))
            continue
        frames.append(clipped)
        layer_records.append(layer_record)

    if not frames:
        if validation_issues:
            return _missing_or_failed_record(source_definition, layer_records, validation_issues)
        return _failed_record(source_definition, definition.source_id, "local_source_materialization_empty", "No materializer layers were available.")

    if output_dir.exists() and replace:
        _remove_project_layer_dir(project_dir, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    combined = _json_safe_attributes(_combine_frames(frames))
    write_geojson(combined, output_path)
    checksum = _sha256(output_path)
    register_materialized_source(project_dir, definition.source_id, output_path)

    feature_count = int(len(combined))
    if feature_count == 0:
        validation_issues.append(
            _issue(
                "info",
                "materialized_source_empty",
                f"{source_definition.name} had no features intersecting the project analysis bounds.",
                str(output_path),
                source_id=definition.source_id,
            )
        )

    return {
        "source_id": definition.source_id,
        "source_name": source_definition.name,
        "source_category": source_definition.category,
        "status": "materialized",
        "data_authenticity": "real",
        "access_method": "local_warehouse_materialization",
        "output_path": str(output_path),
        "feature_count": feature_count,
        "checksum_sha256": checksum,
        "layers": layer_records,
        "source_url": source_definition.url,
        "source_limitations": source_definition.known_limitations,
        "validation_issues": validation_issues,
        "warnings": validation_issues,
    }


def _materialize_layer(
    *,
    definition: LocalSourceMaterializerDefinition,
    source_definition: SourceDefinition,
    layer: MaterializerLayer,
    analysis_bounds: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, dict[str, Any]]:
    source_crs = _layer_crs(layer)
    bounds_for_bbox = analysis_bounds.to_crs(source_crs)
    bbox = tuple(float(value) for value in bounds_for_bbox.total_bounds)
    raw = pyogrio.read_dataframe(layer.path, layer=layer.layer, bbox=bbox)
    if raw.crs is None:
        raw = raw.set_crs(source_crs, allow_override=True)
    raw = raw[~raw.geometry.isna()]
    raw = raw[~raw.geometry.is_empty]
    source_feature_count = int(len(raw))

    if raw.empty:
        clipped = _empty_like(raw, "EPSG:4326")
    else:
        raw = _make_valid(raw)
        projected = raw.to_crs(analysis_bounds.crs)
        clipped = _clip_to_bounds(projected, analysis_bounds)
        clipped = clipped[~clipped.geometry.isna()]
        clipped = clipped[~clipped.geometry.is_empty]
        clipped = _add_normalized_fields(
            clipped.to_crs("EPSG:4326"),
            definition=definition,
            source_definition=source_definition,
            layer=layer,
        )

    layer_record = _layer_record(
        layer,
        status="materialized",
        source_feature_count=source_feature_count,
        clipped_feature_count=int(len(clipped)),
        crs=source_crs,
        bbox=bbox,
    )
    return clipped, layer_record


def _load_or_build_analysis_bounds(project_dir: Path) -> gpd.GeoDataFrame:
    bounds_path = project_dir / PROJECT_ANALYSIS_BOUNDS_PATH
    if not bounds_path.exists():
        try:
            build_project_geometry(project_dir)
        except ProjectGeometryError as exc:
            raise SourceMaterializationError(str(exc)) from exc
    try:
        gdf = gpd.read_file(bounds_path)
    except Exception as exc:  # pragma: no cover - driver-specific exception types vary.
        raise SourceMaterializationError(f"Unable to read project analysis bounds: {bounds_path}: {exc}") from exc
    if gdf.empty:
        raise SourceMaterializationError(f"Project analysis bounds are empty: {bounds_path}")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    return gdf.to_crs("EPSG:4326")


def _add_normalized_fields(
    gdf: gpd.GeoDataFrame,
    *,
    definition: LocalSourceMaterializerDefinition,
    source_definition: SourceDefinition,
    layer: MaterializerLayer,
) -> gpd.GeoDataFrame:
    result = gdf.copy()
    mappings = _normalization_mappings(source_definition.source_id, definition.normalization)
    result["review_assist_source_id"] = source_definition.source_id
    result["review_assist_source_name"] = source_definition.name
    result["review_assist_source_category"] = source_definition.category
    result["review_assist_layer_id"] = layer.source_layer_id
    result["review_assist_layer_name"] = layer.source_layer_name
    result["review_assist_feature_label"] = result.apply(lambda row: _first_value(row, mappings["label"]), axis=1)
    result["review_assist_feature_type"] = result.apply(lambda row: _first_value(row, mappings["type"]), axis=1)
    result["review_assist_feature_subtype"] = result.apply(lambda row: _joined_values(row, mappings["subtype"]), axis=1)
    result["review_assist_feature_original_id"] = result.apply(lambda row: _first_value(row, mappings["original_id"]), axis=1)
    result["review_assist_feature_date"] = result.apply(lambda row: _first_value(row, mappings["date"]), axis=1)
    result["review_assist_quality_flag"] = result.apply(lambda row: _first_value(row, mappings["quality"]), axis=1)
    result["review_assist_source_citation"] = result.apply(lambda row: _first_value(row, mappings["citation"]), axis=1)
    result["review_assist_data_authenticity"] = "real"
    _add_source_specific_fields(result, source_definition.source_id)
    return result


def _normalization_mappings(source_id: str, configured: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    mappings = {
        "usfws_nwi_wetlands": {
            "label": ["ATTRIBUTE"],
            "type": ["ATTRIBUTE"],
            "subtype": ["WETLAND_TYPE"],
            "original_id": ["NWI_ID", "OBJECTID"],
            "date": [],
            "quality": ["QAQC_CODE"],
            "citation": [],
        },
        "usfws_critical_habitat": {
            "label": ["comname", "COMNAME", "sciname", "SCINAME"],
            "type": ["status", "STATUS"],
            "subtype": ["listing_status", "LISTING_STATUS", "listing_st", "unitname", "UNITNAME", "subunitname", "SUBUNITNAME", "subunitnam", "unit", "UNIT", "subunit", "SUBUNIT"],
            "original_id": ["GlobalID", "globalid", "OBJECTID", "OBJECTID_1", "objectid", "objectid_1", "source_id", "entity_id"],
            "date": ["effectdate", "EFFECTDATE", "pubdate", "PUBDATE", "vacatedate", "VACATEDATE"],
            "quality": ["accuracy", "ACCURACY"],
            "citation": ["fedreg", "FEDREG"],
        },
        "usda_nrcs_ssurgo_soils": {
            "label": ["MUSYM", "musym", "MUKEY", "mukey"],
            "type": ["MUSYM", "musym"],
            "subtype": ["AREASYMBOL", "areasymbol"],
            "original_id": ["MUKEY", "mukey"],
            "date": [],
            "quality": ["SPATIALVER", "spatialver"],
            "citation": ["AREASYMBOL", "areasymbol"],
        },
    }
    default = mappings.get(
        source_id,
        {
            "label": ["name", "Name", "NAME", "label", "Label", "LABEL"],
            "type": [],
            "subtype": [],
            "original_id": ["OBJECTID", "objectid", "id", "ID"],
            "date": [],
            "quality": [],
            "citation": [],
        },
    )
    if not configured:
        return default
    merged = dict(default)
    for key, value in configured.items():
        merged[key] = list(value)
    return merged


def _add_source_specific_fields(gdf: gpd.GeoDataFrame, source_id: str) -> None:
    if source_id == "usfws_nwi_wetlands":
        gdf["review_assist_wetland_attribute"] = gdf.apply(lambda row: _first_value(row, ["ATTRIBUTE"]), axis=1)
        gdf["review_assist_wetland_type"] = gdf.apply(lambda row: _first_value(row, ["WETLAND_TYPE"]), axis=1)
        gdf["review_assist_nwi_id"] = gdf.apply(lambda row: _first_value(row, ["NWI_ID"]), axis=1)
    elif source_id == "usfws_critical_habitat":
        gdf["review_assist_species_common_name"] = gdf.apply(lambda row: _first_value(row, ["comname", "COMNAME"]), axis=1)
        gdf["review_assist_species_scientific_name"] = gdf.apply(lambda row: _first_value(row, ["sciname", "SCINAME"]), axis=1)
        gdf["review_assist_listing_status"] = gdf.apply(lambda row: _first_value(row, ["listing_status", "LISTING_STATUS", "listing_st"]), axis=1)
        gdf["review_assist_unit"] = gdf.apply(lambda row: _first_value(row, ["unit", "UNIT", "unitname", "UNITNAME"]), axis=1)
        gdf["review_assist_subunit"] = gdf.apply(lambda row: _first_value(row, ["subunit", "SUBUNIT", "subunitname", "SUBUNITNAME", "subunitnam"]), axis=1)
        gdf["review_assist_federal_register"] = gdf.apply(lambda row: _first_value(row, ["fedreg", "FEDREG"]), axis=1)
    elif source_id == "usda_nrcs_ssurgo_soils":
        gdf["review_assist_soil_mapunit_symbol"] = gdf.apply(lambda row: _first_value(row, ["MUSYM", "musym"]), axis=1)
        gdf["review_assist_soil_mapunit_key"] = gdf.apply(lambda row: _first_value(row, ["MUKEY", "mukey"]), axis=1)
        gdf["review_assist_soil_area_symbol"] = gdf.apply(lambda row: _first_value(row, ["AREASYMBOL", "areasymbol"]), axis=1)
        gdf["review_assist_soil_spatial_version"] = gdf.apply(lambda row: _first_value(row, ["SPATIALVER", "spatialver"]), axis=1)
    elif source_id == "maris_boundary_context":
        gdf["review_assist_county_name"] = gdf.apply(lambda row: _first_value(row, ["CONAME", "County", "COUNTY_NAME"]), axis=1)
        gdf["review_assist_county_seat"] = gdf.apply(lambda row: _first_value(row, ["CO_SEAT", "county_seat"]), axis=1)


def _first_value(row: Any, fields: list[str]) -> str:
    by_lower = {str(column).lower(): column for column in row.index}
    for field in fields:
        column = field if field in row.index else by_lower.get(str(field).lower())
        if column is None:
            continue
        value = row[column]
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


def _joined_values(row: Any, fields: list[str]) -> str:
    values: list[str] = []
    for field in fields:
        value = _first_value(row, [field])
        if value and value not in values:
            values.append(value)
    return "; ".join(values)


def _materializer_layer(raw_layer: Any, *, source_id: str) -> MaterializerLayer:
    if not isinstance(raw_layer, dict):
        raise SourceMaterializationError(f"Each local source materializer layer for '{source_id}' must be an object.")
    raw_path = _required_string(raw_layer, "path", f"local source materializer '{source_id}' layer")
    layer_name = raw_layer.get("layer")
    if layer_name is not None and not isinstance(layer_name, str):
        raise SourceMaterializationError(f"Local source materializer '{source_id}' layer name must be a string when present.")
    source_layer_id = str(raw_layer.get("source_layer_id") or layer_name or Path(raw_path).stem).strip()
    source_layer_name = str(raw_layer.get("source_layer_name") or layer_name or Path(raw_path).stem).strip()
    return MaterializerLayer(
        path=_resolve_warehouse_path(raw_path),
        layer=layer_name.strip() if isinstance(layer_name, str) and layer_name.strip() else None,
        source_layer_id=source_layer_id,
        source_layer_name=source_layer_name,
    )


def _normalization_config(raw_normalization: Any, *, source_id: str) -> dict[str, list[str]]:
    if raw_normalization in (None, {}):
        return {}
    if not isinstance(raw_normalization, dict):
        raise SourceMaterializationError(f"Local source materializer '{source_id}' normalization must be an object when present.")
    key_map = {
        "label": "label",
        "label_fields": "label",
        "type": "type",
        "feature_type_fields": "type",
        "subtype": "subtype",
        "feature_subtype_fields": "subtype",
        "original_id": "original_id",
        "original_id_fields": "original_id",
        "date": "date",
        "date_fields": "date",
        "quality": "quality",
        "quality_flag_fields": "quality",
        "citation": "citation",
        "source_citation_fields": "citation",
    }
    normalization: dict[str, list[str]] = {}
    for raw_key, raw_value in raw_normalization.items():
        key = key_map.get(str(raw_key))
        if key is None:
            raise SourceMaterializationError(
                f"Local source materializer '{source_id}' normalization has unsupported key: {raw_key}"
            )
        if not isinstance(raw_value, list) or not all(isinstance(item, str) for item in raw_value):
            raise SourceMaterializationError(
                f"Local source materializer '{source_id}' normalization field '{raw_key}' must be a string list."
            )
        normalization[key] = [item for item in raw_value if item.strip()]
    return normalization


def _resolve_warehouse_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (repo_root() / path).resolve()


def _layer_crs(layer: MaterializerLayer) -> str:
    try:
        info = pyogrio.read_info(layer.path, layer=layer.layer)
    except Exception as exc:  # pragma: no cover - driver-specific exception types vary.
        raise SourceMaterializationError(f"Unable to inspect local source layer CRS: {layer.path}: {exc}") from exc
    crs = info.get("crs")
    return str(crs) if crs else "EPSG:4326"


def _clip_to_bounds(gdf: gpd.GeoDataFrame, bounds_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    bounds_union = bounds_gdf.geometry.union_all()
    intersecting = gdf[gdf.geometry.intersects(bounds_union)].copy()
    if intersecting.empty:
        return intersecting
    try:
        return gpd.clip(intersecting, bounds_gdf)
    except Exception:
        clipped = intersecting.copy()
        clipped["geometry"] = clipped.geometry.intersection(bounds_union)
        return clipped


def _make_valid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    result = gdf.copy()
    try:
        result["geometry"] = result.geometry.make_valid()
    except Exception:
        pass
    return result


def _empty_like(gdf: gpd.GeoDataFrame, crs: str) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(gdf.iloc[0:0].copy(), geometry="geometry", crs=gdf.crs).to_crs(crs)


def _combine_frames(frames: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    non_empty = [frame for frame in frames if not frame.empty]
    if not non_empty:
        first = frames[0]
        return gpd.GeoDataFrame(first.iloc[0:0].copy(), geometry="geometry", crs="EPSG:4326")
    return gpd.GeoDataFrame(pd.concat(non_empty, ignore_index=True), geometry="geometry", crs="EPSG:4326")


def _json_safe_attributes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    result = gdf.copy()
    for column in result.columns:
        if column == result.geometry.name:
            continue
        series = result[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            result[column] = series.astype("string").fillna("")
        elif series.dtype == "object":
            result[column] = series.map(_json_safe_value)
    return result


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "isoformat") and callable(value.isoformat):
        try:
            return value.isoformat()
        except TypeError:
            return str(value)
    return value


def _existing_project_local_source(project_dir: Path, source_id: str) -> ProjectSource | None:
    registry = load_project_source_registry(project_dir)
    source = registry.by_source_id().get(source_id)
    if source is None or not source.enabled or source.access_method != "local_file" or not source.path:
        return None
    path = resolve_project_source_path(project_dir, source)
    if path is not None and path.exists():
        return source
    return None


def _remove_project_layer_dir(project_dir: Path, target_dir: Path) -> None:
    layers_dir = (project_dir / MATERIALIZED_LAYERS_DIR).resolve()
    try:
        target_dir.resolve().relative_to(layers_dir)
    except ValueError as exc:
        raise SourceMaterializationError(f"Refusing to replace materialized source outside project layers directory: {target_dir}") from exc
    if target_dir.exists():
        shutil.rmtree(target_dir)


def _layer_record(
    layer: MaterializerLayer,
    *,
    status: str,
    source_feature_count: int = 0,
    clipped_feature_count: int = 0,
    crs: str = "",
    bbox: tuple[float, float, float, float] | None = None,
    validation_issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "source_layer_id": layer.source_layer_id,
        "source_layer_name": layer.source_layer_name,
        "warehouse_path": str(layer.path),
        "layer": layer.layer,
        "status": status,
        "crs": crs,
        "requested_bbox_in_source_crs": list(bbox) if bbox is not None else None,
        "source_feature_count": source_feature_count,
        "clipped_feature_count": clipped_feature_count,
        "validation_issues": validation_issues or [],
    }


def _skipped_existing_source_record(project_dir: Path, source_definition: SourceDefinition, existing: ProjectSource) -> dict[str, Any]:
    resolved = resolve_project_source_path(project_dir, existing)
    issue = _issue(
        "info",
        "existing_local_source_preserved",
        "Existing local project source was preserved instead of being replaced by local warehouse materialization.",
        existing.path or source_definition.source_id,
        source_id=source_definition.source_id,
    )
    return {
        "source_id": source_definition.source_id,
        "source_name": source_definition.name,
        "source_category": source_definition.category,
        "status": "skipped_existing_local",
        "data_authenticity": existing.metadata.get("data_authenticity", "real"),
        "output_path": str(resolved) if resolved else existing.path,
        "feature_count": 0,
        "checksum_sha256": "",
        "layers": [],
        "validation_issues": [issue],
        "warnings": [issue],
    }


def _skipped_existing_output_record(source_definition: SourceDefinition, output_path: Path) -> dict[str, Any]:
    issue = _issue(
        "warning",
        "existing_materialized_output_preserved",
        "Project-local materialized output already exists; use --replace to overwrite it.",
        str(output_path),
        source_id=source_definition.source_id,
    )
    return {
        "source_id": source_definition.source_id,
        "source_name": source_definition.name,
        "source_category": source_definition.category,
        "status": "skipped_existing_output",
        "data_authenticity": "real",
        "output_path": str(output_path),
        "feature_count": 0,
        "checksum_sha256": _sha256(output_path) if output_path.exists() else "",
        "layers": [],
        "validation_issues": [issue],
        "warnings": [issue],
    }


def _registered_existing_output_record(project_dir: Path, source_definition: SourceDefinition, output_path: Path) -> dict[str, Any]:
    feature_count = _geojson_feature_count(output_path)
    register_materialized_source(project_dir, source_definition.source_id, output_path)
    issue = _issue(
        "info",
        "existing_materialized_output_registered",
        "Existing project-local materialized output was registered for analysis without overwriting it.",
        str(output_path),
        source_id=source_definition.source_id,
    )
    return {
        "source_id": source_definition.source_id,
        "source_name": source_definition.name,
        "source_category": source_definition.category,
        "status": "registered_existing_output",
        "data_authenticity": "real",
        "access_method": "local_warehouse_materialization",
        "output_path": str(output_path),
        "feature_count": feature_count,
        "checksum_sha256": _sha256(output_path),
        "layers": [],
        "source_url": source_definition.url,
        "source_limitations": source_definition.known_limitations,
        "validation_issues": [],
        "warnings": [issue],
    }


def _missing_or_failed_record(
    source_definition: SourceDefinition,
    layer_records: list[dict[str, Any]],
    validation_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    status = "missing_warehouse_source" if any(record.get("status") == "missing" for record in layer_records) else "failed"
    return {
        "source_id": source_definition.source_id,
        "source_name": source_definition.name,
        "source_category": source_definition.category,
        "status": status,
        "data_authenticity": "stub",
        "output_path": None,
        "feature_count": 0,
        "checksum_sha256": "",
        "layers": layer_records,
        "source_url": source_definition.url,
        "source_limitations": source_definition.known_limitations,
        "validation_issues": validation_issues,
        "warnings": validation_issues,
    }


def _failed_record(source_definition: SourceDefinition, source_id: str, code: str, message: str) -> dict[str, Any]:
    issue = _issue("warning", code, message, source_id, source_id=source_id)
    return {
        "source_id": source_id,
        "source_name": source_definition.name if source_definition else source_id,
        "source_category": source_definition.category if source_definition else "",
        "status": "failed",
        "data_authenticity": "stub",
        "output_path": None,
        "feature_count": 0,
        "checksum_sha256": "",
        "layers": [],
        "validation_issues": [issue],
        "warnings": [issue],
    }


def _record_issues(record: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for field in ("validation_issues", "warnings"):
        raw_issues = record.get(field, [])
        if not isinstance(raw_issues, list):
            continue
        for issue in raw_issues:
            if isinstance(issue, dict):
                issues.append(dict(issue))
    return issues


def _geojson_feature_count(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceMaterializationError(f"Existing materialized source output is not readable GeoJSON: {path}: {exc}") from exc
    features = data.get("features") if isinstance(data, dict) else None
    if not isinstance(features, list):
        raise SourceMaterializationError(f"Existing materialized source output must be a GeoJSON FeatureCollection: {path}")
    return len(features)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SourceMaterializationError(f"{context} requires a non-empty '{key}'.")
    return value.strip()


def _issue(severity: str, code: str, message: str, location: str, *, source_id: str | None = None) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "location": location,
    }
    if source_id:
        issue["source_id"] = source_id
    return issue


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
