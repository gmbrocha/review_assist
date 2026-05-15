from __future__ import annotations

import json
from pathlib import Path

from review_assist.inspection import inspect_project
from review_assist.populate_for_review import populate_for_review
from review_assist.review_queue import load_review_queue
from review_assist.source_catalog import load_project_source_registry, load_source_catalog


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO_ROOT / "projects"


def test_trails_workspace_ingests_expected_input() -> None:
    summary = inspect_project(PROJECTS_DIR / "trails")

    assert summary["project_id"] == "trails"
    assert summary["inputs"][0]["feature_count"] == 323
    assert summary["inputs"][0]["geometry_type_counts"] == {"LineString": 323}
    assert summary["inputs"][0]["validation_issues"] == []


def test_conexon_workspace_ingests_expected_input_with_known_validation_items() -> None:
    summary = inspect_project(PROJECTS_DIR / "conexon_projects")
    issue_codes = [issue["code"] for issue in summary["inputs"][0]["validation_issues"]]

    assert summary["project_id"] == "conexon_projects"
    assert summary["inputs"][0]["feature_count"] == 13282
    assert summary["inputs"][0]["geometry_type_counts"] == {"Point": 13282}
    assert issue_codes == ["blank_placemark_name", "all_feature_names_blank"]


def test_active_project_source_registries_only_reference_catalog_sources() -> None:
    catalog = load_source_catalog()
    catalog_source_ids = set(catalog.sources)

    for project_dir in (PROJECTS_DIR / "trails", PROJECTS_DIR / "conexon_projects"):
        registry = load_project_source_registry(project_dir)
        registry_source_ids = {source.source_id for source in registry.sources}

        assert registry_source_ids <= catalog_source_ids
        assert registry_source_ids


def test_active_projects_populate_for_review_without_warnings() -> None:
    for project_dir, expected_geometry_role in (
        (PROJECTS_DIR / "trails", "line_corridor"),
        (PROJECTS_DIR / "conexon_projects", "point_site"),
    ):
        result = populate_for_review(project_dir)
        queue = load_review_queue(project_dir)
        item_types = {item["type"] for item in queue["items"]}

        assert result["status"] == "completed"
        assert result["warnings"] == []
        assert result["artifact_paths"]["constraint_results"].endswith("constraint_results.json")
        assert json.loads(Path(result["artifact_paths"]["project_geometry"]).read_text(encoding="utf-8"))["geometry_role"] == expected_geometry_role
        assert queue["item_count"] == result["review_queue_item_count"]
        assert {"draft_finding", "comparison_table", "map_figure", "report_section"} <= item_types
        assert "source_inventory_note" not in item_types
        assert Path(result["artifact_paths"]["review_queue"]).exists()
        assert json.loads(Path(result["output_path"]).read_text(encoding="utf-8"))["status"] == "completed"
