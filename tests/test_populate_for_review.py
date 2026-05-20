from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from review_assist.cli import main
from review_assist.populate_for_review import PopulateForReviewError, populate_for_review
from review_assist.review_queue import load_review_queue
from review_assist.spatial_analysis import SpatialAnalysisError, analyze_project


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


def write_registry(project_dir: Path, source_id: str, source_path: str | None, *, enabled: bool = True) -> None:
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": source_id,
                        "enabled": enabled,
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


def item_by_type(queue: dict[str, object], item_type: str) -> list[dict[str, object]]:
    return [item for item in queue["items"] if item["type"] == item_type]  # type: ignore[index]


def test_populate_for_review_writes_manifest_and_review_queue(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = populate_for_review(project_dir)

    assert result["status"] == "completed"
    assert result["project_id"] == "test_project"
    assert (project_dir / "populate_for_review" / "populate_for_review_run.json").exists()
    assert (project_dir / "review_queue" / "review_queue.json").exists()
    assert result["artifact_paths"]["input_package"].endswith("input_package.json")
    assert result["artifact_paths"]["project_context"].endswith("project_context.json")
    assert result["artifact_paths"]["project_geometry"].endswith("project_geometry.json")
    assert result["artifact_paths"]["project_area"].endswith("project_area.json")
    assert result["artifact_paths"]["comparison_units"].endswith("comparison_units.geojson")
    assert result["artifact_paths"]["comparison_units_metadata"].endswith("comparison_units.json")
    assert result["artifact_paths"]["source_status"].endswith("source_status_set.json")
    assert result["artifact_paths"]["constraint_results"].endswith("constraint_results.json")
    assert result["artifact_paths"]["draft_findings"].endswith("draft_findings.json")
    assert result["artifact_paths"]["deliverable_tables"].endswith("tables.json")
    assert result["artifact_paths"]["deliverable_figures"].endswith("figures.json")
    assert result["artifact_paths"]["deliverable_items"].endswith("deliverable_items.json")
    assert result["artifact_paths"]["review_queue"].endswith("review_queue.json")
    assert "project_county_names" in result
    assert "basemap_rendering_status" in result
    assert result["comparison_unit_count"] == 1
    assert result["deliverable_table_count"] == 4
    assert result["deliverable_figure_count"] == 15
    assert result["deliverable_item_count"] > 0
    assert result["expected_count_status"] == "not_configured"
    assert result["review_queue_item_count"] > 0


def test_populate_for_review_tolerates_missing_local_source_and_creates_review_item(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", "missing.geojson")

    with pytest.raises(SpatialAnalysisError, match="Missing local source file"):
        analyze_project(project_dir)

    result = populate_for_review(project_dir)

    assert result["status"] == "completed"
    assert any(warning["code"] == "missing_local_source_file" for warning in result["warnings"])
    queue = load_review_queue(project_dir)
    assert any(issue["code"] == "missing_local_source_file" for issue in queue["validation_issues"])


def test_populate_for_review_tolerates_unreadable_local_source_and_creates_review_item(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    (project_dir / "bad_source.geojson").write_text("not geojson", encoding="utf-8")
    write_registry(project_dir, "usfws_nwi_wetlands", "bad_source.geojson")

    with pytest.raises(SpatialAnalysisError, match="Unable to read source layer"):
        analyze_project(project_dir)

    result = populate_for_review(project_dir)

    assert result["status"] == "completed"
    assert any(warning["code"] == "unreadable_local_source_file" for warning in result["warnings"])
    queue = load_review_queue(project_dir)
    assert any(issue["code"] == "unreadable_local_source_file" for issue in queue["validation_issues"])


def test_populate_for_review_errors_for_missing_manifest(tmp_path: Path) -> None:
    project_dir = tmp_path / "not_a_project"

    with pytest.raises(PopulateForReviewError, match="Missing project manifest"):
        populate_for_review(project_dir)


def test_cli_populate_for_review_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["populate-for-review", str(project_dir)]) == 0

    captured = capsys.readouterr()
    assert "Populated for review" in captured.out
    assert "Review queue items" in captured.out


def test_cli_populate_for_review_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["populate-for-review", str(project_dir), "--json"]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"


def test_cli_populate_for_review_returns_nonzero_for_critical_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["populate-for-review", str(tmp_path / "not_a_project")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Missing project manifest" in captured.err
