"""Matplotlib rendering and layout helpers for deliverable figures."""

from __future__ import annotations

import hashlib
import re
import textwrap
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
    "#0057B8",
    "#D55E00",
    "#008A5B",
    "#7B2CBF",
    "#C1121F",
    "#0072B2",
    "#B0006D",
    "#6F5200",
]
COMPARISON_UNIT_LINE_WIDTH = 1.25
MAX_LEGEND_LABEL_LENGTH = 26
LEGEND_COLLAR_PADDING_FRACTION = 0.045
LEGEND_COLLAR_MAX_FRACTION = 0.34

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
    "mdot_transportation_context": "Roads/rail",
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
}
SOURCE_STYLE_OVERRIDES = {
    "epa_envirofacts_echo": {"color": "#E15759", "marker": "o"},
    "epa_frs_facilities_ms": {"color": "#5E3C99", "marker": "D"},
    "maris_brownfields": {"color": "#B86B00", "marker": "s"},
    "maris_npdes_facilities": {"color": "#0072B2", "marker": "^"},
    "maris_solid_waste_landfills": {"color": "#4D4D4D", "marker": "P"},
    "maris_superfund_sites": {"color": "#D55E00", "marker": "*"},
    "maris_tri_facilities": {"color": "#CC79A7", "marker": "h"},
    "maris_underground_storage_tanks": {"color": "#009E73", "marker": "v"},
    "mdeq_environmental_context": {"color": "#8C564B", "marker": "X"},
    "mississippi_oil_gas_wells": {"color": "#6F4E37", "marker": "X"},
    "fema_nfhl_flood_hazard": {"color": "#7B2CBF", "marker": "o"},
    "usfws_nwi_wetlands": {"color": "#009E73", "marker": "o"},
    "usgs_nhd_flowlines": {"color": "#2F80ED", "marker": "o"},
    "usgs_nhd_hydrography": {"color": "#2F80ED", "marker": "o"},
    "usgs_nhd_waterbodies": {"color": "#56CCF2", "marker": "o"},
    "usgs_nhd_other_areas": {"color": "#2D9CDB", "marker": "o"},
    "local_utility_infrastructure": {"color": "#9467BD", "marker": "s"},
    "mdot_transportation_context": {"color": "#5C677D", "marker": "o"},
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
) -> dict[str, Any]:
    base_bounds = _base_bounds_for_render(focus_bounds, unit_gdf, [layer["gdf"] for layer in source_layers])
    legend_labels = _legend_labels_for_map(unit_gdf, source_layers)
    layout = compute_visual_extent_with_legend_collar(
        base_bounds,
        legend_labels=legend_labels,
        feature_layers=[unit_gdf, *[layer["gdf"] for layer in source_layers]],
    )
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

        unit_handles = _plot_comparison_units(ax, unit_gdf)
        handles.extend(unit_handles)
        handles.extend(source_handles)
        plotted.append(unit_gdf)

        _set_bounds(ax, layout["expanded_bounds"], pad_fraction=0.0)
        ax.set_title(_wrap_title(title), fontsize=9.3, pad=4)
        ax.set_axis_off()
        if handles:
            legend_kwargs = _legend_kwargs_for_layout(layout)
            ax.legend(
                handles=_dedupe_handles(handles),
                loc=legend_kwargs["loc"],
                bbox_to_anchor=legend_kwargs["bbox_to_anchor"],
                ncol=legend_kwargs["ncol"],
                frameon=True,
                framealpha=0.84,
                facecolor="white",
                edgecolor="#AFAFAF",
                fontsize=5.4,
                title="Layers",
                title_fontsize=5.5,
                borderpad=0.35,
                labelspacing=0.25,
                handlelength=1.15,
                handletextpad=0.45,
            )
        _add_north_arrow(ax, layout)
        _add_scale_bar(ax, analysis_crs, layout)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.subplots_adjust(left=0.015, right=0.985, top=0.94, bottom=0.015)
        fig.savefig(output_path, bbox_inches="tight", pad_inches=0.035, facecolor="white")
        return layout
    finally:
        plt.close(fig)


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
    expanded_bounds, collar_bounds, collar_fraction = _expanded_bounds_for_collar(base_bounds, side, labels)
    return _layout_record(side, base_bounds, expanded_bounds, collar_bounds, labels, collar_fraction=collar_fraction)


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
        expanded, collar, _fraction = _expanded_bounds_for_collar(base_bounds, side, legend_labels)
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
    max_len = min(max(len(label) for label in labels), MAX_LEGEND_LABEL_LENGTH)
    count = len(labels)
    if orientation == "side":
        return min(LEGEND_COLLAR_MAX_FRACTION, max(0.22, 0.18 + (max_len * 0.0045)))
    return min(LEGEND_COLLAR_MAX_FRACTION, max(0.18, 0.11 + min(count, 8) * 0.025))


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
    for index, (_, row) in enumerate(gdf.iterrows()):
        unit_id = _row_text(row, "comparison_unit_id") or f"comparison-unit-{index + 1:05d}"
        full_label = _comparison_unit_label(row, index)
        label = _compact_comparison_unit_label(full_label, index)
        original_style_color = _row_text(row, "style_color")
        color = _kml_color_to_visible_hex(original_style_color)
        style_source = "kml_style_color"
        if color is None:
            color = _fallback_comparison_unit_color(unit_id or label, index)
            style_source = "deterministic_fallback"
        records.append(
            {
                "comparison_unit_id": unit_id,
                "label": label,
                "full_label": full_label,
                "color": color,
                "line_width": COMPARISON_UNIT_LINE_WIDTH,
                "style_source": style_source,
                "original_style_color": original_style_color,
            }
        )
    return records


def _plot_comparison_units(ax: Any, gdf: gpd.GeoDataFrame) -> list[Any]:
    if gdf.empty:
        return []
    handles: list[Any] = []
    styles = comparison_unit_style_records(gdf)
    for index, (_, row) in enumerate(gdf.iterrows()):
        geometry = row.geometry
        if geometry is None or geometry.is_empty:
            continue
        style = styles[index]
        geometry_column = getattr(gdf.geometry, "name", "geometry")
        properties = row.drop(labels=[geometry_column]).to_dict() if geometry_column in row.index else row.to_dict()
        properties.pop("geometry", None)
        one = gpd.GeoDataFrame([properties], geometry=[geometry], crs=gdf.crs)
        label = str(style["label"])
        color = str(style["color"])
        geom_type = geometry.geom_type
        if "Polygon" in geom_type:
            one.plot(ax=ax, facecolor=color, edgecolor="white", linewidth=1.45, alpha=0.18, zorder=6)
            one.plot(ax=ax, facecolor=color, edgecolor=color, linewidth=0.75, alpha=0.16, zorder=6.2)
            handles.append(Patch(facecolor=color, edgecolor=color, alpha=0.12, label=label))
        elif "LineString" in geom_type:
            width = float(style["line_width"])
            one.plot(ax=ax, color="white", linewidth=width + 0.82, alpha=0.88, zorder=6.8)
            one.plot(ax=ax, color=color, linewidth=width, alpha=0.92, zorder=7)
            handles.append(Line2D([0], [0], color=color, lw=width, label=label))
        elif "Point" in geom_type:
            one.plot(ax=ax, color="white", markersize=26, alpha=0.88, zorder=7.8)
            one.plot(ax=ax, color=color, markersize=18, alpha=0.92, zorder=8)
            handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markersize=4.8, label=label))
    return handles


def source_layer_style_record(layer: dict[str, Any], index: int) -> dict[str, Any]:
    source_id = str(layer.get("source_id") or "")
    override = SOURCE_STYLE_OVERRIDES.get(source_id, {})
    color = str(override.get("color") or SOURCE_CATEGORY_COLORS.get(str(layer.get("source_category", ""))) or _source_color(index))
    marker = str(override.get("marker") or _source_marker(index))
    feature_count = _feature_count(layer.get("gdf"))
    marker_size = 15 if feature_count <= 50 else 12 if feature_count <= 200 else 9
    return {
        "source_id": source_id,
        "label": legend_label_for_layer(layer),
        "color": color,
        "marker": marker,
        "line_width": 0.52,
        "line_alpha": 0.52,
        "polygon_alpha": 0.18,
        "polygon_line_width": 0.35,
        "marker_size": marker_size,
        "point_alpha": 0.74,
        "style_source": "source_id_override" if override else "category_or_sequence",
    }


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
    color = str(style.get("color") or "#6BAA75")
    label = str(style.get("label") or "Source layer")
    marker = str(style.get("marker") or "o")
    polygon_gdf = gdf[gdf.geometry.geom_type.str.contains("Polygon", na=False)]
    line_gdf = gdf[gdf.geometry.geom_type.str.contains("LineString", na=False)]
    point_gdf = gdf[gdf.geometry.geom_type.str.contains("Point", na=False)]
    if not polygon_gdf.empty:
        if is_project:
            polygon_gdf.plot(ax=ax, facecolor="none", edgecolor=color, linewidth=1.15, zorder=5)
            handles.append(Patch(facecolor="none", edgecolor=color, label=label))
        else:
            polygon_gdf.plot(
                ax=ax,
                facecolor=color,
                edgecolor=color,
                linewidth=float(style.get("polygon_line_width", 0.35)),
                alpha=float(style.get("polygon_alpha", 0.18)),
                zorder=3,
            )
            handles.append(Patch(facecolor=color, edgecolor=color, alpha=0.2, label=label))
    if not line_gdf.empty:
        width = 1.45 if is_project else float(style.get("line_width", 0.52))
        alpha = 0.9 if is_project else float(style.get("line_alpha", 0.52))
        line_gdf.plot(ax=ax, color=color, linewidth=width, alpha=alpha, zorder=6 if is_project else 4)
        handles.append(Line2D([0], [0], color=color, lw=width, label=label))
    if not point_gdf.empty:
        size = 26 if is_project else float(style.get("marker_size", 15))
        if not is_project:
            point_gdf.plot(ax=ax, marker=marker, color="white", markersize=size + 7, alpha=0.76, zorder=4.8)
        point_gdf.plot(ax=ax, marker=marker, color=color, markersize=size, alpha=0.9 if is_project else float(style.get("point_alpha", 0.74)), zorder=7 if is_project else 5)
        handles.append(Line2D([0], [0], marker=marker, color="none", markerfacecolor=color, markeredgecolor="#333333", markeredgewidth=0.4, markersize=4.8, label=label))
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


def _fallback_comparison_unit_color(key: str, index: int) -> str:
    if index < len(COMPARISON_UNIT_FALLBACK_COLORS):
        return COMPARISON_UNIT_FALLBACK_COLORS[index]
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return COMPARISON_UNIT_FALLBACK_COLORS[int(digest[:8], 16) % len(COMPARISON_UNIT_FALLBACK_COLORS)]


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
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float], float]:
    west, south, east, north = bounds
    width = max(east - west, 1.0)
    height = max(north - south, 1.0)
    orientation = "side" if side in {"left", "right"} else "horizontal"
    fraction = estimate_legend_box_fraction(legend_labels, orientation=orientation)
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
    return expanded, collar, fraction


def _layout_record(
    side: str,
    base_bounds: tuple[float, float, float, float],
    expanded_bounds: tuple[float, float, float, float],
    collar_bounds: tuple[float, float, float, float] | None,
    legend_labels: list[str],
    *,
    collar_fraction: float = 0.0,
) -> dict[str, Any]:
    return {
        "layout_strategy": "outside_frame_legend" if side == "outside_frame" else "legend_collar" if side != "none" else "no_legend_collar",
        "legend_side": side,
        "render_extent_type": FIGURE_RENDER_EXTENT,
        "render_extent_is_presentation_only": True,
        "presentation_extent_type": PRESENTATION_ONLY_COLLAR_EXTENT if collar_bounds else "",
        "base_bounds": [float(value) for value in base_bounds],
        "expanded_bounds": [float(value) for value in expanded_bounds],
        "collar_bounds": [float(value) for value in collar_bounds] if collar_bounds else [],
        "legend_label_count": len(legend_labels),
        "legend_labels": legend_labels,
        "collar_fraction": round(float(collar_fraction), 4),
        "legend_bbox_axes": _legend_bbox_axes(expanded_bounds, collar_bounds, side) if collar_bounds else [],
    }


def _legend_bbox_axes(
    expanded_bounds: tuple[float, float, float, float],
    collar_bounds: tuple[float, float, float, float],
    side: str,
) -> list[float]:
    west, south, east, north = expanded_bounds
    cw, cs, ce, cn = collar_bounds
    width = max(east - west, 1.0)
    height = max(north - south, 1.0)
    x0 = (cw - west) / width
    y0 = (cs - south) / height
    x1 = (ce - west) / width
    y1 = (cn - south) / height
    pad = 0.014
    if side in {"right", "left"}:
        return [round(max(0.0, x0 + pad), 4), round(max(0.0, y0 + pad), 4), round(min(1.0, x1 - pad), 4), round(min(1.0, y1 - pad), 4)]
    return [round(max(0.0, x0 + pad), 4), round(max(0.0, y0 + pad), 4), round(min(1.0, x1 - pad), 4), round(min(1.0, y1 - pad), 4)]


def _legend_kwargs_for_layout(layout: dict[str, Any]) -> dict[str, Any]:
    side = str(layout.get("legend_side") or "none")
    bbox = layout.get("legend_bbox_axes") if isinstance(layout.get("legend_bbox_axes"), list) else []
    if len(bbox) != 4:
        return {"loc": "upper right", "bbox_to_anchor": (0.985, 0.985), "ncol": 1}
    x0, y0, x1, y1 = [float(value) for value in bbox]
    if side == "right":
        return {"loc": "upper left", "bbox_to_anchor": (x0, y1), "ncol": 1}
    if side == "left":
        return {"loc": "upper right", "bbox_to_anchor": (x1, y1), "ncol": 1}
    if side == "top":
        return {"loc": "lower left", "bbox_to_anchor": (x0, y0), "ncol": 2}
    if side == "bottom":
        return {"loc": "upper left", "bbox_to_anchor": (x0, y1), "ncol": 2}
    if side == "outside_frame":
        return {"loc": "upper left", "bbox_to_anchor": (1.01, 0.99), "ncol": 1}
    return {"loc": "upper right", "bbox_to_anchor": (0.985, 0.985), "ncol": 1}


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
    if side == "right":
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
    colors = ["#6BAA75", "#E45E5E", "#7A6FF0", "#D99A2B", "#3A8D8F", "#A35C9F"]
    return colors[index % len(colors)]


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
