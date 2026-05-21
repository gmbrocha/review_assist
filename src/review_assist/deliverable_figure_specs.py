"""Static specifications and constants for matrix-backed deliverable figures."""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_REVIEW_STATUSES = {
    "draft",
    "needs_review",
    "accepted",
    "edited",
    "rejected",
    "needs_verification",
    "unable_to_verify",
}
USABLE_SOURCE_STATUSES = {
    "analyzed",
    "analyzed_empty",
    "downloaded",
    "local_materialized",
    "provided_in_input",
    "registered_local",
}
UNIMPLEMENTED_SOURCE_STATUSES = {"unimplemented", "manual", "stubbed"}
MISSING_SOURCE_STATUSES = {
    "missing",
    "source_missing",
    "source_unreadable",
    "failed",
    "downloadable",
    "optional",
    "gated",
    "restricted",
    "unsupported_download",
    "needs_review",
    "selected_not_renderable",
    "warehouse_available",
    "present_not_materialized",
}
RESTRICTED_CULTURAL_SOURCE_ID = "mdah_restricted_archaeology"
PUBLIC_CULTURAL_SOURCE_IDS = {"maris_public_cultural_context", "mdah_public_historic_resources"}
NHD_ROLLUP_SOURCE_ID = "usgs_nhd_hydrography"
NHD_PHYSICAL_SOURCE_IDS = ("usgs_nhd_flowlines", "usgs_nhd_waterbodies", "usgs_nhd_other_areas")
NHD_SOURCE_IDS = (NHD_ROLLUP_SOURCE_ID, *NHD_PHYSICAL_SOURCE_IDS)
IMPAIRED_WATERS_SOURCE_IDS = ("mdeq_303d_impaired_waters",)
HAZARDOUS_REGULATED_SOURCE_IDS = (
    "epa_frs_facilities_ms",
    "maris_brownfields",
    "maris_superfund_sites",
    "maris_tri_facilities",
    "maris_underground_storage_tanks",
)
WATER_DISCHARGE_WASTE_SOURCE_IDS = (
    "maris_npdes_facilities",
    "maris_solid_waste_landfills",
)
OIL_GAS_SOURCE_IDS = (
    "mississippi_oil_gas_wells",
)
REGULATED_FACILITY_SOURCE_IDS = (
    *HAZARDOUS_REGULATED_SOURCE_IDS,
    *WATER_DISCHARGE_WASTE_SOURCE_IDS,
    *OIL_GAS_SOURCE_IDS,
)
RENDERABLE_BASEMAP_SUFFIXES = {".tif", ".tiff", ".png"}
PANEL_ASPECT_THRESHOLD = 2.75
MAX_PANEL_COUNT = 6


@dataclass(frozen=True)
class TargetFigureSpec:
    required_source_ids: tuple[str, ...]
    filter_tokens: tuple[str, ...] = ()
    source_unimplemented_note: str = ""
    prefer_basemap: bool = True
    optional_source_ids: tuple[str, ...] = ()
    excluded_source_ids: tuple[str, ...] = ()

    @property
    def source_ids(self) -> tuple[str, ...]:
        """All source IDs this figure is allowed to render, excluding prohibited carryover IDs."""

        excluded = set(self.excluded_source_ids)
        return _dedupe_source_ids(self.required_source_ids, self.optional_source_ids, exclude=excluded)


def _dedupe_source_ids(*groups: tuple[str, ...], exclude: set[str] | None = None) -> tuple[str, ...]:
    excluded = exclude or set()
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for source_id in group:
            if not source_id or source_id in excluded or source_id in seen:
                continue
            result.append(source_id)
            seen.add(source_id)
    return tuple(result)


TARGET_SPECS: dict[str, TargetFigureSpec] = {
    "figure-wetlands-waterbodies": TargetFigureSpec(
        ("usfws_nwi_wetlands",),
        prefer_basemap=True,
        optional_source_ids=("usgs_nhd_waterbodies",),
        excluded_source_ids=(
            NHD_ROLLUP_SOURCE_ID,
            "usgs_nhd_flowlines",
            "usgs_nhd_other_areas",
            *IMPAIRED_WATERS_SOURCE_IDS,
        ),
    ),
    "figure-fema-flood-zones": TargetFigureSpec(
        ("fema_nfhl_flood_hazard",),
        prefer_basemap=True,
    ),
    "figure-streams-impaired-waters": TargetFigureSpec(
        (*NHD_PHYSICAL_SOURCE_IDS, *IMPAIRED_WATERS_SOURCE_IDS),
        excluded_source_ids=(NHD_ROLLUP_SOURCE_ID, "usfws_nwi_wetlands"),
    ),
    "figure-cultural-resources": TargetFigureSpec(
        ("maris_public_cultural_context", "mdah_public_historic_resources"),
        excluded_source_ids=(RESTRICTED_CULTURAL_SOURCE_ID,),
    ),
    "figure-fire-ems-stations": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure"),
        ("fire", "ems", "emergency", "rescue"),
    ),
    "figure-government-offices": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure"),
        ("government", "courthouse", "city hall", "town hall", "municipal", "county", "office", "civic"),
    ),
    "figure-schools-childcare": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure", "census_tiger_acs"),
        ("school", "childcare", "child care", "daycare", "day care", "education", "college", "university"),
    ),
    "figure-health-care-facilities": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure"),
        ("hospital", "clinic", "health", "medical", "urgent care", "nursing"),
    ),
    "figure-places-of-worship": TargetFigureSpec(
        ("maris_community_facilities", "hifld_community_infrastructure"),
        ("worship", "church", "synagogue", "mosque", "temple", "chapel"),
    ),
    "figure-public-water-supply-wells": TargetFigureSpec(
        ("mdeq_public_water_supply_wells",),
    ),
    "figure-energy-infrastructure": TargetFigureSpec(
        ("local_utility_infrastructure",),
        ("electric", "transmission", "substation", "pipeline", "power", "energy", "utility"),
    ),
    "figure-hazardous-waste-sites": TargetFigureSpec(
        HAZARDOUS_REGULATED_SOURCE_IDS,
        excluded_source_ids=(*WATER_DISCHARGE_WASTE_SOURCE_IDS, *OIL_GAS_SOURCE_IDS, "epa_envirofacts_echo"),
    ),
    "figure-water-discharge-waste-facilities": TargetFigureSpec(
        WATER_DISCHARGE_WASTE_SOURCE_IDS,
        excluded_source_ids=(*HAZARDOUS_REGULATED_SOURCE_IDS, *OIL_GAS_SOURCE_IDS, "epa_envirofacts_echo"),
    ),
    "figure-oil-gas-wells": TargetFigureSpec(
        OIL_GAS_SOURCE_IDS,
        excluded_source_ids=(*HAZARDOUS_REGULATED_SOURCE_IDS, *WATER_DISCHARGE_WASTE_SOURCE_IDS, "epa_envirofacts_echo"),
    ),
    "figure-census-tracts": TargetFigureSpec(
        ("census_tiger_acs",),
    ),
}
