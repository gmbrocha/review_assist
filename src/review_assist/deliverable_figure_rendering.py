"""Matplotlib rendering and layout helpers for deliverable figures."""

from __future__ import annotations

import hashlib
import re
import textwrap
from colorsys import rgb_to_hsv
from functools import lru_cache
from typing import Any

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyproj import CRS

from .extent_policy import FIGURE_RENDER_EXTENT, PRESENTATION_ONLY_COLLAR_EXTENT
from .maps import SOURCE_CATEGORY_COLORS

COMPARISON_UNIT_FALLBACK_COLORS = [
    "#004CFF",
    "#FF2A00",
    "#FFD400",
    "#8A00FF",
    "#00D5FF",
    "#FF00FF",
    "#FF007A",
    "#7B2CBF",
    "#FF7A00",
    "#0033AA",
]
COMPARISON_UNIT_LINE_WIDTH = 1.2
COMPARISON_UNIT_LINE_HALO_WIDTH = 0.0
COMPARISON_UNIT_LINE_HALO_ALPHA = 0.0
COMPARISON_UNIT_LINE_HALO_COLOR = "#FFFFFF"
ROUTE_COLOR_MIN_DISTANCE = 78.0
IMAGERY_RISK_HUE_MIN = 65.0
IMAGERY_RISK_HUE_MAX = 170.0
IMAGERY_RISK_LUMINANCE_MAX = 0.78
IMAGERY_SAFE_MIN_SATURATION = 0.72
IMAGERY_SAFE_MIN_VALUE = 0.78
THEMATIC_MIN_SATURATION = 0.66
THEMATIC_MIN_VALUE = 0.68
THEMATIC_MAX_LOW_SATURATION_LUMINANCE = 0.84
THEMATIC_PROHIBITED_GREEN_HUE_MIN = 85.0
THEMATIC_PROHIBITED_GREEN_HUE_MAX = 165.0
THEMATIC_EARTH_TONE_HUE_MIN = 25.0
THEMATIC_EARTH_TONE_HUE_MAX = 80.0
THEMATIC_FALLBACK_COLORS = [
    "#FF00FF",
    "#0057FF",
    "#FF2A00",
    "#8A00FF",
    "#00D5FF",
    "#FFD400",
    "#FF007A",
    "#7B2CBF",
    "#FF7A00",
]
MAX_LEGEND_LABEL_LENGTH = 26
LEGEND_COLLAR_PADDING_FRACTION = 0.045
LEGEND_COLLAR_MAX_FRACTION = 0.52
LEGEND_COLLAR_AXES_PADDING = 0.026
LEGEND_MEASUREMENT_SAFETY_FACTOR = 1.12
LEGEND_FONT_SIZE = 5.4
LEGEND_TITLE_FONT_SIZE = 5.5
LEGEND_BORDERPAD = 0.35
LEGEND_LABELSPACING = 0.25
LEGEND_HANDLE_LENGTH = 1.15
LEGEND_HANDLETEXTPAD = 0.45

SOURCE_LABEL_OVERRIDES = {
    "epa_envirofacts_echo": "EPA ECHO",
    "epa_frs_facilities_ms": "EPA FRS",
    "fema_nfhl_flood_hazard": "FEMA flood",
    "local_utility_infrastructure": "Utilities",
    "maris_brownfields": "Brownfields",
    "maris_community_facilities": "Community facilities",
    "maris_npdes_facilities": "NPDES",
    "maris_public_cultural_context": "Public cultural",
    "maris_solid_waste_landfills": "Landfills",
    "maris_superfund_sites": "Superfund",
    "maris_tri_facilities": "TRI",
    "maris_underground_storage_tanks": "USTs",
    "mdeq_303d_impaired_waters": "303(d)/TMDL",
    "mdot_transportation_context": "Roads/rail",
    "mdeq_public_water_supply_wells": "PWS wells",
    "mississippi_oil_gas_wells": "Oil/gas wells",
    "usda_nrcs_easements": "NRCS easements",
    "usda_nrcs_ssurgo_soils": "SSURGO soils",
    "usfws_critical_habitat": "Critical habitat",
    "usfws_national_wildlife_refuges": "Wildlife refuges",
    "usfws_nwi_wetlands": "NWI Wetlands",
    "usgs_nhd_flowlines": "NHD Flowlines",
    "usgs_nhd_hydrography": "NHD hydrography",
    "usgs_nhd_other_areas": "NHD Other Areas",
    "usgs_nhd_waterbodies": "NHD Waterbodies",
    "usgs_wbd_huc12_subwatersheds": "HUC-12",
}
SOURCE_STYLE_OVERRIDES = {
    "epa_envirofacts_echo": {"color": "#FF2A00", "marker": "o"},
    "epa_frs_facilities_ms": {"color": "#8A00FF", "marker": "D"},
    "maris_brownfields": {"color": "#FF7A00", "marker": "s"},
    "maris_npdes_facilities": {"color": "#0057B8", "marker": "^"},
    "maris_solid_waste_landfills": {"color": "#FF007A", "marker": "P"},
    "maris_superfund_sites": {"color": "#D73027", "marker": "*"},
    "maris_tri_facilities": {"color": "#C51B7D", "marker": "h"},
    "maris_underground_storage_tanks": {"color": "#00D5FF", "marker": "v"},
    "mdeq_environmental_context": {"color": "#7B2CBF", "marker": "X"},
    "mississippi_oil_gas_wells": {"color": "#FFB000", "marker": "X"},
    "fema_nfhl_flood_hazard": {"color": "#8A00FF", "marker": "o"},
    "maris_public_cultural_context": {"color": "#FF00FF", "marker": "P", "marker_size": 13, "point_alpha": 0.82},
    "maris_community_facilities": {"color": "#FF7A00", "marker": "o"},
    "mdeq_303d_impaired_waters": {
        "color": "#FF2A00",
        "marker": "s",
        "line_width": 1.24,
        "line_alpha": 0.98,
        "polygon_alpha": 0.34,
        "polygon_line_width": 0.72,
    },
    "mdeq_public_water_supply_wells": {"color": "#0057FF", "marker": "P", "marker_size": 13, "point_alpha": 0.88},
    "usfws_nwi_wetlands": {"color": "#FFE500", "marker": "o", "line_width": 0.9, "line_alpha": 0.94, "polygon_alpha": 0.42, "polygon_line_width": 0.56},
    "usgs_nhd_flowlines": {"color": "#00D5FF", "marker": "o", "line_width": 0.86, "line_alpha": 0.82},
    "usgs_nhd_hydrography": {"color": "#00D5FF", "marker": "o", "line_width": 0.86, "line_alpha": 0.82},
    "usgs_nhd_waterbodies": {"color": "#0057FF", "marker": "o", "line_width": 0.7, "line_alpha": 0.72, "polygon_alpha": 0.24, "polygon_line_width": 0.42},
    "usgs_nhd_other_areas": {"color": "#FF00FF", "marker": "o", "line_width": 0.78, "line_alpha": 0.86, "polygon_alpha": 0.32, "polygon_line_width": 0.46},
    "usgs_wbd_huc12_subwatersheds": {"color": "#FFD400", "marker": "o", "line_width": 1.04, "line_alpha": 0.9, "polygon_alpha": 0.08, "polygon_line_width": 0.86},
    "local_utility_infrastructure": {"color": "#7B2CBF", "marker": "s"},
    "mdot_transportation_context": {"color": "#0057FF", "marker": "o"},
}
SOURCE_CATEGORY_IMAGERY_SAFE_COLORS = {
    "wetlands_waterbodies": "#FFE500",
    "hydrography_crossings": "#00D5FF",
    "flood_hazard": "#8A00FF",
    "water_quality": "#FF2A00",
    "species_habitat": "#7B2CBF",
    "regulated_facilities": "#D73027",
    "soils": "#7B2CBF",
    "community_socioeconomic": "#FF7A00",
    "cultural_historic": "#F72585",
    "transportation_utilities": "#0057FF",
}


def render_map(
    *,
    output_path: Any,
    title: str,
    unit_gdf: gpd.GeoDataFrame,
    analysis_crs: str,
    source_layers: list[dict[str, Any]],
    basemap: dict[str, Any] | None,
    method_note: str,
    source_note: str,
    focus_bounds: Any | None = None,
    render_layout: dict[str, Any] | None = None,
    embed_title: bool = False,
    comparison_layer_style: dict[str, Any] | None = None,
) -> dict[str, Any]:
    layout = render_layout or plan_render_layout_for_map(unit_gdf=unit_gdf, source_layers=source_layers, focus_bounds=focus_bounds)
    layout = dict(layout)
    layout["image_text_policy"] = {
        "map_panel_only": not embed_title,
        "embedded_title": bool(embed_title),
        "embedded_caption": False,
        "embedded_source_note": False,
        "embedded_method_note": False,
    }
    fig, ax = plt.subplots(figsize=_figure_size_for_bounds(layout["expanded_bounds"]), dpi=180)
    try:
        handles: list[Any] = []
        plotted: list[gpd.GeoDataFrame] = []
        if basemap and isinstance(basemap.get("layer"), dict):
            layer = basemap["layer"]
            ax.imshow(layer["image"], extent=layer["extent"], alpha=0.78, zorder=0)

        source_handles: list[Any] = []
        for index, layer in enumerate(source_layers):
            gdf = layer["gdf"]
            style = source_layer_style_record(layer, index)
            source_handles.extend(_plot_gdf(ax, gdf, style=style, is_project=False))
            if not gdf.empty:
                plotted.append(gdf)

        unit_handles = _plot_comparison_units(ax, unit_gdf, style_override=comparison_layer_style)
        handles.extend(unit_handles)
        handles.extend(source_handles)
        plotted.append(unit_gdf)

        _set_bounds(ax, layout["expanded_bounds"], pad_fraction=0.0)
        if embed_title:
            ax.set_title(_wrap_title(title), fontsize=9.3, pad=4)
        ax.set_axis_off()
        legend_artist = None
        if handles:
            legend_kwargs = _legend_kwargs_for_layout(layout)
            legend_artist = ax.legend(
                handles=_dedupe_handles(handles),
                loc=legend_kwargs["loc"],
                bbox_to_anchor=legend_kwargs["bbox_to_anchor"],
                ncol=legend_kwargs["ncol"],
                **_legend_style_kwargs(),
            )
        _add_north_arrow(ax, layout)
        _add_scale_bar(ax, analysis_crs, layout)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.subplots_adjust(left=0.015, right=0.985, top=0.985, bottom=0.015)
        if legend_artist is not None:
            fig.canvas.draw()
            actual_bbox = _artist_bbox_axes(legend_artist, ax, fig)
            layout["legend_actual_bbox_axes"] = actual_bbox
            layout["legend_fits_reserved_bbox"] = _bbox_contains(layout.get("legend_bbox_axes"), actual_bbox, tolerance=0.004)
            layout["legend_overlaps_core_bbox"] = _bboxes_overlap(actual_bbox, layout.get("core_bbox_axes"), tolerance=0.002)
        fig.savefig(output_path, bbox_inches="tight", pad_inches=0.035, facecolor="white")
        return layout
    finally:
        plt.close(fig)


def plan_render_layout_for_map(
    *,
    unit_gdf: gpd.GeoDataFrame,
    source_layers: list[dict[str, Any]],
    focus_bounds: Any | None = None,
) -> dict[str, Any]:
    base_bounds = _base_bounds_for_render(focus_bounds, unit_gdf, [layer["gdf"] for layer in source_layers])
    legend_labels = _legend_labels_for_map(unit_gdf, source_layers)
    return compute_visual_extent_with_legend_collar(
        base_bounds,
        legend_labels=legend_labels,
        feature_layers=[unit_gdf, *[layer["gdf"] for layer in source_layers]],
    )


def compute_visual_extent_with_legend_collar(
    bounds: Any,
    *,
    legend_labels: list[str],
    feature_layers: list[gpd.GeoDataFrame],
) -> dict[str, Any]:
    base_bounds = _padded_bounds(_clean_bounds(bounds), LEGEND_COLLAR_PADDING_FRACTION)
    labels = [str(label).strip() for label in legend_labels if str(label).strip()]
    if not labels:
        return _layout_record("none", base_bounds, base_bounds, None, labels)

    side = choose_legend_collar_side(base_bounds, labels, feature_layers)
    if side == "outside_frame":
        return _layout_record(side, base_bounds, base_bounds, None, labels)
    expanded_bounds, collar_bounds, collar_fraction, measurement = _expanded_bounds_for_collar(base_bounds, side, labels)
    return _layout_record(
        side,
        base_bounds,
        expanded_bounds,
        collar_bounds,
        labels,
        collar_fraction=collar_fraction,
        legend_measurement=measurement,
    )


def choose_legend_collar_side(
    bounds: Any,
    legend_labels: list[str],
    feature_layers: list[gpd.GeoDataFrame],
) -> str:
    base_bounds = _clean_bounds(bounds)
    west, south, east, north = base_bounds
    width = max(east - west, 1.0)
    height = max(north - south, 1.0)
    base_aspect = width / height
    if base_aspect < 0.75:
        target_aspect = 0.65
    elif base_aspect > 1.55:
        target_aspect = 1.55
    else:
        target_aspect = base_aspect

    scores: list[tuple[float, float, str]] = []
    for side in ("right", "left", "bottom", "top"):
        expanded, collar, _fraction, _measurement = _expanded_bounds_for_collar(base_bounds, side, legend_labels)
        ew, es, ee, en = expanded
        new_aspect = max((ee - ew) / max(en - es, 1.0), 0.001)
        density = _feature_density_score(collar, feature_layers)
        aspect_score = abs(_safe_log_ratio(new_aspect, target_aspect))
        preference = 0.0
        if base_aspect < 0.75:
            preference = -0.35 if side in {"right", "left"} else 0.35
        elif base_aspect > 1.55:
            preference = -0.25 if side in {"top", "bottom"} else 0.25
        scores.append((density * 8.0 + aspect_score + preference + _side_tie_breaker(side), density, side))
    best_score, best_density, best_side = min(scores, key=lambda item: item[0])
    if best_density >= 8.0 and all(density >= 8.0 for _score, density, _side in scores):
        return "outside_frame"
    return best_side


def estimate_legend_box_fraction(legend_labels: list[str], *, orientation: str) -> float:
    labels = [str(label).strip() for label in legend_labels if str(label).strip()]
    if not labels:
        return 0.0
    return _fallback_legend_box_fraction(labels, orientation=orientation)


def _fallback_legend_box_fraction(legend_labels: list[str], *, orientation: str) -> float:
    max_len = min(max(len(label) for label in legend_labels), MAX_LEGEND_LABEL_LENGTH)
    count = len(legend_labels)
    if orientation == "side":
        return min(LEGEND_COLLAR_MAX_FRACTION, max(0.28, 0.22 + (max_len * 0.0055)))
    return min(LEGEND_COLLAR_MAX_FRACTION, max(0.2, 0.13 + min(count, 8) * 0.028))


def _measured_legend_box_fraction(
    legend_labels: list[str],
    *,
    orientation: str,
    expanded_bounds: tuple[float, float, float, float],
) -> tuple[float, dict[str, Any]]:
    labels = tuple(str(label).strip() for label in legend_labels if str(label).strip())
    if not labels:
        return 0.0, {}
    ncol = _legend_ncol("right" if orientation == "side" else "top")
    figure_width, figure_height = _figure_size_for_bounds(expanded_bounds)
    west, south, east, north = expanded_bounds
    measured = _measure_legend_bbox_axes_fraction(
        labels,
        ncol,
        round(float(figure_width), 3),
        round(float(figure_height), 3),
        round(float(abs(east - west)), 3),
        round(float(abs(north - south)), 3),
    )
    dimension_fraction = float(measured["width_fraction"] if orientation == "side" else measured["height_fraction"])
    required_fraction = min(
        LEGEND_COLLAR_MAX_FRACTION,
        max(
            _fallback_legend_box_fraction(list(labels), orientation=orientation),
            dimension_fraction * LEGEND_MEASUREMENT_SAFETY_FACTOR + (LEGEND_COLLAR_AXES_PADDING * 2.0),
        ),
    )
    return required_fraction, {
        "measurement_method": "matplotlib_legend_bbox",
        "orientation": orientation,
        "ncol": ncol,
        "figure_size_inches": [round(float(figure_width), 3), round(float(figure_height), 3)],
        "legend_bbox_width_fraction": round(float(measured["width_fraction"]), 4),
        "legend_bbox_height_fraction": round(float(measured["height_fraction"]), 4),
        "required_collar_fraction": round(float(required_fraction), 4),
        "axes_padding_fraction": LEGEND_COLLAR_AXES_PADDING,
        "safety_factor": LEGEND_MEASUREMENT_SAFETY_FACTOR,
    }


def panel_bounds(bounds: tuple[float, float, float, float], panel_count: int) -> list[tuple[float, float, float, float]]:
    west, south, east, north = bounds
    width = east - west
    height = north - south
    panels: list[tuple[float, float, float, float]] = []
    if width >= height:
        step = width / panel_count
        for index in range(panel_count):
            left = west + step * index
            right = east if index == panel_count - 1 else west + step * (index + 1)
            panels.append((left, south, right, north))
    else:
        step = height / panel_count
        for index in range(panel_count):
            bottom = south + step * index
            top = north if index == panel_count - 1 else south + step * (index + 1)
            panels.append((west, bottom, east, top))
    return panels


def comparison_unit_style_records(gdf: gpd.GeoDataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if gdf.empty:
        return records
    selected_colors: list[str] = []
    for index, (_, row) in enumerate(gdf.iterrows()):
        unit_id = _row_text(row, "comparison_unit_id") or f"comparison-unit-{index + 1:05d}"
        full_label = _comparison_unit_label(row, index)
        label = _compact_comparison_unit_label(full_label, index)
        original_style_color = _row_text(row, "style_color")
        kml_color = _kml_color_to_visible_hex(original_style_color)
        style_source = "kml_style_color"
        if kml_color is None:
            color = _fallback_comparison_unit_color(unit_id or label, index, selected_colors)
            style_source = "deterministic_fallback"
        elif _route_color_is_usable(kml_color, selected_colors):
            color = kml_color
        else:
            color = _fallback_comparison_unit_color(unit_id or label, index, selected_colors)
            style_source = "deterministic_fallback_replaces_kml_color"
        selected_colors.append(color)
        records.append(
            {
                "comparison_unit_id": unit_id,
                "label": label,
                "full_label": full_label,
                "color": color,
                "line_width": COMPARISON_UNIT_LINE_WIDTH,
                "line_halo_width": COMPARISON_UNIT_LINE_HALO_WIDTH,
                "line_halo_alpha": COMPARISON_UNIT_LINE_HALO_ALPHA,
                "line_halo_color": COMPARISON_UNIT_LINE_HALO_COLOR,
                "style_source": style_source,
                "original_style_color": original_style_color,
            }
        )
    return records


def _plot_comparison_units(ax: Any, gdf: gpd.GeoDataFrame, *, style_override: dict[str, Any] | None = None) -> list[Any]:
    if gdf.empty:
        return []
    handles: list[Any] = []
    styles = comparison_unit_style_records(gdf)
    override = style_override or {}
    for index, (_, row) in enumerate(gdf.iterrows()):
        geometry = row.geometry
        if geometry is None or geometry.is_empty:
            continue
        style = styles[index]
        geometry_column = getattr(gdf.geometry, "name", "geometry")
        properties = row.drop(labels=[geometry_column]).to_dict() if geometry_column in row.index else row.to_dict()
        properties.pop("geometry", None)
        one = gpd.GeoDataFrame([properties], geometry=[geometry], crs=gdf.crs)
        label = str(override.get("label") or style["label"])
        color = str(override.get("stroke_color") or override.get("fill_color") or style["color"])
        fill_color = str(override.get("fill_color") or color)
        stroke_color = str(override.get("stroke_color") or color)
        zorder = float(override.get("z_index", 7))
        geom_type = geometry.geom_type
        if "Polygon" in geom_type:
            alpha = float(override.get("fill_opacity", 0.18))
            width = float(override.get("stroke_width", 0.75))
            one.plot(ax=ax, facecolor=fill_color, edgecolor=stroke_color, linewidth=width, alpha=alpha, zorder=zorder)
            handles.append(Patch(facecolor=fill_color, edgecolor=stroke_color, alpha=min(alpha, 0.28), label=label))
        elif "LineString" in geom_type:
            width = float(override.get("stroke_width", style["line_width"]))
            halo_width = float(style.get("line_halo_width", 0.0))
            halo_alpha = float(style.get("line_halo_alpha", 0.0))
            if halo_width > 0 and halo_alpha > 0:
                one.plot(
                    ax=ax,
                    color=str(style.get("line_halo_color") or COMPARISON_UNIT_LINE_HALO_COLOR),
                    linewidth=width + halo_width,
                    alpha=halo_alpha,
                    zorder=zorder - 0.2,
                )
            one.plot(ax=ax, color=stroke_color, linewidth=width, alpha=0.96, zorder=zorder)
            handles.append(Line2D([0], [0], color=stroke_color, lw=width, label=label))
        elif "Point" in geom_type:
            size = float(override.get("point_size", 18))
            one.plot(ax=ax, color="white", markersize=size + 8, alpha=0.88, zorder=zorder - 0.2)
            one.plot(ax=ax, color=fill_color, markersize=size, alpha=0.92, zorder=zorder)
            handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor=fill_color, markersize=4.8, label=label))
    return handles


def source_layer_style_record(layer: dict[str, Any], index: int) -> dict[str, Any]:
    source_id = str(layer.get("source_id") or "")
    override = SOURCE_STYLE_OVERRIDES.get(source_id, {})
    category = str(layer.get("source_category", ""))
    raw_color = str(
        override.get("color")
        or SOURCE_CATEGORY_IMAGERY_SAFE_COLORS.get(category)
        or SOURCE_CATEGORY_COLORS.get(category)
        or _source_color(index)
    )
    color = _source_thematic_color(raw_color, source_id=source_id, category=category, index=index)
    raw_normalized = _normalize_hex_color(raw_color)
    style_source = "source_id_override" if override else "category_or_sequence"
    if raw_normalized != color:
        style_source = f"{style_source}_palette_fallback"
    marker = str(override.get("marker") or _source_marker(index))
    feature_count = _feature_count(layer.get("gdf"))
    marker_size = float(override.get("marker_size") or (12 if feature_count <= 50 else 10 if feature_count <= 200 else 8))
    style = {
        "source_id": source_id,
        "label": legend_label_for_layer(layer),
        "color": color,
        "fill_color": color,
        "stroke_color": color,
        "marker": marker,
        "line_width": float(override.get("line_width") or 0.52),
        "line_alpha": float(override.get("line_alpha") or 0.52),
        "polygon_alpha": float(override.get("polygon_alpha") or 0.18),
        "polygon_line_width": float(override.get("polygon_line_width") or 0.35),
        "marker_size": marker_size,
        "marker_edge_color": "#111827",
        "marker_edge_width": 0.45,
        "marker_halo_color": "#FFFFFF",
        "marker_halo_alpha": 0.72,
        "marker_halo_size_delta": 6,
        "point_alpha": float(override.get("point_alpha") or 0.68),
        "style_source": style_source,
    }
    reviewer_override = layer.get("style_override") if isinstance(layer.get("style_override"), dict) else {}
    if reviewer_override:
        if reviewer_override.get("label"):
            style["label"] = str(reviewer_override["label"])
        if reviewer_override.get("fill_color"):
            style["fill_color"] = str(reviewer_override["fill_color"])
            style["color"] = str(reviewer_override["fill_color"])
        if reviewer_override.get("stroke_color"):
            style["stroke_color"] = str(reviewer_override["stroke_color"])
            style["color"] = str(reviewer_override["stroke_color"])
        if reviewer_override.get("fill_opacity") is not None:
            style["polygon_alpha"] = float(reviewer_override["fill_opacity"])
            style["point_alpha"] = float(reviewer_override["fill_opacity"])
        if reviewer_override.get("stroke_width") is not None:
            style["line_width"] = float(reviewer_override["stroke_width"])
            style["polygon_line_width"] = float(reviewer_override["stroke_width"])
        if reviewer_override.get("point_size") is not None:
            style["marker_size"] = float(reviewer_override["point_size"])
        if reviewer_override.get("z_index") is not None:
            style["z_index"] = float(reviewer_override["z_index"])
        style["style_source"] = "reviewer_style_override"
    return style


def legend_label_for_layer(layer: dict[str, Any]) -> str:
    source_id = str(layer.get("source_id") or "")
    if source_id in SOURCE_LABEL_OVERRIDES:
        return SOURCE_LABEL_OVERRIDES[source_id]
    label = str(layer.get("source_name") or layer.get("source_id") or "Source layer")
    label = re.sub(r"\bMississippi\b", "", label, flags=re.IGNORECASE)
    label = re.sub(r"\bFacilities\b", "", label, flags=re.IGNORECASE)
    label = re.sub(r"\s+", " ", label.replace("/", " / ")).strip(" -/")
    return _truncate_label(label, MAX_LEGEND_LABEL_LENGTH)


def _plot_gdf(ax: Any, gdf: gpd.GeoDataFrame, *, style: dict[str, Any], is_project: bool) -> list[Any]:
    if gdf.empty:
        return []
    handles: list[Any] = []
    color = str(style.get("color") or THEMATIC_FALLBACK_COLORS[0])
    fill_color = str(style.get("fill_color") or color)
    stroke_color = str(style.get("stroke_color") or color)
    label = str(style.get("label") or "Source layer")
    marker = str(style.get("marker") or "o")
    zorder = float(style.get("z_index", 5 if is_project else 4))
    polygon_gdf = gdf[gdf.geometry.geom_type.str.contains("Polygon", na=False)]
    line_gdf = gdf[gdf.geometry.geom_type.str.contains("LineString", na=False)]
    point_gdf = gdf[gdf.geometry.geom_type.str.contains("Point", na=False)]
    if not polygon_gdf.empty:
        if is_project:
            polygon_gdf.plot(ax=ax, facecolor="none", edgecolor=stroke_color, linewidth=1.15, zorder=zorder)
            handles.append(Patch(facecolor="none", edgecolor=stroke_color, label=label))
        else:
            polygon_gdf.plot(
                ax=ax,
                facecolor=fill_color,
                edgecolor=stroke_color,
                linewidth=float(style.get("polygon_line_width", 0.35)),
                alpha=float(style.get("polygon_alpha", 0.18)),
                zorder=zorder,
            )
            handles.append(Patch(facecolor=fill_color, edgecolor=stroke_color, alpha=0.2, label=label))
    if not line_gdf.empty:
        width = 1.45 if is_project else float(style.get("line_width", 0.52))
        alpha = 0.9 if is_project else float(style.get("line_alpha", 0.52))
        line_gdf.plot(ax=ax, color=stroke_color, linewidth=width, alpha=alpha, zorder=zorder)
        handles.append(Line2D([0], [0], color=stroke_color, lw=width, label=label))
    if not point_gdf.empty:
        size = 26 if is_project else float(style.get("marker_size", 15))
        if not is_project:
            point_gdf.plot(
                ax=ax,
                marker=marker,
                color=str(style.get("marker_halo_color") or "#FFFFFF"),
                markersize=size + float(style.get("marker_halo_size_delta", 6)),
                alpha=float(style.get("marker_halo_alpha", 0.72)),
                zorder=4.8,
            )
        point_gdf.plot(
            ax=ax,
            marker=marker,
            color=fill_color,
            edgecolor=stroke_color or str(style.get("marker_edge_color") or "#111827"),
            linewidth=float(style.get("marker_edge_width", 0.45)),
            markersize=size,
            alpha=0.9 if is_project else float(style.get("point_alpha", 0.74)),
            zorder=zorder,
        )
        handles.append(
            Line2D(
                [0],
                [0],
                marker=marker,
                color="none",
                markerfacecolor=fill_color,
                markeredgecolor=stroke_color or str(style.get("marker_edge_color") or "#111827"),
                markeredgewidth=float(style.get("marker_edge_width", 0.45)),
                markersize=4.8,
                label=label,
            )
        )
    return handles[:1]


def _comparison_unit_label(row: Any, index: int) -> str:
    for column in ("comparison_unit_name", "comparison_unit_group", "candidate_label", "placemark_name", "style_url"):
        value = _row_text(row, column)
        if value and value.lower() != "multiple":
            return value
    unit_id = _row_text(row, "comparison_unit_id")
    return unit_id or f"Comparison unit {index + 1}"


def _compact_comparison_unit_label(label: str, index: int) -> str:
    text = str(label or "").strip()
    text = re.sub(r"\.(dwg|kmz|kml|shp|geojson)$", "", text, flags=re.IGNORECASE)
    normalized = re.sub(r"[_-]+", " ", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    simple_alternative = re.fullmatch(r"(alternative)\s+([0-9]+[A-Za-z]?|[A-Za-z])", normalized, flags=re.IGNORECASE)
    if simple_alternative:
        return f"Alternative {simple_alternative.group(2).upper()}"
    option_match = re.search(r"\b(?:alternative|option|alt)\s*([0-9]+[A-Za-z]?|[A-Za-z])\b", normalized, flags=re.IGNORECASE)
    if option_match:
        prefix = "Alt" if re.search(r"\b(?:alternative|alt)\b", text, flags=re.IGNORECASE) else "Option"
        return f"{prefix} {option_match.group(1).upper()}"
    route_match = re.search(r"\broute\s*([0-9]+[A-Za-z]?|[A-Za-z])\b", normalized, flags=re.IGNORECASE)
    if route_match:
        return f"Route {route_match.group(1).upper()}"
    unit_match = re.search(r"comparison[-_ ]unit[-_ ]0*(\d+)", normalized, flags=re.IGNORECASE)
    if unit_match:
        return f"Unit {int(unit_match.group(1))}"
    text = re.sub(r"\b20\d{2}\b", "", normalized)
    text = re.sub(r"\s+", " ", text).strip()
    return _truncate_label(text or f"Unit {index + 1}", 24)


def _row_text(row: Any, column: str) -> str:
    try:
        if column not in row.index:
            return ""
        value = row[column]
    except Exception:
        return ""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if not text or text.lower() == "nan" else text


def _kml_color_to_visible_hex(value: str) -> str | None:
    text = re.sub(r"[^0-9a-fA-F]", "", str(value or "")).lower()
    if len(text) == 8:
        alpha = int(text[0:2], 16)
        blue = int(text[2:4], 16)
        green = int(text[4:6], 16)
        red = int(text[6:8], 16)
    elif len(text) == 6:
        alpha = 255
        red = int(text[0:2], 16)
        green = int(text[2:4], 16)
        blue = int(text[4:6], 16)
    else:
        return None
    if alpha < 64:
        return None
    if _relative_luminance(red, green, blue) > 0.88:
        return None
    return f"#{red:02x}{green:02x}{blue:02x}"


def _relative_luminance(red: int, green: int, blue: int) -> float:
    def channel(value: int) -> float:
        normalized = value / 255
        return normalized / 12.92 if normalized <= 0.03928 else ((normalized + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def _fallback_comparison_unit_color(key: str, index: int, selected_colors: list[str] | None = None) -> str:
    selected = selected_colors or []
    if index < len(COMPARISON_UNIT_FALLBACK_COLORS):
        ordered = COMPARISON_UNIT_FALLBACK_COLORS[index:] + COMPARISON_UNIT_FALLBACK_COLORS[:index]
    else:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        offset = int(digest[:8], 16) % len(COMPARISON_UNIT_FALLBACK_COLORS)
        ordered = COMPARISON_UNIT_FALLBACK_COLORS[offset:] + COMPARISON_UNIT_FALLBACK_COLORS[:offset]
    for color in ordered:
        if _route_color_is_usable(color, selected):
            return color
    if index < len(COMPARISON_UNIT_FALLBACK_COLORS):
        return COMPARISON_UNIT_FALLBACK_COLORS[index]
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return COMPARISON_UNIT_FALLBACK_COLORS[int(digest[:8], 16) % len(COMPARISON_UNIT_FALLBACK_COLORS)]


def _route_color_is_usable(color: str, selected_colors: list[str]) -> bool:
    rgb = _hex_to_rgb(color)
    if rgb is None:
        return False
    red, green, blue = rgb
    hue = _hue_degrees(red, green, blue)
    saturation = _saturation(red, green, blue)
    value = _color_value(red, green, blue)
    if _relative_luminance(red, green, blue) > IMAGERY_RISK_LUMINANCE_MAX and saturation < IMAGERY_SAFE_MIN_SATURATION:
        return False
    if IMAGERY_RISK_HUE_MIN <= hue <= IMAGERY_RISK_HUE_MAX and (
        saturation < IMAGERY_SAFE_MIN_SATURATION or value < IMAGERY_SAFE_MIN_VALUE
    ):
        return False
    return all(_route_colors_are_distinct(color, selected) for selected in selected_colors)


def _route_colors_are_distinct(color_a: str, color_b: str) -> bool:
    rgb_a = _hex_to_rgb(color_a)
    rgb_b = _hex_to_rgb(color_b)
    if rgb_a is None or rgb_b is None:
        return False
    distance = sum((left - right) ** 2 for left, right in zip(rgb_a, rgb_b)) ** 0.5
    if distance < ROUTE_COLOR_MIN_DISTANCE:
        return False
    if _warm_route_pair_too_close(rgb_a, rgb_b):
        return False
    return True


def _warm_route_pair_too_close(rgb_a: tuple[int, int, int], rgb_b: tuple[int, int, int]) -> bool:
    if max(rgb_a) - min(rgb_a) < 24 or max(rgb_b) - min(rgb_b) < 24:
        return False
    hue_a = _hue_degrees(*rgb_a)
    hue_b = _hue_degrees(*rgb_b)
    warm_a = hue_a <= 55.0 or hue_a >= 335.0
    warm_b = hue_b <= 55.0 or hue_b >= 335.0
    if not warm_a or not warm_b:
        return False
    hue_gap = abs(hue_a - hue_b)
    hue_gap = min(hue_gap, 360.0 - hue_gap)
    return hue_gap < 58.0


def _hex_to_rgb(color: str) -> tuple[int, int, int] | None:
    text = str(color or "").strip().lstrip("#")
    if len(text) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", text):
        return None
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def _normalize_hex_color(color: str) -> str | None:
    rgb = _hex_to_rgb(color)
    if rgb is None:
        return None
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _source_thematic_color(color: str, *, source_id: str, category: str, index: int) -> str:
    normalized = _normalize_hex_color(color)
    if normalized and _thematic_color_is_allowed(normalized):
        return normalized
    return _thematic_fallback_color(f"{source_id}:{category}", index)


def _thematic_fallback_color(key: str, index: int) -> str:
    if index < len(THEMATIC_FALLBACK_COLORS):
        ordered = THEMATIC_FALLBACK_COLORS[index:] + THEMATIC_FALLBACK_COLORS[:index]
    else:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        offset = int(digest[:8], 16) % len(THEMATIC_FALLBACK_COLORS)
        ordered = THEMATIC_FALLBACK_COLORS[offset:] + THEMATIC_FALLBACK_COLORS[:offset]
    for color in ordered:
        normalized = _normalize_hex_color(color)
        if normalized and _thematic_color_is_allowed(normalized):
            return normalized
    return "#FF00FF"


def _thematic_color_is_allowed(color: str) -> bool:
    rgb = _hex_to_rgb(color)
    if rgb is None:
        return False
    red, green, blue = rgb
    hue = _hue_degrees(red, green, blue)
    saturation = _saturation(red, green, blue)
    value = _color_value(red, green, blue)
    luminance = _relative_luminance(red, green, blue)
    if max(red, green, blue) <= 35:
        return False
    if saturation < THEMATIC_MIN_SATURATION or value < THEMATIC_MIN_VALUE:
        return False
    if luminance > THEMATIC_MAX_LOW_SATURATION_LUMINANCE and saturation < 0.9:
        return False
    if THEMATIC_PROHIBITED_GREEN_HUE_MIN <= hue <= THEMATIC_PROHIBITED_GREEN_HUE_MAX:
        return False
    if THEMATIC_EARTH_TONE_HUE_MIN <= hue <= THEMATIC_EARTH_TONE_HUE_MAX and (saturation < 0.88 or value < 0.86):
        return False
    return True


def _hue_degrees(red: int, green: int, blue: int) -> float:
    hue, _saturation, _value = rgb_to_hsv(red / 255, green / 255, blue / 255)
    return hue * 360.0


def _saturation(red: int, green: int, blue: int) -> float:
    _hue, saturation, _value = rgb_to_hsv(red / 255, green / 255, blue / 255)
    return saturation


def _color_value(red: int, green: int, blue: int) -> float:
    _hue, _saturation, value = rgb_to_hsv(red / 255, green / 255, blue / 255)
    return value


def _legend_labels_for_map(unit_gdf: gpd.GeoDataFrame, source_layers: list[dict[str, Any]]) -> list[str]:
    labels = [str(style["label"]) for style in comparison_unit_style_records(unit_gdf)]
    labels.extend(legend_label_for_layer(layer) for layer in source_layers if not layer.get("gdf", gpd.GeoDataFrame()).empty)
    return _dedupe_strings(labels)


def _base_bounds_for_render(
    focus_bounds: Any | None,
    unit_gdf: gpd.GeoDataFrame,
    source_gdfs: list[gpd.GeoDataFrame],
) -> tuple[float, float, float, float]:
    if focus_bounds is not None:
        try:
            return _clean_bounds(focus_bounds)
        except ValueError:
            pass
    return _bounds_for_layers([unit_gdf, *source_gdfs])


def _bounds_for_layers(layers: list[gpd.GeoDataFrame]) -> tuple[float, float, float, float]:
    non_empty = [layer for layer in layers if isinstance(layer, gpd.GeoDataFrame) and not layer.empty]
    if not non_empty:
        return (0.0, 0.0, 1000.0, 1000.0)
    bounds = [layer.total_bounds for layer in non_empty]
    return _clean_bounds(
        (
            min(float(bound[0]) for bound in bounds),
            min(float(bound[1]) for bound in bounds),
            max(float(bound[2]) for bound in bounds),
            max(float(bound[3]) for bound in bounds),
        )
    )


def _clean_bounds(bounds: Any) -> tuple[float, float, float, float]:
    west, south, east, north = [float(value) for value in bounds]
    if west == east:
        west -= 500.0
        east += 500.0
    if south == north:
        south -= 500.0
        north += 500.0
    if west > east:
        west, east = east, west
    if south > north:
        south, north = north, south
    if not all(_is_finite(value) for value in (west, south, east, north)):
        raise ValueError("Bounds must be finite numeric values.")
    return (west, south, east, north)


def _padded_bounds(bounds: tuple[float, float, float, float], fraction: float) -> tuple[float, float, float, float]:
    west, south, east, north = bounds
    width = east - west
    height = north - south
    pad_x = width * fraction if width > 0 else 250.0
    pad_y = height * fraction if height > 0 else 250.0
    return (west - pad_x, south - pad_y, east + pad_x, north + pad_y)


def _expanded_bounds_for_collar(
    bounds: tuple[float, float, float, float],
    side: str,
    legend_labels: list[str],
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float], float, dict[str, Any]]:
    west, south, east, north = bounds
    width = max(east - west, 1.0)
    height = max(north - south, 1.0)
    orientation = "side" if side in {"left", "right"} else "horizontal"
    fraction = estimate_legend_box_fraction(legend_labels, orientation=orientation)
    measurement: dict[str, Any] = {
        "measurement_method": "heuristic_initial",
        "orientation": orientation,
        "required_collar_fraction": round(float(fraction), 4),
    }
    expanded: tuple[float, float, float, float]
    collar: tuple[float, float, float, float]
    for _index in range(4):
        expanded, collar = _bounds_for_collar_fraction(bounds, side, fraction)
        measured_fraction, measured = _measured_legend_box_fraction(
            legend_labels,
            orientation=orientation,
            expanded_bounds=expanded,
        )
        measurement = measured or measurement
        if measured_fraction <= fraction + 0.002:
            break
        fraction = measured_fraction
    expanded, collar = _bounds_for_collar_fraction(bounds, side, fraction)
    measured_fraction, measured = _measured_legend_box_fraction(
        legend_labels,
        orientation=orientation,
        expanded_bounds=expanded,
    )
    if measured:
        measurement = measured
    fraction = max(fraction, measured_fraction)
    expanded, collar = _bounds_for_collar_fraction(bounds, side, fraction)
    measurement["final_collar_fraction"] = round(float(fraction), 4)
    measurement["collar_fraction_max"] = LEGEND_COLLAR_MAX_FRACTION
    return expanded, collar, fraction, measurement


def _bounds_for_collar_fraction(
    bounds: tuple[float, float, float, float],
    side: str,
    fraction: float,
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    west, south, east, north = bounds
    width = max(east - west, 1.0)
    height = max(north - south, 1.0)
    orientation = "side" if side in {"left", "right"} else "horizontal"
    fraction = min(max(float(fraction), 0.0), LEGEND_COLLAR_MAX_FRACTION)
    expansion = (width if orientation == "side" else height) * fraction / max(1.0 - fraction, 0.01)
    if side == "right":
        expanded = (west, south, east + expansion, north)
        collar = (east, south, east + expansion, north)
    elif side == "left":
        expanded = (west - expansion, south, east, north)
        collar = (west - expansion, south, west, north)
    elif side == "top":
        expanded = (west, south, east, north + expansion)
        collar = (west, north, east, north + expansion)
    else:
        expanded = (west, south - expansion, east, north)
        collar = (west, south - expansion, east, south)
    return expanded, collar


def _layout_record(
    side: str,
    base_bounds: tuple[float, float, float, float],
    expanded_bounds: tuple[float, float, float, float],
    collar_bounds: tuple[float, float, float, float] | None,
    legend_labels: list[str],
    *,
    collar_fraction: float = 0.0,
    legend_measurement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    core_bbox = _extent_bbox_axes(expanded_bounds, base_bounds)
    collar_bbox = _extent_bbox_axes(expanded_bounds, collar_bounds) if collar_bounds else []
    return {
        "layout_strategy": "outside_frame_legend" if side == "outside_frame" else "legend_collar" if side != "none" else "no_legend_collar",
        "legend_side": side,
        "render_extent_type": FIGURE_RENDER_EXTENT,
        "render_extent_is_presentation_only": True,
        "presentation_extent_type": PRESENTATION_ONLY_COLLAR_EXTENT if collar_bounds else "",
        "base_bounds": [float(value) for value in base_bounds],
        "expanded_bounds": [float(value) for value in expanded_bounds],
        "collar_bounds": [float(value) for value in collar_bounds] if collar_bounds else [],
        "core_bbox_axes": core_bbox,
        "collar_bbox_axes": collar_bbox,
        "legend_label_count": len(legend_labels),
        "legend_labels": legend_labels,
        "collar_fraction": round(float(collar_fraction), 4),
        "legend_bbox_axes": _legend_bbox_axes(expanded_bounds, collar_bounds, side) if collar_bounds else [],
        "legend_measurement": legend_measurement or {},
        "image_text_policy": {
            "map_panel_only": True,
            "embedded_title": False,
            "embedded_caption": False,
            "embedded_source_note": False,
            "embedded_method_note": False,
        },
    }


def _legend_bbox_axes(
    expanded_bounds: tuple[float, float, float, float],
    collar_bounds: tuple[float, float, float, float],
    side: str,
) -> list[float]:
    x0, y0, x1, y1 = _extent_bbox_axes(expanded_bounds, collar_bounds)
    pad = LEGEND_COLLAR_AXES_PADDING
    if side in {"right", "left"}:
        return [round(max(0.0, x0 + pad), 4), round(max(0.0, y0 + pad), 4), round(min(1.0, x1 - pad), 4), round(min(1.0, y1 - pad), 4)]
    return [round(max(0.0, x0 + pad), 4), round(max(0.0, y0 + pad), 4), round(min(1.0, x1 - pad), 4), round(min(1.0, y1 - pad), 4)]


def _extent_bbox_axes(
    expanded_bounds: tuple[float, float, float, float],
    bounds: tuple[float, float, float, float] | None,
) -> list[float]:
    if bounds is None:
        return []
    west, south, east, north = expanded_bounds
    bw, bs, be, bn = bounds
    width = max(east - west, 1.0)
    height = max(north - south, 1.0)
    return [
        round((bw - west) / width, 4),
        round((bs - south) / height, 4),
        round((be - west) / width, 4),
        round((bn - south) / height, 4),
    ]


def _legend_kwargs_for_layout(layout: dict[str, Any]) -> dict[str, Any]:
    side = str(layout.get("legend_side") or "none")
    bbox = layout.get("legend_bbox_axes") if isinstance(layout.get("legend_bbox_axes"), list) else []
    if len(bbox) != 4:
        return {"loc": "upper right", "bbox_to_anchor": (0.985, 0.985), "ncol": 1}
    x0, y0, x1, y1 = [float(value) for value in bbox]
    if side == "right":
        return {"loc": "upper left", "bbox_to_anchor": (x0, y1), "ncol": _legend_ncol(side)}
    if side == "left":
        return {"loc": "upper right", "bbox_to_anchor": (x1, y1), "ncol": _legend_ncol(side)}
    if side == "top":
        return {"loc": "lower left", "bbox_to_anchor": (x0, y0), "ncol": _legend_ncol(side)}
    if side == "bottom":
        return {"loc": "upper left", "bbox_to_anchor": (x0, y1), "ncol": _legend_ncol(side)}
    if side == "outside_frame":
        return {"loc": "upper left", "bbox_to_anchor": (1.01, 0.99), "ncol": _legend_ncol(side)}
    return {"loc": "upper right", "bbox_to_anchor": (0.985, 0.985), "ncol": 1}


def _legend_ncol(side: str) -> int:
    return 2 if side in {"top", "bottom"} else 1


def _legend_style_kwargs() -> dict[str, Any]:
    return {
        "frameon": True,
        "framealpha": 0.84,
        "facecolor": "white",
        "edgecolor": "#AFAFAF",
        "fontsize": LEGEND_FONT_SIZE,
        "title": "Layers",
        "title_fontsize": LEGEND_TITLE_FONT_SIZE,
        "borderpad": LEGEND_BORDERPAD,
        "labelspacing": LEGEND_LABELSPACING,
        "handlelength": LEGEND_HANDLE_LENGTH,
        "handletextpad": LEGEND_HANDLETEXTPAD,
    }


@lru_cache(maxsize=256)
def _measure_legend_bbox_axes_fraction(
    labels: tuple[str, ...],
    ncol: int,
    figure_width: float,
    figure_height: float,
    bounds_width: float,
    bounds_height: float,
) -> dict[str, float]:
    fig, ax = plt.subplots(figsize=(figure_width, figure_height), dpi=180)
    try:
        fig.subplots_adjust(left=0.015, right=0.985, top=0.985, bottom=0.015)
        ax.set_xlim(0, max(float(bounds_width), 1.0))
        ax.set_ylim(0, max(float(bounds_height), 1.0))
        ax.set_aspect("equal", adjustable="box")
        handles = [Line2D([0], [0], color="#2B2B2B", lw=COMPARISON_UNIT_LINE_WIDTH, label=label) for label in labels]
        legend = ax.legend(
            handles=handles,
            loc="upper left",
            bbox_to_anchor=(0, 1),
            ncol=ncol,
            **_legend_style_kwargs(),
        )
        ax.set_axis_off()
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        legend_bbox = legend.get_window_extent(renderer)
        ax_bbox = ax.get_window_extent(renderer)
        return {
            "width_fraction": float(legend_bbox.width / max(ax_bbox.width, 1.0)),
            "height_fraction": float(legend_bbox.height / max(ax_bbox.height, 1.0)),
        }
    finally:
        plt.close(fig)


def _artist_bbox_axes(artist: Any, ax: Any, fig: Any) -> list[float]:
    renderer = fig.canvas.get_renderer()
    bbox = artist.get_window_extent(renderer)
    transformed = ax.transAxes.inverted().transform([[bbox.x0, bbox.y0], [bbox.x1, bbox.y1]])
    return [
        round(float(transformed[0][0]), 4),
        round(float(transformed[0][1]), 4),
        round(float(transformed[1][0]), 4),
        round(float(transformed[1][1]), 4),
    ]


def _bbox_contains(container: Any, child: Any, *, tolerance: float = 0.0) -> bool:
    if not isinstance(container, list) or not isinstance(child, list) or len(container) != 4 or len(child) != 4:
        return False
    cx0, cy0, cx1, cy1 = [float(value) for value in container]
    x0, y0, x1, y1 = [float(value) for value in child]
    return x0 >= cx0 - tolerance and y0 >= cy0 - tolerance and x1 <= cx1 + tolerance and y1 <= cy1 + tolerance


def _bboxes_overlap(left: Any, right: Any, *, tolerance: float = 0.0) -> bool:
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != 4 or len(right) != 4:
        return False
    lx0, ly0, lx1, ly1 = [float(value) for value in left]
    rx0, ry0, rx1, ry1 = [float(value) for value in right]
    return not (lx1 <= rx0 + tolerance or rx1 <= lx0 + tolerance or ly1 <= ry0 + tolerance or ry1 <= ly0 + tolerance)


def _feature_density_score(bounds: tuple[float, float, float, float], layers: list[gpd.GeoDataFrame]) -> float:
    try:
        from shapely.geometry import box
    except Exception:
        return 0.0
    collar = box(*bounds)
    score = 0.0
    for index, layer in enumerate(layers):
        if not isinstance(layer, gpd.GeoDataFrame) or layer.empty:
            continue
        try:
            hits = layer.geometry.intersects(collar)
        except Exception:
            continue
        weight = 8.0 if index == 0 else 1.0
        score += float(hits.sum()) * weight
    return score


def _safe_log_ratio(value: float, reference: float) -> float:
    import math

    return math.log(max(value, 0.001) / max(reference, 0.001))


def _side_tie_breaker(side: str) -> float:
    return {"right": 0.0, "left": 0.02, "bottom": 0.04, "top": 0.06}.get(side, 0.1)


def _feature_count(value: Any) -> int:
    try:
        return int(len(value))
    except Exception:
        return 0


def _is_finite(value: float) -> bool:
    import math

    return math.isfinite(value)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _set_extent(ax: Any, layers: list[gpd.GeoDataFrame]) -> None:
    non_empty = [layer for layer in layers if not layer.empty]
    if not non_empty:
        return
    bounds = [layer.total_bounds for layer in non_empty]
    west = min(float(bound[0]) for bound in bounds)
    south = min(float(bound[1]) for bound in bounds)
    east = max(float(bound[2]) for bound in bounds)
    north = max(float(bound[3]) for bound in bounds)
    _set_bounds(ax, (west, south, east, north))


def _set_bounds(ax: Any, bounds: Any, *, pad_fraction: float = 0.055) -> None:
    west, south, east, north = [float(value) for value in bounds]
    width = east - west
    height = north - south
    pad_x = width * pad_fraction if width > 0 else 250
    pad_y = height * pad_fraction if height > 0 else 250
    ax.set_xlim(west - pad_x, east + pad_x)
    ax.set_ylim(south - pad_y, north + pad_y)
    ax.set_aspect("equal", adjustable="box")


def _add_north_arrow(ax: Any, layout: dict[str, Any]) -> None:
    side = str(layout.get("legend_side") or "")
    bbox = layout.get("legend_bbox_axes") if isinstance(layout.get("legend_bbox_axes"), list) else []
    if len(bbox) == 4 and side in {"right", "left"}:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        x = (x0 + x1) / 2
        y_text, y_arrow = max(y0 + 0.28, 0.34), max(y0 + 0.39, 0.45)
    elif len(bbox) == 4 and side in {"top", "bottom"}:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        x = min(x1 - 0.05, 0.94)
        y_text = (y0 + y1) / 2 - 0.035
        y_arrow = (y0 + y1) / 2 + 0.075
    elif side == "right":
        x, y_text, y_arrow = 0.07, 0.78, 0.89
    elif side == "top":
        x, y_text, y_arrow = 0.94, 0.68, 0.79
    else:
        x, y_text, y_arrow = 0.94, 0.79, 0.90
    ax.annotate(
        "N",
        xy=(x, y_arrow),
        xytext=(x, y_text),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "color": "#2B2B2B", "lw": 1.0},
        bbox={"facecolor": "white", "edgecolor": "#BDBDBD", "alpha": 0.9, "pad": 1.5},
    )


def _add_scale_bar(ax: Any, analysis_crs: str, layout: dict[str, Any]) -> None:
    feet_per_unit = _feet_per_crs_unit(analysis_crs)
    if feet_per_unit is None:
        return
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    width = abs(x_max - x_min)
    height = abs(y_max - y_min)
    if width <= 0 or height <= 0:
        return
    target_feet = width * feet_per_unit * 0.18
    scale_feet = _nice_scale_feet(target_feet)
    scale_units = scale_feet / feet_per_unit
    side = str(layout.get("legend_side") or "")
    bbox = layout.get("legend_bbox_axes") if isinstance(layout.get("legend_bbox_axes"), list) else []
    if len(bbox) == 4 and side in {"right", "left"}:
        x0, y0, x1, _y1 = [float(value) for value in bbox]
        collar_width_fraction = max(x1 - x0, 0.04)
        target_feet = width * feet_per_unit * min(collar_width_fraction * 0.62, 0.18)
        scale_feet = _nice_scale_feet(target_feet)
        scale_units = scale_feet / feet_per_unit
        x_fraction = x0 + collar_width_fraction * 0.18
        y_fraction = y0 + 0.07
    elif len(bbox) == 4 and side in {"top", "bottom"}:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        x_fraction = x0 + 0.04
        y_fraction = y0 + 0.14 if side == "bottom" else max(y0 + 0.08, (y0 + y1) / 2 - 0.05)
    else:
        x_fraction = 0.58 if side in {"left", "bottom"} else 0.08
        y_fraction = 0.15 if side == "bottom" else 0.08
    x0 = x_min + width * x_fraction
    y0 = y_min + height * y_fraction
    ax.plot([x0, x0 + scale_units], [y0, y0], color="#2B2B2B", linewidth=2.0, solid_capstyle="butt")
    label = f"{scale_feet / 5280:g} mi" if scale_feet >= 5280 else f"{int(scale_feet):,} ft"
    ax.text(
        x0 + scale_units / 2,
        y0 + height * 0.018,
        label,
        ha="center",
        va="bottom",
        fontsize=5.8,
        color="#2B2B2B",
        bbox={"facecolor": "white", "edgecolor": "#D0D0D0", "alpha": 0.9, "pad": 1.5},
    )


def _feet_per_crs_unit(analysis_crs: str) -> float | None:
    try:
        crs = CRS.from_user_input(analysis_crs)
    except Exception:
        return None
    if not crs.axis_info:
        return None
    unit_name = str(crs.axis_info[0].unit_name or "").lower()
    if "metre" in unit_name or "meter" in unit_name:
        return 3.280839895
    if "foot" in unit_name or "feet" in unit_name:
        return 1.0
    return None


def _nice_scale_feet(target_feet: float) -> float:
    candidates = [100, 250, 500, 1000, 2000, 5280, 10000, 26400, 52800, 105600]
    valid = [candidate for candidate in candidates if candidate <= target_feet]
    return float(valid[-1] if valid else candidates[0])


def _dedupe_handles(handles: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for handle in handles:
        label = str(handle.get_label())
        if label in seen:
            continue
        seen.add(label)
        result.append(handle)
    return result


def _source_color(index: int) -> str:
    return THEMATIC_FALLBACK_COLORS[index % len(THEMATIC_FALLBACK_COLORS)]


def _source_marker(index: int) -> str:
    markers = ["o", "s", "^", "D", "P", "v", "h", "*"]
    return markers[index % len(markers)]


def _figure_size_for_bounds(bounds: Any | None) -> tuple[float, float]:
    if bounds is None:
        return (5.4, 4.7)
    try:
        west, south, east, north = [float(value) for value in bounds]
    except Exception:
        return (5.4, 4.7)
    width = abs(east - west)
    height = abs(north - south)
    if width <= 0 or height <= 0:
        return (5.4, 4.7)
    aspect = width / height
    if aspect < 0.45:
        return (4.1, 6.4)
    if aspect < 0.8:
        return (4.7, 5.9)
    if aspect > 2.5:
        return (6.4, 3.7)
    if aspect > 1.45:
        return (6.0, 4.3)
    return (5.3, 5.0)


def _wrap_title(title: str) -> str:
    return "\n".join(textwrap.wrap(str(title), width=58)) or str(title)


def _truncate_label(label: str, max_length: int) -> str:
    text = str(label or "").strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."
