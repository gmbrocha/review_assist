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


def parse_kml_document(source_path: Path, document: KmlDocument) -> tuple[list[dict[str, object]], list[BaseGeometry], int, list[ValidationIssue]]:
    rows: list[dict[str, object]] = []
    geometries: list[BaseGeometry] = []
    issues: list[ValidationIssue] = []
    try:
        root = ET.fromstring(document.text)
    except ET.ParseError as exc:
        raise IngestionError(f"Invalid KML XML in {source_path}:{document.entry_name}: {exc}") from exc

    placemarks = list(descendants(root, "Placemark"))
    blank_name_count = 0
    for placemark_index, placemark in enumerate(placemarks):
        placemark_name = clean_label(child_text(placemark, "name"))
        style_url = clean_label(child_text(placemark, "styleUrl"))
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
                    "kml_entry": document.entry_name,
                    "placemark_index": placemark_index,
                    "geometry_index": geometry_index,
                    "placemark_name": placemark_name,
                    "style_url": style_url,
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
