from __future__ import annotations

import json
from pathlib import Path

import pytest

from review_assist.source_catalog import load_source_catalog, repo_root
from review_assist.source_warehouse import (
    indexed_source_ids,
    load_seed_source_manifest,
    load_source_warehouse_manifest,
    raw_paths_exist,
    source_manifest_path,
)


EXPECTED_STABLE_SOURCE_IDS = {
    "epa_frs_facilities_ms",
    "fema_nfhl_flood_hazard",
    "maris_brownfields",
    "maris_npdes_facilities",
    "maris_solid_waste_landfills",
    "maris_superfund_sites",
    "maris_tri_facilities",
    "maris_underground_storage_tanks",
    "mdeq_303d_impaired_waters",
    "mdeq_public_water_supply_wells",
    "mississippi_oil_gas_wells",
    "usgs_nhd_flowlines",
    "usgs_nhd_other_areas",
    "usgs_nhd_waterbodies",
    "usfws_national_wildlife_refuges",
    "usda_nrcs_easements",
    "usfws_nwi_wetlands",
    "usfws_critical_habitat",
    "usda_nrcs_ssurgo_soils",
    "mdot_transportation_context",
    "maris_public_cultural_context",
    "maris_boundary_context",
    "maris_community_facilities",
    "maris_conservation_recreation_lands",
    "local_utility_infrastructure",
    "maris_naip_2025_imagery",
}


def test_source_warehouse_manifest_indexes_stable_source_manifests() -> None:
    index = load_source_warehouse_manifest()
    indexed_ids = indexed_source_ids()

    assert index["source_count"] == len(index["sources"])
    assert EXPECTED_STABLE_SOURCE_IDS.issubset(indexed_ids)
    for source_id in EXPECTED_STABLE_SOURCE_IDS:
        manifest_path = source_manifest_path(source_id)
        manifest = load_seed_source_manifest(source_id)
        assert manifest_path.name == "source_manifest.json"
        assert manifest_path.exists()
        assert manifest["source_id"] == source_id
        assert manifest["raw_paths"]


def test_source_catalog_warehouse_source_ids_are_indexed() -> None:
    indexed_ids = indexed_source_ids()
    catalog = load_source_catalog()

    referenced_ids = {
        warehouse_source_id
        for source in catalog.sources.values()
        for warehouse_source_id in source.warehouse_source_ids
    }

    assert referenced_ids
    assert referenced_ids.issubset(indexed_ids)


def test_source_warehouse_raw_path_validation_uses_manifest_relative_paths(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "sources"
    source_dir = warehouse_root / "environmental" / "test_source"
    raw_dir = source_dir / "raw" / "Agency_Download"
    raw_dir.mkdir(parents=True)
    (source_dir / "source_manifest.json").write_text(
        json.dumps(
            {
                "source_id": "test_source",
                "display_name": "Test Source",
                "category": "regulated_facilities",
                "authority": "Test Authority",
                "warehouse_group": "environmental",
                "version": "test",
                "raw_paths": ["raw/Agency_Download"],
                "expected_geometry_type": "point",
                "analysis_ready": True,
                "renderable": True,
                "coverage": "test",
                "source_date": "test",
                "acquisition_method": "manual_seed",
                "known_limitations": [],
                "notes": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    index_path = warehouse_root / "source_warehouse_manifest.json"
    index_path.write_text(
        json.dumps(
            {
                "warehouse_version": "test",
                "root": "sources",
                "source_count": 1,
                "sources": [
                    {
                        "source_id": "test_source",
                        "category": "regulated_facilities",
                        "warehouse_group": "environmental",
                        "manifest_path": "environmental/test_source/source_manifest.json",
                        "analysis_ready": True,
                        "renderable": True,
                        "app_targets": ["test_source"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    raw_status = raw_paths_exist("test_source", index_path=index_path)

    assert raw_status == [{"raw_path": "raw/Agency_Download", "path": str(raw_dir.resolve()), "exists": True}]


def test_local_seeded_source_raw_paths_exist_when_bulk_sources_are_present() -> None:
    bulk_marker = repo_root() / "sources" / "wetlands" / "usfws_nwi_wetlands" / "raw" / "MS_geopackage_wetlands"
    if not bulk_marker.exists():
        pytest.skip("Bulk local sources are not present in this checkout.")

    missing: list[tuple[str, str]] = []
    for source_id in indexed_source_ids():
        for raw_status in raw_paths_exist(source_id):
            if not raw_status["exists"]:
                missing.append((source_id, raw_status["raw_path"]))

    assert missing == []
