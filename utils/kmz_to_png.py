"""Create quick PNG previews from KMZ/KML files.

This is intentionally lightweight and dependency-free. It is meant for early
local inspection before the project commits to a GIS stack such as GeoPandas.
"""

from __future__ import annotations

import argparse
import binascii
import math
import re
import struct
import zipfile
import zlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


Color = tuple[int, int, int, int]
Coord = tuple[float, float]

PALETTE: list[Color] = [
    (214, 39, 40, 255),
    (31, 119, 180, 255),
    (44, 160, 44, 255),
    (255, 127, 14, 255),
    (148, 103, 189, 255),
    (140, 86, 75, 255),
    (227, 119, 194, 255),
    (127, 127, 127, 255),
    (188, 189, 34, 255),
    (23, 190, 207, 255),
]


@dataclass
class Style:
    line_color: Color | None = None
    poly_color: Color | None = None
    icon_color: Color | None = None
    icon_href: str | None = None
    line_width: float = 2.0


@dataclass
class Geometry:
    kind: str
    coords: list[Coord]
    holes: list[list[Coord]] = field(default_factory=list)


@dataclass
class Feature:
    name: str
    style_url: str | None
    geometries: list[Geometry]


@dataclass
class KmlData:
    source_file: Path
    kml_entries: list[str]
    features: list[Feature]
    styles: dict[str, Style]
    style_maps: dict[str, str]


class Canvas:
    def __init__(self, width: int, height: int, background: Color = (248, 248, 246, 255)) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray(background * (width * height))

    def blend_pixel(self, x: int, y: int, color: Color) -> None:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        r, g, b, a = color
        if a <= 0:
            return
        i = (y * self.width + x) * 4
        if a >= 255:
            self.pixels[i : i + 4] = bytes((r, g, b, 255))
            return
        inv = 255 - a
        self.pixels[i] = (r * a + self.pixels[i] * inv) // 255
        self.pixels[i + 1] = (g * a + self.pixels[i + 1] * inv) // 255
        self.pixels[i + 2] = (b * a + self.pixels[i + 2] * inv) // 255
        self.pixels[i + 3] = 255

    def draw_circle(self, cx: int, cy: int, radius: int, color: Color) -> None:
        r2 = radius * radius
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                    self.blend_pixel(x, y, color)

    def draw_line(self, start: tuple[int, int], end: tuple[int, int], color: Color, width: int = 2) -> None:
        x0, y0 = start
        x1, y1 = end
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        radius = max(1, width // 2)
        for step in range(steps + 1):
            x = round(x0 + dx * step / steps)
            y = round(y0 + dy * step / steps)
            self.draw_circle(x, y, radius, color)

    def draw_polyline(self, points: list[tuple[int, int]], color: Color, width: int = 2) -> None:
        for start, end in zip(points, points[1:]):
            self.draw_line(start, end, color, width)

    def fill_polygon(self, points: list[tuple[int, int]], color: Color) -> None:
        if len(points) < 3:
            return
        min_y = max(min(y for _, y in points), 0)
        max_y = min(max(y for _, y in points), self.height - 1)
        for y in range(min_y, max_y + 1):
            intersections: list[int] = []
            for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
                if y1 == y2:
                    continue
                if y < min(y1, y2) or y >= max(y1, y2):
                    continue
                x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                intersections.append(round(x))
            intersections.sort()
            for x1, x2 in zip(intersections[0::2], intersections[1::2]):
                for x in range(max(x1, 0), min(x2, self.width - 1) + 1):
                    self.blend_pixel(x, y, color)

    def write_png(self, path: Path) -> None:
        def chunk(kind: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + kind
                + data
                + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
            )

        rows = bytearray()
        stride = self.width * 4
        for y in range(self.height):
            rows.append(0)
            rows.extend(self.pixels[y * stride : (y + 1) * stride])

        raw = b"".join(
            [
                b"\x89PNG\r\n\x1a\n",
                chunk(b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 6, 0, 0, 0)),
                chunk(b"IDAT", zlib.compress(bytes(rows), level=6)),
                chunk(b"IEND", b""),
            ]
        )
        path.write_bytes(raw)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def descendant_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def descendants(element: ET.Element, name: str) -> Iterable[ET.Element]:
    for child in element.iter():
        if local_name(child.tag) == name:
            yield child


def kml_color_to_rgba(value: str | None) -> Color | None:
    if not value:
        return None
    value = value.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{8}", value):
        return None
    # KML colors are aabbggrr.
    alpha = int(value[0:2], 16)
    blue = int(value[2:4], 16)
    green = int(value[4:6], 16)
    red = int(value[6:8], 16)
    return (red, green, blue, alpha)


def visible_color(color: Color | None, fallback: Color) -> Color:
    if color is None or color[3] < 32:
        return fallback
    red, green, blue, alpha = color
    if red > 238 and green > 238 and blue > 238:
        return (35, 35, 35, 255)
    return (red, green, blue, max(alpha, 160))


def parse_coordinates(text: str | None) -> list[Coord]:
    if not text:
        return []
    coords: list[Coord] = []
    for token in text.replace("\n", " ").replace("\t", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        coords.append((lon, lat))
    return coords


def style_key(style_url: str | None) -> str | None:
    if not style_url:
        return None
    return style_url.strip().removeprefix("#")


def parse_style(style_element: ET.Element) -> tuple[str, Style] | None:
    style_id = style_element.attrib.get("id")
    if not style_id:
        return None

    style = Style()
    for child in style_element:
        name = local_name(child.tag)
        if name == "LineStyle":
            style.line_color = kml_color_to_rgba(child_text(child, "color"))
            width_text = child_text(child, "width")
            if width_text:
                try:
                    style.line_width = float(width_text)
                except ValueError:
                    style.line_width = 2.0
        elif name == "PolyStyle":
            style.poly_color = kml_color_to_rgba(child_text(child, "color"))
        elif name == "IconStyle":
            style.icon_color = kml_color_to_rgba(child_text(child, "color"))
            href = descendant_text(child, "href")
            if href:
                style.icon_href = href
    return style_id, style


def parse_style_map(style_map: ET.Element) -> tuple[str, str] | None:
    map_id = style_map.attrib.get("id")
    if not map_id:
        return None

    first_style_url: str | None = None
    normal_style_url: str | None = None
    for pair in style_map:
        if local_name(pair.tag) != "Pair":
            continue
        key = child_text(pair, "key")
        url = child_text(pair, "styleUrl")
        if url and first_style_url is None:
            first_style_url = url
        if key == "normal" and url:
            normal_style_url = url

    target = style_key(normal_style_url or first_style_url)
    if target:
        return map_id, target
    return None


def parse_polygon(polygon: ET.Element) -> Geometry | None:
    rings: list[list[Coord]] = []
    for ring in descendants(polygon, "LinearRing"):
        coords = parse_coordinates(descendant_text(ring, "coordinates"))
        if coords:
            rings.append(coords)
    if not rings:
        return None
    return Geometry("Polygon", rings[0], rings[1:])


def parse_feature(placemark: ET.Element) -> Feature | None:
    name = child_text(placemark, "name") or ""
    style_url = child_text(placemark, "styleUrl")
    geometries: list[Geometry] = []

    for geom in placemark.iter():
        geom_type = local_name(geom.tag)
        if geom_type == "Point":
            coords = parse_coordinates(descendant_text(geom, "coordinates"))
            if coords:
                geometries.append(Geometry("Point", coords[:1]))
        elif geom_type == "LineString":
            coords = parse_coordinates(descendant_text(geom, "coordinates"))
            if coords:
                geometries.append(Geometry("LineString", coords))
        elif geom_type == "Polygon":
            polygon = parse_polygon(geom)
            if polygon:
                geometries.append(polygon)

    if not geometries:
        return None
    return Feature(name=name, style_url=style_url, geometries=geometries)


def decode_xml(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_kml_documents(path: Path) -> list[tuple[str, str]]:
    if path.suffix.lower() == ".kmz":
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith(".kml")]
            documents = []
            for name in names:
                documents.append((name, decode_xml(archive.read(name))))
            return documents
    return [(path.name, decode_xml(path.read_bytes()))]


def parse_kml_file(path: Path) -> KmlData:
    kml_docs = read_kml_documents(path)
    all_features: list[Feature] = []
    all_styles: dict[str, Style] = {}
    all_style_maps: dict[str, str] = {}

    for _, kml_text in kml_docs:
        root = ET.fromstring(kml_text)
        for style_element in descendants(root, "Style"):
            parsed = parse_style(style_element)
            if parsed:
                style_id, style = parsed
                all_styles[style_id] = style
        for style_map in descendants(root, "StyleMap"):
            parsed = parse_style_map(style_map)
            if parsed:
                map_id, target = parsed
                all_style_maps[map_id] = target
        for placemark in descendants(root, "Placemark"):
            feature = parse_feature(placemark)
            if feature:
                all_features.append(feature)

    return KmlData(
        source_file=path,
        kml_entries=[name for name, _ in kml_docs],
        features=all_features,
        styles=all_styles,
        style_maps=all_style_maps,
    )


def all_coords(features: list[Feature]) -> list[Coord]:
    coords: list[Coord] = []
    for feature in features:
        for geometry in feature.geometries:
            coords.extend(geometry.coords)
            for hole in geometry.holes:
                coords.extend(hole)
    return coords


def projected_bounds(coords: list[Coord]) -> tuple[float, float, float, float, float]:
    min_lon = min(lon for lon, _ in coords)
    max_lon = max(lon for lon, _ in coords)
    min_lat = min(lat for _, lat in coords)
    max_lat = max(lat for _, lat in coords)
    mid_lat = (min_lat + max_lat) / 2
    lon_scale = max(math.cos(math.radians(mid_lat)), 0.2)

    projected = [(lon * lon_scale, lat) for lon, lat in coords]
    min_x = min(x for x, _ in projected)
    max_x = max(x for x, _ in projected)
    min_y = min(y for _, y in projected)
    max_y = max(y for _, y in projected)

    if math.isclose(min_x, max_x):
        min_x -= 0.01
        max_x += 0.01
    if math.isclose(min_y, max_y):
        min_y -= 0.01
        max_y += 0.01
    return min_x, min_y, max_x, max_y, lon_scale


def resolve_style(style_url: str | None, styles: dict[str, Style], style_maps: dict[str, str]) -> tuple[str | None, Style | None]:
    key = style_key(style_url)
    visited: set[str] = set()
    while key in style_maps and key not in visited:
        visited.add(key)
        key = style_maps[key]
    if key and key in styles:
        return key, styles[key]
    return key, None


def fallback_color(key: str | None) -> Color:
    if not key:
        return PALETTE[0]
    index = sum(ord(char) for char in key) % len(PALETTE)
    return PALETTE[index]


def render_png(data: KmlData, output_path: Path, width: int, height: int) -> dict[str, object]:
    coords = all_coords(data.features)
    if not coords:
        raise ValueError(f"No coordinates found in {data.source_file}")

    min_x, min_y, max_x, max_y, lon_scale = projected_bounds(coords)
    margin = 70
    draw_width = width - margin * 2
    draw_height = height - margin * 2
    scale = min(draw_width / (max_x - min_x), draw_height / (max_y - min_y))
    offset_x = (width - (max_x - min_x) * scale) / 2
    offset_y = (height - (max_y - min_y) * scale) / 2

    def project(coord: Coord) -> tuple[int, int]:
        lon, lat = coord
        x = lon * lon_scale
        y = lat
        px = round(offset_x + (x - min_x) * scale)
        py = round(height - (offset_y + (y - min_y) * scale))
        return px, py

    canvas = Canvas(width, height)
    grid_color = (220, 220, 216, 255)
    frame_color = (120, 120, 116, 255)
    left = round(offset_x)
    right = round(offset_x + (max_x - min_x) * scale)
    top = round(height - offset_y - (max_y - min_y) * scale)
    bottom = round(height - offset_y)

    for i in range(6):
        x = round(left + (right - left) * i / 5)
        y = round(top + (bottom - top) * i / 5)
        canvas.draw_line((x, top), (x, bottom), grid_color, 1)
        canvas.draw_line((left, y), (right, y), grid_color, 1)
    canvas.draw_polyline([(left, top), (right, top), (right, bottom), (left, bottom), (left, top)], frame_color, 2)

    geometry_counts: Counter[str] = Counter()
    style_counts: Counter[str] = Counter()
    for feature in data.features:
        resolved_key, style = resolve_style(feature.style_url, data.styles, data.style_maps)
        style_counts[resolved_key or "(none)"] += 1
        base_color = fallback_color(resolved_key)
        for geometry in feature.geometries:
            geometry_counts[geometry.kind] += 1
            if geometry.kind == "Point":
                point_color = visible_color(style.icon_color if style else None, base_color)
                px, py = project(geometry.coords[0])
                canvas.draw_circle(px, py, 6, (255, 255, 255, 230))
                canvas.draw_circle(px, py, 4, point_color)
            elif geometry.kind == "LineString":
                line_color = visible_color(style.line_color if style else None, base_color)
                line_width = max(2, min(round(style.line_width if style else 2.0) + 2, 8))
                canvas.draw_polyline([project(coord) for coord in geometry.coords], line_color, line_width)
            elif geometry.kind == "Polygon":
                polygon_color = visible_color(style.poly_color if style else None, (*base_color[:3], 80))
                fill = (*polygon_color[:3], min(polygon_color[3], 90))
                points = [project(coord) for coord in geometry.coords]
                canvas.fill_polygon(points, fill)
                canvas.draw_polyline(points + points[:1], (*polygon_color[:3], 230), 2)
                for hole in geometry.holes:
                    hole_points = [project(coord) for coord in hole]
                    canvas.draw_polyline(hole_points + hole_points[:1], (90, 90, 90, 180), 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.write_png(output_path)

    lon_values = [lon for lon, _ in coords]
    lat_values = [lat for _, lat in coords]
    return {
        "features": len(data.features),
        "geometries": dict(geometry_counts),
        "styles": dict(style_counts),
        "bounds": {
            "west": min(lon_values),
            "south": min(lat_values),
            "east": max(lon_values),
            "north": max(lat_values),
        },
    }


def iter_input_files(paths: list[Path]) -> list[Path]:
    if not paths:
        return sorted([*Path.cwd().glob("*.kmz"), *Path.cwd().glob("*.kml")])

    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(sorted(path.rglob("*.kmz")))
            found.extend(sorted(path.rglob("*.kml")))
        elif path.suffix.lower() in {".kmz", ".kml"}:
            found.append(path)
    return found


def write_summary(output_dir: Path, summaries: list[tuple[Path, Path, dict[str, object], KmlData]]) -> None:
    lines = ["# KMZ/KML Preview Summary", ""]
    for source_path, png_path, summary, data in summaries:
        bounds = summary["bounds"]
        assert isinstance(bounds, dict)
        lines.extend(
            [
                f"## {source_path.name}",
                "",
                f"- Preview: `{png_path}`",
                f"- KML entries: {', '.join(data.kml_entries)}",
                f"- Placemarks with geometry: {summary['features']}",
                f"- Geometry counts: {summary['geometries']}",
                (
                    "- Bounds: "
                    f"west {bounds['west']:.6f}, south {bounds['south']:.6f}, "
                    f"east {bounds['east']:.6f}, north {bounds['north']:.6f}"
                ),
                "",
            ]
        )
    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render KMZ/KML files to simple PNG previews.")
    parser.add_argument("inputs", nargs="*", type=Path, help="KMZ/KML files or directories. Defaults to repo-root files.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/kmz_previews"))
    parser.add_argument("--width", type=int, default=1800)
    parser.add_argument("--height", type=int, default=1400)
    args = parser.parse_args()

    files = iter_input_files(args.inputs)
    if not files:
        print("No KMZ or KML files found.")
        return 1

    summaries: list[tuple[Path, Path, dict[str, object], KmlData]] = []
    for file_path in files:
        data = parse_kml_file(file_path)
        output_path = args.output_dir / f"{file_path.stem}.png"
        summary = render_png(data, output_path, args.width, args.height)
        summaries.append((file_path, output_path, summary, data))
        print(f"Wrote {output_path} from {file_path} ({summary['features']} placemarks).")

    write_summary(args.output_dir, summaries)
    print(f"Wrote {args.output_dir / 'summary.md'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

