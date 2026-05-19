from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from review_assist.cli import main
from review_assist.findings import (
    FindingGenerationError,
    FindingTemplateError,
    generate_draft_findings,
    load_draft_findings,
    load_finding_template_config,
)
from review_assist.project_context import generate_project_context
from review_assist.review_queue import generate_review_queue, update_review_item
from review_assist.spatial_analysis import analyze_project


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


def write_registry(project_dir: Path, source_id: str, source_path: str) -> None:
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": source_id,
                        "enabled": True,
                        "access_method": "local_file",
                        "path": source_path,
                        "role": "context",
                        "buffer_feet": None,
                        "notes": "",
                        "status": "test",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_layer(path: Path, geometries: list[object], rows: list[dict[str, object]]) -> Path:
    gdf = gpd.GeoDataFrame(rows, geometry=geometries, crs="EPSG:4326")
    path.write_text(gdf.to_json(drop_id=True), encoding="utf-8")
    return path


def findings_by_type(result: dict[str, object], finding_type: str) -> list[dict[str, object]]:
    return [item for item in result["findings"] if item["type"] == finding_type]  # type: ignore[index]


def queue_items_by_type(queue: dict[str, object], item_type: str) -> list[dict[str, object]]:
    return [item for item in queue["items"] if item["type"] == item_type]  # type: ignore[index]


def test_finding_template_config_loads() -> None:
    config = load_finding_template_config()

    assert "wetland_or_waterbody_relationship" in config.templates
    assert "protected_species_or_critical_habitat_context" in config.templates
    assert "source_unavailable_or_deferred" in config.templates


def test_finding_template_config_rejects_invalid_templates(tmp_path: Path) -> None:
    template_path = tmp_path / "finding_templates.json"
    template_path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "finding_type": "broken",
                        "title": "Broken",
                        "summary": "Broken",
                        "details": "Broken",
                        "implication": "Broken",
                        "evidence_class": "broken",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FindingTemplateError, match="resource_categories"):
        load_finding_template_config(template_path)


def test_spatial_wetland_relationship_creates_draft_finding(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    analyze_project(project_dir)

    result = generate_draft_findings(project_dir)

    findings = findings_by_type(result, "wetland_or_waterbody_relationship")
    assert findings
    finding = findings[0]
    assert finding["review_status"] == "draft"
    assert finding["resource_category"] == "wetlands_waterbodies"
    assert finding["source_ids"] == ["usfws_nwi_wetlands"]
    assert finding["provenance"]["method"] == "geopandas_shapely_local_spatial_check"  # type: ignore[index]


def test_stream_crossing_creates_cautious_implication_language(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "streams.geojson", [LineString([(-89.995, 31.999), (-89.995, 32.001)])], [{"name": "Stream A"}])
    write_registry(project_dir, "usgs_nhd_hydrography", "streams.geojson")
    analyze_project(project_dir)

    result = generate_draft_findings(project_dir)

    findings = findings_by_type(result, "stream_or_hydrography_crossing")
    assert findings
    implication = str(findings[0]["implication"]).lower()
    assert "bridge" in implication
    assert "culvert" in implication
    assert "permitting" in implication
    assert "may require" in implication
    assert "final determination" in implication


def test_deferred_source_statuses_create_manual_review_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("review_assist.source_status.maybe_load_seed_source_manifest", lambda source_id: None)
    project_dir = write_project(tmp_path)
    result = generate_draft_findings(project_dir)

    deferred = findings_by_type(result, "source_unavailable_or_deferred")
    statuses = {item["assumptions"]["source_status"] for item in deferred}  # type: ignore[index]
    assert "downloadable" in statuses
    assert "gated" in statuses
    assert "stubbed" in statuses
    assert any(item["review_status"] == "needs_verification" for item in deferred)


def test_missing_source_status_creates_unavailable_finding(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    context = generate_project_context(project_dir)
    source_status_path = project_dir / "source_status" / "source_status_set.json"
    source_status_path.parent.mkdir(parents=True)
    source_status_path.write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "project_name": "Test Project",
                "project_dir": str(project_dir),
                "created_at": "2026-05-14T00:00:00+00:00",
                "report_profile": context["report_profile"],
                "project_context_path": context["context_path"],
                "statuses": [
                    {
                        "category": "custom_missing_category",
                        "requirement": "required",
                        "status": "missing",
                        "source_ids": [],
                        "source_names": [],
                        "registered_source_ids": [],
                        "local_paths": [],
                        "uncertainty_flags": ["source_unavailable"],
                        "notes": "Synthetic missing source.",
                    }
                ],
                "validation_issues": [],
                "output_path": str(source_status_path),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = generate_draft_findings(project_dir)

    findings = findings_by_type(result, "source_unavailable_or_deferred")
    assert len(findings) == 1
    assert findings[0]["assumptions"]["source_status"] == "missing"  # type: ignore[index]
    assert findings[0]["review_status"] == "needs_review"


def test_load_draft_findings_rejects_invalid_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    findings_path = project_dir / "findings" / "draft_findings.json"
    findings_path.parent.mkdir(parents=True)
    findings_path.write_text('{"findings": [{"finding_id": "broken"}]}', encoding="utf-8")

    with pytest.raises(FindingGenerationError, match="missing required fields"):
        load_draft_findings(project_dir)


def test_no_mapped_relationship_creates_no_conflict_draft_finding(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "far.geojson", [Point(-89.0, 33.0)], [{"name": "Far Feature"}])
    write_registry(project_dir, "epa_envirofacts_echo", "far.geojson")
    analyze_project(project_dir)

    result = generate_draft_findings(project_dir)

    findings = findings_by_type(result, "no_mapped_conflict_identified")
    assert len(findings) == 1
    assert findings[0]["review_status"] == "draft"
    assert "does not prove absence" in findings[0]["details"]


def test_generated_finding_ids_are_deterministic(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "streams.geojson", [LineString([(-89.995, 31.999), (-89.995, 32.001)])], [{"name": "Stream A"}])
    write_registry(project_dir, "usgs_nhd_hydrography", "streams.geojson")
    analyze_project(project_dir)

    first = generate_draft_findings(project_dir)
    second = generate_draft_findings(project_dir)

    assert [item["finding_id"] for item in first["findings"]] == [item["finding_id"] for item in second["findings"]]


def test_review_queue_includes_draft_findings_and_preserves_review_state(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(
        project_dir / "wetlands.geojson",
        [Polygon([(-90.001, 31.999), (-89.999, 31.999), (-89.999, 32.001), (-90.001, 32.001), (-90.001, 31.999)])],
        [{"name": "Wetland A"}],
    )
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")
    analyze_project(project_dir)
    findings = generate_draft_findings(project_dir)
    finding_id = findings_by_type(findings, "wetland_or_waterbody_relationship")[0]["finding_id"]
    item_id = f"draft-finding-{str(finding_id).replace('_', '-')}".lower()

    queue = generate_review_queue(project_dir, include_legacy_artifacts=True)
    draft_items = queue_items_by_type(queue, "draft_finding")
    assert any(item["id"] == item_id for item in draft_items)

    update_review_item(project_dir, item_id, status="accepted", note="Reviewed finding.")
    generate_draft_findings(project_dir)
    regenerated = generate_review_queue(project_dir, include_legacy_artifacts=True)
    reviewed_item = next(item for item in regenerated["items"] if item["id"] == item_id)
    assert reviewed_item["status"] == "accepted"
    assert reviewed_item["export_eligible"] is True
    assert len(reviewed_item["reviewer_notes"]) == 1


def test_cli_generate_findings_text_and_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["generate-findings", str(project_dir)]) == 0
    captured = capsys.readouterr()
    assert "Generated draft findings" in captured.out

    assert main(["generate-findings", str(project_dir), "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"
