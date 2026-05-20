"""Basemap sidecar loading helpers for deliverable figure rendering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pyproj import Transformer

from .basemaps import MARIS_NAIP_SOURCE_ID, MARIS_NAIP_SOURCE_NAME, USDA_NAIP_SOURCE_ID, USDA_NAIP_SOURCE_NAME
from .deliverable_figure_specs import RENDERABLE_BASEMAP_SUFFIXES


def load_basemap(
    project_area: dict[str, Any],
    analysis_crs: str,
    *,
    required_bounds: Any | None = None,
    required_bounds_crs: str | None = None,
    extent_class: str | None = None,
) -> dict[str, Any]:
    selected_paths = _string_list(project_area.get("selected_basemap_paths", []))
    project_local_basemaps = _dict_list(project_area.get("project_local_basemaps", []))
    renderable_records = _renderable_basemap_records(project_local_basemaps, project_area, extent_class=extent_class)
    renderable_paths = [str(record["path"]) for record in renderable_records]
    failed_materialization = _latest_naip_materialization_failure(project_area)
    if not selected_paths and not renderable_paths:
        if failed_materialization is not None:
            message = str(failed_materialization.get("message") or "NAIP basemap materialization failed; vector-only fallback remains available.")
            return {
                "layer": None,
                "issues": [
                    _issue(
                        "warning",
                        "naip_basemap_materialization_failed",
                        message,
                        str(failed_materialization.get("path") or project_area.get("output_path") or ""),
                        source_id=USDA_NAIP_SOURCE_ID,
                    )
                ],
                "flags": ["basemap_materialization_failed", "vector_only_no_basemap"],
                "shown_layer": {
                    "layer_type": "basemap_provenance",
                    "source_id": USDA_NAIP_SOURCE_ID,
                    "label": USDA_NAIP_SOURCE_NAME,
                    "renderable": False,
                    "renderability_status": "materialization_failed",
                    "visual_use": "failed_not_rendered",
                    "message": message,
                },
                "source_ref": USDA_NAIP_SOURCE_ID,
                "source_refs": [USDA_NAIP_SOURCE_ID],
                "selected_paths": selected_paths,
                "renderable_paths": renderable_paths,
            }
        return {"layer": None, "issues": [], "flags": ["vector_only_no_basemap"], "shown_layer": None, "source_ref": None}
    if selected_paths and not renderable_paths:
        issues = [
            _issue(
                "warning",
                "basemap_selected_not_renderable",
                (
                    "County NAIP imagery was selected as provenance, but only MrSID source files are available. "
                    "Provide GeoTIFF/PNG sidecar for visual basemap rendering."
                ),
                str(project_area.get("output_path") or ""),
                source_id=MARIS_NAIP_SOURCE_ID,
            )
        ]
        flags = ["source_selected_not_renderable", "renderable_sidecar_missing", "vector_only_no_basemap"]
        source_refs = [MARIS_NAIP_SOURCE_ID]
        materialization_failures: list[dict[str, str]] = []
        if failed_materialization is not None:
            message = str(failed_materialization.get("message") or "NAIP basemap materialization failed; vector-only fallback remains available.")
            issues.append(
                _issue(
                    "warning",
                    "naip_basemap_materialization_failed",
                    message,
                    str(failed_materialization.get("path") or project_area.get("output_path") or ""),
                    source_id=USDA_NAIP_SOURCE_ID,
                )
            )
            flags.append("basemap_materialization_failed")
            source_refs.append(USDA_NAIP_SOURCE_ID)
            materialization_failures.append(
                {
                    "source_id": USDA_NAIP_SOURCE_ID,
                    "label": USDA_NAIP_SOURCE_NAME,
                    "message": message,
                }
            )
        return {
            "layer": None,
            "issues": issues,
            "flags": flags,
            "shown_layer": {
                "layer_type": "basemap_provenance",
                "source_id": MARIS_NAIP_SOURCE_ID,
                "label": MARIS_NAIP_SOURCE_NAME,
                "selected_paths": selected_paths,
                "renderable": False,
                "renderability_status": "selected_not_renderable",
                "visual_use": "provenance_only",
                "message": "County NAIP imagery selected as provenance only; renderable GeoTIFF/PNG sidecar is not available.",
            },
            "source_ref": MARIS_NAIP_SOURCE_ID,
            "source_refs": _dedupe_strings(source_refs),
            "materialization_failures": materialization_failures,
            "selected_paths": selected_paths,
            "renderable_paths": renderable_paths,
        }
    insufficient_issues: list[dict[str, Any]] = []
    for record in renderable_records:
        path_text = str(record.get("path") or "")
        path = Path(path_text)
        if not path.exists():
            continue
        source_id = str(record.get("source_id") or MARIS_NAIP_SOURCE_ID)
        source_name = str(record.get("source_name") or record.get("label") or _basemap_name(source_id))
        layer, issue = _read_basemap_layer(path, project_area, analysis_crs, source_id=source_id)
        if layer is not None:
            coverage_issue = _coverage_issue(
                layer,
                required_bounds=required_bounds,
                required_bounds_crs=required_bounds_crs or analysis_crs,
                path=path,
                source_id=source_id,
            )
            if coverage_issue is not None:
                insufficient_issues.append(coverage_issue)
                continue
            return {
                "layer": layer,
                "issues": [],
                "flags": ["basemap_sidecar_rendered"],
                "shown_layer": {
                    "layer_type": "basemap",
                    "source_id": source_id,
                    "label": source_name,
                    "path": str(path),
                    "selected_paths": selected_paths,
                    "renderable": True,
                    "renderability_status": "rendered",
                    "visual_use": "rendered_basemap",
                    "extent_class": record.get("extent_class"),
                    "aoi_source": record.get("aoi_source"),
                    "full_render_extent": record.get("full_render_extent"),
                    "message": f"{source_name} renderable sidecar was used as the visual basemap.",
                },
                "source_ref": source_id,
                "source_refs": [source_id],
                "selected_paths": selected_paths,
                "renderable_paths": renderable_paths,
            }
        if issue is not None:
            return {
                "layer": None,
                "issues": [issue],
                "flags": ["basemap_render_failed", "vector_only_no_basemap"],
                "shown_layer": {
                    "layer_type": "basemap_provenance",
                    "source_id": source_id,
                    "label": source_name,
                    "path": str(path),
                    "selected_paths": selected_paths,
                    "renderable": False,
                    "renderability_status": "render_failed",
                    "visual_use": "provenance_only",
                    "message": f"{source_name} renderable sidecar was selected but could not be rendered.",
                },
                "source_ref": source_id,
                "source_refs": [source_id],
                "selected_paths": selected_paths,
                "renderable_paths": renderable_paths,
            }
    if insufficient_issues:
        return {
            "layer": None,
            "issues": insufficient_issues,
            "flags": ["basemap_sidecar_extent_insufficient", "vector_only_no_basemap"],
            "shown_layer": {
                "layer_type": "basemap_provenance",
                "source_id": USDA_NAIP_SOURCE_ID,
                "label": USDA_NAIP_SOURCE_NAME,
                "selected_paths": selected_paths,
                "renderable_paths": renderable_paths,
                "renderable": False,
                "renderability_status": "extent_insufficient",
                "visual_use": "provenance_only",
                "extent_class": extent_class,
                "message": "Available NAIP sidecar does not cover the planned full figure render extent.",
            },
            "source_ref": USDA_NAIP_SOURCE_ID,
            "source_refs": [USDA_NAIP_SOURCE_ID],
            "selected_paths": selected_paths,
            "renderable_paths": renderable_paths,
        }
    return {
        "layer": None,
        "issues": [
            _issue(
                "warning",
                "basemap_render_failed",
                "Selected MARIS/NAIP renderable sidecar path is unavailable or unusable.",
                str(project_area.get("output_path") or ""),
                source_id=MARIS_NAIP_SOURCE_ID,
            )
        ],
        "flags": ["basemap_render_failed", "vector_only_no_basemap"],
        "shown_layer": None,
        "source_ref": MARIS_NAIP_SOURCE_ID,
        "source_refs": [MARIS_NAIP_SOURCE_ID],
        "selected_paths": selected_paths,
        "renderable_paths": renderable_paths,
    }


def _renderable_basemap_records(
    project_local_basemaps: list[dict[str, Any]],
    project_area: dict[str, Any],
    *,
    extent_class: str | None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record in project_local_basemaps:
        path_text = str(record.get("path") or "").strip()
        if path_text and Path(path_text).suffix.lower() in RENDERABLE_BASEMAP_SUFFIXES:
            records.append(dict(record))
    known_paths = {str(record.get("path")) for record in records}
    for path_text in _string_list(project_area.get("renderable_basemap_paths", [])):
        if path_text in known_paths or Path(path_text).suffix.lower() not in RENDERABLE_BASEMAP_SUFFIXES:
            continue
        path = Path(path_text)
        records.append(_basemap_record_for_path(path, project_area) | {"path": path_text})
        known_paths.add(path_text)
    if extent_class:
        records.sort(key=lambda record: (0 if str(record.get("extent_class") or "") == extent_class else 1, str(record.get("path") or "")))
    return _dedupe_records_by_path(records)


def _dedupe_records_by_path(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for record in records:
        path_text = str(record.get("path") or "")
        if not path_text or path_text in seen:
            continue
        seen.add(path_text)
        result.append(record)
    return result


def _read_basemap_layer(
    path: Path,
    project_area: dict[str, Any],
    analysis_crs: str,
    *,
    source_id: str = MARIS_NAIP_SOURCE_ID,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    suffix = path.suffix.lower()
    if suffix == ".png":
        bbox = _metadata_bbox_for_path(path, project_area)
        if bbox is None:
            return None, _issue(
                "warning",
                "basemap_render_failed",
                "PNG basemap sidecar lacks usable WGS84 metadata extent; falling back to vector-only rendering.",
                str(path),
                source_id=source_id,
            )
        try:
            image = plt.imread(path)
            extent = _bbox_to_crs_extent(bbox, analysis_crs)
        except Exception as exc:  # pragma: no cover - image backends vary.
            return None, _issue(
                "warning",
                "basemap_render_failed",
                f"PNG basemap sidecar could not be read: {exc}",
                str(path),
                source_id=source_id,
            )
        return {"image": image, "extent": extent, "path": str(path)}, None

    try:
        import rasterio
    except ImportError:
        return None, _issue(
            "warning",
            "basemap_render_failed",
            "GeoTIFF basemap sidecar was selected, but rasterio is not installed; falling back to vector-only rendering.",
            str(path),
            source_id=source_id,
        )
    try:
        with rasterio.open(path) as dataset:
            indexes = [1, 2, 3] if dataset.count >= 3 else [1]
            data = dataset.read(indexes)
            if len(indexes) == 1:
                image: Any = data[0]
            else:
                image = data.transpose(1, 2, 0)
            if dataset.crs is None:
                bbox = _metadata_bbox_for_path(path, project_area)
                if bbox is None:
                    raise ValueError("GeoTIFF has no CRS and no metadata bbox is available.")
                extent = _bbox_to_crs_extent(bbox, analysis_crs)
            else:
                west, south, east, north = dataset.bounds
                transformer = Transformer.from_crs(dataset.crs, analysis_crs, always_xy=True)
                xs, ys = transformer.transform([west, east], [south, north])
                extent = (min(xs), max(xs), min(ys), max(ys))
    except Exception as exc:  # pragma: no cover - raster drivers vary.
        return None, _issue(
            "warning",
            "basemap_render_failed",
            f"GeoTIFF basemap sidecar could not be read: {exc}",
            str(path),
            source_id=source_id,
        )
    return {"image": image, "extent": extent, "path": str(path)}, None


def _coverage_issue(
    layer: dict[str, Any],
    *,
    required_bounds: Any | None,
    required_bounds_crs: str,
    path: Path,
    source_id: str,
) -> dict[str, Any] | None:
    if required_bounds is None:
        return None
    try:
        required = _normal_bounds(required_bounds)
        actual = _normal_imshow_extent(layer.get("extent"))
    except Exception:
        return _issue(
            "warning",
            "basemap_sidecar_extent_insufficient",
            "Basemap sidecar extent could not be compared to the planned full figure render extent.",
            str(path),
            source_id=source_id,
        )
    tolerance = 1.0
    covers = (
        actual[0] <= required[0] + tolerance
        and actual[1] <= required[1] + tolerance
        and actual[2] >= required[2] - tolerance
        and actual[3] >= required[3] - tolerance
    )
    if covers:
        return None
    return {
        "severity": "warning",
        "code": "basemap_sidecar_extent_insufficient",
        "message": "Basemap sidecar does not cover the planned full figure render extent; vector-only fallback was used.",
        "location": str(path),
        "source_id": source_id,
        "expected_full_render_extent": _bounds_record(required),
        "expected_full_render_extent_crs": required_bounds_crs,
        "actual_raster_extent": _bounds_record(actual),
        "actual_raster_extent_crs": required_bounds_crs,
    }


def _normal_imshow_extent(extent: Any) -> tuple[float, float, float, float]:
    left, right, bottom, top = [float(value) for value in extent]
    return _normal_bounds((left, bottom, right, top))


def _normal_bounds(bounds: Any) -> tuple[float, float, float, float]:
    west, south, east, north = [float(value) for value in bounds]
    if west > east:
        west, east = east, west
    if south > north:
        south, north = north, south
    return west, south, east, north


def _bounds_record(bounds: tuple[float, float, float, float]) -> dict[str, float]:
    return {"west": bounds[0], "south": bounds[1], "east": bounds[2], "north": bounds[3]}


def _metadata_bbox_for_path(path: Path, project_area: dict[str, Any]) -> dict[str, float] | None:
    for record in _dict_list(project_area.get("project_local_basemaps", [])):
        if str(record.get("path") or "") != str(path):
            continue
        bbox = record.get("metadata_bbox_wgs84") or record.get("bounds_wgs84")
        if isinstance(bbox, dict) and {"west", "south", "east", "north"}.issubset(bbox):
            try:
                return {key: float(bbox[key]) for key in ("west", "south", "east", "north")}
            except (TypeError, ValueError):
                return None
    for candidate in _dict_list(project_area.get("aerial_basemap_candidates", [])):
        paths = set(_string_list(candidate.get("renderable_sidecar_paths", [])))
        paths.update(_string_list(candidate.get("sid_paths", [])))
        if str(path) not in paths:
            continue
        bbox = candidate.get("metadata_bbox_wgs84")
        if isinstance(bbox, dict) and {"west", "south", "east", "north"}.issubset(bbox):
            try:
                return {key: float(bbox[key]) for key in ("west", "south", "east", "north")}
            except (TypeError, ValueError):
                return None
    return None


def _latest_naip_materialization_failure(project_area: dict[str, Any]) -> dict[str, Any] | None:
    output_path = str(project_area.get("output_path") or "").strip()
    if not output_path:
        return None
    project_area_path = Path(output_path)
    project_dir = project_area_path.parent.parent
    manifest_path = project_dir / "basemaps" / "naip" / "naip_basemap_materialization.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(manifest, dict) and manifest.get("status") == "failed":
        return {"path": str(manifest_path), "message": manifest.get("message")}
    return None


def _basemap_record_for_path(path: Path, project_area: dict[str, Any]) -> dict[str, Any]:
    for record in _dict_list(project_area.get("project_local_basemaps", [])):
        if str(record.get("path") or "") == str(path):
            return record
    return {"source_id": MARIS_NAIP_SOURCE_ID, "source_name": MARIS_NAIP_SOURCE_NAME}


def _basemap_name(source_id: str) -> str:
    if source_id == USDA_NAIP_SOURCE_ID:
        return USDA_NAIP_SOURCE_NAME
    return MARIS_NAIP_SOURCE_NAME


def _bbox_to_crs_extent(bbox: dict[str, float], analysis_crs: str) -> tuple[float, float, float, float]:
    transformer = Transformer.from_crs("EPSG:4326", analysis_crs, always_xy=True)
    west, south = transformer.transform(float(bbox["west"]), float(bbox["south"]))
    east, north = transformer.transform(float(bbox["east"]), float(bbox["north"]))
    return min(west, east), max(west, east), min(south, north), max(south, north)


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


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
