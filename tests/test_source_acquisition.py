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


def fake_supported_source_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if "/Wetlands/MapServer" in url:
        return fake_nwi_fetch(url, params)
    if "/nhd/MapServer" in url:
        return fake_nhd_fetch(url, params)
    raise AssertionError(f"Unexpected source fetch URL: {url}")


def fake_empty_nhd_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/6") or url.endswith("/9"):
        return {"maxRecordCount": 1}
    if url.endswith("/6/query") or url.endswith("/9/query"):
        return {"type": "FeatureCollection", "features": []}
    raise AssertionError(f"Unexpected NHD fetch URL: {url}")


def test_gap_resolver_marks_unregistered_nwi_downloadable(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = resolve_source_gaps(project_dir)

    assert source_gap(result, "usfws_nwi_wetlands")["status"] == "downloadable"
    assert (project_dir / "source_acquisition" / "source_acquisition_manifest.json").exists()


def test_gap_resolver_marks_unregistered_nhd_downloadable(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = resolve_source_gaps(project_dir)

    assert source_gap(result, "usgs_nhd_hydrography")["status"] == "downloadable"


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
    assert constraints["constraint_count"] >= 3
    assert any(item["relationship_type"] == "crosses" and item["source_id"] == "usgs_nhd_hydrography" for item in constraints["constraints"])
    assert any("Mock NWI Wetland" in finding["summary"] or "Mock NWI Wetland" in finding["details"] for finding in findings["findings"])
    assert any("Mock NHD Stream" in finding["summary"] or "Mock NHD Stream" in finding["details"] for finding in findings["findings"])
    hydrography_table = next(table for table in tables["tables"] if table["table_id"] == "hydrography-crossing-summary")
    assert hydrography_table["row_count"] >= 2
    assert maps["figure_count"] > 0
    assert any(figure["figure_id"] == "source-context-usgs-nhd-hydrography" for figure in maps["figures"])
    hydrography_section = next(section for section in sections["sections"] if section["resource_category"] == "hydrography_crossings")
    assert "hydrography-crossing-summary" in hydrography_section["related_table_ids"]
    assert "source-context-usgs-nhd-hydrography" in hydrography_section["related_figure_ids"]
    assert any(item["type"] == "report_section" and item["source_refs"] == ["usgs_nhd_hydrography"] for item in queue["items"])


def test_populate_for_review_prepare_sources_records_acquisition_and_constraints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setattr(source_acquisition, "_fetch_json", fake_supported_source_fetch)

    result = populate_for_review(project_dir, prepare_sources=True)

    assert result["artifact_paths"]["source_acquisition"].endswith("source_acquisition_manifest.json")
    assert result["source_acquisition_download_count"] >= 2
    assert result["constraint_count"] >= 3


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
    assert main(["prepare-sources", str(project_dir)]) == 0
    assert main(["populate-for-review", str(project_dir), "--prepare-sources"]) == 0

    captured = capsys.readouterr()
    assert "Resolved source gaps" in captured.out
    assert "Downloaded source workflow" in captured.out
    assert "Prepared sources" in captured.out
    assert "Populated for review" in captured.out
