from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from review_assist.cli import main
import review_assist.maps as maps_module
from review_assist.maps import MapGenerationError, generate_maps, load_map_manifest
from review_assist.populate_for_review import populate_for_review
from review_assist.review_queue import ReviewQueueError, generate_review_queue, update_review_item
from review_assist.spatial_analysis import analyze_project


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


def write_registry(project_dir: Path, source_id: str, source_path: str) -> None:
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
                        "role": "context",
                        "buffer_feet": None,
                        "notes": "",
                        "status": "test",
                    }
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


def figure_by_id(manifest: dict[str, object], figure_id: str) -> dict[str, object]:
    return next(figure for figure in manifest["figures"] if figure["figure_id"] == figure_id)  # type: ignore[index]


def item_by_id(queue: dict[str, object], item_id: str) -> dict[str, object]:
    return next(item for item in queue["items"] if item["id"] == item_id)  # type: ignore[index]


def test_generate_maps_writes_overview_manifest_and_png(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    manifest = generate_maps(project_dir)

    assert (project_dir / "maps" / "map_manifest.json").exists()
    assert manifest["figure_count"] == 1
    figure = figure_by_id(manifest, "project-overview")
    assert Path(str(figure["image_path"])).exists()
    assert figure["review_status"] == "draft"
    assert figure["source_refs"] == []
    assert "vector_only_no_basemap" in figure["uncertainty_flags"]  # type: ignore[operator]


def test_generate_maps_creates_source_context_from_clipped_source(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    analyze_project(project_dir)

    manifest = generate_maps(project_dir)

    assert manifest["figure_count"] == 2
    figure = figure_by_id(manifest, "source-context-usfws-nwi-wetlands")
    assert Path(str(figure["image_path"])).exists()
    assert figure["source_refs"] == ["usfws_nwi_wetlands"]
    assert any(layer["layer_type"] == "source_layer" for layer in figure["shown_layers"])  # type: ignore[index]


def test_generate_maps_handles_missing_and_malformed_spatial_artifacts(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    missing_spatial = generate_maps(project_dir)
    assert [figure["figure_id"] for figure in missing_spatial["figures"]] == ["project-overview"]

    spatial_path = project_dir / "intermediate" / "spatial_relationships.json"
    spatial_path.parent.mkdir(parents=True, exist_ok=True)
    spatial_path.write_text("{not-json", encoding="utf-8")
    malformed = generate_maps(project_dir)

    assert malformed["figure_count"] == 1
    assert any(issue["code"] == "invalid_spatial_relationships_json" for issue in malformed["validation_issues"])


def test_generate_maps_fails_clearly_for_overview_render_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)

    def broken_render_map(**_: object) -> None:
        raise RuntimeError("render failed")

    monkeypatch.setattr(maps_module, "_render_map", broken_render_map)

    with pytest.raises(MapGenerationError, match="Unable to render project overview map"):
        generate_maps(project_dir)


def test_generate_maps_records_source_render_error_and_continues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    analyze_project(project_dir)
    original_render_map = maps_module._render_map

    def partially_broken_render_map(**kwargs: object) -> None:
        if kwargs.get("source_layer") is not None:
            raise RuntimeError("source render failed")
        original_render_map(**kwargs)

    monkeypatch.setattr(maps_module, "_render_map", partially_broken_render_map)

    manifest = generate_maps(project_dir)

    assert manifest["figure_count"] == 1
    assert [figure["figure_id"] for figure in manifest["figures"]] == ["project-overview"]
    assert any(issue["code"] == "source_map_render_error" for issue in manifest["validation_issues"])

    queue = generate_review_queue(project_dir)
    validation_item = item_by_id(queue, "validation-map-generation-001-source-map-render-error")
    assert validation_item["type"] == "validation_issue"
    assert validation_item["source_refs"] == ["usfws_nwi_wetlands"]


def test_map_figure_ids_are_deterministic(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    first = generate_maps(project_dir)
    second = generate_maps(project_dir)

    assert [figure["figure_id"] for figure in first["figures"]] == [figure["figure_id"] for figure in second["figures"]]


def test_load_map_manifest_rejects_invalid_artifacts(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    manifest = generate_maps(project_dir)
    manifest["figure_count"] = manifest["figure_count"] + 1
    Path(manifest["output_path"]).write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(MapGenerationError, match="figure_count does not match"):
        load_map_manifest(project_dir)

    manifest = generate_maps(project_dir)
    manifest["figures"][0]["review_status"] = "done"
    Path(manifest["output_path"]).write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(MapGenerationError, match="unsupported review_status"):
        load_map_manifest(project_dir)

    manifest = generate_maps(project_dir)
    manifest["figures"].append(dict(manifest["figures"][0]))
    manifest["figure_count"] = len(manifest["figures"])
    Path(manifest["output_path"]).write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(MapGenerationError, match="Duplicate map figure id"):
        load_map_manifest(project_dir)

    manifest = generate_maps(project_dir)
    manifest["figures"][0]["image_path"] = str(project_dir / "maps" / "figures" / "missing.png")
    Path(manifest["output_path"]).write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(MapGenerationError, match="image_path does not exist"):
        load_map_manifest(project_dir)


def test_review_queue_includes_map_items_and_preserves_state(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_maps(project_dir)
    queue = generate_review_queue(project_dir)

    item = item_by_id(queue, "map-figure-project-overview")
    assert item["type"] == "map_figure"
    assert Path(str(item["image_path"])).exists()
    assert item["export_eligible"] is False

    update_review_item(project_dir, "map-figure-project-overview", status="accepted", note="Figure reviewed.")
    generate_maps(project_dir)
    regenerated = generate_review_queue(project_dir)

    item = item_by_id(regenerated, "map-figure-project-overview")
    assert item["status"] == "accepted"
    assert item["export_eligible"] is True
    assert len(item["reviewer_notes"]) == 1


def test_review_queue_fails_for_malformed_map_manifest(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    manifest_path = project_dir / "maps" / "map_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text('{"figures": [{"figure_id": "broken"}]}', encoding="utf-8")

    with pytest.raises(ReviewQueueError, match="missing required fields"):
        generate_review_queue(project_dir)


def test_cli_generate_maps_text_and_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["generate-maps", str(project_dir)]) == 0
    captured = capsys.readouterr()
    assert "Generated maps" in captured.out

    assert main(["generate-maps", str(project_dir), "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"


def test_populate_for_review_manifest_includes_maps(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = populate_for_review(project_dir)

    assert result["artifact_paths"]["map_manifest"].endswith("map_manifest.json")
    assert any(step["name"] == "map_generation" and step["status"] == "completed" for step in result["steps"])
    queue = generate_review_queue(project_dir)
    assert item_by_id(queue, "map-figure-project-overview")["type"] == "map_figure"
