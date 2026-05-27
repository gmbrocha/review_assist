from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pytest
from matplotlib.axes import Axes
from shapely.geometry import LineString, Point, Polygon

import review_assist.project_area as project_area_module
from review_assist.cli import main
from review_assist.deliverable_items import generate_deliverable_items
from review_assist.evidence_package import build_evidence_package
from review_assist.review_queue import generate_review_queue
from review_assist.deliverable_figure_rendering import (
    LEGEND_MEASUREMENT_SAFETY_FACTOR,
    _thematic_color_is_allowed,
    choose_legend_collar_side,
    comparison_unit_style_records,
    compute_visual_extent_with_legend_collar,
    render_map,
    source_layer_style_record,
)
from review_assist.deliverable_constraints import (
    analyze_comparison_unit_constraints,
    load_comparison_unit_constraints,
)
from review_assist.deliverable_figure_specs import TARGET_SPECS
from review_assist.deliverable_figures import (
    DeliverableFigureError,
    generate_deliverable_figures,
    generate_figure_extent_plan,
    load_deliverable_figures,
)
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


def write_registry(project_dir: Path, sources: list[tuple[str, str]], *, status: str = "local_materialized") -> None:
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
                        "status": status,
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


def write_project_local_naip_tif(
    project_dir: Path,
    *,
    year: int = 2023,
    bounds: tuple[float, float, float, float] = (-90.05, 31.95, -89.90, 32.05),
    extent_class: str | None = None,
) -> Path:
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_bounds

    output_dir = project_dir / "basemaps" / "naip" / str(extent_class) / str(year) if extent_class else project_dir / "basemaps" / "naip" / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)
    tif_path = output_dir / "naip_project_basemap.tif"
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    data[0, :, :] = 120
    data[1, :, :] = 155
    data[2, :, :] = 105
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
                "aoi_source": "figure_extent_plan_full_render_extent" if extent_class else "project_analysis_bounds",
                "aoi_bounds_wgs84": {"west": bounds[0], "south": bounds[1], "east": bounds[2], "north": bounds[3]},
                "output_path": (
                    f"basemaps/naip/{extent_class}/{year}/naip_project_basemap.tif"
                    if extent_class
                    else f"basemaps/naip/{year}/naip_project_basemap.tif"
                ),
                **({"extent_class": extent_class, "render_extent_is_presentation_only": True} if extent_class else {}),
                "output_crs": "EPSG:4326",
                "output_bounds_wgs84": {"west": bounds[0], "south": bounds[1], "east": bounds[2], "north": bounds[3]},
                "output_shape": [8, 8],
                "pixel_count": 64,
                "selection_method": "latest_year_then_datetime_then_overlap_then_item_id",
                "limits": {"max_pixels": 25_000_000, "max_tiles": 100, "timeout_seconds": 60},
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


def plan_figure_by_id(plan: dict[str, object], figure_id: str) -> dict[str, object]:
    return next(figure for figure in plan["figures"] if figure["figure_id"] == figure_id)  # type: ignore[index]


def issue_codes(record: dict[str, object]) -> set[str]:
    return {str(issue["code"]) for issue in record.get("validation_issues", [])}  # type: ignore[union-attr]


def shown_source_ids(figure: dict[str, object]) -> set[str]:
    return {
        str(layer.get("source_id"))
        for layer in figure.get("shown_layers", [])  # type: ignore[union-attr]
        if isinstance(layer, dict) and layer.get("layer_type") == "source_layer"
    }


def color_distance(color_a: str, color_b: str) -> float:
    a = color_a.lstrip("#")
    b = color_b.lstrip("#")
    return sum((int(a[index : index + 2], 16) - int(b[index : index + 2], 16)) ** 2 for index in (0, 2, 4)) ** 0.5


def test_hazardous_regulated_figure_split_is_declared_in_matrix_and_specs() -> None:
    matrix = load_deliverable_matrix()
    target_ids = [target.target_id for target in matrix.figure_targets]
    section_by_id = {target.target_id: target for target in matrix.section_targets}

    assert target_ids == [
        "figure-wetlands-waterbodies",
        "figure-fema-flood-zones",
        "figure-streams-impaired-waters",
        "figure-cultural-resources",
        "figure-fire-ems-stations",
        "figure-government-offices",
        "figure-schools-childcare",
        "figure-health-care-facilities",
        "figure-places-of-worship",
        "figure-public-water-supply-wells",
        "figure-energy-infrastructure",
        "figure-hazardous-waste-sites",
        "figure-water-discharge-waste-facilities",
        "figure-oil-gas-wells",
        "figure-census-tracts",
    ]
    assert section_by_id["contamination-risks"].figure_refs == [
        "figure-hazardous-waste-sites",
        "figure-water-discharge-waste-facilities",
    ]
    assert section_by_id["hazardous-materials-sites"].figure_refs == [
        "figure-hazardous-waste-sites",
        "figure-water-discharge-waste-facilities",
    ]
    assert section_by_id["oil-wells"].figure_refs == ["figure-oil-gas-wells"]
    assert set(TARGET_SPECS["figure-hazardous-waste-sites"].source_ids) == {
        "epa_frs_facilities_ms",
        "maris_brownfields",
        "maris_superfund_sites",
        "maris_tri_facilities",
        "maris_underground_storage_tanks",
    }
    assert set(TARGET_SPECS["figure-water-discharge-waste-facilities"].source_ids) == {
        "maris_npdes_facilities",
        "maris_solid_waste_landfills",
    }
    assert TARGET_SPECS["figure-oil-gas-wells"].source_ids == ("mississippi_oil_gas_wells",)


def test_target_specs_declare_figure_specific_source_scope() -> None:
    wetlands = TARGET_SPECS["figure-wetlands-waterbodies"]
    streams = TARGET_SPECS["figure-streams-impaired-waters"]
    hazardous = TARGET_SPECS["figure-hazardous-waste-sites"]
    oil = TARGET_SPECS["figure-oil-gas-wells"]

    assert wetlands.required_source_ids == ("usfws_nwi_wetlands",)
    assert wetlands.optional_source_ids == ("usgs_nhd_waterbodies",)
    assert "usgs_nhd_flowlines" in wetlands.excluded_source_ids
    assert "usgs_nhd_other_areas" in wetlands.excluded_source_ids
    assert "usgs_nhd_flowlines" not in wetlands.source_ids
    assert "usgs_nhd_waterbodies" in wetlands.source_ids
    assert set(streams.required_source_ids) == {
        "usgs_nhd_flowlines",
        "usgs_nhd_waterbodies",
        "usgs_nhd_other_areas",
        "mdeq_303d_impaired_waters",
    }
    assert "usfws_nwi_wetlands" in streams.excluded_source_ids
    assert "mississippi_oil_gas_wells" in hazardous.excluded_source_ids
    assert "maris_npdes_facilities" in oil.excluded_source_ids


def test_deliverable_figures_write_15_matrix_records_and_missing_source_stubs(
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
    assert result["figure_count"] == 15
    assert [figure["figure_id"] for figure in result["figures"]] == matrix_ids
    assert [figure["figure_number"] for figure in result["figures"]] == list(range(1, 16))
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


def test_sid_only_basemap_reports_missing_render_asset_and_vector_figure_still_renders(
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
    assert "basemap_render_asset_missing" in issue_codes(wetlands)
    issue_text = json.dumps(wetlands["validation_issues"])
    assert "Expected project-local asset" in issue_text
    assert "MrSID" not in issue_text
    shown_basemaps = [layer for layer in wetlands["shown_layers"] if layer["layer_type"] == "basemap_provenance"]  # type: ignore[index]
    assert shown_basemaps
    assert shown_basemaps[0]["renderability_status"] == "render_asset_missing"
    assert shown_basemaps[0]["visual_use"] == "missing_not_rendered"
    assert shown_basemaps[0]["unsupported_source_paths"]
    assert "usda_naip_imagery" in wetlands["source_refs"]  # type: ignore[operator]
    assert "maris_naip_2025_imagery" not in wetlands["source_refs"]  # type: ignore[operator]


def test_metadata_only_basemap_reports_missing_render_asset_without_sid_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "naip"
    imagery_dir = write_naip_county(basemap_root)
    (imagery_dir / "Test_NAIP_2025.sid").unlink()
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
    assert "basemap_render_asset_missing" in issue_codes(wetlands)
    shown_basemaps = [layer for layer in wetlands["shown_layers"] if layer["layer_type"] == "basemap_provenance"]  # type: ignore[index]
    assert shown_basemaps
    assert shown_basemaps[0]["renderability_status"] == "render_asset_missing"
    assert shown_basemaps[0]["unsupported_source_paths"] == []
    assert "usda_naip_imagery" in wetlands["source_refs"]  # type: ignore[operator]
    assert "maris_naip_2025_imagery" not in wetlands["source_refs"]  # type: ignore[operator]


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

    assert "basemap_render_asset_missing" in issue_codes(wetlands)
    assert "naip_basemap_materialization_failed" in issue_codes(wetlands)
    assert "maris_naip_2025_imagery" not in wetlands["source_refs"]  # type: ignore[operator]
    assert "usda_naip_imagery" in wetlands["source_refs"]  # type: ignore[operator]
    assert "USDA NAIP Project Basemap render asset missing; vector-only fallback used" in wetlands["source_note"]  # type: ignore[operator]
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
    assert "basemap_render_asset_missing" not in issue_codes(wetlands)
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

    assert result["figure_count"] == 15
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


def test_insufficient_naip_sidecar_extent_falls_back_to_vector_with_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("rasterio")
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_project_local_naip_tif(project_dir, bounds=(-90.001, 31.999, -89.999, 32.001))
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
    )
    write_registry(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson")])

    result = generate_deliverable_figures(project_dir)
    wetlands = figure_by_id(result, "figure-wetlands-waterbodies")

    assert wetlands["is_stub"] is False
    assert "basemap_sidecar_extent_insufficient" in issue_codes(wetlands)
    assert not [layer for layer in wetlands["shown_layers"] if layer["layer_type"] == "basemap"]  # type: ignore[index]
    provenance_layers = [layer for layer in wetlands["shown_layers"] if layer["layer_type"] == "basemap_provenance"]  # type: ignore[index]
    assert provenance_layers
    assert provenance_layers[0]["renderability_status"] == "extent_insufficient"
    issue = next(issue for issue in wetlands["validation_issues"] if issue["code"] == "basemap_sidecar_extent_insufficient")  # type: ignore[index]
    assert "expected_full_render_extent" in issue
    assert "actual_raster_extent" in issue


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

    assert result["figure_count"] == 15
    assert hazardous["is_stub"] is False
    shown_basemaps = [layer for layer in hazardous["shown_layers"] if layer["layer_type"] == "basemap"]  # type: ignore[index]
    assert shown_basemaps
    assert shown_basemaps[0]["source_id"] == "usda_naip_imagery"
    assert shown_basemaps[0]["path"] == str(tif_path)
    assert shown_basemaps[0]["visual_use"] == "rendered_basemap"
    assert "USDA NAIP Project Basemap rendered from sidecar" in hazardous["source_note"]  # type: ignore[operator]


def test_figure_generation_preserves_constraint_counts(
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

    before = analyze_comparison_unit_constraints(project_dir, tolerate_source_errors=True)
    before_counts = (
        before["constraint_count"],
        len(before["constraints"]),
        len(before["sources"]),
    )

    result = generate_deliverable_figures(project_dir)
    after = load_comparison_unit_constraints(project_dir)

    assert result["figure_count"] == 15
    assert (after["constraint_count"], len(after["constraints"]), len(after["sources"])) == before_counts


def test_specific_regulated_sources_are_split_without_legacy_broad_ids(
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
    water_discharge = figure_by_id(result, "figure-water-discharge-waste-facilities")
    oil_gas = figure_by_id(result, "figure-oil-gas-wells")
    serialized_issues = json.dumps(
        [
            *hazardous["validation_issues"],
            *water_discharge["validation_issues"],
            *oil_gas["validation_issues"],
        ]
    )
    hazardous_source_ids = {
        "epa_frs_facilities_ms",
        "maris_brownfields",
        "maris_superfund_sites",
        "maris_tri_facilities",
        "maris_underground_storage_tanks",
    }
    water_source_ids = {"maris_npdes_facilities", "maris_solid_waste_landfills"}
    oil_source_ids = {"mississippi_oil_gas_wells"}

    assert hazardous["is_stub"] is False
    assert water_discharge["is_stub"] is False
    assert oil_gas["is_stub"] is False
    for figure in (hazardous, water_discharge, oil_gas):
        assert "epa_envirofacts_echo" not in figure["source_refs"]  # type: ignore[operator]
        assert "mdeq_environmental_context" not in figure["source_refs"]  # type: ignore[operator]
    assert "epa_envirofacts_echo" not in serialized_issues
    assert "mdeq_environmental_context" not in serialized_issues
    assert hazardous_source_ids == set(hazardous["source_refs"])  # type: ignore[arg-type]
    assert water_source_ids == set(water_discharge["source_refs"])  # type: ignore[arg-type]
    assert oil_source_ids == set(oil_gas["source_refs"])  # type: ignore[arg-type]
    shown_source_ids = {layer.get("source_id") for layer in hazardous["shown_layers"] if layer.get("layer_type") == "source_layer"}  # type: ignore[union-attr]
    shown_water_source_ids = {layer.get("source_id") for layer in water_discharge["shown_layers"] if layer.get("layer_type") == "source_layer"}  # type: ignore[union-attr]
    shown_oil_source_ids = {layer.get("source_id") for layer in oil_gas["shown_layers"] if layer.get("layer_type") == "source_layer"}  # type: ignore[union-attr]
    assert hazardous_source_ids == shown_source_ids
    assert water_source_ids == shown_water_source_ids
    assert oil_source_ids == shown_oil_source_ids
    assert "EPA Facility Registry Service" in hazardous["source_note"]  # type: ignore[operator]
    assert "NPDES" in water_discharge["source_note"]  # type: ignore[operator]
    assert "Oil" in oil_gas["source_note"] or "oil" in oil_gas["source_note"]  # type: ignore[operator]
    assert "EPA FRS hazardous" not in hazardous["source_note"]  # type: ignore[operator]


def test_wetlands_and_streams_figures_honor_required_optional_and_excluded_source_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    layers = [
        (
            "usfws_nwi_wetlands",
            "wetlands.geojson",
            [Polygon([(-90.001, 31.999), (-89.998, 31.999), (-89.998, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
            [{"ATTRIBUTE": "Freshwater Emergent Wetland", "OBJECTID": "wetland-1"}],
        ),
        (
            "usgs_nhd_flowlines",
            "nhd_flowlines.geojson",
            [LineString([(-90.002, 31.998), (-89.997, 32.002)])],
            [{"GNIS_NAME": "Synthetic Creek"}],
        ),
        (
            "usgs_nhd_waterbodies",
            "nhd_waterbodies.geojson",
            [Polygon([(-90.0005, 31.9995), (-89.9995, 31.9995), (-89.9995, 32.0005), (-90.0005, 32.0005), (-90.0005, 31.9995)])],
            [{"GNIS_NAME": "Synthetic Pond"}],
        ),
        (
            "usgs_nhd_other_areas",
            "nhd_other_areas.geojson",
            [Polygon([(-90.002, 31.998), (-89.997, 31.998), (-89.997, 32.003), (-90.002, 32.003), (-90.002, 31.998)])],
            [{"FType": "SwampMarsh"}],
        ),
        (
            "mdeq_303d_impaired_waters",
            "impaired.geojson",
            [LineString([(-90.001, 32.001), (-89.997, 32.001)])],
            [{"ASSESSMENT_UNIT": "Synthetic impaired segment"}],
        ),
    ]
    for _source_id, rel_path, geometries, rows in layers:
        write_layer(project_dir / rel_path, geometries, rows)
    write_registry(project_dir, [(source_id, rel_path) for source_id, rel_path, _geometries, _rows in layers])

    result = generate_deliverable_figures(project_dir)
    wetlands = figure_by_id(result, "figure-wetlands-waterbodies")
    streams = figure_by_id(result, "figure-streams-impaired-waters")

    assert wetlands["is_stub"] is False
    assert shown_source_ids(wetlands) == {"usfws_nwi_wetlands", "usgs_nhd_waterbodies"}
    assert "usgs_nhd_flowlines" not in wetlands["source_refs"]  # type: ignore[operator]
    assert "mdeq_303d_impaired_waters" not in wetlands["source_refs"]  # type: ignore[operator]
    assert wetlands["provenance"]["source_scope"]["required_source_ids"] == ["usfws_nwi_wetlands"]  # type: ignore[index]
    assert wetlands["provenance"]["source_scope"]["optional_source_ids"] == ["usgs_nhd_waterbodies"]  # type: ignore[index]
    assert "usgs_nhd_flowlines" in wetlands["provenance"]["source_scope"]["excluded_source_ids"]  # type: ignore[index]

    assert streams["is_stub"] is False
    assert shown_source_ids(streams) == {
        "usgs_nhd_flowlines",
        "usgs_nhd_waterbodies",
        "usgs_nhd_other_areas",
        "mdeq_303d_impaired_waters",
    }
    assert "usfws_nwi_wetlands" not in streams["source_refs"]  # type: ignore[operator]
    assert streams["provenance"]["source_scope"]["required_source_ids"] == [  # type: ignore[index]
        "usgs_nhd_flowlines",
        "usgs_nhd_waterbodies",
        "usgs_nhd_other_areas",
        "mdeq_303d_impaired_waters",
    ]


def test_cultural_and_community_figures_do_not_bleed_related_context_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_layer(project_dir / "cultural.geojson", [Point(-90.0, 32.0)], [{"NAME": "Public cultural marker"}])
    write_layer(project_dir / "community.geojson", [Point(-89.999, 32.0)], [{"TYPE": "Fire Station"}])
    write_registry(
        project_dir,
        [
            ("maris_public_cultural_context", "cultural.geojson"),
            ("maris_community_facilities", "community.geojson"),
        ],
    )

    result = generate_deliverable_figures(project_dir)
    cultural = figure_by_id(result, "figure-cultural-resources")
    fire = figure_by_id(result, "figure-fire-ems-stations")

    assert cultural["is_stub"] is False
    assert shown_source_ids(cultural) == {"maris_public_cultural_context"}
    assert "maris_community_facilities" not in cultural["source_refs"]  # type: ignore[operator]
    assert fire["is_stub"] is False
    assert shown_source_ids(fire) == {"maris_community_facilities"}
    assert "maris_public_cultural_context" not in fire["source_refs"]  # type: ignore[operator]


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

    assert result["figure_count"] == 15
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
                "comparison_unit_name": "Orange route",
                "style_color": "ff009fe6",
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
    assert styles[2]["color"] not in {"#e69f00", "#ff9900"}
    assert color_distance(styles[0]["color"], styles[2]["color"]) > 120
    assert styles[2]["style_source"] == "deterministic_fallback_replaces_kml_color"
    assert all(1.15 <= style["line_width"] <= 1.25 for style in styles)
    assert all(style["line_halo_width"] == 0.0 for style in styles)
    assert all(style["line_halo_alpha"] == 0.0 for style in styles)
    assert color_distance(styles[0]["color"], styles[1]["color"]) > 120


def test_comparison_unit_fallback_colors_are_distinct_and_deterministic() -> None:
    rows = [
        {
            "comparison_unit_id": f"comparison-unit-{index + 1:05d}",
            "comparison_unit_name": f"Alternative {index + 1}",
            "style_color": "",
        }
        for index in range(5)
    ]
    gdf = gpd.GeoDataFrame(
        rows,
        geometry=[
            LineString([(-90.0, 32.0 + index * 0.001), (-89.99, 32.0 + index * 0.001)])
            for index in range(5)
        ],
        crs="EPSG:4326",
    )

    styles = comparison_unit_style_records(gdf)
    repeated = comparison_unit_style_records(gdf)
    colors = [style["color"] for style in styles]

    assert styles == repeated
    assert colors == ["#004CFF", "#FF2A00", "#8A00FF", "#00D5FF", "#FF00FF"]
    assert "#D55E00" not in colors
    assert "#C1121F" not in colors
    assert "#009E73" not in colors
    assert "#111111" not in colors
    assert "#000000" not in colors
    assert min(color_distance(a, b) for index, a in enumerate(colors) for b in colors[index + 1 :]) > 78
    assert all(style["line_width"] == pytest.approx(1.2) for style in styles)
    assert all(style["line_halo_width"] == 0.0 for style in styles)


def test_comparison_unit_muted_green_kml_color_is_replaced_for_imagery_readability() -> None:
    gdf = gpd.GeoDataFrame(
        [
            {
                "comparison_unit_id": "comparison-unit-00001",
                "comparison_unit_name": "Muted green route",
                "style_color": "ff739e00",
            }
        ],
        geometry=[LineString([(-90.0, 32.0), (-89.99, 32.0)])],
        crs="EPSG:4326",
    )

    styles = comparison_unit_style_records(gdf)

    assert styles[0]["color"] == "#004CFF"
    assert styles[0]["style_source"] == "deterministic_fallback_replaces_kml_color"


def test_comparison_unit_bright_green_kml_color_is_allowed() -> None:
    gdf = gpd.GeoDataFrame(
        [
            {
                "comparison_unit_id": "comparison-unit-00001",
                "comparison_unit_name": "Bright green route",
                "style_color": "ff76e600",
            }
        ],
        geometry=[LineString([(-90.0, 32.0), (-89.99, 32.0)])],
        crs="EPSG:4326",
    )

    styles = comparison_unit_style_records(gdf)

    assert styles[0]["color"] == "#00e676"
    assert styles[0]["style_source"] == "kml_style_color"


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
    assert all(style["marker_edge_color"] == "#111827" for style in styles)
    assert all(style["marker_halo_alpha"] > 0.6 for style in styles)


def test_source_marker_styles_avoid_green_on_imagery() -> None:
    layers = [
        {"source_id": "maris_public_cultural_context", "source_name": "Public Cultural Context", "source_category": "cultural_historic"},
        {"source_id": "maris_underground_storage_tanks", "source_name": "Underground Storage Tanks", "source_category": "regulated_facilities"},
        {"source_id": "usfws_nwi_wetlands", "source_name": "National Wetlands Inventory", "source_category": "wetlands_waterbodies"},
        {"source_id": "unknown_context", "source_name": "Unknown Context", "source_category": "cultural_historic"},
    ]

    styles = [source_layer_style_record(layer, index) for index, layer in enumerate(layers)]
    colors = [style["color"] for style in styles]

    assert "#6BAA75" not in colors
    assert "#009E73" not in colors
    assert styles[0]["color"] == "#FF00FF"
    assert styles[1]["color"] == "#00D5FF"
    assert styles[2]["color"] == "#FFE500"
    assert styles[3]["color"] == "#F72585"
    assert all(style["marker_edge_width"] >= 0.4 for style in styles)


def test_wetlands_and_hydrography_source_styles_use_saturated_high_contrast_overlays() -> None:
    layers = [
        {"source_id": "usfws_nwi_wetlands", "source_name": "National Wetlands Inventory", "source_category": "wetlands_waterbodies"},
        {"source_id": "usgs_nhd_flowlines", "source_name": "USGS NHD Flowlines Mississippi", "source_category": "hydrography_crossings"},
        {"source_id": "usgs_nhd_waterbodies", "source_name": "USGS NHD Waterbodies Mississippi", "source_category": "hydrography_crossings"},
        {"source_id": "usgs_nhd_other_areas", "source_name": "USGS NHD Other Areas Mississippi", "source_category": "hydrography_crossings"},
    ]

    styles = [source_layer_style_record(layer, index) for index, layer in enumerate(layers)]

    assert [style["color"] for style in styles] == ["#FFE500", "#00D5FF", "#0057FF", "#FF00FF"]
    assert styles[0]["polygon_alpha"] >= 0.38
    assert styles[1]["line_width"] >= 0.8
    assert styles[1]["line_alpha"] >= 0.8
    assert styles[2]["polygon_alpha"] <= 0.26
    assert styles[3]["line_alpha"] >= 0.86


def test_thematic_palette_rejects_black_washed_out_green_and_earth_tone_colors() -> None:
    for color in ("#000000", "#111111", "#B8C0C0", "#8C7A3A", "#739E00", "#6BAA75", "#00FF66"):
        assert _thematic_color_is_allowed(color) is False

    fallback_layers = [
        {"source_id": "maris_solid_waste_landfills", "source_name": "Landfills", "source_category": "regulated_facilities"},
        {"source_id": "mississippi_oil_gas_wells", "source_name": "Oil Wells", "source_category": "regulated_facilities"},
        {"source_id": "unknown_context", "source_name": "Unknown", "source_category": "unknown_category"},
        {"source_id": "unknown_soils", "source_name": "Soils", "source_category": "soils"},
    ]
    styles = [source_layer_style_record(layer, index) for index, layer in enumerate(fallback_layers)]
    colors = [style["color"] for style in styles]

    assert all(_thematic_color_is_allowed(color) for color in colors)
    assert "#111111" not in colors
    assert "#6BAA75" not in colors
    assert "#8C564B" not in colors
    assert len({style["color"] for style in styles}) >= 3


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
    measurement = layout["legend_measurement"]
    collar_x0, collar_y0, collar_x1, collar_y1 = layout["collar_bbox_axes"]
    assert measurement["measurement_method"] == "matplotlib_legend_bbox"
    if layout["legend_side"] in {"right", "left"}:
        assert (collar_x1 - collar_x0) >= measurement["legend_bbox_width_fraction"] * LEGEND_MEASUREMENT_SAFETY_FACTOR
    else:
        assert (collar_y1 - collar_y0) >= measurement["legend_bbox_height_fraction"] * LEGEND_MEASUREMENT_SAFETY_FACTOR


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


def test_render_map_measured_side_collar_contains_legend_without_core_overlap(tmp_path: Path) -> None:
    unit_gdf = gpd.GeoDataFrame(
        [{"comparison_unit_id": "comparison-unit-00001", "comparison_unit_name": "Alternative A"}],
        geometry=[LineString([(0, 0), (0, 16_000)])],
        crs="EPSG:32616",
    )
    source_layers: list[dict[str, object]] = []
    for index in range(10):
        source_layers.append(
            {
                "source_id": f"synthetic_source_{index}",
                "source_name": f"Long Synthetic Source Layer {index}",
                "source_category": "regulated_facilities",
                "gdf": gpd.GeoDataFrame(
                    [{"name": f"source {index}"}],
                    geometry=[Point(80 + index * 6, 1000 + index * 1200)],
                    crs="EPSG:32616",
                ),
            }
        )

    layout = render_map(
        output_path=tmp_path / "measured-collar.png",
        title="Measured collar test",
        unit_gdf=unit_gdf,
        analysis_crs="EPSG:32616",
        source_layers=source_layers,  # type: ignore[arg-type]
        basemap={"layer": None},
        method_note="metadata only",
        source_note="metadata only",
        focus_bounds=(-2500, 0, 2500, 16_000),
    )

    legend_bbox = layout["legend_actual_bbox_axes"]
    reserved_bbox = layout["legend_bbox_axes"]
    core_bbox = layout["core_bbox_axes"]
    measurement = layout["legend_measurement"]
    assert layout["legend_side"] in {"right", "left"}
    assert layout["legend_fits_reserved_bbox"] is True
    assert layout["legend_overlaps_core_bbox"] is False
    assert reserved_bbox[0] <= legend_bbox[0] < legend_bbox[2] <= reserved_bbox[2]
    assert legend_bbox[2] <= 1.0
    if layout["legend_side"] == "right":
        assert legend_bbox[0] >= core_bbox[2]
    else:
        assert legend_bbox[2] <= core_bbox[0]
    assert measurement["legend_bbox_width_fraction"] * LEGEND_MEASUREMENT_SAFETY_FACTOR <= (
        layout["collar_bbox_axes"][2] - layout["collar_bbox_axes"][0]
    )
    assert layout["render_extent_is_presentation_only"] is True


def test_render_map_keeps_report_text_out_of_image_canvas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    long_text_output_path = tmp_path / "compact-map-long-text.png"
    title_calls: list[str] = []

    def record_title(_axes: object, label: object = "", *args: object, **kwargs: object) -> object:
        title_calls.append(str(label))
        return None

    monkeypatch.setattr(Axes, "set_title", record_title)

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
        focus_bounds=(-1500, 0, 1500, 10_000),
    )
    long_text_layout = render_map(
        output_path=long_text_output_path,
        title="Hazardous Waste Sites near the Project Area " * 18,
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
        method_note="Method note text that must remain metadata only. " * 20,
        source_note="Source note text that must remain metadata only. " * 20,
        focus_bounds=(-1500, 0, 1500, 10_000),
    )

    image = plt.imread(output_path)
    long_text_image = plt.imread(long_text_output_path)
    height, width = image.shape[:2]
    assert height > width * 1.25
    assert width < 950
    assert long_text_image.shape[:2] == image.shape[:2]
    assert layout["layout_strategy"] == "legend_collar"
    assert layout["legend_side"] in {"right", "left"}
    assert layout["legend_fits_reserved_bbox"] is True
    assert layout["legend_overlaps_core_bbox"] is False
    assert layout["image_text_policy"] == {
        "map_panel_only": True,
        "embedded_title": False,
        "embedded_caption": False,
        "embedded_source_note": False,
        "embedded_method_note": False,
    }
    assert long_text_layout["image_text_policy"]["map_panel_only"] is True
    assert title_calls == []


def test_public_water_supply_wells_figure_renders_project_local_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_layer(
        project_dir / "pws.geojson",
        [Point(-89.995, 32.0002)],
        [{"Owner_Name": "Test Water System", "PermitNumb": "PWS-1", "Beneficial": "PS"}],
    )
    write_registry(project_dir, [("mdeq_public_water_supply_wells", "pws.geojson")])

    result = generate_deliverable_figures(project_dir)
    wells = figure_by_id(result, "figure-public-water-supply-wells")
    source_layer = next(layer for layer in wells["shown_layers"] if layer.get("source_id") == "mdeq_public_water_supply_wells")  # type: ignore[index]

    assert result["figure_count"] == 15
    assert wells["is_stub"] is False
    assert Path(str(wells["image_path"])).exists()
    assert wells["source_refs"] == ["mdeq_public_water_supply_wells"]
    assert source_layer["feature_count"] == 1
    assert source_layer["legend_label"] == "PWS wells"
    assert "figure_source_unimplemented" not in issue_codes(wells)
    assert "figure_source_missing" not in issue_codes(wells)
    assert "Public water supply wells are mapped context only" in wells["source_note"]  # type: ignore[operator]


def test_streams_impaired_waters_spec_uses_physical_nhd_and_303d_sources() -> None:
    spec = TARGET_SPECS["figure-streams-impaired-waters"]

    assert "mdeq_303d_impaired_waters" in spec.source_ids
    assert "usgs_nhd_flowlines" in spec.source_ids
    assert "usgs_nhd_waterbodies" in spec.source_ids
    assert "usgs_nhd_other_areas" in spec.source_ids
    assert "usgs_nhd_hydrography" not in spec.source_ids


def test_streams_impaired_waters_figure_renders_nhd_and_303d_with_watershed_limitation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_layer(
        project_dir / "nhd.geojson",
        [LineString([(-90.0005, 31.9995), (-89.998, 32.001)])],
        [{"GNIS_NAME": "Test Creek", "FTYPE": "StreamRiver"}],
    )
    write_layer(
        project_dir / "nhd_waterbody.geojson",
        [Polygon([(-89.999, 32.0005), (-89.9987, 32.0005), (-89.9987, 32.0008), (-89.999, 32.0008), (-89.999, 32.0005)])],
        [{"GNIS_NAME": "Test Pond", "FTYPE": "LakePond"}],
    )
    write_layer(
        project_dir / "nhd_other_area.geojson",
        [Polygon([(-89.9994, 31.9997), (-89.9991, 31.9997), (-89.9991, 32.0), (-89.9994, 32.0), (-89.9994, 31.9997)])],
        [{"GNIS_NAME": "Test Area", "FTYPE": "Area"}],
    )
    write_layer(
        project_dir / "impaired.geojson",
        [LineString([(-90.0002, 31.9996), (-89.9982, 32.0009)])],
        [{"WATER_BODY_NAME": "Test Creek", "review_assist_mdeq_303d_status": "TMDL complete", "review_assist_list_year": "2024"}],
    )
    write_registry(
        project_dir,
        [
            ("usgs_nhd_flowlines", "nhd.geojson"),
            ("usgs_nhd_waterbodies", "nhd_waterbody.geojson"),
            ("usgs_nhd_other_areas", "nhd_other_area.geojson"),
            ("mdeq_303d_impaired_waters", "impaired.geojson"),
        ],
    )

    result = generate_deliverable_figures(project_dir)
    streams = figure_by_id(result, "figure-streams-impaired-waters")
    source_ids = {layer.get("source_id") for layer in streams["shown_layers"]}  # type: ignore[index]

    assert result["figure_count"] == 15
    assert streams["is_stub"] is False
    assert Path(str(streams["image_path"])).exists()
    assert {"usgs_nhd_flowlines", "mdeq_303d_impaired_waters"} <= source_ids
    assert "mdeq_303d_impaired_waters" in streams["source_refs"]  # type: ignore[operator]
    assert "usgs_nhd_flowlines" in streams["source_refs"]  # type: ignore[operator]
    assert "usgs_nhd_waterbodies" in streams["source_refs"]  # type: ignore[operator]
    assert "usgs_nhd_other_areas" in streams["source_refs"]  # type: ignore[operator]
    assert "usgs_nhd_hydrography" not in streams["source_refs"]  # type: ignore[operator]
    assert "figure_created_as_stub" not in issue_codes(streams)
    assert "figure_source_missing" not in issue_codes(streams)
    assert "figure_extent_context_deferred" in issue_codes(streams)
    assert "NHD hydrography is shown" in streams["source_note"]  # type: ignore[operator]
    assert "MDEQ 303(d) impaired waters and TMDL-complete waters are shown" in streams["source_note"]  # type: ignore[operator]
    assert "Watershed/subwatershed context remains deferred" in streams["source_note"]  # type: ignore[operator]
    assert streams["provenance"]["figure_extent_plan"]["status"] == "planned_current_project_area_context"  # type: ignore[index]
    assert streams["provenance"]["figure_extent_plan"]["basemap_materialization_group"] == ""  # type: ignore[index]


def test_streams_figure_does_not_claim_303d_when_only_nhd_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_layer(
        project_dir / "nhd.geojson",
        [LineString([(-90.0005, 31.9995), (-89.998, 32.001)])],
        [{"GNIS_NAME": "Test Creek", "FTYPE": "StreamRiver"}],
    )
    write_layer(
        project_dir / "nhd_waterbody.geojson",
        [Polygon([(-89.999, 32.0005), (-89.9987, 32.0005), (-89.9987, 32.0008), (-89.999, 32.0008), (-89.999, 32.0005)])],
        [{"GNIS_NAME": "Test Pond", "FTYPE": "LakePond"}],
    )
    write_layer(
        project_dir / "nhd_other_area.geojson",
        [Polygon([(-89.9994, 31.9997), (-89.9991, 31.9997), (-89.9991, 32.0), (-89.9994, 32.0), (-89.9994, 31.9997)])],
        [{"GNIS_NAME": "Test Area", "FTYPE": "Area"}],
    )
    write_registry(project_dir, [("usgs_nhd_flowlines", "nhd.geojson")])

    result = generate_deliverable_figures(project_dir)
    streams = figure_by_id(result, "figure-streams-impaired-waters")

    assert streams["is_stub"] is False
    assert "usgs_nhd_flowlines" in streams["source_refs"]  # type: ignore[operator]
    assert "mdeq_303d_impaired_waters" not in streams["source_refs"]  # type: ignore[operator]
    assert "MDEQ 303(d) impaired waters and TMDL-complete waters are shown" not in streams["source_note"]  # type: ignore[operator]
    assert any(
        issue.get("code") == "figure_source_missing" and issue.get("source_id") == "mdeq_303d_impaired_waters"
        for issue in streams["validation_issues"]  # type: ignore[union-attr]
    )


def test_new_source_figure_refs_flow_into_deliverable_items_and_review_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    write_layer(
        project_dir / "pws.geojson",
        [Point(-89.995, 32.0002)],
        [{"Owner_Name": "Test Water System", "PermitNumb": "PWS-1", "Beneficial": "PS"}],
    )
    write_layer(
        project_dir / "nhd.geojson",
        [LineString([(-90.0005, 31.9995), (-89.998, 32.001)])],
        [{"GNIS_NAME": "Test Creek", "FTYPE": "StreamRiver"}],
    )
    write_layer(
        project_dir / "nhd_waterbody.geojson",
        [Polygon([(-89.999, 32.0005), (-89.9987, 32.0005), (-89.9987, 32.0008), (-89.999, 32.0008), (-89.999, 32.0005)])],
        [{"GNIS_NAME": "Test Pond", "FTYPE": "LakePond"}],
    )
    write_layer(
        project_dir / "nhd_other_area.geojson",
        [Polygon([(-89.9994, 31.9997), (-89.9991, 31.9997), (-89.9991, 32.0), (-89.9994, 32.0), (-89.9994, 31.9997)])],
        [{"GNIS_NAME": "Test Area", "FTYPE": "Area"}],
    )
    write_layer(
        project_dir / "impaired.geojson",
        [LineString([(-90.0002, 31.9996), (-89.9982, 32.0009)])],
        [{"WATER_BODY_NAME": "Test Creek", "review_assist_mdeq_303d_status": "TMDL complete", "review_assist_list_year": "2024"}],
    )
    write_layer(
        project_dir / "huc12.geojson",
        [
            Polygon(
                [
                    (-90.1, 31.9),
                    (-89.9, 31.9),
                    (-89.9, 32.1),
                    (-90.1, 32.1),
                    (-90.1, 31.9),
                ]
            )
        ],
        [{"huc12": "080302010407", "name": "Test Creek", "tohuc": "080302010408"}],
    )
    write_registry(
        project_dir,
        [
            ("mdeq_public_water_supply_wells", "pws.geojson"),
            ("usgs_nhd_flowlines", "nhd.geojson"),
            ("usgs_nhd_waterbodies", "nhd_waterbody.geojson"),
            ("usgs_nhd_other_areas", "nhd_other_area.geojson"),
            ("mdeq_303d_impaired_waters", "impaired.geojson"),
            ("usgs_wbd_huc12_subwatersheds", "huc12.geojson"),
        ],
    )

    figures = generate_deliverable_figures(project_dir)
    evidence = build_evidence_package(project_dir)
    items = generate_deliverable_items(project_dir, gpt_drafting=False)
    queue = generate_review_queue(project_dir)
    streams = figure_by_id(figures, "figure-streams-impaired-waters")
    water_quality_evidence = evidence["section_evidence"]["water-quality"]

    pws_item = next(item for item in items["items"] if item["deliverable_item_id"] == "public-water-supply")
    water_quality_item = next(item for item in items["items"] if item["deliverable_item_id"] == "water-quality")
    pws_queue = next(item for item in queue["items"] if item["id"] == "public-water-supply")
    water_quality_queue = next(item for item in queue["items"] if item["id"] == "water-quality")
    serialized = json.dumps({"items": items, "queue": queue})

    assert "figure-public-water-supply-wells" in pws_item["related_figure_ids"]
    assert "figure-streams-impaired-waters" in water_quality_item["related_figure_ids"]
    assert "figure-wetlands-waterbodies" in water_quality_item["related_figure_ids"]
    assert "table-wetlands-waterbodies" in water_quality_item["related_table_ids"]
    assert "figure-public-water-supply-wells" in pws_queue["related_figure_ids"]
    assert "figure-streams-impaired-waters" in water_quality_queue["related_figure_ids"]
    assert "figure-wetlands-waterbodies" in water_quality_queue["related_figure_ids"]
    assert "table-wetlands-waterbodies" in water_quality_queue["related_table_ids"]
    assert water_quality_item["render_decision"] == "include_body"
    assert water_quality_item["report_body_eligible"] is True
    assert water_quality_item["manual_material"]["material_status"] == "source_backed_generated"
    assert "mdeq_303d_impaired_waters" in water_quality_item["source_refs"]
    assert "mdeq_303d_impaired_waters" in water_quality_queue["source_refs"]
    assert "usgs_nhd_flowlines" in water_quality_item["source_refs"]
    assert "usgs_nhd_flowlines" in water_quality_queue["source_refs"]
    assert "usgs_nhd_waterbodies" in water_quality_item["source_refs"]
    assert "usgs_nhd_waterbodies" in water_quality_queue["source_refs"]
    assert "usgs_nhd_other_areas" in water_quality_item["source_refs"]
    assert "usgs_nhd_other_areas" in water_quality_queue["source_refs"]
    assert "usgs_wbd_huc12_subwatersheds" in streams["source_refs"]
    assert "usgs_wbd_huc12_subwatersheds" in water_quality_evidence["source_refs"]
    assert "usgs_wbd_huc12_subwatersheds" in water_quality_item["source_refs"]
    assert "usgs_wbd_huc12_subwatersheds" in water_quality_queue["source_refs"]
    assert "USGS WBD HUC-12 subwatershed boundaries are shown" in streams["source_note"]
    assert "Materialized HUC-12 watershed/subwatershed polygons are available" in streams["source_selection_reason"]
    assert "Materialized HUC-12 watershed/subwatershed polygons are available" in water_quality_evidence["source_selection_reason"]
    assert not any(issue["code"] == "figure_extent_context_deferred" for issue in streams["validation_issues"])
    assert not any(issue["code"] == "figure_extent_context_deferred" for issue in water_quality_item["validation_issues"])
    assert "usgs_nhd_hydrography" not in water_quality_item["source_refs"]
    assert "usgs_nhd_hydrography" not in water_quality_queue["source_refs"]
    assert not any(issue["code"] == "figure_created_as_stub" for issue in pws_item["validation_issues"])
    assert not any(issue["code"] == "figure_created_as_stub" for issue in water_quality_item["validation_issues"])
    assert "source_download_failed" not in serialized
    assert "source_not_downloaded" not in serialized


def test_figure_extent_plan_records_small_medium_and_deferred_watershed_classes(
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
        [{"ATTRIBUTE": "Freshwater Emergent Wetland"}],
    )
    write_layer(
        project_dir / "community.geojson",
        [Point(-89.997, 32.0005)],
        [{"NAME": "Test Fire Station", "TYPE": "Fire Station"}],
    )
    write_layer(
        project_dir / "nhd.geojson",
        [LineString([(-90.0005, 31.9995), (-89.998, 32.001)])],
        [{"GNIS_NAME": "Test Creek"}],
    )
    write_registry(
        project_dir,
        [
            ("usfws_nwi_wetlands", "wetlands.geojson"),
            ("maris_community_facilities", "community.geojson"),
            ("usgs_nhd_flowlines", "nhd.geojson"),
        ],
    )

    plan = generate_figure_extent_plan(project_dir)

    wetlands = plan_figure_by_id(plan, "figure-wetlands-waterbodies")
    fire = plan_figure_by_id(plan, "figure-fire-ems-stations")
    streams = plan_figure_by_id(plan, "figure-streams-impaired-waters")
    census = plan_figure_by_id(plan, "figure-census-tracts")
    groups = {str(group["group_id"]): group for group in plan["basemap_materialization_groups"]}  # type: ignore[index]

    assert wetlands["extent_class"] == "small_direct"
    assert wetlands["status"] == "planned"
    assert wetlands["basemap_materialization_group"] == "small_direct"
    assert wetlands["render_extent_is_presentation_only"] is True
    assert len(wetlands["full_render_bounds"]) == 4  # type: ignore[arg-type]
    assert wetlands["full_render_bounds"][2] > wetlands["core_bounds"][2]  # type: ignore[index]
    assert wetlands["map_furniture"]["legend"]["placement"] == "presentation_collar"  # type: ignore[index]

    assert fire["extent_class"] == "medium_context"
    assert fire["status"] == "planned_current_project_area_context"
    assert fire["basemap_materialization_group"] == "medium_context"
    assert fire["core_bounds"][0] < wetlands["core_bounds"][0]  # type: ignore[index]

    assert streams["extent_class"] == "large_watershed"
    assert streams["status"] == "planned_current_project_area_context"
    assert streams["basemap_materialization_group"] == ""
    assert any(issue["code"] == "figure_extent_context_deferred" for issue in plan["validation_issues"])  # type: ignore[index]

    assert census["extent_class"] == "county_regional"
    assert census["core_extent_type"] == "county_or_regional_context_extent"
    assert census["basemap_materialization_group"] == ""
    assert set(groups) == {"medium_context", "small_direct"}


def test_cli_plan_figure_extents_json_writes_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_dir = write_project(tmp_path)
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)

    assert main(["plan-figure-extents", str(project_dir), "--json"]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["figure_count"] == 15
    assert result["output_path"].endswith("maps\\figure_extent_plan.json") or result["output_path"].endswith("maps/figure_extent_plan.json")
    assert (project_dir / "maps" / "figure_extent_plan.json").exists()


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

    assert result["figure_count"] == 15
    assert wetlands["is_stub"] is False
    assert result["extent_policy"]["core_rule"].startswith("Rendered map extent")
    assert wetlands["query_extent_type"] == "project_area_analysis_bounds"
    assert wetlands["figure_extent_type"] == "direct_intersection_extent"
    assert wetlands["render_extent_type"] == "figure_render_extent"
    assert wetlands["render_extent_is_presentation_only"] is True
    assert wetlands["provenance"]["render_layout"]["layout_strategy"] == "legend_collar"  # type: ignore[index]
    assert wetlands["provenance"]["render_layout"]["render_extent_is_presentation_only"] is True  # type: ignore[index]
    assert wetlands["figure_policy"]["render_extent_is_presentation_only"] is True  # type: ignore[index]
    assert wetlands["provenance"]["figure_policy"]["visual_extent_class"] == "small_direct"  # type: ignore[index]
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
    assert "HUC-12" in streams["source_selection_reason"]
    assert "until HUC-12 watershed/subwatershed context is materialized" in streams["source_selection_reason"]


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

    assert result["figure_count"] == 15
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
        "figure_policy",
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
    assert result["figure_count"] == 15
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
    assert load_deliverable_figures(project_dir)["figure_count"] == 15

    result = populate_for_review(project_dir)

    assert result["artifact_paths"]["deliverable_figures"].endswith("figures.json")
    assert result["deliverable_figure_count"] == 15
