from __future__ import annotations

from pathlib import Path

import pytest

from review_assist.export_report import export_report
from review_assist.populate_for_review import populate_for_review
from review_assist.review_queue import generate_review_queue, load_review_queue
from review_assist.web.app import create_app

from test_deliverable_compactness import _write_large_deliverable_table
from test_export_report import set_review_states, write_project


@pytest.fixture
def app_client(tmp_path: Path):
    app = create_app(project_root=tmp_path, testing=True)
    return app.test_client()


def _select_project(client) -> None:
    response = client.post("/projects/select", data={"project_key": "project"}, follow_redirects=True)
    assert response.status_code == 200


def _populated_project(tmp_path: Path) -> Path:
    project_dir = write_project(tmp_path)
    populate_for_review(project_dir)
    return project_dir


def test_app_loads_with_no_selected_project_empty_state(app_client) -> None:
    response = app_client.get("/overview")

    assert response.status_code == 200
    assert b"Select an existing project workspace" in response.data
    assert b"Go to Projects" in response.data


def test_project_list_and_select(tmp_path: Path) -> None:
    write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()

    response = client.get("/projects")
    assert response.status_code == 200
    assert b"Test Project" in response.data

    response = client.post("/projects/select", data={"project_key": "project"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Overview" in response.data
    assert b"Test Project" in response.data


def test_project_selection_rejects_traversal(tmp_path: Path) -> None:
    write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()

    response = client.post("/projects/select", data={"project_key": "../project"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid project id" in response.data
    with client.session_transaction() as session:
        assert "project_key" not in session


def test_overview_displays_project_populate_and_source_status(tmp_path: Path) -> None:
    _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/overview")

    assert response.status_code == 200
    text = response.data.decode()
    assert "Test Project" in text
    assert "Create Review Queue" in text
    assert "Source Status" in text
    assert "Review Items" in text


def test_review_queue_default_uses_bounded_items_and_excludes_legacy_types(tmp_path: Path) -> None:
    _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review")
    text = response.data.decode()

    assert response.status_code == 200
    assert "deliverable_items" in text
    assert "draft_finding" not in text
    assert "spatial_relationship" not in text
    assert "source_inventory_note" not in text
    assert "comparison_table" not in text


def test_review_page_rejects_legacy_audit_queue_by_default(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    generate_review_queue(project_dir, include_legacy_artifacts=True)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review")
    text = response.data.decode()

    assert response.status_code == 200
    assert "standard UI requires the matrix-bounded deliverable review queue" in text
    assert "draft_finding" not in text
    assert "spatial_relationship" not in text
    assert "source_inventory_note" not in text


def test_review_detail_displays_previews_not_full_table_rows(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    _write_large_deliverable_table(project_dir, row_count=60)
    from review_assist.deliverable_items import generate_deliverable_items

    generate_deliverable_items(project_dir, gpt_drafting=False)
    generate_review_queue(project_dir)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/table-wetlands-waterbodies")
    text = response.data.decode()

    assert response.status_code == 200
    assert "Table Preview" in text
    assert "Alternative 004" in text
    assert "Alternative 059" not in text
    assert "full table detail remains in the deliverable table artifact" in text


def test_review_action_persists_through_backend_update(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.post(
        "/review/wetlands-and-waterbodies",
        data={"status": "accepted", "note": "Reviewed in web UI."},
        follow_redirects=True,
    )
    queue = load_review_queue(project_dir)
    item = next(item for item in queue["items"] if item["id"] == "wetlands-and-waterbodies")

    assert response.status_code == 200
    assert item["status"] == "accepted"
    assert item["export_eligible"] is True
    assert item["reviewer_notes"][-1]["note"] == "Reviewed in web UI."


def test_export_readiness_disabled_until_gate_passes_then_enabled(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    blocked = client.get("/export")
    assert blocked.status_code == 200
    blocked_text = blocked.data.decode()
    assert "Export Blockers" in blocked_text
    assert "Create Reviewed Export</button>" in blocked_text
    assert "disabled" in blocked_text

    set_review_states(project_dir)
    ready = client.get("/export")
    ready_text = ready.data.decode()
    assert ready.status_code == 200
    assert "Reviewed export is ready" in ready_text
    assert "disabled" not in ready_text.split("Create Reviewed Export")[1].split("</form>")[0]


def test_preview_export_shows_compactness_and_final_verification(tmp_path: Path) -> None:
    _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.post("/export/preview", follow_redirects=True)
    text = response.data.decode()

    assert response.status_code == 200
    assert "Internal preview export created" in text
    assert "Compactness Budget" in text
    assert "Final Verification" in text
    assert "preview_bypassed" in text


def test_outputs_expose_manifest_artifacts_without_path_traversal(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    set_review_states(project_dir)
    manifest = export_report(project_dir, output_format="both")
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    outputs = client.get("/outputs")
    assert outputs.status_code == 200
    assert b"environmental_constraints_report.md" in outputs.data
    assert b"environmental_constraints_report.docx" in outputs.data

    relative_markdown = Path(manifest["markdown_path"]).resolve().relative_to(project_dir.resolve()).as_posix()
    ok = client.get(f"/artifact?project=project&path={relative_markdown}")
    assert ok.status_code == 200

    traversal = client.get("/artifact?project=project&path=../README.md")
    assert traversal.status_code == 404

    bad_project = client.get(f"/artifact?project=..&path={relative_markdown}")
    assert bad_project.status_code == 404
