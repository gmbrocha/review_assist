from __future__ import annotations

import json
import zipfile
from pathlib import Path

from review_assist.inspection import inspect_project
from review_assist.populate_for_review import populate_for_review
from review_assist.review_queue import load_review_queue
from review_assist.source_catalog import load_project_source_registry, load_source_catalog


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


def route_kmz() -> bytes:
    return kmz_bytes(
        kml_document(
            """
            <Placemark><name>Route A</name><LineString><coordinates>-90.0,32.0,0 -89.99,32.0,0</coordinates></LineString></Placemark>
            <Placemark><name>Route B</name><LineString><coordinates>-90.0,32.002,0 -89.99,32.002,0</coordinates></LineString></Placemark>
            """
        )
    )


def point_kmz() -> bytes:
    return kmz_bytes(
        kml_document(
            """
            <Placemark><name>Site A</name><Point><coordinates>-90.0,32.0,0</coordinates></Point></Placemark>
            <Placemark><name>Site B</name><Point><coordinates>-89.99,32.0,0</coordinates></Point></Placemark>
            """
        )
    )


def write_project(tmp_path: Path, *, project_id: str, kmz: bytes, role: str = "alternatives") -> Path:
    project_dir = tmp_path / project_id
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    (project_dir / "inputs" / "project.kmz").write_bytes(kmz)
    (project_dir / "config" / "project.json").write_text(
        json.dumps(
            {
                "project_id": project_id,
                "name": project_id.replace("_", " ").title(),
                "description": "Synthetic project workspace for smoke tests.",
                "project_type": "alternatives_review",
                "inputs": [
                    {
                        "path": "inputs/project.kmz",
                        "role": role,
                        "description": "Project geometry",
                    }
                ],
                "assumptions": {"default_buffer_feet": 100, "input_crs": "EPSG:4326"},
                "special_reviewer_instructions": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": project_id,
                "sources": [
                    {
                        "source_id": "usfws_nwi_wetlands",
                        "enabled": False,
                        "access_method": "local_file",
                        "path": "layers/usfws_nwi_wetlands/usfws_nwi_wetlands.geojson",
                        "role": "context",
                        "status": "candidate",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project_dir


def test_line_workspace_ingests_expected_input(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path, project_id="line_project", kmz=route_kmz())

    summary = inspect_project(project_dir)

    assert summary["project_id"] == "line_project"
    assert summary["inputs"][0]["feature_count"] == 2
    assert summary["inputs"][0]["geometry_type_counts"] == {"LineString": 2}
    assert summary["inputs"][0]["validation_issues"] == []


def test_point_workspace_ingests_expected_input(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path, project_id="point_project", kmz=point_kmz())

    summary = inspect_project(project_dir)

    assert summary["project_id"] == "point_project"
    assert summary["inputs"][0]["feature_count"] == 2
    assert summary["inputs"][0]["geometry_type_counts"] == {"Point": 2}
    assert summary["inputs"][0]["validation_issues"] == []


def test_project_source_registry_only_references_catalog_sources(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path, project_id="registry_project", kmz=route_kmz())
    catalog = load_source_catalog()
    catalog_source_ids = set(catalog.sources)

    registry = load_project_source_registry(project_dir)
    registry_source_ids = {source.source_id for source in registry.sources}

    assert registry_source_ids <= catalog_source_ids
    assert registry_source_ids == {"usfws_nwi_wetlands"}


def test_project_workspace_populate_for_review(tmp_path: Path) -> None:
    for project_id, kmz, expected_geometry_role in (
        ("line_project", route_kmz(), "line_corridor"),
        ("point_project", point_kmz(), "point_site"),
    ):
        project_dir = write_project(tmp_path, project_id=project_id, kmz=kmz)

        result = populate_for_review(project_dir, gpt_drafting=False)
        queue = load_review_queue(project_dir)
        item_types = {item["type"] for item in queue["items"]}

        assert result["status"] == "completed"
        assert all(
            warning.get("stage") in {"project_area", "deliverable_figures", "deliverable_items", "evidence_package"}
            for warning in result["warnings"]
        )
        assert result["artifact_paths"]["input_package"].endswith("input_package.json")
        assert result["artifact_paths"]["project_area"].endswith("project_area.json")
        assert result["artifact_paths"]["constraint_results"].endswith("constraint_results.json")
        assert result["artifact_paths"]["deliverable_figures"].endswith("figures.json")
        assert result["artifact_paths"]["deliverable_items"].endswith("deliverable_items.json")
        assert result["deliverable_figure_count"] == 15
        assert result["deliverable_item_count"] > 0
        assert "project_county_names" in result
        assert "basemap_rendering_status" in result
        assert json.loads(Path(result["artifact_paths"]["project_geometry"]).read_text(encoding="utf-8"))["geometry_role"] == expected_geometry_role
        assert queue["item_count"] == result["review_queue_item_count"]
        assert {"section_text", "table", "figure", "attachment"} <= item_types
        assert not {"draft_finding", "comparison_table", "map_figure", "report_section"}.intersection(item_types)
        assert "source_inventory_note" not in item_types
        assert Path(result["artifact_paths"]["review_queue"]).exists()
        assert json.loads(Path(result["output_path"]).read_text(encoding="utf-8"))["status"] == "completed"
