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
}
RESTRICTED_CULTURAL_SOURCE_ID = "mdah_restricted_archaeology"
PUBLIC_CULTURAL_SOURCE_IDS = {"maris_public_cultural_context", "mdah_public_historic_resources"}
RENDERABLE_BASEMAP_SUFFIXES = {".tif", ".tiff", ".png"}
PANEL_ASPECT_THRESHOLD = 2.75
MAX_PANEL_COUNT = 6


@dataclass(frozen=True)
class TargetFigureSpec:
    source_ids: tuple[str, ...]
    filter_tokens: tuple[str, ...] = ()
    source_unimplemented_note: str = ""
    prefer_basemap: bool = False


TARGET_SPECS: dict[str, TargetFigureSpec] = {
    "figure-wetlands-waterbodies": TargetFigureSpec(
        ("usfws_nwi_wetlands", "usgs_nhd_hydrography"),
        prefer_basemap=True,
    ),
    "figure-fema-flood-zones": TargetFigureSpec(
        ("fema_nfhl_flood_hazard",),
        prefer_basemap=True,
    ),
    "figure-streams-impaired-waters": TargetFigureSpec(
        ("usgs_nhd_hydrography",),
        source_unimplemented_note="303(d) impaired-water layer rendering is not implemented for Sprint 2.3; hydrography is shown when available.",
    ),
    "figure-cultural-resources": TargetFigureSpec(
        ("maris_public_cultural_context", "mdah_public_historic_resources"),
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
        ("epa_envirofacts_echo", "mdeq_environmental_context", "mississippi_oil_gas_wells"),
    ),
    "figure-census-tracts": TargetFigureSpec(
        ("census_tiger_acs",),
    ),
}
