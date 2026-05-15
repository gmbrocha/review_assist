from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from review_assist import source_acquisition
from review_assist.cli import main
from review_assist.export_report import export_report
from review_assist.populate_for_review import populate_for_review
from review_assist.review_queue import load_review_queue, update_review_item


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


def fake_nwi_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if url.endswith("/0"):
        return {"maxRecordCount": 100}
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Mock NWI Wetland"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-90.001, 31.999],
                            [-89.998, 31.999],
                            [-89.998, 32.001],
                            [-90.001, 32.001],
                            [-90.001, 31.999],
                        ]
                    ],
                },
            }
        ],
    }


def set_queue_item(project_dir: Path, item_id: str, **updates: Any) -> None:
    queue = load_review_queue(project_dir)
    for item in queue["items"]:
        if item["id"] == item_id:
            item.update(updates)
            Path(queue["output_path"]).write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
            return
    raise AssertionError(f"Missing queue item: {item_id}")


def included_ids(manifest: dict[str, Any]) -> set[str]:
    return {item["id"] for item in manifest["included_items"]}


def test_export_manifest_filters_reviewed_items_and_uses_edited_content(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    update_review_item(project_dir, "report-section-front-matter", status="accepted")
    update_review_item(project_dir, "report-section-executive-summary", status="edited")
    set_queue_item(project_dir, "report-section-executive-summary", edited_content="Reviewer edited executive summary.")
    update_review_item(project_dir, "report-section-introduction", status="rejected")

    manifest = export_report(project_dir)
    markdown = Path(manifest["markdown_path"]).read_text(encoding="utf-8")

    assert "report-section-front-matter" in included_ids(manifest)
    assert "report-section-executive-summary" in included_ids(manifest)
    assert "report-section-introduction" not in included_ids(manifest)
    assert "report-section-study-area" not in included_ids(manifest)
    assert "Reviewer edited executive summary." in markdown
    assert "INTERNAL PREVIEW EXPORT" not in markdown


def test_export_includes_unable_to_verify_only_when_export_eligible(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    update_review_item(project_dir, "report-section-limitations-and-missing-data", status="unable_to_verify")
    first = export_report(project_dir)
    assert "report-section-limitations-and-missing-data" not in included_ids(first)

    update_review_item(project_dir, "report-section-limitations-and-missing-data", status="unable_to_verify", export_eligible=True)
    second = export_report(project_dir)
    assert "report-section-limitations-and-missing-data" in included_ids(second)


def test_export_warns_when_no_accepted_sections_are_available(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    manifest = export_report(project_dir)

    assert manifest["included_count"] == 0
    assert any(issue["code"] == "no_accepted_report_sections" for issue in manifest["validation_issues"])
    assert any(issue["code"] == "unresolved_required_source_gaps" for issue in manifest["validation_issues"])
    assert "No review queue items met the export criteria" in Path(manifest["markdown_path"]).read_text(encoding="utf-8")


def test_export_preview_includes_drafts_and_marks_markdown(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    manifest = export_report(project_dir, include_draft=True)
    markdown = Path(manifest["markdown_path"]).read_text(encoding="utf-8")

    assert manifest["include_draft"] is True
    assert manifest["included_count"] > 0
    assert "report-section-study-area" in included_ids(manifest)
    assert "INTERNAL PREVIEW EXPORT" in markdown


def test_export_with_nwi_backed_constraints_includes_accepted_findings_tables_and_maps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setattr(source_acquisition, "_fetch_json", fake_nwi_fetch)
    populate_for_review(project_dir, prepare_sources=True)
    queue = load_review_queue(project_dir)
    finding_id = next(item["id"] for item in queue["items"] if item["type"] == "draft_finding" and "Wetland" in item["title"])
    map_id = next(item["id"] for item in queue["items"] if item["type"] == "map_figure" and item["source_refs"])

    update_review_item(project_dir, finding_id, status="accepted")
    update_review_item(project_dir, "report-section-wetlands-and-waterbodies", status="accepted")
    update_review_item(project_dir, "comparison-table-constraint-summary", status="accepted")
    update_review_item(project_dir, map_id, status="accepted")

    manifest = export_report(project_dir)
    markdown = Path(manifest["markdown_path"]).read_text(encoding="utf-8")

    assert finding_id in included_ids(manifest)
    assert "report-section-wetlands-and-waterbodies" in included_ids(manifest)
    assert "comparison-table-constraint-summary" in included_ids(manifest)
    assert map_id in included_ids(manifest)
    assert "Mock NWI Wetland" in markdown
    assert "Map file:" in markdown


def test_export_preserves_reviewer_edit_after_regeneration(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    update_review_item(project_dir, "report-section-front-matter", status="edited")
    set_queue_item(project_dir, "report-section-front-matter", edited_content="Reviewer edited front matter.")
    populate_for_review(project_dir)

    manifest = export_report(project_dir)
    markdown = Path(manifest["markdown_path"]).read_text(encoding="utf-8")

    assert "Reviewer edited front matter." in markdown


def test_cli_export_report_text_and_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    assert main(["export-report", str(project_dir), "--include-draft"]) == 0
    captured = capsys.readouterr()
    assert "Generated preview export" in captured.out

    assert main(["export-report", str(project_dir), "--include-draft", "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"
