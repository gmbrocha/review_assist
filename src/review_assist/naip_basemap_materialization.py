"""Project-local NAIP basemap materialization from public STAC COG assets."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import box, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .basemaps import (
    PROJECT_LOCAL_NAIP_FILENAME,
    PROJECT_LOCAL_NAIP_METADATA_FILENAME,
    PROJECT_LOCAL_NAIP_ROOT,
    USDA_NAIP_SOURCE_ID,
    USDA_NAIP_SOURCE_NAME,
    discover_project_local_naip_basemaps,
)
from .project_area import PROJECT_AREA_PATH, ProjectAreaError, build_project_area, load_project_area
from .project_geometry import PROJECT_ANALYSIS_BOUNDS_PATH, ProjectGeometryError, build_project_geometry
from .projects import ProjectManifestError, load_project_manifest


PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
NAIP_COLLECTION_ID = "naip"
NAIP_ASSET_KEY = "image"
NAIP_PROVIDER = "Microsoft Planetary Computer"
NAIP_RUN_MANIFEST_PATH = PROJECT_LOCAL_NAIP_ROOT / "naip_basemap_materialization.json"
DEFAULT_MAX_PIXELS = 25_000_000
DEFAULT_MAX_TILES = 12
DEFAULT_TIMEOUT_SECONDS = 60


class NaipBasemapMaterializationError(RuntimeError):
    """Raised when NAIP basemap materialization cannot complete."""


class NaipBasemapDependencyError(NaipBasemapMaterializationError):
    """Raised when optional imagery dependencies are unavailable."""


@dataclass(frozen=True)
class _ImageryDependencies:
    requests: Any
    rasterio: Any
    merge: Any
    transform_bounds: Any
    array_bounds: Any
    WarpedVRT: Any
    planetary_computer: Any


def materialize_naip_basemap(
    project_dir: Path,
    *,
    year: int | None = None,
    max_pixels: int = DEFAULT_MAX_PIXELS,
    max_tiles: int = DEFAULT_MAX_TILES,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    refresh: bool = False,
    fail_on_error: bool = False,
) -> dict[str, Any]:
    """Materialize an AOI-clipped NAIP basemap sidecar for a project."""

    project_dir = project_dir.resolve()
    started_at = _utc_now()
    try:
        result = _materialize_naip_basemap(
            project_dir,
            year=year,
            max_pixels=max_pixels,
            max_tiles=max_tiles,
            timeout_seconds=timeout_seconds,
            refresh=refresh,
            started_at=started_at,
        )
    except (NaipBasemapMaterializationError, ProjectManifestError, ProjectGeometryError, ProjectAreaError) as exc:
        result = _failure_result(
            project_dir,
            started_at=started_at,
            year=year,
            max_pixels=max_pixels,
            max_tiles=max_tiles,
            timeout_seconds=timeout_seconds,
            message=str(exc),
        )
    except Exception as exc:  # pragma: no cover - defensive boundary for external raster/STAC libs.
        result = _failure_result(
            project_dir,
            started_at=started_at,
            year=year,
            max_pixels=max_pixels,
            max_tiles=max_tiles,
            timeout_seconds=timeout_seconds,
            message=f"Unexpected NAIP basemap materialization failure: {exc}",
        )
    _write_run_manifest(project_dir, result)
    if fail_on_error and not result.get("success"):
        raise NaipBasemapMaterializationError(str(result.get("message") or "NAIP basemap materialization failed."))
    return result


def select_naip_items(
    items: list[dict[str, Any]],
    aoi_geometry: BaseGeometry,
    *,
    year: int | None = None,
    max_tiles: int = DEFAULT_MAX_TILES,
) -> list[dict[str, Any]]:
    """Select a deterministic latest-year tile set from STAC item dictionaries."""

    candidates: list[dict[str, Any]] = []
    for item in items:
        item_year = _item_year(item)
        if year is not None and item_year != year:
            continue
        if NAIP_ASSET_KEY not in _item_assets(item):
            continue
        overlap = _item_overlap_area(item, aoi_geometry)
        if overlap <= 0:
            continue
        candidates.append(
            {
                "item": item,
                "year": item_year or 0,
                "timestamp": _item_timestamp(item),
                "overlap": overlap,
                "id": str(item.get("id") or ""),
            }
        )
    if not candidates:
        return []
    selected_year = year if year is not None else max(candidate["year"] for candidate in candidates)
    selected = [candidate for candidate in candidates if candidate["year"] == selected_year]
    if len(selected) > max_tiles:
        raise NaipBasemapMaterializationError(
            f"NAIP query selected {len(selected)} intersecting tile(s), exceeding --max-tiles {max_tiles}."
        )
    selected.sort(key=lambda candidate: (-float(candidate["timestamp"]), -float(candidate["overlap"]), str(candidate["id"])))
    return [dict(candidate["item"]) for candidate in selected]


def _materialize_naip_basemap(
    project_dir: Path,
    *,
    year: int | None,
    max_pixels: int,
    max_tiles: int,
    timeout_seconds: int,
    refresh: bool,
    started_at: str,
) -> dict[str, Any]:
    _validate_limits(max_pixels=max_pixels, max_tiles=max_tiles, timeout_seconds=timeout_seconds)
    manifest = load_project_manifest(project_dir)
    existing = _existing_sidecar(project_dir, year)
    if existing is not None and not refresh:
        project_area = build_project_area(project_dir)
        return _success_result(
            project_dir,
            started_at=started_at,
            project_id=manifest.project_id,
            project_name=manifest.name,
            status="reused",
            action="reused_existing_sidecar",
            sidecar_path=Path(str(existing["path"])),
            metadata_path=Path(str(existing["metadata_path"])) if existing.get("metadata_path") else None,
            project_area_path=Path(str(project_area.get("output_path") or project_dir / PROJECT_AREA_PATH)),
            year=_safe_int(existing.get("year")) or year,
            item_ids=[str(item_id) for item_id in existing.get("item_ids", [])] if isinstance(existing.get("item_ids"), list) else [],
            limits=_limits(max_pixels, max_tiles, timeout_seconds),
        )

    deps = _load_imagery_dependencies()
    aoi_gdf, aoi_geometry = _load_or_build_aoi(project_dir)
    aoi_geometry_wgs84 = unary_union([geometry for geometry in aoi_gdf.geometry if geometry is not None and not geometry.is_empty])
    if aoi_geometry_wgs84.is_empty:
        raise NaipBasemapMaterializationError("Project analysis bounds are empty; NAIP basemap materialization requires a non-empty AOI.")
    aoi_bounds = _bounds_dict(aoi_geometry_wgs84.bounds)
    items = _query_naip_items(mapping(aoi_geometry_wgs84), year=year, max_tiles=max_tiles, timeout_seconds=timeout_seconds, deps=deps)
    selected_items = select_naip_items(items, aoi_geometry_wgs84, year=year, max_tiles=max_tiles)
    if not selected_items:
        raise NaipBasemapMaterializationError("No NAIP COG tiles intersect the project AOI for the requested criteria.")
    selected_year = _item_year(selected_items[0])
    if selected_year is None:
        raise NaipBasemapMaterializationError("Selected NAIP item does not include a usable year/datetime.")

    output_dir = project_dir / PROJECT_LOCAL_NAIP_ROOT / str(selected_year)
    output_path = output_dir / PROJECT_LOCAL_NAIP_FILENAME
    metadata_path = output_dir / PROJECT_LOCAL_NAIP_METADATA_FILENAME
    if (output_path.exists() or metadata_path.exists()) and not refresh:
        raise NaipBasemapMaterializationError(
            f"NAIP basemap sidecar already exists for {selected_year}; use --refresh or --force to overwrite it."
        )

    raster_info = _write_basemap_raster(
        selected_items,
        output_path,
        aoi_bounds=aoi_bounds,
        max_pixels=max_pixels,
        timeout_seconds=timeout_seconds,
        deps=deps,
    )
    metadata = _sidecar_metadata(
        project_dir=project_dir,
        output_path=output_path,
        selected_items=selected_items,
        selected_year=selected_year,
        aoi_bounds=aoi_bounds,
        raster_info=raster_info,
        limits=_limits(max_pixels, max_tiles, timeout_seconds),
    )
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    project_area = build_project_area(project_dir)
    return _success_result(
        project_dir,
        started_at=started_at,
        project_id=manifest.project_id,
        project_name=manifest.name,
        status="completed",
        action="materialized",
        sidecar_path=output_path,
        metadata_path=metadata_path,
        project_area_path=Path(str(project_area.get("output_path") or project_dir / PROJECT_AREA_PATH)),
        year=selected_year,
        item_ids=[str(item.get("id") or "") for item in selected_items if str(item.get("id") or "").strip()],
        limits=_limits(max_pixels, max_tiles, timeout_seconds),
        raster_info=raster_info,
    )


def _load_imagery_dependencies() -> _ImageryDependencies:
    missing: list[str] = []
    try:
        import requests
    except ImportError:
        requests = None
        missing.append("requests")
    try:
        import rasterio
        from rasterio.merge import merge
        from rasterio.transform import array_bounds
        from rasterio.vrt import WarpedVRT
        from rasterio.warp import transform_bounds
    except ImportError:
        rasterio = None
        merge = None
        transform_bounds = None
        array_bounds = None
        WarpedVRT = None
        missing.append("rasterio")
    try:
        import planetary_computer
    except ImportError:
        planetary_computer = None
        missing.append("planetary-computer")
    try:
        import pystac_client  # noqa: F401
    except ImportError:
        missing.append("pystac-client")
    if missing:
        names = ", ".join(sorted(set(missing)))
        raise NaipBasemapDependencyError(
            f"NAIP basemap materialization requires optional imagery dependencies ({names}). "
            'Install them with: pip install "review-assist[imagery]".'
        )
    return _ImageryDependencies(
        requests=requests,
        rasterio=rasterio,
        merge=merge,
        transform_bounds=transform_bounds,
        array_bounds=array_bounds,
        WarpedVRT=WarpedVRT,
        planetary_computer=planetary_computer,
    )


def _load_or_build_aoi(project_dir: Path) -> tuple[gpd.GeoDataFrame, BaseGeometry]:
    bounds_path = project_dir / PROJECT_ANALYSIS_BOUNDS_PATH
    if not bounds_path.exists():
        build_project_geometry(project_dir)
    if not bounds_path.exists():
        raise NaipBasemapMaterializationError(f"Missing project analysis bounds: {bounds_path}")
    gdf = gpd.read_file(bounds_path)
    if gdf.empty:
        raise NaipBasemapMaterializationError("Project analysis bounds are empty.")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    gdf = gdf.to_crs("EPSG:4326")
    geometry = unary_union([geom for geom in gdf.geometry if geom is not None and not geom.is_empty])
    return gdf, geometry


def _query_naip_items(
    aoi_geojson: dict[str, Any],
    *,
    year: int | None,
    max_tiles: int,
    timeout_seconds: int,
    deps: _ImageryDependencies,
) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {
        "collections": [NAIP_COLLECTION_ID],
        "intersects": aoi_geojson,
        "limit": max(50, min(200, max_tiles * 20)),
    }
    if year is not None:
        payload["datetime"] = f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z"
    response = deps.requests.post(f"{PC_STAC_URL}/search", json=payload, timeout=timeout_seconds)
    response.raise_for_status()
    data = response.json()
    features = data.get("features", []) if isinstance(data, dict) else []
    if not isinstance(features, list):
        raise NaipBasemapMaterializationError("Planetary Computer NAIP STAC response did not include a feature list.")
    return [dict(item) for item in features if isinstance(item, dict)]


def _write_basemap_raster(
    selected_items: list[dict[str, Any]],
    output_path: Path,
    *,
    aoi_bounds: dict[str, float],
    max_pixels: int,
    timeout_seconds: int,
    deps: _ImageryDependencies,
) -> dict[str, Any]:
    hrefs = [_item_asset_href(item) for item in selected_items]
    signed_hrefs = [deps.planetary_computer.sign(href) for href in hrefs]
    datasets: list[Any] = []
    sources: list[Any] = []
    try:
        with deps.rasterio.Env(
            GDAL_HTTP_TIMEOUT=str(timeout_seconds),
            GDAL_DISABLE_READDIR_ON_OPEN="YES",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
        ):
            for href in signed_hrefs:
                datasets.append(deps.rasterio.open(href))
            if not datasets:
                raise NaipBasemapMaterializationError("No NAIP raster datasets could be opened.")
            crs = datasets[0].crs
            if crs is None:
                raise NaipBasemapMaterializationError("Selected NAIP COG has no CRS.")
            for dataset in datasets:
                if dataset.count < 3:
                    raise NaipBasemapMaterializationError("Selected NAIP COG does not include RGB bands.")
                sources.append(dataset if dataset.crs == crs else deps.WarpedVRT(dataset, crs=crs))
            raster_bounds = deps.transform_bounds(
                "EPSG:4326",
                crs,
                aoi_bounds["west"],
                aoi_bounds["south"],
                aoi_bounds["east"],
                aoi_bounds["north"],
                densify_pts=21,
            )
            native_width, native_height = _estimate_pixel_shape(datasets[0], raster_bounds)
            estimated_pixels = int(native_width * native_height)
            output_res = _resolution_for_pixel_cap(datasets[0], estimated_pixels, max_pixels)
            merge_kwargs: dict[str, Any] = {"bounds": raster_bounds, "indexes": [1, 2, 3]}
            if output_res is not None:
                merge_kwargs["res"] = output_res
            data, transform = deps.merge(sources, **merge_kwargs)
            actual_pixels = int(data.shape[1] * data.shape[2])
            if actual_pixels > max_pixels:
                raise NaipBasemapMaterializationError(
                    f"NAIP output size is {actual_pixels} pixels, exceeding --max-pixels {max_pixels}."
                )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            profile = dict(datasets[0].profile)
            profile.update(
                {
                    "driver": "GTiff",
                    "height": int(data.shape[1]),
                    "width": int(data.shape[2]),
                    "count": 3,
                    "dtype": str(data.dtype),
                    "crs": crs,
                    "transform": transform,
                    "compress": "deflate",
                    "tiled": True,
                }
            )
            with deps.rasterio.open(output_path, "w", **profile) as destination:
                destination.write(data)
            output_bounds = deps.array_bounds(int(data.shape[1]), int(data.shape[2]), transform)
            output_bounds_wgs84 = deps.transform_bounds(crs, "EPSG:4326", *output_bounds, densify_pts=21)
            return {
                "output_crs": str(crs),
                "output_bounds": [float(value) for value in output_bounds],
                "output_bounds_wgs84": _bounds_dict(output_bounds_wgs84),
                "output_shape": [int(data.shape[1]), int(data.shape[2])],
                "pixel_count": actual_pixels,
                "native_estimated_pixel_count": estimated_pixels,
                "native_estimated_shape": [int(native_height), int(native_width)],
                "native_resolution": [abs(float(datasets[0].res[0])), abs(float(datasets[0].res[1]))],
                "output_resolution": [abs(float(transform.a)), abs(float(transform.e))],
                "resampled_to_fit_max_pixels": output_res is not None,
                "source_hrefs": hrefs,
            }
    finally:
        for source in sources:
            if source in datasets:
                continue
            try:
                source.close()
            except Exception:
                pass
        for dataset in datasets:
            try:
                dataset.close()
            except Exception:
                pass


def _sidecar_metadata(
    *,
    project_dir: Path,
    output_path: Path,
    selected_items: list[dict[str, Any]],
    selected_year: int,
    aoi_bounds: dict[str, float],
    raster_info: dict[str, Any],
    limits: dict[str, int],
) -> dict[str, Any]:
    datetimes = [_item_datetime(item) for item in selected_items if _item_datetime(item)]
    source_hrefs = [str(href) for href in raster_info.get("source_hrefs", []) if str(href).strip()]
    return {
        "source_id": USDA_NAIP_SOURCE_ID,
        "display_name": USDA_NAIP_SOURCE_NAME,
        "provider": NAIP_PROVIDER,
        "collection_id": NAIP_COLLECTION_ID,
        "asset_key": NAIP_ASSET_KEY,
        "item_ids": [str(item.get("id") or "") for item in selected_items if str(item.get("id") or "").strip()],
        "item_datetimes": datetimes,
        "source_datetime": max(datetimes) if datetimes else None,
        "naip_year": selected_year,
        "source_hrefs": source_hrefs,
        "signed_hrefs_stored": False,
        "aoi_source": "project_analysis_bounds",
        "aoi_bounds_wgs84": aoi_bounds,
        "output_path": _project_relative(project_dir, output_path),
        "output_crs": raster_info.get("output_crs"),
        "output_bounds": raster_info.get("output_bounds"),
        "output_bounds_wgs84": raster_info.get("output_bounds_wgs84"),
        "output_shape": raster_info.get("output_shape"),
        "pixel_count": raster_info.get("pixel_count"),
        "native_estimated_pixel_count": raster_info.get("native_estimated_pixel_count"),
        "native_estimated_shape": raster_info.get("native_estimated_shape"),
        "native_resolution": raster_info.get("native_resolution"),
        "output_resolution": raster_info.get("output_resolution"),
        "resampled_to_fit_max_pixels": bool(raster_info.get("resampled_to_fit_max_pixels")),
        "selection_method": "latest_year_then_datetime_then_overlap_then_item_id",
        "limits": limits,
        "created_at": _utc_now(),
        "acquisition_method": "planetary_computer_stac_cog_window",
        "known_limitations": [
            "Imagery is visual context only and requires reviewer interpretation.",
            "Signed asset URLs are not stored as durable provenance.",
        ],
    }


def _existing_sidecar(project_dir: Path, year: int | None) -> dict[str, Any] | None:
    for record in discover_project_local_naip_basemaps(project_dir):
        if year is not None and _safe_int(record.get("year")) != year:
            continue
        if record.get("metadata_path") and Path(str(record["metadata_path"])).exists():
            return record
    return None


def _success_result(
    project_dir: Path,
    *,
    started_at: str,
    project_id: str,
    project_name: str,
    status: str,
    action: str,
    sidecar_path: Path,
    metadata_path: Path | None,
    project_area_path: Path,
    year: int | None,
    item_ids: list[str],
    limits: dict[str, int],
    raster_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "project_name": project_name,
        "project_dir": str(project_dir),
        "source_id": USDA_NAIP_SOURCE_ID,
        "provider": NAIP_PROVIDER,
        "status": status,
        "success": True,
        "action": action,
        "started_at": started_at,
        "completed_at": _utc_now(),
        "naip_year": year,
        "item_ids": item_ids,
        "sidecar_path": str(sidecar_path),
        "metadata_path": str(metadata_path) if metadata_path else None,
        "project_area_path": str(project_area_path),
        "limits": limits,
        "raster": raster_info or {},
        "validation_issues": [],
    }


def _failure_result(
    project_dir: Path,
    *,
    started_at: str,
    year: int | None,
    max_pixels: int,
    max_tiles: int,
    timeout_seconds: int,
    message: str,
) -> dict[str, Any]:
    project_id = None
    project_name = None
    try:
        manifest = load_project_manifest(project_dir)
        project_id = manifest.project_id
        project_name = manifest.name
    except Exception:
        pass
    return {
        "project_id": project_id,
        "project_name": project_name,
        "project_dir": str(project_dir),
        "source_id": USDA_NAIP_SOURCE_ID,
        "provider": NAIP_PROVIDER,
        "status": "failed",
        "success": False,
        "action": "failed",
        "started_at": started_at,
        "completed_at": _utc_now(),
        "naip_year": year,
        "sidecar_path": None,
        "metadata_path": None,
        "project_area_path": str(project_dir / PROJECT_AREA_PATH),
        "limits": _limits(max_pixels, max_tiles, timeout_seconds),
        "message": message,
        "validation_issues": [
            {
                "severity": "warning",
                "code": "naip_basemap_materialization_failed",
                "message": message,
                "source_id": USDA_NAIP_SOURCE_ID,
            }
        ],
    }


def _write_run_manifest(project_dir: Path, result: dict[str, Any]) -> Path:
    path = project_dir / NAIP_RUN_MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    result["output_path"] = str(path)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return path


def _validate_limits(*, max_pixels: int, max_tiles: int, timeout_seconds: int) -> None:
    if max_pixels <= 0:
        raise NaipBasemapMaterializationError("--max-pixels must be greater than zero.")
    if max_tiles <= 0:
        raise NaipBasemapMaterializationError("--max-tiles must be greater than zero.")
    if timeout_seconds <= 0:
        raise NaipBasemapMaterializationError("--timeout-seconds must be greater than zero.")


def _limits(max_pixels: int, max_tiles: int, timeout_seconds: int) -> dict[str, int]:
    return {
        "max_pixels": int(max_pixels),
        "max_tiles": int(max_tiles),
        "timeout_seconds": int(timeout_seconds),
    }


def _estimate_pixel_shape(dataset: Any, raster_bounds: tuple[float, float, float, float]) -> tuple[int, int]:
    west, south, east, north = raster_bounds
    res_x, res_y = dataset.res
    width = max(1, math.ceil(abs(east - west) / abs(float(res_x))))
    height = max(1, math.ceil(abs(north - south) / abs(float(res_y))))
    return int(width), int(height)


def _resolution_for_pixel_cap(dataset: Any, estimated_pixels: int, max_pixels: int) -> tuple[float, float] | None:
    if estimated_pixels <= max_pixels:
        return None
    res_x, res_y = dataset.res
    scale = math.sqrt(float(estimated_pixels) / float(max_pixels)) * 1.02
    return abs(float(res_x)) * scale, abs(float(res_y)) * scale


def _item_assets(item: dict[str, Any]) -> dict[str, Any]:
    assets = item.get("assets", {})
    return assets if isinstance(assets, dict) else {}


def _item_asset_href(item: dict[str, Any]) -> str:
    asset = _item_assets(item).get(NAIP_ASSET_KEY)
    if not isinstance(asset, dict) or not str(asset.get("href") or "").strip():
        raise NaipBasemapMaterializationError(f"Selected NAIP item '{item.get('id')}' is missing image asset href.")
    return str(asset["href"])


def _item_datetime(item: dict[str, Any]) -> str | None:
    properties = item.get("properties", {})
    if isinstance(properties, dict) and str(properties.get("datetime") or "").strip():
        return str(properties["datetime"])
    return None


def _item_year(item: dict[str, Any]) -> int | None:
    properties = item.get("properties", {})
    if isinstance(properties, dict):
        for key in ("naip:year", "year"):
            value = _safe_int(properties.get(key))
            if value:
                return value
    value = _item_datetime(item)
    if value and len(value) >= 4:
        return _safe_int(value[:4])
    return None


def _item_timestamp(item: dict[str, Any]) -> float:
    value = _item_datetime(item)
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _item_overlap_area(item: dict[str, Any], aoi_geometry: BaseGeometry) -> float:
    try:
        raw_geometry = item.get("geometry")
        geometry = shape(raw_geometry) if isinstance(raw_geometry, dict) else None
    except Exception:
        geometry = None
    if geometry is None or geometry.is_empty:
        bbox_values = item.get("bbox")
        if isinstance(bbox_values, list) and len(bbox_values) >= 4:
            try:
                geometry = box(float(bbox_values[0]), float(bbox_values[1]), float(bbox_values[2]), float(bbox_values[3]))
            except (TypeError, ValueError):
                return 0.0
    if geometry is None or geometry.is_empty:
        return 0.0
    try:
        return float(geometry.intersection(aoi_geometry).area)
    except Exception:
        return 0.0


def _bounds_dict(bounds: Any) -> dict[str, float]:
    west, south, east, north = bounds
    return {
        "west": float(west),
        "south": float(south),
        "east": float(east),
        "north": float(north),
    }


def _project_relative(project_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        return str(path)


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
