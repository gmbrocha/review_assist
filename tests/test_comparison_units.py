from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest

from review_assist.cli import main
from review_assist.comparison_units import build_comparison_units, load_comparison_units


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


def write_project(
    tmp_path: Path,
    kml_body: str,
    *,
    assumptions: dict[str, object] | None = None,
    role: str = "project_geometry",
    project_type: str = "alternatives_review",
) -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    (project_dir / "inputs" / "input.kmz").write_bytes(kmz_bytes(kml_document(kml_body)))
    merged_assumptions = {
        "default_buffer_feet": 100,
        "input_crs": "EPSG:4326",
    }
    if assumptions:
        merged_assumptions.update(assumptions)
    (project_dir / "config" / "project.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "name": "Test Project",
                "description": "Synthetic project",
                "project_type": project_type,
                "inputs": [
                    {
                        "path": "inputs/input.kmz",
                        "role": role,
                        "description": "Synthetic input",
                    }
                ],
                "assumptions": merged_assumptions,
                "special_reviewer_instructions": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project_dir


def comparison_feature_payload(project_dir: Path) -> list[dict[str, object]]:
    data = json.loads((project_dir / "intermediate" / "comparison_units.geojson").read_text(encoding="utf-8"))
    return data["features"]


def test_line_comparison_units_group_by_folder_and_merge_connected_segments(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Folder><name>Option A</name>
          <Placemark><name>Segment 1</name><LineString><coordinates>-90.0000,32.0000,0 -89.9950,32.0000,0</coordinates></LineString></Placemark>
          <Placemark><name>Segment 2</name><LineString><coordinates>-89.9950,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        </Folder>
        <Folder><name>Option B</name>
          <Placemark><name>Segment 3</name><LineString><coordinates>-90.0000,32.0010,0 -89.9900,32.0010,0</coordinates></LineString></Placemark>
        </Folder>
        """,
    )

    result = build_comparison_units(project_dir)
    units = gpd.read_file(project_dir / "intermediate" / "comparison_units.geojson")

    assert result["comparison_unit_count"] == 2
    assert set(units["comparison_unit_name"]) == {"Option A", "Option B"}
    option_a = units.loc[units["comparison_unit_name"] == "Option A"].iloc[0]
    assert option_a.geometry.geom_type == "LineString"
    assert int(option_a["source_feature_count"]) == 2
    assert option_a["grouping_method"] == "folder_group"


def test_disconnected_line_segments_preserve_multilinestring_without_invented_connection(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Folder><name>Option A</name>
          <Placemark><name>Segment 1</name><LineString><coordinates>-90.0000,32.0000,0 -89.9950,32.0000,0</coordinates></LineString></Placemark>
          <Placemark><name>Segment 2</name><LineString><coordinates>-89.9900,32.0000,0 -89.9850,32.0000,0</coordinates></LineString></Placemark>
        </Folder>
        """,
    )

    build_comparison_units(project_dir)
    units = gpd.read_file(project_dir / "intermediate" / "comparison_units.geojson")

    assert len(units) == 1
    assert units.geometry.iloc[0].geom_type == "MultiLineString"
    assert len(units.geometry.iloc[0].geoms) == 2


def test_expected_count_mismatch_creates_validation_issue(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Folder><name>Option A</name>
          <Placemark><name>Segment 1</name><LineString><coordinates>-90.0000,32.0000,0 -89.9950,32.0000,0</coordinates></LineString></Placemark>
        </Folder>
        """,
        assumptions={"expected_comparison_unit_count": 2},
    )

    result = build_comparison_units(project_dir)

    assert result["comparison_unit_count"] == 1
    assert result["expected_comparison_unit_count"] == 2
    assert result["expected_count_status"] == "mismatch"
    assert any(issue["code"] == "comparison_unit_count_mismatch" for issue in result["validation_issues"])


def test_trails_style_folder_structure_resolves_to_five_expected_units(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Folder><name>ali_option1A_2013.dwg</name><Folder><name>Levels</name><Folder><name>0</name>
          <Placemark><name>Style1</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        </Folder></Folder></Folder>
        <Folder><name>ali_option1B_2013.dwg</name><Folder><name>Levels</name><Folder><name>0</name>
          <Placemark><name>Style2</name><LineString><coordinates>-90.0000,32.0010,0 -89.9900,32.0010,0</coordinates></LineString></Placemark>
        </Folder><Folder><name>P_TRAIL-OPTION1A-1B</name>
          <Placemark><name>Style3</name><LineString><coordinates>-89.9900,32.0010,0 -89.9850,32.0010,0</coordinates></LineString></Placemark>
        </Folder></Folder></Folder>
        <Folder><name>ali_option2_2013.dwg</name><Folder><name>Levels</name><Folder><name>0</name>
          <Placemark><name>Style4</name><LineString><coordinates>-90.0000,32.0020,0 -89.9900,32.0020,0</coordinates></LineString></Placemark>
        </Folder><Folder><name>P_TRAIL-OPTION2</name>
          <Placemark><name>Style5</name><LineString><coordinates>-89.9900,32.0020,0 -89.9850,32.0020,0</coordinates></LineString></Placemark>
        </Folder></Folder></Folder>
        <Folder><name>ali_option3_2013.dwg</name><Folder><name>Levels</name><Folder><name>0</name>
          <Placemark><name>Style6</name><LineString><coordinates>-90.0000,32.0030,0 -89.9900,32.0030,0</coordinates></LineString></Placemark>
        </Folder></Folder></Folder>
        <Folder><name>ali_option4-2013.dwg</name><Folder><name>Levels</name><Folder><name>0</name>
          <Placemark><name>Style7</name><LineString><coordinates>-90.0000,32.0040,0 -89.9900,32.0040,0</coordinates></LineString></Placemark>
        </Folder></Folder></Folder>
        """,
        assumptions={"expected_comparison_unit_count": 5},
    )

    result = build_comparison_units(project_dir)

    assert result["comparison_unit_count"] == 5
    assert result["expected_count_status"] == "matched"
    assert not any(issue["code"] == "comparison_unit_count_mismatch" for issue in result["validation_issues"])


def test_point_heavy_project_groups_by_style_and_preserves_raw_point_count(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Style id="Red"><IconStyle><color>ff0000ff</color></IconStyle></Style>
        <Style id="Blue"><IconStyle><color>ffff0000</color></IconStyle></Style>
        <Placemark><styleUrl>#Red</styleUrl><Point><coordinates>-90.0000,32.0000,0</coordinates></Point></Placemark>
        <Placemark><styleUrl>#Red</styleUrl><Point><coordinates>-89.9900,32.0000,0</coordinates></Point></Placemark>
        <Placemark><styleUrl>#Blue</styleUrl><Point><coordinates>-89.9800,32.0000,0</coordinates></Point></Placemark>
        """,
        project_type="location_review",
    )

    result = build_comparison_units(project_dir)
    units = gpd.read_file(project_dir / "intermediate" / "comparison_units.geojson")

    assert result["raw_project_feature_count"] == 3
    assert result["comparison_unit_count"] == 2
    assert set(units["style_color"]) == {"ff0000ff", "ffff0000"}
    assert int(units.loc[units["style_url"] == "#Red", "source_feature_count"].iloc[0]) == 2


def test_point_heavy_project_uses_all_points_fallback_when_no_grouping_signal_exists(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><Point><coordinates>-90.0000,32.0000,0</coordinates></Point></Placemark>
        <Placemark><Point><coordinates>-89.9900,32.0000,0</coordinates></Point></Placemark>
        """,
        project_type="location_review",
    )

    result = build_comparison_units(project_dir)
    units = gpd.read_file(project_dir / "intermediate" / "comparison_units.geojson")

    assert result["comparison_unit_count"] == 1
    assert units["comparison_unit_name"].iloc[0] == "All points"
    assert int(units["source_feature_count"].iloc[0]) == 2
    assert bool(units["requires_reviewer_confirmation"].iloc[0])
    assert any(issue["code"] == "comparison_unit_grouping_requires_review" for issue in result["validation_issues"])


def test_single_and_multiple_named_polygons_create_named_units(tmp_path: Path) -> None:
    single_project = write_project(
        tmp_path / "single",
        """
        <Placemark><name>Study Area</name><Polygon><outerBoundaryIs><LinearRing><coordinates>-90,32,0 -90,32.01,0 -89.99,32.01,0 -90,32,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
        """,
    )
    multiple_project = write_project(
        tmp_path / "multiple",
        """
        <Placemark><name>Area A</name><Polygon><outerBoundaryIs><LinearRing><coordinates>-90,32,0 -90,32.01,0 -89.99,32.01,0 -90,32,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
        <Placemark><name>Area B</name><Polygon><outerBoundaryIs><LinearRing><coordinates>-89.98,32,0 -89.98,32.01,0 -89.97,32.01,0 -89.98,32,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
        """,
    )

    single_result = build_comparison_units(single_project)
    multiple_result = build_comparison_units(multiple_project)
    multiple_units = gpd.read_file(multiple_project / "intermediate" / "comparison_units.geojson")

    assert single_result["comparison_unit_count"] == 1
    assert multiple_result["comparison_unit_count"] == 2
    assert set(multiple_units["comparison_unit_name"]) == {"Area A", "Area B"}


def test_mixed_geometry_emits_review_warning_and_marks_polygon_boundary_context(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        <Placemark><name>Study Area</name><Polygon><outerBoundaryIs><LinearRing><coordinates>-90.01,31.99,0 -90.01,32.01,0 -89.98,32.01,0 -90.01,31.99,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
        """,
    )

    result = build_comparison_units(project_dir)
    units = gpd.read_file(project_dir / "intermediate" / "comparison_units.geojson")

    assert any(issue["code"] == "mixed_geometry_requires_review" for issue in result["validation_issues"])
    assert any(issue["code"] == "mixed_boundary_proposition_ambiguity" for issue in result["validation_issues"])
    assert "boundary_context" in set(units["comparison_unit_type"])


def test_comparison_unit_metadata_loads_and_validates_geojson_path(tmp_path: Path) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )

    created = build_comparison_units(project_dir)
    loaded = load_comparison_units(project_dir)

    assert loaded["output_path"] == created["output_path"]
    assert Path(loaded["comparison_units_path"]).exists()


def test_cli_build_comparison_units_text_and_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(
        tmp_path,
        """
        <Placemark><name>Route A</name><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """,
    )

    assert main(["build-comparison-units", str(project_dir)]) == 0
    text = capsys.readouterr()
    assert "Built comparison units" in text.out

    assert main(["build-comparison-units", str(project_dir), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["project_id"] == "test_project"
