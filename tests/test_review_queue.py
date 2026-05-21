from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from review_assist.cli import main
from review_assist.constraints import analyze_constraints
from review_assist.deliverable_items import load_deliverable_items
from review_assist.review_queue import (
    REQUIRED_ITEM_FIELDS,
    ReviewQueueError,
    generate_review_queue,
    load_review_queue,
    update_review_item,
)
from review_assist.review_queue_reset import reset_review_queue
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


def test_generate_review_queue_writes_bounded_deliverable_item_queue(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    queue = generate_review_queue(project_dir)
    deliverable_items = load_deliverable_items(project_dir)

    assert (project_dir / "review_queue" / "review_queue.json").exists()
    assert queue["project_id"] == "test_project"
    assert queue["queue_mode"] == "deliverable_items"
    assert queue["item_count"] == len(queue["items"])
    assert queue["item_count"] == deliverable_items["item_count"]
    assert all(REQUIRED_ITEM_FIELDS.issubset(item) for item in queue["items"])

    wetlands = item_by_id(queue, "wetlands-and-waterbodies")
    assert wetlands["type"] == "section_text"
    assert wetlands["deliverable_item_id"] == "wetlands-and-waterbodies"
    assert wetlands["target_id"] == "wetlands-and-waterbodies"
    assert wetlands["related_table_ids"] == ["table-wetlands-waterbodies"]
    assert wetlands["related_figure_ids"] == ["figure-wetlands-waterbodies"]
    assert wetlands["evidence_refs"] == ["section_evidence:wetlands-and-waterbodies"]
    assert wetlands["status"] == "needs_review"
    assert wetlands["query_extent_type"] == "project_area_analysis_bounds"
    assert wetlands["analysis_extent_type"] in {"direct_intersection_extent", "mixed_extent_types"}
    contamination = item_by_id(queue, "contamination-risks")
    oil_wells = item_by_id(queue, "oil-wells")
    demographics = item_by_id(queue, "demographic-characteristics")
    assert contamination["related_figure_ids"] == ["figure-hazardous-waste-sites", "figure-water-discharge-waste-facilities"]
    assert contamination["analysis_extent_type"] == "nearby_context_extent"
    assert "project vicinity" in contamination["interpretation_scope_label"]
    assert oil_wells["related_figure_ids"] == ["figure-oil-gas-wells"]
    assert oil_wells["analysis_extent_type"] == "direct_intersection_extent"
    assert demographics["analysis_extent_type"] == "county_or_regional_context_extent"
    assert "county or regional context" in demographics["interpretation_scope_label"]
    assert not items_by_type(queue, "draft_finding")
    assert not items_by_type(queue, "comparison_table")
    assert not items_by_type(queue, "spatial_relationship")
    assert not items_by_type(queue, "no_mapped_relationships")
    assert not items_by_type(queue, "source_inventory_note")


def test_legacy_review_queue_mode_still_writes_source_and_validation_items(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("review_assist.source_status.maybe_load_seed_source_manifest", lambda source_id: None)
    project_dir = write_project(tmp_path)

    queue = generate_review_queue(project_dir, include_legacy_artifacts=True)

    assert queue["queue_mode"] == "legacy_audit"
    wetlands = item_by_id(queue, "missing-data-wetlands-waterbodies")
    assert wetlands["type"] == "missing_data_placeholder"
    assert wetlands["status"] == "needs_review"
    assert wetlands["provenance"]["artifact"] == "source_status_set"  # type: ignore[index]
    assert "source_not_downloaded" in wetlands["uncertainty_flags"]  # type: ignore[operator]

    validation_items = items_by_type(queue, "validation_issue")
    assert validation_items
    assert validation_items[0]["status"] == "needs_review"


def test_generate_review_queue_creates_spatial_relationship_item(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_point_layer(project_dir / "wetlands.geojson", Point(-89.995, 32.0))
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    analyze_project(project_dir)

    queue = generate_review_queue(project_dir, include_legacy_artifacts=True)

    spatial_items = items_by_type(queue, "spatial_relationship")
    assert len(spatial_items) == 1
    item = spatial_items[0]
    assert item["status"] == "draft"
    assert item["source_refs"] == ["usfws_nwi_wetlands"]
    assert item["provenance"]["method"] == "geopandas_shapely_local_spatial_check"  # type: ignore[index]


def test_generate_review_queue_omits_direct_spatial_items_when_constraints_exist(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_point_layer(project_dir / "wetlands.geojson", Point(-89.995, 32.0))
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    analyze_project(project_dir)
    analyze_constraints(project_dir)

    queue = generate_review_queue(project_dir, include_legacy_artifacts=True)

    assert not items_by_type(queue, "spatial_relationship")


def test_generate_review_queue_creates_no_mapped_relationship_item(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_point_layer(project_dir / "far.geojson", Point(-89.0, 33.0))
    write_registry(project_dir, "epa_envirofacts_echo", "far.geojson")
    analyze_project(project_dir)

    queue = generate_review_queue(project_dir, include_legacy_artifacts=True)

    item = item_by_id(queue, "no-mapped-relationships-epa-envirofacts-echo")
    assert item["type"] == "no_mapped_relationships"
    assert item["status"] == "draft"
    assert item["source_refs"] == ["epa_envirofacts_echo"]


def test_update_review_item_validates_status_and_missing_items(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    with pytest.raises(ReviewQueueError, match="Missing review queue"):
        update_review_item(project_dir, "wetlands-and-waterbodies", status="accepted")

    generate_review_queue(project_dir)

    with pytest.raises(ReviewQueueError, match="Unsupported review status"):
        update_review_item(project_dir, "wetlands-and-waterbodies", status="done")

    with pytest.raises(ReviewQueueError, match="Review item not found"):
        update_review_item(project_dir, "missing-item", status="accepted")


def test_update_review_item_appends_notes_and_enforces_export_rules(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_review_queue(project_dir)
    item_id = "wetlands-and-waterbodies"

    item = update_review_item(project_dir, item_id, status="accepted", note="Looks usable.")
    assert item["export_eligible"] is True
    assert len(item["reviewer_notes"]) == 1

    item = update_review_item(project_dir, item_id, status="accepted", note="Second note.")
    assert len(item["reviewer_notes"]) == 2

    with pytest.raises(ReviewQueueError, match="Only these statuses"):
        update_review_item(project_dir, item_id, status="declined", export_eligible=True)

    item = update_review_item(project_dir, item_id, status="rejected")
    assert item["status"] == "declined"
    assert item["export_eligible"] is False

    item = update_review_item(project_dir, item_id, status="unable_to_verify", export_eligible=True)
    assert item["export_eligible"] is True

    item = update_review_item(project_dir, item_id, status="edited", edited_content="Reviewer edited wetlands text.")
    assert item["edited_content"] == "Reviewer edited wetlands text."

    item = update_review_item(project_dir, item_id, status="replaced")
    assert item["export_eligible"] is False
    assert any(issue["code"] == "replacement_content_missing" for issue in item["validation_issues"])

    item = update_review_item(project_dir, item_id, status="replaced", replacement_content="Reviewer replacement text.")
    assert item["replacement_content"] == "Reviewer replacement text."
    assert item["export_eligible"] is True
    assert not any(issue["code"] == "replacement_content_missing" for issue in item["validation_issues"])


def test_generate_review_queue_preserves_existing_review_state(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_review_queue(project_dir)
    update_review_item(project_dir, "wetlands-and-waterbodies", status="accepted", note="Reviewed.")

    regenerated = generate_review_queue(project_dir)

    item = item_by_id(regenerated, "wetlands-and-waterbodies")
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
                "wetlands-and-waterbodies",
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
    item = item_by_id(queue, "wetlands-and-waterbodies")
    assert item["status"] == "accepted"

    assert main(["generate-review-queue", str(project_dir), "--include-legacy-artifacts"]) == 0
    legacy = load_review_queue(project_dir)
    assert legacy["queue_mode"] == "legacy_audit"


def test_cli_review_queue_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["generate-review-queue", str(project_dir), "--json"]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"


def test_reset_review_queue_deletes_generated_candidates_and_regenerates(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_point_layer(project_dir / "wetlands.geojson", Point(-89.995, 32.0))
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    generate_review_queue(project_dir)
    source_registry = project_dir / "config" / "sources.json"
    layer_artifact = project_dir / "layers" / "usfws_nwi_wetlands" / "usfws_nwi_wetlands.geojson"
    layer_artifact.parent.mkdir(parents=True)
    layer_artifact.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")
    tables_path = project_dir / "deliverable" / "tables.json"
    figures_path = project_dir / "deliverable" / "figures.json"
    evidence_path = project_dir / "evidence" / "evidence_package.json"
    export_manifest_path = project_dir / "exports" / "export_manifest.json"
    export_markdown_path = project_dir / "exports" / "environmental_constraints_report.md"
    export_manifest_path.parent.mkdir(parents=True)
    export_manifest_path.write_text('{"status":"stale"}\n', encoding="utf-8")
    export_markdown_path.write_text("stale export\n", encoding="utf-8")
    tables_path.write_text('{"table_count": 0, "stale": true}\n', encoding="utf-8")
    figures_path.write_text('{"figure_count": 0, "stale": true}\n', encoding="utf-8")
    evidence_path.write_text('{"item_count": 0, "stale": true}\n', encoding="utf-8")
    deliverable_items_path = project_dir / "deliverable" / "deliverable_items.json"
    queue_path = project_dir / "review_queue" / "review_queue.json"
    deliverable_items_path.write_text(
        deliverable_items_path.read_text(encoding="utf-8").replace(
            "Wetlands and Waterbodies",
            "Draft review candidate Wetlands and Waterbodies",
            1,
        ),
        encoding="utf-8",
    )
    queue_path.write_text(
        queue_path.read_text(encoding="utf-8").replace(
            "Wetlands and Waterbodies",
            "Reviewer focus Wetlands and Waterbodies",
            1,
        ),
        encoding="utf-8",
    )

    result = reset_review_queue(project_dir, regenerate=True)
    queue = load_review_queue(project_dir)
    deliverable_items = load_deliverable_items(project_dir)
    wetlands_queue = item_by_id(queue, "wetlands-and-waterbodies")
    wetlands_item = next(item for item in deliverable_items["items"] if item["deliverable_item_id"] == "wetlands-and-waterbodies")

    assert {record["relative_path"] for record in result["deleted"]} == {
        "deliverable/deliverable_items.json",
        "review_queue/review_queue.json",
    }
    assert result["before"]["deliverable_item_count"] == result["after"]["deliverable_item_count"]
    assert result["before"]["review_queue_item_count"] == result["after"]["review_queue_item_count"]
    assert result["after"]["deliverable_figure_count"] == 15
    assert result["process_language"]["before"]["has_process_language"] is True
    assert result["process_language"]["after"]["has_process_language"] is False
    assert result["refresh_upstream_artifacts"] is True
    regenerated = [record["artifact"] for record in result["regenerated"]]
    assert "comparison_unit_constraints" in regenerated
    assert "deliverable_tables" in regenerated
    assert "deliverable_figures" in regenerated
    assert "map_manifest" in regenerated
    assert "evidence_package" in regenerated
    assert "report_sections" in regenerated
    assert wetlands_queue["generated_content"] == wetlands_item["generated_content"]
    assert "stale" not in json.loads(tables_path.read_text(encoding="utf-8"))
    assert "stale" not in json.loads(figures_path.read_text(encoding="utf-8"))
    assert "stale" not in json.loads(evidence_path.read_text(encoding="utf-8"))
    assert source_registry.exists()
    assert layer_artifact.exists()
    assert tables_path.exists()
    assert figures_path.exists()
    assert evidence_path.exists()
    assert export_manifest_path.exists()
    assert export_markdown_path.exists()


def test_reset_review_queue_dry_run_does_not_delete_artifacts(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_review_queue(project_dir)
    deliverable_items_path = project_dir / "deliverable" / "deliverable_items.json"
    queue_path = project_dir / "review_queue" / "review_queue.json"
    before_items = deliverable_items_path.read_text(encoding="utf-8")
    before_queue = queue_path.read_text(encoding="utf-8")

    result = reset_review_queue(project_dir, dry_run=True)

    assert result["dry_run"] is True
    assert {record["relative_path"] for record in result["would_delete"]} == {
        "deliverable/deliverable_items.json",
        "review_queue/review_queue.json",
    }
    assert result["deleted"] == []
    assert "deliverable/tables.json" in result["would_refresh"]
    assert "deliverable/figures.json" in result["would_refresh"]
    assert "evidence/evidence_package.json" in result["would_refresh"]
    assert deliverable_items_path.read_text(encoding="utf-8") == before_items
    assert queue_path.read_text(encoding="utf-8") == before_queue


def test_reset_review_queue_refreshes_evidence_even_without_legacy_flag(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_review_queue(project_dir)
    evidence_path = project_dir / "evidence" / "evidence_package.json"
    evidence_path.write_text('{"item_count": 0, "stale": true}\n', encoding="utf-8")

    result = reset_review_queue(project_dir)
    regenerated = [record["artifact"] for record in result["regenerated"]]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert "evidence_package" in regenerated
    assert regenerated[-2:] == ["deliverable_items", "review_queue"]
    assert "stale" not in evidence
    assert evidence.get("project_id") == "test_project"


def test_reset_review_queue_include_exports_deletes_generated_export_outputs(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_review_queue(project_dir)
    exports_dir = project_dir / "exports"
    figure_assets_dir = exports_dir / "assets" / "figures"
    figure_assets_dir.mkdir(parents=True)
    export_manifest_path = exports_dir / "export_manifest.json"
    package_manifest_path = exports_dir / "deliverable_package_manifest.json"
    export_markdown_path = exports_dir / "environmental_constraints_report.md"
    export_docx_path = exports_dir / "environmental_constraints_report.docx"
    export_manifest_path.write_text('{"status":"stale"}\n', encoding="utf-8")
    package_manifest_path.write_text('{"status":"stale"}\n', encoding="utf-8")
    export_markdown_path.write_text("stale export\n", encoding="utf-8")
    export_docx_path.write_bytes(b"stale docx")
    (figure_assets_dir / "stale.png").write_bytes(b"stale figure")

    result = reset_review_queue(project_dir, include_exports=True)
    deleted = {record["relative_path"] for record in result["deleted"]}

    assert "exports/export_manifest.json" in deleted
    assert "exports/deliverable_package_manifest.json" in deleted
    assert "exports/environmental_constraints_report.md" in deleted
    assert "exports/environmental_constraints_report.docx" in deleted
    assert "exports/assets/figures" in deleted
    assert not export_manifest_path.exists()
    assert not package_manifest_path.exists()
    assert not export_markdown_path.exists()
    assert not export_docx_path.exists()
    assert not figure_assets_dir.exists()
    assert load_review_queue(project_dir)["item_count"] == result["after"]["review_queue_item_count"]


def test_cli_reset_review_queue_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)
    generate_review_queue(project_dir)

    assert main(["reset-review-queue", str(project_dir), "--yes", "--json"]) == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["after"]["review_queue_item_count"] == load_review_queue(project_dir)["item_count"]
    assert result["after"]["deliverable_figure_count"] == 15
    assert result["process_language"]["after"]["has_process_language"] is False
