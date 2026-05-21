from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from review_assist.cli import main
from review_assist.deliverable_items import generate_deliverable_items
from review_assist.evidence_package import build_evidence_package
from review_assist.project_context import ProjectContextError, generate_project_context
from review_assist.projects import load_project_manifest
from review_assist.report_profiles import ReportProfileError, load_report_profile_config, resolve_report_profile
from review_assist.data_lineage import build_data_lineage
from review_assist.review_queue import generate_review_queue
from review_assist.source_status import _category_status, effective_source_status, resolve_source_status_set


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


def write_project(tmp_path: Path, *, project_type: str = "alternatives_review", report_profile: str | None = None) -> Path:
    project_dir = tmp_path / "project"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "inputs").mkdir()
    kml = kml_document(
        """
        <Placemark><LineString><coordinates>-90.0000,32.0000,0 -89.9900,32.0000,0</coordinates></LineString></Placemark>
        """
    )
    (project_dir / "inputs" / "routes.kmz").write_bytes(kmz_bytes(kml))
    manifest = {
        "project_id": "test_project",
        "name": "Test Project",
        "description": "Synthetic project",
        "project_type": project_type,
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
        "special_reviewer_instructions": "Synthetic reviewer instruction.",
    }
    if report_profile is not None:
        manifest["report_profile"] = report_profile
    (project_dir / "config" / "project.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return project_dir


def write_registry(project_dir: Path, source_id: str, source_path: str | None, *, enabled: bool = True) -> None:
    write_registry_sources(project_dir, [(source_id, source_path, enabled, "test")])


def write_registry_sources(project_dir: Path, sources: list[tuple[str, str | None, bool, str]]) -> None:
    (project_dir / "config" / "sources.json").write_text(
        json.dumps(
            {
                "project_id": "test_project",
                "sources": [
                    {
                        "source_id": source_id,
                        "enabled": enabled,
                        "access_method": "local_file",
                        "path": source_path,
                        "role": "context",
                        "buffer_feet": None,
                        "notes": "",
                        "status": status,
                    }
                    for source_id, source_path, enabled, status in sources
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_layer(path: Path) -> Path:
    gdf = gpd.GeoDataFrame([{"name": "Source Feature"}], geometry=[Point(-89.995, 32.0)], crs="EPSG:4326")
    path.write_text(gdf.to_json(drop_id=True), encoding="utf-8")
    return path


def write_failed_acquisition_manifest(project_dir: Path, source_id: str = "usfws_nwi_wetlands") -> Path:
    path = project_dir / "source_acquisition" / "source_acquisition_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "output_path": str(path),
                "download_count": 1,
                "downloads": [
                    {
                        "source_id": source_id,
                        "source_name": "National Wetlands Inventory",
                        "source_category": "wetlands_waterbodies",
                        "status": "failed",
                        "output_path": str(project_dir / "source_acquisition" / "downloads" / f"{source_id}.geojson"),
                    }
                ],
                "validation_issues": [
                    {
                        "severity": "warning",
                        "code": "source_download_failed",
                        "message": "Unable to download National Wetlands Inventory source.",
                        "source_id": source_id,
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def status_by_category(status_set: dict[str, object], category: str) -> dict[str, object]:
    return next(item for item in status_set["statuses"] if item["category"] == category)  # type: ignore[index]


def detail_by_source(status_record: dict[str, object], source_id: str) -> dict[str, object]:
    return next(detail for detail in status_record["source_details"] if detail["source_id"] == source_id)  # type: ignore[index]


def test_generate_project_context_writes_workflow_artifact(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    context = generate_project_context(project_dir)

    context_path = project_dir / "context" / "project_context.json"
    assert context_path.exists()
    assert context["project_id"] == "test_project"
    assert context["report_profile"]["profile_id"] == "environmental_constraints_example"
    assert context["project_extent_wgs84"]["west"] == pytest.approx(-90.0)
    assert context["detected_inputs"][0]["geometry_type_counts"] == {"LineString": 1}
    assert context["input_roles"] == ["alternatives"]
    assert context["assumptions"]["default_buffer_feet"] == 100
    assert context["validation_issues"][0]["code"] == "blank_placemark_name"


def test_generate_project_context_errors_for_missing_manifest(tmp_path: Path) -> None:
    with pytest.raises(ProjectContextError, match="Missing project manifest"):
        generate_project_context(tmp_path / "missing")


def test_report_profiles_load_and_resolve_defaults(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    location_project_dir = write_project(tmp_path / "location", project_type="location_review")
    config = load_report_profile_config()
    profile = resolve_report_profile(load_project_manifest(project_dir), config)
    location_profile = resolve_report_profile(load_project_manifest(location_project_dir), config)

    assert "environmental_constraints_example" in config.profiles
    assert "environmental_constraints_basic" in config.profiles
    assert profile.profile_id == "environmental_constraints_example"
    assert location_profile.profile_id == "location_screening_basic"
    assert "flood_hazard" in profile.required_categories
    assert "imagery_basemaps" in profile.required_categories


def test_explicit_basic_report_profile_still_resolves(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path, report_profile="environmental_constraints_basic")

    profile = resolve_report_profile(load_project_manifest(project_dir))

    assert profile.profile_id == "environmental_constraints_basic"
    assert "flood_hazard" in profile.optional_categories


def test_report_profile_config_rejects_invalid_profiles(tmp_path: Path) -> None:
    profile_path = tmp_path / "report_profiles.json"
    profile_path.write_text('{"profiles": {}}', encoding="utf-8")

    with pytest.raises(ReportProfileError, match="requires a non-empty list"):
        load_report_profile_config(profile_path)


def test_report_profile_resolution_errors_for_unknown_project_type(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path, project_type="unknown_review")

    with pytest.raises(ReportProfileError, match="No report profile configured"):
        resolve_report_profile(load_project_manifest(project_dir))


def test_source_status_marks_local_registered_source_provided(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    layer_path = write_layer(project_dir / "wetlands.geojson")
    write_registry(project_dir, "usfws_nwi_wetlands", "wetlands.geojson")

    status_set = resolve_source_status_set(project_dir)

    wetlands = status_by_category(status_set, "wetlands_waterbodies")
    assert wetlands["status"] == "provided_locally"
    assert str(layer_path) in wetlands["local_paths"]


def test_effective_source_status_suppresses_stale_failed_acquisition_when_local_materialized(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    layer_path = write_layer(project_dir / "wetlands.geojson")
    write_registry_sources(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson", True, "local_materialized")])
    acquisition_dir = project_dir / "source_acquisition"
    acquisition_dir.mkdir()
    (acquisition_dir / "source_acquisition_manifest.json").write_text(
        json.dumps(
            {
                "downloads": [
                    {
                        "source_id": "usfws_nwi_wetlands",
                        "source_name": "National Wetlands Inventory",
                        "source_category": "wetlands_waterbodies",
                        "status": "failed",
                        "output_path": str(project_dir / "source_acquisition" / "downloads" / "usfws_nwi_wetlands.geojson"),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    status_set = resolve_source_status_set(project_dir)
    lineage = build_data_lineage(project_dir)
    effective = effective_source_status(project_dir, "usfws_nwi_wetlands")

    wetlands = status_by_category(status_set, "wetlands_waterbodies")
    assert wetlands["status"] == "provided_locally"
    assert wetlands["report_caveat_flags"] == []
    assert effective["status"] == "local_materialized"
    assert effective["report_caveat_flags"] == []
    assert str(layer_path) in wetlands["local_paths"]
    assert not any(
        record.get("source_id") == "usfws_nwi_wetlands" and record.get("lineage_type") == "missing_stub"
        for record in lineage["records"]
    )
    assert any(issue["code"] == "stale_acquisition_record_ignored" for issue in lineage["validation_issues"])


def test_stale_source_acquisition_failure_is_not_report_facing_when_source_is_local_materialized(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "wetlands.geojson")
    write_registry_sources(project_dir, [("usfws_nwi_wetlands", "wetlands.geojson", True, "local_materialized")])
    acquisition_path = write_failed_acquisition_manifest(project_dir)

    status_set = resolve_source_status_set(project_dir)
    evidence = build_evidence_package(project_dir)
    deliverable_items = generate_deliverable_items(project_dir, gpt_drafting=False)
    review_queue = generate_review_queue(project_dir)

    acquisition_history = json.loads(acquisition_path.read_text(encoding="utf-8"))
    assert status_by_category(status_set, "wetlands_waterbodies")["report_caveat_flags"] == []
    assert any(issue["code"] == "source_download_failed" for issue in acquisition_history["validation_issues"])
    assert "source_download_failed" not in json.dumps(evidence)
    assert "source_download_failed" not in json.dumps(deliverable_items)
    assert "source_download_failed" not in json.dumps(review_queue)
    assert any(issue["code"] == "stale_acquisition_record_ignored" for issue in evidence["validation_issues"])


def test_true_failed_required_source_acquisition_remains_report_facing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("review_assist.source_status.maybe_load_seed_source_manifest", lambda source_id: None)
    project_dir = write_project(tmp_path)
    write_failed_acquisition_manifest(project_dir)

    status_set = resolve_source_status_set(project_dir)
    evidence = build_evidence_package(project_dir)

    wetlands = status_by_category(status_set, "wetlands_waterbodies")
    assert wetlands["status"] == "failed"
    assert "source_download_failed" in wetlands["report_caveat_flags"]
    assert any(issue["code"] == "source_download_failed" for issue in evidence["validation_issues"])


def test_logical_rollup_source_status_is_satisfied_by_specific_project_layers(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "flowlines.geojson")
    write_layer(project_dir / "waterbodies.geojson")
    write_layer(project_dir / "other_areas.geojson")
    write_registry_sources(
        project_dir,
        [
            ("usgs_nhd_flowlines", "flowlines.geojson", True, "local_materialized"),
            ("usgs_nhd_waterbodies", "waterbodies.geojson", True, "local_materialized"),
            ("usgs_nhd_other_areas", "other_areas.geojson", True, "local_materialized"),
        ],
    )

    resolve_source_status_set(project_dir)
    effective = effective_source_status(project_dir, "usgs_nhd_hydrography")

    assert effective["status"] == "logical_rollup_satisfied"
    assert effective["report_caveat_flags"] == []
    assert effective["source_need_class"] == "available_materialized"
    assert effective["satisfied_by_source_ids"] == [
        "usgs_nhd_flowlines",
        "usgs_nhd_other_areas",
        "usgs_nhd_waterbodies",
    ]


def test_regulated_facility_rollups_are_satisfied_by_specific_project_layers(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "frs.geojson")
    write_layer(project_dir / "ust.geojson")
    write_registry_sources(
        project_dir,
        [
            ("epa_frs_facilities_ms", "frs.geojson", True, "local_materialized"),
            ("maris_underground_storage_tanks", "ust.geojson", True, "local_materialized"),
        ],
    )

    resolve_source_status_set(project_dir)
    echo = effective_source_status(project_dir, "epa_envirofacts_echo")
    mdeq = effective_source_status(project_dir, "mdeq_environmental_context")

    assert echo["status"] == "logical_rollup_satisfied"
    assert echo["report_caveat_flags"] == []
    assert "epa_frs_facilities_ms" in echo["satisfied_by_source_ids"]
    assert echo["source_need_class"] == "available_materialized"
    assert mdeq["status"] == "manual"
    assert mdeq["source_need_class"] == "manual_reviewer_supplied"
    assert mdeq["satisfied_by_source_ids"] == []


def test_source_status_marks_public_candidate_downloadable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("review_assist.source_status.maybe_load_seed_source_manifest", lambda source_id: None)
    project_dir = write_project(tmp_path)

    status_set = resolve_source_status_set(project_dir)

    wetlands = status_by_category(status_set, "wetlands_waterbodies")
    assert wetlands["status"] == "downloadable"
    assert "source_not_downloaded" in wetlands["uncertainty_flags"]


def test_source_status_marks_seeded_warehouse_source_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "review_assist.source_status.maybe_load_seed_source_manifest",
        lambda source_id: {
            "source_id": source_id,
            "analysis_ready": True,
            "raw_paths": ["raw/source"],
        },
    )
    monkeypatch.setattr("review_assist.source_status.raw_paths_exist", lambda source_id: [{"raw_path": "raw/source", "exists": True}])
    project_dir = write_project(tmp_path)

    status_set = resolve_source_status_set(project_dir)

    wetlands = status_by_category(status_set, "wetlands_waterbodies")
    detail = detail_by_source(wetlands, "usfws_nwi_wetlands")
    assert wetlands["status"] == "needs_review"
    assert "local_warehouse_source_unmaterialized" in wetlands["uncertainty_flags"]
    assert detail["status"] == "warehouse_available"
    assert detail["source_need_class"] == "warehouse_available_not_materialized"


def test_source_status_marks_seeded_source_present_not_materialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "review_assist.source_status.maybe_load_seed_source_manifest",
        lambda source_id: {
            "source_id": source_id,
            "analysis_ready": False,
            "raw_paths": ["raw/source"],
        },
    )
    monkeypatch.setattr("review_assist.source_status.raw_paths_exist", lambda source_id: [{"raw_path": "raw/source", "exists": True}])
    project_dir = write_project(tmp_path)

    status_set = resolve_source_status_set(project_dir)

    wetlands = status_by_category(status_set, "wetlands_waterbodies")
    detail = detail_by_source(wetlands, "usfws_nwi_wetlands")
    assert wetlands["status"] == "present_not_materialized"
    assert "source_present_not_materialized" in wetlands["uncertainty_flags"]
    assert detail["status"] == "present_not_materialized"
    assert detail["source_need_class"] == "warehouse_available_not_materialized"


def test_source_status_marks_restricted_manual_category_gated(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)

    status_set = resolve_source_status_set(project_dir)

    cultural = status_by_category(status_set, "cultural_historic")
    assert cultural["status"] == "gated"
    assert "restricted_source_required" in cultural["uncertainty_flags"]
    mdah = detail_by_source(cultural, "mdah_restricted_archaeology")
    assert mdah["status"] == "restricted"


def test_source_status_marks_missing_required_category_nonfatal() -> None:
    result = _category_status(
        project_dir=Path("."),
        category="not_in_catalog",
        requirement="required",
        catalog_sources=[],
        project_sources={},
    )

    assert result["status"] == "missing"
    assert "source_unavailable" in result["uncertainty_flags"]


def test_source_status_marks_example_flood_hazard_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("review_assist.source_status.maybe_load_seed_source_manifest", lambda source_id: None)
    project_dir = write_project(tmp_path)

    status_set = resolve_source_status_set(project_dir)

    flood = status_by_category(status_set, "flood_hazard")
    assert flood["status"] == "downloadable"
    assert flood["requirement"] == "required"


def test_source_status_marks_basic_optional_category_nonblocking(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path, report_profile="environmental_constraints_basic")

    status_set = resolve_source_status_set(project_dir)

    flood = status_by_category(status_set, "flood_hazard")
    assert flood["status"] == "optional"
    assert flood["requirement"] == "optional"


def test_source_status_exposes_manual_unimplemented_and_census_stub_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    project_dir = write_project(tmp_path)

    status_set = resolve_source_status_set(project_dir)

    community = status_by_category(status_set, "community_socioeconomic")
    census = detail_by_source(community, "census_tiger_acs")
    businesses = detail_by_source(community, "local_business_economic_nodes")
    land_cover = status_by_category(status_set, "land_cover_disturbance")
    nlcd = detail_by_source(land_cover, "mrlc_nlcd_land_cover")
    attachments = status_by_category(status_set, "attachments")
    hazmat = detail_by_source(attachments, "hazardous_materials_support_report")

    assert census["status"] == "stubbed"
    assert "missing_census_api_key" in census["uncertainty_flags"]
    assert census["source_need_class"] == "deferred"
    assert businesses["status"] == "manual"
    assert businesses["source_need_class"] == "manual_reviewer_supplied"
    assert nlcd["status"] == "unimplemented"
    assert nlcd["source_need_class"] == "deferred"
    assert hazmat["status"] == "manual"
    assert hazmat["source_need_class"] == "manual_reviewer_supplied"
    assert "source_download_failed" not in hazmat["uncertainty_flags"]


def test_source_status_writes_section_source_needs_from_policy(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_layer(project_dir / "flowlines.geojson")
    write_registry_sources(
        project_dir,
        [("usgs_nhd_flowlines", "flowlines.geojson", True, "local_materialized")],
    )

    status_set = resolve_source_status_set(project_dir)

    needs_by_section = {
        str(item["section_id"]): item
        for item in status_set["section_source_needs"]  # type: ignore[index]
    }
    wetlands = needs_by_section["wetlands-and-waterbodies"]
    assert wetlands["inclusion_status"] == "default"  # type: ignore[index]
    assert wetlands["activation_condition"] == "source_backed_or_stub"  # type: ignore[index]
    assert "hydrography_crossings" in wetlands["source_categories"]  # type: ignore[operator]
    assert "usgs_nhd_flowlines" in wetlands["source_ids"]  # type: ignore[operator]
    flowline = next(need for need in wetlands["source_needs"] if need["source_id"] == "usgs_nhd_flowlines")  # type: ignore[index]
    assert flowline["source_need_class"] == "available_materialized"

    pel = needs_by_section["relationship-with-pel-study"]
    assert pel["section_need_status"] == "manual_reviewer_supplied"  # type: ignore[index]
    assert pel["source_need_classes"] == []  # type: ignore[index]

    cultural = needs_by_section["cultural-and-historic-resources"]
    public_context = next(need for need in cultural["source_needs"] if need["source_id"] == "maris_public_cultural_context")  # type: ignore[index]
    restricted_context = next(need for need in cultural["source_needs"] if need["source_id"] == "mdah_restricted_archaeology")  # type: ignore[index]
    assert public_context["source_need_class"] == "public_coarse_screening_context"
    assert restricted_context["source_need_class"] == "restricted_authorized_reviewer_supplied"


def test_source_status_marks_missing_local_source_needs_review(tmp_path: Path) -> None:
    project_dir = write_project(tmp_path)
    write_registry(project_dir, "usfws_nwi_wetlands", "missing.geojson")

    status_set = resolve_source_status_set(project_dir)

    wetlands = status_by_category(status_set, "wetlands_waterbodies")
    assert wetlands["status"] == "needs_review"
    assert "local_source_missing" in wetlands["uncertainty_flags"]


def test_cli_workflow_artifact_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["generate-context", str(project_dir)]) == 0
    assert main(["resolve-sources", str(project_dir)]) == 0

    captured = capsys.readouterr()
    assert "Generated context" in captured.out
    assert "Resolved sources" in captured.out
    assert (project_dir / "context" / "project_context.json").exists()
    assert (project_dir / "source_status" / "source_status_set.json").exists()


def test_cli_workflow_artifact_command_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_dir = write_project(tmp_path)

    assert main(["generate-context", str(project_dir), "--json"]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out)["project_id"] == "test_project"
