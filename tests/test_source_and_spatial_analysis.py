from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from review_assist.cli import main
from review_assist.source_catalog import (
    SourceCatalogError,
    load_project_source_registry,
    load_source_catalog,
    register_local_source,
)
from review_assist.spatial_analysis import SpatialAnalysisError, analyze_project


def kml_document(body: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    {body}
  </Document>
</kml>
""".encode("utf-8")


def kmz_bytes(kml: bytes) -> bytes:
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("doc.kml", kml)
    return buffer.getvalue()


def write_project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    kml = kml_document(
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """
    )
    (project_dir / "inputs" / "routes.kmz").write_bytes(kmz_bytes(kml))
    (project_dir / "config" / "project.json").write_text(
        """{
  "project_id": "test_project",
  "name": "Test Project",
  "description": "Synthetic project",
  "project_type": "alternatives_review",
  "inputs": [
    {
      "path": "inputs/routes.kmz",
      "role": "alternatives",
      "description": "Synthetic route input"
    }
  ],
  "assumptions": {
    "default_buffer_feet": 100,
    "input_crs": "EPSG:4326"
  },
  "special_reviewer_instructions": ""
}
""",
        encoding="utf-8",
    )
    return project_dir


def set_project_buffer(project_dir: Path, value: object) -> None:
    manifest_path = project_dir / "config" / "project.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["assumptions"]["default_buffer_feet"] = value
    manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_registry(project_dir: Path, source_id: str, source_path: str | None, *, enabled: bool = True, access_method: str = "local_file") -> None:
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": source_id,
                        "enabled": enabled,
                        "access_method": access_method,
                        "path": source_path,
                        "role": "context",
                        "buffer_feet": None,
                        "notes": "",
                        "status": "test",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_layer(path: Path, geometries: list[object], rows: list[dict[str, object]]) -> Path:
    gdf = gpd.GeoDataFrame(rows, geometry=geometries, crs="EPSG:4326")
    path.write_text(gdf.to_json(drop_id=True), encoding="utf-8")
    return path


def test_source_catalog_loads_broad_categories() -> None:
    catalog = load_source_catalog()

    assert "usfws_nwi_wetlands" in catalog.sources
    assert "usgs_nhd_hydrography" in catalog.sources
    assert "mrlc_nlcd_land_cover" in catalog.sources
    assert "usda_nrcs_ssurgo_soils" in catalog.sources
    assert catalog.sources["fema_nfhl_flood_hazard"].priority == "secondary_optional"


def test_invalid_source_catalog_requires_sources_list(tmp_path: Path) -> None:
    catalog_path = tmp_path / "source_catalog.json"
    catalog_path.write_text('{"sources": {}}', encoding="utf-8")

    with pytest.raises(SourceCatalogError, match="requires a list"):
        load_source_catalog(catalog_path)


def test_project_source_registry_loads_disabled_and_manual_sources(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_ipac_report", None, enabled=True, access_method="manual_document")

    registry = load_project_source_registry(project_dir)
    result = analyze_project(project_dir)

    assert registry.sources[0].access_method == "manual_document"
    assert result["sources"][0]["status"] == "skipped_non_local"
    assert result["relationships"] == []


def test_project_source_registry_requires_boolean_enabled(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", None, enabled=True)
    data = json.loads((project_dir / "config" / "sources.json").read_text(encoding="utf-8"))
    data["sources"][0]["enabled"] = "false"
    (project_dir / "config" / "sources.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SourceCatalogError, match="enabled must be true or false"):
        load_project_source_registry(project_dir)


def test_project_source_registry_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", None, enabled=False)
    data = json.loads((project_dir / "config" / "sources.json").read_text(encoding="utf-8"))
    data["sources"].append(dict(data["sources"][0]))
    (project_dir / "config" / "sources.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SourceCatalogError, match="Duplicate source_id"):
        load_project_source_registry(project_dir)


def test_project_source_registry_rejects_blank_local_path(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", "", enabled=True)

    with pytest.raises(SourceCatalogError, match="path must not be blank"):
        load_project_source_registry(project_dir)


def test_project_source_registry_requires_non_empty_access_method(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", None, enabled=False)
    data = json.loads((project_dir / "config" / "sources.json").read_text(encoding="utf-8"))
    data["sources"][0]["access_method"] = ""
    (project_dir / "config" / "sources.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SourceCatalogError, match="access_method"):
        load_project_source_registry(project_dir)


def test_project_source_registry_must_match_manifest_id(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", None, enabled=False)
    data = json.loads((project_dir / "config" / "sources.json").read_text(encoding="utf-8"))
    data["project_id"] = "wrong_project"
    (project_dir / "config" / "sources.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SourceCatalogError, match="does not match project manifest"):
        load_project_source_registry(project_dir)


def test_project_source_registry_requires_project_manifest(tmp_path: Path) -> None:
    with pytest.raises(SourceCatalogError, match="Missing project manifest"):
        load_project_source_registry(tmp_path / "not_a_project")


def test_register_local_source_updates_project_registry(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    layer_path = write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )

    registry = register_local_source(project_dir, "usfws_nwi_wetlands", layer_path)

    source = registry.by_source_id()["usfws_nwi_wetlands"]
    assert source.enabled is True
    assert source.path == "wetlands.geojson"


def test_analyze_project_reports_wetland_intersection(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    layer_path = write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")

    result = analyze_project(project_dir)

    relationships = {item["spatial_relationship"] for item in result["relationships"]}
    assert "intersects" in relationships
    assert result["sources"][0]["clipped_feature_count"] == 1
    assert Path(result["sources"][0]["clipped_geojson"]).exists()


def test_analyze_project_reports_stream_crossing(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "streams.geojson",
        [LineString([(-89.995, 31.999), (-89.995, 32.001)])],
        [{"name": "Stream A"}],
    )
    write_registry(project_dir, "usgs_nhd_hydrography", "streams.geojson")

    result = analyze_project(project_dir)

    relationships = {item["spatial_relationship"] for item in result["relationships"]}
    assert "intersects" in relationships
    assert "crosses" in relationships


def test_analyze_project_reports_land_cover_overlap_measurement(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "landcover.geojson",
        [Polygon([(-90.001, 31.999), (-89.997, 31.999), (-89.997, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Forested"}],
    )
    write_registry(project_dir, "mrlc_nlcd_land_cover", "landcover.geojson")

    result = analyze_project(project_dir)

    measurements = result["relationships"][0]["measurements"]
    assert measurements["intersection_length_feet"] > 0


def test_analyze_project_reports_nearby_feature_within_buffer(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "points.geojson", [Point(-89.995, 32.0002)], [{"name": "Nearby Facility"}])
    write_registry(project_dir, "epa_envirofacts_echo", "points.geojson")

    result = analyze_project(project_dir)

    assert result["relationships"][0]["spatial_relationship"] == "within_buffer"
    assert result["relationships"][0]["measurements"]["distance_feet"] > 0


def test_analyze_project_no_overlap_returns_empty_relationships(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "far.geojson", [Point(-89.0, 33.0)], [{"name": "Far Feature"}])
    write_registry(project_dir, "epa_envirofacts_echo", "far.geojson")

    result = analyze_project(project_dir)

    assert result["relationships"] == []
    assert result["sources"][0]["clipped_feature_count"] == 0


def test_analyze_project_errors_for_missing_local_source(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", "missing.geojson")

    with pytest.raises(SpatialAnalysisError, match="Missing local source file"):
        analyze_project(project_dir)


def test_analyze_project_rejects_negative_default_buffer(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    set_project_buffer(project_dir, -1)
    write_layer(project_dir / "far.geojson", [Point(-89.0, 33.0)], [{"name": "Far Feature"}])
    write_registry(project_dir, "epa_envirofacts_echo", "far.geojson")

    with pytest.raises(SpatialAnalysisError, match="zero or greater"):
        analyze_project(project_dir)


def test_analyze_project_rejects_boolean_default_buffer(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    set_project_buffer(project_dir, True)
    write_layer(project_dir / "far.geojson", [Point(-89.0, 33.0)], [{"name": "Far Feature"}])
    write_registry(project_dir, "epa_envirofacts_echo", "far.geojson")

    with pytest.raises(SpatialAnalysisError, match="default_buffer_feet.*numeric"):
        analyze_project(project_dir)


def test_analyze_project_rejects_negative_source_buffer(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "far.geojson", [Point(-89.0, 33.0)], [{"name": "Far Feature"}])
    write_registry(project_dir, "epa_envirofacts_echo", "far.geojson")
    data = json.loads((project_dir / "config" / "sources.json").read_text(encoding="utf-8"))
    data["sources"][0]["buffer_feet"] = -1
    (project_dir / "config" / "sources.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SpatialAnalysisError, match="zero or greater"):
        analyze_project(project_dir)


def test_project_source_registry_rejects_boolean_source_buffer(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "epa_envirofacts_echo", None, enabled=False)
    data = json.loads((project_dir / "config" / "sources.json").read_text(encoding="utf-8"))
    data["sources"][0]["buffer_feet"] = True
    (project_dir / "config" / "sources.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SourceCatalogError, match="buffer_feet must be numeric"):
        load_project_source_registry(project_dir)


def test_cli_source_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)
    layer_path = write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )

    assert main(["list-sources", str(project_dir)]) == 0
    assert main(["import-source", str(project_dir), "usfws_nwi_wetlands", str(layer_path)]) == 0
    assert main(["analyze-project", str(project_dir)]) == 0

    captured = capsys.readouterr()
    assert "Source catalog" in captured.out
    assert "Registered source" in captured.out
    assert "Spatial relationships" in captured.out


def test_cli_analyze_project_returns_nonzero_for_missing_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", "missing.geojson")

    exit_code = main(["analyze-project", str(project_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Missing local source file" in captured.err


def test_cli_list_sources_returns_nonzero_for_missing_project_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["list-sources", str(tmp_path / "not_a_project")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Missing project manifest" in captured.err
