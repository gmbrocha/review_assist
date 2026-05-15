from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from review_assist.cli import main
from review_assist.maps import generate_maps
from review_assist.populate_for_review import populate_for_review
from review_assist.report_sections import (
    ReportSectionGenerationError,
    ReportSectionTemplateError,
    generate_report_sections,
    load_report_section_template_config,
    load_report_sections,
)
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


def write_layer(path: Path) -> Path:
    gdf = gpd.GeoDataFrame(
        [{"name": "Wetland A"}],
        geometry=[Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        crs="EPSG:4326",
    )
    path.write_text(gdf.to_json(drop_id=True), encoding="utf-8")
    return path


def section_by_id(result: dict[str, object], section_id: str) -> dict[str, object]:
    return next(section for section in result["sections"] if section["section_id"] == section_id)  # type: ignore[index]


def item_by_id(queue: dict[str, object], item_id: str) -> dict[str, object]:
    return next(item for item in queue["items"] if item["id"] == item_id)  # type: ignore[index]


def test_report_section_template_config_loads() -> None:
    config = load_report_section_template_config()

    assert config.sections[0].section_id == "front-matter"
    assert any(section.section_id == "executive-summary" for section in config.sections)
    assert any(section.section_id == "wetlands-and-waterbodies" for section in config.sections)
    wetlands = next(section for section in config.sections if section.section_id == "wetlands-and-waterbodies")
    assert wetlands.export_group == "resource_sections"
    assert wetlands.visual_slots


def test_report_section_template_config_rejects_invalid_templates(tmp_path: Path) -> None:
    template_path = tmp_path / "report_section_templates.json"
    template_path.write_text(
        json.dumps(
            {
                "sections": [
                    {
                        "section_id": "broken",
                        "type": "resource_section",
                        "title": "Broken",
                        "section_order": "not an integer",
                        "resource_category": "broken",
                        "purpose": "Broken",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReportSectionTemplateError, match="section_order"):
        load_report_section_template_config(template_path)


def test_report_section_template_config_rejects_boolean_section_order(tmp_path: Path) -> None:
    template_path = tmp_path / "report_section_templates.json"
    template_path.write_text(
        json.dumps(
            {
                "sections": [
                    {
                        "section_id": "broken",
                        "type": "resource_section",
                        "title": "Broken",
                        "section_order": True,
                        "resource_category": "broken",
                        "purpose": "Broken",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReportSectionTemplateError, match="section_order"):
        load_report_section_template_config(template_path)


def test_generate_report_sections_writes_no_blank_page_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = generate_report_sections(project_dir)

    assert (project_dir / "drafts" / "report_sections.json").exists()
    assert result["section_count"] == len(result["sections"])
    section_ids = [section["section_id"] for section in result["sections"]]
    assert section_ids == sorted(section_ids, key=lambda section_id: section_by_id(result, section_id)["section_order"])
    assert "project-overview" in section_ids
    assert "front-matter" in section_ids
    assert "conclusion-and-next-steps" in section_ids
    assert "maps-and-figures" in section_ids
    wetlands = section_by_id(result, "wetlands-and-waterbodies")
    assert wetlands["export_group"] == "resource_sections"
    assert wetlands["visual_slots"]
    assert wetlands["table_slots"]

    overview = section_by_id(result, "project-overview")
    assert "desktop screening" in str(overview["generated_content"]).lower()
    assert overview["review_status"] == "draft"

    maps = section_by_id(result, "maps-and-figures")
    assert maps["review_status"] == "needs_review"
    assert "missing_map_manifest" in maps["uncertainty_flags"]  # type: ignore[operator]


def test_deferred_source_sections_use_review_statuses_and_cautious_language(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = generate_report_sections(project_dir)

    wetlands = section_by_id(result, "wetlands-and-waterbodies")
    cultural = section_by_id(result, "cultural-and-historic")
    limitations = section_by_id(result, "limitations-and-missing-data")
    follow_up = section_by_id(result, "reviewer-follow-up")
    content = str(wetlands["generated_content"]).lower()
    assert wetlands["review_status"] == "needs_review"
    assert cultural["review_status"] == "needs_verification"
    assert limitations["review_status"] == "needs_verification"
    assert follow_up["review_status"] == "needs_verification"
    assert "draft/pre-review" in content
    assert "final determinations may require" in content
    assert "source-status-matrix" in str(limitations["generated_content"])
    assert "draft-finding-summary" in str(limitations["generated_content"])


def test_report_sections_preserve_related_ids_and_source_refs(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "wetlands.geojson")
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    analyze_project(project_dir)
    generate_maps(project_dir)

    result = generate_report_sections(project_dir)

    wetlands = section_by_id(result, "wetlands-and-waterbodies")
    assert wetlands["related_finding_ids"]  # type: ignore[index]
    assert "draft-finding-summary" in wetlands["related_table_ids"]  # type: ignore[operator]
    assert "usfws_nwi_wetlands" in wetlands["source_refs"]  # type: ignore[operator]
    assert "source-context-usfws-nwi-wetlands" in wetlands["related_figure_ids"]  # type: ignore[operator]


def test_load_report_sections_rejects_malformed_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    sections_path = project_dir / "drafts" / "report_sections.json"
    sections_path.parent.mkdir(parents=True)
    sections_path.write_text('{"sections": [{"section_id": "broken"}]}', encoding="utf-8")

    with pytest.raises(ReportSectionGenerationError, match="missing required fields"):
        load_report_sections(project_dir)
    with pytest.raises(ReviewQueueError, match="missing required fields"):
        generate_review_queue(project_dir)


def test_load_report_sections_rejects_boolean_section_order(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    result = generate_report_sections(project_dir)
    result["sections"][0]["section_order"] = False
    Path(result["output_path"]).write_text(json.dumps(result), encoding="utf-8")  # type: ignore[arg-type]

    with pytest.raises(ReportSectionGenerationError, match="section_order"):
        load_report_sections(project_dir)


def test_generate_report_sections_fails_clearly_for_malformed_upstream_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    findings_path = project_dir / "findings" / "draft_findings.json"
    findings_path.parent.mkdir(parents=True)
    findings_path.write_text('{"findings": [{"finding_id": "broken"}]}', encoding="utf-8")

    with pytest.raises(ReportSectionGenerationError, match="missing required fields"):
        generate_report_sections(project_dir)


def test_review_queue_includes_report_sections_and_preserves_state(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_report_sections(project_dir)

    queue = generate_review_queue(project_dir)
    item = item_by_id(queue, "report-section-wetlands-and-waterbodies")
    assert item["type"] == "report_section"
    assert item["section_id"] == "wetlands-and-waterbodies"
    assert item["resource_category"] == "wetlands_waterbodies"

    update_review_item(project_dir, "report-section-wetlands-and-waterbodies", status="accepted", note="Section reviewed.")
    generate_report_sections(project_dir)
    regenerated = generate_review_queue(project_dir)

    reviewed = item_by_id(regenerated, "report-section-wetlands-and-waterbodies")
    assert reviewed["status"] == "accepted"
    assert reviewed["export_eligible"] is True
    assert len(reviewed["reviewer_notes"]) == 1


def test_review_queue_updates_untouched_stale_draft_section_status(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    generate_report_sections(project_dir)
    queue = generate_review_queue(project_dir)
    item = item_by_id(queue, "report-section-limitations-and-missing-data")
    assert item["status"] == "needs_verification"

    item["status"] = "draft"
    item["export_eligible"] = False
    Path(queue["output_path"]).write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")  # type: ignore[arg-type]

    regenerated = generate_review_queue(project_dir)

    assert item_by_id(regenerated, "report-section-limitations-and-missing-data")["status"] == "needs_verification"


def test_cli_generate_report_sections_text_and_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["generate-report-sections", str(project_dir)]) == 0
    captured = capsys.readouterr()
    assert "Generated report sections" in captured.out

    assert main(["generate-report-sections", str(project_dir), "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"


def test_populate_for_review_manifest_includes_report_sections(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    result = populate_for_review(project_dir)

    assert result["artifact_paths"]["report_sections"].endswith("report_sections.json")
    assert any(step["name"] == "report_sections" and step["status"] == "completed" for step in result["steps"])
