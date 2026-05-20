from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from review_assist.export_report import export_report
from review_assist.populate_for_review import populate_for_review
from review_assist.projects import load_project_manifest
from review_assist.review_queue import generate_review_queue, load_review_queue
from review_assist.web import adapter
from review_assist.web.app import create_app

from test_deliverable_compactness import _write_large_deliverable_table
from test_export_report import kml_document, kmz_bytes, set_review_states, write_project, write_tiny_png


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


def _valid_kmz_upload() -> io.BytesIO:
    kml = kml_document(
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """
    )
    return io.BytesIO(kmz_bytes(kml))


def _tiny_png_upload(tmp_path: Path) -> io.BytesIO:
    path = tmp_path / "tiny.png"
    write_tiny_png(path)
    return io.BytesIO(path.read_bytes())


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


def test_safe_draft_project_creation_succeeds_without_manifest(tmp_path: Path) -> None:
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()

    response = client.post(
        "/projects/create",
        data={"project_id": "fresh_project", "name": "Fresh Project", "description": "New local review"},
        follow_redirects=True,
    )
    project_dir = tmp_path / "fresh_project"

    assert response.status_code == 200
    assert b"Project Setup" in response.data
    assert (project_dir / "config" / "project_draft.json").exists()
    assert (project_dir / "staging" / "uploads").is_dir()
    assert (project_dir / "inputs").is_dir()
    assert not (project_dir / "config" / "project.json").exists()
    with client.session_transaction() as session:
        assert session["project_key"] == "fresh_project"


def test_invalid_project_names_and_duplicates_are_rejected(tmp_path: Path) -> None:
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()

    bad = client.post(
        "/projects/create",
        data={"project_id": "../bad", "name": "Bad"},
        follow_redirects=True,
    )
    assert bad.status_code == 200
    assert b"Project id" in bad.data
    assert not (tmp_path / "bad").exists()

    trailing_dot = client.post(
        "/projects/create",
        data={"project_id": "bad.", "name": "Bad"},
        follow_redirects=True,
    )
    assert trailing_dot.status_code == 200
    assert b"end with a dot" in trailing_dot.data
    assert not (tmp_path / "bad.").exists()

    first = client.post(
        "/projects/create",
        data={"project_id": "fresh_project", "name": "Fresh Project"},
        follow_redirects=True,
    )
    duplicate = client.post(
        "/projects/create",
        data={"project_id": "fresh_project", "name": "Fresh Project Again"},
        follow_redirects=True,
    )
    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert b"already exists" in duplicate.data


def test_project_selection_rejects_traversal(tmp_path: Path) -> None:
    write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()

    response = client.post("/projects/select", data={"project_key": "../project"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid project id" in response.data
    with client.session_transaction() as session:
        assert "project_key" not in session


def test_upload_staging_saves_inside_project_and_rejects_traversal(tmp_path: Path) -> None:
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    client.post("/projects/create", data={"project_id": "fresh_project", "name": "Fresh Project"}, follow_redirects=True)

    response = client.post(
        "/setup/upload",
        data={"files": (_valid_kmz_upload(), "routes.kmz")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    staged_path = tmp_path / "fresh_project" / "staging" / "uploads" / "routes.kmz"

    assert response.status_code == 200
    assert staged_path.exists()
    assert staged_path.resolve().is_relative_to((tmp_path / "fresh_project").resolve())
    assert b"routes.kmz" in response.data

    traversal = client.post(
        "/setup/upload",
        data={"files": (io.BytesIO(b"bad"), "../escape.kmz")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert traversal.status_code == 200
    assert b"path separators" in traversal.data
    assert not (tmp_path / "escape.kmz").exists()


def test_duplicate_upload_behavior_is_explicit(tmp_path: Path) -> None:
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    client.post("/projects/create", data={"project_id": "fresh_project", "name": "Fresh Project"}, follow_redirects=True)
    client.post(
        "/setup/upload",
        data={"files": (_valid_kmz_upload(), "routes.kmz")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    duplicate = client.post(
        "/setup/upload",
        data={"files": (_valid_kmz_upload(), "routes.kmz")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert duplicate.status_code == 200
    assert b"already exists in staging" in duplicate.data


def test_commit_staged_inputs_creates_valid_manifest_and_classification(tmp_path: Path) -> None:
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    client.post("/projects/create", data={"project_id": "fresh_project", "name": "Fresh Project"}, follow_redirects=True)
    client.post(
        "/setup/upload",
        data={"files": (_valid_kmz_upload(), "routes.kmz")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    response = client.post("/setup/commit", follow_redirects=True)
    project_dir = tmp_path / "fresh_project"
    manifest = load_project_manifest(project_dir)
    input_package = json.loads((project_dir / "context" / "input_package.json").read_text(encoding="utf-8"))

    assert response.status_code == 200
    text = response.data.decode()
    assert b"Committed 1 input" in response.data
    assert "Latest Run Status" in text
    assert "classify_inputs" in text
    assert "Committed Inputs" in text
    assert "inputs/routes.kmz" in text
    assert "project_geometry" in text
    assert "Classification Summary" in text
    assert manifest.project_id == "fresh_project"
    assert manifest.inputs[0].path == "inputs/routes.kmz"
    assert (project_dir / "inputs" / "routes.kmz").exists()
    assert not (project_dir / "staging" / "uploads" / "routes.kmz").exists()
    assert input_package["required_kmz_present"] is True


def test_classification_route_calls_adapter_service(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    called: dict[str, Path] = {}

    def fake_classify(path: Path) -> dict[str, object]:
        called["path"] = path
        return {"input_count": 1, "output_path": str(project_dir / "context" / "input_package.json")}

    monkeypatch.setattr(adapter, "classify_project_inputs", fake_classify)

    response = client.post("/setup/classify", follow_redirects=True)

    assert response.status_code == 200
    assert called["path"] == project_dir.resolve()
    assert b"Input classification completed" in response.data


def test_missing_required_input_and_populate_failure_are_user_visible_without_traceback(tmp_path: Path) -> None:
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    client.post("/projects/create", data={"project_id": "fresh_project", "name": "Fresh Project"}, follow_redirects=True)

    setup = client.get("/setup")
    assert setup.status_code == 200
    assert b"staged_input_missing" in setup.data
    assert b"config/project.json" in setup.data

    response = client.post("/overview/populate", follow_redirects=True)
    status_path = tmp_path / "fresh_project" / "web_runs" / "latest_run.json"
    latest_run = json.loads(status_path.read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert b"Latest Run Status" in response.data
    assert b"failed" in response.data
    assert b"Traceback" not in response.data
    assert latest_run["action"] == "populate_for_review"
    assert latest_run["status"] == "failed"


def test_overview_displays_workflow_readiness_ladder_and_setup_blockers(tmp_path: Path) -> None:
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    client.post("/projects/create", data={"project_id": "fresh_project", "name": "Fresh Project"}, follow_redirects=True)

    draft = client.get("/overview")
    draft_text = draft.data.decode()

    assert draft.status_code == 200
    assert "Workflow Readiness" in draft_text
    assert "Project Manifest" in draft_text
    assert "Input Classification" in draft_text
    assert "Project Area" in draft_text
    assert "Standard Review Queue" in draft_text
    assert "Draft workspace only" in draft_text
    assert 'disabled>Create Review Queue' in draft_text

    client.post(
        "/setup/upload",
        data={"files": (_valid_kmz_upload(), "routes.kmz")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    client.post("/setup/commit", follow_redirects=True)
    committed = client.get("/overview")
    committed_text = committed.data.decode()

    assert committed.status_code == 200
    assert "1 input(s), 1 project geometry input(s)" in committed_text
    assert "Run Create Review Queue after setup blockers are cleared" in committed_text
    assert 'disabled>Create Review Queue' not in committed_text


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


def test_figure_review_detail_uses_figure_specific_form(tmp_path: Path) -> None:
    _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/figure-wetlands-waterbodies")
    text = response.data.decode()

    assert response.status_code == 200
    assert "Proposed Export Figure" in text
    assert "Edited Caption" in text
    assert "Upload New Figure" in text
    assert "Accept Final" in text
    assert "Edited content" not in text
    assert "Replacement content" not in text
    assert "Export eligible when unable to verify" not in text


def test_non_figure_review_detail_keeps_generic_review_form(tmp_path: Path) -> None:
    _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/wetlands-and-waterbodies")
    text = response.data.decode()

    assert response.status_code == 200
    assert "Reviewed Content Candidate" in text
    assert "Edited content" in text
    assert "Replacement content" in text
    assert "Upload New Figure" not in text


def test_figure_review_accepts_edited_caption_only(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.post(
        "/review/figure-wetlands-waterbodies",
        data={"form_kind": "figure_review", "caption": "Edited final figure caption."},
        follow_redirects=True,
    )
    queue = load_review_queue(project_dir)
    item = next(item for item in queue["items"] if item["id"] == "figure-wetlands-waterbodies")

    assert response.status_code == 200
    assert item["status"] == "edited"
    assert item["export_eligible"] is True
    assert item["edited_content"] == "Edited final figure caption."
    assert item["caption"] == "Edited final figure caption."
    assert item["figure_review"]["caption_source"] == "edited_caption"


def test_figure_review_accepts_generated_caption_and_figure(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    queue = load_review_queue(project_dir)
    existing = next(item for item in queue["items"] if item["id"] == "figure-wetlands-waterbodies")
    generated_caption = existing["assumptions"]["caption"]
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.post(
        "/review/figure-wetlands-waterbodies",
        data={"form_kind": "figure_review", "caption": generated_caption},
        follow_redirects=True,
    )
    updated = next(item for item in load_review_queue(project_dir)["items"] if item["id"] == "figure-wetlands-waterbodies")

    assert response.status_code == 200
    assert updated["status"] == "accepted"
    assert updated["export_eligible"] is True
    assert updated["edited_content"] == ""
    assert updated["replacement_content"] == ""
    assert updated["caption"] == generated_caption
    assert updated["figure_review"]["caption_source"] == "generated_caption"


def test_figure_review_replacement_upload_saves_inside_project(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.post(
        "/review/figure-wetlands-waterbodies",
        data={
            "form_kind": "figure_review",
            "caption": "Replacement figure caption.",
            "replacement_figure": (_tiny_png_upload(tmp_path), "replacement.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    queue = load_review_queue(project_dir)
    item = next(item for item in queue["items"] if item["id"] == "figure-wetlands-waterbodies")
    replacement_path = project_dir / item["replacement_content"]

    assert response.status_code == 200
    assert item["status"] == "replaced"
    assert item["export_eligible"] is True
    assert item["image_path"] == item["replacement_content"]
    assert item["figure_review"]["image_source"] == "replacement_figure"
    assert replacement_path.exists()
    assert replacement_path.resolve().is_relative_to(project_dir.resolve())


def test_figure_review_replacement_upload_reuses_generated_caption(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    queue = load_review_queue(project_dir)
    existing = next(item for item in queue["items"] if item["id"] == "figure-wetlands-waterbodies")
    generated_caption = existing["assumptions"]["caption"]
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.post(
        "/review/figure-wetlands-waterbodies",
        data={
            "form_kind": "figure_review",
            "caption": generated_caption,
            "replacement_figure": (_tiny_png_upload(tmp_path), "replacement.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    item = next(item for item in load_review_queue(project_dir)["items"] if item["id"] == "figure-wetlands-waterbodies")

    assert response.status_code == 200
    assert item["status"] == "replaced"
    assert item["edited_content"] == ""
    assert item["caption"] == generated_caption
    assert item["figure_review"]["caption_source"] == "generated_caption"
    assert item["figure_review"]["image_source"] == "replacement_figure"


def test_figure_review_rejects_unsafe_replacement_upload_names(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.post(
        "/review/figure-wetlands-waterbodies",
        data={
            "form_kind": "figure_review",
            "caption": "Unsafe replacement caption.",
            "replacement_figure": (io.BytesIO(b"bad"), "../escape.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    queue = load_review_queue(project_dir)
    item = next(item for item in queue["items"] if item["id"] == "figure-wetlands-waterbodies")

    assert response.status_code == 200
    assert b"path separators" in response.data
    assert item["status"] != "replaced"
    assert not (tmp_path / "escape.png").exists()


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
    assert "Latest Run Status" in text
    assert "preview_export" in text
    assert "Started" in text
    assert "Completed" in text
    assert "Artifact" in text
    assert "Traceback" not in text


def test_reviewed_export_failure_and_success_status_without_traceback(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    failed = client.post("/export/reviewed", follow_redirects=True)
    failed_text = failed.data.decode()
    failed_status = json.loads((project_dir / "web_runs" / "latest_run.json").read_text(encoding="utf-8"))
    assert failed.status_code == 200
    assert "Export is blocked" in failed_text
    assert "Traceback" not in failed_text
    assert failed_status["action"] == "reviewed_export"
    assert failed_status["status"] == "failed"

    set_review_states(project_dir)
    succeeded = client.post("/export/reviewed", follow_redirects=True)
    success_status = json.loads((project_dir / "web_runs" / "latest_run.json").read_text(encoding="utf-8"))
    assert succeeded.status_code == 200
    assert "Reviewed export created" in succeeded.data.decode()
    assert success_status["action"] == "reviewed_export"
    assert success_status["status"] == "completed"


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


def test_fresh_project_flow_reaches_standard_bounded_review_queue(tmp_path: Path) -> None:
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    client.post("/projects/create", data={"project_id": "fresh_project", "name": "Fresh Project"}, follow_redirects=True)
    client.post(
        "/setup/upload",
        data={"files": (_valid_kmz_upload(), "routes.kmz")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    client.post("/setup/commit", follow_redirects=True)
    populated = client.post("/overview/populate", follow_redirects=True)
    review = client.get("/review")
    review_text = review.data.decode()

    assert populated.status_code == 200
    assert b"Create Review Queue completed" in populated.data
    assert review.status_code == 200
    assert "deliverable_items" in review_text
    assert "draft_finding" not in review_text
    assert "spatial_relationship" not in review_text
    assert "source_inventory_note" not in review_text


def test_create_review_queue_ui_requests_local_source_materialization(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    called: dict[str, object] = {}

    def fake_populate(path: Path, **kwargs: object) -> dict[str, object]:
        called["path"] = path
        called.update(kwargs)
        return {"review_queue_item_count": 1, "output_path": str(project_dir / "populate_for_review" / "populate_for_review_run.json")}

    monkeypatch.setattr(adapter, "populate_for_review", fake_populate)

    response = client.post("/overview/populate", follow_redirects=True)

    assert response.status_code == 200
    assert called["path"] == project_dir.resolve()
    assert called["materialize_local_sources"] is True
    assert called["gpt_drafting"] is False
