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
    generate_deliverable_items,
    load_deliverable_items,
)
from review_assist.deliverable_matrix import REQUIRED_STUB_TEXT, load_deliverable_matrix


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

    dynamic_a = item_by_id(result, "wetlands-waterbodies-comparison-unit-00001")
    dynamic_b = item_by_id(result, "wetlands-waterbodies-comparison-unit-00002")
    assert dynamic_a["section_number"] == "3.1.1.1"
    assert dynamic_b["section_number"] == "3.1.1.2"
    assert dynamic_a["title"] == "Alternative A"
    assert dynamic_b["title"] == "Alternative B"
    assert dynamic_a["comparison_unit_ids"] == ["comparison-unit-00001"]
    assert dynamic_b["comparison_unit_ids"] == ["comparison-unit-00002"]


def test_deliverable_items_preserve_table_figure_attachment_refs_and_stubs(
    tmp_path: Path,
    empty_basemap_root: Path,
) -> None:
    project_dir = write_project(tmp_path, alternatives=1)

    result = generate_deliverable_items(project_dir, gpt_drafting=False)

    table = item_by_id(result, "table-wetlands-waterbodies")
    figure = item_by_id(result, "figure-wetlands-waterbodies")
    attachment = item_by_id(result, "attachment-hazardous-materials-report")
    section = item_by_id(result, "wetlands-and-waterbodies")

    assert table["review_item_type"] == "table"
    assert table["table_id"] == "table-wetlands-waterbodies"
    assert table["is_stub"] is True
    assert table["generated_content"] == REQUIRED_STUB_TEXT
    assert figure["review_item_type"] == "figure"
    assert figure["figure_id"] == "figure-wetlands-waterbodies"
    assert figure["is_stub"] is True
    assert figure["generated_content"] == REQUIRED_STUB_TEXT
    assert attachment["review_item_type"] == "attachment"
    assert attachment["attachment_id"] == "attachment-hazardous-materials-report"
    assert attachment["generated_content"] == REQUIRED_STUB_TEXT
    assert section["related_table_ids"] == ["table-wetlands-waterbodies"]
    assert section["related_figure_ids"] == ["figure-wetlands-waterbodies"]
    assert section["generated_content"] == REQUIRED_STUB_TEXT


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
