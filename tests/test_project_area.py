from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

import review_assist.project_area as project_area_module
from review_assist.basemaps import build_basemap_index, renderable_sidecars_for
from review_assist.cli import main
from review_assist.project_area import build_project_area, index_maris_naip_basemaps, load_project_area
from review_assist.source_catalog import repo_root


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


def write_project(tmp_path: Path, coordinates: str = "-90.0,32.0,0 -89.99,32.0,0") -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    (project_dir / "inputs" / "project.kmz").write_bytes(
        kmz_bytes(
            kml_document(
                f"""
                <Placemark><name>Route A</name><LineString><coordinates>{coordinates}</coordinates></LineString></Placemark>
                """
            )
        )
    )
    (project_dir / "config" / "project.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "name": "Test Project",
                "description": "Synthetic project",
                "project_type": "alternatives_review",
                "inputs": [
                    {
                        "path": "inputs/project.kmz",
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


def write_naip_county(root: Path, county_name: str = "Test") -> Path:
    imagery_dir = root / county_name / f"{county_name}_NAIP_2025"
    imagery_dir.mkdir(parents=True)
    (imagery_dir / f"{county_name}_NAIP_2025.sid").write_bytes(b"sid")
    (imagery_dir / f"{county_name}_NAIP_2025.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<metadata>
  <westBoundLongitude><Decimal>-90.5</Decimal></westBoundLongitude>
  <eastBoundLongitude><Decimal>-89.5</Decimal></eastBoundLongitude>
  <southBoundLatitude><Decimal>31.5</Decimal></southBoundLatitude>
  <northBoundLatitude><Decimal>32.5</Decimal></northBoundLatitude>
</metadata>
""",
        encoding="utf-8",
    )
    return imagery_dir


def write_naip_county_with_sidecar(root: Path, suffix: str, county_name: str = "Test") -> Path:
    imagery_dir = write_naip_county(root, county_name)
    (imagery_dir / f"{county_name}_NAIP_2025{suffix}").write_bytes(b"sidecar")
    return imagery_dir


def write_boundary_context(project_dir: Path, county_name: str = "Test") -> None:
    boundary_path = project_dir / "boundary.geojson"
    gdf = gpd.GeoDataFrame(
        [{"CONAME": county_name, "review_assist_layer_id": "county_boundaries"}],
        geometry=[box(-90.1, 31.9, -89.9, 32.1)],
        crs="EPSG:4326",
    )
    gdf.to_file(boundary_path, driver="GeoJSON")
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": "maris_boundary_context",
                        "enabled": True,
                        "access_method": "local_file",
                        "path": "boundary.geojson",
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def issue_codes(artifact: dict[str, object]) -> set[str]:
    return {str(issue["code"]) for issue in artifact["validation_issues"]}  # type: ignore[index]


def test_project_area_records_wgs84_and_analysis_crs_bbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    result = build_project_area(project_dir)

    assert result["bbox_wgs84"]["west"] < result["bbox_wgs84"]["east"]  # type: ignore[index]
    assert result["bbox_analysis_crs"]["west"] < result["bbox_analysis_crs"]["east"]  # type: ignore[index]
    assert result["analysis_crs"].startswith("EPSG:")
    assert result["default_buffer_feet"] == 100


def test_project_area_handles_no_county_context_with_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path, "-120.0,40.0,0 -119.99,40.0,0")
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    result = build_project_area(project_dir)

    assert result["county_names"] == []
    assert "county_detection_unavailable" in issue_codes(result)


def test_naip_index_sees_local_county_folders_when_available() -> None:
    root = repo_root() / project_area_module.AERIAL_BASEMAP_ROOT
    if not root.exists():
        pytest.skip("Local MARIS/NAIP aerial basemap warehouse is not available.")

    records = index_maris_naip_basemaps(root)

    assert len(records) == 82
    assert all("county_name" in record for record in records)


def test_sid_only_county_imagery_reports_missing_render_asset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "naip"
    sid_dir = write_naip_county(basemap_root)
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    result = build_project_area(project_dir)

    assert result["county_names"] == ["Test County"]
    assert result["basemap_rendering_status"] == "render_asset_missing"
    assert result["selected_basemap_paths"] == []
    assert result["unsupported_basemap_source_paths"] == [str(sid_dir / "Test_NAIP_2025.sid")]
    assert result["renderable_basemap_paths"] == []
    assert any(warning["code"] == "basemap_render_asset_missing" for warning in result["warnings"])  # type: ignore[index]


def test_county_source_disagreement_warning_is_actionable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    write_boundary_context(project_dir)
    basemap_root = tmp_path / "naip"
    test_sid_dir = write_naip_county(basemap_root, "Test")
    write_naip_county(basemap_root, "Adjacent")
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    result = build_project_area(project_dir)
    warning = next(issue for issue in result["validation_issues"] if issue["code"] == "county_source_disagreement")  # type: ignore[index]
    details = warning["details"]  # type: ignore[index]

    assert result["county_names"] == ["Test County"]
    assert result["county_detection_method"] == "maris_boundary_context"
    assert result["selected_basemap_paths"] == []
    assert result["unsupported_basemap_source_paths"] == [str(test_sid_dir / "Test_NAIP_2025.sid")]
    assert details["selected_counties"] == ["Test County"]
    assert details["final_county_list"] == ["Test County"]
    assert details["preferred_source"] == "maris_boundary_context"
    assert "Boundary context is the highest-confidence" in details["preferred_reason"]
    assert details["alternate_county_sources"][0]["method"] == "naip_maris_metadata_extent"
    assert details["alternate_county_sources"][0]["county_names"] == ["Adjacent County", "Test County"]
    assert "Alternate metadata-only counties do not change non-basemap source selection" in details["source_selection_impact"]
    assert "broader metadata extents are not selected as project counties" in details["basemap_selection_impact"]
    assert "Selected counties: Test County" in details["summary"]
    assert "Adjacent County" in warning["message"]  # type: ignore[operator]


@pytest.mark.parametrize("suffix", [".tif", ".tiff", ".png"])
def test_renderable_sidecar_detection_finds_supported_formats(tmp_path: Path, suffix: str) -> None:
    basemap_root = tmp_path / "naip"
    imagery_dir = write_naip_county_with_sidecar(basemap_root, suffix)

    index = build_basemap_index(basemap_root)
    candidate = index["candidates"][0]

    assert index["candidate_count"] == 1
    assert candidate["status"] == "renderable_sidecar_available"
    assert renderable_sidecars_for(candidate) == [imagery_dir / f"Test_NAIP_2025{suffix}"]


def test_project_area_loads_after_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "naip"
    write_naip_county(basemap_root)
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    written = build_project_area(project_dir)
    loaded = load_project_area(project_dir)

    assert loaded["output_path"] == written["output_path"]


def test_cli_build_project_area_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "naip"
    write_naip_county(basemap_root)
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    assert main(["build-project-area", str(project_dir), "--json"]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out)["basemap_rendering_status"] == "render_asset_missing"
