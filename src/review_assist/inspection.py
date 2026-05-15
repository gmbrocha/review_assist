"""Project-level inspection pipeline for Phase 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .kml import IngestionError, ingest_kml_input
from .projects import ProjectManifestError, load_project_manifest
from .summary import input_summary


class ProjectInspectionError(RuntimeError):
    """Raised when project inspection cannot complete."""


def write_geojson(gdf, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_json_safe_geodataframe(gdf).to_json(drop_id=True), encoding="utf-8")


def _json_safe_geodataframe(gdf):
    result = gdf.copy()
    geometry_name = getattr(getattr(result, "geometry", None), "name", "geometry")
    for column in result.columns:
        if column == geometry_name:
            continue
        series = result[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            result[column] = series.astype("string").fillna("")
        elif series.dtype == "object":
            result[column] = series.map(_json_safe_value)
    return result


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and callable(value.isoformat):
        try:
            return value.isoformat()
        except TypeError:
            return str(value)
    return value


def inspect_project(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        manifest = load_project_manifest(project_dir)
    except ProjectManifestError as exc:
        raise ProjectInspectionError(str(exc)) from exc

    intermediate_dir = project_dir / "intermediate"
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    input_summaries: list[dict[str, Any]] = []
    source_input_summaries: list[dict[str, Any]] = []
    for project_input in manifest.inputs:
        input_path = (project_dir / project_input.path).resolve()
        if project_input.is_source_layer:
            source_input_summaries.append(_source_input_summary(project_input, input_path))
            continue
        try:
            ingested = ingest_kml_input(input_path)
        except IngestionError as exc:
            raise ProjectInspectionError(str(exc)) from exc

        geojson_path = intermediate_dir / f"{input_path.stem}.geojson"
        write_geojson(ingested.geo_data_frame, geojson_path)
        input_summaries.append(input_summary(project_input, ingested, geojson_path))

    summary_path = intermediate_dir / "geometry_summary.json"
    summary = {
        "project_id": manifest.project_id,
        "project_name": manifest.name,
        "project_type": manifest.project_type,
        "project_dir": str(project_dir),
        "summary_path": str(summary_path),
        "assumptions": manifest.assumptions,
        "special_reviewer_instructions": manifest.special_reviewer_instructions,
        "inputs": input_summaries,
        "source_inputs": source_input_summaries,
    }

    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _source_input_summary(project_input, input_path: Path) -> dict[str, Any]:
    return {
        "input_path": project_input.path,
        "resolved_input_path": str(input_path),
        "role": project_input.role,
        "description": project_input.description,
        "source_id": project_input.source_id,
        "source_category": project_input.source_category,
        "exists": input_path.exists(),
        "validation_issues": [] if input_path.exists() else [
            {
                "severity": "warning",
                "code": "missing_project_input_source",
                "message": f"Project input source layer does not exist: {project_input.path}",
                "location": str(input_path),
            }
        ],
    }
