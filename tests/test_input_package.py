from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from review_assist.cli import main
from review_assist.input_package import classify_input_package, load_input_package


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO_ROOT / "projects"


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


def write_project(tmp_path: Path, inputs: list[dict[str, object]]) -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    for item in inputs:
        content = item.get("content", b"")
        if content is None:
            continue
        input_path = project_dir / str(item["path"])
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_bytes(content if isinstance(content, bytes) else str(content).encode("utf-8"))

    manifest_inputs = [
        {
            key: value
            for key, value in item.items()
            if key in {"path", "role", "description", "source_id", "source_category"}
        }
        for item in inputs
    ]
    (project_dir / "config" / "project.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "name": "Test Project",
                "description": "Synthetic project",
                "project_type": "alternatives_review",
                "inputs": manifest_inputs,
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


def route_kmz() -> bytes:
    return kmz_bytes(
        kml_document(
            """
            <Placemark><name>Route A</name><LineString><coordinates>-90.0,32.0,0 -89.99,32.0,0</coordinates></LineString></Placemark>
            """
        )
    )


def issue_codes(artifact: dict[str, object]) -> set[str]:
    return {str(issue["code"]) for issue in artifact["validation_issues"]}  # type: ignore[index]


def test_sample_workspaces_mark_required_kmz_present() -> None:
    for project_name in ("trails", "conexon_projects"):
        result = classify_input_package(PROJECTS_DIR / project_name)

        assert result["required_kmz_present"] is True
        assert result["project_geometry_input_count"] == 1
        assert result["inputs"][0]["classification"] == "project_geometry"  # type: ignore[index]


def test_missing_kmz_creates_required_kmz_missing(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        [
            {
                "path": "inputs/missing.kmz",
                "role": "alternatives",
                "description": "Missing KMZ",
                "content": None,
            }
        ],
    )

    result = classify_input_package(project_dir)

    assert result["required_kmz_present"] is False
    assert {"required_kmz_missing", "missing_project_input_file"} <= issue_codes(result)


def test_multiple_project_kmz_inputs_require_confirmation_when_roles_do_not_disambiguate(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        [
            {
                "path": "inputs/routes_a.kmz",
                "role": "alternatives",
                "description": "Route input A",
                "content": route_kmz(),
            },
            {
                "path": "inputs/routes_b.kmz",
                "role": "alternatives",
                "description": "Route input B",
                "content": route_kmz(),
            },
        ],
    )

    result = classify_input_package(project_dir)

    assert "multiple_project_kmz_inputs" in issue_codes(result)
    assert all(record["requires_reviewer_confirmation"] for record in result["inputs"])  # type: ignore[index]


def test_manifest_source_layer_input_classifies_as_source_layer(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        [
            {
                "path": "inputs/project.kmz",
                "role": "alternatives",
                "description": "Project KMZ",
                "content": route_kmz(),
            },
            {
                "path": "inputs/wetlands.geojson",
                "role": "wetlands",
                "description": "NWI wetlands source layer",
                "source_id": "usfws_nwi_wetlands",
                "source_category": "wetlands_waterbodies",
                "content": b'{"type":"FeatureCollection","features":[]}',
            },
        ],
    )

    result = classify_input_package(project_dir)
    source_record = next(record for record in result["inputs"] if record["path"] == "inputs/wetlands.geojson")  # type: ignore[index]

    assert source_record["classification"] == "source_layer"
    assert source_record["requires_reviewer_confirmation"] is False
    assert result["source_layer_input_count"] == 1


def test_missing_input_path_creates_validation_issue(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        [
            {
                "path": "inputs/project.kmz",
                "role": "alternatives",
                "description": "Project KMZ",
                "content": route_kmz(),
            },
            {
                "path": "inputs/prior-report.pdf",
                "role": "supporting_report",
                "description": "Prior report",
                "content": None,
            },
        ],
    )

    result = classify_input_package(project_dir)
    report_record = next(record for record in result["inputs"] if record["path"] == "inputs/prior-report.pdf")  # type: ignore[index]

    assert report_record["classification"] == "supporting_report"
    assert "missing_project_input_file" in issue_codes(result)


def test_input_package_loads_after_write(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        [
            {
                "path": "inputs/project.kmz",
                "role": "alternatives",
                "description": "Project KMZ",
                "content": route_kmz(),
            }
        ],
    )

    written = classify_input_package(project_dir)
    loaded = load_input_package(project_dir)

    assert loaded["output_path"] == written["output_path"]


def test_cli_classify_input_package_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(
        tmp_path,
        [
            {
                "path": "inputs/project.kmz",
                "role": "alternatives",
                "description": "Project KMZ",
                "content": route_kmz(),
            }
        ],
    )

    assert main(["classify-input-package", str(project_dir), "--json"]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out)["required_kmz_present"] is True
