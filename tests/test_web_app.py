from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from review_assist.export_report import export_report
from review_assist.figure_style_model import FIGURE_STYLE_OVERRIDES_PATH, FIGURE_VERSIONS_PATH, active_style_override
from review_assist.gpt_interpretive_assist import draft_section_candidates
from review_assist.populate_for_review import populate_for_review
from review_assist.projects import load_project_manifest
from review_assist.review_queue import generate_review_queue, load_review_queue
from review_assist.web import adapter
from review_assist.web.app import create_app

from test_deliverable_compactness import _write_large_deliverable_table
from test_export_report import add_supported_real_source_inputs, kml_document, kmz_bytes, set_review_states, write_project, write_tiny_png


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


def _project_with_figure_layers(tmp_path: Path) -> Path:
    project_dir = write_project(tmp_path)
    add_supported_real_source_inputs(project_dir)
    populate_for_review(project_dir, prepare_sources=True, gpt_drafting=False)
    return project_dir


def _safe_gpt_ui_response(*, model: str, payload: dict, schema: dict) -> dict:
    return {
        "draft_content": "GPT-assisted wetlands text remains a review candidate.",
        "cited_finding_ids": [],
        "cited_table_ids": payload["related_ids"]["table_ids"][:1],
        "cited_figure_ids": payload["related_ids"]["figure_ids"][:1],
        "cited_source_refs": payload["related_ids"]["source_refs"][:1],
        "caveats": payload["section_policy"]["required_caveats"],
        "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    }


def _rejected_gpt_ui_response(*, model: str, payload: dict, schema: dict) -> dict:
    return {
        "draft_content": "According to the style context, this section is supported by example report evidence.",
        "cited_finding_ids": [],
        "cited_table_ids": [],
        "cited_figure_ids": [],
        "cited_source_refs": ["style_context"],
        "caveats": payload["section_policy"]["required_caveats"],
        "usage": {"input_tokens": 9, "output_tokens": 4, "total_tokens": 13},
    }


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


def test_package_data_includes_web_javascript_assets() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '"web/static/*.js"' in pyproject


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

    sid_upload = client.post(
        "/setup/upload",
        data={"files": (io.BytesIO(b"sid"), "county_naip.sid")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert sid_upload.status_code == 200
    assert b"Unsupported upload type" in sid_upload.data
    assert b".sid" in sid_upload.data
    assert not (tmp_path / "fresh_project" / "staging" / "uploads" / "county_naip.sid").exists()


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


def test_overview_displays_structured_validation_issue_details(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    project_area_path = project_dir / "context" / "project_area.json"
    project_area = json.loads(project_area_path.read_text(encoding="utf-8"))
    project_area["validation_issues"] = [
        {
            "severity": "warning",
            "code": "county_source_disagreement",
            "message": "County detection sources disagree.",
            "details": {
                "summary": "Selected counties: Test County. Alternate detections: naip_maris_metadata_extent: Adjacent County, Test County.",
            },
        }
    ]
    project_area_path.write_text(json.dumps(project_area, indent=2) + "\n", encoding="utf-8")
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/overview")
    text = response.data.decode()

    assert response.status_code == 200
    assert "County detection sources disagree." in text
    assert "Selected counties: Test County" in text
    assert "Adjacent County" in text


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
    assert "Report Role" in text
    assert "Report body" in text
    assert ">Render<" not in text
    assert "include_body" not in text


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


def test_review_detail_reads_canonical_queue_source_refs(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    queue_path = project_dir / "review_queue" / "review_queue.json"
    legacy_queue_path = project_dir / "review_queue.json"
    queue = load_review_queue(project_dir)
    item = next(item for item in queue["items"] if item["id"] == "water-quality")
    item["source_refs"] = ["mdeq_303d_impaired_waters", "usgs_nhd_flowlines", "usgs_nhd_waterbodies", "usgs_nhd_other_areas"]
    item["generated_content"] = "Water quality review candidate."
    item["validation_issues"] = []
    item["uncertainty_flags"] = []
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    stale_queue = dict(queue)
    stale_queue["items"] = [dict(row) for row in queue["items"]]
    next(row for row in stale_queue["items"] if row["id"] == "water-quality")["source_refs"] = ["usgs_nhd_hydrography"]
    legacy_queue_path.write_text(json.dumps(stale_queue, indent=2) + "\n", encoding="utf-8")
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/water-quality")
    text = response.data.decode()

    assert response.status_code == 200
    assert "mdeq_303d_impaired_waters" in text
    assert "usgs_nhd_flowlines" in text
    assert "usgs_nhd_waterbodies" in text
    assert "usgs_nhd_other_areas" in text
    assert "usgs_nhd_hydrography" not in text


def test_review_detail_shows_full_generated_content_without_preview_truncation(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    queue_path = project_dir / "review_queue" / "review_queue.json"
    queue = load_review_queue(project_dir)
    long_content = (
        "Wetlands and Waterbodies section rollup.\n\n"
        + "Planning considerations for mapped wetlands and waterbodies remain reviewable in the web UI. " * 35
        + "\n\nFinal sentence remains visible for reviewer acceptance."
    )
    item = next(item for item in queue["items"] if item["id"] == "wetlands-and-waterbodies")
    item["generated_content"] = long_content
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/wetlands-and-waterbodies")
    text = response.data.decode()

    assert response.status_code == 200
    assert "Wetlands and Waterbodies section rollup." in text
    assert "Final sentence remains visible for reviewer acceptance." in text
    assert "Preview limited in web UI" not in text


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
    assert "Open Figure Style Editor" in text
    assert "Edited content" not in text
    assert "Replacement content" not in text
    assert "Export eligible when unable to verify" not in text


def test_review_figure_preview_css_uses_larger_review_only_display_scale() -> None:
    styles = Path("src/review_assist/web/static/styles.css").read_text(encoding="utf-8")
    preview_block = styles.split(".figure-preview {", 1)[1].split("}", 1)[0]

    assert "width: 100%;" in preview_block
    assert "max-width: 1120px;" in preview_block
    assert "max-height: 78vh;" in preview_block
    assert "height: auto;" in preview_block


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
    assert "Open Figure Style Editor" not in text


def test_figure_style_editor_renders_for_figure_items(tmp_path: Path) -> None:
    _project_with_figure_layers(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/figure-wetlands-waterbodies/figure-style")
    text = response.data.decode()

    assert response.status_code == 200
    assert "Figure Style Editor" in text
    assert "Current Figure Preview" in text
    assert "Review Context" in text
    assert "Source Refs" in text
    assert "Evidence Refs" in text
    assert "Basemap And Render Status" in text
    assert "Validation Warnings" in text
    assert "No validation warnings recorded for this figure." in text
    assert "Saved style drafts and regenerated versions are project-local presentation metadata" in text
    assert "Export Eligible" in text
    assert "Version History" in text
    assert "Layer Styling" in text
    assert "figure_style_editor.js" in text
    assert "data-color-control" in text
    assert "data-color-picker" in text
    assert 'type="color"' in text
    assert "color-swatch" in text
    assert "Color preview" in text
    assert "Use #RRGGBB or leave blank for default." in text
    assert "comparison_units:" in text
    assert "National Wetlands Inventory" in text
    assert 'value="basemap' not in text
    assert "name=\"layer_0_visible\"" in text
    assert "name=\"layer_0_z_index\"" in text
    assert "name=\"layer_0_display_name\"" in text
    assert "name=\"layer_0_fill_color\"" in text
    assert "name=\"layer_0_fill_opacity\"" in text
    assert "name=\"layer_0_stroke_color\"" in text
    assert "name=\"layer_0_stroke_width\"" in text
    assert "name=\"layer_0_point_size\"" in text
    assert "name=\"layer_0_label_visible\"" in text
    assert "name=\"layer_0_label_field\"" in text
    assert 'step="0.01" name="layer_0_fill_opacity"' in text
    assert 'step="0.01" name="layer_0_stroke_width"' in text
    assert 'step="0.01" name="layer_0_point_size"' in text
    assert "Save and Regenerate Figure" in text
    assert 'name="style_action" value="save_and_regenerate"' in text
    assert "Approve Figure" in text
    assert "geometry editing" not in text.lower()


def test_figure_style_editor_rejects_non_figure_items(tmp_path: Path) -> None:
    _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/wetlands-and-waterbodies/figure-style")

    assert response.status_code == 404


def test_figure_style_editor_save_draft_creates_sparse_override(tmp_path: Path) -> None:
    project_dir = _project_with_figure_layers(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    queue_before = (project_dir / "review_queue" / "review_queue.json").read_bytes()
    figures_before = (project_dir / "deliverable" / "figures.json").read_bytes()

    response = client.post(
        "/review/figure-wetlands-waterbodies/figure-style",
        data={
            "style_action": "save_draft",
                "layer_id": ["comparison_units:comparison-unit-00001", "source:usfws_nwi_wetlands"],
                "layer_0_visible": "true",
                "layer_0_z_index": "0",
                "layer_0_display_name": "Comparison 1",
                "layer_0_stroke_color": "#22C55E",
                "layer_1_visible": "true",
                "layer_1_z_index": "1",
                "layer_1_display_name": "National Wetlands Inventory",
                "layer_1_stroke_color": "#00AAFF",
            },
            follow_redirects=True,
        )
    artifact = json.loads((project_dir / FIGURE_STYLE_OVERRIDES_PATH).read_text(encoding="utf-8"))
    active = active_style_override(artifact, "figure-wetlands-waterbodies")

    assert response.status_code == 200
    assert "Draft figure style saved" in response.data.decode()
    assert active is not None
    assert active["overrides"] == [
        {"layer_id": "comparison_units:comparison-unit-00001", "display_name": "Comparison 1", "stroke_color": "#22C55E"},
        {"layer_id": "source:usfws_nwi_wetlands", "stroke_color": "#00AAFF"},
    ]
    assert (project_dir / "review_queue" / "review_queue.json").read_bytes() == queue_before
    assert (project_dir / "deliverable" / "figures.json").read_bytes() == figures_before


def test_figure_style_editor_reset_marks_active_override_reset(tmp_path: Path) -> None:
    project_dir = _project_with_figure_layers(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    client.post(
        "/review/figure-wetlands-waterbodies/figure-style",
        data={
            "style_action": "save_draft",
            "layer_id": ["source:usfws_nwi_wetlands"],
            "layer_0_visible": "true",
            "layer_0_z_index": "1",
            "layer_0_display_name": "National Wetlands Inventory",
            "layer_0_stroke_color": "#00AAFF",
        },
        follow_redirects=True,
    )

    response = client.post(
        "/review/figure-wetlands-waterbodies/figure-style",
        data={"style_action": "reset_default"},
        follow_redirects=True,
    )
    artifact = json.loads((project_dir / FIGURE_STYLE_OVERRIDES_PATH).read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert "Figure style reset to default" in response.data.decode()
    assert active_style_override(artifact, "figure-wetlands-waterbodies") is None
    assert artifact["overrides"][0]["status"] == "reset"


def test_figure_style_editor_save_and_regenerate_creates_review_only_version(tmp_path: Path) -> None:
    project_dir = _project_with_figure_layers(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    queue_before = (project_dir / "review_queue" / "review_queue.json").read_bytes()
    figures_before = (project_dir / "deliverable" / "figures.json").read_bytes()

    response = client.post(
        "/review/figure-wetlands-waterbodies/figure-style",
        data={
            "style_action": "save_and_regenerate",
            "layer_id": ["comparison_units:comparison-unit-00001", "source:usfws_nwi_wetlands"],
            "layer_0_visible": "true",
            "layer_0_z_index": "0",
            "layer_0_display_name": "Comparison 1",
            "layer_1_visible": "true",
            "layer_1_z_index": "8",
            "layer_1_display_name": "Wetland Overlay",
            "layer_1_stroke_color": "#00AAFF",
        },
        follow_redirects=True,
    )
    versions = json.loads((project_dir / FIGURE_VERSIONS_PATH).read_text(encoding="utf-8"))
    latest = versions["versions"][-1]
    text = response.data.decode()

    assert response.status_code == 200
    assert "Review-only regenerated figure version created" in text
    assert "Latest Regenerated Version" in text
    assert latest["approval_state"] == "regenerated"
    assert latest["export_active"] is False
    assert (project_dir / latest["output_artifact_path"]).exists()
    assert (project_dir / "review_queue" / "review_queue.json").read_bytes() == queue_before
    assert (project_dir / "deliverable" / "figures.json").read_bytes() == figures_before


def test_figure_style_editor_approves_exact_version_without_review_or_export_mutation(tmp_path: Path) -> None:
    project_dir = _project_with_figure_layers(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    client.post(
        "/review/figure-wetlands-waterbodies/figure-style",
        data={
            "style_action": "save_and_regenerate",
            "layer_id": ["source:usfws_nwi_wetlands"],
            "layer_0_visible": "true",
            "layer_0_z_index": "8",
            "layer_0_display_name": "Wetland Overlay",
            "layer_0_stroke_color": "#00AAFF",
        },
        follow_redirects=True,
    )
    versions = json.loads((project_dir / FIGURE_VERSIONS_PATH).read_text(encoding="utf-8"))
    target_version_id = versions["versions"][-1]["version_id"]
    queue_before = (project_dir / "review_queue" / "review_queue.json").read_bytes()
    figures_before = (project_dir / "deliverable" / "figures.json").read_bytes()
    readiness_before = adapter.export_readiness(project_dir)

    response = client.post(
        "/review/figure-wetlands-waterbodies/figure-style",
        data={"style_action": "approve_version", "version_id": target_version_id},
        follow_redirects=True,
    )
    versions_after = json.loads((project_dir / FIGURE_VERSIONS_PATH).read_text(encoding="utf-8"))
    approved = next(item for item in versions_after["versions"] if item["version_id"] == target_version_id)
    text = response.data.decode()

    assert response.status_code == 200
    assert "Figure version approved" in text
    assert "Approved Figure Version" in text
    assert approved["approval_state"] == "approved"
    assert approved["approved_version"] is True
    assert approved["approved_by"] == "local_reviewer"
    assert (project_dir / "review_queue" / "review_queue.json").read_bytes() == queue_before
    assert (project_dir / "deliverable" / "figures.json").read_bytes() == figures_before
    assert adapter.export_readiness(project_dir)["review_gate_status"] == readiness_before["review_gate_status"]


def test_review_detail_displays_gpt_assist_provenance(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    add_supported_real_source_inputs(project_dir)
    populate_for_review(project_dir, prepare_sources=True, gpt_drafting=False)
    draft_section_candidates(
        project_dir,
        model="gpt-test",
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        response_create=_safe_gpt_ui_response,
    )
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/wetlands-and-waterbodies")
    text = response.data.decode()

    assert response.status_code == 200
    assert "GPT Assist Provenance" in text
    assert "GPT-assisted content remains a review candidate" in text
    assert "gpt-test" in text
    assert "15 total" in text
    assert "Evidence Hash" in text


def test_review_detail_displays_gpt_assist_fallback_reason(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    add_supported_real_source_inputs(project_dir)
    populate_for_review(project_dir, prepare_sources=True, gpt_drafting=False)
    draft_section_candidates(
        project_dir,
        model="gpt-test",
        sections=["wetlands-and-waterbodies"],
        max_calls=1,
        response_create=_rejected_gpt_ui_response,
    )
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/wetlands-and-waterbodies")
    text = response.data.decode()

    assert response.status_code == 200
    assert "GPT Assist Fallback" in text
    assert "deterministic source-backed content was retained" in text
    assert "gpt_output_rejected" in text
    assert "style_context_cited_as_evidence" in text
    assert "13 total" in text


def test_section_review_detail_displays_related_table_figure_and_evidence_refs(tmp_path: Path) -> None:
    _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/review/wetlands-and-waterbodies")
    text = response.data.decode()

    assert response.status_code == 200
    assert "table-wetlands-waterbodies" in text
    assert "figure-wetlands-waterbodies" in text
    assert "section_evidence:wetlands-and-waterbodies" in text
    assert "Report Role" in text
    assert "Report body" in text
    assert "<strong>include_body</strong>" not in text
    assert "<span>Table</span><strong>none</strong>" not in text
    assert "<span>Figure</span><strong>none</strong>" not in text


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


def test_figure_review_accepts_replacement_and_edited_caption(tmp_path: Path) -> None:
    project_dir = _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.post(
        "/review/figure-wetlands-waterbodies",
        data={
            "form_kind": "figure_review",
            "caption": "Edited replacement figure caption.",
            "replacement_figure": (_tiny_png_upload(tmp_path), "replacement.jpg"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    item = next(item for item in load_review_queue(project_dir)["items"] if item["id"] == "figure-wetlands-waterbodies")

    assert response.status_code == 200
    assert item["status"] == "replaced"
    assert item["export_eligible"] is True
    assert item["edited_content"] == "Edited replacement figure caption."
    assert item["caption"] == "Edited replacement figure caption."
    assert item["figure_review"]["caption_source"] == "edited_caption"
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


@pytest.mark.parametrize(
    ("filename", "message"),
    [
        (".hidden.png", "cannot be hidden"),
        ("replacement.gif", "Replacement figure must be one of"),
    ],
)
def test_figure_review_rejects_hidden_and_unsupported_replacement_uploads(tmp_path: Path, filename: str, message: str) -> None:
    project_dir = _populated_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.post(
        "/review/figure-wetlands-waterbodies",
        data={
            "form_kind": "figure_review",
            "caption": "Unsafe replacement caption.",
            "replacement_figure": (io.BytesIO(b"bad"), filename),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    item = next(item for item in load_review_queue(project_dir)["items"] if item["id"] == "figure-wetlands-waterbodies")

    assert response.status_code == 200
    assert message in response.data.decode()
    assert item["status"] != "replaced"


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
    assert called["materialize_naip_basemap"] is True
    assert called["gpt_drafting"] is False
    assert callable(called["progress_callback"])


def test_process_log_panel_and_api_capture_create_queue(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    def fake_populate(path: Path, **kwargs: object) -> dict[str, object]:
        progress = kwargs.get("progress_callback")
        assert callable(progress)
        progress({"event": "step_started", "step": "review_queue"})
        progress({"event": "step_completed", "step": "review_queue", "count": 1})
        return {"review_queue_item_count": 1, "deliverable_item_count": 1, "warnings": [], "output_path": ""}

    monkeypatch.setattr(adapter, "populate_for_review", fake_populate)

    overview = client.get("/overview")
    response = client.post("/overview/populate", follow_redirects=True)
    logs = client.get("/api/logs?tail=50")
    payload = logs.get_json()
    lines = "\n".join(payload["lines"])

    assert overview.status_code == 200
    assert b"Process Log" in overview.data
    assert b"process_log.js" in overview.data
    assert response.status_code == 200
    assert logs.status_code == 200
    assert payload["tail"] == 50
    assert b'id="process-log-resizer"' in overview.data
    assert b"Resize process log" in overview.data
    assert "create_queue started" in lines
    assert "create_queue review_queue complete" in lines
    assert "create_queue complete" in lines


def test_overview_exposes_dev_review_queue_reset_with_confirmation(tmp_path: Path) -> None:
    write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    overview = client.get("/overview")
    blocked = client.post("/overview/reset-review-queue", follow_redirects=True)

    assert overview.status_code == 200
    assert b"Refresh artifacts and rebuild queue" in overview.data
    assert b"refreshes deterministic review artifacts" in overview.data
    assert b"without source acquisition, NAIP acquisition, source materialization, or GPT drafting" in overview.data
    assert blocked.status_code == 200
    assert b"Confirm the developer reset" in blocked.data


def test_overview_dev_review_queue_reset_calls_adapter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    called: dict[str, object] = {}

    def fake_reset(path: Path, **kwargs: object) -> dict[str, object]:
        called["path"] = path
        called.update(kwargs)
        return {"after": {"review_queue_item_count": 42}}

    monkeypatch.setattr(adapter, "reset_generated_review_queue", fake_reset)

    response = client.post(
        "/overview/reset-review-queue",
        data={"confirm_reset": "yes"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert called["path"] == project_dir.resolve()
    assert called["include_exports"] is False
    assert b"Review artifacts refreshed and queue rebuilt with 42 review items" in response.data


def test_process_log_captures_refresh_and_rebuild(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    def fake_reset(path: Path, **kwargs: object) -> dict[str, object]:
        progress = kwargs.get("progress_callback")
        assert callable(progress)
        progress({"event": "refresh_started", "delete_count": 2})
        progress({"event": "delete_artifact", "artifact": "review_queue/review_queue.json"})
        progress({"event": "rebuild_started"})
        progress({"event": "rebuild_completed", "review_items": 42})
        return {"after": {"review_queue_item_count": 42}}

    monkeypatch.setattr(adapter, "reset_review_queue", fake_reset)

    adapter.reset_generated_review_queue(project_dir)
    payload = adapter.process_log_tail(50)
    lines = "\n".join(payload["lines"])

    assert "refresh_artifacts started" in lines
    assert "refresh_artifacts deleted artifact" in lines
    assert "rebuild_queue started" in lines
    assert "rebuild_queue generated review queue" in lines
    assert "refresh_artifacts complete" in lines


def test_overview_dev_review_queue_reset_can_include_exports(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    called: dict[str, object] = {}

    def fake_reset(path: Path, **kwargs: object) -> dict[str, object]:
        called["path"] = path
        called.update(kwargs)
        return {"after": {"review_queue_item_count": 42}}

    monkeypatch.setattr(adapter, "reset_generated_review_queue", fake_reset)

    response = client.post(
        "/overview/reset-review-queue",
        data={"confirm_reset": "yes", "include_exports": "yes"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert called["path"] == project_dir.resolve()
    assert called["include_exports"] is True


def test_gpt_interpretive_assist_controls_default_off(tmp_path: Path) -> None:
    write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)

    response = client.get("/overview")
    text = response.data.decode()

    assert response.status_code == 200
    assert "GPT Interpretive Assist" in text
    assert "GPT Assist" in text
    assert "GPT controls are off." in text
    assert "Turn On GPT Controls" in text
    assert "Preview Planned Calls" in text
    assert "Generate GPT Drafts" in text
    assert '<fieldset class="control-group" disabled>' in text


def test_gpt_interpretive_assist_generate_requires_toggle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    called = False

    def fake_run(path: Path, **kwargs: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {"accepted_gpt_draft_count": 1, "rejected_gpt_draft_count": 0, "output_path": ""}

    monkeypatch.setattr(adapter, "run_gpt_interpretive_assist", fake_run)
    response = client.post("/overview/gpt-interpretive-assist/generate", follow_redirects=True)

    assert response.status_code == 200
    assert called is False
    assert b"Turn on GPT Interpretive Assist" in response.data


def test_gpt_interpretive_assist_generate_button_disabled_until_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_project(tmp_path)
    monkeypatch.setenv("GPT_DRAFTING", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    client.post(
        "/overview/gpt-interpretive-assist/toggle",
        data={"gpt_interpretive_assist_enabled": "yes"},
        follow_redirects=True,
    )

    response = client.get("/overview")
    text = response.data.decode()

    assert response.status_code == 200
    assert "GPT Validated / Rejected" in text
    assert "Deterministic Fallbacks" in text
    assert "Preview Planned Calls" in text
    assert '<button class="primary" type="submit" disabled>Generate GPT Drafts</button>' in text


def test_gpt_interpretive_assist_non_dry_run_requires_ready_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    write_project(tmp_path)
    monkeypatch.setenv("GPT_DRAFTING", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    called = False

    def fake_run(path: Path, **kwargs: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {"accepted_gpt_draft_count": 1, "rejected_gpt_draft_count": 0, "output_path": ""}

    monkeypatch.setattr(adapter, "run_gpt_interpretive_assist", fake_run)
    client.post(
        "/overview/gpt-interpretive-assist/toggle",
        data={"gpt_interpretive_assist_enabled": "yes"},
        follow_redirects=True,
    )
    response = client.post("/overview/gpt-interpretive-assist/generate", follow_redirects=True)

    assert response.status_code == 200
    assert called is False
    assert b"GPT Interpretive Assist is not ready" in response.data


def test_gpt_interpretive_assist_explicit_submit_calls_adapter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    app = create_app(project_root=tmp_path, testing=True)
    client = app.test_client()
    _select_project(client)
    called: dict[str, object] = {}

    def fake_run(path: Path, **kwargs: object) -> dict[str, object]:
        called["path"] = path
        called.update(kwargs)
        return {
            "dry_run": True,
            "planned_call_count": 1,
            "accepted_gpt_draft_count": 0,
            "rejected_gpt_draft_count": 0,
            "output_path": str(project_dir / "drafts" / "gpt_interpretive_assist_run.json"),
        }

    monkeypatch.setattr(adapter, "run_gpt_interpretive_assist", fake_run)
    client.post(
        "/overview/gpt-interpretive-assist/toggle",
        data={"gpt_interpretive_assist_enabled": "yes"},
        follow_redirects=True,
    )
    response = client.post(
        "/overview/gpt-interpretive-assist/generate",
        data={
            "sections": ["wetlands-and-waterbodies"],
            "max_calls": "1",
            "dry_run": "yes",
            "skip_existing": "yes",
            "source_backed_only": "yes",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert called["path"] == project_dir.resolve()
    assert called["sections"] == ["wetlands-and-waterbodies"]
    assert called["max_calls"] == 1
    assert called["dry_run"] is True
    assert called["skip_existing"] is True
    assert called["source_backed_only"] is True
    assert b"GPT dry run planned 1 section draft call" in response.data


def test_process_log_captures_gpt_draft_items(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    def fake_draft(path: Path, **kwargs: object) -> dict[str, object]:
        progress = kwargs.get("progress_callback")
        assert callable(progress)
        progress({"event": "planned", "planned_call_count": 1, "eligible_count": 1})
        progress({"event": "item_started", "target_id": "wetlands-and-waterbodies"})
        progress({"event": "item_completed", "target_id": "wetlands-and-waterbodies", "status": "success"})
        progress({"event": "drafting_completed", "accepted": 1, "rejected": 0, "cache_hits": 0})
        return {"accepted_gpt_draft_count": 1, "rejected_gpt_draft_count": 0, "output_path": ""}

    monkeypatch.setattr(adapter, "draft_section_candidates", fake_draft)

    adapter.run_gpt_interpretive_assist(project_dir, sections=["wetlands-and-waterbodies"], max_calls=1)
    payload = adapter.process_log_tail(50)
    lines = "\n".join(payload["lines"])

    assert "generate_gpt_drafts started" in lines
    assert "generate_gpt_drafts item complete" in lines
    assert "item=wetlands-and-waterbodies" in lines
    assert "status=success" in lines
    assert "generate_gpt_drafts complete" in lines
