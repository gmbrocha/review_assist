"""Matplotlib rendering and layout helpers for deliverable figures."""

from __future__ import annotations

import hashlib
import re
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
    "#2F80ED",
    "#D55E00",
    "#009E73",
    "#9B51E0",
    "#EB5757",
    "#0072B2",
    "#CC79A7",
    "#7A5C00",
]
COMPARISON_UNIT_LINE_WIDTH = 1.15


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
    fig, ax = plt.subplots(figsize=(6.5, 4.25), dpi=180)
    try:
        handles: list[Any] = []
        plotted: list[gpd.GeoDataFrame] = []
        if basemap and isinstance(basemap.get("layer"), dict):
            layer = basemap["layer"]
            ax.imshow(layer["image"], extent=layer["extent"], alpha=0.78, zorder=0)

        source_handles: list[Any] = []
        for index, layer in enumerate(source_layers):
            gdf = layer["gdf"]
            color = SOURCE_CATEGORY_COLORS.get(str(layer.get("source_category", "")), _source_color(index))
            label = str(layer.get("source_name") or layer.get("source_id") or "Source layer")
            source_handles.extend(_plot_gdf(ax, gdf, color=color, label=label, is_project=False))
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
        ax.set_title(title, fontsize=10, pad=7)
        ax.set_axis_off()
        if handles:
            ax.legend(handles=_dedupe_handles(handles), loc="upper left", frameon=True, framealpha=0.94, fontsize=6.2, title="Mapped layers", title_fontsize=6.4)
        _add_north_arrow(ax)
        _add_scale_bar(ax, analysis_crs)
        if source_note:
            ax.text(
                0.01,
                0.01,
                source_note,
                transform=ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=5.8,
                color="#333333",
                bbox={"facecolor": "white", "edgecolor": "#D0D0D0", "alpha": 0.9, "pad": 2},
            )
        ax.text(
            0.99,
            0.01,
            "Draft / Pre-Review\n" + method_note,
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=5.8,
            color="#333333",
            bbox={"facecolor": "white", "edgecolor": "#BDBDBD", "alpha": 0.9, "pad": 2},
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, bbox_inches="tight", facecolor="white")
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
        label = _comparison_unit_label(row, index)
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
            one.plot(ax=ax, facecolor=color, edgecolor=color, linewidth=0.9, alpha=0.14, zorder=6)
            handles.append(Patch(facecolor=color, edgecolor=color, alpha=0.14, label=label))
        elif "LineString" in geom_type:
            width = float(style["line_width"])
            one.plot(ax=ax, color=color, linewidth=width, alpha=0.92, zorder=7)
            handles.append(Line2D([0], [0], color=color, lw=width, label=label))
        elif "Point" in geom_type:
            one.plot(ax=ax, color=color, markersize=28, alpha=0.92, zorder=8)
            handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markersize=5.5, label=label))
    return handles


def _plot_gdf(ax: Any, gdf: gpd.GeoDataFrame, *, color: str, label: str, is_project: bool) -> list[Any]:
    if gdf.empty:
        return []
    handles: list[Any] = []
    polygon_gdf = gdf[gdf.geometry.geom_type.str.contains("Polygon", na=False)]
    line_gdf = gdf[gdf.geometry.geom_type.str.contains("LineString", na=False)]
    point_gdf = gdf[gdf.geometry.geom_type.str.contains("Point", na=False)]
    if not polygon_gdf.empty:
        if is_project:
            polygon_gdf.plot(ax=ax, facecolor="none", edgecolor=color, linewidth=1.5, zorder=5)
            handles.append(Patch(facecolor="none", edgecolor=color, label=label))
        else:
            polygon_gdf.plot(ax=ax, facecolor=color, edgecolor=color, linewidth=0.6, alpha=0.32, zorder=3)
            handles.append(Patch(facecolor=color, edgecolor=color, alpha=0.32, label=label))
    if not line_gdf.empty:
        width = 2.0 if is_project else 1.1
        line_gdf.plot(ax=ax, color=color, linewidth=width, alpha=0.94 if is_project else 0.7, zorder=6 if is_project else 4)
        handles.append(Line2D([0], [0], color=color, lw=width, label=label))
    if not point_gdf.empty:
        size = 34 if is_project else 20
        point_gdf.plot(ax=ax, color=color, markersize=size, alpha=0.94 if is_project else 0.72, zorder=7 if is_project else 5)
        handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markersize=5.5, label=label))
    return handles[:1]


def _comparison_unit_label(row: Any, index: int) -> str:
    for column in ("comparison_unit_name", "comparison_unit_group", "candidate_label", "placemark_name", "style_url"):
        value = _row_text(row, column)
        if value and value.lower() != "multiple":
            return value
    unit_id = _row_text(row, "comparison_unit_id")
    return unit_id or f"Comparison unit {index + 1}"


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
    pad_x = width * 0.08 if width > 0 else 250
    pad_y = height * 0.08 if height > 0 else 250
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
