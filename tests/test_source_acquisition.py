from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from review_assist import source_acquisition
from review_assist.cli import main
from review_assist.constraints import analyze_constraints
from review_assist.findings import generate_draft_findings
from review_assist.maps import generate_maps
from review_assist.populate_for_review import populate_for_review
from review_assist.report_sections import generate_report_sections
from review_assist.review_queue import generate_review_queue
from review_assist.source_acquisition import download_source, prepare_sources, resolve_source_gaps
from review_assist.source_catalog import load_project_source_registry
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
                "inputs": [
                    {
                        "path": "inputs/routes.kmz",
                        "role": "alternatives",
                        "description": "Synthetic route input",
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


def write_layer(path: Path, geometries: list[object], rows: list[dict[str, object]]) -> Path:
    gdf = gpd.GeoDataFrame(rows, geometry=geometries, crs="EPSG:4326")
    path.write_text(gdf.to_json(drop_id=True), encoding="utf-8")
    return path


def write_registry(project_dir: Path, source_id: str, source_path: str, *, status: str = "local_registered") -> None:
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": source_id,
                        "enabled": True,
                        "access_method": "local_file",
                        "path": source_path,
                        "role": "constraint_screening",
                        "buffer_feet": None,
                        "notes": "Local test source",
                        "status": status,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def source_gap(manifest: dict[str, Any], source_id: str) -> dict[str, Any]:
    return next(gap for gap in manifest["gaps"] if gap.get("source_id") == source_id)


def fake_nwi_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/0"):
        return {"maxRecordCount": 1}
    offset = int(params.get("resultOffset", 0))
    if offset:
        return {"type": "FeatureCollection", "features": []}
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Mock NWI Wetland", "ATTRIBUTE": "Freshwater Forested/Shrub Wetland"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-90.001, 31.999],
                            [-89.998, 31.999],
                            [-89.998, 32.001],
                            [-90.001, 32.001],
                            [-90.001, 31.999],
                        ]
                    ],
                },
            }
        ],
    }


def fake_nhd_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/6") or url.endswith("/9"):
        return {"maxRecordCount": 1}
    offset = int(params.get("resultOffset", 0))
    if offset:
        return {"type": "FeatureCollection", "features": []}
    if url.endswith("/6/query"):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"gnis_name": "Mock NHD Stream", "ftype": 460, "fcode": 46006},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-89.995, 31.999], [-89.995, 32.001]],
                    },
                }
            ],
        }
    if url.endswith("/9/query"):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"GNIS_NAME": "Mock NHD Waterbody", "FTYPE": 390, "FCODE": 39004},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-90.001, 31.9995],
                                [-89.999, 31.9995],
                                [-89.999, 32.0005],
                                [-90.001, 32.0005],
                                [-90.001, 31.9995],
                            ]
                        ],
                    },
                }
            ],
        }
    raise AssertionError(f"Unexpected NHD fetch URL: {url}")


def fake_fema_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/28"):
        return {"maxRecordCount": 2}
    offset = int(params.get("resultOffset", 0))
    if offset:
        return {"type": "FeatureCollection", "features": []}
    if url.endswith("/28/query"):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "FLD_ZONE": "AE",
                        "ZONE_SUBTY": "FLOODWAY",
                        "SFHA_TF": "T",
                        "STATIC_BFE": 101.5,
                        "V_DATUM": "NAVD88",
                        "DEPTH": 2.0,
                        "LEN_UNIT": "feet",
                        "SOURCE_CIT": "Mock FEMA NFHL",
                        "GFID": "fema-zone-1",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-90.001, 31.999],
                                [-89.998, 31.999],
                                [-89.998, 32.001],
                                [-90.001, 32.001],
                                [-90.001, 31.999],
                            ]
                        ],
                    },
                }
            ],
        }
    raise AssertionError(f"Unexpected FEMA fetch URL: {url}")


def fake_echo_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/0"):
        return {"maxRecordCount": 2}
    offset = int(params.get("resultOffset", 0))
    if offset:
        return {"type": "FeatureCollection", "features": []}
    if url.endswith("/0/query"):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "REGISTRY_ID": "110000000001",
                        "FAC_NAME": "Mock ECHO Facility",
                        "FAC_STREET": "100 Test Road",
                        "FAC_CITY": "Jackson",
                        "FAC_STATE": "MS",
                        "FAC_ZIP": "39201",
                        "FAC_COUNTY": "Hinds",
                        "FAC_ACTIVE_FLAG": "Y",
                        "FAC_MAJOR_FLAG": "N",
                        "FAC_CURR_COMPLIANCE_STATUS": "No Violation Identified",
                        "FAC_CURR_SNC_FLG": "N",
                        "FAC_INSPECTION_COUNT": 2,
                        "FAC_DATE_LAST_INSPECTION": "20250115",
                        "FAC_FORMAL_ACTION_COUNT": 0,
                        "FAC_INFORMAL_COUNT": 1,
                        "FAC_TOTAL_PENALTIES": 0,
                        "FAC_COLLECTION_METHOD": "ADDRESS MATCHING-HOUSE NUMBER",
                        "FAC_ACCURACY_METERS": 25,
                        "AIR_FLAG": "Y",
                        "NPDES_FLAG": "N",
                        "RCRA_FLAG": "Y",
                        "TRI_FLAG": "N",
                        "SDWIS_FLAG": "N",
                        "GHG_FLAG": "N",
                        "DFR_URL": "https://echo.epa.gov/detailed-facility-report?fid=110000000001",
                    },
                    "geometry": {"type": "Point", "coordinates": [-89.995, 32.0002]},
                }
            ],
        }
    raise AssertionError(f"Unexpected ECHO fetch URL: {url}")


def fake_critical_habitat_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/0") or url.endswith("/2"):
        return {"maxRecordCount": 1}
    offset = int(params.get("resultOffset", 0))
    if offset:
        return {"type": "FeatureCollection", "features": []}
    if url.endswith("/0/query"):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "comname": "Mock Mussel",
                        "sciname": "Musselus testus",
                        "status": "FINAL",
                        "listing_status": "Endangered",
                        "unitname": "Unit 1",
                        "subunitname": "Subunit A",
                        "fedreg": "88FR12345",
                        "pubdate": "20240101",
                        "effectdate": "20240201",
                        "accuracy": "Source Adjustment",
                        "GlobalID": "critical-final-1",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-90.001, 31.999],
                                [-89.998, 31.999],
                                [-89.998, 32.001],
                                [-90.001, 32.001],
                                [-90.001, 31.999],
                            ]
                        ],
                    },
                }
            ],
        }
    if url.endswith("/2/query"):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "comname": "Mock Bat",
                        "sciname": "Battus testus",
                        "status": "PROPOSED",
                        "listing_status": "Threatened",
                        "unit": "Unit 2",
                        "subunit": "Subunit B",
                        "fedreg": "89FR54321",
                        "pubdate": "20240301",
                        "effectdate": "20240401",
                        "accuracy": "Tidal Adjustment",
                        "OBJECTID": 22,
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-90.0005, 31.9995],
                                [-89.999, 31.9995],
                                [-89.999, 32.0005],
                                [-90.0005, 32.0005],
                                [-90.0005, 31.9995],
                            ]
                        ],
                    },
                }
            ],
        }
    raise AssertionError(f"Unexpected Critical Habitat fetch URL: {url}")


def fake_supported_source_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if "/Wetlands/MapServer" in url:
        return fake_nwi_fetch(url, params)
    if "/nhd/MapServer" in url:
        return fake_nhd_fetch(url, params)
    if "/USFWS_Critical_Habitat/FeatureServer" in url:
        return fake_critical_habitat_fetch(url, params)
    if "/ECHO/Facilities/MapServer" in url:
        return fake_echo_fetch(url, params)
    raise AssertionError(f"Unexpected source fetch URL: {url}")


def fake_supported_source_fetch_with_optional(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if "/NFHL/MapServer" in url:
        return fake_fema_fetch(url, params)
    return fake_supported_source_fetch(url, params)


def fake_empty_nhd_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/6") or url.endswith("/9"):
        return {"maxRecordCount": 1}
    if url.endswith("/6/query") or url.endswith("/9/query"):
        return {"type": "FeatureCollection", "features": []}
    raise AssertionError(f"Unexpected NHD fetch URL: {url}")


def fake_empty_fema_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/28"):
        return {"maxRecordCount": 2}
    if url.endswith("/28/query"):
        return {"type": "FeatureCollection", "features": []}
    raise AssertionError(f"Unexpected FEMA fetch URL: {url}")


def fake_empty_critical_habitat_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/0") or url.endswith("/2"):
        return {"maxRecordCount": 1}
    if url.endswith("/0/query") or url.endswith("/2/query"):
        return {"type": "FeatureCollection", "features": []}
    raise AssertionError(f"Unexpected Critical Habitat fetch URL: {url}")


def fake_empty_echo_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/0"):
        return {"maxRecordCount": 2}
    if url.endswith("/0/query"):
        return {"type": "FeatureCollection", "features": []}
    raise AssertionError(f"Unexpected ECHO fetch URL: {url}")


def fake_no_overlap_critical_habitat_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/0") or url.endswith("/2"):
        return {"maxRecordCount": 1}
    offset = int(params.get("resultOffset", 0))
    if offset or url.endswith("/2/query"):
        return {"type": "FeatureCollection", "features": []}
    if url.endswith("/0/query"):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"comname": "Far Species", "sciname": "Species farus", "status": "FINAL"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-89.0, 33.0], [-88.9, 33.0], [-88.9, 33.1], [-89.0, 33.1], [-89.0, 33.0]]],
                    },
                }
            ],
        }
    raise AssertionError(f"Unexpected Critical Habitat fetch URL: {url}")


def fake_no_overlap_echo_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/0"):
        return {"maxRecordCount": 1}
    offset = int(params.get("resultOffset", 0))
    if offset:
        return {"type": "FeatureCollection", "features": []}
    if url.endswith("/0/query"):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"REGISTRY_ID": "far-echo", "FAC_NAME": "Far ECHO Facility", "RCRA_FLAG": "Y"},
                    "geometry": {"type": "Point", "coordinates": [-89.0, 33.0]},
                }
            ],
        }
    raise AssertionError(f"Unexpected ECHO fetch URL: {url}")


def test_gap_resolver_marks_unregistered_nwi_downloadable(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = resolve_source_gaps(project_dir)

    assert source_gap(result, "usfws_nwi_wetlands")["status"] == "downloadable"
    assert (project_dir / "source_acquisition" / "source_acquisition_manifest.json").exists()


def test_gap_resolver_marks_unregistered_nhd_downloadable(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = resolve_source_gaps(project_dir)

    assert source_gap(result, "usgs_nhd_hydrography")["status"] == "downloadable"


def test_gap_resolver_marks_unregistered_critical_habitat_downloadable(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = resolve_source_gaps(project_dir)
    gap = source_gap(result, "usfws_critical_habitat")

    assert gap["status"] == "downloadable"
    assert gap["download_supported"] is True


def test_gap_resolver_marks_unregistered_echo_downloadable(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = resolve_source_gaps(project_dir)
    gap = source_gap(result, "epa_envirofacts_echo")

    assert gap["status"] == "downloadable"
    assert gap["download_supported"] is True


def test_gap_resolver_marks_fema_optional_but_download_supported(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = resolve_source_gaps(project_dir)
    gap = source_gap(result, "fema_nfhl_flood_hazard")

    assert gap["status"] == "optional"
    assert gap["requirement"] == "optional"
    assert gap["download_supported"] is True


def test_gap_resolver_marks_tagged_project_input_as_provided_source(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "inputs" / "provided_nwi.geojson", [Point(-89.995, 32.0)], [{"name": "Provided wetland point"}])
    manifest_path = project_dir / "config" / "project.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inputs"].append(
        {
            "path": "inputs/provided_nwi.geojson",
            "role": "source_layer",
            "description": "Provided NWI-style source layer",
            "source_id": "usfws_nwi_wetlands",
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = resolve_source_gaps(project_dir)

    assert source_gap(result, "usfws_nwi_wetlands")["status"] == "provided_in_input"
    source = load_project_source_registry(project_dir).by_source_id()["usfws_nwi_wetlands"]
    assert source.path == "inputs/provided_nwi.geojson"
    assert source.status == "provided_in_input"


def test_successful_nwi_downloader_writes_geojson_provenance_checksum_and_registry(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = download_source(project_dir, "usfws_nwi_wetlands", fetch_json=fake_nwi_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["usfws_nwi_wetlands"]

    assert download["status"] == "downloaded"
    assert download["feature_count"] == 1
    assert download["checksum_sha256"]
    assert Path(download["output_path"]).exists()
    assert registry_source.access_method == "local_file"
    assert registry_source.status == "downloaded"
    assert registry_source.path == "source_acquisition/downloads/usfws_nwi_wetlands.geojson"


def test_successful_nhd_downloader_writes_combined_geojson_normalized_fields_and_registry(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = download_source(project_dir, "usgs_nhd_hydrography", fetch_json=fake_nhd_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["usgs_nhd_hydrography"]
    output_path = Path(download["output_path"])
    gdf = gpd.read_file(output_path)

    assert download["status"] == "downloaded"
    assert download["feature_count"] == 2
    assert [layer["feature_count"] for layer in download["layers"]] == [1, 1]
    assert download["checksum_sha256"]
    assert output_path.exists()
    assert registry_source.access_method == "local_file"
    assert registry_source.status == "downloaded"
    assert registry_source.path == "source_acquisition/downloads/usgs_nhd_hydrography.geojson"
    assert set(gdf["review_assist_source_id"]) == {"usgs_nhd_hydrography"}
    assert set(gdf["review_assist_layer_name"]) == {"Flowline - Large Scale", "Area - Large Scale"}
    assert "Mock NHD Stream" in set(gdf["review_assist_feature_label"])
    assert "review_assist_feature_subtype" in gdf.columns
    assert "review_assist_feature_original_id" in gdf.columns


def test_successful_fema_downloader_writes_geojson_normalized_fields_and_registry(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = download_source(project_dir, "fema_nfhl_flood_hazard", fetch_json=fake_fema_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["fema_nfhl_flood_hazard"]
    output_path = Path(download["output_path"])
    gdf = gpd.read_file(output_path)

    assert download["status"] == "downloaded"
    assert download["feature_count"] == 1
    assert download["layer_id"] == 28
    assert download["layers"][0]["layer_name"] == "Flood Hazard Zones"
    assert download["layers"][0]["service_record_limit"] == 2
    assert download["checksum_sha256"]
    assert output_path.exists()
    assert registry_source.access_method == "local_file"
    assert registry_source.status == "downloaded"
    assert registry_source.path == "source_acquisition/downloads/fema_nfhl_flood_hazard.geojson"
    assert set(gdf["review_assist_source_id"]) == {"fema_nfhl_flood_hazard"}
    assert set(gdf["review_assist_feature_label"]) == {"AE"}
    assert set(gdf["review_assist_feature_type"]) == {"AE"}
    assert set(gdf["review_assist_feature_subtype"]) == {"FLOODWAY"}
    assert set(gdf["review_assist_quality_flag"]) == {"T"}
    assert set(gdf["review_assist_source_citation"]) == {"Mock FEMA NFHL"}


def test_successful_critical_habitat_downloader_writes_combined_geojson_normalized_fields_and_registry(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = download_source(project_dir, "usfws_critical_habitat", fetch_json=fake_critical_habitat_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["usfws_critical_habitat"]
    output_path = Path(download["output_path"])
    gdf = gpd.read_file(output_path)

    assert download["status"] == "downloaded"
    assert download["feature_count"] == 2
    assert [layer["feature_count"] for layer in download["layers"]] == [1, 1]
    assert [layer["layer_id"] for layer in download["layers"]] == [0, 2]
    assert download["checksum_sha256"]
    assert output_path.exists()
    assert registry_source.access_method == "local_file"
    assert registry_source.status == "downloaded"
    assert registry_source.path == "source_acquisition/downloads/usfws_critical_habitat.geojson"
    assert set(gdf["review_assist_source_id"]) == {"usfws_critical_habitat"}
    assert set(gdf["review_assist_layer_name"]) == {"Final Critical Habitat Features", "Proposed Critical Habitat Features"}
    assert {"Mock Mussel", "Mock Bat"}.issubset(set(gdf["review_assist_feature_label"]))
    assert {"FINAL", "PROPOSED"}.issubset(set(gdf["review_assist_feature_type"]))
    assert {"88FR12345", "89FR54321"}.issubset(set(gdf["review_assist_source_citation"]))


def test_successful_echo_downloader_writes_geojson_normalized_fields_and_registry(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = download_source(project_dir, "epa_envirofacts_echo", fetch_json=fake_echo_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["epa_envirofacts_echo"]
    output_path = Path(download["output_path"])
    gdf = gpd.read_file(output_path)

    assert download["status"] == "downloaded"
    assert download["feature_count"] == 1
    assert download["layer_id"] == 0
    assert download["layers"][0]["layer_name"] == "All ECHO Facilities"
    assert download["checksum_sha256"]
    assert output_path.exists()
    assert registry_source.access_method == "local_file"
    assert registry_source.status == "downloaded"
    assert registry_source.path == "source_acquisition/downloads/epa_envirofacts_echo.geojson"
    assert set(gdf["review_assist_source_id"]) == {"epa_envirofacts_echo"}
    assert set(gdf["review_assist_feature_label"]) == {"Mock ECHO Facility"}
    assert "AIR" in str(gdf["review_assist_feature_type"].iloc[0])
    assert "RCRA" in str(gdf["review_assist_feature_type"].iloc[0])
    assert set(gdf["review_assist_feature_original_id"]) == {"110000000001"}
    assert set(gdf["review_assist_source_citation"]) == {"https://echo.epa.gov/detailed-facility-report?fid=110000000001"}


def test_failed_nwi_downloader_records_nonfatal_failed_status(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    def failing_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("network unavailable")

    result = download_source(project_dir, "usfws_nwi_wetlands", fetch_json=failing_fetch)
    download = result["downloads"][-1]

    assert download["status"] == "failed"
    assert download["validation_issues"][0]["code"] == "source_download_failed"
    assert source_gap(result, "usfws_nwi_wetlands")["status"] == "failed"

    source_status = resolve_source_status_set(project_dir)
    wetlands_status = next(item for item in source_status["statuses"] if item["category"] == "wetlands_waterbodies")
    assert wetlands_status["status"] == "failed"
    assert "source_download_failed" in wetlands_status["uncertainty_flags"]

    findings = generate_draft_findings(project_dir)
    failed_finding = next(item for item in findings["findings"] if item["resource_category"] == "wetlands_waterbodies")
    assert failed_finding["assumptions"]["source_status"] == "failed"

    queue = generate_review_queue(project_dir)
    missing_item = next(item for item in queue["items"] if item["id"] == "missing-data-wetlands-waterbodies")
    assert missing_item["assumptions"]["source_status"] == "failed"


def test_failed_nhd_downloader_records_nonfatal_failed_status(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    def failing_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("network unavailable")

    result = download_source(project_dir, "usgs_nhd_hydrography", fetch_json=failing_fetch)
    download = result["downloads"][-1]

    assert download["status"] == "failed"
    assert download["validation_issues"][0]["code"] == "source_download_failed"
    assert source_gap(result, "usgs_nhd_hydrography")["status"] == "failed"

    source_status = resolve_source_status_set(project_dir)
    hydrography_status = next(item for item in source_status["statuses"] if item["category"] == "hydrography_crossings")
    assert hydrography_status["status"] == "failed"
    assert "source_download_failed" in hydrography_status["uncertainty_flags"]

    findings = generate_draft_findings(project_dir)
    failed_finding = next(item for item in findings["findings"] if item["resource_category"] == "hydrography_crossings")
    assert failed_finding["assumptions"]["source_status"] == "failed"


def test_failed_fema_downloader_records_nonfatal_failed_status_and_caveats(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    def failing_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("network unavailable")

    result = download_source(project_dir, "fema_nfhl_flood_hazard", fetch_json=failing_fetch)
    download = result["downloads"][-1]

    assert download["status"] == "failed"
    assert download["validation_issues"][0]["code"] == "source_download_failed"
    assert source_gap(result, "fema_nfhl_flood_hazard")["status"] == "failed"

    source_status = resolve_source_status_set(project_dir)
    flood_status = next(item for item in source_status["statuses"] if item["category"] == "flood_hazard")
    assert flood_status["status"] == "failed"
    assert "source_download_failed" in flood_status["uncertainty_flags"]

    findings = generate_draft_findings(project_dir)
    failed_finding = next(item for item in findings["findings"] if item["resource_category"] == "flood_hazard")
    assert failed_finding["assumptions"]["source_status"] == "failed"

    sections = generate_report_sections(project_dir)
    flood_section = next(section for section in sections["sections"] if section["section_id"] == "flood-hazard")
    assert flood_section["review_status"] == "needs_review"
    assert "source_download_failed" in flood_section["uncertainty_flags"]

    queue = generate_review_queue(project_dir)
    missing_item = next(item for item in queue["items"] if item["id"] == "missing-data-flood-hazard")
    assert missing_item["assumptions"]["source_status"] == "failed"


def test_failed_critical_habitat_downloader_records_nonfatal_failed_status_and_caveats(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    def failing_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("network unavailable")

    result = download_source(project_dir, "usfws_critical_habitat", fetch_json=failing_fetch)
    download = result["downloads"][-1]

    assert download["status"] == "failed"
    assert download["validation_issues"][0]["code"] == "source_download_failed"
    assert source_gap(result, "usfws_critical_habitat")["status"] == "failed"

    source_status = resolve_source_status_set(project_dir)
    species_status = next(item for item in source_status["statuses"] if item["category"] == "species_habitat")
    assert species_status["status"] == "failed"
    assert "source_download_failed" in species_status["uncertainty_flags"]

    findings = generate_draft_findings(project_dir)
    failed_finding = next(item for item in findings["findings"] if item["resource_category"] == "species_habitat")
    assert failed_finding["assumptions"]["source_status"] == "failed"

    sections = generate_report_sections(project_dir)
    species_section = next(section for section in sections["sections"] if section["section_id"] == "species-and-habitat")
    assert species_section["review_status"] == "needs_review"
    assert "source_download_failed" in species_section["uncertainty_flags"]

    queue = generate_review_queue(project_dir)
    missing_item = next(item for item in queue["items"] if item["id"] == "missing-data-species-habitat")
    assert missing_item["assumptions"]["source_status"] == "failed"


def test_failed_echo_downloader_records_nonfatal_failed_status_and_caveats(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    def failing_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("network unavailable")

    result = download_source(project_dir, "epa_envirofacts_echo", fetch_json=failing_fetch)
    download = result["downloads"][-1]

    assert download["status"] == "failed"
    assert download["validation_issues"][0]["code"] == "source_download_failed"
    assert source_gap(result, "epa_envirofacts_echo")["status"] == "failed"

    source_status = resolve_source_status_set(project_dir)
    regulated_status = next(item for item in source_status["statuses"] if item["category"] == "regulated_facilities")
    assert regulated_status["status"] == "failed"
    assert "source_download_failed" in regulated_status["uncertainty_flags"]

    findings = generate_draft_findings(project_dir)
    failed_finding = next(item for item in findings["findings"] if item["resource_category"] == "regulated_facilities")
    assert failed_finding["assumptions"]["source_status"] == "failed"

    sections = generate_report_sections(project_dir)
    regulated_section = next(section for section in sections["sections"] if section["section_id"] == "regulated-facilities")
    assert regulated_section["review_status"] == "needs_review"
    assert "source_download_failed" in regulated_section["uncertainty_flags"]

    queue = generate_review_queue(project_dir)
    missing_item = next(item for item in queue["items"] if item["id"] == "missing-data-regulated-facilities")
    assert missing_item["assumptions"]["source_status"] == "failed"


def test_empty_nhd_downloader_writes_valid_empty_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = download_source(project_dir, "usgs_nhd_hydrography", fetch_json=fake_empty_nhd_fetch)
    download = result["downloads"][-1]
    constraints = analyze_constraints(project_dir)

    assert download["status"] == "downloaded"
    assert download["feature_count"] == 0
    assert download["warnings"][0]["code"] == "downloaded_source_empty"
    assert Path(download["output_path"]).exists()
    assert constraints["constraint_count"] == 0
    assert constraints["sources"][0]["status"] == "analyzed_empty"


def test_empty_fema_downloader_writes_valid_empty_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = download_source(project_dir, "fema_nfhl_flood_hazard", fetch_json=fake_empty_fema_fetch)
    download = result["downloads"][-1]
    constraints = analyze_constraints(project_dir)

    assert download["status"] == "downloaded"
    assert download["feature_count"] == 0
    assert download["warnings"][0]["code"] == "downloaded_source_empty"
    assert Path(download["output_path"]).exists()
    assert constraints["constraint_count"] == 0
    assert constraints["sources"][0]["status"] == "analyzed_empty"


def test_empty_critical_habitat_downloader_writes_valid_empty_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = download_source(project_dir, "usfws_critical_habitat", fetch_json=fake_empty_critical_habitat_fetch)
    download = result["downloads"][-1]
    constraints = analyze_constraints(project_dir)

    assert download["status"] == "downloaded"
    assert download["feature_count"] == 0
    assert download["warnings"][0]["code"] == "downloaded_source_empty"
    assert Path(download["output_path"]).exists()
    assert constraints["constraint_count"] == 0
    assert constraints["sources"][0]["status"] == "analyzed_empty"


def test_empty_echo_downloader_writes_valid_empty_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = download_source(project_dir, "epa_envirofacts_echo", fetch_json=fake_empty_echo_fetch)
    download = result["downloads"][-1]
    constraints = analyze_constraints(project_dir)

    assert download["status"] == "downloaded"
    assert download["feature_count"] == 0
    assert download["warnings"][0]["code"] == "downloaded_source_empty"
    assert Path(download["output_path"]).exists()
    assert constraints["constraint_count"] == 0
    assert constraints["sources"][0]["status"] == "analyzed_empty"


def test_no_overlap_critical_habitat_produces_no_mapped_context(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    download_source(project_dir, "usfws_critical_habitat", fetch_json=fake_no_overlap_critical_habitat_fetch)
    constraints = analyze_constraints(project_dir)
    findings = generate_draft_findings(project_dir)

    source = next(item for item in constraints["sources"] if item["source_id"] == "usfws_critical_habitat")
    assert source["status"] == "analyzed"
    assert source["constraint_count"] == 0
    assert any(
        item["type"] == "no_mapped_conflict_identified" and item["resource_category"] == "species_habitat"
        for item in findings["findings"]
    )


def test_no_overlap_echo_produces_no_mapped_context(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    download_source(project_dir, "epa_envirofacts_echo", fetch_json=fake_no_overlap_echo_fetch)
    constraints = analyze_constraints(project_dir)
    findings = generate_draft_findings(project_dir)

    source = next(item for item in constraints["sources"] if item["source_id"] == "epa_envirofacts_echo")
    assert source["status"] == "analyzed"
    assert source["constraint_count"] == 0
    assert any(
        item["type"] == "no_mapped_conflict_identified" and item["resource_category"] == "regulated_facilities"
        for item in findings["findings"]
    )


def test_existing_local_registered_source_is_not_overwritten_by_download(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "wetlands.geojson", [Point(-89.995, 32.0)], [{"name": "Local wetland"}])
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")

    result = download_source(project_dir, "usfws_nwi_wetlands", fetch_json=fake_nwi_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["usfws_nwi_wetlands"]

    assert download["status"] == "skipped_existing_local"
    assert registry_source.path == "wetlands.geojson"
    assert registry_source.status == "local_registered"


def test_existing_local_hydrography_source_is_not_overwritten_by_download(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "streams.geojson", [LineString([(-89.995, 31.999), (-89.995, 32.001)])], [{"name": "Local stream"}])
    write_registry(project_dir, "usgs_nhd_hydrography", "streams.geojson")

    result = download_source(project_dir, "usgs_nhd_hydrography", fetch_json=fake_nhd_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["usgs_nhd_hydrography"]

    assert download["status"] == "skipped_existing_local"
    assert registry_source.path == "streams.geojson"
    assert registry_source.status == "local_registered"


def test_existing_local_flood_hazard_source_is_not_overwritten_by_download(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "flood.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"FLD_ZONE": "X"}],
    )
    write_registry(project_dir, "fema_nfhl_flood_hazard", "flood.geojson")

    result = download_source(project_dir, "fema_nfhl_flood_hazard", fetch_json=fake_fema_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["fema_nfhl_flood_hazard"]

    assert download["status"] == "skipped_existing_local"
    assert registry_source.path == "flood.geojson"
    assert registry_source.status == "local_registered"


def test_existing_local_critical_habitat_source_is_not_overwritten_by_download(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "critical.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"comname": "Local critical habitat"}],
    )
    write_registry(project_dir, "usfws_critical_habitat", "critical.geojson")

    result = download_source(project_dir, "usfws_critical_habitat", fetch_json=fake_critical_habitat_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["usfws_critical_habitat"]

    assert download["status"] == "skipped_existing_local"
    assert registry_source.path == "critical.geojson"
    assert registry_source.status == "local_registered"


def test_existing_local_echo_source_is_not_overwritten_by_download(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "echo.geojson", [Point(-89.995, 32.0002)], [{"FAC_NAME": "Local ECHO Facility"}])
    write_registry(project_dir, "epa_envirofacts_echo", "echo.geojson")

    result = download_source(project_dir, "epa_envirofacts_echo", fetch_json=fake_echo_fetch)
    download = result["downloads"][-1]
    registry_source = load_project_source_registry(project_dir).by_source_id()["epa_envirofacts_echo"]

    assert download["status"] == "skipped_existing_local"
    assert registry_source.path == "echo.geojson"
    assert registry_source.status == "local_registered"


def test_prepare_sources_feeds_downloaded_sources_into_constraints_findings_tables_and_maps(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    acquisition = prepare_sources(project_dir, fetch_json=fake_supported_source_fetch)
    constraints = analyze_constraints(project_dir)
    findings = generate_draft_findings(project_dir)
    tables = generate_comparison_tables(project_dir)
    maps = generate_maps(project_dir)
    sections = generate_report_sections(project_dir)
    queue = generate_review_queue(project_dir)

    assert source_gap(acquisition, "usfws_nwi_wetlands")["status"] == "downloaded"
    assert source_gap(acquisition, "usgs_nhd_hydrography")["status"] == "downloaded"
    assert source_gap(acquisition, "usfws_critical_habitat")["status"] == "downloaded"
    assert source_gap(acquisition, "epa_envirofacts_echo")["status"] == "downloaded"
    assert constraints["constraint_count"] >= 6
    assert any(item["relationship_type"] == "crosses" and item["source_id"] == "usgs_nhd_hydrography" for item in constraints["constraints"])
    assert any(item["source_id"] == "usfws_critical_habitat" for item in constraints["constraints"])
    assert any(item["source_id"] == "epa_envirofacts_echo" for item in constraints["constraints"])
    assert any("Mock NWI Wetland" in finding["summary"] or "Mock NWI Wetland" in finding["details"] for finding in findings["findings"])
    assert any("Mock NHD Stream" in finding["summary"] or "Mock NHD Stream" in finding["details"] for finding in findings["findings"])
    assert any("Mock Mussel" in finding["summary"] or "Mock Mussel" in finding["details"] for finding in findings["findings"])
    assert any("Mock ECHO Facility" in finding["summary"] or "Mock ECHO Facility" in finding["details"] for finding in findings["findings"])
    hydrography_table = next(table for table in tables["tables"] if table["table_id"] == "hydrography-crossing-summary")
    critical_table = next(table for table in tables["tables"] if table["table_id"] == "critical-habitat-summary")
    regulated_table = next(table for table in tables["tables"] if table["table_id"] == "regulated-facility-summary")
    assert hydrography_table["row_count"] >= 2
    assert critical_table["row_count"] >= 2
    assert critical_table["rows"][0]["species_common_name"] in {"Mock Mussel", "Mock Bat"}
    assert regulated_table["row_count"] >= 1
    assert regulated_table["rows"][0]["facility_name"] == "Mock ECHO Facility"
    assert regulated_table["rows"][0]["registry_id"] == "110000000001"
    assert "AIR" in regulated_table["rows"][0]["program_flags"]
    assert "RCRA" in regulated_table["rows"][0]["program_flags"]
    assert regulated_table["rows"][0]["dfr_url"].startswith("https://echo.epa.gov/")
    assert maps["figure_count"] > 0
    assert any(figure["figure_id"] == "source-context-usgs-nhd-hydrography" for figure in maps["figures"])
    assert any(figure["figure_id"] == "source-context-usfws-critical-habitat" for figure in maps["figures"])
    assert any(figure["figure_id"] == "source-context-epa-envirofacts-echo" for figure in maps["figures"])
    hydrography_section = next(section for section in sections["sections"] if section["resource_category"] == "hydrography_crossings")
    species_section = next(section for section in sections["sections"] if section["resource_category"] == "species_habitat")
    regulated_section = next(section for section in sections["sections"] if section["resource_category"] == "regulated_facilities")
    assert "hydrography-crossing-summary" in hydrography_section["related_table_ids"]
    assert "source-context-usgs-nhd-hydrography" in hydrography_section["related_figure_ids"]
    assert "critical-habitat-summary" in species_section["related_table_ids"]
    assert "source-context-usfws-critical-habitat" in species_section["related_figure_ids"]
    assert "critical-habitat-summary" in str(species_section["generated_content"])
    assert "regulated-facility-summary" in regulated_section["related_table_ids"]
    assert "source-context-epa-envirofacts-echo" in regulated_section["related_figure_ids"]
    assert "regulated-facility-summary" in str(regulated_section["generated_content"])
    assert any(item["type"] == "report_section" and item["source_refs"] == ["usgs_nhd_hydrography"] for item in queue["items"])
    assert any(item["type"] == "report_section" and "usfws_critical_habitat" in item["source_refs"] for item in queue["items"])
    assert any(item["type"] == "report_section" and "epa_envirofacts_echo" in item["source_refs"] for item in queue["items"])
    assert source_gap(acquisition, "fema_nfhl_flood_hazard")["status"] == "optional"
    assert not (project_dir / "source_acquisition" / "downloads" / "fema_nfhl_flood_hazard.geojson").exists()


def test_prepare_sources_with_optional_feeds_fema_into_downstream_artifacts(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    acquisition = prepare_sources(project_dir, fetch_json=fake_supported_source_fetch_with_optional, include_optional_sources=True)
    constraints = analyze_constraints(project_dir)
    findings = generate_draft_findings(project_dir)
    tables = generate_comparison_tables(project_dir)
    maps = generate_maps(project_dir)
    sections = generate_report_sections(project_dir)
    queue = generate_review_queue(project_dir)

    assert acquisition["include_optional_sources"] is True
    assert source_gap(acquisition, "epa_envirofacts_echo")["status"] == "downloaded"
    assert source_gap(acquisition, "fema_nfhl_flood_hazard")["status"] == "downloaded"
    assert any(item["source_id"] == "fema_nfhl_flood_hazard" for item in constraints["constraints"])
    assert any(item["source_id"] == "epa_envirofacts_echo" for item in constraints["constraints"])
    assert any(item["resource_category"] == "flood_hazard" for item in findings["findings"])
    grouped_table = next(table for table in tables["tables"] if table["table_id"] == "grouped-constraint-summary")
    flood_table = next(table for table in tables["tables"] if table["table_id"] == "flood-hazard-summary")
    regulated_table = next(table for table in tables["tables"] if table["table_id"] == "regulated-facility-summary")
    assert any(row["source_category"] == "flood_hazard" for row in grouped_table["rows"])
    assert any(row["source_category"] == "regulated_facilities" for row in grouped_table["rows"])
    assert flood_table["row_count"] >= 1
    assert regulated_table["row_count"] >= 1
    assert flood_table["rows"][0]["flood_zone"] == "AE"
    assert flood_table["rows"][0]["zone_subtype"] == "FLOODWAY"
    assert flood_table["rows"][0]["sfha_flag"] == "T"
    assert flood_table["rows"][0]["vertical_datum"] == "NAVD88"
    assert flood_table["rows"][0]["length_unit"] == "feet"
    assert any(figure["figure_id"] == "source-context-fema-nfhl-flood-hazard" for figure in maps["figures"])
    assert any(figure["figure_id"] == "source-context-epa-envirofacts-echo" for figure in maps["figures"])
    flood_section = next(section for section in sections["sections"] if section["resource_category"] == "flood_hazard")
    regulated_section = next(section for section in sections["sections"] if section["resource_category"] == "regulated_facilities")
    inventory_section = next(section for section in sections["sections"] if section["section_id"] == "environmental-constraints-inventory")
    assert "flood-hazard-summary" in flood_section["related_table_ids"]
    assert "source-context-fema-nfhl-flood-hazard" in flood_section["related_figure_ids"]
    assert "regulated-facility-summary" in regulated_section["related_table_ids"]
    assert "source-context-epa-envirofacts-echo" in regulated_section["related_figure_ids"]
    assert "grouped-constraint-summary" in inventory_section["related_table_ids"]
    assert "project-overview" in inventory_section["related_figure_ids"]
    assert any(item["type"] == "report_section" and item["source_refs"] == ["fema_nfhl_flood_hazard"] for item in queue["items"])
    assert any(item["type"] == "report_section" and "epa_envirofacts_echo" in item["source_refs"] for item in queue["items"])


def test_populate_for_review_prepare_sources_records_acquisition_and_constraints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setattr(source_acquisition, "_fetch_json", fake_supported_source_fetch)

    result = populate_for_review(project_dir, prepare_sources=True)

    assert result["artifact_paths"]["source_acquisition"].endswith("source_acquisition_manifest.json")
    assert result["source_acquisition_download_count"] >= 4
    assert result["source_acquisition_include_optional_sources"] is False
    assert result["constraint_count"] >= 6
    assert not (project_dir / "source_acquisition" / "downloads" / "fema_nfhl_flood_hazard.geojson").exists()
    assert (project_dir / "source_acquisition" / "downloads" / "epa_envirofacts_echo.geojson").exists()


def test_populate_for_review_prepare_sources_with_optional_records_fema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setattr(source_acquisition, "_fetch_json", fake_supported_source_fetch_with_optional)

    result = populate_for_review(project_dir, prepare_sources=True, include_optional_sources=True)

    assert result["source_acquisition_include_optional_sources"] is True
    assert result["source_acquisition_download_count"] >= 5
    assert result["constraint_count"] >= 7
    assert (project_dir / "source_acquisition" / "downloads" / "fema_nfhl_flood_hazard.geojson").exists()
    assert (project_dir / "source_acquisition" / "downloads" / "epa_envirofacts_echo.geojson").exists()


def test_populate_for_review_without_prepare_sources_does_not_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)

    def failing_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("populate-for-review should not download without --prepare-sources")

    monkeypatch.setattr(source_acquisition, "_fetch_json", failing_fetch)
    result = populate_for_review(project_dir)

    assert result["artifact_paths"]["source_acquisition"] is None
    assert not (project_dir / "source_acquisition" / "downloads" / "usfws_nwi_wetlands.geojson").exists()


def test_source_acquisition_cli_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setattr(source_acquisition, "_fetch_json", fake_supported_source_fetch)

    assert main(["resolve-source-gaps", str(project_dir)]) == 0
    assert main(["download-source", str(project_dir), "usfws_nwi_wetlands"]) == 0
    assert main(["download-source", str(project_dir), "usgs_nhd_hydrography"]) == 0
    assert main(["download-source", str(project_dir), "usfws_critical_habitat"]) == 0
    assert main(["download-source", str(project_dir), "epa_envirofacts_echo"]) == 0
    assert main(["download-source", str(project_dir), "fema_nfhl_flood_hazard"]) == 0
    assert main(["prepare-sources", str(project_dir)]) == 0
    assert main(["prepare-sources", str(project_dir), "--include-optional-sources"]) == 0
    assert main(["populate-for-review", str(project_dir), "--prepare-sources", "--include-optional-sources"]) == 0

    captured = capsys.readouterr()
    assert "Resolved source gaps" in captured.out
    assert "Downloaded source workflow" in captured.out
    assert "Prepared sources" in captured.out
    assert "Populated for review" in captured.out


def test_populate_for_review_optional_sources_requires_prepare_sources(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_dir = write_project(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        main(["populate-for-review", str(project_dir), "--include-optional-sources"])

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "--include-optional-sources requires --prepare-sources" in captured.err
