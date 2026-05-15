"""Vector-only static map/figure generation."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from .project_context import ProjectContextError, generate_project_context, load_project_context


MAP_MANIFEST_PATH = Path("maps/map_manifest.json")
FIGURES_DIR = Path("maps/figures")
CONSTRAINT_RESULTS_PATH = Path("constraints/constraint_results.json")
SPATIAL_RELATIONSHIPS_PATH = Path("intermediate/spatial_relationships.json")
SUPPORTED_FIGURE_REVIEW_STATUSES = {
    "draft",
    "needs_review",
    "accepted",
    "edited",
    "rejected",
    "needs_verification",
    "unable_to_verify",
}
REQUIRED_FIGURE_FIELDS = {
    "figure_id",
    "type",
    "title",
    "image_path",
    "file_format",
    "shown_layers",
    "source_refs",
    "provenance",
    "uncertainty_flags",
    "review_status",
    "validation_issues",
}
PROJECT_COLORS = ["#2F80ED", "#F2994A", "#9B51E0", "#27AE60", "#EB5757", "#56CCF2", "#F2C94C"]
SOURCE_COLOR = "#6BAA75"


class MapGenerationError(RuntimeError):
    """Raised when map generation or map manifest loading cannot complete."""


def generate_maps(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    try:
        context = _load_or_generate_context(project_dir)
    except ProjectContextError as exc:
        raise MapGenerationError(str(exc)) from exc

    project_layers = _load_project_layers(context)
    analysis_crs = _analysis_crs(project_layers)
    constraints, validation_issues = _load_optional_constraint_results(project_dir)
    spatial: dict[str, Any] | None = None
    source_artifact = constraints
    source_artifact_name = "constraint_results"
    if source_artifact is None:
        spatial, spatial_issues = _load_optional_spatial_relationships(project_dir)
        validation_issues.extend(spatial_issues)
        source_artifact = spatial
        source_artifact_name = "spatial_relationships"
    figures_dir = project_dir / FIGURES_DIR
    figures_dir.mkdir(parents=True, exist_ok=True)

    figures: list[dict[str, Any]] = []
    overview_path = figures_dir / "project-overview.png"
    try:
        _render_map(
            output_path=overview_path,
            title=f"{context['project_name']} - Project Overview",
            project_layers=project_layers,
            analysis_crs=analysis_crs,
        )
    except Exception as exc:
        raise MapGenerationError(f"Unable to render project overview map: {exc}") from exc
    figures.append(
        _figure_record(
            figure_id="project-overview",
            figure_type="project_overview",
            title="Project Overview",
            image_path=overview_path,
            shown_layers=_project_shown_layers(project_layers),
            source_refs=[],
            provenance={
                "artifact": "project_context",
                "artifact_path": context.get("context_path"),
                "method": "geopandas_matplotlib_vector_static_map",
                "analysis_crs": analysis_crs,
            },
            uncertainty_flags=["draft_pre_review", "vector_only_no_basemap"],
            validation_issues=[],
        )
    )

    if source_artifact is not None:
        for source in _dict_list(source_artifact.get("sources", [])):
            if source.get("status") != "analyzed":
                continue
            source_figure = _source_context_figure(
                project_layers=project_layers,
                figures_dir=figures_dir,
                analysis_crs=analysis_crs,
                source_artifact=source_artifact,
                source_artifact_name=source_artifact_name,
                source=source,
            )
            if source_figure["figure"] is not None:
                figures.append(source_figure["figure"])
            validation_issues.extend(source_figure["validation_issues"])

    output_path = project_dir / MAP_MANIFEST_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "project_id": context["project_id"],
        "project_name": context["project_name"],
        "project_dir": str(project_dir),
        "created_at": _utc_now(),
        "map_generation_policy": "vector_only_no_basemap",
        "upstream_artifacts": {
            "project_context_path": context.get("context_path"),
            "constraint_results_path": constraints.get("output_path") if constraints else None,
            "spatial_relationships_path": spatial.get("output_path") if spatial else None,
        },
        "figure_count": len(figures),
        "figures": figures,
        "validation_issues": validation_issues,
        "output_path": str(output_path),
    }
    _validate_map_manifest(result, str(output_path))
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def load_map_manifest(project_dir: Path) -> dict[str, Any]:
    manifest_path = project_dir.resolve() / MAP_MANIFEST_PATH
    if not manifest_path.exists():
        raise MapGenerationError(f"Missing map manifest artifact: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MapGenerationError(f"Invalid map manifest JSON: {manifest_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise MapGenerationError(f"Map manifest artifact must be a JSON object: {manifest_path}")
    _validate_map_manifest(data, str(manifest_path))
    return data


def _load_or_generate_context(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_context(project_dir)
    except ProjectContextError:
        return generate_project_context(project_dir)


def _load_project_layers(context: dict[str, Any]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for item in _dict_list(context.get("detected_inputs", [])):
        geojson_value = item.get("normalized_geojson")
        if not geojson_value:
            raise MapGenerationError("Project input is missing normalized GeoJSON needed for map generation.")
        geojson_path = Path(str(geojson_value))
        try:
            gdf = gpd.read_file(geojson_path)
        except Exception as exc:  # pragma: no cover - driver-specific exception types vary.
            raise MapGenerationError(f"Unable to read project geometry for mapping: {geojson_path}: {exc}") from exc
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        gdf = gdf[~gdf.geometry.isna()]
        gdf = gdf[~gdf.geometry.is_empty]
        if not gdf.empty:
            layers.append({"summary": item, "gdf": gdf})
    if not layers:
        raise MapGenerationError("No non-empty project geometries are available for map generation.")
    return layers


def _load_optional_spatial_relationships(project_dir: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    spatial_path = project_dir / SPATIAL_RELATIONSHIPS_PATH
    if not spatial_path.exists():
        return None, []
    try:
        data = json.loads(spatial_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                code="invalid_spatial_relationships_json",
                message=f"Spatial relationships JSON could not be parsed for map generation: {exc}",
                location=str(spatial_path),
            )
        ]
    if not isinstance(data, dict) or not isinstance(data.get("sources", []), list):
        return None, [
            _issue(
                code="invalid_spatial_relationships_artifact",
                message="Spatial relationships artifact must be an object with a sources list for source-context maps.",
                location=str(spatial_path),
            )
        ]
    return data, []


def _load_optional_constraint_results(project_dir: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    constraint_path = project_dir / CONSTRAINT_RESULTS_PATH
    if not constraint_path.exists():
        return None, []
    try:
        data = json.loads(constraint_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                code="invalid_constraint_results_json",
                message=f"Constraint results JSON could not be parsed for map generation: {exc}",
                location=str(constraint_path),
            )
        ]
    if not isinstance(data, dict) or not isinstance(data.get("sources", []), list):
        return None, [
            _issue(
                code="invalid_constraint_results_artifact",
                message="Constraint results artifact must be an object with a sources list for source-context maps.",
                location=str(constraint_path),
            )
        ]
    return data, []


def _source_context_figure(
    *,
    project_layers: list[dict[str, Any]],
    figures_dir: Path,
    analysis_crs: str,
    source_artifact: dict[str, Any],
    source_artifact_name: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    source_id = str(source.get("source_id", "unknown_source"))
    source_name = str(source.get("source_name") or source_id)
    clipped_value = source.get("clipped_geojson")
    validation_issues: list[dict[str, Any]] = []
    if not clipped_value:
        validation_issues.append(
            _issue(
                code="missing_clipped_source_layer",
                message=f"Analyzed source '{source_id}' does not reference a clipped layer for mapping.",
                location=str(source_artifact.get("output_path", "")),
                source_id=source_id,
            )
        )
        return {"figure": None, "validation_issues": validation_issues}

    clipped_path = Path(str(clipped_value))
    if not clipped_path.exists():
        validation_issues.append(
            _issue(
                code="missing_clipped_source_layer",
                message=f"Clipped layer for source '{source_id}' is missing: {clipped_path}",
                location=str(clipped_path),
                source_id=source_id,
            )
        )
        return {"figure": None, "validation_issues": validation_issues}

    try:
        source_gdf = gpd.read_file(clipped_path)
    except Exception as exc:  # pragma: no cover - driver-specific exception types vary.
        validation_issues.append(
            _issue(
                code="unreadable_clipped_source_layer",
                message=f"Unable to read clipped layer for source '{source_id}': {clipped_path}: {exc}",
                location=str(clipped_path),
                source_id=source_id,
            )
        )
        return {"figure": None, "validation_issues": validation_issues}

    if source_gdf.crs is None:
        validation_issues.append(
            _issue(
                code="missing_clipped_source_crs",
                message=f"Clipped source layer '{source_id}' has no CRS; assuming EPSG:4326 for draft map rendering.",
                location=str(clipped_path),
                source_id=source_id,
            )
        )
        source_gdf = source_gdf.set_crs("EPSG:4326", allow_override=True)
    source_gdf = source_gdf[~source_gdf.geometry.isna()]
    source_gdf = source_gdf[~source_gdf.geometry.is_empty]

    figure_id = f"source-context-{_slug(source_id)}"
    image_path = figures_dir / f"{figure_id}.png"
    try:
        _render_map(
            output_path=image_path,
            title=f"{source_name} - Source Context",
            project_layers=project_layers,
            analysis_crs=analysis_crs,
            source_layer={"source": source, "gdf": source_gdf, "path": clipped_path},
        )
    except Exception as exc:
        validation_issues.append(
            _issue(
                code="source_map_render_error",
                message=f"Unable to render source-context figure for source '{source_id}': {exc}",
                location=str(clipped_path),
                source_id=source_id,
            )
        )
        return {"figure": None, "validation_issues": validation_issues}
    uncertainty_flags = ["draft_pre_review", "vector_only_no_basemap"]
    if source_gdf.empty:
        uncertainty_flags.append("empty_clipped_source_layer")
    return {
        "figure": _figure_record(
            figure_id=figure_id,
            figure_type="source_context",
            title=f"Source Context: {source_name}",
            image_path=image_path,
            shown_layers=[
                *_project_shown_layers(project_layers),
                {
                    "layer_type": "source_layer",
                    "source_id": source_id,
                    "label": source_name,
                    "path": str(clipped_path),
                    "feature_count": int(len(source_gdf)),
                    "geometry_type_counts": _geometry_type_counts(source_gdf),
                },
            ],
            source_refs=[source_id],
            provenance={
                "artifact": source_artifact_name,
                "artifact_path": source_artifact.get("output_path"),
                "clipped_geojson": str(clipped_path),
                "method": "geopandas_matplotlib_vector_static_map",
                "analysis_crs": analysis_crs,
            },
            uncertainty_flags=uncertainty_flags,
            validation_issues=validation_issues,
        ),
        "validation_issues": validation_issues,
    }


def _render_map(
    *,
    output_path: Path,
    title: str,
    project_layers: list[dict[str, Any]],
    analysis_crs: str,
    source_layer: dict[str, Any] | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 7.5), dpi=150)
    try:
        handles: list[Any] = []
        plotted_layers: list[gpd.GeoDataFrame] = []

        for index, layer in enumerate(project_layers):
            gdf = layer["gdf"].to_crs(analysis_crs)
            color = PROJECT_COLORS[index % len(PROJECT_COLORS)]
            label = _project_layer_label(layer)
            handles.extend(_plot_gdf(ax, gdf, color=color, label=label, is_project=True))
            plotted_layers.append(gdf)

        if source_layer is not None:
            source_gdf = source_layer["gdf"].to_crs(analysis_crs)
            source_label = str(source_layer["source"].get("source_name") or source_layer["source"].get("source_id") or "Source layer")
            handles.extend(_plot_gdf(ax, source_gdf, color=SOURCE_COLOR, label=source_label, is_project=False))
            if not source_gdf.empty:
                plotted_layers.append(source_gdf)

        _set_extent(ax, plotted_layers)
        ax.set_title(title, fontsize=14, pad=12)
        ax.set_axis_off()
        if handles:
            ax.legend(handles=handles, loc="upper left", frameon=True, framealpha=0.92, fontsize=8)
        ax.text(
            0.99,
            0.01,
            "Draft / Pre-Review - Vector Only",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=8,
            color="#4A4A4A",
            bbox={"facecolor": "white", "edgecolor": "#BDBDBD", "alpha": 0.9, "pad": 4},
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    finally:
        plt.close(fig)


def _plot_gdf(
    ax: Any,
    gdf: gpd.GeoDataFrame,
    *,
    color: str,
    label: str,
    is_project: bool,
) -> list[Any]:
    if gdf.empty:
        return []
    handles: list[Any] = []
    polygon_gdf = gdf[gdf.geometry.geom_type.str.contains("Polygon", na=False)]
    line_gdf = gdf[gdf.geometry.geom_type.str.contains("LineString", na=False)]
    point_gdf = gdf[gdf.geometry.geom_type.str.contains("Point", na=False)]

    if not polygon_gdf.empty:
        if is_project:
            polygon_gdf.plot(ax=ax, facecolor="none", edgecolor=color, linewidth=2.0)
            handles.append(Patch(facecolor="none", edgecolor=color, label=label))
        else:
            polygon_gdf.plot(ax=ax, facecolor=color, edgecolor=color, linewidth=1.0, alpha=0.28)
            handles.append(Patch(facecolor=color, edgecolor=color, alpha=0.28, label=label))
    if not line_gdf.empty:
        line_width = 2.8 if is_project else 1.8
        line_gdf.plot(ax=ax, color=color, linewidth=line_width, alpha=0.95 if is_project else 0.65)
        handles.append(Line2D([0], [0], color=color, lw=line_width, label=label))
    if not point_gdf.empty:
        marker_size = 42 if is_project else 26
        point_gdf.plot(ax=ax, color=color, markersize=marker_size, alpha=0.95 if is_project else 0.65)
        handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markersize=7, label=label))
    return handles[:1]


def _set_extent(ax: Any, layers: list[gpd.GeoDataFrame]) -> None:
    non_empty = [layer for layer in layers if not layer.empty]
    if not non_empty:
        return
    bounds = [layer.total_bounds for layer in non_empty]
    west = min(float(bound[0]) for bound in bounds)
    south = min(float(bound[1]) for bound in bounds)
    east = max(float(bound[2]) for bound in bounds)
    north = max(float(bound[3]) for bound in bounds)
    width = east - west
    height = north - south
    pad_x = width * 0.08 if width > 0 else 250
    pad_y = height * 0.08 if height > 0 else 250
    ax.set_xlim(west - pad_x, east + pad_x)
    ax.set_ylim(south - pad_y, north + pad_y)
    ax.set_aspect("equal", adjustable="box")


def _figure_record(
    *,
    figure_id: str,
    figure_type: str,
    title: str,
    image_path: Path,
    shown_layers: list[dict[str, Any]],
    source_refs: list[str],
    provenance: dict[str, Any],
    uncertainty_flags: list[str],
    validation_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "figure_id": figure_id,
        "type": figure_type,
        "title": title,
        "image_path": str(image_path),
        "file_format": "png",
        "shown_layers": shown_layers,
        "source_refs": source_refs,
        "provenance": provenance,
        "uncertainty_flags": uncertainty_flags,
        "review_status": "draft",
        "validation_issues": validation_issues,
    }


def _project_shown_layers(project_layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "layer_type": "project_input",
            "label": _project_layer_label(layer),
            "input_path": layer["summary"].get("input_path"),
            "role": layer["summary"].get("role"),
            "feature_count": int(len(layer["gdf"])),
            "geometry_type_counts": _geometry_type_counts(layer["gdf"]),
        }
        for layer in project_layers
    ]


def _project_layer_label(layer: dict[str, Any]) -> str:
    summary = layer["summary"]
    return str(summary.get("role") or summary.get("input_path") or "Project input")


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


def _geometry_type_counts(gdf: gpd.GeoDataFrame) -> dict[str, int]:
    if gdf.empty:
        return {}
    counts = gdf.geometry.geom_type.value_counts().to_dict()
    return {str(key): int(value) for key, value in sorted(counts.items())}


def _validate_map_manifest(data: dict[str, Any], location: str) -> None:
    figures = data.get("figures")
    if not isinstance(figures, list):
        raise MapGenerationError(f"Map manifest requires a list field named 'figures': {location}")
    figure_count = data.get("figure_count")
    if figure_count is not None and figure_count != len(figures):
        raise MapGenerationError(f"Map manifest figure_count does not match figures: {location}")
    if not isinstance(data.get("validation_issues", []), list):
        raise MapGenerationError(f"Map manifest validation_issues must be a list: {location}")
    seen_ids: set[str] = set()
    for figure in figures:
        if not isinstance(figure, dict):
            raise MapGenerationError(f"Each map figure must be an object: {location}")
        missing = sorted(REQUIRED_FIGURE_FIELDS - set(figure))
        if missing:
            raise MapGenerationError(f"Map figure is missing required fields {missing}: {location}")
        figure_id = figure["figure_id"]
        if not isinstance(figure_id, str) or not figure_id.strip():
            raise MapGenerationError(f"Map figure requires a non-empty figure_id: {location}")
        if figure_id in seen_ids:
            raise MapGenerationError(f"Duplicate map figure id '{figure_id}': {location}")
        seen_ids.add(figure_id)
        image_path = figure["image_path"]
        if not isinstance(image_path, str) or not image_path.strip():
            raise MapGenerationError(f"Map figure '{figure_id}' requires a non-empty image_path: {location}")
        if not Path(image_path).exists():
            raise MapGenerationError(f"Map figure '{figure_id}' image_path does not exist: {image_path}")
        if figure["file_format"] != "png":
            raise MapGenerationError(f"Map figure '{figure_id}' file_format must be png: {location}")
        if figure["review_status"] not in SUPPORTED_FIGURE_REVIEW_STATUSES:
            raise MapGenerationError(f"Map figure '{figure_id}' has unsupported review_status: {location}")
        if not isinstance(figure["provenance"], dict):
            raise MapGenerationError(f"Map figure '{figure_id}' provenance must be an object: {location}")
        for list_field in ("shown_layers", "source_refs", "uncertainty_flags", "validation_issues"):
            if not isinstance(figure[list_field], list):
                raise MapGenerationError(f"Map figure '{figure_id}' field '{list_field}' must be a list: {location}")


def _issue(*, code: str, message: str, location: str, source_id: str | None = None) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "severity": "warning",
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


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
