"""Review-only figure regeneration from style recipes and sparse overrides."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import geopandas as gpd

from .deliverable_figure_basemaps import load_basemap
from .deliverable_figure_rendering import render_map
from .figure_style_model import (
    FIGURE_RENDER_JOBS_PATH,
    FIGURE_VERSION_OUTPUT_DIR,
    FIGURE_VERSIONS_PATH,
    active_style_override,
    ensure_figure_style_model,
    figure_recipe_for,
    load_figure_style_artifacts,
    make_render_job,
    validate_figure_versions_artifact,
    validate_render_jobs_artifact,
)


COMPARISON_UNITS_GEOJSON_PATH = Path("intermediate/comparison_units.geojson")
PROJECT_AREA_PATH = Path("context/project_area.json")


class FigureRegenerationError(RuntimeError):
    """Raised when a review-only figure regeneration job cannot complete safely."""


def regenerate_figure_version(
    project_dir: Path,
    figure_id: str,
    *,
    output_format: str = "png",
    actor: str = "local_reviewer",
    renderer: Callable[..., dict[str, Any]] = render_map,
) -> dict[str, Any]:
    """Render a new review-only figure version without changing review/export state."""

    if output_format != "png":
        raise FigureRegenerationError("Sprint 6.5 figure regeneration supports PNG output only.")

    project_dir = project_dir.resolve()
    ensure_figure_style_model(project_dir)
    artifacts = load_figure_style_artifacts(project_dir)
    recipe = figure_recipe_for(artifacts["recipes"], figure_id)
    overrides_artifact = artifacts["style_overrides"]
    active_override = active_style_override(overrides_artifact, figure_id)
    style_plan = _style_plan(recipe, active_override)
    versions_artifact = dict(artifacts["versions"])
    render_jobs_artifact = dict(artifacts["render_jobs"])
    version_number = _next_version_number(versions_artifact, figure_id)
    output_relative_path = FIGURE_VERSION_OUTPUT_DIR / figure_id / f"v{version_number}.png"
    output_path = project_dir / output_relative_path
    now = _utc_now()

    job = make_render_job(
        project_id=str(recipe.get("project_id") or artifacts["recipes"].get("project_id") or ""),
        figure_id=figure_id,
        analysis_snapshot_id=str(recipe.get("analysis_snapshot_id") or ""),
        figure_recipe_id=str(recipe.get("recipe_id") or ""),
        style_override_id=str((active_override or {}).get("override_id") or ""),
        output_format=output_format,
        status="running",
        created_at=now,
    )
    job["started_at"] = now
    job["created_by"] = actor
    _append_or_replace_job(project_dir, render_jobs_artifact, job)

    try:
        unit_gdf = _load_comparison_units(project_dir)
        analysis_crs = _analysis_crs(unit_gdf)
        unit_gdf = _clean_gdf(unit_gdf, analysis_crs)
        source_layers = _source_layers_from_recipe(project_dir, recipe, style_plan["source_layers"], analysis_crs)
        render_layout = recipe.get("render_layout") if isinstance(recipe.get("render_layout"), dict) else {}
        if "expanded_bounds" not in render_layout:
            render_layout = None
        basemap = _load_regeneration_basemap(project_dir, analysis_crs, render_layout, style_plan["basemap_requested"])
        rendered_layout = renderer(
            output_path=output_path,
            title=str(recipe.get("title") or figure_id),
            unit_gdf=unit_gdf,
            analysis_crs=analysis_crs,
            source_layers=source_layers,
            basemap=basemap,
            method_note=str(recipe.get("method_note") or "Review-only regenerated figure."),
            source_note=str(recipe.get("source_note") or ""),
            focus_bounds=_focus_bounds(recipe, unit_gdf),
            render_layout=render_layout,
            comparison_layer_style=style_plan["comparison_layer_style"],
        )
    except Exception as exc:
        if output_path.exists():
            output_path.unlink()
        job["status"] = "failed"
        job["completed_at"] = _utc_now()
        job["errors"] = [{"code": "figure_regeneration_failed", "message": _safe_error(exc)}]
        _append_or_replace_job(project_dir, render_jobs_artifact, job)
        raise FigureRegenerationError(f"Figure regeneration failed for '{figure_id}': {_safe_error(exc)}") from exc

    completed_at = _utc_now()
    job["status"] = "succeeded"
    job["completed_at"] = completed_at
    job["output_artifact_path"] = output_relative_path.as_posix()
    _append_or_replace_job(project_dir, render_jobs_artifact, job)

    version = {
        "version_id": f"{figure_id}:v{version_number}",
        "figure_id": figure_id,
        "version_number": version_number,
        "created_at": completed_at,
        "created_by": actor,
        "generated_by": actor,
        "analysis_snapshot_id": str(recipe.get("analysis_snapshot_id") or ""),
        "figure_recipe_id": str(recipe.get("recipe_id") or ""),
        "style_override_id": str((active_override or {}).get("override_id") or ""),
        "render_job_id": job["render_job_id"],
        "output_artifact_path": output_relative_path.as_posix(),
        "file_format": "png",
        "approval_state": "regenerated",
        "is_stub": False,
        "source_image_status": "regenerated_review_only",
        "review_only": True,
        "export_active": False,
        "rendered_layers": style_plan["rendered_layers"],
        "hidden_layers": style_plan["hidden_layers"],
        "render_layout": rendered_layout,
    }
    _append_version(project_dir, versions_artifact, version)
    return {
        "project_id": str(recipe.get("project_id") or artifacts["recipes"].get("project_id") or ""),
        "figure_id": figure_id,
        "render_job": job,
        "version": version,
        "output_artifact_path": output_relative_path.as_posix(),
        "review_only": True,
        "export_artifacts_mutated": False,
        "review_queue_mutated": False,
        "analysis_artifacts_mutated": False,
        "source_artifacts_mutated": False,
    }


def _style_plan(recipe: dict[str, Any], active_override: dict[str, Any] | None) -> dict[str, Any]:
    overrides = {
        str(layer.get("layer_id") or ""): layer
        for layer in _dict_list((active_override or {}).get("overrides", []))
    }
    rendered_layers: list[dict[str, Any]] = []
    hidden_layers: list[dict[str, Any]] = []
    source_layers: list[dict[str, Any]] = []
    comparison_layer_style: dict[str, Any] | None = None
    basemap_requested = False
    for layer in _dict_list(recipe.get("layers", [])):
        layer_id = str(layer.get("layer_id") or "")
        current = _current_layer_style(layer, overrides.get(layer_id, {}))
        record = {
            "layer_id": layer_id,
            "layer_type": str(layer.get("layer_type") or ""),
            "source_id": str(layer.get("source_id") or ""),
            "display_name": current["display_name"],
            "z_index": current["z_index"],
            "style": current["style"],
        }
        if not current["visible"]:
            hidden_layers.append(record)
            continue
        rendered_layers.append(record)
        if record["layer_type"] == "comparison_units":
            comparison_layer_style = {"label": current["display_name"], "z_index": current["z_index"], **current["style"]}
        elif record["layer_type"] == "source_layer":
            source_layers.append({"recipe_layer": layer, "style": {"label": current["display_name"], "z_index": current["z_index"], **current["style"]}})
        elif record["layer_type"] == "basemap":
            basemap_requested = True
    rendered_layers.sort(key=lambda item: (int(item.get("z_index", 0)), str(item.get("layer_id") or "")))
    source_layers.sort(key=lambda item: (int(item["style"].get("z_index", 0)), str(item["recipe_layer"].get("layer_id") or "")))
    return {
        "rendered_layers": rendered_layers,
        "hidden_layers": hidden_layers,
        "source_layers": source_layers,
        "comparison_layer_style": comparison_layer_style,
        "basemap_requested": basemap_requested,
    }


def _current_layer_style(layer: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    default_style = layer.get("default_style") if isinstance(layer.get("default_style"), dict) else {}
    style = {
        "fill_color": override.get("fill_color", default_style.get("fill_color")),
        "fill_opacity": override.get("fill_opacity", default_style.get("fill_opacity")),
        "stroke_color": override.get("stroke_color", default_style.get("stroke_color")),
        "stroke_width": override.get("stroke_width", default_style.get("stroke_width")),
        "point_size": override.get("point_size", default_style.get("point_size")),
    }
    return {
        "visible": _coerce_bool(override.get("visible", bool(layer.get("default_visible", True)))),
        "z_index": int(override.get("z_index", int(layer.get("default_z_index", 0)))),
        "display_name": str(override.get("display_name", str(layer.get("default_display_name") or layer.get("layer_id") or ""))),
        "style": {key: value for key, value in style.items() if value not in (None, "")},
    }


def _source_layers_from_recipe(
    project_dir: Path,
    recipe: dict[str, Any],
    source_layer_plans: list[dict[str, Any]],
    analysis_crs: str,
) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for index, plan in enumerate(source_layer_plans):
        layer = plan["recipe_layer"]
        path = _resolve_project_path(project_dir, layer.get("path"))
        if path is None or not path.exists():
            continue
        gdf = gpd.read_file(path)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        gdf = gdf[~gdf.geometry.isna()]
        gdf = gdf[~gdf.geometry.is_empty]
        if not gdf.empty:
            gdf = gdf.to_crs(analysis_crs)
        layers.append(
            {
                "source_id": str(layer.get("source_id") or ""),
                "source_name": str(layer.get("default_display_name") or layer.get("source_id") or f"Source layer {index + 1}"),
                "source_category": "",
                "path": str(path),
                "gdf": gdf,
                "style_override": plan["style"],
            }
        )
    return layers


def _load_regeneration_basemap(project_dir: Path, analysis_crs: str, render_layout: dict[str, Any] | None, requested: bool) -> dict[str, Any] | None:
    if not requested:
        return None
    project_area = _read_json(project_dir / PROJECT_AREA_PATH)
    if not project_area:
        return None
    required_bounds = render_layout.get("expanded_bounds") if isinstance(render_layout, dict) else None
    try:
        return load_basemap(project_area, analysis_crs, required_bounds=required_bounds, required_bounds_crs=analysis_crs)
    except Exception:
        return None


def _load_comparison_units(project_dir: Path) -> gpd.GeoDataFrame:
    path = project_dir / COMPARISON_UNITS_GEOJSON_PATH
    if not path.exists():
        raise FigureRegenerationError(f"Missing comparison units artifact: {COMPARISON_UNITS_GEOJSON_PATH}")
    gdf = gpd.read_file(path)
    if gdf.empty:
        raise FigureRegenerationError("Comparison units artifact contains no features.")
    return gdf


def _analysis_crs(gdf: gpd.GeoDataFrame) -> str:
    if gdf.crs is not None:
        try:
            estimated = gdf.estimate_utm_crs()
        except RuntimeError:
            estimated = None
        if estimated is not None:
            return estimated.to_string()
        return gdf.crs.to_string()
    return "EPSG:3857"


def _clean_gdf(gdf: gpd.GeoDataFrame, analysis_crs: str) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    gdf = gdf[~gdf.geometry.isna()]
    gdf = gdf[~gdf.geometry.is_empty]
    return gdf.to_crs(analysis_crs)


def _focus_bounds(recipe: dict[str, Any], unit_gdf: gpd.GeoDataFrame) -> Any:
    layout = recipe.get("render_layout") if isinstance(recipe.get("render_layout"), dict) else {}
    if isinstance(layout.get("base_bounds"), list):
        return layout["base_bounds"]
    return unit_gdf.total_bounds


def _next_version_number(versions_artifact: dict[str, Any], figure_id: str) -> int:
    numbers = [
        int(version.get("version_number") or 0)
        for version in _dict_list(versions_artifact.get("versions", []))
        if str(version.get("figure_id") or "") == figure_id
    ]
    return max(numbers or [0]) + 1


def _append_version(project_dir: Path, versions_artifact: dict[str, Any], version: dict[str, Any]) -> None:
    versions = [dict(item) for item in _dict_list(versions_artifact.get("versions", []))]
    versions.append(version)
    versions_artifact["versions"] = versions
    versions_artifact["version_count"] = len(versions)
    versions_artifact["updated_at"] = _utc_now()
    validate_figure_versions_artifact(versions_artifact)
    _write_json(project_dir / FIGURE_VERSIONS_PATH, versions_artifact)


def _append_or_replace_job(project_dir: Path, render_jobs_artifact: dict[str, Any], job: dict[str, Any]) -> None:
    jobs = [
        dict(item)
        for item in _dict_list(render_jobs_artifact.get("render_jobs", []))
        if str(item.get("render_job_id") or "") != str(job.get("render_job_id") or "")
    ]
    jobs.append(dict(job))
    render_jobs_artifact["render_jobs"] = jobs
    render_jobs_artifact["render_job_count"] = len(jobs)
    render_jobs_artifact["updated_at"] = _utc_now()
    validate_render_jobs_artifact(render_jobs_artifact)
    _write_json(project_dir / FIGURE_RENDER_JOBS_PATH, render_jobs_artifact)


def _resolve_project_path(project_dir: Path, value: Any) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    return project_dir / path


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _safe_error(exc: Exception) -> str:
    return " ".join(str(exc).split())[:500]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
