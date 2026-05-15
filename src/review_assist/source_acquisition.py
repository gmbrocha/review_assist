"""Catalog-driven source gap resolution and public source downloads."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import geopandas as gpd

from .project_geometry import PROJECT_ANALYSIS_BOUNDS_PATH, ProjectGeometryError, build_project_geometry
from .projects import ProjectInput, ProjectManifest, ProjectManifestError, load_project_manifest
from .report_profiles import ReportProfileError, resolve_report_profile
from .source_catalog import (
    ProjectSource,
    ProjectSourceRegistry,
    SourceCatalog,
    SourceCatalogError,
    SourceDefinition,
    load_project_source_registry,
    load_source_catalog,
    resolve_project_source_path,
    save_project_source_registry,
)


SOURCE_ACQUISITION_PATH = Path("source_acquisition/source_acquisition_manifest.json")
SOURCE_DOWNLOADS_DIR = Path("source_acquisition/downloads")

NWI_SOURCE_ID = "usfws_nwi_wetlands"
NWI_SERVICE_ROOT = "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest"
NWI_SERVICE_URL = f"{NWI_SERVICE_ROOT}/services/Wetlands/MapServer"
NWI_LAYER_ID = 0

NHD_SOURCE_ID = "usgs_nhd_hydrography"
NHD_SERVICE_URL = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer"
NHD_FLOWLINE_LAYER_ID = 6
NHD_AREA_LAYER_ID = 9

FEMA_SOURCE_ID = "fema_nfhl_flood_hazard"
FEMA_NFHL_SERVICE_URL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
FEMA_FLOOD_HAZARD_LAYER_ID = 28

SUPPORTED_DOWNLOADERS = {
    NWI_SOURCE_ID: {
        "downloader": "arcgis_rest_geojson",
        "service_url": NWI_SERVICE_URL,
        "output_name": NWI_SOURCE_ID,
        "layers": [
            {
                "layer_id": NWI_LAYER_ID,
                "layer_name": "Wetlands",
                "label_fields": ["name", "Name", "ATTRIBUTE", "WETLAND_TYPE"],
                "feature_type_fields": ["ATTRIBUTE", "WETLAND_TYPE"],
                "feature_subtype_fields": ["WETLAND_TYPE", "SYSTEM", "CLASS_NAME"],
                "original_id_fields": ["OBJECTID", "WETLAND_ID"],
                "date_fields": ["UPDATED", "DATE"],
                "quality_flag_fields": [],
                "source_citation_fields": [],
            }
        ],
    },
    NHD_SOURCE_ID: {
        "downloader": "arcgis_rest_geojson",
        "service_url": NHD_SERVICE_URL,
        "output_name": NHD_SOURCE_ID,
        "layers": [
            {
                "layer_id": NHD_FLOWLINE_LAYER_ID,
                "layer_name": "Flowline - Large Scale",
                "label_fields": ["gnis_name", "GNIS_NAME", "ftype", "FTYPE", "fcode", "FCODE"],
                "feature_type_fields": ["featuretypelabel", "ftype", "FTYPE", "fcode", "FCODE"],
                "feature_subtype_fields": ["fcode", "FCODE"],
                "original_id_fields": ["permanent_identifier", "Permanent_Identifier", "nhdplusid", "NHDPlusID", "objectid", "OBJECTID"],
                "date_fields": ["fdate", "FDATE", "resolution"],
                "quality_flag_fields": ["visibilityfilter", "VisibilityFilter"],
                "source_citation_fields": [],
            },
            {
                "layer_id": NHD_AREA_LAYER_ID,
                "layer_name": "Area - Large Scale",
                "label_fields": ["gnis_name", "GNIS_NAME", "ftype", "FTYPE", "fcode", "FCODE"],
                "feature_type_fields": ["featuretypelabel", "ftype", "FTYPE", "fcode", "FCODE"],
                "feature_subtype_fields": ["fcode", "FCODE"],
                "original_id_fields": ["permanent_identifier", "Permanent_Identifier", "nhdplusid", "NHDPlusID", "objectid", "OBJECTID"],
                "date_fields": ["fdate", "FDATE", "resolution"],
                "quality_flag_fields": ["visibilityfilter", "VisibilityFilter"],
                "source_citation_fields": [],
            },
        ],
    },
    FEMA_SOURCE_ID: {
        "downloader": "arcgis_rest_geojson",
        "service_url": FEMA_NFHL_SERVICE_URL,
        "output_name": FEMA_SOURCE_ID,
        "layers": [
            {
                "layer_id": FEMA_FLOOD_HAZARD_LAYER_ID,
                "layer_name": "Flood Hazard Zones",
                "label_fields": ["FLD_ZONE", "ZONE_SUBTY", "SFHA_TF", "SOURCE_CIT"],
                "feature_type_fields": ["FLD_ZONE"],
                "feature_subtype_fields": ["ZONE_SUBTY"],
                "original_id_fields": ["GFID", "FLD_AR_ID", "OBJECTID", "OBJECTID_1"],
                "date_fields": ["EFF_DATE", "REVERT_DATE", "PANEL_DATE"],
                "quality_flag_fields": ["SFHA_TF", "AR_REVERT", "DUAL_ZONE"],
                "source_citation_fields": ["SOURCE_CIT"],
            }
        ],
    },
}

FetchJson = Callable[[str, dict[str, Any]], dict[str, Any]]


class SourceAcquisitionError(RuntimeError):
    """Raised when source gap resolution or source acquisition cannot complete."""


def resolve_source_gaps(project_dir: Path) -> dict[str, Any]:
    """Write a source acquisition manifest without performing live downloads."""

    result = _resolve_source_gaps(project_dir.resolve(), preserve_downloads=True)
    _write_manifest(project_dir.resolve(), result)
    return result


def download_source(project_dir: Path, source_id: str, *, fetch_json: FetchJson | None = None) -> dict[str, Any]:
    """Download one supported public source and update the project registry."""

    return _download_source(project_dir.resolve(), source_id, fetch_json=fetch_json, write_manifest=True)


def prepare_sources(
    project_dir: Path,
    *,
    fetch_json: FetchJson | None = None,
    include_optional_sources: bool = False,
) -> dict[str, Any]:
    """Resolve source gaps, download supported missing sources, and write the manifest."""

    project_dir = project_dir.resolve()
    initial = _resolve_source_gaps(project_dir, preserve_downloads=True)
    downloads: list[dict[str, Any]] = []
    seen_download_keys = {_download_key(download) for download in initial.get("downloads", []) if isinstance(download, dict)}

    for gap in initial.get("gaps", []):
        if not isinstance(gap, dict):
            continue
        source_id = str(gap.get("source_id") or "")
        if not gap.get("download_supported"):
            continue
        if not _should_prepare_download(gap, include_optional_sources=include_optional_sources):
            continue
        attempt = _download_source(project_dir, source_id, fetch_json=fetch_json, write_manifest=False)
        for download in attempt.get("downloads", []):
            if not isinstance(download, dict):
                continue
            key = _download_key(download)
            if key not in seen_download_keys:
                downloads.append(download)
                seen_download_keys.add(key)

    final = _resolve_source_gaps(project_dir, preserve_downloads=True)
    existing_downloads = [download for download in final.get("downloads", []) if isinstance(download, dict)]
    merged_downloads = existing_downloads + [download for download in downloads if _download_key(download) not in {_download_key(item) for item in existing_downloads}]
    final["downloads"] = merged_downloads
    final["download_count"] = len(merged_downloads)
    final["include_optional_sources"] = include_optional_sources
    final["validation_issues"] = _merged_validation_issues(final.get("validation_issues", []), merged_downloads)
    _apply_download_statuses_to_gaps(final)
    _write_manifest(project_dir, final)
    return final


def load_source_acquisition_manifest(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / SOURCE_ACQUISITION_PATH
    if not path.exists():
        raise SourceAcquisitionError(f"Missing source acquisition manifest: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceAcquisitionError(f"Invalid source acquisition manifest JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceAcquisitionError(f"Source acquisition manifest must be a JSON object: {path}")
    return data


def _download_source(project_dir: Path, source_id: str, *, fetch_json: FetchJson | None, write_manifest: bool) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    initial = _resolve_source_gaps(project_dir, preserve_downloads=True)
    try:
        catalog = load_source_catalog()
    except SourceCatalogError as exc:
        raise SourceAcquisitionError(str(exc)) from exc
    source = catalog.sources.get(source_id)
    if source is None:
        raise SourceAcquisitionError(f"Unknown source_id '{source_id}'.")
    if not _source_download_supported(source):
        raise SourceAcquisitionError(f"Unsupported source downloader: {source_id}")

    download = _download_arcgis_geojson_source(project_dir, source, fetch_json=fetch_json)

    final = _resolve_source_gaps(project_dir, preserve_downloads=True)
    existing_downloads = [item for item in final.get("downloads", []) if isinstance(item, dict)]
    downloads = existing_downloads + [download]
    final["downloads"] = downloads
    final["download_count"] = len(downloads)
    final["validation_issues"] = _merged_validation_issues(initial.get("validation_issues", []), downloads)
    _apply_download_statuses_to_gaps(final)
    if write_manifest:
        _write_manifest(project_dir, final)
    return final


def _resolve_source_gaps(project_dir: Path, *, preserve_downloads: bool) -> dict[str, Any]:
    try:
        manifest = load_project_manifest(project_dir)
        report_profile = resolve_report_profile(manifest)
        catalog = load_source_catalog()
        registry = load_project_source_registry(project_dir)
    except (ProjectManifestError, ReportProfileError, SourceCatalogError) as exc:
        raise SourceAcquisitionError(str(exc)) from exc

    catalog_by_category = _catalog_by_category(catalog)
    tagged_inputs, input_issues = _tagged_source_inputs(project_dir, manifest, catalog, catalog_by_category)
    registry, registry_issues, registry_update_count = _register_tagged_source_inputs(
        project_dir,
        manifest,
        catalog,
        catalog_by_category,
        registry,
    )
    project_sources = registry.by_source_id()
    previous_downloads = _existing_downloads(project_dir) if preserve_downloads else []
    latest_download_status = _latest_download_status(previous_downloads)

    categories = list(report_profile.required_categories) + [
        category for category in report_profile.optional_categories if category not in report_profile.required_categories
    ]
    gaps: list[dict[str, Any]] = []
    for category in categories:
        requirement = "required" if category in report_profile.required_categories else "optional"
        catalog_sources = catalog_by_category.get(category, [])
        if not catalog_sources:
            gaps.append(_category_missing_gap(category, requirement))
            continue
        for source in catalog_sources:
            gaps.append(
                _source_gap(
                    project_dir=project_dir,
                    source=source,
                    requirement=requirement,
                    project_source=project_sources.get(source.source_id),
                    tagged_inputs=tagged_inputs,
                    latest_download_status=latest_download_status,
                )
            )

    validation_issues = input_issues + registry_issues + _unknown_project_source_issues(project_sources, catalog)
    validation_issues = _merged_validation_issues(validation_issues, previous_downloads)
    output_path = project_dir / SOURCE_ACQUISITION_PATH
    counts: dict[str, int] = {}
    for gap in gaps:
        status = str(gap.get("status", ""))
        counts[status] = counts.get(status, 0) + 1

    return {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "report_profile": {
            "profile_id": report_profile.profile_id,
            "name": report_profile.name,
        },
        "source_catalog_version": catalog.catalog_version,
        "source_registry_path": str(project_dir / "config" / "sources.json"),
        "gap_count": len(gaps),
        "gap_status_counts": counts,
        "gaps": gaps,
        "tagged_source_inputs": _tagged_input_records(tagged_inputs),
        "registered_project_input_source_count": registry_update_count,
        "downloads": previous_downloads,
        "download_count": len(previous_downloads),
        "validation_issues": validation_issues,
        "output_path": str(output_path),
    }


def _download_arcgis_geojson_source(project_dir: Path, source: SourceDefinition, *, fetch_json: FetchJson | None) -> dict[str, Any]:
    access_date = _utc_now()
    config = _download_config(source)
    service_url = str(config["service_url"])
    layers = _download_layers(config)
    output_name = str(config.get("output_name") or source.source_id)
    output_path = project_dir / SOURCE_DOWNLOADS_DIR / f"{output_name}.geojson"
    single_layer = layers[0] if len(layers) == 1 else None
    query_url = _layer_query_url(service_url, single_layer["layer_id"]) if single_layer else None
    base_record = {
        "source_id": source.source_id,
        "source_name": source.name,
        "source_category": source.category,
        "status": "failed",
        "downloader": str(config.get("downloader") or "arcgis_rest_geojson"),
        "service_url": service_url,
        "layer_id": single_layer["layer_id"] if single_layer else None,
        "query_url": query_url,
        "layers": _layer_manifest_records(service_url, layers),
        "source_url": source.url,
        "access_date": access_date,
        "output_path": str(output_path),
        "feature_count": 0,
        "checksum_sha256": "",
        "requested_bounds_wgs84": None,
        "source_limitations": source.known_limitations,
        "validation_issues": [],
        "warnings": [],
    }

    existing = _existing_local_project_source(project_dir, source.source_id)
    if existing is not None and existing.status != "downloaded":
        record = dict(base_record)
        record.update(
            {
                "status": "skipped_existing_local",
                "output_path": existing.path,
                "validation_issues": [
                    _issue(
                        "info",
                        "existing_local_source_preserved",
                        "Existing reviewer-supplied local source was preserved instead of being replaced by a download.",
                        existing.path or source.source_id,
                        source_id=source.source_id,
                    )
                ],
            }
        )
        return record

    try:
        bounds = _project_analysis_bounds_wgs84(project_dir)
        fetcher = fetch_json or _fetch_json
        feature_collection, layer_records = _query_arcgis_geojson_layers(
            source=source,
            config=config,
            layers=layers,
            bounds=bounds,
            fetch_json=fetcher,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(feature_collection, indent=2).encode("utf-8")
        output_path.write_bytes(payload)
        checksum = hashlib.sha256(payload).hexdigest()
        _register_downloaded_source(project_dir, source, output_path, access_date)
        feature_count = len(feature_collection.get("features", []))
        record = dict(base_record)
        record.update(
            {
                "status": "downloaded",
                "output_path": str(output_path),
                "feature_count": feature_count,
                "checksum_sha256": checksum,
                "requested_bounds_wgs84": bounds,
                "layers": layer_records,
                "service_record_limit": layer_records[0]["service_record_limit"] if len(layer_records) == 1 else None,
            }
        )
        if record["feature_count"] == 0:
            record["warnings"] = [
                _issue(
                    "info",
                    "downloaded_source_empty",
                    f"{source.name} returned no features inside the project analysis bounds.",
                    str(output_path),
                    source_id=source.source_id,
                )
            ]
        return record
    except Exception as exc:  # noqa: BLE001 - downloader failures are intentionally nonfatal.
        record = dict(base_record)
        issue = _issue(
            "warning",
            "source_download_failed",
            f"Unable to download {source.name} source: {exc}",
            query_url or service_url,
            source_id=source.source_id,
        )
        record["validation_issues"] = [issue]
        record["warnings"] = [issue]
        return record


def _query_arcgis_geojson_layers(
    *,
    source: SourceDefinition,
    config: dict[str, Any],
    layers: list[dict[str, Any]],
    bounds: dict[str, float],
    fetch_json: FetchJson,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    service_url = str(config["service_url"])
    features: list[dict[str, Any]] = []
    layer_records: list[dict[str, Any]] = []
    for layer in layers:
        layer_features, service_limit = _query_arcgis_geojson_layer(
            source=source,
            service_url=service_url,
            layer=layer,
            bounds=bounds,
            fetch_json=fetch_json,
        )
        normalized_features = [
            _normalized_download_feature(feature, source=source, layer=layer)
            for feature in layer_features
            if isinstance(feature, dict)
        ]
        features.extend(normalized_features)
        layer_records.append(
            {
                "layer_id": layer["layer_id"],
                "layer_name": layer["layer_name"],
                "service_url": service_url,
                "layer_url": _layer_url(service_url, layer["layer_id"]),
                "query_url": _layer_query_url(service_url, layer["layer_id"]),
                "feature_count": len(normalized_features),
                "service_record_limit": service_limit,
            }
        )
    return {
        "type": "FeatureCollection",
        "name": str(config.get("output_name") or source.source_id),
        "features": features,
    }, layer_records


def _query_arcgis_geojson_layer(
    *,
    source: SourceDefinition,
    service_url: str,
    layer: dict[str, Any],
    bounds: dict[str, float],
    fetch_json: FetchJson,
) -> tuple[list[dict[str, Any]], int]:
    layer_url = _layer_url(service_url, layer["layer_id"])
    query_url = _layer_query_url(service_url, layer["layer_id"])
    metadata = fetch_json(layer_url, {"f": "pjson"})
    page_size = _service_record_limit(metadata)
    features: list[dict[str, Any]] = []
    offset = 0
    geometry = {
        "xmin": bounds["west"],
        "ymin": bounds["south"],
        "xmax": bounds["east"],
        "ymax": bounds["north"],
        "spatialReference": {"wkid": 4326},
    }
    while True:
        page = fetch_json(
            query_url,
            {
                "f": "geojson",
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "geometry": json.dumps(geometry, separators=(",", ":")),
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outSR": "4326",
                "resultOffset": str(offset),
                "resultRecordCount": str(page_size),
            },
        )
        if isinstance(page.get("error"), dict):
            message = page["error"].get("message") or page["error"]
            raise SourceAcquisitionError(f"{source.source_id} layer {layer['layer_id']} service returned an error: {message}")
        page_features = page.get("features", [])
        if not isinstance(page_features, list):
            raise SourceAcquisitionError(f"{source.source_id} layer {layer['layer_id']} GeoJSON response did not include a feature list.")
        features.extend(page_features)
        if not page_features:
            break
        if not page.get("exceededTransferLimit") and len(page_features) < page_size:
            break
        offset += len(page_features)

    return features, page_size


def _download_config(source: SourceDefinition) -> dict[str, Any]:
    catalog_config = source.download if isinstance(source.download, dict) else {}
    if catalog_config.get("supported"):
        config = dict(catalog_config)
    else:
        config = dict(SUPPORTED_DOWNLOADERS.get(source.source_id, {}))
    if str(config.get("downloader") or "") != "arcgis_rest_geojson":
        raise SourceAcquisitionError(f"Unsupported downloader type for source '{source.source_id}'.")
    if not str(config.get("service_url") or "").strip():
        raise SourceAcquisitionError(f"Source '{source.source_id}' download metadata requires a service_url.")
    return config


def _source_download_supported(source: SourceDefinition) -> bool:
    catalog_config = source.download if isinstance(source.download, dict) else {}
    if catalog_config.get("supported"):
        return str(catalog_config.get("downloader") or "") == "arcgis_rest_geojson"
    return source.source_id in SUPPORTED_DOWNLOADERS


def _download_layers(config: dict[str, Any]) -> list[dict[str, Any]]:
    raw_layers = config.get("layers", [])
    if not isinstance(raw_layers, list) or not raw_layers:
        raise SourceAcquisitionError("ArcGIS REST download metadata requires a non-empty layers list.")
    layers: list[dict[str, Any]] = []
    for raw_layer in raw_layers:
        if not isinstance(raw_layer, dict):
            raise SourceAcquisitionError("Each ArcGIS REST download layer must be an object.")
        try:
            layer_id = int(raw_layer["layer_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SourceAcquisitionError("Each ArcGIS REST download layer requires integer layer_id.") from exc
        layer_name = str(raw_layer.get("layer_name") or f"Layer {layer_id}")
        layers.append(
            {
                "layer_id": layer_id,
                "layer_name": layer_name,
                "label_fields": _string_list(raw_layer.get("label_fields", [])),
                "feature_type_fields": _string_list(raw_layer.get("feature_type_fields", [])),
                "feature_subtype_fields": _string_list(raw_layer.get("feature_subtype_fields", [])),
                "original_id_fields": _string_list(raw_layer.get("original_id_fields", [])),
                "date_fields": _string_list(raw_layer.get("date_fields", [])),
                "quality_flag_fields": _string_list(raw_layer.get("quality_flag_fields", [])),
                "source_citation_fields": _string_list(raw_layer.get("source_citation_fields", [])),
            }
        )
    return layers


def _layer_manifest_records(service_url: str, layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "layer_id": layer["layer_id"],
            "layer_name": layer["layer_name"],
            "service_url": service_url,
            "layer_url": _layer_url(service_url, layer["layer_id"]),
            "query_url": _layer_query_url(service_url, layer["layer_id"]),
            "feature_count": 0,
            "service_record_limit": None,
        }
        for layer in layers
    ]


def _normalized_download_feature(feature: dict[str, Any], *, source: SourceDefinition, layer: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(feature)
    raw_properties = feature.get("properties", {})
    properties = dict(raw_properties) if isinstance(raw_properties, dict) else {}
    label = _first_property_value(properties, layer.get("label_fields", []))
    feature_type = _first_property_value(properties, layer.get("feature_type_fields", []))
    feature_subtype = _first_property_value(properties, layer.get("feature_subtype_fields", []))
    original_id = _first_property_value(properties, layer.get("original_id_fields", []))
    feature_date = _first_property_value(properties, layer.get("date_fields", []))
    quality_flag = _first_property_value(properties, layer.get("quality_flag_fields", []))
    source_citation = _first_property_value(properties, layer.get("source_citation_fields", []))
    if not label:
        label = feature_type or layer["layer_name"]
    properties.update(
        {
            "review_assist_source_id": source.source_id,
            "review_assist_source_name": source.name,
            "review_assist_source_category": source.category,
            "review_assist_layer_id": layer["layer_id"],
            "review_assist_layer_name": layer["layer_name"],
            "review_assist_feature_label": label,
            "review_assist_feature_type": feature_type,
            "review_assist_feature_subtype": feature_subtype,
            "review_assist_feature_original_id": original_id,
            "review_assist_feature_date": feature_date,
            "review_assist_quality_flag": quality_flag,
            "review_assist_source_citation": source_citation,
        }
    )
    normalized["properties"] = properties
    return normalized


def _first_property_value(properties: dict[str, Any], fields: list[str]) -> str:
    by_lower = {str(key).lower(): key for key in properties}
    for field in fields:
        key = field if field in properties else by_lower.get(str(field).lower())
        if key is None:
            continue
        value = properties.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


def _layer_url(service_url: str, layer_id: int) -> str:
    return f"{service_url.rstrip('/')}/{layer_id}"


def _layer_query_url(service_url: str, layer_id: int) -> str:
    return f"{_layer_url(service_url, layer_id)}/query"


def _fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode({key: str(value) for key, value in params.items()})
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"User-Agent": "review-assist-source-acquisition/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise SourceAcquisitionError(str(exc)) from exc
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise SourceAcquisitionError(f"Expected JSON object from source service: {url}")
    return data


def _service_record_limit(metadata: dict[str, Any]) -> int:
    raw_limit = metadata.get("maxRecordCount", 1000)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = 1000
    return max(1, min(limit, 10000))


def _project_analysis_bounds_wgs84(project_dir: Path) -> dict[str, float]:
    bounds_path = project_dir / PROJECT_ANALYSIS_BOUNDS_PATH
    if not bounds_path.exists():
        try:
            build_project_geometry(project_dir)
        except ProjectGeometryError as exc:
            raise SourceAcquisitionError(str(exc)) from exc
    gdf = gpd.read_file(bounds_path)
    if gdf.empty:
        raise SourceAcquisitionError(f"Project analysis bounds are empty: {bounds_path}")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    total_bounds = gdf.to_crs("EPSG:4326").total_bounds
    return {
        "west": float(total_bounds[0]),
        "south": float(total_bounds[1]),
        "east": float(total_bounds[2]),
        "north": float(total_bounds[3]),
    }


def _register_downloaded_source(project_dir: Path, source: SourceDefinition, output_path: Path, access_date: str) -> None:
    registry = load_project_source_registry(project_dir)
    existing = registry.by_source_id()
    old_source = existing.get(source.source_id)
    if old_source is not None and _has_existing_local_path(project_dir, old_source) and old_source.status != "downloaded":
        return

    metadata = dict(old_source.metadata) if old_source else {}
    metadata.update(
        {
            "source_url": source.url,
            "access_date": access_date,
            "citation": source.name,
            "attribution": source.publisher,
            "review_notes": source.known_limitations,
        }
    )
    updated = ProjectSource(
        source_id=source.source_id,
        enabled=True,
        access_method="local_file",
        path=_display_path(output_path, project_dir),
        role=old_source.role if old_source else "constraint_screening",
        buffer_feet=old_source.buffer_feet if old_source else None,
        notes=old_source.notes if old_source else "Downloaded public source layer.",
        status="downloaded",
        metadata=metadata,
    )
    _save_updated_source(project_dir, registry, updated)


def _register_tagged_source_inputs(
    project_dir: Path,
    manifest: ProjectManifest,
    catalog: SourceCatalog,
    catalog_by_category: dict[str, list[SourceDefinition]],
    registry: ProjectSourceRegistry,
) -> tuple[ProjectSourceRegistry, list[dict[str, Any]], int]:
    issues: list[dict[str, Any]] = []
    update_count = 0
    current = registry
    for project_input in manifest.inputs:
        source = _source_for_tagged_input(project_input, catalog, catalog_by_category)
        if source is None:
            continue
        input_path = (project_dir / project_input.path).resolve()
        if not input_path.exists():
            issues.append(
                _issue(
                    "warning",
                    "missing_project_input_source",
                    f"Project input source layer does not exist: {project_input.path}",
                    str(input_path),
                    source_id=source.source_id,
                )
            )
            continue
        existing = current.by_source_id().get(source.source_id)
        if existing is not None and _has_existing_local_path(project_dir, existing) and existing.status not in {"downloaded", "provided_in_input"}:
            continue
        updated = ProjectSource(
            source_id=source.source_id,
            enabled=True,
            access_method="local_file",
            path=_display_path(input_path, project_dir),
            role=existing.role if existing else "constraint_screening",
            buffer_feet=existing.buffer_feet if existing else None,
            notes=existing.notes if existing else "Provided in project input package.",
            status="provided_in_input",
            metadata=existing.metadata if existing else {},
        )
        current = _save_updated_source(project_dir, current, updated)
        update_count += 1
    return current, issues, update_count


def _save_updated_source(project_dir: Path, registry: ProjectSourceRegistry, updated: ProjectSource) -> ProjectSourceRegistry:
    sources: list[ProjectSource] = []
    replaced = False
    for source in registry.sources:
        if source.source_id == updated.source_id:
            sources.append(updated)
            replaced = True
        else:
            sources.append(source)
    if not replaced:
        sources.append(updated)
    saved = ProjectSourceRegistry(project_id=registry.project_id, sources=sources)
    save_project_source_registry(project_dir, saved)
    return saved


def _tagged_source_inputs(
    project_dir: Path,
    manifest: ProjectManifest,
    catalog: SourceCatalog,
    catalog_by_category: dict[str, list[SourceDefinition]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    tagged: dict[str, list[dict[str, Any]]] = defaultdict(list)
    issues: list[dict[str, Any]] = []
    for project_input in manifest.inputs:
        if not project_input.is_source_layer:
            continue
        source = _source_for_tagged_input(project_input, catalog, catalog_by_category)
        if source is None:
            issues.extend(_tagged_input_issues(project_input, catalog, catalog_by_category))
            continue
        input_path = (project_dir / project_input.path).resolve()
        if not input_path.exists():
            issues.append(
                _issue(
                    "warning",
                    "missing_project_input_source",
                    f"Project input source layer does not exist: {project_input.path}",
                    str(input_path),
                    source_id=source.source_id,
                )
            )
        tagged[source.source_id].append(
            {
                "path": project_input.path,
                "resolved_path": str(input_path),
                "role": project_input.role,
                "source_id": source.source_id,
                "source_category": source.category,
                "exists": input_path.exists(),
            }
        )
    return dict(tagged), issues


def _source_for_tagged_input(
    project_input: ProjectInput,
    catalog: SourceCatalog,
    catalog_by_category: dict[str, list[SourceDefinition]],
) -> SourceDefinition | None:
    if project_input.source_id:
        return catalog.sources.get(project_input.source_id)
    if not project_input.source_category:
        return None
    sources = catalog_by_category.get(project_input.source_category, [])
    if len(sources) == 1:
        return sources[0]
    return None


def _tagged_input_issues(
    project_input: ProjectInput,
    catalog: SourceCatalog,
    catalog_by_category: dict[str, list[SourceDefinition]],
) -> list[dict[str, Any]]:
    if project_input.source_id and project_input.source_id not in catalog.sources:
        return [
            _issue(
                "warning",
                "unknown_project_input_source_id",
                f"Project input source_id '{project_input.source_id}' is not present in the source catalog.",
                project_input.path,
                source_id=project_input.source_id,
            )
        ]
    if project_input.source_category:
        sources = catalog_by_category.get(project_input.source_category, [])
        if not sources:
            return [
                _issue(
                    "warning",
                    "unknown_project_input_source_category",
                    f"Project input source_category '{project_input.source_category}' is not present in the source catalog.",
                    project_input.path,
                )
            ]
        return [
            _issue(
                "warning",
                "ambiguous_project_input_source_category",
                f"Project input source_category '{project_input.source_category}' matches multiple catalog sources; add source_id to register it.",
                project_input.path,
            )
        ]
    return []


def _source_gap(
    *,
    project_dir: Path,
    source: SourceDefinition,
    requirement: str,
    project_source: ProjectSource | None,
    tagged_inputs: dict[str, list[dict[str, Any]]],
    latest_download_status: dict[str, str],
) -> dict[str, Any]:
    input_records = tagged_inputs.get(source.source_id, [])
    status, reason = _gap_status(project_dir, source, requirement, project_source, input_records, latest_download_status)
    return {
        "source_id": source.source_id,
        "name": source.name,
        "category": source.category,
        "requirement": requirement,
        "status": status,
        "reason": reason,
        "download_supported": _source_download_supported(source),
        "access_methods": source.access_methods,
        "public_or_restricted": source.public_or_restricted,
        "source_url": source.url,
        "known_limitations": source.known_limitations,
        "project_registry": _project_source_record(project_dir, project_source),
        "input_paths": [item["path"] for item in input_records],
        "provenance": {
            "catalog_source_id": source.source_id,
            "catalog_url": source.url,
            "latest_download_status": latest_download_status.get(source.source_id),
        },
    }


def _gap_status(
    project_dir: Path,
    source: SourceDefinition,
    requirement: str,
    project_source: ProjectSource | None,
    input_records: list[dict[str, Any]],
    latest_download_status: dict[str, str],
) -> tuple[str, str]:
    existing_input_records = [item for item in input_records if item.get("exists")]
    if existing_input_records and _has_existing_local_path(project_dir, project_source):
        return "provided_in_input", "Project input package includes this source layer and it is registered for analysis."
    if project_source is not None and _has_existing_local_path(project_dir, project_source):
        if project_source.status == "downloaded":
            return "downloaded", "Downloaded source data is available in the workspace."
        if project_source.status == "provided_in_input":
            return "provided_in_input", "Project input package includes this source layer and it is registered for analysis."
        return "registered_local", "Reviewer-supplied or locally registered source data is available in the workspace."
    if latest_download_status.get(source.source_id) == "failed":
        return "failed", "The latest supported download attempt failed; the workflow can continue with a caveat."
    if requirement == "optional":
        return "optional", "Optional source is not required for this report profile."
    if _public_future_download(source):
        if _source_download_supported(source):
            return "downloadable", "Public source data is supported by an implemented downloader but has not been downloaded."
        return "unsupported_download", "Public source data appears downloadable, but no downloader is implemented yet."
    if _gated_source(source):
        return "gated", "Source requires restricted, sensitive, or qualified-access handling."
    if _manual_source(source):
        return "manual", "Source requires manual lookup, manual download, or reviewer-supplied material."
    return "missing", "No supported source path is available for this required catalog source."


def _category_missing_gap(category: str, requirement: str) -> dict[str, Any]:
    return {
        "source_id": None,
        "name": category,
        "category": category,
        "requirement": requirement,
        "status": "optional" if requirement == "optional" else "missing",
        "reason": "No catalog source candidate exists for this category.",
        "download_supported": False,
        "access_methods": [],
        "public_or_restricted": "",
        "source_url": "",
        "known_limitations": "",
        "project_registry": {"registered": False},
        "input_paths": [],
        "provenance": {},
    }


def _project_source_record(project_dir: Path, project_source: ProjectSource | None) -> dict[str, Any]:
    if project_source is None:
        return {
            "registered": False,
            "enabled": False,
            "access_method": "",
            "path": None,
            "status": "not_registered",
            "path_exists": False,
        }
    path = resolve_project_source_path(project_dir, project_source)
    return {
        "registered": True,
        "enabled": project_source.enabled,
        "access_method": project_source.access_method,
        "path": project_source.path,
        "status": project_source.status,
        "path_exists": bool(path and path.exists()),
    }


def _apply_download_statuses_to_gaps(manifest: dict[str, Any]) -> None:
    downloads = [download for download in manifest.get("downloads", []) if isinstance(download, dict)]
    latest_status = _latest_download_status(downloads)
    for gap in manifest.get("gaps", []):
        if not isinstance(gap, dict):
            continue
        source_id = str(gap.get("source_id") or "")
        if latest_status.get(source_id) != "failed":
            continue
        if gap.get("status") in {"downloaded", "registered_local", "provided_in_input"}:
            continue
        gap["status"] = "failed"
        gap["reason"] = "The latest supported download attempt failed; the workflow can continue with a caveat."
    counts: dict[str, int] = {}
    for gap in manifest.get("gaps", []):
        if isinstance(gap, dict):
            status = str(gap.get("status", ""))
            counts[status] = counts.get(status, 0) + 1
    manifest["gap_status_counts"] = counts


def _existing_local_project_source(project_dir: Path, source_id: str) -> ProjectSource | None:
    registry = load_project_source_registry(project_dir)
    source = registry.by_source_id().get(source_id)
    if source is not None and _has_existing_local_path(project_dir, source):
        return source
    return None


def _has_existing_local_path(project_dir: Path, source: ProjectSource | None) -> bool:
    if source is None or not source.enabled or source.access_method != "local_file" or not source.path:
        return False
    path = resolve_project_source_path(project_dir, source)
    return bool(path and path.exists())


def _catalog_by_category(catalog: SourceCatalog) -> dict[str, list[SourceDefinition]]:
    grouped: dict[str, list[SourceDefinition]] = defaultdict(list)
    for source in catalog.sources.values():
        grouped[source.category].append(source)
    return {category: sorted(items, key=lambda item: item.source_id) for category, items in grouped.items()}


def _unknown_project_source_issues(project_sources: dict[str, ProjectSource], catalog: SourceCatalog) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for source_id in sorted(project_sources):
        if source_id not in catalog.sources:
            issues.append(
                _issue(
                    "warning",
                    "unknown_project_source",
                    f"Project source '{source_id}' is not present in the source catalog.",
                    "config/sources.json",
                    source_id=source_id,
                )
            )
    return issues


def _existing_downloads(project_dir: Path) -> list[dict[str, Any]]:
    manifest_path = project_dir / SOURCE_ACQUISITION_PATH
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    downloads = data.get("downloads", []) if isinstance(data, dict) else []
    if not isinstance(downloads, list):
        return []
    return [download for download in downloads if isinstance(download, dict)]


def _latest_download_status(downloads: list[dict[str, Any]]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for download in downloads:
        source_id = str(download.get("source_id") or "")
        status = str(download.get("status") or "")
        if source_id and status:
            statuses[source_id] = status
    return statuses


def _merged_validation_issues(issues: Any, downloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = [dict(issue) for issue in issues if isinstance(issue, dict)] if isinstance(issues, list) else []
    seen = {_issue_key(issue) for issue in merged}
    for download in downloads:
        for field in ("validation_issues", "warnings"):
            raw_issues = download.get(field, [])
            if not isinstance(raw_issues, list):
                continue
            for issue in raw_issues:
                if not isinstance(issue, dict):
                    continue
                key = _issue_key(issue)
                if key not in seen:
                    merged.append(dict(issue))
                    seen.add(key)
    return merged


def _issue_key(issue: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(issue.get("severity", "")),
        str(issue.get("code", "")),
        str(issue.get("source_id", "")),
        str(issue.get("location", "")),
    )


def _download_key(download: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(download.get("source_id", "")),
        str(download.get("status", "")),
        str(download.get("access_date", "")),
        str(download.get("output_path", "")),
    )


def _should_prepare_download(gap: dict[str, Any], *, include_optional_sources: bool) -> bool:
    status = str(gap.get("status") or "")
    requirement = str(gap.get("requirement") or "")
    if requirement == "required":
        return status in {"downloadable", "failed"}
    if include_optional_sources and requirement == "optional":
        return status in {"optional", "downloadable", "failed"}
    return False


def _tagged_input_records(tagged_inputs: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source_id, inputs in sorted(tagged_inputs.items()):
        records.append(
            {
                "source_id": source_id,
                "input_count": len(inputs),
                "inputs": inputs,
            }
        )
    return records


def _write_manifest(project_dir: Path, data: dict[str, Any]) -> None:
    output_path = project_dir / SOURCE_ACQUISITION_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data["output_path"] = str(output_path)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _public_future_download(source: SourceDefinition) -> bool:
    return "future_download" in source.access_methods and "public" in source.public_or_restricted


def _gated_source(source: SourceDefinition) -> bool:
    gated_markers = ("restricted", "sensitive")
    return any(marker in source.public_or_restricted for marker in gated_markers) or "restricted" in source.tier


def _manual_source(source: SourceDefinition) -> bool:
    manual_methods = {"manual_document", "manual_lookup", "manual_download", "reviewer_supplied"}
    return bool(manual_methods.intersection(source.access_methods))


def _display_path(path: Path, project_dir: Path) -> str:
    try:
        return path.resolve().relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


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
