from __future__ import annotations

import json
import sys
import types
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from shapely.geometry import box, mapping

import review_assist.naip_basemap_materialization as naip_module
import review_assist.project_area as project_area_module
import review_assist.populate_for_review as populate_module
from review_assist.basemaps import USDA_NAIP_SOURCE_ID, discover_project_local_naip_basemaps
from review_assist.cli import main
from review_assist.deliverable_figure_basemaps import load_basemap
from review_assist.naip_basemap_materialization import (
    NaipBasemapDependencyError,
    materialize_naip_basemap,
    select_naip_items,
)
from review_assist.populate_for_review import populate_for_review
from review_assist.project_area import build_project_area
from review_assist.source_status import resolve_source_status_set


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


def write_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    kml = kml_document(
        """
        <Placemark><name>Feature A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """
    )
    (project_dir / "inputs" / "project_features.kmz").write_bytes(kmz_bytes(kml))
    (project_dir / "config" / "project.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "name": "Test Project",
                "description": "Synthetic project",
                "project_type": "alternatives_review",
                "inputs": [
                    {
                        "path": "inputs/project_features.kmz",
                        "role": "alternatives",
                        "description": "Synthetic project feature input",
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
    empty_basemap_root = tmp_path / "empty_naip"
    empty_basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", empty_basemap_root)
    return project_dir


def write_existing_sidecar(project_dir: Path, *, year: int = 2023) -> tuple[Path, Path]:
    output_dir = project_dir / "basemaps" / "naip" / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)
    sidecar_path = output_dir / "naip_project_basemap.tif"
    sidecar_path.write_bytes(b"fake-geotiff")
    metadata_path = output_dir / "naip_project_basemap.json"
    metadata_path.write_text(
        json.dumps(
            {
                "source_id": USDA_NAIP_SOURCE_ID,
                "display_name": "USDA NAIP Project Basemap",
                "provider": "Microsoft Planetary Computer",
                "collection_id": "naip",
                "asset_key": "image",
                "item_ids": ["ms_fake_2023"],
                "item_datetimes": ["2023-08-13T16:00:00Z"],
                "source_datetime": "2023-08-13T16:00:00Z",
                "naip_year": year,
                "source_hrefs": ["https://example.invalid/naip.tif"],
                "signed_hrefs_stored": False,
                "aoi_source": "project_analysis_bounds",
                "aoi_bounds_wgs84": {"west": -90.1, "south": 31.9, "east": -89.9, "north": 32.1},
                "output_path": f"basemaps/naip/{year}/naip_project_basemap.tif",
                "output_crs": "EPSG:4326",
                "output_bounds": [-90.1, 31.9, -89.9, 32.1],
                "output_bounds_wgs84": {"west": -90.1, "south": 31.9, "east": -89.9, "north": 32.1},
                "output_shape": [2, 2],
                "pixel_count": 4,
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
    return sidecar_path, metadata_path


def fake_item(item_id: str, year: int, bounds: tuple[float, float, float, float]) -> dict[str, Any]:
    return {
        "id": item_id,
        "bbox": list(bounds),
        "geometry": mapping(box(*bounds)),
        "properties": {"datetime": f"{year}-08-13T16:00:00Z"},
        "assets": {"image": {"href": f"https://example.invalid/{item_id}.tif"}},
    }


def fake_raster_info() -> dict[str, Any]:
    return {
        "output_crs": "EPSG:4326",
        "output_bounds": [-90.1, 31.9, -89.9, 32.1],
        "output_bounds_wgs84": {"west": -90.1, "south": 31.9, "east": -89.9, "north": 32.1},
        "output_shape": [2, 2],
        "pixel_count": 4,
        "source_hrefs": ["https://example.invalid/ms_fake_2023.tif"],
    }


def test_existing_sidecar_reuse_avoids_stac_query(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path, monkeypatch)
    sidecar_path, metadata_path = write_existing_sidecar(project_dir)

    def fail_query(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("Existing NAIP sidecar reuse should not query STAC.")

    monkeypatch.setattr(naip_module, "_query_naip_items", fail_query)

    result = materialize_naip_basemap(project_dir, year=2023)

    assert result["status"] == "reused"
    assert result["success"] is True
    assert result["sidecar_path"] == str(sidecar_path)
    assert result["metadata_path"] == str(metadata_path)
    project_area = json.loads((project_dir / "context" / "project_area.json").read_text(encoding="utf-8"))
    assert str(sidecar_path) in project_area["renderable_basemap_paths"]


def test_successful_materialization_writes_metadata_and_project_area(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, monkeypatch)
    item = fake_item("ms_fake_2023", 2023, (-90.1, 31.9, -89.9, 32.1))
    monkeypatch.setattr(naip_module, "_load_imagery_dependencies", lambda: object())
    monkeypatch.setattr(naip_module, "_query_naip_items", lambda *args, **kwargs: [item])

    def fake_write(selected_items: list[dict[str, Any]], output_path: Path, **kwargs: Any) -> dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-geotiff")
        return fake_raster_info()

    monkeypatch.setattr(naip_module, "_write_basemap_raster", fake_write)

    result = materialize_naip_basemap(project_dir)

    assert result["status"] == "completed"
    metadata = json.loads(Path(str(result["metadata_path"])).read_text(encoding="utf-8"))
    assert metadata["source_id"] == USDA_NAIP_SOURCE_ID
    assert metadata["output_path"] == "basemaps/naip/2023/naip_project_basemap.tif"
    assert metadata["signed_hrefs_stored"] is False
    records = discover_project_local_naip_basemaps(project_dir)
    assert records and records[0]["source_id"] == USDA_NAIP_SOURCE_ID
    project_area = json.loads((project_dir / "context" / "project_area.json").read_text(encoding="utf-8"))
    assert result["sidecar_path"] in project_area["renderable_basemap_paths"]


def test_selection_prefers_latest_year_then_datetime_overlap_and_id() -> None:
    aoi = box(-90.05, 31.95, -89.95, 32.05)
    items = [
        fake_item("older_large", 2021, (-91, 31, -89, 33)),
        fake_item("newer_small_b", 2023, (-90.02, 31.98, -89.98, 32.02)),
        fake_item("newer_small_a", 2023, (-90.02, 31.98, -89.98, 32.02)),
    ]

    selected = select_naip_items(items, aoi, max_tiles=12)

    assert [item["id"] for item in selected] == ["newer_small_a", "newer_small_b"]


def test_materialization_fails_before_raster_when_tile_limit_exceeded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, monkeypatch)
    items = [
        fake_item("tile_a", 2023, (-90.1, 31.9, -89.9, 32.1)),
        fake_item("tile_b", 2023, (-90.2, 31.9, -89.8, 32.1)),
    ]
    monkeypatch.setattr(naip_module, "_load_imagery_dependencies", lambda: object())
    monkeypatch.setattr(naip_module, "_query_naip_items", lambda *args, **kwargs: items)

    def fail_write(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("Raster writing should not run after tile limit failure.")

    monkeypatch.setattr(naip_module, "_write_basemap_raster", fail_write)

    result = materialize_naip_basemap(project_dir, max_tiles=1)

    assert result["status"] == "failed"
    assert "exceeding --max-tiles 1" in result["message"]
    assert (project_dir / "basemaps" / "naip" / "naip_basemap_materialization.json").exists()


def test_missing_optional_dependencies_are_reported_as_controlled_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, monkeypatch)
    monkeypatch.setattr(
        naip_module,
        "_load_imagery_dependencies",
        lambda: (_ for _ in ()).throw(NaipBasemapDependencyError('Install them with: pip install "review-assist[imagery]".')),
    )

    result = materialize_naip_basemap(project_dir)

    assert result["status"] == "failed"
    assert "review-assist[imagery]" in result["message"]
    assert result["validation_issues"][0]["code"] == "naip_basemap_materialization_failed"


def test_cli_materialize_naip_basemap_json_reuses_existing_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_dir = write_project(tmp_path, monkeypatch)
    write_existing_sidecar(project_dir)

    assert main(["materialize-naip-basemap", str(project_dir), "--json"]) == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["status"] == "reused"
    assert result["source_id"] == USDA_NAIP_SOURCE_ID


def test_cli_materialize_naip_basemap_failure_writes_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_dir = write_project(tmp_path, monkeypatch)
    monkeypatch.setattr(
        naip_module,
        "_load_imagery_dependencies",
        lambda: (_ for _ in ()).throw(NaipBasemapDependencyError("missing imagery dependencies")),
    )

    assert main(["materialize-naip-basemap", str(project_dir)]) == 1

    captured = capsys.readouterr()
    assert "missing imagery dependencies" in captured.err
    assert (project_dir / "basemaps" / "naip" / "naip_basemap_materialization.json").exists()


def test_load_basemap_prefers_project_local_naip_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    sidecar_path, _ = write_existing_sidecar(project_dir)

    class FakeDataset:
        count = 3
        crs = "EPSG:4326"
        bounds = (-90.1, 31.9, -89.9, 32.1)

        def __enter__(self) -> "FakeDataset":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, indexes: list[int]) -> np.ndarray:
            return np.ones((len(indexes), 2, 2), dtype=np.uint8)

    fake_rasterio = types.SimpleNamespace(open=lambda path: FakeDataset())
    monkeypatch.setitem(sys.modules, "rasterio", fake_rasterio)
    project_area = {
        "project_local_basemaps": discover_project_local_naip_basemaps(project_dir),
        "renderable_basemap_paths": [str(sidecar_path)],
        "selected_basemap_paths": [],
    }

    result = load_basemap(project_area, "EPSG:4326")

    assert result["source_ref"] == USDA_NAIP_SOURCE_ID
    assert result["shown_layer"]["source_id"] == USDA_NAIP_SOURCE_ID
    assert result["shown_layer"]["path"] == str(sidecar_path)


def test_source_status_reports_project_local_naip_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, monkeypatch)
    write_existing_sidecar(project_dir)
    build_project_area(project_dir)

    result = resolve_source_status_set(project_dir)

    imagery = next(status for status in result["statuses"] if status["category"] == "imagery_basemaps")
    detail = next(item for item in imagery["source_details"] if item["source_id"] == USDA_NAIP_SOURCE_ID)
    assert detail["status"] == "registered_local"
    assert imagery["status"] == "provided_locally"


def test_populate_default_does_not_materialize_naip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, monkeypatch)

    def fail_materialize(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("Default populate-for-review must not materialize NAIP basemaps.")

    monkeypatch.setattr(populate_module, "materialize_project_naip_basemap", fail_materialize)

    result = populate_for_review(project_dir, gpt_drafting=False)

    assert result["status"] == "completed"
    assert result["artifact_paths"]["naip_basemap_materialization"] is None


def test_populate_optional_naip_success_refreshes_project_area(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, monkeypatch)

    def fake_materialize(project_dir_arg: Path) -> dict[str, Any]:
        sidecar_path, metadata_path = write_existing_sidecar(project_dir_arg)
        return {
            "project_id": "test_project",
            "project_name": "Test Project",
            "status": "reused",
            "success": True,
            "source_id": USDA_NAIP_SOURCE_ID,
            "sidecar_path": str(sidecar_path),
            "metadata_path": str(metadata_path),
            "output_path": str(project_dir_arg / "basemaps" / "naip" / "naip_basemap_materialization.json"),
            "validation_issues": [],
        }

    monkeypatch.setattr(populate_module, "materialize_project_naip_basemap", fake_materialize)

    result = populate_for_review(project_dir, materialize_naip_basemap=True, gpt_drafting=False)

    assert result["status"] == "completed"
    assert result["naip_basemap_materialization_status"] == "reused"
    assert result["artifact_paths"]["naip_basemap_sidecar"].endswith("naip_project_basemap.tif")
    assert result["basemap_rendering_status"] == "renderable_sidecar_available"
    assert any(step["name"] == "naip_basemap_materialization" and step["status"] == "completed" for step in result["steps"])


def test_populate_optional_naip_failure_is_nonblocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path, monkeypatch)

    def fake_materialize(project_dir_arg: Path) -> dict[str, Any]:
        return {
            "project_id": "test_project",
            "project_name": "Test Project",
            "status": "failed",
            "success": False,
            "source_id": USDA_NAIP_SOURCE_ID,
            "sidecar_path": None,
            "metadata_path": None,
            "output_path": str(project_dir_arg / "basemaps" / "naip" / "naip_basemap_materialization.json"),
            "message": "mock NAIP failure",
            "validation_issues": [
                {
                    "severity": "warning",
                    "code": "naip_basemap_materialization_failed",
                    "message": "mock NAIP failure",
                    "source_id": USDA_NAIP_SOURCE_ID,
                }
            ],
        }

    monkeypatch.setattr(populate_module, "materialize_project_naip_basemap", fake_materialize)

    result = populate_for_review(project_dir, materialize_naip_basemap=True, gpt_drafting=False)

    assert result["status"] == "completed"
    assert result["naip_basemap_materialization_status"] == "failed"
    assert any(warning["code"] == "naip_basemap_materialization_failed" for warning in result["warnings"])
    assert any(step["name"] == "naip_basemap_materialization" and step["status"] == "warning" for step in result["steps"])
