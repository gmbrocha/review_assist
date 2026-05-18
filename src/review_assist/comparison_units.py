"""Report-facing comparison unit generation."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import MultiLineString, MultiPoint
from shapely.geometry.base import BaseGeometry
from shapely.ops import linemerge, unary_union

from .inspection import ProjectInspectionError, write_geojson
from .project_geometry import ProjectGeometryError, build_project_geometry
from .projects import ProjectManifestError, load_project_manifest


COMPARISON_UNITS_PATH = Path("intermediate/comparison_units.geojson")
COMPARISON_UNITS_METADATA_PATH = Path("intermediate/comparison_units.json")


class ComparisonUnitError(RuntimeError):
    """Raised when comparison unit generation cannot complete."""


@dataclass(frozen=True)
class _Grouping:
    key: str
    label: str
    method: str
    requires_reviewer_confirmation: bool


def build_comparison_units(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
        project_geometry = build_project_geometry(project_dir)
        inspection = _load_geometry_summary(project_geometry)
    except (ProjectManifestError, ProjectGeometryError, ProjectInspectionError) as exc:
        raise ComparisonUnitError(str(exc)) from exc

    analysis_crs = str(project_geometry.get("analysis_crs") or "EPSG:4326")
    geometry_role = str(project_geometry.get("geometry_role") or "mixed")
    project_layers = _load_project_layers(inspection, analysis_crs)
    if not project_layers:
        raise ComparisonUnitError("Comparison unit generation requires at least one project layer.")

    unit_rows, unit_geometries, validation_issues = _comparison_unit_rows(project_layers, geometry_role)
    if not unit_rows:
        raise ComparisonUnitError("Comparison unit generation produced no comparison units.")

    output_path = project_dir / COMPARISON_UNITS_PATH
    metadata_path = project_dir / COMPARISON_UNITS_METADATA_PATH
    unit_gdf = gpd.GeoDataFrame(unit_rows, geometry=unit_geometries, crs=analysis_crs)
    write_geojson(unit_gdf.to_crs("EPSG:4326"), output_path)

    expected_count, expected_issue = _expected_comparison_unit_count(manifest.assumptions)
    if expected_issue:
        validation_issues.append(expected_issue)
    expected_count_status = _expected_count_status(expected_count, len(unit_rows))
    if expected_count_status == "mismatch":
        validation_issues.append(
            _issue(
                "warning",
                "comparison_unit_count_mismatch",
                (
                    f"Generated {len(unit_rows)} comparison unit(s), but project assumptions "
                    f"expected {expected_count}."
                ),
                str(metadata_path),
            )
        )

    metadata = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "geometry_role": geometry_role,
        "analysis_crs": analysis_crs,
        "default_buffer_feet": project_geometry.get("default_buffer_feet"),
        "comparison_unit_count": len(unit_rows),
        "raw_project_feature_count": _raw_project_feature_count(project_layers),
        "expected_comparison_unit_count": expected_count,
        "expected_count_status": expected_count_status,
        "comparison_units_path": str(output_path),
        "project_features_path": project_geometry.get("project_features_path"),
        "validation_issues": validation_issues,
        "output_path": str(metadata_path),
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def load_comparison_units(project_dir: Path) -> dict[str, Any]:
    path = project_dir.resolve() / COMPARISON_UNITS_METADATA_PATH
    if not path.exists():
        raise ComparisonUnitError(f"Missing comparison units artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ComparisonUnitError(f"Invalid comparison units JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ComparisonUnitError(f"Comparison units artifact must be a JSON object: {path}")

    geojson_path = Path(str(data.get("comparison_units_path") or project_dir.resolve() / COMPARISON_UNITS_PATH))
    if not geojson_path.exists():
        raise ComparisonUnitError(f"Missing comparison units GeoJSON artifact: {geojson_path}")
    return data


def _load_geometry_summary(project_geometry: dict[str, Any]) -> dict[str, Any]:
    summary_path = project_geometry.get("geometry_summary_path")
    if not summary_path:
        raise ProjectInspectionError("Project geometry artifact does not reference a geometry summary.")
    path = Path(str(summary_path))
    if not path.exists():
        raise ProjectInspectionError(f"Missing geometry summary artifact: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectInspectionError(f"Invalid geometry summary JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectInspectionError(f"Geometry summary artifact must be a JSON object: {path}")
    return data


def _load_project_layers(inspection: dict[str, Any], analysis_crs: str) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for item in inspection.get("inputs", []):
        if not isinstance(item, dict):
            continue
        geojson_path = Path(str(item.get("normalized_geojson", "")))
        if not geojson_path.exists():
            raise ComparisonUnitError(f"Missing normalized input GeoJSON: {geojson_path}")
        gdf = gpd.read_file(geojson_path)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        layers.append({"summary": item, "gdf": gdf.to_crs(analysis_crs)})
    return layers


def _comparison_unit_rows(
    project_layers: list[dict[str, Any]],
    geometry_role: str,
) -> tuple[list[dict[str, Any]], list[BaseGeometry], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    raw_roles: set[str] = set()
    for layer in project_layers:
        summary = layer["summary"]
        gdf = layer["gdf"]
        for index, row in gdf.iterrows():
            geometry = row.geometry
            if geometry is None or geometry.is_empty:
                continue
            role = _geometry_role_for_geometry(geometry)
            raw_roles.add(role)
            grouping = _grouping_for_row(row, index, role, summary)
            grouped[(role, grouping.key)].append(
                {
                    "row": row,
                    "index": index,
                    "summary": summary,
                    "geometry": geometry,
                    "role": role,
                    "grouping": grouping,
                }
            )

    rows: list[dict[str, Any]] = []
    geometries: list[BaseGeometry] = []
    validation_issues: list[dict[str, Any]] = []
    if geometry_role == "mixed" or len(raw_roles) > 1:
        validation_issues.append(
            _issue(
                "warning",
                "mixed_geometry_requires_review",
                "Project inputs contain multiple geometry families; comparison units are grouped by geometry family first.",
                None,
            )
        )

    for counter, (_group_key, records) in enumerate(sorted(grouped.items(), key=_group_sort_key), start=1):
        grouping = records[0]["grouping"]
        unit_id = f"comparison-unit-{counter:05d}"
        role = str(records[0]["role"])
        comparison_unit_type = _comparison_unit_type(records, raw_roles)
        requires_review = grouping.requires_reviewer_confirmation or comparison_unit_type == "boundary_context"
        geometry = _combined_geometry([record["geometry"] for record in records], role)

        row = {
            "comparison_unit_id": unit_id,
            "comparison_unit_name": _unit_name(grouping.label, role, counter),
            "comparison_unit_group": grouping.label,
            "comparison_unit_type": comparison_unit_type,
            "geometry_role": role,
            "source_input": _single_or_multiple(_record_values(records, "source_input")),
            "source_feature_ids": _record_values(records, "source_feature_id"),
            "source_feature_count": len(records),
            "style_url": _single_or_multiple(_record_values(records, "style_url")),
            "style_color": _single_or_multiple(_record_values(records, "style_color")),
            "placemark_names": _record_values(records, "placemark_name"),
            "candidate_labels": _record_values(records, "candidate_label"),
            "grouping_method": grouping.method,
            "requires_reviewer_confirmation": requires_review,
        }
        rows.append(row)
        geometries.append(geometry)

        if grouping.requires_reviewer_confirmation:
            validation_issues.append(
                _issue(
                    "warning",
                    "comparison_unit_grouping_requires_review",
                    f"Comparison unit '{row['comparison_unit_name']}' used weak or fallback grouping: {grouping.method}.",
                    unit_id,
                )
            )
        if comparison_unit_type == "boundary_context":
            validation_issues.append(
                _issue(
                    "warning",
                    "mixed_boundary_proposition_ambiguity",
                    (
                        f"Polygon comparison unit '{row['comparison_unit_name']}' appears alongside line or point "
                        "propositions and is marked as boundary context for reviewer confirmation."
                    ),
                    unit_id,
                )
            )

    return rows, geometries, validation_issues


def _group_sort_key(item: tuple[tuple[str, str], list[dict[str, Any]]]) -> tuple[str, str]:
    (role, key), records = item
    label = records[0]["grouping"].label if records else key
    return role, _slug(label), key


def _grouping_for_row(row: Any, index: Any, role: str, summary: dict[str, Any]) -> _Grouping:
    source_input = str(summary.get("input_path", ""))
    if role == "line_corridor":
        return _line_grouping(row, index, source_input)
    if role == "point_site":
        return _point_grouping(row)
    if role == "polygon_area":
        return _polygon_grouping(row, index, source_input)
    return _fallback_grouping(role, index, source_input)


def _line_grouping(row: Any, index: Any, source_input: str) -> _Grouping:
    folder_group = _string_value(row, "folder_group")
    if folder_group:
        return _Grouping(f"folder:{folder_group}", folder_group, "folder_group", False)

    placemark_name = _string_value(row, "placemark_name")
    if placemark_name and _is_explicit_alternative_name(placemark_name):
        return _Grouping(f"explicit-name:{placemark_name}", placemark_name, "explicit_name", False)

    style_url = _string_value(row, "style_url")
    candidate_label = _string_value(row, "candidate_label")
    if style_url and candidate_label:
        return _Grouping(
            f"style-candidate:{style_url}:{candidate_label}",
            candidate_label,
            "style_url_plus_candidate_label",
            True,
        )
    if placemark_name:
        return _Grouping(
            f"placemark:{placemark_name}",
            placemark_name,
            "placemark_name",
            _is_weak_generated_label(placemark_name),
        )
    if candidate_label:
        return _Grouping(
            f"candidate:{candidate_label}",
            candidate_label,
            "candidate_label",
            _is_weak_generated_label(candidate_label),
        )
    return _fallback_grouping("line_corridor", index, source_input)


def _point_grouping(row: Any) -> _Grouping:
    style_url = _string_value(row, "style_url")
    style_color = _string_value(row, "style_color")
    if style_url or style_color:
        label = " / ".join(value for value in (style_url, style_color) if value)
        return _Grouping(f"point-style:{style_url}:{style_color}", label, "style_color", False)

    folder_group = _string_value(row, "folder_group")
    if folder_group:
        return _Grouping(f"point-folder:{folder_group}", folder_group, "folder_group", False)

    candidate_label = _string_value(row, "candidate_label")
    if candidate_label and not _is_weak_generated_label(candidate_label):
        return _Grouping(f"point-candidate:{candidate_label}", candidate_label, "candidate_label", False)

    return _Grouping("point-fallback:all-points", "All points", "fallback_all_points", True)


def _polygon_grouping(row: Any, index: Any, source_input: str) -> _Grouping:
    for column, method in (
        ("folder_group", "folder_group"),
        ("placemark_name", "placemark_name"),
        ("candidate_label", "candidate_label"),
    ):
        value = _string_value(row, column)
        if value:
            return _Grouping(f"polygon-{method}:{value}", value, method, _is_weak_generated_label(value))
    return _fallback_grouping("polygon_area", index, source_input)


def _fallback_grouping(role: str, index: Any, source_input: str) -> _Grouping:
    key = f"fallback:{role}:{source_input}:{index}"
    return _Grouping(key, f"{role.replace('_', ' ').title()} {index}", "fallback_generated_group", True)


def _comparison_unit_type(records: list[dict[str, Any]], raw_roles: set[str]) -> str:
    role = str(records[0]["role"])
    if role == "line_corridor":
        return "alternative"
    if role == "point_site":
        return "point_group"
    if role == "polygon_area":
        if raw_roles.intersection({"line_corridor", "point_site"}) and not _records_are_proposition_polygons(records):
            return "boundary_context"
        return "polygon_area"
    return "mixed_geometry_unit"


def _records_are_proposition_polygons(records: list[dict[str, Any]]) -> bool:
    for record in records:
        role = str(record["summary"].get("role", "")).lower()
        if any(token in role for token in ("alternative", "alignment", "route", "proposed", "proposition")):
            return True
    return False


def _combined_geometry(geometries: list[BaseGeometry], role: str) -> BaseGeometry:
    if role == "line_corridor":
        return _merge_lines(geometries)
    if role == "point_site":
        return _merge_points(geometries)
    if role == "polygon_area":
        return unary_union([geometry for geometry in geometries if geometry is not None and not geometry.is_empty])
    return unary_union([geometry for geometry in geometries if geometry is not None and not geometry.is_empty])


def _merge_lines(geometries: list[BaseGeometry]) -> BaseGeometry:
    lines: list[BaseGeometry] = []
    for geometry in geometries:
        if geometry.geom_type == "LineString":
            lines.append(geometry)
        elif geometry.geom_type == "MultiLineString":
            lines.extend(list(geometry.geoms))
    if not lines:
        return MultiLineString([])
    return linemerge(MultiLineString(lines)) if len(lines) > 1 else lines[0]


def _merge_points(geometries: list[BaseGeometry]) -> BaseGeometry:
    points: list[BaseGeometry] = []
    for geometry in geometries:
        if geometry.geom_type == "Point":
            points.append(geometry)
        elif geometry.geom_type == "MultiPoint":
            points.extend(list(geometry.geoms))
    if not points:
        return MultiPoint([])
    return points[0] if len(points) == 1 else MultiPoint(points)


def _record_values(records: list[dict[str, Any]], column: str) -> list[str]:
    values: list[str] = []
    for record in records:
        if column == "source_input":
            value = str(record["summary"].get("input_path", ""))
        else:
            value = _string_value(record["row"], column)
            if column == "source_feature_id" and not value:
                value = f"{record['summary'].get('input_path', '')}:feature-{record['index']}"
        if value and value not in values:
            values.append(value)
    return values


def _single_or_multiple(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return "multiple"


def _unit_name(label: str, role: str, counter: int) -> str:
    if label:
        return label
    return f"{role.replace('_', ' ').title()} {counter}"


def _geometry_role_for_geometry(geometry: BaseGeometry) -> str:
    geom_type = geometry.geom_type
    if "Point" in geom_type:
        return "point_site"
    if "LineString" in geom_type:
        return "line_corridor"
    if "Polygon" in geom_type:
        return "polygon_area"
    return "mixed"


def _is_explicit_alternative_name(value: str) -> bool:
    normalized = value.lower()
    return any(token in normalized for token in ("alternative", "alt", "option", "route", "alignment", "corridor"))


def _is_weak_generated_label(value: str) -> bool:
    normalized = value.strip().lower()
    return bool(re.fullmatch(r"#?style\d+", normalized) or re.fullmatch(r"placemark\s+\d+", normalized))


def _expected_comparison_unit_count(assumptions: dict[str, Any]) -> tuple[int | None, dict[str, Any] | None]:
    value = assumptions.get("expected_comparison_unit_count")
    if value is None:
        return None, None
    try:
        expected_count = int(value)
    except (TypeError, ValueError):
        return None, _issue(
            "warning",
            "invalid_expected_comparison_unit_count",
            "Project assumptions.expected_comparison_unit_count must be an integer when provided.",
            "config/project.json",
        )
    if expected_count < 0:
        return None, _issue(
            "warning",
            "invalid_expected_comparison_unit_count",
            "Project assumptions.expected_comparison_unit_count must be non-negative when provided.",
            "config/project.json",
        )
    return expected_count, None


def _expected_count_status(expected_count: int | None, actual_count: int) -> str:
    if expected_count is None:
        return "not_configured"
    return "matched" if expected_count == actual_count else "mismatch"


def _raw_project_feature_count(project_layers: list[dict[str, Any]]) -> int:
    return sum(len(layer["gdf"]) for layer in project_layers)


def _string_value(row: Any, column: str) -> str:
    if column not in row.index:
        return ""
    value = row[column]
    if value is None:
        return ""
    text = str(value).strip()
    return "" if not text or text.lower() == "nan" else text


def _issue(severity: str, code: str, message: str, location: str | None) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "location": location,
        "source_id": None,
    }


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
