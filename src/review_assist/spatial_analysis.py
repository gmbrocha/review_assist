"""Local source-layer clipping and spatial relationship checks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry.base import BaseGeometry

from .inspection import ProjectInspectionError, inspect_project, write_geojson
from .projects import ProjectManifestError, load_project_manifest
from .source_catalog import (
    ProjectSource,
    SourceCatalogError,
    load_project_source_registry,
    load_source_catalog,
    resolve_project_source_path,
)
from .validation import ValidationIssue


FEET_PER_METER = 3.280839895
SQUARE_METERS_PER_ACRE = 4046.8564224


class SpatialAnalysisError(RuntimeError):
    """Raised when spatial analysis cannot complete."""


def analyze_project(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        catalog = load_source_catalog()
        registry = load_project_source_registry(project_dir)
        inspection = inspect_project(project_dir)
    except (ProjectManifestError, SourceCatalogError, ProjectInspectionError) as exc:
        raise SpatialAnalysisError(str(exc)) from exc

    project_layers = _load_project_layers(inspection)
    default_buffer_feet = _default_buffer_feet(manifest.assumptions)
    output_dir = project_dir / "intermediate"
    clipped_dir = output_dir / "clipped_layers"
    clipped_dir.mkdir(parents=True, exist_ok=True)

    source_results: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    issues: list[ValidationIssue] = []

    for project_source in registry.sources:
        source_definition = catalog.sources.get(project_source.source_id)
        if source_definition is None:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="unknown_project_source",
                    message=f"Project source '{project_source.source_id}' is not present in the global catalog.",
                    location=str(project_dir / "config" / "sources.json"),
                )
            )
            source_results.append(_source_result(project_source, status="skipped_unknown_source"))
            continue

        if not project_source.enabled:
            source_results.append(_source_result(project_source, source_definition, status="disabled"))
            continue

        if project_source.access_method != "local_file":
            source_results.append(_source_result(project_source, source_definition, status="skipped_non_local"))
            continue

        source_path = resolve_project_source_path(project_dir, project_source)
        if source_path is None:
            raise SpatialAnalysisError(f"Enabled local source '{project_source.source_id}' requires a path.")
        if not source_path.exists():
            raise SpatialAnalysisError(f"Missing local source file for '{project_source.source_id}': {source_path}")

        try:
            source_gdf = gpd.read_file(source_path)
        except Exception as exc:  # pragma: no cover - driver-specific exception types vary.
            raise SpatialAnalysisError(f"Unable to read source layer '{project_source.source_id}': {source_path}: {exc}") from exc

        source_issues: list[ValidationIssue] = []
        if source_gdf.crs is None:
            source_issues.append(
                ValidationIssue(
                    severity="warning",
                    code="missing_source_crs",
                    message="Source layer CRS is missing; assuming EPSG:4326 for screening.",
                    location=str(source_path),
                )
            )
            source_gdf = source_gdf.set_crs("EPSG:4326", allow_override=True)

        source_gdf = source_gdf[~source_gdf.geometry.isna()]
        source_gdf = source_gdf[~source_gdf.geometry.is_empty]
        if source_gdf.empty:
            source_issues.append(
                ValidationIssue(
                    severity="warning",
                    code="empty_source_layer",
                    message="Source layer contains no non-empty geometries.",
                    location=str(source_path),
                )
            )
            source_results.append(
                _source_result(
                    project_source,
                    source_definition,
                    status="analyzed_empty",
                    source_path=source_path,
                    validation_issues=source_issues,
                )
            )
            continue

        buffer_feet = project_source.buffer_feet if project_source.buffer_feet is not None else default_buffer_feet
        clipped_wgs84, source_relationships, analysis_crs = _analyze_source(
            project_layers=project_layers,
            source_gdf=source_gdf,
            project_source=project_source,
            source_definition=source_definition,
            buffer_feet=buffer_feet,
            relationship_start=len(relationships),
        )

        clipped_path = clipped_dir / f"{project_source.source_id}.geojson"
        write_geojson(clipped_wgs84, clipped_path)
        relationships.extend(source_relationships)
        source_results.append(
            _source_result(
                project_source,
                source_definition,
                status="analyzed",
                source_path=source_path,
                clipped_path=clipped_path,
                source_feature_count=len(source_gdf),
                clipped_feature_count=len(clipped_wgs84),
                relationship_count=len(source_relationships),
                analysis_crs=analysis_crs,
                buffer_feet=buffer_feet,
                validation_issues=source_issues,
            )
        )

    output_path = output_dir / "spatial_relationships.json"
    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "geometry_summary_path": inspection["summary_path"],
        "default_buffer_feet": default_buffer_feet,
        "sources": source_results,
        "relationships": relationships,
        "validation_issues": [issue.to_dict() for issue in issues],
        "output_path": str(output_path),
    }
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _load_project_layers(inspection: dict[str, Any]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for item in inspection["inputs"]:
        geojson_path = Path(item["normalized_geojson"])
        gdf = gpd.read_file(geojson_path)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        layers.append({"summary": item, "gdf": gdf})
    return layers


def _default_buffer_feet(assumptions: dict[str, Any]) -> float:
    raw_value = assumptions.get("default_buffer_feet", 100)
    try:
        return float(raw_value)
    except (TypeError, ValueError) as exc:
        raise SpatialAnalysisError("Project assumption 'default_buffer_feet' must be numeric.") from exc


def _analyze_source(
    *,
    project_layers: list[dict[str, Any]],
    source_gdf: gpd.GeoDataFrame,
    project_source: ProjectSource,
    source_definition: Any,
    buffer_feet: float,
    relationship_start: int,
) -> tuple[gpd.GeoDataFrame, list[dict[str, Any]], str]:
    analysis_crs = _analysis_crs(project_layers)
    buffer_distance = buffer_feet / FEET_PER_METER
    source_projected = source_gdf.to_crs(analysis_crs)
    project_projected_layers = [
        {"summary": layer["summary"], "gdf": layer["gdf"].to_crs(analysis_crs)} for layer in project_layers
    ]

    buffered_geometries: list[BaseGeometry] = []
    for layer in project_projected_layers:
        buffered_geometries.extend(layer["gdf"].geometry.buffer(buffer_distance).tolist())
    buffered_union = gpd.GeoSeries(buffered_geometries, crs=analysis_crs).union_all()

    clipped = source_projected[source_projected.geometry.intersects(buffered_union)].copy()
    clipped_wgs84 = clipped.to_crs("EPSG:4326") if not clipped.empty else source_projected.iloc[0:0].to_crs("EPSG:4326")

    relationships: list[dict[str, Any]] = []
    for layer in project_projected_layers:
        input_summary = layer["summary"]
        for project_index, project_row in layer["gdf"].iterrows():
            project_geometry = project_row.geometry
            if project_geometry is None or project_geometry.is_empty:
                continue
            project_buffer = project_geometry.buffer(buffer_distance)
            for source_index, source_row in clipped.iterrows():
                source_geometry = source_row.geometry
                if source_geometry is None or source_geometry.is_empty:
                    continue

                if project_geometry.intersects(source_geometry):
                    intersection = project_geometry.intersection(source_geometry)
                    relationships.append(
                        _relationship_record(
                            relationship_id=relationship_start + len(relationships) + 1,
                            relationship="intersects",
                            input_summary=input_summary,
                            project_index=project_index,
                            project_row=project_row,
                            project_geometry=project_geometry,
                            source_index=source_index,
                            source_row=source_row,
                            source_geometry=source_geometry,
                            source_definition=source_definition,
                            project_source=project_source,
                            buffer_feet=buffer_feet,
                            analysis_crs=analysis_crs,
                            measurements=_measure_intersection(intersection),
                        )
                    )
                    if project_geometry.crosses(source_geometry):
                        relationships.append(
                            _relationship_record(
                                relationship_id=relationship_start + len(relationships) + 1,
                                relationship="crosses",
                                input_summary=input_summary,
                                project_index=project_index,
                                project_row=project_row,
                                project_geometry=project_geometry,
                                source_index=source_index,
                                source_row=source_row,
                                source_geometry=source_geometry,
                                source_definition=source_definition,
                                project_source=project_source,
                                buffer_feet=buffer_feet,
                                analysis_crs=analysis_crs,
                                measurements=_measure_intersection(intersection),
                            )
                        )
                elif project_buffer.intersects(source_geometry):
                    distance_feet = project_geometry.distance(source_geometry) * FEET_PER_METER
                    relationships.append(
                        _relationship_record(
                            relationship_id=relationship_start + len(relationships) + 1,
                            relationship="within_buffer",
                            input_summary=input_summary,
                            project_index=project_index,
                            project_row=project_row,
                            project_geometry=project_geometry,
                            source_index=source_index,
                            source_row=source_row,
                            source_geometry=source_geometry,
                            source_definition=source_definition,
                            project_source=project_source,
                            buffer_feet=buffer_feet,
                            analysis_crs=analysis_crs,
                            measurements={"distance_feet": round(distance_feet, 2)},
                        )
                    )

    return clipped_wgs84, relationships, analysis_crs


def _analysis_crs(project_layers: list[dict[str, Any]]) -> str:
    for layer in project_layers:
        summary_crs = layer["summary"].get("estimated_local_crs")
        if summary_crs:
            return str(summary_crs)
        try:
            estimated = layer["gdf"].estimate_utm_crs()
        except RuntimeError:
            estimated = None
        if estimated is not None:
            return estimated.to_string()
    return "EPSG:3857"


def _relationship_record(
    *,
    relationship_id: int,
    relationship: str,
    input_summary: dict[str, Any],
    project_index: Any,
    project_row: Any,
    project_geometry: BaseGeometry,
    source_index: Any,
    source_row: Any,
    source_geometry: BaseGeometry,
    source_definition: Any,
    project_source: ProjectSource,
    buffer_feet: float,
    analysis_crs: str,
    measurements: dict[str, float],
) -> dict[str, Any]:
    return {
        "relationship_id": f"spatial-{relationship_id:05d}",
        "source_id": project_source.source_id,
        "source_name": source_definition.name,
        "source_category": source_definition.category,
        "project_input": input_summary["input_path"],
        "project_input_role": input_summary["role"],
        "project_feature_index": _json_value(project_index),
        "project_feature_label": _feature_label(project_row),
        "source_feature_index": _json_value(source_index),
        "source_feature_label": _feature_label(source_row),
        "spatial_relationship": relationship,
        "buffer_feet": buffer_feet,
        "measurements": measurements,
        "project_geometry_type": project_geometry.geom_type,
        "source_geometry_type": source_geometry.geom_type,
        "analysis_crs": analysis_crs,
        "method": "geopandas_shapely_local_spatial_check",
        "review_status": "draft",
    }


def _measure_intersection(intersection: BaseGeometry) -> dict[str, float]:
    measurements: dict[str, float] = {}
    if intersection.is_empty:
        return measurements
    if intersection.length > 0:
        measurements["intersection_length_feet"] = round(intersection.length * FEET_PER_METER, 2)
    if intersection.area > 0:
        measurements["intersection_area_acres"] = round(intersection.area / SQUARE_METERS_PER_ACRE, 4)
    return measurements


def _feature_label(row: Any) -> str:
    for column in ("candidate_label", "placemark_name", "name", "Name", "NAME", "label", "Label", "LABEL"):
        if column in row.index:
            value = row[column]
            if value is not None and str(value).strip() and str(value).lower() != "nan":
                return str(value).strip()
    return ""


def _source_result(
    project_source: ProjectSource,
    source_definition: Any | None = None,
    *,
    status: str,
    source_path: Path | None = None,
    clipped_path: Path | None = None,
    source_feature_count: int = 0,
    clipped_feature_count: int = 0,
    relationship_count: int = 0,
    analysis_crs: str | None = None,
    buffer_feet: float | None = None,
    validation_issues: list[ValidationIssue] | None = None,
) -> dict[str, Any]:
    return {
        "source_id": project_source.source_id,
        "source_name": source_definition.name if source_definition else "",
        "source_category": source_definition.category if source_definition else "",
        "enabled": project_source.enabled,
        "access_method": project_source.access_method,
        "status": status,
        "path": str(source_path) if source_path else project_source.path,
        "clipped_geojson": str(clipped_path) if clipped_path else None,
        "source_feature_count": int(source_feature_count),
        "clipped_feature_count": int(clipped_feature_count),
        "relationship_count": int(relationship_count),
        "analysis_crs": analysis_crs,
        "buffer_feet": buffer_feet,
        "validation_issues": [issue.to_dict() for issue in validation_issues or []],
    }


def _json_value(value: Any) -> str | int:
    if isinstance(value, int):
        return value
    return str(value)
