"""Geometry summary generation for Phase 1 ingestion."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import geopandas as gpd

from .kml import IngestedInput
from .projects import ProjectInput
from .validation import ValidationIssue


def bounds_wgs84(gdf: gpd.GeoDataFrame) -> dict[str, float] | None:
    if gdf.empty:
        return None
    wgs84 = gdf.to_crs("EPSG:4326") if gdf.crs else gdf.set_crs("EPSG:4326", allow_override=True)
    west, south, east, north = wgs84.total_bounds
    return {
        "west": float(west),
        "south": float(south),
        "east": float(east),
        "north": float(north),
    }


def estimated_local_crs(gdf: gpd.GeoDataFrame) -> str | None:
    if gdf.empty or gdf.crs is None:
        return None
    try:
        crs = gdf.estimate_utm_crs()
    except RuntimeError:
        return None
    if crs is None:
        return None
    return crs.to_string()


def candidate_labels(gdf: gpd.GeoDataFrame, limit: int = 25) -> list[str]:
    labels: list[str] = []
    for column in ("candidate_label", "placemark_name", "style_url"):
        if column not in gdf.columns:
            continue
        for value in gdf[column].dropna().astype(str):
            value = value.strip()
            if value and value not in labels:
                labels.append(value)
            if len(labels) >= limit:
                return labels
    return labels


def blank_label_count(gdf: gpd.GeoDataFrame) -> int:
    if "placemark_name" not in gdf.columns:
        return 0
    return int((gdf["placemark_name"].fillna("").astype(str).str.strip() == "").sum())


def input_summary(project_input: ProjectInput, ingested: IngestedInput, geojson_path: Path) -> dict[str, Any]:
    gdf = ingested.geo_data_frame
    geometry_types = Counter(gdf.geometry.geom_type.dropna().tolist())
    issues: list[ValidationIssue] = list(ingested.issues)
    if blank_label_count(gdf) == len(gdf):
        issues.append(
            ValidationIssue(
                severity="info",
                code="all_feature_names_blank",
                message="All parsed geometries came from placemarks with blank names.",
                location=str(ingested.source_path),
            )
        )

    return {
        "input_path": project_input.path,
        "resolved_input_path": str(ingested.source_path),
        "role": project_input.role,
        "description": project_input.description,
        "kml_entries": ingested.kml_entries,
        "placemark_count": ingested.placemark_count,
        "feature_count": int(len(gdf)),
        "geometry_type_counts": dict(sorted(geometry_types.items())),
        "bounds_wgs84": bounds_wgs84(gdf),
        "source_crs": gdf.crs.to_string() if gdf.crs else None,
        "estimated_local_crs": estimated_local_crs(gdf),
        "candidate_labels": candidate_labels(gdf),
        "blank_feature_name_count": blank_label_count(gdf),
        "normalized_geojson": str(geojson_path),
        "validation_issues": [issue.to_dict() for issue in issues],
    }

