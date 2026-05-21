from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from review_assist.cli import main
from review_assist.deliverable_constraints import analyze_comparison_unit_constraints
from review_assist.deliverable_matrix import REQUIRED_STUB_TEXT
from review_assist.deliverable_tables import generate_deliverable_tables, load_deliverable_tables
from review_assist.populate_for_review import populate_for_review


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


def write_project(tmp_path: Path, *, expected_count: int | None = None) -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    kml = kml_document(
        """
        <Placemark><name>Alternative A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9950,32.0000,0</coordinates></LineString></Placemark>
        <Placemark><name>Alternative A</name><LineString><coordinates>-89.9950,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        <Placemark><name>Alternative B</name><LineString><coordinates>-90.0000,32.0020,0 -89.9900,32.0020,0</coordinates></LineString></Placemark>
        """
    )
    (project_dir / "inputs" / "routes.kmz").write_bytes(kmz_bytes(kml))
    assumptions: dict[str, object] = {
        "default_buffer_feet": 100,
        "input_crs": "EPSG:4326",
    }
    if expected_count is not None:
        assumptions["expected_comparison_unit_count"] = expected_count
    (project_dir / "config" / "project.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "name": "Test Project",
                "description": "Synthetic project",
                "project_type": "alternatives_review",
                "inputs": [
                    {
                        "path": "inputs/routes.kmz",
                        "role": "alternatives",
                        "description": "Synthetic route input",
                    }
                ],
                "assumptions": assumptions,
                "special_reviewer_instructions": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project_dir


def write_registry(project_dir: Path, sources: list[tuple[str, str]]) -> None:
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": source_id,
                        "enabled": True,
                        "access_method": "local_file",
                        "path": path,
                        "role": "constraint_screening",
                        "buffer_feet": None,
                        "notes": "",
                        "status": "test",
                    }
                    for source_id, path in sources
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


def table_by_id(tables: dict[str, object], table_id: str) -> dict[str, object]:
    return next(table for table in tables["tables"] if table["table_id"] == table_id)  # type: ignore[index]


def test_comparison_unit_constraints_preserve_unit_ids_and_raw_feature_ids(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson")])

    result = analyze_comparison_unit_constraints(project_dir)

    constraint = result["constraints"][0]
    assert constraint["comparison_unit_id"].startswith("comparison-unit-")
    assert constraint["comparison_unit_name"] == "Alternative A"
    assert constraint["comparison_unit_type"] == "alternative"
    assert constraint["raw_feature_count"] == 2
    assert len(constraint["raw_feature_ids"]) == 2
    assert constraint["analysis_geometry_kind"] == "buffered_corridor"
    assert constraint["query_extent_type"] == "project_area_analysis_bounds"
    assert constraint["analysis_extent_type"] == "direct_intersection_extent"
    assert constraint["interpretation_scope_label"] == "within the submitted project feature or comparison unit"
    assert "buffer_assumption" in constraint["uncertainty_flags"]


def test_comparison_unit_constraints_label_screening_buffer_extent(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "facilities.geojson",
        [Point(-90.0, 32.0002)],
        [{"FAC_NAME": "Nearby Facility", "REGISTRY_ID": "facility-1"}],
    )
    write_registry(project_dir, [("epa_frs_facilities_ms", "facilities.geojson")])

    result = analyze_comparison_unit_constraints(project_dir)

    constraint = result["constraints"][0]
    assert result["extent_policy"]["core_rule"].startswith("Rendered map extent")
    assert constraint["relationship_type"] == "nearest_within_buffer"
    assert constraint["query_extent_type"] == "project_area_analysis_bounds"
    assert constraint["analysis_extent_type"] == "screening_buffer_extent"
    assert constraint["query_distance"] == 100.0
    assert constraint["query_units"] == "feet"
    assert "buffered comparison-unit screening geometry" in constraint["source_selection_reason"]


def test_deliverable_wetlands_table_uses_exact_columns_and_deduplicated_counts(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [
            Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)]),
            Polygon([(-89.997, 32.0015), (-89.994, 32.0015), (-89.994, 32.0025), (-89.997, 32.0025), (-89.997, 32.0015)]),
        ],
        [
            {"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"},
            {"WETLAND_TYPE": "Freshwater Pond", "OBJECTID": "pond-1"},
        ],
    )
    write_layer(
        project_dir / "streams.geojson",
        [
            LineString([(-89.996, 31.999), (-89.996, 32.001)]),
            LineString([(-89.996, 31.999), (-89.996, 32.001)]),
        ],
        [
            {"gnis_name": "Stream A", "Permanent_Identifier": "stream-1", "FTYPE": "StreamRiver"},
            {"gnis_name": "Stream A duplicate", "Permanent_Identifier": "stream-1", "FTYPE": "StreamRiver"},
        ],
    )
    write_registry(
        project_dir,
        [
            ("usfws_nwi_wetlands", "wetlands.geojson"),
            ("usgs_nhd_flowlines", "streams.geojson"),
        ],
    )

    tables = generate_deliverable_tables(project_dir)
    wetlands = table_by_id(tables, "table-wetlands-waterbodies")

    assert wetlands["columns"] == [
        "Alternative",
        "Stream Crossings",
        "Freshwater Emergent Wetland",
        "Freshwater Forested/Shrub Wetland",
        "Freshwater Pond",
    ]
    assert wetlands["is_stub"] is False
    assert wetlands["row_count"] == 2
    row_a = next(row for row in wetlands["rows"] if row["Alternative"] == "Alternative A")  # type: ignore[index]
    row_b = next(row for row in wetlands["rows"] if row["Alternative"] == "Alternative B")  # type: ignore[index]
    assert row_a["Stream Crossings"] == 1
    assert row_a["Freshwater Emergent Wetland"] == 1
    assert row_b["Freshwater Pond"] == 1
    assert wetlands["source_refs"] == ["usfws_nwi_wetlands", "usgs_nhd_flowlines"]
    assert wetlands["provenance"]["metric_contract"]["Stream Crossings"]["required_source_ids"] == ["usgs_nhd_flowlines"]  # type: ignore[index]
    assert wetlands["query_extent_type"] == "project_area_analysis_bounds"
    assert wetlands["table_extent_type"] == "direct_intersection_extent"
    assert wetlands["analysis_extent_type"] == "direct_intersection_extent"
    assert wetlands["provenance"]["extent_policy"]["table_extent_type"] == "direct_intersection_extent"  # type: ignore[index]

    census = table_by_id(tables, "table-income-demographics")
    assert census["is_stub"] is True
    assert census["table_extent_type"] == "county_or_regional_context_extent"
    assert "for county or regional context" in census["interpretation_scope_label"]


def test_wetlands_table_uses_effective_source_status_not_logical_rollup_noise(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_layer(
        project_dir / "flowlines.geojson",
        [LineString([(-89.996, 31.999), (-89.996, 32.001)])],
        [{"gnis_name": "Stream A", "Permanent_Identifier": "stream-1", "FTYPE": "StreamRiver"}],
    )
    write_layer(
        project_dir / "waterbodies.geojson",
        [Polygon([(-89.997, 32.0015), (-89.994, 32.0015), (-89.994, 32.0025), (-89.997, 32.0025), (-89.997, 32.0015)])],
        [{"gnis_name": "Pond A", "Permanent_Identifier": "waterbody-1", "FTYPE": "LakePond"}],
    )
    write_layer(
        project_dir / "other_areas.geojson",
        [Polygon([(-89.999, 32.003), (-89.998, 32.003), (-89.998, 32.004), (-89.999, 32.004), (-89.999, 32.003)])],
        [{"gnis_name": "Area A", "Permanent_Identifier": "other-area-1", "FTYPE": "Area"}],
    )
    write_registry(
        project_dir,
        [
            ("usfws_nwi_wetlands", "wetlands.geojson"),
            ("usgs_nhd_flowlines", "flowlines.geojson"),
            ("usgs_nhd_waterbodies", "waterbodies.geojson"),
            ("usgs_nhd_other_areas", "other_areas.geojson"),
        ],
    )

    tables = generate_deliverable_tables(project_dir)
    wetlands = table_by_id(tables, "table-wetlands-waterbodies")

    assert wetlands["is_stub"] is False
    assert "source_not_downloaded" not in wetlands["uncertainty_flags"]
    assert "hydrography_source_unavailable" not in wetlands["uncertainty_flags"]
    row_a = next(row for row in wetlands["rows"] if row["Alternative"] == "Alternative A")  # type: ignore[index]
    row_b = next(row for row in wetlands["rows"] if row["Alternative"] == "Alternative B")  # type: ignore[index]
    assert row_a["Stream Crossings"] == 1
    assert row_b["Freshwater Pond"] == 0
    assert "usgs_nhd_waterbodies" not in wetlands["source_refs"]
    assert "usgs_nhd_other_areas" not in wetlands["source_refs"]


def test_wetlands_table_does_not_count_logical_hydrography_rollup_as_stream_source(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_layer(
        project_dir / "rollup.geojson",
        [LineString([(-89.996, 31.999), (-89.996, 32.001)])],
        [{"gnis_name": "Rollup Stream", "Permanent_Identifier": "rollup-stream-1", "FTYPE": "StreamRiver"}],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson"), ("usgs_nhd_hydrography", "rollup.geojson")])

    tables = generate_deliverable_tables(project_dir)
    wetlands = table_by_id(tables, "table-wetlands-waterbodies")
    row_a = next(row for row in wetlands["rows"] if row["Alternative"] == "Alternative A")  # type: ignore[index]

    assert row_a["Stream Crossings"] == 0
    assert "usgs_nhd_hydrography" not in wetlands["source_refs"]
    assert "hydrography_source_unavailable" in wetlands["uncertainty_flags"]


def test_wetlands_table_uses_canonical_flowlines_when_rollup_overlaps(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    stream = LineString([(-89.996, 31.999), (-89.996, 32.001)])
    write_layer(project_dir / "flowlines.geojson", [stream], [{"gnis_name": "Stream A", "Permanent_Identifier": "stream-1"}])
    write_layer(project_dir / "rollup.geojson", [stream], [{"gnis_name": "Stream A", "Permanent_Identifier": "stream-1"}])
    write_registry(
        project_dir,
        [
            ("usfws_nwi_wetlands", "wetlands.geojson"),
            ("usgs_nhd_flowlines", "flowlines.geojson"),
            ("usgs_nhd_hydrography", "rollup.geojson"),
        ],
    )

    tables = generate_deliverable_tables(project_dir)
    wetlands = table_by_id(tables, "table-wetlands-waterbodies")
    row_a = next(row for row in wetlands["rows"] if row["Alternative"] == "Alternative A")  # type: ignore[index]

    assert row_a["Stream Crossings"] == 1
    assert "usgs_nhd_flowlines" in wetlands["source_refs"]
    assert "usgs_nhd_hydrography" not in wetlands["source_refs"]


def test_wetlands_table_dedupes_overlapping_flowline_crossing_events(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    duplicate_crossing = LineString([(-89.996, 31.999), (-89.996, 32.001)])
    write_layer(
        project_dir / "flowlines.geojson",
        [duplicate_crossing, duplicate_crossing],
        [
            {"gnis_name": "Stream A", "Permanent_Identifier": "stream-1"},
            {"gnis_name": "Stream A duplicate", "Permanent_Identifier": "stream-2"},
        ],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson"), ("usgs_nhd_flowlines", "flowlines.geojson")])

    tables = generate_deliverable_tables(project_dir)
    wetlands = table_by_id(tables, "table-wetlands-waterbodies")
    row_a = next(row for row in wetlands["rows"] if row["Alternative"] == "Alternative A")  # type: ignore[index]

    assert row_a["Stream Crossings"] == 1
    assert wetlands["row_count"] == 2


def test_deliverable_flood_table_uses_buffered_corridor_acreage(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "flood.geojson",
        [Polygon([(-90.001, 32.00012), (-89.998, 32.00012), (-89.998, 32.00022), (-90.001, 32.00022), (-90.001, 32.00012)])],
        [{"FLD_ZONE": "AE", "ZONE_SUBTY": "FLOODWAY", "SFHA_TF": "T", "FLD_AR_ID": "flood-1"}],
    )
    write_registry(project_dir, [("fema_nfhl_flood_hazard", "flood.geojson")])

    tables = generate_deliverable_tables(project_dir)
    flood = table_by_id(tables, "table-fema-flood-zones")

    assert flood["columns"] == ["Alternative", "Flood Zone Classification", "Estimated Acreage"]
    assert flood["is_stub"] is False
    row = next(row for row in flood["rows"] if row["Alternative"] == "Alternative A")  # type: ignore[index]
    assert row["Flood Zone Classification"] == "AE - FLOODWAY"
    assert row["Estimated Acreage"] > 0


def test_census_tables_stub_when_api_key_and_local_source_are_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    project_dir = write_project(tmp_path)

    tables = generate_deliverable_tables(project_dir)
    income = table_by_id(tables, "table-income-demographics")
    composition = table_by_id(tables, "table-demographic-composition")

    assert income["is_stub"] is True
    assert composition["is_stub"] is True
    assert income["stub_text"] == REQUIRED_STUB_TEXT
    assert "missing_census_api_key" in income["uncertainty_flags"]  # type: ignore[operator]
    assert tables["table_count"] == 4


def test_census_tables_use_registered_local_acs_values(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "census.geojson",
        [Polygon([(-90.001, 31.999), (-89.989, 31.999), (-89.989, 32.003), (-90.001, 32.003), (-90.001, 31.999)])],
        [
            {
                "GEOID": "28121000100",
                "NAMELSAD": "Census Tract 1",
                "B17001_002E": 42,
                "B02001_003E": 100,
                "B02001_005E": 25,
                "B02001_002E": 300,
            }
        ],
    )
    write_registry(project_dir, [("census_tiger_acs", "census.geojson")])

    tables = generate_deliverable_tables(project_dir)
    income = table_by_id(tables, "table-income-demographics")
    composition = table_by_id(tables, "table-demographic-composition")

    assert income["is_stub"] is False
    assert income["rows"] == [{"Census Tract": "Census Tract 1", "Population Below the Poverty Line": "42"}]
    assert composition["is_stub"] is False
    assert composition["rows"][0]["Black or African American"] == "100"  # type: ignore[index]
    assert composition["rows"][0]["Asian"] == "25"  # type: ignore[index]
    assert composition["rows"][0]["White"] == "300"  # type: ignore[index]


def test_cli_and_populate_manifest_include_deliverable_tables(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["analyze-comparison-unit-constraints", str(project_dir)]) == 0
    captured = capsys.readouterr()
    assert "Analyzed comparison-unit constraints" in captured.out

    assert main(["generate-deliverable-tables", str(project_dir)]) == 0
    captured = capsys.readouterr()
    assert "Generated deliverable tables" in captured.out
    assert load_deliverable_tables(project_dir)["table_count"] == 4

    result = populate_for_review(project_dir)

    assert result["artifact_paths"]["comparison_unit_constraints"].endswith("comparison_unit_constraints.json")
    assert result["artifact_paths"]["deliverable_tables"].endswith("tables.json")
    assert result["deliverable_table_count"] == 4
