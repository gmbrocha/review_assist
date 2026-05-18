"""Basemap sidecar loading helpers for deliverable figure rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pyproj import Transformer

from .basemaps import MARIS_NAIP_SOURCE_ID, MARIS_NAIP_SOURCE_NAME
from .deliverable_figure_specs import RENDERABLE_BASEMAP_SUFFIXES


def load_basemap(project_area: dict[str, Any], analysis_crs: str) -> dict[str, Any]:
    selected_paths = _string_list(project_area.get("selected_basemap_paths", []))
    renderable_paths = [path for path in _string_list(project_area.get("renderable_basemap_paths", [])) if Path(path).suffix.lower() in RENDERABLE_BASEMAP_SUFFIXES]
    if not selected_paths and not renderable_paths:
        return {"layer": None, "issues": [], "flags": ["vector_only_no_basemap"], "shown_layer": None, "source_ref": None}
    if selected_paths and not renderable_paths:
        return {
            "layer": None,
            "issues": [
                _issue(
                    "warning",
                    "basemap_selected_not_renderable",
                    "Selected MARIS/NAIP imagery is MrSID provenance only; no renderable sidecar was selected for figure rendering.",
                    str(project_area.get("output_path") or ""),
                    source_id=MARIS_NAIP_SOURCE_ID,
                )
            ],
            "flags": ["source_selected_not_renderable", "renderable_sidecar_missing", "vector_only_no_basemap"],
            "shown_layer": {
                "layer_type": "basemap_provenance",
                "source_id": MARIS_NAIP_SOURCE_ID,
                "label": MARIS_NAIP_SOURCE_NAME,
                "selected_paths": selected_paths,
                "renderable": False,
            },
            "source_ref": MARIS_NAIP_SOURCE_ID,
            "selected_paths": selected_paths,
            "renderable_paths": renderable_paths,
        }
    for path_text in renderable_paths:
        path = Path(path_text)
        if not path.exists():
            continue
        layer, issue = _read_basemap_layer(path, project_area, analysis_crs)
        if layer is not None:
            return {
                "layer": layer,
                "issues": [],
                "flags": ["basemap_sidecar_rendered"],
                "shown_layer": {
                    "layer_type": "basemap",
                    "source_id": MARIS_NAIP_SOURCE_ID,
                    "label": MARIS_NAIP_SOURCE_NAME,
                    "path": str(path),
                    "selected_paths": selected_paths,
                    "renderable": True,
                },
                "source_ref": MARIS_NAIP_SOURCE_ID,
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
                    "source_id": MARIS_NAIP_SOURCE_ID,
                    "label": MARIS_NAIP_SOURCE_NAME,
                    "path": str(path),
                    "selected_paths": selected_paths,
                    "renderable": False,
                },
                "source_ref": MARIS_NAIP_SOURCE_ID,
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
        "selected_paths": selected_paths,
        "renderable_paths": renderable_paths,
    }


def _read_basemap_layer(path: Path, project_area: dict[str, Any], analysis_crs: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    suffix = path.suffix.lower()
    if suffix == ".png":
        bbox = _metadata_bbox_for_path(path, project_area)
        if bbox is None:
            return None, _issue(
                "warning",
                "basemap_render_failed",
                "PNG basemap sidecar lacks usable WGS84 metadata extent; falling back to vector-only rendering.",
                str(path),
                source_id=MARIS_NAIP_SOURCE_ID,
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
                source_id=MARIS_NAIP_SOURCE_ID,
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
            source_id=MARIS_NAIP_SOURCE_ID,
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
            source_id=MARIS_NAIP_SOURCE_ID,
        )
    return {"image": image, "extent": extent, "path": str(path)}, None


def _metadata_bbox_for_path(path: Path, project_area: dict[str, Any]) -> dict[str, float] | None:
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
