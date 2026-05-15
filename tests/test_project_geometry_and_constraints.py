from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from review_assist.cli import main
from review_assist.constraints import analyze_constraints
from review_assist.project_geometry import build_project_geometry
from review_assist.populate_for_review import populate_for_review
from review_assist.review_queue import generate_review_queue, update_review_item


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


def write_project(tmp_path: Path, kml_body: str, *, project_type: str = "alternatives_review") -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    (project_dir / "inputs" / "input.kmz").write_bytes(kmz_bytes(kml_document(kml_body)))
    (project_dir / "config" / "project.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "name": "Test Project",
                "description": "Synthetic project",
                "project_type": project_type,
                "inputs": [
                    {
                        "path": "inputs/input.kmz",
                        "role": "project_geometry",
                        "description": "Synthetic input",
                    }
                ],
                "assumptions": {
                    "default_buffer_feet": 100,
                    "input_crs": "EPSG:4326",
                },
                "special_reviewer_instructions": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project_dir


def write_registry(project_dir: Path, source_id: str, source_path: str | None, *, enabled: bool = True) -> None:
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": source_id,
                        "enabled": enabled,
                        "access_method": "local_file",
                        "path": source_path,
                        "role": "constraint_screening",
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


def test_segmented_lines_group_by_name_and_merge_connected_segments(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9950,32.0000,0</coordinates></LineString></Placemark>
        <Placemark><name>Route A</name><LineString><coordinates>-89.9950,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        <Placemark><name>Route B</name><LineString><coordinates>-90.0000,32.0010,0 -89.9900,32.0010,0</coordinates></LineString></Placemark>
        """,
    )

    result = build_project_geometry(project_dir)
    features = gpd.read_file(project_dir / "intermediate" / "project_features.geojson")

    assert result["geometry_role"] == "line_corridor"
    assert result["feature_count"] == 2
    assert set(features["feature_name"]) == {"Route A", "Route B"}
    assert int(features.loc[features["feature_name"] == "Route A", "source_feature_count"].iloc[0]) == 2
    assert features.loc[features["feature_name"] == "Route A"].geometry.iloc[0].geom_type == "LineString"


def test_disconnected_line_segments_preserve_multilinestring(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9950,32.0000,0</coordinates></LineString></Placemark>
        <Placemark><name>Route A</name><LineString><coordinates>-89.9900,32.0000,0 -89.9850,32.0000,0</coordinates></LineString></Placemark>
        """,
    )

    build_project_geometry(project_dir)
    features = gpd.read_file(project_dir / "intermediate" / "project_features.geojson")

    assert len(features) == 1
    assert features.geometry.iloc[0].geom_type == "MultiLineString"


def test_point_heavy_project_preserves_points_and_style_groups(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><styleUrl>#IconStyle00</styleUrl><Point><coordinates>-90.0000,32.0000,0</coordinates></Point></Placemark>
        <Placemark><styleUrl>#IconStyle01</styleUrl><Point><coordinates>-89.9900,32.0000,0</coordinates></Point></Placemark>
        """,
        project_type="location_review",
    )

    result = build_project_geometry(project_dir)
    features = gpd.read_file(project_dir / "intermediate" / "project_features.geojson")

    assert result["geometry_role"] == "point_site"
    assert result["feature_count"] == 2
    assert set(features["feature_group"]) == {"#IconStyle00", "#IconStyle01"}
    assert set(features.geometry.geom_type) == {"Point"}


def test_analysis_bounds_include_configured_buffer(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )

    result = build_project_geometry(project_dir)
    features = gpd.read_file(project_dir / "intermediate" / "project_features.geojson").to_crs(result["analysis_crs"])
    bounds = gpd.read_file(project_dir / "intermediate" / "project_analysis_bounds.geojson").to_crs(result["analysis_crs"])

    feature_bounds = features.total_bounds
    analysis_bounds = bounds.total_bounds
    assert analysis_bounds[0] < feature_bounds[0]
    assert analysis_bounds[1] < feature_bounds[1]
    assert analysis_bounds[2] > feature_bounds[2]
    assert analysis_bounds[3] > feature_bounds[3]


def test_constraint_analysis_reports_line_polygon_wetland_constraint(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")

    result = analyze_constraints(project_dir)

    assert result["constraint_count"] == 1
    assert result["constraints"][0]["source_category"] == "wetlands_waterbodies"
    assert result["constraints"][0]["project_feature_name"] == "Route A"
    assert result["constraints"][0]["provenance"]["source_id"] == "usfws_nwi_wetlands"
    assert result["constraints"][0]["measurements"]


def test_constraint_analysis_reports_line_line_stream_crossing(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )
    write_layer(project_dir / "streams.geojson", [LineString([(-89.995, 31.999), (-89.995, 32.001)])], [{"gnis_name": "Stream A", "ftype": 460}])
    write_registry(project_dir, "usgs_nhd_hydrography", "streams.geojson")

    result = analyze_constraints(project_dir)

    assert result["constraints"][0]["relationship_type"] == "crosses"
    assert result["constraints"][0]["source_feature_label"] == "Stream A"
    assert result["constraints"][0]["source_feature_type"] == "460"


def test_constraint_analysis_reports_ssurgo_soil_mapunit_values(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )
    write_layer(
        project_dir / "soils.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"MUSYM": "s3973", "MUKEY": "669769", "AREASYMBOL": "US", "SPATIALVER": 3}],
    )
    write_registry(project_dir, "usda_nrcs_ssurgo_soils", "soils.geojson")

    result = analyze_constraints(project_dir)
    constraint = result["constraints"][0]

    assert constraint["source_category"] == "soils"
    assert constraint["source_feature_label"] == "s3973"
    assert constraint["source_feature_type"] == "s3973"
    assert constraint["source_feature_original_id"] == "669769"
    assert constraint["source_feature_values"]["soil_mapunit_symbol"] == "s3973"
    assert constraint["source_feature_values"]["soil_mapunit_key"] == "669769"
    assert constraint["source_feature_values"]["soil_area_symbol"] == "US"
    assert constraint["source_feature_values"]["soil_spatial_version"] == "3"


def test_constraint_analysis_reports_point_polygon_and_nearby_line_constraints(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><styleUrl>#IconStyle00</styleUrl><Point><coordinates>-90.0000,32.0000,0</coordinates></Point></Placemark>
        """,
        project_type="location_review",
    )
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    polygon_result = analyze_constraints(project_dir)

    write_layer(project_dir / "streams.geojson", [LineString([(-89.9998, 31.999), (-89.9998, 32.001)])], [{"name": "Stream A"}])
    write_registry(project_dir, "usgs_nhd_hydrography", "streams.geojson")
    line_result = analyze_constraints(project_dir)

    assert polygon_result["constraints"][0]["relationship_type"] in {"contains", "intersects"}
    assert line_result["constraints"][0]["relationship_type"] == "nearest_within_buffer"
    assert line_result["constraints"][0]["measurements"]["distance_feet"] > 0


def test_constraint_analysis_no_sources_and_no_overlap_are_nonfatal(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )

    no_source_result = analyze_constraints(project_dir)

    write_layer(project_dir / "far.geojson", [Point(-89.0, 33.0)], [{"name": "Far Feature"}])
    write_registry(project_dir, "epa_envirofacts_echo", "far.geojson")
    no_overlap_result = analyze_constraints(project_dir)

    assert no_source_result["constraint_count"] == 0
    assert no_overlap_result["constraint_count"] == 0
    assert no_overlap_result["sources"][0]["status"] == "analyzed"
    assert no_overlap_result["sources"][0]["clipped_feature_count"] == 0


def test_full_pipeline_uses_constraints_for_findings_sections_and_lean_queue(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")

    result = populate_for_review(project_dir)
    queue = generate_review_queue(project_dir)
    item_types = {item["type"] for item in queue["items"]}

    assert result["constraint_count"] == 1
    assert Path(result["artifact_paths"]["constraint_results"]).exists()
    assert "draft_finding" in item_types
    assert "report_section" in item_types
    assert "source_inventory_note" not in item_types
    assert any(item["type"] == "draft_finding" and "Wetland A" in item["generated_content"] for item in queue["items"])


def test_review_queue_preserves_state_across_constraint_regeneration(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    populate_for_review(project_dir)
    queue = generate_review_queue(project_dir)
    finding_id = next(item["id"] for item in queue["items"] if item["type"] == "draft_finding")

    update_review_item(project_dir, finding_id, status="accepted", note="Reviewed.")
    populate_for_review(project_dir)
    regenerated = generate_review_queue(project_dir)
    finding = next(item for item in regenerated["items"] if item["id"] == finding_id)

    assert finding["status"] == "accepted"
    assert finding["reviewer_notes"][0]["note"] == "Reviewed."


def test_cli_project_geometry_and_constraints_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )

    assert main(["build-project-geometry", str(project_dir)]) == 0
    assert main(["analyze-constraints", str(project_dir)]) == 0

    captured = capsys.readouterr()
    assert "Built project geometry" in captured.out
    assert "Analyzed constraints" in captured.out
