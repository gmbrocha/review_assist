from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from review_assist.cli import main
from review_assist.populate_for_review import populate_for_review
from review_assist.review_queue import ReviewQueueError, generate_review_queue, update_review_item
from review_assist.source_catalog import SourceCatalogError, load_project_source_registry
from review_assist.source_inventory import SourceInventoryError, generate_source_inventory
from review_assist.spatial_analysis import analyze_project
from review_assist.tables import TableGenerationError, generate_comparison_tables, load_comparison_tables


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


def write_registry(
    project_dir: Path,
    source_id: str,
    source_path: str | None,
    *,
    enabled: bool = True,
    metadata: dict[str, str] | object | None = None,
) -> None:
    source: dict[str, object] = {
        "source_id": source_id,
        "enabled": enabled,
        "access_method": "local_file",
        "path": source_path,
        "role": "context",
        "buffer_feet": None,
        "notes": "",
        "status": "test",
    }
    if metadata is not None:
        source["metadata"] = metadata
    (project_dir / "config" / "sources.json").write_text(
        json.dumps({"project_id": "test_project", "sources": [source]}, indent=2) + "\n",
        encoding="utf-8",
    )


def write_layer(path: Path, geometries: list[object], rows: list[dict[str, object]]) -> Path:
    gdf = gpd.GeoDataFrame(rows, geometry=geometries, crs="EPSG:4326")
    path.write_text(gdf.to_json(drop_id=True), encoding="utf-8")
    return path


def record_by_id(inventory: dict[str, object], source_id: str) -> dict[str, object]:
    return next(record for record in inventory["records"] if record["source_id"] == source_id)  # type: ignore[index]


def table_by_id(tables: dict[str, object], table_id: str) -> dict[str, object]:
    return next(table for table in tables["tables"] if table["table_id"] == table_id)  # type: ignore[index]


def item_by_id(queue: dict[str, object], item_id: str) -> dict[str, object]:
    return next(item for item in queue["items"] if item["id"] == item_id)  # type: ignore[index]


def test_source_inventory_records_catalog_statuses_for_unavailable_sources(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    inventory = generate_source_inventory(project_dir)

    assert (project_dir / "source_inventory" / "source_inventory.json").exists()
    wetlands = record_by_id(inventory, "usfws_nwi_wetlands")
    mdah = record_by_id(inventory, "mdah_restricted_archaeology")
    utilities = record_by_id(inventory, "local_utility_infrastructure")
    assert wetlands["source_status"]["category_status"] == "downloadable"  # type: ignore[index]
    assert mdah["source_status"]["category_status"] == "gated"  # type: ignore[index]
    assert utilities["source_status"]["category_status"] == "stubbed"  # type: ignore[index]
    assert "source_not_downloaded" in wetlands["uncertainty_flags"]  # type: ignore[operator]


def test_source_inventory_records_local_geojson_metadata(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "wetlands.geojson", [Point(-89.995, 32.0)], [{"name": "Wetland A"}])
    write_registry(
        project_dir,
        "usfws_nwi_wetlands",
        "wetlands.geojson",
        metadata={"citation": "Synthetic NWI export", "access_date": "2026-05-14"},
    )

    inventory = generate_source_inventory(project_dir)

    record = record_by_id(inventory, "usfws_nwi_wetlands")
    local_metadata = record["local_metadata"]  # type: ignore[index]
    assert local_metadata["readable"] is True
    assert local_metadata["crs"] == "EPSG:4326"
    assert local_metadata["feature_count"] == 1
    assert local_metadata["geometry_type_counts"] == {"Point": 1}
    assert local_metadata["bounds_wgs84"]["west"] == pytest.approx(-89.995)  # type: ignore[index]
    assert record["metadata"]["citation"] == "Synthetic NWI export"  # type: ignore[index]


def test_source_inventory_records_missing_and_unreadable_local_sources(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", "missing.geojson")

    missing_inventory = generate_source_inventory(project_dir)

    missing_record = record_by_id(missing_inventory, "usfws_nwi_wetlands")
    assert any(issue["code"] == "missing_local_source_file" for issue in missing_record["validation_issues"])  # type: ignore[index]

    (project_dir / "bad.geojson").write_text("not geojson", encoding="utf-8")
    write_registry(project_dir, "usfws_nwi_wetlands", "bad.geojson")
    unreadable_inventory = generate_source_inventory(project_dir)

    unreadable_record = record_by_id(unreadable_inventory, "usfws_nwi_wetlands")
    assert any(issue["code"] == "unreadable_local_source_file" for issue in unreadable_record["validation_issues"])  # type: ignore[index]


def test_project_source_registry_rejects_invalid_metadata(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", None, metadata="not an object")

    with pytest.raises(SourceCatalogError, match="metadata must be an object"):
        load_project_source_registry(project_dir)
    with pytest.raises(SourceInventoryError, match="metadata must be an object"):
        generate_source_inventory(project_dir)


def test_generate_comparison_tables_writes_status_and_empty_spatial_tables(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = generate_comparison_tables(project_dir)

    assert (project_dir / "tables" / "comparison_tables.json").exists()
    source_table = table_by_id(result, "source-status-matrix")
    spatial_table = table_by_id(result, "spatial-relationship-summary")
    finding_table = table_by_id(result, "draft-finding-summary")
    assert source_table["row_count"] > 0
    assert spatial_table["row_count"] == 0
    assert "no_spatial_relationship_artifact" in spatial_table["uncertainty_flags"]  # type: ignore[operator]
    assert finding_table["row_count"] > 0


def test_generate_comparison_tables_summarizes_spatial_relationships_and_findings(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    analyze_project(project_dir)

    result = generate_comparison_tables(project_dir)

    spatial_table = table_by_id(result, "spatial-relationship-summary")
    finding_table = table_by_id(result, "draft-finding-summary")
    assert spatial_table["row_count"] >= 1
    assert spatial_table["rows"][0]["source_category"] == "wetlands_waterbodies"  # type: ignore[index]
    assert spatial_table["rows"][0]["measurements"]  # type: ignore[index]
    assert any(row["resource_category"] == "wetlands_waterbodies" for row in finding_table["rows"])  # type: ignore[index]


def test_comparison_table_ids_are_deterministic(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    first = generate_comparison_tables(project_dir)
    second = generate_comparison_tables(project_dir)

    assert [table["table_id"] for table in first["tables"]] == [table["table_id"] for table in second["tables"]]


def test_load_comparison_tables_rejects_malformed_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    tables_path = project_dir / "tables" / "comparison_tables.json"
    tables_path.parent.mkdir(parents=True)
    tables_path.write_text('{"tables": [{"table_id": "broken"}]}', encoding="utf-8")

    with pytest.raises(TableGenerationError, match="missing required fields"):
        load_comparison_tables(project_dir)
    with pytest.raises(ReviewQueueError, match="missing required fields"):
        generate_review_queue(project_dir)


def test_review_queue_includes_inventory_and_table_items_and_preserves_state(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_source_inventory(project_dir)
    generate_comparison_tables(project_dir)

    queue = generate_review_queue(project_dir)

    assert item_by_id(queue, "source-inventory-usfws-nwi-wetlands")["type"] == "source_inventory_note"
    assert item_by_id(queue, "comparison-table-source-status-matrix")["type"] == "comparison_table"

    update_review_item(project_dir, "source-inventory-usfws-nwi-wetlands", status="accepted", note="Source note reviewed.")
    update_review_item(project_dir, "comparison-table-source-status-matrix", status="accepted", note="Table reviewed.")
    generate_source_inventory(project_dir)
    generate_comparison_tables(project_dir)
    regenerated = generate_review_queue(project_dir)

    source_item = item_by_id(regenerated, "source-inventory-usfws-nwi-wetlands")
    table_item = item_by_id(regenerated, "comparison-table-source-status-matrix")
    assert source_item["status"] == "accepted"
    assert table_item["status"] == "accepted"
    assert len(source_item["reviewer_notes"]) == 1
    assert table_item["row_count"] > 0
    assert table_item["rows_preview"]


def test_cli_source_inventory_and_tables_text_and_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["generate-source-inventory", str(project_dir)]) == 0
    captured = capsys.readouterr()
    assert "Generated source inventory" in captured.out

    assert main(["generate-source-inventory", str(project_dir), "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"

    assert main(["generate-tables", str(project_dir)]) == 0
    captured = capsys.readouterr()
    assert "Generated comparison tables" in captured.out

    assert main(["generate-tables", str(project_dir), "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"


def test_populate_for_review_manifest_includes_inventory_and_tables(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = populate_for_review(project_dir)

    assert result["artifact_paths"]["source_inventory"].endswith("source_inventory.json")
    assert result["artifact_paths"]["comparison_tables"].endswith("comparison_tables.json")
