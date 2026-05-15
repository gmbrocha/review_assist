"""Constraint overlap/proximity analysis from normalized project geometry."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry.base import BaseGeometry

from .inspection import write_geojson
from .project_geometry import (
    PROJECT_ANALYSIS_BOUNDS_PATH,
    PROJECT_FEATURES_PATH,
    ProjectGeometryError,
    build_project_geometry,
    load_project_geometry,
)
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


CONSTRAINT_RESULTS_PATH = Path("constraints/constraint_results.json")


class ConstraintAnalysisError(RuntimeError):
    """Raised when constraint analysis cannot complete."""


def analyze_constraints(project_dir: Path, *, tolerate_source_errors: bool = False) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        catalog = load_source_catalog()
        registry = load_project_source_registry(project_dir)
        project_geometry = _load_or_build_project_geometry(project_dir)
        default_buffer_feet = _default_buffer_feet(manifest.assumptions)
    except (ProjectManifestError, SourceCatalogError, ProjectGeometryError, SpatialAnalysisError, ConstraintAnalysisError) as exc:
        raise ConstraintAnalysisError(str(exc)) from exc

    try:
        project_features = gpd.read_file(project_dir / PROJECT_FEATURES_PATH)
        analysis_bounds = gpd.read_file(project_dir / PROJECT_ANALYSIS_BOUNDS_PATH)
    except Exception as exc:  # pragma: no cover - driver-specific exception types vary.
        raise ConstraintAnalysisError(f"Unable to read normalized project geometry artifacts: {exc}") from exc

    analysis_crs = str(project_geometry.get("analysis_crs") or project_features.crs.to_string())
    project_features = project_features.to_crs(analysis_crs)
    analysis_bounds = analysis_bounds.to_crs(analysis_crs)
    bounds_union = analysis_bounds.geometry.union_all()

    output_dir = project_dir / "constraints"
    clipped_dir = output_dir / "clipped_layers"
    clipped_dir.mkdir(parents=True, exist_ok=True)

    source_results: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
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
            raise ConstraintAnalysisError(issue.message)
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
            raise ConstraintAnalysisError(issue.message)

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
            raise ConstraintAnalysisError(issue.message) from exc

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
            continue

        buffer_feet = project_source.buffer_feet if project_source.buffer_feet is not None else default_buffer_feet
        source_projected = source_gdf.to_crs(analysis_crs)
        clipped = source_projected[source_projected.geometry.intersects(bounds_union)].copy()
        clipped_wgs84 = clipped.to_crs("EPSG:4326") if not clipped.empty else source_projected.iloc[0:0].to_crs("EPSG:4326")
        clipped_path = clipped_dir / f"{project_source.source_id}.geojson"
        write_geojson(clipped_wgs84, clipped_path)

        source_constraints = _source_constraints(
            project_features=project_features,
            source_gdf=clipped,
            source_definition=source_definition,
            project_source=project_source,
            buffer_feet=buffer_feet,
            analysis_crs=analysis_crs,
            constraint_start=len(constraints),
        )
        constraints.extend(source_constraints)
        source_results.append(
            _source_result(
                project_source,
                source_definition,
                status="analyzed",
                source_path=source_path,
                clipped_path=clipped_path,
                source_feature_count=len(source_gdf),
                clipped_feature_count=len(clipped),
                constraint_count=len(source_constraints),
                analysis_crs=analysis_crs,
                buffer_feet=buffer_feet,
                validation_issues=source_issues,
            )
        )

    output_path = project_dir / CONSTRAINT_RESULTS_PATH
    result = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "project_geometry_path": project_geometry.get("output_path"),
        "project_features_path": str(project_dir / PROJECT_FEATURES_PATH),
        "analysis_bounds_path": str(project_dir / PROJECT_ANALYSIS_BOUNDS_PATH),
        "geometry_role": project_geometry.get("geometry_role"),
        "analysis_crs": analysis_crs,
        "default_buffer_feet": default_buffer_feet,
        "sources": source_results,
        "constraint_count": len(constraints),
        "constraints": constraints,
        "validation_issues": validation_issues,
        "output_path": str(output_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_constraint_results(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / CONSTRAINT_RESULTS_PATH
    if not path.exists():
        raise ConstraintAnalysisError(f"Missing constraint results artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConstraintAnalysisError(f"Invalid constraint results JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConstraintAnalysisError(f"Constraint results artifact must be a JSON object: {path}")
    if not isinstance(data.get("constraints", []), list):
        raise ConstraintAnalysisError(f"Constraint results artifact requires a list field named 'constraints': {path}")
    return data


def _load_or_build_project_geometry(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_geometry(project_dir)
    except ProjectGeometryError:
        return build_project_geometry(project_dir)


def _source_constraints(
    *,
    project_features: gpd.GeoDataFrame,
    source_gdf: gpd.GeoDataFrame,
    source_definition: Any,
    project_source: ProjectSource,
    buffer_feet: float,
    analysis_crs: str,
    constraint_start: int,
) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    buffer_distance = buffer_feet / FEET_PER_METER
    for feature_index, feature_row in project_features.iterrows():
        project_geometry = feature_row.geometry
        if project_geometry is None or project_geometry.is_empty:
            continue
        project_buffer = project_geometry.buffer(buffer_distance)
        for source_index, source_row in source_gdf.iterrows():
            source_geometry = source_row.geometry
            if source_geometry is None or source_geometry.is_empty:
                continue
            relationship = _relationship_type(project_geometry, source_geometry)
            measurements: dict[str, float] = {}
            if relationship:
                measurements = _measure_relationship(project_geometry, source_geometry)
            elif project_buffer.intersects(source_geometry):
                relationship = "nearest_within_buffer"
                measurements = {"distance_feet": round(project_geometry.distance(source_geometry) * FEET_PER_METER, 2)}
            if not relationship:
                continue
            constraints.append(
                _constraint_record(
                    constraint_id=constraint_start + len(constraints) + 1,
                    relationship=relationship,
                    feature_row=feature_row,
                    feature_index=feature_index,
                    source_row=source_row,
                    source_index=source_index,
                    project_geometry=project_geometry,
                    source_geometry=source_geometry,
                    source_definition=source_definition,
                    project_source=project_source,
                    buffer_feet=buffer_feet,
                    analysis_crs=analysis_crs,
                    measurements=measurements,
                )
            )
    return constraints


def _relationship_type(project_geometry: BaseGeometry, source_geometry: BaseGeometry) -> str | None:
    if project_geometry.crosses(source_geometry):
        return "crosses"
    if project_geometry.overlaps(source_geometry):
        return "overlaps"
    if project_geometry.contains(source_geometry) or source_geometry.contains(project_geometry):
        return "contains"
    if project_geometry.intersects(source_geometry):
        return "intersects"
    return None


def _constraint_record(
    *,
    constraint_id: int,
    relationship: str,
    feature_row: Any,
    feature_index: Any,
    source_row: Any,
    source_index: Any,
    project_geometry: BaseGeometry,
    source_geometry: BaseGeometry,
    source_definition: Any,
    project_source: ProjectSource,
    buffer_feet: float,
    analysis_crs: str,
    measurements: dict[str, float],
) -> dict[str, Any]:
    return {
        "constraint_id": f"constraint-{constraint_id:05d}",
        "project_feature_id": str(feature_row.get("feature_id", feature_index)),
        "project_feature_name": str(feature_row.get("feature_name") or feature_row.get("feature_group") or feature_index),
        "project_feature_group": str(feature_row.get("feature_group", "")),
        "project_geometry_role": str(feature_row.get("geometry_role", "")),
        "source_id": project_source.source_id,
        "source_name": source_definition.name,
        "source_category": source_definition.category,
        "source_feature_index": _json_value(source_index),
        "source_feature_label": _feature_label(source_row),
        "source_feature_type": _feature_type(source_row),
        "source_feature_subtype": _feature_subtype(source_row),
        "source_feature_original_id": _feature_original_id(source_row),
        "source_feature_date": _feature_date(source_row),
        "source_feature_quality_flag": _feature_quality_flag(source_row),
        "source_feature_source_citation": _feature_source_citation(source_row),
        "source_feature_values": _source_feature_values(source_row),
        "relationship_type": relationship,
        "buffer_feet": buffer_feet,
        "measurements": measurements,
        "project_geometry_type": project_geometry.geom_type,
        "source_geometry_type": source_geometry.geom_type,
        "analysis_crs": analysis_crs,
        "method": "geopandas_shapely_constraint_overlap_check",
        "provenance": {
            "source_id": project_source.source_id,
            "source_name": source_definition.name,
            "source_category": source_definition.category,
            "access_method": project_source.access_method,
            "source_path": project_source.path,
            "method": "geopandas_shapely_constraint_overlap_check",
            "analysis_crs": analysis_crs,
            "desktop_screening_only": True,
        },
        "review_status": "draft",
    }


def _measure_relationship(project_geometry: BaseGeometry, source_geometry: BaseGeometry) -> dict[str, float]:
    measurements: dict[str, float] = {}
    intersection = project_geometry.intersection(source_geometry)
    if not intersection.is_empty:
        if intersection.length > 0:
            measurements["intersection_length_feet"] = round(intersection.length * FEET_PER_METER, 2)
        if intersection.area > 0:
            measurements["intersection_area_acres"] = round(intersection.area / SQUARE_METERS_PER_ACRE, 4)
    distance = project_geometry.distance(source_geometry)
    if distance > 0:
        measurements["distance_feet"] = round(distance * FEET_PER_METER, 2)
    return measurements


def _feature_label(row: Any) -> str:
    for column in (
        "review_assist_feature_label",
        "candidate_label",
        "placemark_name",
        "FAC_NAME",
        "fac_name",
        "comname",
        "COMNAME",
        "sciname",
        "SCINAME",
        "MUSYM",
        "musym",
        "MUKEY",
        "mukey",
        "AREASYMBOL",
        "areasymbol",
        "unitname",
        "UNITNAME",
        "subunitname",
        "SUBUNITNAME",
        "FLD_ZONE",
        "ZONE_SUBTY",
        "gnis_name",
        "GNIS_NAME",
        "name",
        "Name",
        "NAME",
        "label",
        "Label",
        "LABEL",
        "ATTRIBUTE",
        "WETLAND_TYPE",
        "featuretypelabel",
        "ftype",
        "FTYPE",
        "fcode",
        "FCODE",
        "SOURCE_CIT",
    ):
        if column in row.index:
            value = row[column]
            if value is not None and str(value).strip() and str(value).lower() != "nan":
                return str(value).strip()
    return ""


def _feature_type(row: Any) -> str:
    for column in (
        "review_assist_feature_type",
        "FAC_MAP_ICON",
        "FAC_CURR_COMPLIANCE_STATUS",
        "FAC_ACTIVE_FLAG",
        "FAC_MAJOR_FLAG",
        "status",
        "STATUS",
        "MUSYM",
        "musym",
        "FLD_ZONE",
        "featuretypelabel",
        "ATTRIBUTE",
        "WETLAND_TYPE",
        "ftype",
        "FTYPE",
        "fcode",
        "FCODE",
    ):
        if column in row.index:
            value = row[column]
            if value is not None and str(value).strip() and str(value).lower() != "nan":
                return str(value).strip()
    return ""


def _feature_subtype(row: Any) -> str:
    return _feature_value(
        row,
        (
            "review_assist_feature_subtype",
            "FAC_CURR_SNC_FLG",
            "FAC_MAJOR_FLAG",
            "FAC_ACTIVE_FLAG",
            "listing_status",
            "LISTING_STATUS",
            "MUKEY",
            "mukey",
            "AREASYMBOL",
            "areasymbol",
            "unitname",
            "UNITNAME",
            "subunitname",
            "SUBUNITNAME",
            "unit",
            "UNIT",
            "subunit",
            "SUBUNIT",
            "ZONE_SUBTY",
            "fcode",
            "FCODE",
            "WETLAND_TYPE",
        ),
    )


def _feature_original_id(row: Any) -> str:
    return _feature_value(
        row,
        (
            "review_assist_feature_original_id",
            "REGISTRY_ID",
            "GLOBALID",
            "GFID",
            "MUKEY",
            "mukey",
            "FLD_AR_ID",
            "permanent_identifier",
            "Permanent_Identifier",
            "nhdplusid",
            "NHDPlusID",
            "GlobalID",
            "globalid",
            "objectid_1",
            "source_id",
            "entity_id",
            "OBJECTID",
            "objectid",
        ),
    )


def _feature_date(row: Any) -> str:
    return _feature_value(
        row,
        (
            "review_assist_feature_date",
            "FAC_DATE_LAST_INSPECTION",
            "FAC_DATE_LAST_INSPECTION_EPA",
            "FAC_DATE_LAST_INSPECTION_STATE",
            "FAC_DATE_LAST_FORMAL_ACTION",
            "FAC_DATE_LAST_FORMAL_ACT_EPA",
            "FAC_DATE_LAST_FORMAL_ACT_ST",
            "FAC_DATE_LAST_INFORMAL_ACTION",
            "FAC_DATE_LAST_INFORMAL_ACT_EPA",
            "FAC_DATE_LAST_INFORMAL_ACT_ST",
            "FAC_DATE_LAST_PENALTY",
            "effectdate",
            "EFFECTDATE",
            "pubdate",
            "PUBDATE",
            "vacatedate",
            "VACATEDATE",
            "EFF_DATE",
            "PANEL_DATE",
            "REVERT_DATE",
            "fdate",
            "FDATE",
            "UPDATED",
            "DATE",
        ),
    )


def _feature_quality_flag(row: Any) -> str:
    return _feature_value(
        row,
        (
            "review_assist_quality_flag",
            "FAC_ACTIVE_FLAG",
            "FAC_MAJOR_FLAG",
            "FAC_CURR_COMPLIANCE_STATUS",
            "FAC_CURR_SNC_FLG",
            "FAC_COLLECTION_METHOD",
            "FAC_ACCURACY_METERS",
            "accuracy",
            "ACCURACY",
            "SFHA_TF",
            "AR_REVERT",
            "DUAL_ZONE",
            "visibilityfilter",
            "VisibilityFilter",
        ),
    )


def _feature_source_citation(row: Any) -> str:
    return _feature_value(row, ("review_assist_source_citation", "DFR_URL", "fedreg", "FEDREG", "SOURCE_CIT", "source_cit", "Source_Cit"))


def _source_feature_values(row: Any) -> dict[str, str]:
    values = {
        "flood_zone": _feature_value(row, ("FLD_ZONE", "review_assist_feature_type")),
        "flood_zone_subtype": _feature_value(row, ("ZONE_SUBTY", "review_assist_feature_subtype")),
        "sfha_flag": _feature_value(row, ("SFHA_TF", "review_assist_quality_flag")),
        "static_bfe": _feature_value(row, ("STATIC_BFE",)),
        "vertical_datum": _feature_value(row, ("V_DATUM",)),
        "depth": _feature_value(row, ("DEPTH",)),
        "length_unit": _feature_value(row, ("LEN_UNIT",)),
        "source_citation": _feature_source_citation(row),
        "species_common_name": _feature_value(row, ("comname", "COMNAME", "review_assist_feature_label")),
        "species_scientific_name": _feature_value(row, ("sciname", "SCINAME")),
        "critical_habitat_status": _feature_value(row, ("status", "STATUS", "review_assist_feature_type")),
        "listing_status": _feature_value(row, ("listing_status", "LISTING_STATUS")),
        "critical_habitat_unit": _feature_value(row, ("unitname", "UNITNAME", "unit", "UNIT")),
        "critical_habitat_subunit": _feature_value(row, ("subunitname", "SUBUNITNAME", "subunit", "SUBUNIT")),
        "federal_register": _feature_value(row, ("fedreg", "FEDREG", "review_assist_source_citation")),
        "publication_date": _feature_value(row, ("pubdate", "PUBDATE")),
        "effective_date": _feature_value(row, ("effectdate", "EFFECTDATE", "review_assist_feature_date")),
        "vacate_date": _feature_value(row, ("vacatedate", "VACATEDATE")),
        "accuracy": _feature_value(row, ("accuracy", "ACCURACY", "review_assist_quality_flag")),
        "facility_name": _feature_value(row, ("FAC_NAME", "fac_name", "review_assist_feature_label")),
        "facility_registry_id": _feature_value(row, ("REGISTRY_ID", "review_assist_feature_original_id")),
        "facility_street": _feature_value(row, ("FAC_STREET",)),
        "facility_city": _feature_value(row, ("FAC_CITY",)),
        "facility_state": _feature_value(row, ("FAC_STATE",)),
        "facility_zip": _feature_value(row, ("FAC_ZIP",)),
        "facility_county": _feature_value(row, ("FAC_COUNTY",)),
        "facility_programs": _facility_programs(row),
        "facility_active_flag": _feature_value(row, ("FAC_ACTIVE_FLAG",)),
        "facility_major_flag": _feature_value(row, ("FAC_MAJOR_FLAG",)),
        "facility_current_compliance_status": _feature_value(row, ("FAC_CURR_COMPLIANCE_STATUS",)),
        "facility_current_snc_flag": _feature_value(row, ("FAC_CURR_SNC_FLG",)),
        "facility_inspection_count": _feature_value(row, ("FAC_INSPECTION_COUNT",)),
        "facility_last_inspection_date": _feature_value(row, ("FAC_DATE_LAST_INSPECTION",)),
        "facility_formal_action_count": _feature_value(row, ("FAC_FORMAL_ACTION_COUNT",)),
        "facility_informal_action_count": _feature_value(row, ("FAC_INFORMAL_COUNT",)),
        "facility_total_penalties": _feature_value(row, ("FAC_TOTAL_PENALTIES",)),
        "facility_collection_method": _feature_value(row, ("FAC_COLLECTION_METHOD",)),
        "facility_accuracy_meters": _feature_value(row, ("FAC_ACCURACY_METERS",)),
        "facility_dfr_url": _feature_value(row, ("DFR_URL", "review_assist_source_citation")),
        "soil_mapunit_symbol": _feature_value(row, ("MUSYM", "musym", "review_assist_feature_label")),
        "soil_mapunit_key": _feature_value(row, ("MUKEY", "mukey", "review_assist_feature_original_id")),
        "soil_area_symbol": _feature_value(row, ("AREASYMBOL", "areasymbol")),
        "soil_spatial_version": _feature_value(row, ("SPATIALVER", "spatialver")),
    }
    return {key: value for key, value in values.items() if value}


def _facility_programs(row: Any) -> str:
    labels: list[str] = []
    for column, label in (
        ("AIR_FLAG", "AIR"),
        ("NPDES_FLAG", "NPDES"),
        ("RCRA_FLAG", "RCRA"),
        ("TRI_FLAG", "TRI"),
        ("SDWIS_FLAG", "SDWA"),
        ("SDWA_FLAG", "SDWA"),
        ("GHG_FLAG", "GHG"),
    ):
        value = _feature_value(row, (column,))
        if value.upper() in {"Y", "YES", "TRUE", "T", "1"} and label not in labels:
            labels.append(label)
    if labels:
        return ", ".join(labels)
    return _feature_value(row, ("review_assist_feature_type",))


def _feature_value(row: Any, columns: tuple[str, ...]) -> str:
    lower_index = {str(column).lower(): column for column in row.index}
    for column in columns:
        key = column if column in row.index else lower_index.get(column.lower())
        if key is None:
            continue
        value = row[key]
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
    constraint_count: int = 0,
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
        "constraint_count": int(constraint_count),
        "analysis_crs": analysis_crs,
        "buffer_feet": buffer_feet,
        "validation_issues": [issue.to_dict() for issue in validation_issues or []],
    }


def _source_issue(project_source: ProjectSource, *, code: str, message: str, location: str) -> ValidationIssue:
    return ValidationIssue(
        severity="warning",
        code=code,
        message=message,
        location=location,
        source_id=project_source.source_id,
    )


def _json_value(value: Any) -> str | int:
    if isinstance(value, int):
        return value
    return str(value)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
