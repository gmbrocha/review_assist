from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

import review_assist.project_area as project_area_module
from review_assist.cli import main
from review_assist.deliverable_items import (
    DELIVERABLE_ITEMS_PATH,
    REQUIRED_ITEM_FIELDS,
    DeliverableItemsError,
    _attachment_item,
    _figure_item,
    _section_evidence,
    _section_content,
    _stub_section_content,
    _table_item,
    generate_deliverable_items,
    load_deliverable_items,
)
from review_assist.deliverable_matrix import REQUIRED_STUB_TEXT, load_deliverable_matrix
from review_assist.extent_policy import target_extent_metadata


PROCESS_LANGUAGE = [
    "draft review candidate",
    "pre-review",
    "reviewer verification",
    "reviewer focus",
    "related table status",
]


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


def write_project(tmp_path: Path, *, alternatives: int = 2) -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    if alternatives == 1:
        body = """
        <Placemark><name>Alternative A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """
    else:
        body = """
        <Placemark><name>Alternative A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        <Placemark><name>Alternative B</name><LineString><coordinates>-90.0000,32.0020,0 -89.9900,32.0020,0</coordinates></LineString></Placemark>
        """
    (project_dir / "inputs" / "routes.kmz").write_bytes(kmz_bytes(kml_document(body)))
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


@pytest.fixture()
def empty_basemap_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    basemap_root = tmp_path / "empty_naip"
    basemap_root.mkdir()
    monkeypatch.setattr(project_area_module, "AERIAL_BASEMAP_ROOT", basemap_root)
    return basemap_root


def item_by_id(items: dict[str, object], item_id: str) -> dict[str, object]:
    return next(item for item in items["items"] if item["deliverable_item_id"] == item_id)  # type: ignore[index]


def test_deliverable_items_write_matrix_contract_and_dynamic_children(
    tmp_path: Path,
    empty_basemap_root: Path,
) -> None:
    project_dir = write_project(tmp_path, alternatives=2)

    result = generate_deliverable_items(project_dir, gpt_drafting=False)
    matrix = load_deliverable_matrix()
    static_sections = [target for target in matrix.section_targets if target.target_type != "dynamic_subsection_template"]
    expected_count = len(static_sections) + 2 + len(matrix.table_targets) + len(matrix.figure_targets) + len(matrix.attachment_targets)

    assert (project_dir / DELIVERABLE_ITEMS_PATH).exists()
    assert result["item_count"] == expected_count
    assert result["expected_item_count"] == expected_count
    assert result["project_id"] == "test_project"
    assert result["upstream_artifacts"]["deliverable_matrix_path"] == "config/deliverable_section_matrix.json"
    assert result["upstream_artifacts"]["report_generation_prompts_path"] == "config/report_generation_prompts.json"
    assert all(REQUIRED_ITEM_FIELDS <= set(item) for item in result["items"])
    for item in result["items"]:
        lowered = str(item["generated_content"]).lower()
        assert all(phrase not in lowered for phrase in PROCESS_LANGUAGE)

    dynamic_a = item_by_id(result, "wetlands-waterbodies-comparison-unit-00001")
    dynamic_b = item_by_id(result, "wetlands-waterbodies-comparison-unit-00002")
    assert dynamic_a["section_number"] == "3.1.1.1"
    assert dynamic_b["section_number"] == "3.1.1.2"
    assert dynamic_a["title"] == "Alternative A"
    assert dynamic_b["title"] == "Alternative B"
    assert dynamic_a["comparison_unit_ids"] == ["comparison-unit-00001"]
    assert dynamic_b["comparison_unit_ids"] == ["comparison-unit-00002"]
    assert dynamic_a["policy_comparison_unit_expansion"] == "narrative_children"
    assert dynamic_a["render_decision"] == "include_body"
    assert dynamic_a["report_body_eligible"] is True
    assert dynamic_b["policy_comparison_unit_expansion"] == "narrative_children"
    assert dynamic_b["render_decision"] == "include_body"
    assert dynamic_b["report_body_eligible"] is True

    pel = item_by_id(result, "relationship-with-pel-study")
    assert pel["policy_inclusion_status"] == "conditional"
    assert pel["policy_activation_condition"] == "reviewer_supplied_parent_study"
    assert pel["policy_review_requirement"] == "manual_review"
    assert pel["render_decision"] == "needs_reviewer_decision"
    assert pel["render_destination"] == "review_status"
    assert pel["report_body_eligible"] is False
    assert pel["review_status"] == "needs_verification"
    assert pel["is_stub"] is True
    assert "Render decision: needs_reviewer_decision." in pel["generated_content"]

    floodplains = item_by_id(result, "floodplains-and-floodways")
    assert floodplains["policy_comparison_unit_expansion"] == "table_only"
    assert floodplains["render_decision"] == "table_figure_only"
    assert floodplains["render_destination"] == "tables_figures"
    assert floodplains["report_body_eligible"] is False
    assert floodplains["related_table_ids"] == ["table-fema-flood-zones"]
    assert "Render decision: table_figure_only." in floodplains["generated_content"]


def test_deliverable_items_preserve_table_figure_attachment_refs_and_stubs(
    tmp_path: Path,
    empty_basemap_root: Path,
) -> None:
    project_dir = write_project(tmp_path, alternatives=1)

    result = generate_deliverable_items(project_dir, gpt_drafting=False)

    table = item_by_id(result, "table-wetlands-waterbodies")
    figure = item_by_id(result, "figure-wetlands-waterbodies")
    attachment_a_wrapper = item_by_id(result, "attachment-a-project-maps")
    attachment_b_wrapper = item_by_id(result, "attachment-b-hazardous-materials-report")
    attachment = item_by_id(result, "attachment-hazardous-materials-report")
    section = item_by_id(result, "wetlands-and-waterbodies")

    assert table["review_item_type"] == "table"
    assert table["table_id"] == "table-wetlands-waterbodies"
    assert table["is_stub"] is True
    assert table["stub_text"] == REQUIRED_STUB_TEXT
    assert "explicit source/data stub" in table["generated_content"]
    assert "Expected source refs" in table["generated_content"]
    assert figure["review_item_type"] == "figure"
    assert figure["figure_id"] == "figure-wetlands-waterbodies"
    assert figure["is_stub"] is True
    assert figure["stub_text"] == REQUIRED_STUB_TEXT
    assert "could not be generated" in figure["generated_content"]
    assert "missing figure should be carried as an explicit limitation" in figure["generated_content"]
    assert attachment["review_item_type"] == "attachment"
    assert attachment["attachment_id"] == "attachment-hazardous-materials-report"
    assert attachment["stub_text"] == REQUIRED_STUB_TEXT
    assert "Hazardous Materials Report" in attachment["generated_content"]
    assert "supporting attachment material" in attachment["generated_content"]
    assert "attachment-environmental-constraints-maps" in attachment_a_wrapper["generated_content"]
    assert "Accepted figures and supporting panels form the attachment map package" in attachment_a_wrapper["generated_content"]
    assert attachment_a_wrapper["assumptions"]["source_gap_status"] == []
    assert "attachment-hazardous-materials-report" in attachment_b_wrapper["generated_content"]
    assert attachment_b_wrapper["assumptions"]["source_gap_status"] == []
    assert section["related_table_ids"] == ["table-wetlands-waterbodies"]
    assert section["related_figure_ids"] == ["figure-wetlands-waterbodies"]
    assert section["evidence_refs"] == ["section_evidence:wetlands-and-waterbodies"]
    assert section["stub_text"] == REQUIRED_STUB_TEXT
    assert "explicit source/data gap" in section["generated_content"]
    assert "Related table limitation" in section["generated_content"]

    contamination = item_by_id(result, "contamination-risks")
    hazardous = item_by_id(result, "hazardous-materials-sites")
    oil_wells = item_by_id(result, "oil-wells")
    assert contamination["related_figure_ids"] == ["figure-hazardous-waste-sites", "figure-water-discharge-waste-facilities"]
    assert hazardous["related_figure_ids"] == ["figure-hazardous-waste-sites", "figure-water-discharge-waste-facilities"]
    assert oil_wells["related_figure_ids"] == ["figure-oil-gas-wells"]


def test_load_deliverable_items_round_trip_and_validates_contract(
    tmp_path: Path,
    empty_basemap_root: Path,
) -> None:
    project_dir = write_project(tmp_path)
    written = generate_deliverable_items(project_dir, gpt_drafting=False)

    loaded = load_deliverable_items(project_dir)
    assert loaded["item_count"] == written["item_count"]
    assert [item["deliverable_item_id"] for item in loaded["items"]] == [
        item["deliverable_item_id"] for item in written["items"]
    ]

    path = project_dir / DELIVERABLE_ITEMS_PATH
    corrupted = json.loads(path.read_text(encoding="utf-8"))
    corrupted["item_count"] = corrupted["item_count"] + 1
    path.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(DeliverableItemsError, match="item_count"):
        load_deliverable_items(project_dir)

    corrupted["item_count"] = written["item_count"]
    corrupted["expected_item_count"] = written["expected_item_count"]
    corrupted["items"][0]["is_stub"] = True
    corrupted["items"][0]["stub_text"] = REQUIRED_STUB_TEXT
    corrupted["items"][0]["generated_content"] = ""
    path.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(DeliverableItemsError, match="stub generated_content"):
        load_deliverable_items(project_dir)


def test_section_evidence_prefers_available_category_for_broad_targets() -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.section_targets if item.target_id == "natural-and-ecological-resources")
    evidence = {
        "section_evidence": {
            "flood-hazard": {
                "section_id": "flood-hazard",
                "resource_category": "flood_hazard",
                "source_gap_status": [{"category": "flood_hazard", "status": "downloadable"}],
                "evidence_classes": ["failed_or_missing"],
                "source_refs": ["fema_nfhl_flood_hazard"],
            },
            "wetlands-and-waterbodies": {
                "section_id": "wetlands-and-waterbodies",
                "resource_category": "wetlands_waterbodies",
                "source_gap_status": [{"category": "wetlands_waterbodies", "status": "provided_locally"}],
                "evidence_classes": ["real_source"],
                "source_refs": ["usfws_nwi_wetlands"],
            },
        }
    }

    selected = _section_evidence(evidence, target, None, None)

    assert selected["section_id"] == "wetlands-and-waterbodies"


def test_source_backed_wetlands_section_candidate_is_report_style_prose() -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.section_targets if item.target_id == "wetlands-and-waterbodies")
    table = {
        "table_id": "table-wetlands-waterbodies",
        "table_number": 1,
        "title": "Descriptions of Wetlands and Waterbodies Present within the Project Area",
        "is_stub": False,
        "row_count": 2,
        "source_refs": ["usfws_nwi_wetlands"],
    }
    figure = {
        "figure_id": "figure-wetlands-waterbodies",
        "figure_number": 1,
        "title": "Wetlands and Waterbodies in and near the Project Area",
        "is_stub": False,
        "image_path": "maps/figures/figure-wetlands-waterbodies.png",
        "source_refs": ["usfws_nwi_wetlands"],
    }
    evidence = {
        "source_refs": ["usfws_nwi_wetlands"],
        "source_gap_status": [{"category": "wetlands_waterbodies", "status": "provided_locally"}],
        "constraint_summaries": [{"constraint_id": "constraint-1"}],
        "comparison_unit_summaries": [{"comparison_unit_id": "comparison-unit-00001"}],
    }

    content = _section_content(
        target=target,
        context={"project_name": "Test Project"},
        evidence=evidence,
        related_tables=[table],
        related_figures=[figure],
        comparison_unit=None,
    )

    lowered = content.lower()
    assert "Mapped wetland and waterbody features" in content
    assert "U.S. Fish and Wildlife Service National Wetlands Inventory" in content
    assert "Table 1" in content
    assert "Figure 1" in content
    assert "Table 1" in content and "2 bounded row(s)" in content
    assert "NWI and hydrography data are suitable for early screening" in content
    assert all(phrase not in lowered for phrase in PROCESS_LANGUAGE)
    assert "Empty stub" not in content
    assert "coordinates" not in lowered
    assert "FeatureCollection" not in content
    assert "sources/" not in content


def test_dynamic_wetlands_comparison_unit_candidate_mentions_unit_and_remains_compact() -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.section_targets if item.target_id == "wetlands-and-waterbodies")

    content = _section_content(
        target=target,
        context={},
        evidence={
            "source_refs": ["usfws_nwi_wetlands"],
            "comparison_unit_summaries": [{"comparison_unit_id": "comparison-unit-00002"}],
        },
        related_tables=[],
        related_figures=[],
        comparison_unit={"comparison_unit_id": "comparison-unit-00002", "comparison_unit_name": "Alternative B"},
    )

    lowered = content.lower()
    assert "Alternative B" in content
    assert "comparison unit Alternative B" in content
    assert "U.S. Fish and Wildlife Service National Wetlands Inventory" in content
    assert all(phrase not in lowered for phrase in PROCESS_LANGUAGE)
    assert len(content) < 1400


def test_broad_source_backed_section_prefers_available_evidence_and_limitations() -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.section_targets if item.target_id == "contamination-risks")
    evidence = {
        "source_refs": ["epa_frs_facilities_ms", "maris_brownfields", "mississippi_oil_gas_wells"],
        "source_gap_status": [
            {"category": "regulated_facilities", "status": "provided_locally", "source_ids": ["epa_frs_facilities_ms"]},
            {"category": "hazardous_materials_report", "status": "manual", "source_ids": ["attachment-hazardous-materials-report"]},
        ],
        "constraint_summaries": [
            {
                "constraint_id": "constraint-1",
                "relationship_type": "nearest_within_buffer",
                "source_id": "epa_frs_facilities_ms",
                "source_category": "regulated_facilities",
            }
        ],
    }

    content = _section_content(
        target=target,
        context={"project_name": "Test Project"},
        evidence=evidence,
        related_tables=[],
        related_figures=[],
        comparison_unit=None,
        extent_metadata=target_extent_metadata(
            target_id=target.target_id,
            target_type=target.target_type,
            resource_category=target.resource_category,
            source_categories=target.source_categories,
        ),
    )

    lowered = content.lower()
    assert "Mapped regulated facility and contamination-risk context" in content
    assert "in the project vicinity" in content
    assert "within the project area" not in lowered
    assert "EPA Facility Registry Service facilities" in content
    assert "MARIS brownfields" in content
    assert "Mississippi Oil and Gas Board wells" in content
    assert "1 compact source-backed mapped relationship" in content
    assert "Unavailable or deferred source categories remain limitations" in content
    assert "hazardous_materials_report=manual" in content
    assert "do not establish contamination extent" in content
    assert all(phrase not in lowered for phrase in PROCESS_LANGUAGE)


def test_watershed_section_wording_uses_context_scope_without_fake_implementation() -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.section_targets if item.target_id == "water-quality")

    content = _section_content(
        target=target,
        context={"project_name": "Test Project"},
        evidence={
            "source_refs": ["usgs_nhd_flowlines"],
            "source_gap_status": [{"category": "hydrography_crossings", "status": "provided_locally"}],
            "constraint_summaries": [{"constraint_id": "constraint-1", "relationship_type": "crosses"}],
        },
        related_tables=[],
        related_figures=[],
        comparison_unit=None,
        extent_metadata=target_extent_metadata(
            target_id=target.target_id,
            target_type=target.target_type,
            resource_category=target.resource_category,
            source_categories=target.source_categories,
        ),
    )

    lowered = content.lower()
    assert "in the watershed/subwatershed context" in content
    assert "current automated watershed context remains limited" in content
    assert "direct project impact" not in lowered


def test_p2_missing_source_section_keeps_honest_source_gap_content() -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.section_targets if item.target_id == "cultural-and-historic-resources")

    content = _stub_section_content(
        target,
        [{"category": "cultural_historic", "status": "restricted", "source_ids": ["maris_public_cultural_context"]}],
        related_tables=[],
        related_figures=[],
        validation_issues=[],
    )

    lowered = content.lower()
    assert "explicit source/data gap" in content
    assert "cultural_historic=restricted" in content
    assert "MARIS public cultural context" not in content
    assert "does not rank alternatives or make determinations" in content
    assert all(phrase not in lowered for phrase in PROCESS_LANGUAGE)


def test_section_content_excludes_raw_rows_coordinates_geojson_and_source_paths() -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.section_targets if item.target_id == "wetlands-and-waterbodies")
    content = _section_content(
        target=target,
        context={"project_name": "Test Project"},
        evidence={
            "source_refs": ["usfws_nwi_wetlands"],
            "row_summaries": [
                {
                    "table_id": "table-wetlands-waterbodies",
                    "values": {
                        "geometry": {"coordinates": [[-90.0, 32.0]]},
                        "raw_path": r"F:\\Desktop\\review_assist\\sources\\wetlands\\raw.shp",
                    },
                }
            ],
            "constraint_summaries": [{"constraint_id": "constraint-1", "relationship_type": "intersects"}],
        },
        related_tables=[
            {
                "table_id": "table-wetlands-waterbodies",
                "is_stub": False,
                "row_count": 1,
                "source_refs": ["usfws_nwi_wetlands"],
            }
        ],
        related_figures=[],
        comparison_unit=None,
    )

    serialized = content.lower()
    assert "coordinates" not in serialized
    assert "geojson" not in serialized
    assert "featurecollection" not in serialized
    assert "raw.shp" not in serialized
    assert "sources" not in serialized


def test_generated_table_candidate_summarizes_rows_without_dumping_raw_rows(tmp_path: Path) -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.table_targets if item.target_id == "table-wetlands-waterbodies")
    table = {
        "table_id": target.target_id,
        "title": target.title,
        "columns": ["Alternative", "Wetland Type", "Estimated Acreage"],
        "rows": [
            {"Alternative": f"Alternative {i}", "Wetland Type": "Freshwater Pond", "Estimated Acreage": i}
            for i in range(1, 8)
        ],
        "row_count": 7,
        "source_refs": ["usfws_nwi_wetlands"],
        "comparison_unit_ids": ["comparison-unit-00001", "comparison-unit-00002"],
        "related_constraint_ids": [],
        "uncertainty_flags": [],
        "is_stub": False,
        "review_status": "needs_review",
        "validation_issues": [],
        "provenance": {},
    }

    item = _table_item(target, {"output_path": "deliverable/tables.json", "tables": [table]}, "test", tmp_path / "deliverable_items.json")

    assert "7 bounded row(s)" in item["generated_content"]
    assert "Body preview is limited to 5 row(s)" in item["generated_content"]
    assert "usfws_nwi_wetlands" in item["generated_content"]
    assert "Alternative 7" not in item["generated_content"]


def test_generated_figure_candidate_includes_caption_source_method_and_image_status(tmp_path: Path) -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.figure_targets if item.target_id == "figure-wetlands-waterbodies")
    figure = {
        "figure_id": target.target_id,
        "title": target.title,
        "image_path": "maps/figures/figure-wetlands-waterbodies.png",
        "caption": "Wetlands and waterbodies in and near the project area.",
        "source_note": "USFWS NWI and project geometry.",
        "method_note": "Vector overlay screening map.",
        "source_refs": ["usfws_nwi_wetlands"],
        "related_constraint_ids": [],
        "comparison_unit_ids": ["comparison-unit-00001"],
        "uncertainty_flags": [],
        "is_stub": False,
        "review_status": "needs_review",
        "validation_issues": [],
        "provenance": {},
    }

    item = _figure_item(target, {"output_path": "deliverable/figures.json", "figures": [figure]}, "test", tmp_path / "deliverable_items.json")

    assert "Caption: Wetlands and waterbodies" in item["generated_content"]
    assert "Source note: USFWS NWI" in item["generated_content"]
    assert "Method note: Vector overlay" in item["generated_content"]
    assert "reviewer verification" not in item["generated_content"].lower()
    assert "draft/pre-review" not in item["generated_content"].lower()
    assert "Draft figure review candidate" not in item["generated_content"]
    assert "Generated deliverable figure" not in item["generated_content"]


def test_attachment_a_candidate_references_main_figures_and_panel_maps(tmp_path: Path) -> None:
    matrix = load_deliverable_matrix()
    target = next(item for item in matrix.attachment_targets if item.target_id == "attachment-environmental-constraints-maps")
    figures = {
        "output_path": "deliverable/figures.json",
        "figures": [
            {"figure_id": "figure-wetlands-waterbodies"},
            {"figure_id": "figure-energy-infrastructure"},
        ],
        "attachment_supporting_figures": [
            {"figure_id": "attachment-a-panel-001"},
            {"figure_id": "attachment-a-panel-002"},
        ],
    }

    item = _attachment_item(target, figures, "test", tmp_path / "deliverable_items.json")

    assert "map package references generated report figures" in item["generated_content"]
    assert "figure-wetlands-waterbodies" in item["generated_content"]
    assert "Supporting panel maps included: 2" in item["generated_content"]


def test_cli_generate_deliverable_items_json(
    tmp_path: Path,
    empty_basemap_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_dir = write_project(tmp_path, alternatives=1)

    assert main(["generate-deliverable-items", str(project_dir), "--no-gpt-drafting", "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["project_id"] == "test_project"
    assert payload["output_path"].endswith("deliverable_items.json")
    water_quality = next(item for item in payload["items"] if item["deliverable_item_id"] == "water-quality")
    health_care = next(item for item in payload["items"] if item["deliverable_item_id"] == "health-care-facilities")
    demographics = next(item for item in payload["items"] if item["deliverable_item_id"] == "demographic-characteristics")
    assert water_quality["analysis_extent_type"] == "watershed_context_extent"
    assert "watershed/subwatershed context" in water_quality["interpretation_scope_label"]
    assert health_care["analysis_extent_type"] == "community_context_extent"
    assert "near the project area" in health_care["interpretation_scope_label"]
    assert demographics["analysis_extent_type"] == "county_or_regional_context_extent"
    assert "for county or regional context" in demographics["interpretation_scope_label"]
