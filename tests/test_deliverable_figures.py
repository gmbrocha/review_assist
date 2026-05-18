from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib
import pytest
from shapely.geometry import LineString, Point, Polygon

import review_assist.project_area as project_area_module
from review_assist.cli import main
from review_assist.deliverable_figures import generate_deliverable_figures, load_deliverable_figures
from review_assist.deliverable_matrix import REQUIRED_STUB_TEXT, load_deliverable_matrix
from review_assist.populate_for_review import populate_for_review

matplotlib.use("Agg")
import matplotlib.pyplot as plt


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


def write_project(tmp_path: Path, *, coordinates: str = "-90.0000,32.0000,0 -89.9900,32.0000,0") -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    (project_dir / "inputs" / "routes.kmz").write_bytes(
        kmz_bytes(
            kml_document(
                f"""
                <Placemark><name>Alternative A</name><LineString><coordinates>{coordinates}</coordinates></LineString></Placemark>
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


def write_png_sidecar(imagery_dir: Path, county_name: str = "Test") -> Path:
    path = imagery_dir / f"{county_name}_NAIP_2025.png"
    plt.imsave(path, [[[0.8, 0.9, 0.8], [0.7, 0.8, 0.7]], [[0.6, 0.7, 0.6], [0.5, 0.6, 0.5]]])
    return path


def figure_by_id(figures: dict[str, object], figure_id: str) -> dict[str, object]:
    return next(figure for figure in figures["figures"] if figure["figure_id"] == figure_id)  # type: ignore[index]


def issue_codes(record: dict[str, object]) -> set[str]:
    return {str(issue["code"]) for issue in record.get("validation_issues", [])}  # type: ignore[union-attr]


def test_deliverable_figures_write_13_matrix_records_and_missing_source_stubs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    result = generate_deliverable_figures(project_dir)
    matrix_ids = [target.target_id for target in load_deliverable_matrix().figure_targets]

    assert (project_dir / "deliverable" / "figures.json").exists()
    assert result["figure_count"] == 13
    assert [figure["figure_id"] for figure in result["figures"]] == matrix_ids
    assert [figure["figure_number"] for figure in result["figures"]] == list(range(1, 14))
    assert all(figure["section_target_id"] for figure in result["figures"])
    assert all(figure["comparison_unit_ids"] for figure in result["figures"])
    assert all(figure["is_stub"] is True for figure in result["figures"])

    census = figure_by_id(result, "figure-census-tracts")
    assert census["stub_text"] == REQUIRED_STUB_TEXT
    assert "figure_created_as_stub" in issue_codes(census)


def test_sid_only_basemap_warns_and_vector_figure_still_renders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "naip"
    write_naip_county(basemap_root)
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson")])

    result = generate_deliverable_figures(project_dir)
    wetlands = figure_by_id(result, "figure-wetlands-waterbodies")

    assert wetlands["is_stub"] is False
    assert Path(str(wetlands["image_path"])).exists()
    assert "basemap_selected_not_renderable" in issue_codes(wetlands)
    assert "maris_naip_2025_imagery" in wetlands["source_refs"]  # type: ignore[operator]


def test_renderable_png_sidecar_is_selected_when_metadata_is_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "naip"
    imagery_dir = write_naip_county(basemap_root)
    png_path = write_png_sidecar(imagery_dir)
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson")])

    result = generate_deliverable_figures(project_dir)
    wetlands = figure_by_id(result, "figure-wetlands-waterbodies")

    assert wetlands["is_stub"] is False
    assert "basemap_selected_not_renderable" not in issue_codes(wetlands)
    assert wetlands["provenance"]["basemap"]["renderable_paths"] == [str(png_path)]  # type: ignore[index]
    assert wetlands["provenance"]["basemap"]["rendered_path"] == str(png_path)  # type: ignore[index]


def test_restricted_cultural_source_is_not_mapped_or_exposed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_layer(
        project_dir / "public_cultural.geojson",
        [Point(-89.996, 32.0001)],
        [{"name": "Public historic marker", "OBJECTID": "public-1"}],
    )
    write_layer(
        project_dir / "restricted.geojson",
        [Point(-89.995, 32.0001)],
        [{"name": "Restricted archaeology location", "OBJECTID": "restricted-1"}],
    )
    write_registry(
        project_dir,
        [
            ("maris_public_cultural_context", "public_cultural.geojson"),
            ("mdah_restricted_archaeology", "restricted.geojson"),
        ],
    )

    result = generate_deliverable_figures(project_dir)
    cultural = figure_by_id(result, "figure-cultural-resources")
    serialized = json.dumps(cultural)

    assert cultural["is_stub"] is False
    assert "restricted_source_not_mapped" in issue_codes(cultural)
    assert "mdah_restricted_archaeology" not in cultural["source_refs"]  # type: ignore[operator]
    assert "Restricted archaeology location" not in serialized
    assert "restricted.geojson" not in serialized


def test_panel_records_are_attachment_supporting_not_main_figures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, coordinates="-90.5000,32.0000,0 -89.5000,32.0000,0")
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    result = generate_deliverable_figures(project_dir)

    assert result["figure_count"] == 13
    assert result["attachment_supporting_figure_count"] > 0
    main_ids = {figure["figure_id"] for figure in result["figures"]}
    assert all(panel["figure_id"] not in main_ids for panel in result["attachment_supporting_figures"])


def test_cli_and_populate_manifest_include_deliverable_figures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    assert main(["generate-deliverable-figures", str(project_dir)]) == 0
    captured = capsys.readouterr()
    assert "Generated deliverable figures" in captured.out
    assert load_deliverable_figures(project_dir)["figure_count"] == 13

    result = populate_for_review(project_dir)

    assert result["artifact_paths"]["deliverable_figures"].endswith("figures.json")
    assert result["deliverable_figure_count"] == 13
