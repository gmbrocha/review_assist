"""Report-facing constraint analysis by comparison unit."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry.base import BaseGeometry

from .comparison_units import COMPARISON_UNITS_PATH, ComparisonUnitError, build_comparison_units, load_comparison_units
from .constraints import (
    ConstraintAnalysisError,
    _feature_date,
    _feature_label,
    _feature_original_id,
    _feature_quality_flag,
    _feature_source_citation,
    _feature_subtype,
    _feature_type,
    _feature_value,
    _json_value,
    _relationship_type,
    _source_feature_values,
    _source_issue,
    _source_result,
)
from .project_geometry import PROJECT_ANALYSIS_BOUNDS_PATH, ProjectGeometryError, build_project_geometry, load_project_geometry
from .projects import ProjectManifestError, load_project_manifest
from .source_catalog import (
    ProjectSource,
    SourceCatalogError,
    load_project_source_registry,
    load_source_catalog,
    resolve_project_source_path,
)
from .spatial_analysis import FEET_PER_METER, SQUARE_METERS_PER_ACRE, SpatialAnalysisError, _default_buffer_feet
from .validation import ValidationIssue


COMPARISON_UNIT_CONSTRAINTS_PATH = Path("constraints/comparison_unit_constraints.json")


class ComparisonUnitConstraintError(RuntimeError):
    """Raised when comparison-unit constraint analysis cannot complete."""


def analyze_comparison_unit_constraints(project_dir: Path, *, tolerate_source_errors: bool = False) -> dict[str, Any]:
    """Run report-facing source checks against comparison units.

    Raw project-feature constraints remain in ``constraint_results.json``. This artifact is the
    deterministic input for standard deliverable tables and later matrix-backed report targets.
    """

    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        catalog = load_source_catalog()
        registry = load_project_source_registry(project_dir)
        project_geometry = _load_or_build_project_geometry(project_dir)
        comparison_units = _load_or_build_comparison_units(project_dir)
        default_buffer_feet = _default_buffer_feet(manifest.assumptions)
    except (
        ProjectManifestError,
        SourceCatalogError,
        ProjectGeometryError,
        ComparisonUnitError,
        SpatialAnalysisError,
        ConstraintAnalysisError,
    ) as exc:
        raise ComparisonUnitConstraintError(str(exc)) from exc

    try:
        units_path = Path(str(comparison_units.get("comparison_units_path") or project_dir / COMPARISON_UNITS_PATH))
        unit_gdf = gpd.read_file(units_path)
        analysis_bounds = gpd.read_file(project_dir / PROJECT_ANALYSIS_BOUNDS_PATH)
    except Exception as exc:  # pragma: no cover - driver-specific exception types vary.
        raise ComparisonUnitConstraintError(f"Unable to read comparison unit artifacts: {exc}") from exc

    analysis_crs = str(project_geometry.get("analysis_crs") or unit_gdf.crs.to_string())
    if unit_gdf.crs is None:
        unit_gdf = unit_gdf.set_crs("EPSG:4326", allow_override=True)
    if analysis_bounds.crs is None:
        analysis_bounds = analysis_bounds.set_crs("EPSG:4326", allow_override=True)
    unit_gdf = unit_gdf.to_crs(analysis_crs)
    analysis_bounds = analysis_bounds.to_crs(analysis_crs)
    bounds_union = analysis_bounds.geometry.union_all()

    source_results: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    no_overlap_summaries: list[dict[str, Any]] = []
    validation_issues: list[dict[str, Any]] = []

    for project_source in registry.sources:
        source_definition = catalog.sources.get(project_source.source_id)
        if source_definition is None:
            issue = ValidationIssue(
                severity="warning",
                code="unknown_project_source",
                message=f"Project source '{project_source.source_id}' is not present in the global catalog.",
                location=str(project_dir / "config" / "sources.json"),
            )
            validation_issues.append(issue.to_dict())
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
            issue = _source_issue(
                project_source,
                code="local_source_path_missing",
                message=f"Enabled local source '{project_source.source_id}' requires a path.",
                location=str(project_dir / "config" / "sources.json"),
            )
            if tolerate_source_errors:
                source_results.append(_source_result(project_source, source_definition, status="source_missing", validation_issues=[issue]))
                continue
            raise ComparisonUnitConstraintError(issue.message)
        if not source_path.exists():
            issue = _source_issue(
                project_source,
                code="missing_local_source_file",
                message=f"Missing local source file for '{project_source.source_id}': {source_path}",
                location=str(source_path),
            )
            if tolerate_source_errors:
                source_results.append(
                    _source_result(project_source, source_definition, status="source_missing", source_path=source_path, validation_issues=[issue])
                )
                continue
            raise ComparisonUnitConstraintError(issue.message)

        try:
            source_gdf = gpd.read_file(source_path)
        except Exception as exc:  # pragma: no cover - driver-specific exception types vary.
            issue = _source_issue(
                project_source,
                code="unreadable_local_source_file",
                message=f"Unable to read source layer '{project_source.source_id}': {source_path}: {exc}",
                location=str(source_path),
            )
            if tolerate_source_errors:
                source_results.append(
                    _source_result(
                        project_source,
                        source_definition,
                        status="source_unreadable",
                        source_path=source_path,
                        validation_issues=[issue],
                    )
                )
                continue
            raise ComparisonUnitConstraintError(issue.message) from exc

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
            source_results.append(
                _source_result(
                    project_source,
                    source_definition,
                    status="analyzed_empty",
                    source_path=source_path,
                    validation_issues=source_issues,
                )
            )
            no_overlap_summaries.extend(
                _no_overlap_summaries(
                    unit_gdf=unit_gdf,
                    source_definition=source_definition,
                    project_source=project_source,
                    source_path=source_path,
                    source_feature_count=0,
                )
            )
            continue

        buffer_feet = project_source.buffer_feet if project_source.buffer_feet is not None else default_buffer_feet
        source_projected = source_gdf.to_crs(analysis_crs)
        clipped = source_projected[source_projected.geometry.intersects(bounds_union)].copy()
        source_constraints = _source_comparison_unit_constraints(
            comparison_units=unit_gdf,
            source_gdf=clipped,
            source_definition=source_definition,
            project_source=project_source,
            source_path=source_path,
            buffer_feet=buffer_feet,
            analysis_crs=analysis_crs,
            constraint_start=len(constraints),
        )
        constraints.extend(source_constraints)
        no_overlap_summaries.extend(
            _no_overlap_summaries(
                unit_gdf=unit_gdf,
                source_definition=source_definition,
                project_source=project_source,
                source_path=source_path,
                source_feature_count=len(clipped),
                constraints=source_constraints,
            )
        )
        source_results.append(
            _source_result(
                project_source,
                source_definition,
                status="analyzed",
                source_path=source_path,
                source_feature_count=len(source_gdf),
                clipped_feature_count=len(clipped),
                constraint_count=len(source_constraints),
                analysis_crs=analysis_crs,
                buffer_feet=buffer_feet,
                validation_issues=source_issues,
            )
        )

    output_path = project_dir / COMPARISON_UNIT_CONSTRAINTS_PATH
    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "comparison_units_path": str(units_path),
        "comparison_units_metadata_path": comparison_units.get("output_path"),
        "analysis_bounds_path": str(project_dir / PROJECT_ANALYSIS_BOUNDS_PATH),
        "analysis_crs": analysis_crs,
        "default_buffer_feet": default_buffer_feet,
        "sources": source_results,
        "constraint_count": len(constraints),
        "constraints": constraints,
        "no_overlap_summaries": no_overlap_summaries,
        "validation_issues": validation_issues,
        "output_path": str(output_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_comparison_unit_constraints(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / COMPARISON_UNIT_CONSTRAINTS_PATH
    if not path.exists():
        raise ComparisonUnitConstraintError(f"Missing comparison-unit constraint artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ComparisonUnitConstraintError(f"Invalid comparison-unit constraint JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ComparisonUnitConstraintError(f"Comparison-unit constraint artifact must be a JSON object: {path}")
    if not isinstance(data.get("constraints", []), list):
        raise ComparisonUnitConstraintError(f"Comparison-unit constraint artifact requires a list field named 'constraints': {path}")
    return data


def _load_or_build_project_geometry(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_geometry(project_dir)
    except ProjectGeometryError:
        return build_project_geometry(project_dir)


def _load_or_build_comparison_units(project_dir: Path) -> dict[str, Any]:
    try:
        return load_comparison_units(project_dir)
    except ComparisonUnitError:
        return build_comparison_units(project_dir)


def _source_comparison_unit_constraints(
    *,
    comparison_units: gpd.GeoDataFrame,
    source_gdf: gpd.GeoDataFrame,
    source_definition: Any,
    project_source: ProjectSource,
    source_path: Path,
    buffer_feet: float,
    analysis_crs: str,
    constraint_start: int,
) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    for unit_index, unit_row in comparison_units.iterrows():
        unit_geometry = unit_row.geometry
        if unit_geometry is None or unit_geometry.is_empty:
            continue
        analysis_geometry, analysis_geometry_kind = _analysis_geometry(unit_geometry, _unit_geometry_role(unit_row), buffer_feet)
        for source_index, source_row in source_gdf.iterrows():
            source_geometry = source_row.geometry
            if source_geometry is None or source_geometry.is_empty:
                continue
            relationship = _comparison_unit_relationship(unit_geometry, analysis_geometry, source_geometry)
            if not relationship:
                continue
            constraints.append(
                _comparison_unit_constraint_record(
                    constraint_id=constraint_start + len(constraints) + 1,
                    relationship=relationship,
                    unit_row=unit_row,
                    unit_index=unit_index,
                    unit_geometry=unit_geometry,
                    analysis_geometry=analysis_geometry,
                    analysis_geometry_kind=analysis_geometry_kind,
                    source_row=source_row,
                    source_index=source_index,
                    source_geometry=source_geometry,
                    source_definition=source_definition,
                    project_source=project_source,
                    source_path=source_path,
                    buffer_feet=buffer_feet,
                    analysis_crs=analysis_crs,
                )
            )
    return constraints


def _analysis_geometry(unit_geometry: BaseGeometry, geometry_role: str, buffer_feet: float) -> tuple[BaseGeometry, str]:
    if geometry_role == "polygon_area":
        return unit_geometry, "polygon"
    buffer_distance = buffer_feet / FEET_PER_METER
    if buffer_distance <= 0:
        return unit_geometry, "raw_geometry"
    if geometry_role == "line_corridor":
        return unit_geometry.buffer(buffer_distance), "buffered_corridor"
    if geometry_role == "point_site":
        return unit_geometry.buffer(buffer_distance), "buffered_site"
    return unit_geometry.buffer(buffer_distance), "buffered_geometry"


def _comparison_unit_relationship(
    raw_geometry: BaseGeometry,
    analysis_geometry: BaseGeometry,
    source_geometry: BaseGeometry,
) -> str | None:
    raw_relationship = _relationship_type(raw_geometry, source_geometry)
    if raw_relationship:
        return raw_relationship
    if not analysis_geometry.intersects(source_geometry):
        return None
    intersection = analysis_geometry.intersection(source_geometry)
    if not intersection.is_empty and intersection.area > 0:
        return "overlaps"
    return "nearest_within_buffer"


def _comparison_unit_constraint_record(
    *,
    constraint_id: int,
    relationship: str,
    unit_row: Any,
    unit_index: Any,
    unit_geometry: BaseGeometry,
    analysis_geometry: BaseGeometry,
    analysis_geometry_kind: str,
    source_row: Any,
    source_index: Any,
    source_geometry: BaseGeometry,
    source_definition: Any,
    project_source: ProjectSource,
    source_path: Path,
    buffer_feet: float,
    analysis_crs: str,
) -> dict[str, Any]:
    source_values = _source_feature_values(source_row)
    source_values.update(_report_table_source_values(source_row))
    uncertainty_flags = ["desktop_screening_only"]
    if buffer_feet > 0 and analysis_geometry_kind.startswith("buffered"):
        uncertainty_flags.append("buffer_assumption")
    if not _feature_date(source_row):
        uncertainty_flags.append("source_date_unknown")
    return {
        "constraint_id": f"comparison-unit-constraint-{constraint_id:05d}",
        "comparison_unit_id": _string_value(unit_row, "comparison_unit_id", unit_index),
        "comparison_unit_name": _string_value(unit_row, "comparison_unit_name", unit_index),
        "comparison_unit_group": _string_value(unit_row, "comparison_unit_group", ""),
        "comparison_unit_type": _string_value(unit_row, "comparison_unit_type", ""),
        "geometry_role": _unit_geometry_role(unit_row),
        "raw_feature_ids": _string_list(unit_row.get("source_feature_ids", [])),
        "raw_feature_count": _int_value(unit_row.get("source_feature_count"), default=len(_string_list(unit_row.get("source_feature_ids", [])))),
        "source_id": project_source.source_id,
        "source_name": source_definition.name,
        "source_category": source_definition.category,
        "source_layer": _source_layer(source_row),
        "source_feature_index": _json_value(source_index),
        "source_feature_label": _feature_label(source_row),
        "source_feature_type": _feature_type(source_row),
        "source_feature_subtype": _feature_subtype(source_row),
        "source_feature_original_id": _feature_original_id(source_row),
        "source_feature_geometry_hash": _geometry_hash(source_geometry),
        "source_feature_date": _feature_date(source_row),
        "source_feature_quality_flag": _feature_quality_flag(source_row),
        "source_feature_source_citation": _feature_source_citation(source_row),
        "source_feature_values": source_values,
        "relationship_type": relationship,
        "buffer_feet": buffer_feet,
        "analysis_geometry_kind": analysis_geometry_kind,
        "measurement_crs": analysis_crs,
        "measurements": _measure_comparison_unit_relationship(unit_geometry, analysis_geometry, source_geometry),
        "comparison_unit_geometry_type": unit_geometry.geom_type,
        "source_geometry_type": source_geometry.geom_type,
        "provenance": {
            "source_id": project_source.source_id,
            "source_name": source_definition.name,
            "source_category": source_definition.category,
            "access_method": project_source.access_method,
            "source_path": str(source_path),
            "method": "geopandas_shapely_comparison_unit_constraint_check",
            "analysis_crs": analysis_crs,
            "analysis_geometry_kind": analysis_geometry_kind,
            "buffer_feet": buffer_feet,
            "desktop_screening_only": True,
        },
        "uncertainty_flags": uncertainty_flags,
        "review_status": "draft",
    }


def _measure_comparison_unit_relationship(
    raw_geometry: BaseGeometry,
    analysis_geometry: BaseGeometry,
    source_geometry: BaseGeometry,
) -> dict[str, float]:
    measurements: dict[str, float] = {}
    intersection = analysis_geometry.intersection(source_geometry)
    if not intersection.is_empty:
        if intersection.length > 0:
            measurements["intersection_length_feet"] = round(intersection.length * FEET_PER_METER, 2)
        if intersection.area > 0:
            measurements["intersection_area_acres"] = round(intersection.area / SQUARE_METERS_PER_ACRE, 4)
    raw_intersection = raw_geometry.intersection(source_geometry)
    if not raw_intersection.is_empty:
        if raw_intersection.length > 0:
            measurements["raw_intersection_length_feet"] = round(raw_intersection.length * FEET_PER_METER, 2)
        if raw_intersection.area > 0:
            measurements["raw_intersection_area_acres"] = round(raw_intersection.area / SQUARE_METERS_PER_ACRE, 4)
    distance = raw_geometry.distance(source_geometry)
    measurements["distance_feet"] = round(distance * FEET_PER_METER, 2)
    if analysis_geometry.area > 0:
        measurements["analysis_geometry_area_acres"] = round(analysis_geometry.area / SQUARE_METERS_PER_ACRE, 4)
    return measurements


def _no_overlap_summaries(
    *,
    unit_gdf: gpd.GeoDataFrame,
    source_definition: Any,
    project_source: ProjectSource,
    source_path: Path,
    source_feature_count: int,
    constraints: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    constraints_by_unit = {str(item.get("comparison_unit_id", "")) for item in constraints or []}
    summaries: list[dict[str, Any]] = []
    for unit_index, unit_row in unit_gdf.iterrows():
        unit_id = _string_value(unit_row, "comparison_unit_id", unit_index)
        if unit_id in constraints_by_unit:
            continue
        summaries.append(
            {
                "comparison_unit_id": unit_id,
                "comparison_unit_name": _string_value(unit_row, "comparison_unit_name", unit_index),
                "comparison_unit_type": _string_value(unit_row, "comparison_unit_type", ""),
                "source_id": project_source.source_id,
                "source_name": source_definition.name,
                "source_category": source_definition.category,
                "relationship_type": "source_available_no_overlap",
                "source_feature_count": source_feature_count,
                "source_path": str(source_path),
                "review_status": "draft",
                "uncertainty_flags": ["desktop_screening_only"],
            }
        )
    return summaries


def _report_table_source_values(row: Any) -> dict[str, str]:
    return {
        key: value
        for key, value in {
            "nwi_attribute": _feature_value(row, ("ATTRIBUTE", "attribute")),
            "nwi_wetland_type": _feature_value(row, ("WETLAND_TYPE", "wetland_type")),
            "nwi_system": _feature_value(row, ("SYSTEM", "system")),
            "nwi_class_name": _feature_value(row, ("CLASS_NAME", "class_name")),
            "census_geoid": _feature_value(row, ("GEOID", "geoid", "GEOIDFQ", "geoidfq", "TRACTCE", "tractce")),
            "census_geography": _feature_value(row, ("Geography", "geography", "NAMELSAD", "namelsad", "NAME", "name")),
            "census_geography_level": _feature_value(row, ("geography_level", "GEO_LEVEL", "SUMLEV", "summary_level")),
            "population_below_poverty_line": _feature_value(
                row,
                (
                    "population_below_poverty_line",
                    "below_poverty_population",
                    "poverty_population",
                    "B17001_002E",
                    "B17001_002",
                    "S1701_C02_001E",
                ),
            ),
            "population_below_poverty_line_moe": _feature_value(row, ("population_below_poverty_line_moe", "B17001_002M")),
            "black_or_african_american": _feature_value(row, ("black_or_african_american", "black", "B02001_003E", "B02001_003")),
            "black_or_african_american_moe": _feature_value(row, ("black_or_african_american_moe", "B02001_003M")),
            "asian": _feature_value(row, ("asian", "B02001_005E", "B02001_005")),
            "asian_moe": _feature_value(row, ("asian_moe", "B02001_005M")),
            "white": _feature_value(row, ("white", "B02001_002E", "B02001_002")),
            "white_moe": _feature_value(row, ("white_moe", "B02001_002M")),
        }.items()
        if value
    }


def _source_layer(row: Any) -> str:
    return _feature_value(row, ("review_assist_source_layer", "source_layer", "layer", "Layer", "LAYER", "featuretypelabel"))


def _unit_geometry_role(row: Any) -> str:
    return _string_value(row, "geometry_role", "")


def _string_value(row: Any, column: str, default: Any) -> str:
    if column not in row.index:
        return str(default)
    value = row[column]
    if value is None:
        return str(default)
    text = str(value).strip()
    return str(default) if not text or text.lower() == "nan" else text


def _string_list(value: Any) -> list[str]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return [text]
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    return [text]


def _int_value(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _geometry_hash(geometry: BaseGeometry) -> str:
    return hashlib.sha1(geometry.wkb).hexdigest()[:16]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
