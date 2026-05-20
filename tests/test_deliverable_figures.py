from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon

import review_assist.project_area as project_area_module
from review_assist.cli import main
from review_assist.deliverable_figure_rendering import (
    choose_legend_collar_side,
    comparison_unit_style_records,
    compute_visual_extent_with_legend_collar,
    render_map,
    source_layer_style_record,
)
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


def write_project_local_naip_tif(project_dir: Path, *, year: int = 2023) -> Path:
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_bounds

    output_dir = project_dir / "basemaps" / "naip" / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)
    tif_path = output_dir / "naip_project_basemap.tif"
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    data[0, :, :] = 120
    data[1, :, :] = 155
    data[2, :, :] = 105
    bounds = (-90.01, 31.99, -89.98, 32.01)
    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=data.shape[1],
        width=data.shape[2],
        count=3,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=from_bounds(*bounds, width=data.shape[2], height=data.shape[1]),
    ) as dataset:
        dataset.write(data)
    metadata_path = output_dir / "naip_project_basemap.json"
    metadata_path.write_text(
        json.dumps(
            {
                "source_id": "usda_naip_imagery",
                "display_name": "USDA NAIP Project Basemap",
                "provider": "Microsoft Planetary Computer",
                "collection_id": "naip",
                "asset_key": "image",
                "item_ids": ["test-naip-item"],
                "item_datetimes": [f"{year}-08-13T16:00:00Z"],
                "source_datetime": f"{year}-08-13T16:00:00Z",
                "naip_year": year,
                "source_hrefs": ["https://example.invalid/test-naip-item.tif"],
                "signed_hrefs_stored": False,
                "aoi_source": "project_analysis_bounds",
                "aoi_bounds_wgs84": {"west": bounds[0], "south": bounds[1], "east": bounds[2], "north": bounds[3]},
                "output_path": f"basemaps/naip/{year}/naip_project_basemap.tif",
                "output_crs": "EPSG:4326",
                "output_bounds_wgs84": {"west": bounds[0], "south": bounds[1], "east": bounds[2], "north": bounds[3]},
                "output_shape": [8, 8],
                "pixel_count": 64,
                "selection_method": "latest_year_then_datetime_then_overlap_then_item_id",
                "limits": {"max_pixels": 25_000_000, "max_tiles": 12, "timeout_seconds": 60},
                "created_at": "2026-05-19T00:00:00+00:00",
                "acquisition_method": "planetary_computer_stac_cog_window",
                "known_limitations": ["Imagery is visual context only."],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return tif_path


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
    serialized_export_fields = "\n".join(
        str(value)
        for figure in result["figures"]
        for value in (figure.get("caption"), figure.get("source_note"), figure.get("method_note"))
    ).lower()
    assert "reviewer verification" not in serialized_export_fields
    assert "pre-review" not in serialized_export_fields
    assert "draft desktop" not in serialized_export_fields
    assert all("draft_label" not in figure["map_elements"] for figure in result["figures"])

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


def test_sid_only_basemap_keeps_naip_materialization_failure_visible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "naip"
    write_naip_county(basemap_root)
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    run_manifest = project_dir / "basemaps" / "naip" / "naip_basemap_materialization.json"
    run_manifest.parent.mkdir(parents=True, exist_ok=True)
    run_manifest.write_text(
        json.dumps(
            {
                "status": "failed",
                "success": False,
                "source_id": "usda_naip_imagery",
                "message": "mock NAIP materialization failure",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson")])

    result = generate_deliverable_figures(project_dir)
    wetlands = figure_by_id(result, "figure-wetlands-waterbodies")

    assert "basemap_selected_not_renderable" in issue_codes(wetlands)
    assert "naip_basemap_materialization_failed" in issue_codes(wetlands)
    assert "maris_naip_2025_imagery" in wetlands["source_refs"]  # type: ignore[operator]
    assert "usda_naip_imagery" in wetlands["source_refs"]  # type: ignore[operator]
    assert "MARIS/NAIP 2025 Imagery provenance only; no visual basemap sidecar" in wetlands["source_note"]  # type: ignore[operator]
    assert "USDA NAIP Project Basemap materialization failed; vector-only fallback used" in wetlands["source_note"]  # type: ignore[operator]


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


def test_project_local_naip_geotiff_sidecar_is_rendered_in_deliverable_figures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("rasterio")
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    tif_path = write_project_local_naip_tif(project_dir)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson")])

    result = generate_deliverable_figures(project_dir)
    wetlands = figure_by_id(result, "figure-wetlands-waterbodies")

    assert result["figure_count"] == 13
    assert wetlands["is_stub"] is False
    shown_basemaps = [layer for layer in wetlands["shown_layers"] if layer["layer_type"] == "basemap"]  # type: ignore[index]
    assert shown_basemaps
    assert shown_basemaps[0]["source_id"] == "usda_naip_imagery"
    assert shown_basemaps[0]["path"] == str(tif_path)
    assert shown_basemaps[0]["renderability_status"] == "rendered"
    assert shown_basemaps[0]["visual_use"] == "rendered_basemap"
    assert "USDA NAIP Project Basemap rendered from sidecar" in wetlands["source_note"]  # type: ignore[operator]
    assert "Vector and selected renderable basemap sidecar" in wetlands["method_note"]  # type: ignore[operator]
    assert "usda_naip_imagery" in wetlands["source_refs"]  # type: ignore[operator]
    assert wetlands["provenance"]["basemap"]["rendered_path"] == str(tif_path)  # type: ignore[index]


def test_project_local_naip_sidecar_is_rendered_in_regulated_facilities_figure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("rasterio")
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    tif_path = write_project_local_naip_tif(project_dir)
    write_layer(
        project_dir / "frs.geojson",
        [Point(-90.0, 32.0)],
        [{"REGISTRY_ID": "FRS-1", "PRIMARY_NAME": "Synthetic facility"}],
    )
    write_registry(project_dir, [("epa_frs_facilities_ms", "frs.geojson")])

    result = generate_deliverable_figures(project_dir)
    hazardous = figure_by_id(result, "figure-hazardous-waste-sites")

    assert result["figure_count"] == 13
    assert hazardous["is_stub"] is False
    shown_basemaps = [layer for layer in hazardous["shown_layers"] if layer["layer_type"] == "basemap"]  # type: ignore[index]
    assert shown_basemaps
    assert shown_basemaps[0]["source_id"] == "usda_naip_imagery"
    assert shown_basemaps[0]["path"] == str(tif_path)
    assert shown_basemaps[0]["visual_use"] == "rendered_basemap"
    assert "USDA NAIP Project Basemap rendered from sidecar" in hazardous["source_note"]  # type: ignore[operator]


def test_specific_regulated_sources_satisfy_hazardous_figure_without_legacy_broad_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    source_ids = [
        "epa_frs_facilities_ms",
        "maris_brownfields",
        "maris_npdes_facilities",
        "maris_solid_waste_landfills",
        "maris_superfund_sites",
        "maris_tri_facilities",
        "maris_underground_storage_tanks",
        "mississippi_oil_gas_wells",
    ]
    for index, source_id in enumerate(source_ids):
        write_layer(
            project_dir / f"{source_id}.geojson",
            [Point(-90.0 + index * 0.0001, 32.0)],
            [{"name": f"{source_id} feature"}],
        )
    write_registry(project_dir, [(source_id, f"{source_id}.geojson") for source_id in source_ids])

    result = generate_deliverable_figures(project_dir)
    hazardous = figure_by_id(result, "figure-hazardous-waste-sites")
    serialized_issues = json.dumps(hazardous["validation_issues"])

    assert hazardous["is_stub"] is False
    assert "epa_envirofacts_echo" not in hazardous["source_refs"]  # type: ignore[operator]
    assert "mdeq_environmental_context" not in hazardous["source_refs"]  # type: ignore[operator]
    assert "epa_envirofacts_echo" not in serialized_issues
    assert "mdeq_environmental_context" not in serialized_issues
    assert set(source_ids).issubset(set(hazardous["source_refs"]))  # type: ignore[arg-type]
    shown_source_ids = {layer.get("source_id") for layer in hazardous["shown_layers"] if layer.get("layer_type") == "source_layer"}  # type: ignore[union-attr]
    assert set(source_ids).issubset(shown_source_ids)
    assert "EPA Facility Registry Service" in hazardous["source_note"]  # type: ignore[operator]
    assert "EPA FRS hazardous" not in hazardous["source_note"]  # type: ignore[operator]


def test_naip_materialization_failure_is_reported_in_vector_only_figure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    run_manifest = project_dir / "basemaps" / "naip" / "naip_basemap_materialization.json"
    run_manifest.parent.mkdir(parents=True, exist_ok=True)
    run_manifest.write_text(
        json.dumps(
            {
                "status": "failed",
                "success": False,
                "source_id": "usda_naip_imagery",
                "message": "mock NAIP materialization failure",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson")])

    result = generate_deliverable_figures(project_dir)
    wetlands = figure_by_id(result, "figure-wetlands-waterbodies")

    assert wetlands["is_stub"] is False
    assert "naip_basemap_materialization_failed" in issue_codes(wetlands)
    shown_basemaps = [layer for layer in wetlands["shown_layers"] if layer["layer_type"] == "basemap_provenance"]  # type: ignore[index]
    assert shown_basemaps
    assert shown_basemaps[0]["source_id"] == "usda_naip_imagery"
    assert shown_basemaps[0]["renderability_status"] == "materialization_failed"
    assert shown_basemaps[0]["visual_use"] == "failed_not_rendered"
    assert "USDA NAIP Project Basemap materialization failed; vector-only fallback used" in wetlands["source_note"]  # type: ignore[operator]
    assert "Vector-only" in wetlands["method_note"]  # type: ignore[operator]
    assert "usda_naip_imagery" in wetlands["source_refs"]  # type: ignore[operator]


def test_attachment_panel_records_project_local_naip_basemap_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("rasterio")
    project_dir = write_project(tmp_path, coordinates="-90.5000,32.0000,0 -89.5000,32.0000,0")
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    tif_path = write_project_local_naip_tif(project_dir)

    result = generate_deliverable_figures(project_dir)

    assert result["figure_count"] == 13
    assert result["attachment_supporting_figure_count"] > 0
    panel = result["attachment_supporting_figures"][0]
    shown_basemaps = [layer for layer in panel["shown_layers"] if layer["layer_type"] == "basemap"]
    assert shown_basemaps
    assert shown_basemaps[0]["source_id"] == "usda_naip_imagery"
    assert shown_basemaps[0]["path"] == str(tif_path)
    assert "usda_naip_imagery" in panel["source_refs"]
    assert panel["provenance"]["basemap"]["rendered_path"] == str(tif_path)


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
    assert all(1.0 < style["line_width"] < 2.0 for style in styles)


def test_comparison_unit_labels_are_compact_for_legend() -> None:
    gdf = gpd.GeoDataFrame(
        [
            {
                "comparison_unit_id": "comparison-unit-00001",
                "comparison_unit_name": "ali_option1A_2013.dwg",
                "style_color": "",
            },
            {
                "comparison_unit_id": "comparison-unit-00002",
                "comparison_unit_name": "Very Long Submitted Project Feature Name With Extra Metadata",
                "style_color": "",
            },
        ],
        geometry=[
            LineString([(-90.0, 32.0), (-89.99, 32.0)]),
            LineString([(-90.0, 32.001), (-89.99, 32.001)]),
        ],
        crs="EPSG:4326",
    )

    styles = comparison_unit_style_records(gdf)

    assert styles[0]["label"] == "Option 1A"
    assert styles[0]["full_label"] == "ali_option1A_2013.dwg"
    assert len(styles[1]["label"]) <= 24


def test_regulated_facility_source_styles_are_distinct_and_compact() -> None:
    layers = [
        {"source_id": "epa_frs_facilities_ms", "source_name": "EPA Facility Registry Service Facilities Mississippi", "source_category": "regulated_facilities"},
        {"source_id": "maris_brownfields", "source_name": "MARIS Brownfields", "source_category": "regulated_facilities"},
        {"source_id": "maris_npdes_facilities", "source_name": "MARIS NPDES Facilities", "source_category": "regulated_facilities"},
        {"source_id": "maris_underground_storage_tanks", "source_name": "MARIS Underground Storage Tanks", "source_category": "regulated_facilities"},
    ]

    styles = [source_layer_style_record(layer, index) for index, layer in enumerate(layers)]

    assert [style["label"] for style in styles] == ["EPA FRS", "Brownfields", "NPDES", "USTs"]
    assert len({style["color"] for style in styles}) == len(styles)
    assert len({style["marker"] for style in styles}) == len(styles)
    assert all(style["line_width"] < 0.7 for style in styles)
    assert all(style["marker_size"] <= 15 for style in styles)


def test_legend_label_abbreviations_keep_source_labels_compact() -> None:
    labels = [
        source_layer_style_record({"source_id": "usfws_nwi_wetlands", "source_name": "National Wetlands Inventory", "source_category": "wetlands_waterbodies"}, 0)["label"],
        source_layer_style_record({"source_id": "usgs_nhd_flowlines", "source_name": "USGS NHD Flowlines Mississippi", "source_category": "hydrography"}, 1)["label"],
        source_layer_style_record({"source_id": "usgs_nhd_waterbodies", "source_name": "USGS NHD Waterbodies Mississippi", "source_category": "hydrography"}, 2)["label"],
        source_layer_style_record({"source_id": "usgs_nhd_other_areas", "source_name": "USGS NHD Other Areas Mississippi", "source_category": "hydrography"}, 3)["label"],
    ]

    assert labels == ["NWI Wetlands", "NHD Flowlines", "NHD Waterbodies", "NHD Other Areas"]
    assert all(len(label) <= 18 for label in labels)


def test_tall_project_uses_side_legend_collar_and_expands_x_extent() -> None:
    layout = compute_visual_extent_with_legend_collar(
        (-250, 0, 250, 10_000),
        legend_labels=["Alternative A", "EPA FRS", "Brownfields", "NPDES"],
        feature_layers=[],
    )
    base_w, base_s, base_e, base_n = layout["base_bounds"]
    ext_w, ext_s, ext_e, ext_n = layout["expanded_bounds"]
    collar_w, collar_s, collar_e, collar_n = layout["collar_bounds"]

    assert layout["legend_side"] in {"right", "left"}
    assert layout["render_extent_type"] == "figure_render_extent"
    assert layout["render_extent_is_presentation_only"] is True
    assert layout["presentation_extent_type"] == "presentation_only_collar_extent"
    assert (ext_e - ext_w) > (base_e - base_w)
    assert (ext_n - ext_s) == pytest.approx(base_n - base_s)
    assert collar_w >= base_e or collar_e <= base_w
    assert collar_s == pytest.approx(base_s)
    assert collar_n == pytest.approx(base_n)


def test_wide_project_can_use_horizontal_legend_collar() -> None:
    side = choose_legend_collar_side(
        (0, -250, 10_000, 250),
        ["Alternative A", "NWI Wetlands", "NHD Flowlines", "NHD Waterbodies"],
        [],
    )

    assert side in {"top", "bottom"}


def test_legend_collar_expansion_is_bounded_and_bbox_stays_in_collar() -> None:
    layout = compute_visual_extent_with_legend_collar(
        (0, 0, 1000, 1000),
        legend_labels=[f"Layer {index}" for index in range(12)],
        feature_layers=[],
    )
    base_w, base_s, base_e, base_n = layout["base_bounds"]
    ext_w, ext_s, ext_e, ext_n = layout["expanded_bounds"]
    bbox_x0, bbox_y0, bbox_x1, bbox_y1 = layout["legend_bbox_axes"]

    assert (ext_e - ext_w) <= (base_e - base_w) * 1.6
    assert (ext_n - ext_s) <= (base_n - base_s) * 1.6
    assert 0 <= bbox_x0 < bbox_x1 <= 1
    assert 0 <= bbox_y0 < bbox_y1 <= 1


def test_dense_feature_conflicts_can_fall_back_to_outside_frame_legend() -> None:
    surrounding_features = gpd.GeoDataFrame(
        [{"name": "surrounding feature"}],
        geometry=[Polygon([(-1000, -1000), (2000, -1000), (2000, 2000), (-1000, 2000), (-1000, -1000)])],
        crs="EPSG:32616",
    )

    layout = compute_visual_extent_with_legend_collar(
        (0, 0, 1000, 1000),
        legend_labels=["Alternative A", "NWI Wetlands", "EPA FRS"],
        feature_layers=[surrounding_features],
    )

    assert layout["layout_strategy"] == "outside_frame_legend"
    assert layout["expanded_bounds"] == layout["base_bounds"]


def test_render_map_keeps_long_notes_out_of_image_canvas(tmp_path: Path) -> None:
    unit_gdf = gpd.GeoDataFrame(
        [{"comparison_unit_id": "comparison-unit-00001", "comparison_unit_name": "Alternative A"}],
        geometry=[LineString([(0, 0), (0, 10_000)])],
        crs="EPSG:32616",
    )
    source_gdf = gpd.GeoDataFrame(
        [{"review_assist_source_id": "epa_frs_facilities_ms"}],
        geometry=[Point(120, 4000)],
        crs="EPSG:32616",
    )
    output_path = tmp_path / "compact-map.png"

    layout = render_map(
        output_path=output_path,
        title="Hazardous Waste Sites near the Project Area",
        unit_gdf=unit_gdf,
        analysis_crs="EPSG:32616",
        source_layers=[
            {
                "source_id": "epa_frs_facilities_ms",
                "source_name": "EPA Facility Registry Service Facilities Mississippi",
                "source_category": "regulated_facilities",
                "gdf": source_gdf,
            }
        ],
        basemap={"layer": None},
        method_note="Vector-only desktop screening map. Analysis CRS: EPSG:32616.",
        source_note="Sources: " + "; ".join(["A very long source/provenance note"] * 20),
        focus_bounds=(-250, 0, 250, 10_000),
    )

    image = plt.imread(output_path)
    height, width = image.shape[:2]
    assert height > width * 1.25
    assert width < 950
    assert layout["layout_strategy"] == "legend_collar"
    assert layout["legend_side"] in {"right", "left"}


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
    assert result["extent_policy"]["core_rule"].startswith("Rendered map extent")
    assert wetlands["query_extent_type"] == "project_area_analysis_bounds"
    assert wetlands["figure_extent_type"] == "direct_intersection_extent"
    assert wetlands["render_extent_type"] == "figure_render_extent"
    assert wetlands["render_extent_is_presentation_only"] is True
    assert wetlands["provenance"]["render_layout"]["layout_strategy"] == "legend_collar"  # type: ignore[index]
    assert wetlands["provenance"]["render_layout"]["render_extent_is_presentation_only"] is True  # type: ignore[index]
    assert comparison_layer["rendered_as"] == "individual_comparison_units"
    assert comparison_layer["geometry_type_counts"] == {"LineString": 1}
    assert comparison_layer["unit_styles"]
    assert comparison_layer["unit_styles"][0]["label"] == "Alternative A"
    assert comparison_layer["unit_styles"][0]["style_source"] == "deterministic_fallback"
    source_layer = next(layer for layer in wetlands["shown_layers"] if layer.get("source_id") == "usfws_nwi_wetlands")  # type: ignore[index]
    assert source_layer["legend_label"] == "NWI Wetlands"
    assert source_layer["render_style"]["color"]
    assert source_layer["render_style"]["line_width"] < comparison_layer["unit_styles"][0]["line_width"]

    streams = figure_by_id(result, "figure-streams-impaired-waters")
    assert streams["figure_extent_type"] == "watershed_context_extent"
    assert streams["analysis_extent_type"] == "watershed_context_extent"
    assert "watershed_context_extent and 303(d) acquisition" in streams["source_selection_reason"]


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
