from __future__ import annotations

import json
from pathlib import Path

import pytest

from review_assist.figure_regeneration import FigureRegenerationError, regenerate_figure_version
from review_assist.figure_style_model import (
    FIGURE_RENDER_JOBS_PATH,
    FIGURE_STYLE_OVERRIDES_PATH,
    FIGURE_VERSIONS_PATH,
    active_style_override,
    approve_figure_version,
    approved_figure_version,
    initialize_figure_style_model,
    save_project_style_override,
)

from test_figure_style_model import read_json, write_project_with_figures


def test_regenerate_figure_version_creates_render_job_version_and_png(tmp_path: Path) -> None:
    project_dir = write_project_with_figures(tmp_path)
    initialize_figure_style_model(project_dir)

    result = regenerate_figure_version(project_dir, "figure-wetlands-waterbodies")
    versions = read_json(project_dir / FIGURE_VERSIONS_PATH)
    jobs = read_json(project_dir / FIGURE_RENDER_JOBS_PATH)
    version = result["version"]

    assert result["review_only"] is True
    assert version["version_number"] == 2
    assert version["approval_state"] == "regenerated"
    assert version["export_active"] is False
    assert (project_dir / version["output_artifact_path"]).exists()
    assert jobs["render_jobs"][-1]["status"] == "succeeded"
    assert jobs["render_jobs"][-1]["output_artifact_path"] == version["output_artifact_path"]
    assert versions["versions"][-1]["version_id"] == "figure-wetlands-waterbodies:v2"


def test_regeneration_applies_sparse_style_overrides_to_render_metadata(tmp_path: Path) -> None:
    project_dir = write_project_with_figures(tmp_path)
    save_project_style_override(
        project_dir,
        "figure-wetlands-waterbodies",
        [
            {
                "layer_id": "source:usfws_nwi_wetlands",
                "display_name": "Wetland Overlay",
                "stroke_color": "#00AAFF",
                "fill_color": "#22C55E",
                "fill_opacity": "0.35",
                "stroke_width": "2.5",
                "point_size": "20",
                "z_index": "8",
            }
        ],
    )

    result = regenerate_figure_version(project_dir, "figure-wetlands-waterbodies")
    source_layer = next(layer for layer in result["version"]["rendered_layers"] if layer["layer_id"] == "source:usfws_nwi_wetlands")

    assert source_layer["display_name"] == "Wetland Overlay"
    assert source_layer["z_index"] == 8
    assert source_layer["style"]["stroke_color"] == "#00AAFF"
    assert source_layer["style"]["fill_color"] == "#22C55E"
    assert source_layer["style"]["stroke_width"] == 2.5
    assert source_layer["style"]["point_size"] == 20.0


def test_regeneration_hides_layers_and_orders_visible_layers(tmp_path: Path) -> None:
    project_dir = write_project_with_figures(tmp_path)
    save_project_style_override(
        project_dir,
        "figure-wetlands-waterbodies",
        [
            {"layer_id": "comparison_units", "z_index": "9"},
            {"layer_id": "source:usfws_nwi_wetlands", "visible": "false", "z_index": "1"},
        ],
    )

    result = regenerate_figure_version(project_dir, "figure-wetlands-waterbodies")

    assert [layer["layer_id"] for layer in result["version"]["rendered_layers"]] == ["basemap:1", "comparison_units:unit-1", "comparison_units:unit-2"]
    assert result["version"]["hidden_layers"][0]["layer_id"] == "source:usfws_nwi_wetlands"


def test_regeneration_applies_comparison_feature_overrides(tmp_path: Path) -> None:
    project_dir = write_project_with_figures(tmp_path)
    save_project_style_override(
        project_dir,
        "figure-wetlands-waterbodies",
        [
            {"layer_id": "comparison_units:unit-1", "stroke_color": "#00AAFF", "display_name": "Comparison 1", "z_index": "7"},
            {"layer_id": "comparison_units:unit-2", "visible": "false", "z_index": "3"},
        ],
    )
    captured: dict[str, object] = {}

    def spy_renderer(**kwargs):
        output_path = Path(kwargs["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
        captured.update(kwargs)
        return {"layout": "spy"}

    result = regenerate_figure_version(project_dir, "figure-wetlands-waterbodies", renderer=spy_renderer)

    assert captured["comparison_feature_styles"]["unit-1"]["stroke_color"] == "#00AAFF"  # type: ignore[index]
    assert captured["comparison_feature_styles"]["unit-1"]["label"] == "Comparison 1"  # type: ignore[index]
    assert captured["comparison_feature_styles"]["unit-2"]["visible"] is False  # type: ignore[index]
    assert [layer["layer_id"] for layer in result["version"]["rendered_layers"] if layer["layer_id"].startswith("comparison_units:")] == [
        "comparison_units:unit-1"
    ]
    assert any(layer["layer_id"] == "comparison_units:unit-2" for layer in result["version"]["hidden_layers"])


def test_regeneration_rejects_unsupported_output_format(tmp_path: Path) -> None:
    project_dir = write_project_with_figures(tmp_path)

    with pytest.raises(FigureRegenerationError, match="PNG output only"):
        regenerate_figure_version(project_dir, "figure-wetlands-waterbodies", output_format="pdf")


def test_failed_regeneration_preserves_versions_and_records_failed_job(tmp_path: Path) -> None:
    project_dir = write_project_with_figures(tmp_path)
    initialize_figure_style_model(project_dir)
    versions_before = (project_dir / FIGURE_VERSIONS_PATH).read_bytes()

    def failing_renderer(**_kwargs):
        raise RuntimeError("renderer unavailable")

    with pytest.raises(FigureRegenerationError, match="renderer unavailable"):
        regenerate_figure_version(project_dir, "figure-wetlands-waterbodies", renderer=failing_renderer)

    jobs = read_json(project_dir / FIGURE_RENDER_JOBS_PATH)
    assert (project_dir / FIGURE_VERSIONS_PATH).read_bytes() == versions_before
    assert jobs["render_jobs"][-1]["status"] == "failed"
    assert jobs["render_jobs"][-1]["errors"][0]["code"] == "figure_regeneration_failed"


def test_later_regeneration_does_not_modify_approved_version(tmp_path: Path) -> None:
    project_dir = write_project_with_figures(tmp_path)
    first = regenerate_figure_version(project_dir, "figure-wetlands-waterbodies")
    approve_figure_version(project_dir, "figure-wetlands-waterbodies", first["version"]["version_id"])
    approved_before = approved_figure_version(read_json(project_dir / FIGURE_VERSIONS_PATH), "figure-wetlands-waterbodies")

    second = regenerate_figure_version(project_dir, "figure-wetlands-waterbodies")
    versions = read_json(project_dir / FIGURE_VERSIONS_PATH)
    approved_after = approved_figure_version(versions, "figure-wetlands-waterbodies")

    assert second["version"]["version_number"] == 3
    assert approved_after["version_id"] == approved_before["version_id"]
    assert approved_after["approval_state"] == "approved"
    assert approved_after["approved_at"] == approved_before["approved_at"]


def test_regeneration_does_not_mutate_analysis_review_or_export_artifacts(tmp_path: Path) -> None:
    project_dir = write_project_with_figures(tmp_path)
    for path in [project_dir / "review_queue" / "review_queue.json", project_dir / "exports" / "export_manifest.json"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"sentinel": path.name}) + "\n", encoding="utf-8")
    watched_paths = [
        project_dir / "deliverable" / "figures.json",
        project_dir / "source_status" / "source_status_set.json",
        project_dir / "context" / "project_area.json",
        project_dir / "intermediate" / "comparison_units.json",
        project_dir / "intermediate" / "comparison_units.geojson",
        project_dir / "constraints" / "comparison_unit_constraints.json",
        project_dir / "review_queue" / "review_queue.json",
        project_dir / "exports" / "export_manifest.json",
    ]
    before = {path: path.read_bytes() for path in watched_paths}

    regenerate_figure_version(project_dir, "figure-wetlands-waterbodies")

    assert {path: path.read_bytes() for path in watched_paths} == before
    assert active_style_override(read_json(project_dir / FIGURE_STYLE_OVERRIDES_PATH), "figure-wetlands-waterbodies") is None
