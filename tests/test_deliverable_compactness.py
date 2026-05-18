from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from review_assist import section_drafting
from review_assist.deliverable_items import generate_deliverable_items, load_deliverable_items
from review_assist.deliverable_matrix import load_deliverable_matrix
from review_assist.export_report import export_report
from review_assist.populate_for_review import populate_for_review
from review_assist.review_queue import generate_review_queue, load_review_queue

from test_export_report import set_only_reviewed_items, set_review_states, write_project


RAW_LEGACY_TYPES = {
    "draft_finding",
    "spatial_relationship",
    "comparison_table",
    "source_inventory_note",
    "source_status_note",
    "no_mapped_relationships",
}


EXPECTED_STATIC_SECTION_IDS = [
    "cover-title",
    "list-of-figures",
    "list-of-tables",
    "list-of-attachments",
    "executive-summary",
    "introduction",
    "relationship-with-pel-study",
    "study-area",
    "methodology",
    "data-collection-and-sources",
    "mapping-and-analysis-procedures",
    "limitations-and-data-gaps",
    "environmental-constraints-inventory",
    "natural-and-ecological-resources",
    "wetlands-and-waterbodies",
    "floodplains-and-floodways",
    "water-quality",
    "protected-species-and-critical-habitat",
    "cultural-and-historic-resources",
    "archaeological-sites",
    "historic-structures-and-districts",
    "community-resources",
    "fire-ems-stations",
    "government-buildings",
    "education-facilities",
    "health-care-facilities",
    "places-of-worship",
    "parks-and-recreation-areas",
    "utility-and-infrastructure-considerations",
    "public-water-supply",
    "utility-infrastructure",
    "energy-infrastructure",
    "airports",
    "contamination-risks",
    "hazardous-materials-sites",
    "oil-wells",
    "socioeconomic-and-business-considerations",
    "demographic-characteristics",
    "local-businesses-and-economic-nodes",
    "conclusion-and-next-steps",
    "attachment-a-project-maps",
    "attachment-b-hazardous-materials-report",
    "attachment-c-agency-consultation-letters",
]


EXPECTED_TABLE_IDS = [
    "table-wetlands-waterbodies",
    "table-fema-flood-zones",
    "table-income-demographics",
    "table-demographic-composition",
]


EXPECTED_FIGURE_IDS = [
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
    "figure-census-tracts",
]


EXPECTED_ATTACHMENT_IDS = [
    "attachment-environmental-constraints-maps",
    "attachment-hazardous-materials-report",
    "attachment-agency-consultation-letters",
]


def test_standard_deliverable_outline_is_bounded(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    result = generate_deliverable_items(project_dir, gpt_drafting=False)
    matrix = load_deliverable_matrix()
    static_sections = [target for target in matrix.section_targets if target.target_type != "dynamic_subsection_template"]
    dynamic_templates = [target for target in matrix.section_targets if target.target_type == "dynamic_subsection_template"]
    comparison_unit_count = 1
    expected_count = len(static_sections) + comparison_unit_count + len(matrix.table_targets) + len(matrix.figure_targets) + len(matrix.attachment_targets)

    assert len(static_sections) == 43
    assert len(dynamic_templates) == 1
    assert len(matrix.table_targets) == 4
    assert len(matrix.figure_targets) == 13
    assert len(matrix.attachment_targets) == 3
    assert result["item_count"] == expected_count
    assert result["expected_item_count"] == expected_count
    assert not {item["review_item_type"] for item in result["items"]}.intersection(RAW_LEGACY_TYPES)


def test_default_export_contains_no_legacy_raw_item_types(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)

    standard_queue = load_review_queue(project_dir)
    assert standard_queue["queue_mode"] == "deliverable_items"
    assert not {item["type"] for item in standard_queue["items"]}.intersection(RAW_LEGACY_TYPES)

    legacy_queue = generate_review_queue(project_dir, include_legacy_artifacts=True)
    assert legacy_queue["queue_mode"] == "legacy_audit"

    generate_review_queue(project_dir)
    set_review_states(project_dir)
    manifest = export_report(project_dir)

    assert manifest["review_gate_status"] == "passed"
    assert not {item["type"] for item in manifest["included_items"]}.intersection(RAW_LEGACY_TYPES)


def test_large_table_is_body_preview_limited(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)
    _write_large_deliverable_table(project_dir, row_count=60)
    generate_deliverable_items(project_dir, gpt_drafting=False)
    generate_review_queue(project_dir)
    set_only_reviewed_items(
        project_dir,
        {
            "wetlands-and-waterbodies": "accepted",
            "table-wetlands-waterbodies": "accepted",
        },
    )

    manifest = export_report(project_dir)
    markdown = Path(manifest["markdown_path"]).read_text(encoding="utf-8")

    assert "Table preview limited to 5 of 60 rows" in markdown
    assert "Alternative 004" in markdown
    assert "Alternative 059" not in markdown
    assert manifest["compactness_budget"]["rendered_table_preview_row_count"] == 5


def test_export_manifest_reports_compactness_budget(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)
    set_review_states(project_dir)

    manifest = export_report(project_dir)
    budget = manifest["compactness_budget"]

    assert budget["included_section_count"] > 0
    assert budget["included_table_count"] == 4
    assert budget["included_figure_count"] == 13
    assert budget["included_attachment_count"] == 3
    assert budget["stub_item_count"] == manifest["stub_item_count"]
    assert budget["rendered_table_preview_row_count"] <= 4 * 5
    assert budget["approximate_body_character_count"] > 0
    assert budget["review_gate_status"] == "passed"
    assert budget["expected_deliverable_item_count"] == manifest["expected_deliverable_item_count"]
    assert budget["actual_deliverable_item_count"] == manifest["actual_deliverable_item_count"]


def test_deliverable_items_store_row_previews_not_full_raw_rows(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)
    _write_large_deliverable_table(project_dir, row_count=60)
    result = generate_deliverable_items(project_dir, gpt_drafting=False)

    table_item = next(item for item in result["items"] if item["deliverable_item_id"] == "table-wetlands-waterbodies")
    assumptions = table_item["assumptions"]

    assert table_item["table_id"] == "table-wetlands-waterbodies"
    assert assumptions["row_count"] == 60
    assert len(assumptions["rows_preview"]) == 5
    assert "rows" not in assumptions
    assert "rows" not in table_item

    loaded = load_deliverable_items(project_dir)
    loaded_table = next(item for item in loaded["items"] if item["deliverable_item_id"] == "table-wetlands-waterbodies")
    assert len(loaded_table["assumptions"]["rows_preview"]) == 5


def test_planned_report_outline_snapshot() -> None:
    matrix = load_deliverable_matrix()
    static_section_ids = [target.target_id for target in matrix.section_targets if target.target_type != "dynamic_subsection_template"]
    table_ids = [target.target_id for target in matrix.table_targets]
    figure_ids = [target.target_id for target in matrix.figure_targets]
    attachment_ids = [target.target_id for target in matrix.attachment_targets]

    assert static_section_ids == EXPECTED_STATIC_SECTION_IDS
    assert table_ids == EXPECTED_TABLE_IDS
    assert figure_ids == EXPECTED_FIGURE_IDS
    assert attachment_ids == EXPECTED_ATTACHMENT_IDS


def test_gpt_or_section_draft_length_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = write_project(tmp_path)

    def oversized_gpt_response(self: section_drafting.OpenAISectionDraftProvider, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "draft_content": "Long generated section. " * 250,
            "cited_finding_ids": [],
            "cited_table_ids": [],
            "cited_figure_ids": [],
            "cited_source_refs": [],
            "caveats": [],
        }

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("GPT_DRAFTING_WORKERS", "1")
    monkeypatch.setattr(section_drafting.OpenAISectionDraftProvider, "_create_response", oversized_gpt_response)

    result = generate_deliverable_items(project_dir, gpt_drafting=True, gpt_model="gpt-test")

    assert any(
        issue["code"] == "deliverable_item_content_over_budget"
        for item in result["items"]
        for issue in item["validation_issues"]
    )
    assert any(issue["code"] == "deliverable_item_content_over_budget" for issue in result["validation_issues"])


def _write_large_deliverable_table(project_dir: Path, *, row_count: int) -> None:
    tables_path = project_dir / "deliverable" / "tables.json"
    artifact = json.loads(tables_path.read_text(encoding="utf-8"))
    rows = [
        {
            "Alternative": f"Alternative {index:03d}",
            "Stream Crossings": index,
            "Freshwater Emergent Wetland": index + 1,
            "Freshwater Forested/Shrub Wetland": index + 2,
            "Freshwater Pond": index + 3,
        }
        for index in range(row_count)
    ]
    for table in artifact["tables"]:
        if table["table_id"] == "table-wetlands-waterbodies":
            table["rows"] = rows
            table["row_count"] = len(rows)
            table["source_refs"] = ["usfws_nwi_wetlands"]
            table["comparison_unit_ids"] = ["comparison-unit-00001"]
            table["related_constraint_ids"] = [f"constraint-{index:03d}" for index in range(row_count)]
            table["is_stub"] = False
            table["stub_text"] = ""
            table["review_status"] = "draft"
            table["uncertainty_flags"] = ["draft_pre_review"]
            break
    tables_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
