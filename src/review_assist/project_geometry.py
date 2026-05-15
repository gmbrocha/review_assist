"""Project geometry normalization for constraint analysis."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import MultiLineString
from shapely.geometry.base import BaseGeometry
from shapely.ops import linemerge, unary_union

from .inspection import ProjectInspectionError, inspect_project, write_geojson
from .projects import ProjectManifestError, load_project_manifest
from .spatial_analysis import FEET_PER_METER, SpatialAnalysisError, _analysis_crs, _default_buffer_feet


PROJECT_GEOMETRY_PATH = Path("intermediate/project_geometry.json")
PROJECT_FEATURES_PATH = Path("intermediate/project_features.geojson")
PROJECT_ANALYSIS_BOUNDS_PATH = Path("intermediate/project_analysis_bounds.geojson")


class ProjectGeometryError(RuntimeError):
    """Raised when project geometry normalization cannot complete."""


def build_project_geometry(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        inspection = inspect_project(project_dir)
        default_buffer_feet = _default_buffer_feet(manifest.assumptions)
    except (ProjectManifestError, ProjectInspectionError, SpatialAnalysisError) as exc:
        raise ProjectGeometryError(str(exc)) from exc

    project_layers = _load_project_layers(inspection)
    if not project_layers:
        raise ProjectGeometryError("Project geometry normalization requires at least one project layer.")

    geometry_role = _geometry_role(project_layers)
    analysis_crs = _analysis_crs(project_layers)
    feature_gdf = _normalized_features(project_layers, geometry_role, analysis_crs)
    if feature_gdf.empty:
        raise ProjectGeometryError("Project geometry normalization produced no project features.")

    bounds_gdf = _analysis_bounds(feature_gdf, analysis_crs, default_buffer_feet)
    feature_output = project_dir / PROJECT_FEATURES_PATH
    bounds_output = project_dir / PROJECT_ANALYSIS_BOUNDS_PATH
    metadata_output = project_dir / PROJECT_GEOMETRY_PATH
    write_geojson(feature_gdf.to_crs("EPSG:4326"), feature_output)
    write_geojson(bounds_gdf.to_crs("EPSG:4326"), bounds_output)

    feature_records = [
        {
            "feature_id": str(row["feature_id"]),
            "feature_name": str(row["feature_name"]),
            "feature_group": str(row["feature_group"]),
            "geometry_role": str(row["geometry_role"]),
            "source_input": str(row["source_input"]),
            "source_role": str(row["source_role"]),
            "source_feature_count": int(row["source_feature_count"]),
            "geometry_type": row.geometry.geom_type,
        }
        for _, row in feature_gdf.iterrows()
    ]
    geometry_type_counts = dict(Counter(record["geometry_type"] for record in feature_records))
    metadata = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "geometry_role": geometry_role,
        "analysis_crs": analysis_crs,
        "default_buffer_feet": default_buffer_feet,
        "input_count": len(project_layers),
        "feature_count": len(feature_records),
        "geometry_type_counts": geometry_type_counts,
        "features": feature_records,
        "project_features_path": str(feature_output),
        "analysis_bounds_path": str(bounds_output),
        "geometry_summary_path": inspection.get("summary_path"),
        "output_path": str(metadata_output),
    }
    metadata_output.parent.mkdir(parents=True, exist_ok=True)
    metadata_output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def load_project_geometry(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / PROJECT_GEOMETRY_PATH
    if not path.exists():
        raise ProjectGeometryError(f"Missing project geometry artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectGeometryError(f"Invalid project geometry JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectGeometryError(f"Project geometry artifact must be a JSON object: {path}")
    return data


def _load_project_layers(inspection: dict[str, Any]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for item in inspection["inputs"]:
        geojson_path = Path(item["normalized_geojson"])
        gdf = gpd.read_file(geojson_path)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        layers.append({"summary": item, "gdf": gdf})
    return layers


def _geometry_role(project_layers: list[dict[str, Any]]) -> str:
    families: set[str] = set()
    for layer in project_layers:
        for geom_type in layer["gdf"].geometry.geom_type.dropna().unique().tolist():
            if "Point" in geom_type:
                families.add("point_site")
            elif "LineString" in geom_type:
                families.add("line_corridor")
            elif "Polygon" in geom_type:
                families.add("polygon_area")
            else:
                families.add("mixed")
    if len(families) == 1:
        return next(iter(families))
    return "mixed"


def _normalized_features(project_layers: list[dict[str, Any]], geometry_role: str, analysis_crs: str) -> gpd.GeoDataFrame:
    rows: list[dict[str, Any]] = []
    geometries: list[BaseGeometry] = []
    feature_counter = 1
    for layer in project_layers:
        summary = layer["summary"]
        gdf = layer["gdf"].to_crs(analysis_crs)
        line_rows: dict[str, list[tuple[Any, BaseGeometry]]] = defaultdict(list)
        for index, row in gdf.iterrows():
            geometry = row.geometry
            if geometry is None or geometry.is_empty:
                continue
            role = _geometry_role_for_geometry(geometry)
            if role == "line_corridor":
                line_rows[_feature_group(row, index)].append((index, geometry))
                continue
            rows.append(
                _feature_row(
                    feature_counter,
                    row,
                    index,
                    summary,
                    role if geometry_role == "mixed" else geometry_role,
                    source_feature_count=1,
                )
            )
            geometries.append(geometry)
            feature_counter += 1

        for group, grouped_geometries in sorted(line_rows.items()):
            merged = _merge_lines([geometry for _, geometry in grouped_geometries])
            first_index, first_geometry = grouped_geometries[0]
            first_row = gdf.loc[first_index]
            row_data = _feature_row(
                feature_counter,
                first_row,
                first_index,
                summary,
                "line_corridor" if geometry_role == "mixed" else geometry_role,
                source_feature_count=len(grouped_geometries),
            )
            row_data["feature_group"] = group
            row_data["feature_name"] = _feature_name(first_row, first_index, group)
            rows.append(row_data)
            geometries.append(merged if not merged.is_empty else first_geometry)
            feature_counter += 1

    return gpd.GeoDataFrame(rows, geometry=geometries, crs=analysis_crs)


def _feature_row(
    feature_counter: int,
    row: Any,
    index: Any,
    summary: dict[str, Any],
    geometry_role: str,
    *,
    source_feature_count: int,
) -> dict[str, Any]:
    group = _feature_group(row, index)
    return {
        "feature_id": f"feature-{feature_counter:05d}",
        "feature_name": _feature_name(row, index, group),
        "feature_group": group,
        "geometry_role": geometry_role,
        "source_input": summary.get("input_path", ""),
        "source_role": summary.get("role", ""),
        "source_feature_count": source_feature_count,
        "source_feature_index": str(index),
        "candidate_label": _string_value(row, "candidate_label"),
        "placemark_name": _string_value(row, "placemark_name"),
        "style_url": _string_value(row, "style_url"),
    }


def _feature_group(row: Any, index: Any) -> str:
    for column in ("placemark_name", "style_url", "candidate_label"):
        value = _string_value(row, column)
        if value:
            return value
    return f"feature-{index}"


def _feature_name(row: Any, index: Any, group: str) -> str:
    for column in ("candidate_label", "placemark_name", "style_url"):
        value = _string_value(row, column)
        if value:
            return value
    return group or f"Feature {index}"


def _geometry_role_for_geometry(geometry: BaseGeometry) -> str:
    geom_type = geometry.geom_type
    if "Point" in geom_type:
        return "point_site"
    if "LineString" in geom_type:
        return "line_corridor"
    if "Polygon" in geom_type:
        return "polygon_area"
    return "mixed"


def _merge_lines(geometries: list[BaseGeometry]) -> BaseGeometry:
    lines: list[BaseGeometry] = []
    for geometry in geometries:
        if geometry.geom_type == "LineString":
            lines.append(geometry)
        elif geometry.geom_type == "MultiLineString":
            lines.extend(list(geometry.geoms))
    if not lines:
        return MultiLineString([])
    merged = linemerge(MultiLineString(lines)) if len(lines) > 1 else lines[0]
    return merged


def _analysis_bounds(feature_gdf: gpd.GeoDataFrame, analysis_crs: str, buffer_feet: float) -> gpd.GeoDataFrame:
    buffer_distance = buffer_feet / FEET_PER_METER
    geometries = feature_gdf.geometry
    buffered = geometries.buffer(buffer_distance) if buffer_distance > 0 else geometries
    unioned = unary_union([geometry for geometry in buffered if geometry is not None and not geometry.is_empty])
    if unioned.is_empty:
        unioned = unary_union([geometry for geometry in geometries if geometry is not None and not geometry.is_empty])
    bounds = unioned.envelope
    return gpd.GeoDataFrame(
        [
            {
                "bounds_id": "project-analysis-bounds",
                "buffer_feet": buffer_feet,
                "analysis_crs": analysis_crs,
            }
        ],
        geometry=[bounds],
        crs=analysis_crs,
    )


def _string_value(row: Any, column: str) -> str:
    if column not in row.index:
        return ""
    value = row[column]
    if value is None:
        return ""
    text = str(value).strip()
    return "" if not text or text.lower() == "nan" else text


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
