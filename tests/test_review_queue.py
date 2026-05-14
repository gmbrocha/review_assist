from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from review_assist.cli import main
from review_assist.review_queue import (
    REQUIRED_ITEM_FIELDS,
    ReviewQueueError,
    generate_review_queue,
    load_review_queue,
    update_review_item,
)
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
        <Placemark><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
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


def write_point_layer(path: Path, point: Point) -> Path:
    gdf = gpd.GeoDataFrame([{"name": "Source Feature"}], geometry=[point], crs="EPSG:4326")
    path.write_text(gdf.to_json(drop_id=True), encoding="utf-8")
    return path


def item_by_id(queue: dict[str, object], item_id: str) -> dict[str, object]:
    return next(item for item in queue["items"] if item["id"] == item_id)  # type: ignore[index]


def items_by_type(queue: dict[str, object], item_type: str) -> list[dict[str, object]]:
    return [item for item in queue["items"] if item["type"] == item_type]  # type: ignore[index]


def test_generate_review_queue_writes_artifact_and_source_items(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    queue = generate_review_queue(project_dir)

    assert (project_dir / "review_queue" / "review_queue.json").exists()
    assert queue["project_id"] == "test_project"
    assert queue["item_count"] == len(queue["items"])
    assert all(REQUIRED_ITEM_FIELDS.issubset(item) for item in queue["items"])

    wetlands = item_by_id(queue, "source-status-wetlands-waterbodies")
    assert wetlands["type"] == "source_status_note"
    assert wetlands["status"] == "needs_review"
    assert wetlands["provenance"]["artifact"] == "source_status_set"  # type: ignore[index]
    assert "source_not_downloaded" in wetlands["uncertainty_flags"]  # type: ignore[operator]

    cultural_placeholder = item_by_id(queue, "missing-data-cultural-historic")
    assert cultural_placeholder["type"] == "missing_data_placeholder"
    assert cultural_placeholder["status"] == "needs_verification"
    assert "mdah_restricted_archaeology" in cultural_placeholder["source_refs"]  # type: ignore[operator]

    validation_items = items_by_type(queue, "validation_issue")
    assert validation_items
    assert validation_items[0]["status"] == "needs_review"


def test_generate_review_queue_creates_spatial_relationship_item(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_point_layer(project_dir / "wetlands.geojson", Point(-89.995, 32.0))
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    analyze_project(project_dir)

    queue = generate_review_queue(project_dir)

    spatial_items = items_by_type(queue, "spatial_relationship")
    assert len(spatial_items) == 1
    item = spatial_items[0]
    assert item["status"] == "draft"
    assert item["source_refs"] == ["usfws_nwi_wetlands"]
    assert item["provenance"]["method"] == "geopandas_shapely_local_spatial_check"  # type: ignore[index]


def test_generate_review_queue_creates_no_mapped_relationship_item(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_point_layer(project_dir / "far.geojson", Point(-89.0, 33.0))
    write_registry(project_dir, "epa_envirofacts_echo", "far.geojson")
    analyze_project(project_dir)

    queue = generate_review_queue(project_dir)

    item = item_by_id(queue, "no-mapped-relationships-epa-envirofacts-echo")
    assert item["type"] == "no_mapped_relationships"
    assert item["status"] == "draft"
    assert item["source_refs"] == ["epa_envirofacts_echo"]


def test_update_review_item_validates_status_and_missing_items(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    with pytest.raises(ReviewQueueError, match="Missing review queue"):
        update_review_item(project_dir, "source-status-wetlands-waterbodies", status="accepted")

    generate_review_queue(project_dir)

    with pytest.raises(ReviewQueueError, match="Unsupported review status"):
        update_review_item(project_dir, "source-status-wetlands-waterbodies", status="done")

    with pytest.raises(ReviewQueueError, match="Review item not found"):
        update_review_item(project_dir, "missing-item", status="accepted")


def test_update_review_item_appends_notes_and_enforces_export_rules(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_review_queue(project_dir)
    item_id = "source-status-wetlands-waterbodies"

    item = update_review_item(project_dir, item_id, status="accepted", note="Looks usable.")
    assert item["export_eligible"] is True
    assert len(item["reviewer_notes"]) == 1

    item = update_review_item(project_dir, item_id, status="accepted", note="Second note.")
    assert len(item["reviewer_notes"]) == 2

    with pytest.raises(ReviewQueueError, match="Only these statuses"):
        update_review_item(project_dir, item_id, status="rejected", export_eligible=True)

    item = update_review_item(project_dir, item_id, status="rejected")
    assert item["export_eligible"] is False

    item = update_review_item(project_dir, item_id, status="unable_to_verify", export_eligible=True)
    assert item["export_eligible"] is True


def test_generate_review_queue_preserves_existing_review_state(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_review_queue(project_dir)
    update_review_item(project_dir, "source-status-wetlands-waterbodies", status="accepted", note="Reviewed.")

    regenerated = generate_review_queue(project_dir)

    item = item_by_id(regenerated, "source-status-wetlands-waterbodies")
    assert item["status"] == "accepted"
    assert item["export_eligible"] is True
    assert len(item["reviewer_notes"]) == 1


def test_cli_review_queue_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["generate-review-queue", str(project_dir)]) == 0
    assert main(["list-review-queue", str(project_dir)]) == 0
    assert (
        main(
            [
                "update-review-item",
                str(project_dir),
                "source-status-wetlands-waterbodies",
                "--status",
                "accepted",
                "--note",
                "CLI reviewed.",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert "Generated review queue" in captured.out
    assert "Review queue" in captured.out
    assert "Updated review item" in captured.out

    queue = load_review_queue(project_dir)
    item = item_by_id(queue, "source-status-wetlands-waterbodies")
    assert item["status"] == "accepted"


def test_cli_review_queue_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["generate-review-queue", str(project_dir), "--json"]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"
