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
COMPARISON_UNIT_LINE_WIDTH = 1.55
MAX_LEGEND_LABEL_LENGTH = 30

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
    "usfws_nwi_wetlands": "NWI wetlands",
    "usgs_nhd_flowlines": "NHD flowlines",
    "usgs_nhd_hydrography": "NHD hydrography",
    "usgs_nhd_other_areas": "NHD areas",
    "usgs_nhd_waterbodies": "NHD waterbodies",
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
) -> None:
    fig, ax = plt.subplots(figsize=_figure_size_for_bounds(focus_bounds), dpi=180)
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

        if focus_bounds is not None:
            _set_bounds(ax, focus_bounds)
        else:
            _set_extent(ax, plotted)
        ax.set_title(_wrap_title(title), fontsize=9.3, pad=4)
        ax.set_axis_off()
        if handles:
            ax.legend(
                handles=_dedupe_handles(handles),
                loc="upper right",
                frameon=True,
                framealpha=0.9,
                fontsize=5.7,
                title="Layers",
                title_fontsize=5.8,
                borderpad=0.35,
                labelspacing=0.25,
                handlelength=1.35,
                handletextpad=0.45,
            )
        _add_north_arrow(ax)
        _add_scale_bar(ax, analysis_crs)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.subplots_adjust(left=0.015, right=0.985, top=0.94, bottom=0.015)
        fig.savefig(output_path, bbox_inches="tight", pad_inches=0.035, facecolor="white")
    finally:
        plt.close(fig)


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
            one.plot(ax=ax, facecolor=color, edgecolor="white", linewidth=2.2, alpha=0.2, zorder=6)
            one.plot(ax=ax, facecolor=color, edgecolor=color, linewidth=1.05, alpha=0.18, zorder=6.2)
            handles.append(Patch(facecolor=color, edgecolor=color, alpha=0.14, label=label))
        elif "LineString" in geom_type:
            width = float(style["line_width"])
            one.plot(ax=ax, color="white", linewidth=width + 1.15, alpha=0.92, zorder=6.8)
            one.plot(ax=ax, color=color, linewidth=width, alpha=0.96, zorder=7)
            handles.append(Line2D([0], [0], color=color, lw=width, label=label))
        elif "Point" in geom_type:
            one.plot(ax=ax, color="white", markersize=34, alpha=0.92, zorder=7.8)
            one.plot(ax=ax, color=color, markersize=24, alpha=0.96, zorder=8)
            handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markersize=5.5, label=label))
    return handles


def source_layer_style_record(layer: dict[str, Any], index: int) -> dict[str, Any]:
    source_id = str(layer.get("source_id") or "")
    override = SOURCE_STYLE_OVERRIDES.get(source_id, {})
    color = str(override.get("color") or SOURCE_CATEGORY_COLORS.get(str(layer.get("source_category", ""))) or _source_color(index))
    marker = str(override.get("marker") or _source_marker(index))
    return {
        "source_id": source_id,
        "label": legend_label_for_layer(layer),
        "color": color,
        "marker": marker,
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
            polygon_gdf.plot(ax=ax, facecolor="none", edgecolor=color, linewidth=1.5, zorder=5)
            handles.append(Patch(facecolor="none", edgecolor=color, label=label))
        else:
            polygon_gdf.plot(ax=ax, facecolor=color, edgecolor=color, linewidth=0.45, alpha=0.22, zorder=3)
            handles.append(Patch(facecolor=color, edgecolor=color, alpha=0.25, label=label))
    if not line_gdf.empty:
        width = 2.0 if is_project else 0.85
        line_gdf.plot(ax=ax, color=color, linewidth=width, alpha=0.94 if is_project else 0.58, zorder=6 if is_project else 4)
        handles.append(Line2D([0], [0], color=color, lw=width, label=label))
    if not point_gdf.empty:
        size = 34 if is_project else 22
        if not is_project:
            point_gdf.plot(ax=ax, marker=marker, color="white", markersize=size + 10, alpha=0.82, zorder=4.8)
        point_gdf.plot(ax=ax, marker=marker, color=color, markersize=size, alpha=0.94 if is_project else 0.78, zorder=7 if is_project else 5)
        handles.append(Line2D([0], [0], marker=marker, color="none", markerfacecolor=color, markeredgecolor="#333333", markeredgewidth=0.45, markersize=5.5, label=label))
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


def _set_bounds(ax: Any, bounds: Any) -> None:
    west, south, east, north = [float(value) for value in bounds]
    width = east - west
    height = north - south
    pad_x = width * 0.055 if width > 0 else 250
    pad_y = height * 0.055 if height > 0 else 250
    ax.set_xlim(west - pad_x, east + pad_x)
    ax.set_ylim(south - pad_y, north + pad_y)
    ax.set_aspect("equal", adjustable="box")


def _add_north_arrow(ax: Any) -> None:
    ax.annotate(
        "N",
        xy=(0.94, 0.90),
        xytext=(0.94, 0.79),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "color": "#2B2B2B", "lw": 1.0},
        bbox={"facecolor": "white", "edgecolor": "#BDBDBD", "alpha": 0.9, "pad": 1.5},
    )


def _add_scale_bar(ax: Any, analysis_crs: str) -> None:
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
    x0 = x_min + width * 0.08
    y0 = y_min + height * 0.08
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
    return text[: max_length - 1].rstrip() + "…"
