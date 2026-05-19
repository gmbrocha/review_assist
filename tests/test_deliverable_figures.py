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
from review_assist.deliverable_figure_rendering import comparison_unit_style_records
from review_assist.deliverable_figures import DeliverableFigureError, generate_deliverable_figures, load_deliverable_figures
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
    issue_text = json.dumps(wetlands["validation_issues"])
    assert "only MrSID source files are available" in issue_text
    assert "Provide GeoTIFF/PNG sidecar" in issue_text
    shown_basemaps = [layer for layer in wetlands["shown_layers"] if layer["layer_type"] == "basemap_provenance"]  # type: ignore[index]
    assert shown_basemaps
    assert shown_basemaps[0]["renderability_status"] == "selected_not_renderable"
    assert shown_basemaps[0]["visual_use"] == "provenance_only"
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
    shown_basemaps = [layer for layer in wetlands["shown_layers"] if layer["layer_type"] == "basemap"]  # type: ignore[index]
    assert shown_basemaps
    assert shown_basemaps[0]["renderability_status"] == "rendered"
    assert shown_basemaps[0]["visual_use"] == "rendered_basemap"
    assert wetlands["provenance"]["basemap"]["renderable_paths"] == [str(png_path)]  # type: ignore[index]
    assert wetlands["provenance"]["basemap"]["rendered_path"] == str(png_path)  # type: ignore[index]


def test_comparison_unit_styles_use_usable_kml_colors_and_visible_fallbacks() -> None:
    gdf = gpd.GeoDataFrame(
        [
            {
                "comparison_unit_id": "comparison-unit-00001",
                "comparison_unit_name": "Red route",
                "style_color": "ff0000ff",
            },
            {
                "comparison_unit_id": "comparison-unit-00002",
                "comparison_unit_name": "White route",
                "style_color": "ffffffff",
            },
            {
                "comparison_unit_id": "comparison-unit-00003",
                "comparison_unit_name": "Blank route",
                "style_color": "",
            },
        ],
        geometry=[
            LineString([(-90.0, 32.0), (-89.99, 32.0)]),
            LineString([(-90.0, 32.001), (-89.99, 32.001)]),
            LineString([(-90.0, 32.002), (-89.99, 32.002)]),
        ],
        crs="EPSG:4326",
    )

    styles = comparison_unit_style_records(gdf)
    repeated = comparison_unit_style_records(gdf)

    assert styles == repeated
    assert styles[0]["color"] == "#ff0000"
    assert styles[0]["style_source"] == "kml_style_color"
    assert styles[1]["color"] != "#ffffff"
    assert styles[1]["style_source"] == "deterministic_fallback"
    assert styles[2]["color"] != styles[1]["color"]
    assert styles[2]["style_source"] == "deterministic_fallback"
    assert all(style["line_width"] < 2.0 for style in styles)


def test_generated_figures_record_distinct_comparison_unit_visual_styles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson")])

    result = generate_deliverable_figures(project_dir)
    wetlands = figure_by_id(result, "figure-wetlands-waterbodies")
    comparison_layer = next(layer for layer in wetlands["shown_layers"] if layer["layer_type"] == "comparison_units")  # type: ignore[index]

    assert result["figure_count"] == 13
    assert wetlands["is_stub"] is False
    assert comparison_layer["rendered_as"] == "individual_comparison_units"
    assert comparison_layer["geometry_type_counts"] == {"LineString": 1}
    assert comparison_layer["unit_styles"]
    assert comparison_layer["unit_styles"][0]["label"] == "Alternative A"
    assert comparison_layer["unit_styles"][0]["style_source"] == "deterministic_fallback"


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


def test_deliverable_figure_artifact_contract_fields_for_main_and_panel_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, coordinates="-90.5000,32.0000,0 -89.5000,32.0000,0")
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    result = generate_deliverable_figures(project_dir)

    required_main_fields = {
        "figure_id",
        "type",
        "figure_type",
        "figure_number",
        "title",
        "section_target_id",
        "image_path",
        "file_format",
        "caption",
        "source_note",
        "method_note",
        "map_elements",
        "figure_group",
        "related_resource_categories",
        "shown_layers",
        "source_refs",
        "layer_refs",
        "related_constraint_ids",
        "comparison_unit_ids",
        "provenance",
        "uncertainty_flags",
        "is_stub",
        "stub_text",
        "review_status",
        "validation_issues",
    }
    required_panel_fields = {
        "figure_id",
        "type",
        "figure_type",
        "title",
        "section_target_id",
        "image_path",
        "file_format",
        "caption",
        "source_note",
        "method_note",
        "map_elements",
        "figure_group",
        "shown_layers",
        "source_refs",
        "provenance",
        "uncertainty_flags",
        "review_status",
        "validation_issues",
    }

    assert result["figures"]
    assert result["attachment_supporting_figures"]
    assert all(required_main_fields <= set(figure) for figure in result["figures"])
    assert all(required_panel_fields <= set(panel) for panel in result["attachment_supporting_figures"])
    assert all(figure["file_format"] == "png" for figure in result["figures"])
    assert all(panel["file_format"] == "png" for panel in result["attachment_supporting_figures"])


def test_deliverable_figures_top_level_contract_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    result = generate_deliverable_figures(project_dir)

    assert {
        "project_id",
        "project_name",
        "project_dir",
        "created_at",
        "matrix_version",
        "figure_count",
        "figures",
        "attachment_supporting_figure_count",
        "attachment_supporting_figures",
        "validation_issues",
        "upstream_artifacts",
        "output_path",
    } <= set(result)
    assert result["figure_count"] == 13
    assert result["attachment_supporting_figure_count"] == len(result["attachment_supporting_figures"])
    assert result["output_path"].endswith("deliverable\\figures.json") or result["output_path"].endswith("deliverable/figures.json")
    assert result["upstream_artifacts"]["deliverable_matrix_path"] == "config/deliverable_section_matrix.json"


def test_load_deliverable_figures_round_trip_and_validates_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    written = generate_deliverable_figures(project_dir)

    loaded = load_deliverable_figures(project_dir)
    assert loaded["figure_count"] == written["figure_count"]
    assert [figure["figure_id"] for figure in loaded["figures"]] == [figure["figure_id"] for figure in written["figures"]]

    path = project_dir / "deliverable" / "figures.json"
    corrupted = json.loads(path.read_text(encoding="utf-8"))
    corrupted["figure_count"] = 12
    path.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(DeliverableFigureError, match="figure_count"):
        load_deliverable_figures(project_dir)


def test_load_deliverable_figures_validates_attachment_panel_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, coordinates="-90.5000,32.0000,0 -89.5000,32.0000,0")
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    written = generate_deliverable_figures(project_dir)

    assert written["attachment_supporting_figures"]
    path = project_dir / "deliverable" / "figures.json"
    corrupted = json.loads(path.read_text(encoding="utf-8"))
    del corrupted["attachment_supporting_figures"][0]["caption"]
    path.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(DeliverableFigureError, match="Attachment supporting figure is missing required fields"):
        load_deliverable_figures(project_dir)


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
