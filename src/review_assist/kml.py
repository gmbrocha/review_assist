"""KMZ/KML ingestion utilities backed by GeoPandas data structures."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry

from .validation import ValidationIssue


SUPPORTED_SUFFIXES = {".kml", ".kmz"}
GEOMETRY_TAGS = {"Point", "LineString", "Polygon"}
UNSUPPORTED_GEOMETRY_TAGS = {"Model", "Track", "MultiTrack"}


class IngestionError(RuntimeError):
    """Raised when a KML/KMZ input cannot be ingested."""


@dataclass(frozen=True)
class KmlDocument:
    entry_name: str
    text: str


@dataclass(frozen=True)
class IngestedInput:
    source_path: Path
    kml_entries: list[str]
    placemark_count: int
    geo_data_frame: gpd.GeoDataFrame
    issues: list[ValidationIssue]


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


def parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def decode_xml(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_kml_documents(path: Path) -> list[KmlDocument]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise IngestionError(f"Unsupported input type '{path.suffix}' for {path}")
    if suffix == ".kmz":
        try:
            with zipfile.ZipFile(path) as archive:
                names = [name for name in archive.namelist() if name.lower().endswith(".kml")]
                if not names:
                    raise IngestionError(f"No KML documents found inside KMZ: {path}")
                return [KmlDocument(name, decode_xml(archive.read(name))) for name in names]
        except zipfile.BadZipFile as exc:
            raise IngestionError(f"Invalid KMZ file: {path}") from exc
    return [KmlDocument(path.name, decode_xml(path.read_bytes()))]


def parse_coordinates(text: str | None) -> list[tuple[float, float]]:
    if not text:
        return []
    coords: list[tuple[float, float]] = []
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


def parse_point(point: ET.Element) -> Point | None:
    coords = parse_coordinates(descendant_text(point, "coordinates"))
    if not coords:
        return None
    return Point(coords[0])


def parse_line(line: ET.Element) -> LineString | None:
    coords = parse_coordinates(descendant_text(line, "coordinates"))
    if len(coords) < 2:
        return None
    return LineString(coords)


def parse_polygon(polygon: ET.Element) -> Polygon | None:
    rings: list[list[tuple[float, float]]] = []
    for ring in descendants(polygon, "LinearRing"):
        coords = parse_coordinates(descendant_text(ring, "coordinates"))
        if coords:
            rings.append(coords)
    if not rings:
        return None
    shell = rings[0]
    holes = rings[1:] if len(rings) > 1 else None
    return Polygon(shell=shell, holes=holes)


def geometry_elements(placemark: ET.Element) -> Iterable[tuple[str, ET.Element]]:
    for element in placemark.iter():
        name = local_name(element.tag)
        if name in GEOMETRY_TAGS:
            yield name, element


def clean_label(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def style_color_lookup(root: ET.Element) -> dict[str, str]:
    styles: dict[str, str] = {}
    style_maps: dict[str, str] = {}
    for element in root.iter():
        if local_name(element.tag) != "Style":
            continue
        style_id = element.attrib.get("id", "").strip()
        if not style_id:
            continue
        color = first_style_color(element)
        if color:
            styles[f"#{style_id}"] = color

    for element in root.iter():
        if local_name(element.tag) != "StyleMap":
            continue
        style_map_id = element.attrib.get("id", "").strip()
        if not style_map_id:
            continue
        mapped_url = style_map_url(element)
        color = styles.get(mapped_url, "")
        if color:
            style_maps[f"#{style_map_id}"] = color

    return {**styles, **style_maps}


def first_style_color(style: ET.Element) -> str:
    for child in style.iter():
        if local_name(child.tag) == "color" and child.text:
            return clean_label(child.text)
    return ""


def style_map_url(style_map: ET.Element) -> str:
    fallback = ""
    for pair in style_map:
        if local_name(pair.tag) != "Pair":
            continue
        key = child_text(pair, "key")
        url = clean_label(child_text(pair, "styleUrl"))
        if not url:
            continue
        if key == "normal":
            return url
        if not fallback:
            fallback = url
    return fallback


def folder_path_for(placemark: ET.Element, parents: dict[ET.Element, ET.Element]) -> list[str]:
    folders: list[str] = []
    current = parents.get(placemark)
    while current is not None:
        if local_name(current.tag) == "Folder":
            folder_name = clean_label(child_text(current, "name"))
            if folder_name:
                folders.append(folder_name)
        current = parents.get(current)
    return list(reversed(folders))


def selected_folder_group(folder_path: list[str]) -> str:
    for folder_name in folder_path:
        if _is_meaningful_folder_name(folder_name):
            return folder_name
    return ""


def _is_meaningful_folder_name(value: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", value.strip().lower())
    if not normalized:
        return False
    return normalized not in {
        "0",
        "00",
        "default",
        "folder",
        "folders",
        "layer",
        "layers",
        "level",
        "levels",
    }


def parse_kml_document(source_path: Path, document: KmlDocument) -> tuple[list[dict[str, object]], list[BaseGeometry], int, list[ValidationIssue]]:
    rows: list[dict[str, object]] = []
    geometries: list[BaseGeometry] = []
    issues: list[ValidationIssue] = []
    try:
        root = ET.fromstring(document.text)
    except ET.ParseError as exc:
        raise IngestionError(f"Invalid KML XML in {source_path}:{document.entry_name}: {exc}") from exc

    parents = parent_map(root)
    style_colors = style_color_lookup(root)
    placemarks = list(descendants(root, "Placemark"))
    blank_name_count = 0
    for placemark_index, placemark in enumerate(placemarks):
        placemark_name = clean_label(child_text(placemark, "name"))
        style_url = clean_label(child_text(placemark, "styleUrl"))
        folders = folder_path_for(placemark, parents)
        folder_path = " > ".join(folders)
        folder_group = selected_folder_group(folders)
        style_color = style_colors.get(style_url, "")
        if not placemark_name:
            blank_name_count += 1

        unsupported = sorted({local_name(element.tag) for element in placemark.iter() if local_name(element.tag) in UNSUPPORTED_GEOMETRY_TAGS})
        for tag in unsupported:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="unsupported_geometry",
                    message=f"Unsupported KML geometry tag encountered: {tag}",
                    location=f"{document.entry_name}:Placemark[{placemark_index}]",
                )
            )

        parsed_for_placemark = 0
        for geometry_index, (geometry_kind, element) in enumerate(geometry_elements(placemark)):
            geometry: BaseGeometry | None
            if geometry_kind == "Point":
                geometry = parse_point(element)
            elif geometry_kind == "LineString":
                geometry = parse_line(element)
            elif geometry_kind == "Polygon":
                geometry = parse_polygon(element)
            else:
                geometry = None

            if geometry is None or geometry.is_empty:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="empty_geometry",
                        message=f"{geometry_kind} geometry is empty or invalid.",
                        location=f"{document.entry_name}:Placemark[{placemark_index}]:Geometry[{geometry_index}]",
                    )
                )
                continue

            parsed_for_placemark += 1
            candidate_label = placemark_name or style_url or f"Placemark {placemark_index + 1}"
            rows.append(
                {
                    "source_file": str(source_path),
                    "source_feature_id": (
                        f"{source_path.name}:{document.entry_name}:"
                        f"placemark-{placemark_index + 1}:geometry-{geometry_index + 1}"
                    ),
                    "kml_entry": document.entry_name,
                    "folder_path": folder_path,
                    "folder_group": folder_group,
                    "placemark_index": placemark_index,
                    "geometry_index": geometry_index,
                    "placemark_name": placemark_name,
                    "style_url": style_url,
                    "style_color": style_color,
                    "geometry_kind": geometry_kind,
                    "candidate_label": candidate_label,
                }
            )
            geometries.append(geometry)

        if parsed_for_placemark == 0:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="placemark_without_supported_geometry",
                    message="Placemark did not contain a supported non-empty Point, LineString, or Polygon.",
                    location=f"{document.entry_name}:Placemark[{placemark_index}]",
                )
            )

    if blank_name_count:
        issues.append(
            ValidationIssue(
                severity="warning",
                code="blank_placemark_name",
                message=f"{blank_name_count} placemark(s) have no name.",
                location=document.entry_name,
            )
        )

    return rows, geometries, len(placemarks), issues


def ingest_kml_input(path: Path) -> IngestedInput:
    if not path.exists():
        raise IngestionError(f"Missing input file: {path}")

    documents = read_kml_documents(path)
    rows: list[dict[str, object]] = []
    geometries: list[BaseGeometry] = []
    issues: list[ValidationIssue] = []
    placemark_count = 0

    for document in documents:
        doc_rows, doc_geometries, doc_placemarks, doc_issues = parse_kml_document(path, document)
        rows.extend(doc_rows)
        geometries.extend(doc_geometries)
        issues.extend(doc_issues)
        placemark_count += doc_placemarks

    if not geometries:
        raise IngestionError(f"No supported geometries found in input: {path}")

    gdf = gpd.GeoDataFrame(rows, geometry=geometries, crs="EPSG:4326")
    if gdf.crs is None:
        issues.append(
            ValidationIssue(
                severity="warning",
                code="missing_crs",
                message="Input CRS could not be established.",
                location=str(path),
            )
        )

    geometry_types = sorted(gdf.geometry.geom_type.dropna().unique().tolist())
    if len(geometry_types) > 1:
        issues.append(
            ValidationIssue(
                severity="warning",
                code="mixed_geometry_types",
                message=f"Input contains mixed geometry types: {', '.join(geometry_types)}.",
                location=str(path),
            )
        )

    return IngestedInput(
        source_path=path,
        kml_entries=[document.entry_name for document in documents],
        placemark_count=placemark_count,
        geo_data_frame=gdf,
        issues=issues,
    )
