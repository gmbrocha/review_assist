from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from review_assist.cli import main
from review_assist.comparison_units import build_comparison_units
from review_assist.constraints import analyze_constraints
from review_assist.deliverable_constraints import analyze_comparison_unit_constraints
from review_assist.deliverable_figures import generate_deliverable_figures
from review_assist.deliverable_items import generate_deliverable_items
from review_assist.deliverable_tables import generate_deliverable_tables
from review_assist.evidence_package import build_evidence_package
from review_assist.populate_for_review import populate_for_review
from review_assist.project_context import generate_project_context
from review_assist.report_sections import generate_report_sections
from review_assist.review_queue import generate_review_queue
from review_assist.source_catalog import load_project_source_registry
from review_assist.source_inventory import generate_source_inventory
from review_assist.source_materialization import (
    SourceMaterializationError,
    load_local_source_materializers,
    materialize_local_source,
    materialize_local_sources,
)
from review_assist.source_status import resolve_source_status_set
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


def test_seeded_environmental_facility_materializes_and_reports_provided_locally(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    brownfields_path = write_layer(
        warehouse / "brownfields.geojson",
        [{"PRIMARY_NA": "Former Mill", "REGISTRY_I": "110001", "INTEREST_T": "BROWNFIELDS"}],
        [Point(-89.995, 32.0002)],
    )
    config_path = write_config(
        tmp_path / "materializers.json",
        [
            {
                "source_id": "maris_brownfields",
                "output_name": "maris_brownfields",
                "warehouse_source_ids": ["maris_brownfields"],
                "normalization": {
                    "label_fields": ["PRIMARY_NA"],
                    "feature_type_fields": ["INTEREST_T"],
                    "original_id_fields": ["REGISTRY_I"],
                },
                "layers": [
                    {
                        "path": str(brownfields_path),
                        "source_layer_id": "brownfields",
                        "source_layer_name": "Brownfields",
                        "warehouse_source_id": "maris_brownfields",
                    }
                ],
            }
        ],
    )

    result = materialize_local_source(project_dir, "maris_brownfields", config_path=config_path)
    source_status = resolve_source_status_set(project_dir)
    constraints = analyze_constraints(project_dir)

    assert result["materialized_count"] == 1
    registered = load_project_source_registry(project_dir).by_source_id()["maris_brownfields"]
    assert registered.path == "layers/maris_brownfields/maris_brownfields.geojson"
    regulated = next(status for status in source_status["statuses"] if status["category"] == "regulated_facilities")
    detail = next(item for item in regulated["source_details"] if item["source_id"] == "maris_brownfields")
    assert regulated["status"] == "provided_locally"
    assert detail["status"] == "local_materialized"
    assert any(constraint["source_id"] == "maris_brownfields" for constraint in constraints["constraints"])


def test_seeded_fema_flood_hazard_materializes_from_configured_shapefile_source(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    flood_path = write_layer(
        tmp_path / "flood.geojson",
        [{"FLD_ZONE": "AE", "ZONE_SUBTY": "Floodway", "GFID": "flood-1", "SFHA_TF": "T"}],
        [wetland_polygon()],
    )
    config_path = write_config(
        tmp_path / "materializers.json",
        [
            {
                "source_id": "fema_nfhl_flood_hazard",
                "output_name": "fema_nfhl_flood_hazard",
                "warehouse_source_ids": ["fema_nfhl_flood_hazard"],
                "layers": [
                    {
                        "path": str(flood_path),
                        "source_layer_id": "flood",
                        "source_layer_name": "Flood Hazard",
                        "warehouse_source_id": "fema_nfhl_flood_hazard",
                    }
                ],
            }
        ],
    )

    result = materialize_local_source(project_dir, "fema_nfhl_flood_hazard", config_path=config_path)
    constraints = analyze_comparison_unit_constraints(project_dir)

    assert result["materialized_count"] == 1
    assert any(constraint["source_id"] == "fema_nfhl_flood_hazard" for constraint in constraints["constraints"])


def test_specific_seeded_nhd_flowline_materializes_as_hydrography_source(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    flowline_path = write_layer(
        tmp_path / "flowlines.geojson",
        [{"gnis_name": "Test Creek", "permanent_": "nhd-1", "ftype": "StreamRiver", "fcode": "46006"}],
        [LineString([(-89.995, 31.999), (-89.995, 32.001)])],
    )
    config_path = write_config(
        tmp_path / "materializers.json",
        [
            {
                "source_id": "usgs_nhd_flowlines",
                "output_name": "usgs_nhd_flowlines",
                "warehouse_source_ids": ["usgs_nhd_flowlines"],
                "normalization": {
                    "label_fields": ["gnis_name"],
                    "feature_type_fields": ["ftype"],
                    "feature_subtype_fields": ["fcode"],
                    "original_id_fields": ["permanent_"],
                },
                "layers": [
                    {
                        "path": str(flowline_path),
                        "source_layer_id": "flowlines",
                        "source_layer_name": "Flowlines",
                        "warehouse_source_id": "usgs_nhd_flowlines",
                    }
                ],
            }
        ],
    )

    result = materialize_local_source(project_dir, "usgs_nhd_flowlines", config_path=config_path)
    constraints = analyze_constraints(project_dir)

    assert result["materialized_count"] == 1
    assert any(constraint["source_id"] == "usgs_nhd_flowlines" for constraint in constraints["constraints"])
    hydro_constraint = next(constraint for constraint in constraints["constraints"] if constraint["source_id"] == "usgs_nhd_flowlines")
    assert hydro_constraint["source_feature_label"] == "Test Creek"


def test_new_mdeq_water_sources_materialize_and_report_project_local_status(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    pws_path = write_layer(
        tmp_path / "pws.geojson",
        [{"Owner_Name": "Test Water System", "PermitNumb": "PWS-1", "Beneficial": "PS"}],
        [Point(-89.995, 32.0002)],
    )
    impaired_line_path = write_layer(
        tmp_path / "impaired_lines.geojson",
        [{"WATER_BODY_NAME": "Test Creek", "review_assist_mdeq_303d_status": "active_303d", "review_assist_list_year": "2024"}],
        [LineString([(-90.0005, 31.9995), (-89.998, 32.001)])],
    )
    impaired_polygon_path = write_layer(
        tmp_path / "impaired_polygons.geojson",
        [{"WATER_BODY_NAME": "Test Lake", "review_assist_mdeq_303d_status": "TMDL complete", "review_assist_list_year": "2024"}],
        [wetland_polygon()],
    )
    config_path = write_config(
        tmp_path / "materializers.json",
        [
            {
                "source_id": "mdeq_public_water_supply_wells",
                "output_name": "mdeq_public_water_supply_wells",
                "warehouse_source_ids": ["mdeq_public_water_supply_wells"],
                "normalization": {
                    "label_fields": ["Owner_Name", "PermitNumb"],
                    "feature_type_fields": ["Beneficial"],
                    "original_id_fields": ["PermitNumb"],
                },
                "layers": [
                    {
                        "path": str(pws_path),
                        "source_layer_id": "pws",
                        "source_layer_name": "Public Water Supply Wells",
                        "warehouse_source_id": "mdeq_public_water_supply_wells",
                    }
                ],
            },
            {
                "source_id": "mdeq_303d_impaired_waters",
                "output_name": "mdeq_303d_impaired_waters",
                "warehouse_source_ids": ["mdeq_303d_impaired_waters"],
                "normalization": {
                    "label_fields": ["WATER_BODY_NAME"],
                    "feature_type_fields": ["review_assist_mdeq_303d_status"],
                    "date_fields": ["review_assist_list_year"],
                },
                "layers": [
                    {
                        "path": str(impaired_line_path),
                        "source_layer_id": "active_lines",
                        "source_layer_name": "Active 303(d) Lines",
                        "warehouse_source_id": "mdeq_303d_impaired_waters",
                    },
                    {
                        "path": str(impaired_polygon_path),
                        "source_layer_id": "tmdl_polygons",
                        "source_layer_name": "TMDL Complete Polygons",
                        "warehouse_source_id": "mdeq_303d_impaired_waters",
                    },
                ],
            },
        ],
    )

    result = materialize_local_sources(project_dir, config_path=config_path)
    registry = load_project_source_registry(project_dir).by_source_id()
    source_status = resolve_source_status_set(project_dir)
    pws_output = project_dir / "layers" / "mdeq_public_water_supply_wells" / "mdeq_public_water_supply_wells.geojson"
    impaired_output = project_dir / "layers" / "mdeq_303d_impaired_waters" / "mdeq_303d_impaired_waters.geojson"
    transportation = next(status for status in source_status["statuses"] if status["category"] == "transportation_utilities")
    water_quality = next(status for status in source_status["statuses"] if status["category"] == "water_quality")
    pws_detail = next(detail for detail in transportation["source_details"] if detail["source_id"] == "mdeq_public_water_supply_wells")
    impaired_detail = next(detail for detail in water_quality["source_details"] if detail["source_id"] == "mdeq_303d_impaired_waters")

    assert result["materialized_count"] == 2
    assert pws_output.exists()
    assert impaired_output.exists()
    assert set(gpd.read_file(impaired_output).geometry.geom_type) == {"LineString", "Polygon"}
    assert registry["mdeq_public_water_supply_wells"].status == "local_materialized"
    assert registry["mdeq_303d_impaired_waters"].status == "local_materialized"
    assert pws_detail["status"] == "local_materialized"
    assert impaired_detail["status"] == "local_materialized"
    assert water_quality["status"] == "provided_locally"
    assert water_quality["report_caveat_flags"] == []


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


def test_materializer_registers_existing_project_layer_without_replace(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    existing_output = project_dir / "layers" / "usfws_nwi_wetlands" / "usfws_nwi_wetlands.geojson"
    existing_output.parent.mkdir(parents=True)
    write_layer(existing_output, [{"ATTRIBUTE": "Freshwater Pond", "NWI_ID": "nwi-1"}], [wetland_polygon()])
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": "usfws_nwi_wetlands",
                        "enabled": False,
                        "access_method": "local_file",
                        "path": None,
                        "role": "wetland_and_waterbody_screening",
                        "buffer_feet": None,
                        "notes": "Stale path-null registry entry.",
                        "status": "candidate_needs_local_layer",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    config_path = write_config(tmp_path / "materializers.json", [materializer_entry("usfws_nwi_wetlands", tmp_path / "missing.geojson")])

    result = materialize_local_source(project_dir, "usfws_nwi_wetlands", config_path=config_path)

    assert result["materialized_count"] == 1
    assert result["registered_existing_count"] == 1
    assert result["sources"][0]["status"] == "registered_existing_output"
    assert result["sources"][0]["feature_count"] == 1
    registered = load_project_source_registry(project_dir).by_source_id()["usfws_nwi_wetlands"]
    assert registered.enabled is True
    assert registered.status == "local_materialized"
    assert registered.path == "layers/usfws_nwi_wetlands/usfws_nwi_wetlands.geojson"
    assert existing_output.exists()


def test_existing_project_layer_recovery_feeds_deliverable_pipeline(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    existing_output = project_dir / "layers" / "usfws_nwi_wetlands" / "usfws_nwi_wetlands.geojson"
    existing_output.parent.mkdir(parents=True)
    write_layer(
        existing_output,
        [{"ATTRIBUTE": "Freshwater Pond", "WETLAND_TYPE": "Freshwater Pond", "NWI_ID": "nwi-1"}],
        [wetland_polygon()],
    )
    config_path = write_config(tmp_path / "materializers.json", [materializer_entry("usfws_nwi_wetlands", tmp_path / "missing.geojson")])

    materialize_local_sources(project_dir, config_path=config_path)
    source_status = resolve_source_status_set(project_dir)
    constraints = analyze_constraints(project_dir)
    build_comparison_units(project_dir)
    comparison_constraints = analyze_comparison_unit_constraints(project_dir)
    tables = generate_deliverable_tables(project_dir)
    figures = generate_deliverable_figures(project_dir)
    build_evidence_package(project_dir)
    items = generate_deliverable_items(project_dir, gpt_drafting=False)
    queue = generate_review_queue(project_dir)

    wetlands_status = next(status for status in source_status["statuses"] if status["category"] == "wetlands_waterbodies")
    assert wetlands_status["status"] == "provided_locally"
    assert wetlands_status["local_paths"] == [str(existing_output.resolve())]
    assert constraints["constraint_count"] > 0
    assert comparison_constraints["constraint_count"] > 0
    wetlands_table = next(table for table in tables["tables"] if table["table_id"] == "table-wetlands-waterbodies")
    assert wetlands_table["rows"]
    assert "usfws_nwi_wetlands" in wetlands_table["source_refs"]
    wetlands_figure = next(figure for figure in figures["figures"] if figure["figure_id"] == "figure-wetlands-waterbodies")
    assert wetlands_figure["image_path"]
    figure_path = Path(wetlands_figure["image_path"])
    if not figure_path.is_absolute():
        figure_path = project_dir / figure_path
    assert figure_path.exists()
    wetlands_item = next(item for item in items["items"] if item["deliverable_item_id"] == "wetlands-and-waterbodies")
    assert "usfws_nwi_wetlands" in wetlands_item["source_refs"]
    queue_item = next(item for item in queue["items"] if item["id"] == "wetlands-and-waterbodies")
    assert "usfws_nwi_wetlands" in queue_item["source_refs"]
    assert "Empty stub for future implements whenever source data is accessible." not in queue_item["generated_content"]


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
