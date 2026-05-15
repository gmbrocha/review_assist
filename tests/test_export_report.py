from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from review_assist import source_acquisition
from review_assist import deliverable as deliverable_module
from review_assist.data_lineage import build_data_lineage
from review_assist.deliverable import MvpDeliverableError, build_demo_deliverable, build_mvp_deliverable
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


def fake_empty_public_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    if params.get("f") == "pjson":
        return {"maxRecordCount": 100}
    return {"type": "FeatureCollection", "features": []}


def add_source_input(project_dir: Path, source_id: str, filename: str, geometry: dict[str, Any]) -> None:
    input_path = project_dir / "inputs" / filename
    input_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": source_id},
                        "geometry": geometry,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest_path = project_dir / "config" / "project.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inputs"].append(
        {
            "path": f"inputs/{filename}",
            "role": "source_layer",
            "description": f"Provided source layer for {source_id}",
            "source_id": source_id,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def add_supported_real_source_inputs(project_dir: Path) -> None:
    add_source_input(
        project_dir,
        "usfws_nwi_wetlands",
        "provided_nwi.geojson",
        {
            "type": "Polygon",
            "coordinates": [[[-90.001, 31.999], [-89.998, 31.999], [-89.998, 32.001], [-90.001, 32.001], [-90.001, 31.999]]],
        },
    )
    add_source_input(
        project_dir,
        "usgs_nhd_hydrography",
        "provided_nhd.geojson",
        {
            "type": "LineString",
            "coordinates": [[-90.001, 32.0], [-89.998, 32.0]],
        },
    )
    add_source_input(
        project_dir,
        "usfws_critical_habitat",
        "provided_critical_habitat.geojson",
        {
            "type": "Polygon",
            "coordinates": [[[-90.002, 31.998], [-89.997, 31.998], [-89.997, 32.002], [-90.002, 32.002], [-90.002, 31.998]]],
        },
    )
    add_source_input(
        project_dir,
        "epa_envirofacts_echo",
        "provided_echo.geojson",
        {
            "type": "Point",
            "coordinates": [-89.999, 32.0],
        },
    )


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


def docx_text(path: str | Path) -> str:
    from docx import Document

    document = Document(path)
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


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


def test_data_lineage_ignores_stale_download_manifest_without_active_registry_source(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    acquisition_dir = project_dir / "source_acquisition"
    acquisition_dir.mkdir()
    (acquisition_dir / "source_acquisition_manifest.json").write_text(
        json.dumps(
            {
                "downloads": [
                    {
                        "source_id": "usgs_nhd_hydrography",
                        "source_name": "National Hydrography Dataset",
                        "source_category": "hydrography_crossings",
                        "status": "downloaded",
                        "data_authenticity": "real",
                        "output_path": str(project_dir / "source_acquisition" / "downloads" / "usgs_nhd_hydrography.geojson"),
                        "feature_count": 12,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    lineage = build_data_lineage(project_dir)

    assert lineage["counts"]["downloaded_public_source"] == 0
    assert lineage["real_source_count"] == 0
    assert any(issue["code"] == "stale_download_record_ignored" for issue in lineage["validation_issues"])


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


def test_export_docx_preview_includes_drafts_and_marks_output(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    manifest = export_report(project_dir, include_draft=True, output_format="docx")
    text = docx_text(manifest["docx_path"])

    assert manifest["markdown_path"] is None
    assert manifest["docx_path"].endswith("environmental_constraints_report.docx")
    assert Path(manifest["docx_path"]).exists()
    assert "docx" in manifest["output_formats"]
    assert "INTERNAL PREVIEW / NOT REVIEWED" in text
    assert "Real Data Used" in text
    assert "Stubs / Manual Review Needed" in text
    assert manifest["data_lineage"]["counts"]["project_input"] == 1
    assert manifest["data_lineage"]["counts"]["missing_stub"] > 0
    assert any(issue["code"] == "no_real_source_layers" for issue in manifest["validation_issues"])
    assert "Study Area" in text
    assert "Generated Package Contents" in text


def test_export_strips_duplicate_report_section_headings(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)
    set_queue_item(
        project_dir,
        "report-section-front-matter",
        generated_content="# Front Matter\n\nBody without duplicate heading.",
    )

    manifest = export_report(project_dir, include_draft=True, output_format="both")
    markdown = Path(manifest["markdown_path"]).read_text(encoding="utf-8")
    text = docx_text(manifest["docx_path"])

    assert "\n### Front Matter\n" not in markdown
    assert "Body without duplicate heading." in markdown
    assert "Front Matter\nFront Matter\nBody without duplicate heading." not in text
    assert "Body without duplicate heading." in text


def test_docx_export_front_matter_lists_included_figures_tables_and_attachments(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    manifest = export_report(project_dir, include_draft=True, output_format="docx")
    text = docx_text(manifest["docx_path"])

    assert "List of Figures" in text
    assert "Project Overview" in text
    assert "List of Tables" in text
    assert "Source Status Matrix" in text
    assert "List of Attachments" in text
    assert "Attachment A: Project Maps." in text


def test_export_format_both_writes_markdown_and_docx(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    manifest = export_report(project_dir, include_draft=True, output_format="both")

    assert Path(manifest["markdown_path"]).exists()
    assert Path(manifest["docx_path"]).exists()
    assert manifest["output_formats"] == ["markdown", "docx"]


def test_docx_export_embeds_table_content_and_missing_figure_placeholder(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)
    set_queue_item(project_dir, "map-figure-project-overview", image_path=str(project_dir / "missing-map.png"))

    manifest = export_report(project_dir, include_draft=True, output_format="docx")
    text = docx_text(manifest["docx_path"])

    assert "category" in text
    assert "wetlands_waterbodies" in text
    assert "Figure placeholder: figure file was not available" in text
    assert any(issue["code"] == "missing_export_figure_asset" for issue in manifest["validation_issues"])
    assert manifest["mvp_quality"]["missing_figure_asset_warning_count"] >= 1


def test_export_with_nwi_backed_constraints_includes_accepted_findings_tables_and_maps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setattr(source_acquisition, "_fetch_json", fake_nwi_fetch)
    populate_for_review(project_dir, prepare_sources=True)
    queue = load_review_queue(project_dir)
    finding_id = next(item["id"] for item in queue["items"] if item["type"] == "draft_finding" and "Wetland" in item["title"])
    map_id = next(item["id"] for item in queue["items"] if item["type"] == "map_figure" and str(item.get("figure_id", "")).startswith("source-context"))

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
    assert manifest["data_lineage"]["counts"]["test_or_mock"] > 0
    assert "Mock NWI Wetland" in markdown
    assert "Map file:" in markdown
    assert "Caption:" in markdown
    assert "Source note:" in markdown
    assert manifest["export_figure_assets"]
    assert manifest["mvp_quality"]["copied_figure_asset_count"] == 1
    assert Path(manifest["export_figure_assets"][0]["export_image_path"]).exists()


def test_docx_export_with_nwi_backed_constraints_includes_accepted_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setattr(source_acquisition, "_fetch_json", fake_nwi_fetch)
    populate_for_review(project_dir, prepare_sources=True)
    queue = load_review_queue(project_dir)
    finding_id = next(item["id"] for item in queue["items"] if item["type"] == "draft_finding" and "Wetland" in item["title"])
    map_id = next(item["id"] for item in queue["items"] if item["type"] == "map_figure" and str(item.get("figure_id", "")).startswith("source-context"))

    update_review_item(project_dir, finding_id, status="accepted")
    update_review_item(project_dir, "report-section-wetlands-and-waterbodies", status="accepted")
    update_review_item(project_dir, "comparison-table-constraint-summary", status="accepted")
    update_review_item(project_dir, map_id, status="accepted")

    manifest = export_report(project_dir, output_format="docx")
    text = docx_text(manifest["docx_path"])

    assert finding_id in included_ids(manifest)
    assert "Mock NWI Wetland" in text
    assert "Constraint Summary" in text
    assert "Figure file:" in text
    assert "Caption:" in text
    assert "Source note:" in text
    assert manifest["mvp_quality"]["inline_rendered_table_count"] > 0
    assert manifest["mvp_quality"]["inline_rendered_figure_count"] > 0
    assert manifest["mvp_quality"]["copied_figure_asset_count"] == 1
    assert text.count("Figure file:") == 1


def test_report_sections_render_related_table_and_figure_inline_without_standalone_duplicates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setattr(source_acquisition, "_fetch_json", fake_nwi_fetch)
    populate_for_review(project_dir, prepare_sources=True)
    queue = load_review_queue(project_dir)
    map_id = next(item["id"] for item in queue["items"] if item["type"] == "map_figure" and str(item.get("figure_id", "")).startswith("source-context"))

    update_review_item(project_dir, "report-section-wetlands-and-waterbodies", status="accepted")
    update_review_item(project_dir, "comparison-table-constraint-summary", status="accepted")
    update_review_item(project_dir, map_id, status="accepted")

    manifest = export_report(project_dir, output_format="docx")
    text = docx_text(manifest["docx_path"])

    assert "Table: Constraint Summary" in text
    assert "Figure: Source Context:" in text
    assert "Generated draft map figure" not in text
    assert manifest["mvp_quality"]["inline_rendered_table_ids"] == ["constraint-summary"]
    assert manifest["mvp_quality"]["inline_rendered_figure_count"] == 1
    assert manifest["mvp_quality"]["copied_figure_asset_ids"] == ["source-context-usfws-nwi-wetlands"]


def test_export_warns_when_existing_map_manifest_cannot_be_loaded(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)
    manifest_path = project_dir / "maps" / "map_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{not-json", encoding="utf-8")

    manifest = export_report(project_dir, include_draft=True)

    assert any(issue["code"] == "map_manifest_unavailable" for issue in manifest["validation_issues"])
    assert manifest["mvp_quality"]["validation_warning_count"] >= 1


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

    assert main(["export-report", str(project_dir), "--include-draft", "--format", "both"]) == 0
    captured = capsys.readouterr()
    assert "Generated preview export" in captured.out
    assert "DOCX:" in captured.out

    assert main(["export-report", str(project_dir), "--include-draft", "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"


def test_build_demo_deliverable_writes_package_manifest_without_accepting_items(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    manifest = build_demo_deliverable(project_dir, output_format="both")
    queue = load_review_queue(project_dir)

    assert manifest["package_status"] == "internal_preview"
    assert Path(manifest["output_path"]).exists()
    assert Path(manifest["markdown_path"]).exists()
    assert Path(manifest["docx_path"]).exists()
    assert "data_lineage" in manifest
    assert not any(item["status"] in {"accepted", "edited"} for item in queue["items"])


def test_build_mvp_deliverable_fails_without_real_source_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)

    def populate_without_source_preparation(
        project_dir: Path,
        *,
        prepare_sources: bool,
        include_optional_sources: bool,
        materialize_local_sources: bool = False,
        gpt_drafting: bool | None = None,
        gpt_model: str | None = None,
    ) -> dict[str, Any]:
        return populate_for_review(project_dir, prepare_sources=False, include_optional_sources=False)

    monkeypatch.setattr(deliverable_module, "populate_for_review", populate_without_source_preparation)

    with pytest.raises(MvpDeliverableError, match="MVP deliverables require"):
        build_mvp_deliverable(project_dir)


def test_build_mvp_deliverable_fails_with_test_fixture_downloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = write_project(tmp_path)
    monkeypatch.setattr(source_acquisition, "_fetch_json", fake_empty_public_fetch)

    with pytest.raises(MvpDeliverableError, match="test fixture"):
        build_mvp_deliverable(project_dir, fail_on_no_downloaded_sources=False)


def test_build_mvp_deliverable_succeeds_with_real_provided_source_layers(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    add_supported_real_source_inputs(project_dir)

    manifest = build_mvp_deliverable(project_dir, output_format="docx")
    text = docx_text(manifest["docx_path"])

    assert manifest["package_status"] == "internal_preview_real_data_mvp"
    assert manifest["data_lineage"]["counts"]["provided_in_input"] >= 4
    assert manifest["data_lineage"]["counts"]["test_or_mock"] == 0
    assert manifest["mvp_quality"]["real_source_count"] >= 4
    assert manifest["mvp_quality"]["source_backed_constraint_count"] > 0
    assert "Real Data Used" in text
    assert "provided_in_input" in json.dumps(manifest["data_lineage"])


def test_cli_build_mvp_deliverable_json_with_real_provided_sources(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_dir = write_project(tmp_path)
    add_supported_real_source_inputs(project_dir)

    assert main(["build-mvp-deliverable", str(project_dir), "--format", "docx", "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["project_id"] == "test_project"
    assert payload["data_lineage"]["real_source_count"] >= 4
    assert Path(payload["docx_path"]).exists()


def test_cli_build_demo_deliverable_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["build-demo-deliverable", str(project_dir), "--format", "docx", "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["project_id"] == "test_project"
    assert payload["markdown_path"] is None
    assert Path(payload["docx_path"]).exists()
