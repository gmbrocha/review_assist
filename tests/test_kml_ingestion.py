from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from review_assist.cli import main
from review_assist.inspection import ProjectInspectionError, inspect_project
from review_assist.kml import ingest_kml_input


def write_project(tmp_path: Path, input_name: str, input_bytes: bytes, *, role: str = "alternatives") -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    (project_dir / "inputs" / input_name).write_bytes(input_bytes)
    (project_dir / "config" / "project.json").write_text(
        f"""{{
  "project_id": "test_project",
  "name": "Test Project",
  "description": "Synthetic project",
  "project_type": "alternatives_review",
  "inputs": [
    {{
      "path": "inputs/{input_name}",
      "role": "{role}",
      "description": "Synthetic input"
    }}
  ],
  "assumptions": {{
    "default_buffer_feet": 100,
    "input_crs": "EPSG:4326"
  }},
  "special_reviewer_instructions": ""
}}
""",
        encoding="utf-8",
    )
    return project_dir


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


def test_ingests_points_lines_and_polygons(tmp_path: Path) -> None:
    kml = kml_document(
        """
        <Placemark><name>Point A</name><Point><coordinates>-90.0,32.0,0</coordinates></Point></Placemark>
        <Placemark><name>Line A</name><LineString><coordinates>-90.0,32.0,0 -90.1,32.1,0</coordinates></LineString></Placemark>
        <Placemark><name>Polygon A</name><Polygon><outerBoundaryIs><LinearRing><coordinates>-90,32,0 -90,33,0 -89,33,0 -90,32,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
        """
    )
    path = tmp_path / "mixed.kml"
    path.write_bytes(kml)

    ingested = ingest_kml_input(path)

    assert len(ingested.geo_data_frame) == 3
    assert set(ingested.geo_data_frame.geometry.geom_type) == {"Point", "LineString", "Polygon"}
    assert any(issue.code == "mixed_geometry_types" for issue in ingested.issues)


def test_reports_blank_names(tmp_path: Path) -> None:
    kml = kml_document(
        """
        <Placemark><Point><coordinates>-90.0,32.0,0</coordinates></Point></Placemark>
        """
    )
    path = tmp_path / "blank.kml"
    path.write_bytes(kml)

    ingested = ingest_kml_input(path)

    assert len(ingested.geo_data_frame) == 1
    assert ingested.geo_data_frame.iloc[0]["candidate_label"] == "Placemark 1"
    assert any(issue.code == "blank_placemark_name" for issue in ingested.issues)


def test_inspect_project_writes_summary_and_geojson(tmp_path: Path) -> None:
    kml = kml_document(
        """
        <Placemark><name>Line A</name><LineString><coordinates>-90.0,32.0,0 -90.1,32.1,0</coordinates></LineString></Placemark>
        """
    )
    project_dir = write_project(tmp_path, "routes.kmz", kmz_bytes(kml))

    summary = inspect_project(project_dir)

    summary_path = Path(summary["summary_path"])
    geojson_path = project_dir / "intermediate" / "routes.geojson"
    assert summary_path.exists()
    assert geojson_path.exists()
    assert summary["inputs"][0]["feature_count"] == 1
    assert summary["inputs"][0]["geometry_type_counts"] == {"LineString": 1}


def test_missing_manifest_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ProjectInspectionError, match="Missing project manifest"):
        inspect_project(tmp_path / "missing")


def test_missing_input_raises_clear_error(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path, "missing.kmz", b"")
    (project_dir / "inputs" / "missing.kmz").unlink()

    with pytest.raises(ProjectInspectionError, match="Missing input file"):
        inspect_project(project_dir)


def test_invalid_kmz_raises_clear_error(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path, "bad.kmz", b"not a zip")

    with pytest.raises(ProjectInspectionError, match="Invalid KMZ file"):
        inspect_project(project_dir)


def test_no_geometries_raises_clear_error(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path, "empty.kml", kml_document("<Folder><name>Only folders</name></Folder>"))

    with pytest.raises(ProjectInspectionError, match="No supported geometries found"):
        inspect_project(project_dir)


@pytest.mark.parametrize(
    ("input_name", "input_bytes", "expected_message"),
    [
        ("missing.kmz", None, "Missing input file"),
        ("bad.kmz", b"not a zip", "Invalid KMZ file"),
        ("empty.kml", kml_document("<Folder><name>Only folders</name></Folder>"), "No supported geometries found"),
    ],
)
def test_cli_returns_nonzero_for_input_failures(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    input_name: str,
    input_bytes: bytes | None,
    expected_message: str,
) -> None:
    project_dir = write_project(tmp_path, input_name, input_bytes or b"")
    if input_bytes is None:
        (project_dir / "inputs" / input_name).unlink()

    exit_code = main(["inspect-project", str(project_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert expected_message in captured.err


def test_cli_returns_nonzero_for_missing_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["inspect-project", str(tmp_path / "missing_project")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Missing project manifest" in captured.err
