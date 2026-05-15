from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from review_assist.cli import main
from review_assist.constraints import analyze_constraints
from review_assist.populate_for_review import populate_for_review
from review_assist.project_context import generate_project_context
from review_assist.report_sections import generate_report_sections
from review_assist.source_catalog import load_project_source_registry
from review_assist.source_inventory import generate_source_inventory
from review_assist.source_materialization import (
    SourceMaterializationError,
    load_local_source_materializers,
    materialize_local_source,
    materialize_local_sources,
)
from review_assist.tables import generate_comparison_tables


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
        json.dumps(
            {
                "project_id": "test_project",
                "name": "Test Project",
                "description": "Synthetic project",
                "project_type": "alternatives_review",
                "inputs": [{"path": "inputs/routes.kmz", "role": "alternatives", "description": "Synthetic route input"}],
                "assumptions": {"default_buffer_feet": 100, "input_crs": "EPSG:4326"},
                "special_reviewer_instructions": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project_dir


def write_config(path: Path, entries: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"materializer_version": "test", "sources": entries}, indent=2) + "\n", encoding="utf-8")
    return path


def write_layer(path: Path, rows: list[dict[str, object]], geometries: list[object], *, driver: str | None = None, layer: str | None = None) -> Path:
    gdf = gpd.GeoDataFrame(rows, geometry=geometries, crs="EPSG:4326")
    if path.suffix.lower() == ".shp":
        gdf.to_file(path)
    elif driver or layer:
        kwargs: dict[str, object] = {}
        if driver:
            kwargs["driver"] = driver
        if layer:
            kwargs["layer"] = layer
        gdf.to_file(path, **kwargs)
    else:
        path.write_text(gdf.to_json(drop_id=True), encoding="utf-8")
    return path


def wetland_polygon() -> Polygon:
    return Polygon(
        [
            (-90.001, 31.9995),
            (-89.998, 31.9995),
            (-89.998, 32.0005),
            (-90.001, 32.0005),
            (-90.001, 31.9995),
        ]
    )


def materializer_entry(source_id: str, path: Path, *, layer: str | None = None) -> dict[str, object]:
    entry: dict[str, object] = {
        "source_id": source_id,
        "output_name": source_id,
        "layers": [{"path": str(path), "source_layer_id": path.stem, "source_layer_name": path.stem}],
    }
    if layer:
        entry["layers"][0]["layer"] = layer
    return entry


def test_materializer_config_validates_source_ids_paths_layers_and_output_names(tmp_path: Path) -> None:
    layer_path = tmp_path / "wetlands.geojson"
    config_path = write_config(tmp_path / "materializers.json", [materializer_entry("usfws_nwi_wetlands", layer_path)])

    definitions = load_local_source_materializers(config_path)

    assert definitions[0].source_id == "usfws_nwi_wetlands"
    assert definitions[0].output_name == "usfws_nwi_wetlands"
    assert definitions[0].layers[0].path == layer_path.resolve()


def test_configured_normalization_supports_transportation_layers(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    roads_path = write_layer(
        warehouse / "roads.geojson",
        [{"ROAD_NAME": "Main Street", "ROUTE_CLAS": "LOCAL", "SRI": "road-1", "WM_VALIDFR": "2025-01-01"}],
        [LineString([(-90.0005, 32.0), (-89.9895, 32.0)])],
    )
    rail_path = write_layer(
        warehouse / "rail.geojson",
        [{"RROWNER1": "CN", "NET": "Main sub network", "FRAARCID": "rail-1"}],
        [LineString([(-89.995, 31.999), (-89.995, 32.001)])],
    )
    config_path = write_config(
        tmp_path / "materializers.json",
        [
            {
                "source_id": "mdot_transportation_context",
                "output_name": "mdot_transportation_context",
                "normalization": {
                    "label_fields": ["ROAD_NAME", "RROWNER1"],
                    "feature_type_fields": ["ROUTE_CLAS", "NET"],
                    "original_id_fields": ["SRI", "FRAARCID"],
                    "date_fields": ["WM_VALIDFR"],
                },
                "layers": [
                    {"path": str(roads_path), "source_layer_id": "roads", "source_layer_name": "Roads"},
                    {"path": str(rail_path), "source_layer_id": "rail", "source_layer_name": "Rail"},
                ],
            }
        ],
    )

    result = materialize_local_source(project_dir, "mdot_transportation_context", config_path=config_path)

    output = gpd.read_file(result["sources"][0]["output_path"])
    assert set(output["review_assist_feature_label"]) == {"Main Street", "CN"}
    assert set(output["review_assist_feature_type"]) == {"LOCAL", "Main sub network"}
    registered = load_project_source_registry(project_dir).by_source_id()["mdot_transportation_context"]
    assert registered.status == "local_materialized"
    constraints = analyze_constraints(project_dir)
    assert any(constraint["source_id"] == "mdot_transportation_context" for constraint in constraints["constraints"])


def test_boundary_materialization_adds_county_names_to_context_and_sections(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    county_path = write_layer(
        tmp_path / "counties.geojson",
        [{"CONAME": "Test", "CO_SEAT": "Testville", "NEWSTCO_ID": "001"}],
        [
            Polygon(
                [
                    (-90.01, 31.99),
                    (-89.98, 31.99),
                    (-89.98, 32.01),
                    (-90.01, 32.01),
                    (-90.01, 31.99),
                ]
            )
        ],
    )
    config_path = write_config(
        tmp_path / "materializers.json",
        [
            {
                "source_id": "maris_boundary_context",
                "output_name": "maris_boundary_context",
                "normalization": {
                    "label_fields": ["CONAME"],
                    "original_id_fields": ["NEWSTCO_ID"],
                },
                "layers": [
                    {
                        "path": str(county_path),
                        "source_layer_id": "MS_CountyBoundaries_2015",
                        "source_layer_name": "Mississippi County Boundaries 2015",
                    }
                ],
            }
        ],
    )

    materialize_local_source(project_dir, "maris_boundary_context", config_path=config_path)
    context = generate_project_context(project_dir)
    sections = generate_report_sections(project_dir, gpt_drafting=False)

    assert context["administrative_areas"]["counties"][0]["name"] == "Test County"
    study_area = next(section for section in sections["sections"] if section["section_id"] == "study-area")
    assert "Test County" in study_area["generated_content"]


def test_configured_normalization_supports_public_cultural_community_utility_and_conservation_layers(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    cemetery_path = write_layer(
        warehouse / "cemeteries.geojson",
        [{"name": "Old Cemetery", "permanent_": "cem-1", "ftype": "820"}],
        [Point(-89.995, 32.0)],
    )
    fire_path = write_layer(
        warehouse / "fire.geojson",
        [{"NAME": "Station 1", "FTYPE": "740", "OBJECTID": "fire-1"}],
        [Point(-89.996, 32.0)],
    )
    utility_path = write_layer(
        warehouse / "utility.geojson",
        [{"NAME": "Substation A", "TYPE": "Substation", "OBJECTID": "util-1"}],
        [Point(-89.997, 32.0)],
    )
    park_path = write_layer(
        warehouse / "parks.geojson",
        [{"Name": "State Park", "TYPE": "Park", "ID": "park-1"}],
        [wetland_polygon()],
    )
    config_path = write_config(
        tmp_path / "materializers.json",
        [
            {
                "source_id": "maris_public_cultural_context",
                "output_name": "maris_public_cultural_context",
                "normalization": {
                    "label_fields": ["name"],
                    "feature_type_fields": ["ftype"],
                    "original_id_fields": ["permanent_"],
                },
                "layers": [{"path": str(cemetery_path), "source_layer_id": "cemeteries", "source_layer_name": "Cemeteries"}],
            },
            {
                "source_id": "maris_community_facilities",
                "output_name": "maris_community_facilities",
                "normalization": {
                    "label_fields": ["NAME"],
                    "feature_type_fields": ["FTYPE"],
                    "original_id_fields": ["OBJECTID"],
                },
                "layers": [{"path": str(fire_path), "source_layer_id": "fire", "source_layer_name": "Fire Stations"}],
            },
            {
                "source_id": "local_utility_infrastructure",
                "output_name": "local_utility_infrastructure",
                "normalization": {
                    "label_fields": ["NAME"],
                    "feature_type_fields": ["TYPE"],
                    "original_id_fields": ["OBJECTID"],
                },
                "layers": [{"path": str(utility_path), "source_layer_id": "utility", "source_layer_name": "Utilities"}],
            },
            {
                "source_id": "maris_conservation_recreation_lands",
                "output_name": "maris_conservation_recreation_lands",
                "normalization": {
                    "label_fields": ["Name"],
                    "feature_type_fields": ["TYPE"],
                    "original_id_fields": ["ID"],
                },
                "layers": [{"path": str(park_path), "source_layer_id": "parks", "source_layer_name": "Parks"}],
            },
        ],
    )

    result = materialize_local_sources(project_dir, config_path=config_path)

    assert result["materialized_count"] == 4
    for source_id, expected_label in {
        "maris_public_cultural_context": "Old Cemetery",
        "maris_community_facilities": "Station 1",
        "local_utility_infrastructure": "Substation A",
        "maris_conservation_recreation_lands": "State Park",
    }.items():
        output_path = Path(next(source for source in result["sources"] if source["source_id"] == source_id)["output_path"])
        output = gpd.read_file(output_path)
        assert output["review_assist_feature_label"].tolist() == [expected_label]


def test_wetlands_materialization_reads_named_geopackage_layer_not_default(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    gpkg_path = tmp_path / "warehouse" / "wetlands.gpkg"
    gpkg_path.parent.mkdir()
    write_layer(
        gpkg_path,
        [{"ATTRIBUTE": "Wrong default layer", "WETLAND_TYPE": "Default", "NWI_ID": "default"}],
        [wetland_polygon()],
        driver="GPKG",
        layer="Mississippi",
    )
    write_layer(
        gpkg_path,
        [{"ATTRIBUTE": "Freshwater Forested/Shrub Wetland", "WETLAND_TYPE": "Freshwater Wetland", "NWI_ID": "nwi-1"}],
        [wetland_polygon()],
        driver="GPKG",
        layer="MS_Wetlands",
    )
    config_path = write_config(
        tmp_path / "materializers.json",
        [
            {
                "source_id": "usfws_nwi_wetlands",
                "output_name": "usfws_nwi_wetlands",
                "layers": [
                    {
                        "path": str(gpkg_path),
                        "layer": "MS_Wetlands",
                        "source_layer_id": "MS_Wetlands",
                        "source_layer_name": "MS Wetlands",
                    }
                ],
            }
        ],
    )

    result = materialize_local_source(project_dir, "usfws_nwi_wetlands", config_path=config_path)

    assert result["materialized_count"] == 1
    output_path = Path(result["sources"][0]["output_path"])
    output = gpd.read_file(output_path)
    assert output["review_assist_feature_label"].tolist() == ["Freshwater Forested/Shrub Wetland"]
    assert "Wrong default layer" not in output.to_json()


def test_critical_habitat_materialization_combines_line_and_polygon_records(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    line_path = write_layer(
        warehouse / "CRITHAB_LINE.shp",
        [{"comname": "Test Mussel", "sciname": "Testus musselus", "status": "Final", "listing_st": "Endangered", "source_id": "line-1"}],
        [LineString([(-90.0, 31.999), (-90.0, 32.001)])],
    )
    poly_path = write_layer(
        warehouse / "crithab_poly.shp",
        [{"comname": "Test Turtle", "sciname": "Testus turtlus", "status": "Proposed", "listing_st": "Threatened", "source_id": "poly-1"}],
        [wetland_polygon()],
    )
    config_path = write_config(
        tmp_path / "materializers.json",
        [
            {
                "source_id": "usfws_critical_habitat",
                "output_name": "usfws_critical_habitat",
                "layers": [
                    {"path": str(line_path), "source_layer_id": "CRITHAB_LINE", "source_layer_name": "Critical Habitat Lines"},
                    {"path": str(poly_path), "source_layer_id": "crithab_poly", "source_layer_name": "Critical Habitat Polygons"},
                ],
            }
        ],
    )

    result = materialize_local_source(project_dir, "usfws_critical_habitat", config_path=config_path)

    output = gpd.read_file(result["sources"][0]["output_path"])
    assert set(output["review_assist_species_common_name"]) == {"Test Mussel", "Test Turtle"}
    assert set(output.geometry.geom_type) == {"LineString", "Polygon"}
    assert result["sources"][0]["feature_count"] == 2


def test_ssurgo_materialization_feeds_constraints_inventory_and_soil_table(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    soil_path = write_layer(
        tmp_path / "soil.geojson",
        [{"MUSYM": "Sa", "MUKEY": "12345", "AREASYMBOL": "MS001", "SPATIALVER": "1"}],
        [wetland_polygon()],
    )
    config_path = write_config(tmp_path / "materializers.json", [materializer_entry("usda_nrcs_ssurgo_soils", soil_path)])

    materialize_local_sources(project_dir, config_path=config_path)
    constraints = analyze_constraints(project_dir)
    inventory = generate_source_inventory(project_dir)
    tables = generate_comparison_tables(project_dir)

    assert any(constraint["source_id"] == "usda_nrcs_ssurgo_soils" for constraint in constraints["constraints"])
    soil_constraint = next(constraint for constraint in constraints["constraints"] if constraint["source_id"] == "usda_nrcs_ssurgo_soils")
    assert soil_constraint["source_feature_label"] == "Sa"
    assert soil_constraint["source_feature_original_id"] == "12345"
    record = next(item for item in inventory["records"] if item["source_id"] == "usda_nrcs_ssurgo_soils")
    assert record["materialization"]["status"] == "materialized"
    soil_table = next(table for table in tables["tables"] if table["table_id"] == "soil-mapunit-summary")
    assert soil_table["rows"][0]["mapunit_symbol"] == "Sa"


def test_materializer_preserves_existing_reviewer_local_source_without_replace(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    existing_path = write_layer(project_dir / "existing.geojson", [{"ATTRIBUTE": "Existing"}], [wetland_polygon()])
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": "usfws_nwi_wetlands",
                        "enabled": True,
                        "access_method": "local_file",
                        "path": "existing.geojson",
                        "role": "constraint_screening",
                        "buffer_feet": None,
                        "notes": "Reviewer source",
                        "status": "local_registered",
                        "metadata": {"data_authenticity": "real"},
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    warehouse_path = write_layer(tmp_path / "warehouse.geojson", [{"ATTRIBUTE": "Warehouse"}], [wetland_polygon()])
    config_path = write_config(tmp_path / "materializers.json", [materializer_entry("usfws_nwi_wetlands", warehouse_path)])

    result = materialize_local_source(project_dir, "usfws_nwi_wetlands", config_path=config_path)

    assert result["sources"][0]["status"] == "skipped_existing_local"
    registered = load_project_source_registry(project_dir).by_source_id()["usfws_nwi_wetlands"]
    assert registered.path == "existing.geojson"
    assert existing_path.exists()


def test_missing_warehouse_files_warn_in_all_source_mode_and_fail_single_source_mode(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    missing_path = tmp_path / "missing.geojson"
    config_path = write_config(tmp_path / "materializers.json", [materializer_entry("usfws_nwi_wetlands", missing_path)])

    all_result = materialize_local_sources(project_dir, config_path=config_path)

    assert all_result["sources"][0]["status"] == "missing_warehouse_source"
    assert all_result["validation_issues"][0]["code"] == "missing_warehouse_source_file"
    with pytest.raises(SourceMaterializationError, match="missing"):
        materialize_local_source(project_dir, "usfws_nwi_wetlands", config_path=config_path)


def test_populate_for_review_records_materialization_paths_and_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    soil_path = write_layer(
        tmp_path / "soil.geojson",
        [{"MUSYM": "Sa", "MUKEY": "12345", "AREASYMBOL": "MS001", "SPATIALVER": "1"}],
        [wetland_polygon()],
    )
    config_path = write_config(tmp_path / "materializers.json", [materializer_entry("usda_nrcs_ssurgo_soils", soil_path)])
    monkeypatch.setattr("review_assist.source_materialization.LOCAL_SOURCE_MATERIALIZER_CONFIG_PATH", config_path)

    result = populate_for_review(project_dir, materialize_local_sources=True, gpt_drafting=False)

    assert result["source_materialization_enabled"] is True
    assert result["source_materialization_count"] == 1
    assert result["artifact_paths"]["source_materialization"].endswith("local_source_materialization_manifest.json")


def test_cli_materialize_local_source_json(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    soil_path = write_layer(
        tmp_path / "soil.geojson",
        [{"MUSYM": "Sa", "MUKEY": "12345", "AREASYMBOL": "MS001", "SPATIALVER": "1"}],
        [wetland_polygon()],
    )
    config_path = write_config(tmp_path / "materializers.json", [materializer_entry("usda_nrcs_ssurgo_soils", soil_path)])
    monkeypatch.setattr("review_assist.source_materialization.LOCAL_SOURCE_MATERIALIZER_CONFIG_PATH", config_path)

    exit_code = main(["materialize-local-source", str(project_dir), "usda_nrcs_ssurgo_soils", "--json"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["materialized_count"] == 1
    assert output["sources"][0]["source_id"] == "usda_nrcs_ssurgo_soils"
