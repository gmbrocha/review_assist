"""Shared extent semantics for review artifacts.

This module labels existing pipeline artifacts. It does not create new query
buffers or change spatial analysis behavior.
"""

from __future__ import annotations

from typing import Any


EXTENT_POLICY_VERSION = "extent-policy-v1"

SUBMITTED_PROJECT_GEOMETRY = "submitted_project_geometry"
COMPARISON_UNITS = "comparison_units"
PROJECT_AREA_ANALYSIS_BOUNDS = "project_area_analysis_bounds"
DIRECT_INTERSECTION_EXTENT = "direct_intersection_extent"
SCREENING_BUFFER_EXTENT = "screening_buffer_extent"
NEARBY_CONTEXT_EXTENT = "nearby_context_extent"
COMMUNITY_CONTEXT_EXTENT = "community_context_extent"
WATERSHED_CONTEXT_EXTENT = "watershed_context_extent"
COUNTY_OR_REGIONAL_CONTEXT_EXTENT = "county_or_regional_context_extent"
FIGURE_RENDER_EXTENT = "figure_render_extent"
PRESENTATION_ONLY_COLLAR_EXTENT = "presentation_only_collar_extent"

EXTENT_FIELD_NAMES = (
    "query_extent_type",
    "query_distance",
    "query_units",
    "analysis_extent_type",
    "table_extent_type",
    "list_extent_type",
    "figure_extent_type",
    "render_extent_type",
    "render_extent_is_presentation_only",
    "interpretation_scope_label",
    "source_selection_reason",
)

DIRECT_CATEGORIES = {
    "wetlands_waterbodies",
    "flood_hazard",
    "species_habitat",
    "soils",
    "land_cover_disturbance",
}
NEARBY_CONTEXT_CATEGORIES = {
    "cultural_historic",
    "regulated_facilities",
    "transportation_utilities",
    "parcels_property",
    "conservation_public_lands",
    "imagery_basemaps",
}
COMMUNITY_CONTEXT_CATEGORIES = {"community_socioeconomic"}
WATERSHED_TARGET_IDS = {
    "water-quality",
    "streams-hydrography-crossings",
    "figure-streams-impaired-waters",
}
COUNTY_OR_REGIONAL_TARGET_IDS = {
    "demographics-and-socioeconomics",
    "income-demographics",
    "race-demographics",
    "figure-census-tracts",
    "table-income-demographics",
    "table-demographic-composition",
}
DIRECT_TARGET_IDS = {
    "oil-wells",
}


def base_extent_metadata(
    *,
    query_extent_type: str = PROJECT_AREA_ANALYSIS_BOUNDS,
    analysis_extent_type: str = DIRECT_INTERSECTION_EXTENT,
    query_distance: float | int | None = None,
    query_units: str = "",
    table_extent_type: str = "",
    list_extent_type: str = "",
    figure_extent_type: str = "",
    render_extent_type: str = "",
    render_extent_is_presentation_only: bool = False,
    interpretation_scope_label: str = "within the project area or comparison-unit screening geometry",
    source_selection_reason: str = "Existing automated checks use registered project-local source layers clipped to project_area_analysis_bounds.",
) -> dict[str, Any]:
    return {
        "query_extent_type": query_extent_type,
        "query_distance": _number_or_none(query_distance),
        "query_units": query_units,
        "analysis_extent_type": analysis_extent_type,
        "table_extent_type": table_extent_type,
        "list_extent_type": list_extent_type,
        "figure_extent_type": figure_extent_type,
        "render_extent_type": render_extent_type,
        "render_extent_is_presentation_only": bool(render_extent_is_presentation_only),
        "interpretation_scope_label": interpretation_scope_label,
        "source_selection_reason": source_selection_reason,
    }


def constraint_extent_metadata(
    *,
    relationship_type: str,
    analysis_geometry_kind: str,
    raw_intersects: bool,
    buffer_feet: float | int | None,
) -> dict[str, Any]:
    uses_screening_buffer = _uses_screening_buffer(
        relationship_type=relationship_type,
        analysis_geometry_kind=analysis_geometry_kind,
        raw_intersects=raw_intersects,
    )
    if uses_screening_buffer:
        return base_extent_metadata(
            query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
            analysis_extent_type=SCREENING_BUFFER_EXTENT,
            query_distance=buffer_feet,
            query_units="feet",
            interpretation_scope_label="within the comparison-unit screening buffer",
            source_selection_reason=(
                "The source layer was clipped to project_area_analysis_bounds, then compared "
                "against a buffered comparison-unit screening geometry."
            ),
        )
    return base_extent_metadata(
        query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
        analysis_extent_type=DIRECT_INTERSECTION_EXTENT,
        query_distance=0,
        query_units="feet",
        interpretation_scope_label="within the submitted project feature or comparison unit",
        source_selection_reason=(
            "The source layer was clipped to project_area_analysis_bounds, then compared "
            "against the submitted comparison-unit geometry."
        ),
    )


def no_overlap_extent_metadata(*, buffer_feet: float | int | None) -> dict[str, Any]:
    return base_extent_metadata(
        query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
        analysis_extent_type=SCREENING_BUFFER_EXTENT,
        query_distance=buffer_feet,
        query_units="feet",
        interpretation_scope_label="within the comparison-unit screening extent",
        source_selection_reason=(
            "The source was available in the project workspace, but no comparison-unit "
            "relationship was found within the current project_area_analysis_bounds "
            "and screening-buffer method."
        ),
    )


def target_extent_metadata(
    *,
    target_id: str = "",
    target_type: str = "",
    resource_category: str = "",
    source_categories: list[str] | tuple[str, ...] | None = None,
    query_distance: float | int | None = None,
    query_units: str = "",
) -> dict[str, Any]:
    category = _primary_category(resource_category, source_categories)
    scope = _scope_for_target(target_id, category)
    metadata = _metadata_for_scope(scope, query_distance=query_distance, query_units=query_units)
    if target_type == "table":
        metadata["table_extent_type"] = scope
    elif target_type == "figure":
        metadata["figure_extent_type"] = scope
        metadata["render_extent_type"] = FIGURE_RENDER_EXTENT
        metadata["render_extent_is_presentation_only"] = True
        metadata["source_selection_reason"] += (
            " Rendered map extent, including any legend collar, is presentation-only and does not drive evidence counts."
        )
    elif target_type in {"section", "subsection", "front_matter", "attachment", "dynamic_subsection_template"}:
        metadata["list_extent_type"] = scope
    return metadata


def render_extent_metadata(render_layout: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = base_extent_metadata(
        query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
        analysis_extent_type=DIRECT_INTERSECTION_EXTENT,
        render_extent_type=FIGURE_RENDER_EXTENT,
        render_extent_is_presentation_only=True,
        interpretation_scope_label="map rendering extent for geographic context",
        source_selection_reason="Figure render extent is presentation-only and does not drive counts, findings, source inclusion, or interpretation.",
    )
    if isinstance(render_layout, dict) and render_layout.get("collar_bounds"):
        metadata["presentation_extent_type"] = PRESENTATION_ONLY_COLLAR_EXTENT
    return metadata


def extent_metadata_from_record(record: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    return {field: record[field] for field in EXTENT_FIELD_NAMES if field in record}


def merge_extent_metadata(records: list[dict[str, Any]], fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    values = [extent_metadata_from_record(record) for record in records if isinstance(record, dict)]
    values = [value for value in values if value]
    if not values:
        return dict(fallback or {})
    merged = dict(fallback or {})
    for field in EXTENT_FIELD_NAMES:
        candidates = [_normalized_value(value.get(field)) for value in values if field in value]
        candidates = [candidate for candidate in candidates if candidate not in {"", None}]
        if not candidates:
            continue
        unique = []
        for candidate in candidates:
            if candidate not in unique:
                unique.append(candidate)
        if field == "render_extent_is_presentation_only":
            merged[field] = any(bool(candidate) for candidate in candidates)
        elif len(unique) == 1:
            merged[field] = unique[0]
        elif field in {"analysis_extent_type", "query_extent_type", "table_extent_type", "list_extent_type", "figure_extent_type"}:
            merged[field] = "mixed_extent_types"
            merged[f"{field}s"] = unique
        elif field == "interpretation_scope_label":
            merged[field] = "; ".join(str(item) for item in unique[:3])
        elif field == "source_selection_reason":
            merged[field] = " ".join(str(item) for item in unique[:3])
        else:
            merged[field] = unique[0]
    return merged


def apply_extent_metadata(record: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    for field in EXTENT_FIELD_NAMES:
        if field in metadata:
            record[field] = metadata[field]
    record["extent_policy_version"] = EXTENT_POLICY_VERSION
    return record


def extent_policy_summary() -> dict[str, Any]:
    return {
        "extent_policy_version": EXTENT_POLICY_VERSION,
        "extent_types": [
            SUBMITTED_PROJECT_GEOMETRY,
            COMPARISON_UNITS,
            PROJECT_AREA_ANALYSIS_BOUNDS,
            DIRECT_INTERSECTION_EXTENT,
            SCREENING_BUFFER_EXTENT,
            NEARBY_CONTEXT_EXTENT,
            COMMUNITY_CONTEXT_EXTENT,
            WATERSHED_CONTEXT_EXTENT,
            COUNTY_OR_REGIONAL_CONTEXT_EXTENT,
            FIGURE_RENDER_EXTENT,
            PRESENTATION_ONLY_COLLAR_EXTENT,
        ],
        "core_rule": "Rendered map extent and legend/basemap collar extent are presentation-only and must not drive counts, findings, source inclusion, or interpretation.",
    }


def extent_wording_for_scope(metadata: dict[str, Any]) -> str:
    extent_type = str(metadata.get("analysis_extent_type") or metadata.get("list_extent_type") or "")
    if extent_type == COMMUNITY_CONTEXT_EXTENT:
        return "near the project area"
    if extent_type == NEARBY_CONTEXT_EXTENT:
        return "in the project vicinity"
    if extent_type == WATERSHED_CONTEXT_EXTENT:
        return "within the watershed/subwatershed context"
    if extent_type == COUNTY_OR_REGIONAL_CONTEXT_EXTENT:
        return "within the county or regional context"
    if extent_type == SCREENING_BUFFER_EXTENT:
        return "within the screening buffer"
    return "within the project area"


def _uses_screening_buffer(*, relationship_type: str, analysis_geometry_kind: str, raw_intersects: bool) -> bool:
    if not analysis_geometry_kind.startswith("buffered"):
        return False
    if relationship_type == "nearest_within_buffer":
        return True
    return not raw_intersects


def _primary_category(resource_category: str, source_categories: list[str] | tuple[str, ...] | None) -> str:
    if resource_category:
        return resource_category
    for category in source_categories or []:
        if str(category).strip():
            return str(category)
    return "overall"


def _scope_for_target(target_id: str, category: str) -> str:
    if target_id in DIRECT_TARGET_IDS:
        return DIRECT_INTERSECTION_EXTENT
    if target_id in WATERSHED_TARGET_IDS:
        return WATERSHED_CONTEXT_EXTENT
    if target_id in COUNTY_OR_REGIONAL_TARGET_IDS:
        return COUNTY_OR_REGIONAL_CONTEXT_EXTENT
    if category in COMMUNITY_CONTEXT_CATEGORIES:
        return COMMUNITY_CONTEXT_EXTENT
    if category in NEARBY_CONTEXT_CATEGORIES:
        return NEARBY_CONTEXT_EXTENT
    if category == "hydrography_crossings":
        return DIRECT_INTERSECTION_EXTENT
    if category in DIRECT_CATEGORIES:
        return DIRECT_INTERSECTION_EXTENT
    return PROJECT_AREA_ANALYSIS_BOUNDS


def _metadata_for_scope(scope: str, *, query_distance: float | int | None, query_units: str) -> dict[str, Any]:
    if scope == COMMUNITY_CONTEXT_EXTENT:
        return base_extent_metadata(
            query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
            analysis_extent_type=COMMUNITY_CONTEXT_EXTENT,
            query_distance=query_distance,
            query_units=query_units,
            interpretation_scope_label="near the project area / community screening context",
            source_selection_reason=(
                "This report target is interpreted as nearby/community context. Current automated evidence "
                "uses project_area_analysis_bounds until a separate community_context_extent is implemented."
            ),
        )
    if scope == NEARBY_CONTEXT_EXTENT:
        return base_extent_metadata(
            query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
            analysis_extent_type=NEARBY_CONTEXT_EXTENT,
            query_distance=query_distance,
            query_units=query_units,
            interpretation_scope_label="near the project area / project vicinity screening context",
            source_selection_reason=(
                "This report target is interpreted as nearby context. Current automated evidence uses "
                "project_area_analysis_bounds until a separate nearby_context_extent is implemented."
            ),
        )
    if scope == WATERSHED_CONTEXT_EXTENT:
        return base_extent_metadata(
            query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
            analysis_extent_type=WATERSHED_CONTEXT_EXTENT,
            query_distance=query_distance,
            query_units=query_units,
            interpretation_scope_label="within the watershed/subwatershed context",
            source_selection_reason=(
                "Watershed/subwatershed context is a report-scope target. Current automated evidence remains "
                "limited to project_area_analysis_bounds until watershed_context_extent and 303(d) acquisition are implemented."
            ),
        )
    if scope == COUNTY_OR_REGIONAL_CONTEXT_EXTENT:
        return base_extent_metadata(
            query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
            analysis_extent_type=COUNTY_OR_REGIONAL_CONTEXT_EXTENT,
            query_distance=query_distance,
            query_units=query_units,
            interpretation_scope_label="within the county or regional context",
            source_selection_reason=(
                "This report target is interpreted as county/regional context. Current automated evidence uses "
                "available local source geometry intersecting project_area_analysis_bounds until county/regional querying is implemented."
            ),
        )
    if scope == SCREENING_BUFFER_EXTENT:
        return base_extent_metadata(
            query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
            analysis_extent_type=SCREENING_BUFFER_EXTENT,
            query_distance=query_distance,
            query_units=query_units or "feet",
            interpretation_scope_label="within the screening context area",
            source_selection_reason="Current automated evidence uses project_area_analysis_bounds and configured screening buffers.",
        )
    if scope == DIRECT_INTERSECTION_EXTENT:
        return base_extent_metadata(
            query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
            analysis_extent_type=DIRECT_INTERSECTION_EXTENT,
            query_distance=query_distance,
            query_units=query_units,
            interpretation_scope_label="within the project area or comparison-unit screening geometry",
            source_selection_reason="Current automated evidence uses registered project-local source layers clipped to project_area_analysis_bounds.",
        )
    return base_extent_metadata(
        query_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
        analysis_extent_type=PROJECT_AREA_ANALYSIS_BOUNDS,
        query_distance=query_distance,
        query_units=query_units,
        interpretation_scope_label="within the project-area analysis bounds",
        source_selection_reason="Current automated evidence uses project_area_analysis_bounds.",
    )


def _number_or_none(value: float | int | None) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _normalized_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(value)
    return value
