# Sprint 2: Constraints, Tables, Figures, And Evidence

## Purpose

Implement the report-facing analysis layer on top of Sprint 1. This sprint converts comparison units and source data into exact deliverable tables, exact deliverable figures, and evidence packages while keeping raw GIS relationships out of the standard report path.

`CANONICAL_PLAN.md` is the canonical planning source for duplicated or conflicting workflow decisions. If current docs or existing service behavior duplicate and conflict with it, follow `CANONICAL_PLAN.md`.

## Sprint Outcome

By the end of this sprint, the repo should:

- Analyze constraints by comparison unit for report-facing outputs.
- Keep raw constraints as evidence, not standard report rows.
- Generate exact table targets from `config/deliverable_section_matrix.json`.
- Generate exact figure targets from `config/deliverable_section_matrix.json`.
- Select NAIP/MARIS basemaps and render them only from renderable sidecars.
- Create stubs for unavailable, missing, or unimplemented required deliverable targets.
- Update evidence packages so section generation has compact, aligned table/figure/source context.

## Non-UI Boundary

Do not implement:

- Web map previews.
- Interactive review screens.
- Browser rendering.
- Upload or file classification UI.

Everything should be service/CLI artifacts.

## Sub-Sprint Breakdown

- Completed Sprint 2.1: `docs/archive/sprints/SPRINT_2_1_SOURCE_PROFILE_AND_BASEMAPS.md` implemented the example report profile, source status behavior, NAIP/MARIS basemap service, and Census source setup.
- Completed Sprint 2.2: `docs/archive/sprints/SPRINT_2_2_COMPARISON_CONSTRAINTS_AND_TABLES.md` implemented comparison-unit constraints, source-specific normalization, and exact deliverable table generation.
- `SPRINT_2_3_FIGURES_EVIDENCE_AND_VALIDATION.md`: exact deliverable figures, panel map support, evidence package updates, and Sprint 2 validation.

## Sprint 1 Dependencies

This sprint assumes these Sprint 1 artifacts exist:

- `config/deliverable_section_matrix.json`
- `config/report_generation_prompts.json`
- `projects/<project_id>/context/input_package.json`
- `projects/<project_id>/context/project_area.json`
- `projects/<project_id>/intermediate/comparison_units.geojson`

If a Sprint 1 artifact is missing, this sprint's services should fail clearly or generate a validation issue, depending on whether the artifact is required for that operation.

## Workstream 1: Source/Profile Updates

### 1.1 Add an example-report profile

- Add or update a report profile for the example deliverable, likely:
  - `environmental_constraints_example`
- This profile should require every source category needed by the example deliverable shape.
- Missing sources must not block generation. They must produce stubs or source-gap review items.

### 1.2 Required categories for example profile

The profile should treat these as required deliverable categories:

- `wetlands_waterbodies`
- `hydrography_crossings`
- `flood_hazard`
- `species_habitat`
- `cultural_historic`
- `community_socioeconomic`
- `transportation_utilities`
- `regulated_facilities`
- `imagery_basemaps`
- `census_demographics` or the existing `community_socioeconomic` category with a distinct Census source requirement
- `attachments`

### 1.3 Stub categories

For categories with missing or unavailable data, generate the exact stub:

`Empty stub for future implements whenever source data is accessible.`

Likely stubbed/manual categories include:

- IPaC project report.
- State heritage data.
- Restricted MDAH archaeological review.
- MDEQ/manual environmental sources not yet available.
- Oil wells if no source exists.
- Airports if no source exists.
- Business/economic nodes if no source exists.
- Agency consultation letters.
- Hazardous materials support report.

### 1.4 Source status updates

- Update source status resolution so the example profile can distinguish:
  - source present and usable.
  - source present but no overlap.
  - source missing.
  - source unimplemented.
  - source manual.
  - source restricted.
  - source selected but not renderable.
  - source failed.
- Preserve the current behavior that failed supported downloads are nonfatal.

## Workstream 2: NAIP/MARIS Basemap Service

### 2.1 Basemap index

- Add a service module, likely `basemaps.py` or `imagery_basemaps.py`.
- Read the NAIP/MARIS warehouse:
  - `sources/aerial_base_maps/maris_naip_2025`
- Build an index with:
  - county name.
  - source directory.
  - `.sid` path.
  - sidecar metadata paths.
  - renderable sidecar paths.
  - world file paths if present.
  - validation status.

### 2.2 Preconverted sidecar rule

- Do not require in-app MrSID decoding.
- Treat `.sid` as source/provenance.
- Render basemap only when a renderable sidecar exists:
  - `.tif`
  - `.tiff`
  - `.png`
- If no renderable sidecar exists, the figure service should:
  - keep vector rendering.
  - include source/provenance note that NAIP source is selected but not renderable.
  - create a validation issue.
  - create the figure review target as a stub or vector-only figure depending on source requirements.

### 2.3 Raster dependency

- Add `rasterio` only if needed for GeoTIFF rendering.
- Do not add GDAL/MrSID system dependency as a hard requirement.
- If `rasterio` is unavailable, basemap rendering should degrade to vector-only with validation issues.

### 2.4 Basemap provenance

Every rendered figure using NAIP should record:

- source ID.
- source name.
- county/county folder.
- source `.sid` path.
- renderable sidecar path.
- basemap date/year.
- access/materialization date.
- limitations.
- attribution/source note.

## Workstream 3: Constraint Analysis By Comparison Unit

### 3.1 Standard report-facing input

- Update report-facing constraint generation to use `comparison_units.geojson`.
- Preserve existing `project_features.geojson` and raw constraint analysis for evidence.
- Make the standard downstream table/figure/report services consume comparison-unit results.

### 3.2 Constraint result additions

Add fields to report-facing constraint records:

- `comparison_unit_id`
- `comparison_unit_name`
- `comparison_unit_group`
- `comparison_unit_type`
- `raw_feature_ids`
- `raw_feature_count`
- `analysis_geometry_kind`
- `buffer_distance_feet`
- `buffer_method`
- `measurement_crs`
- `source_category`
- `source_id`
- `source_layer`
- `source_feature_label`
- `source_feature_type`
- `source_feature_subtype`
- `relationship_type`
- `measurements`
- `provenance`
- `uncertainty_flags`

### 3.3 Geometry measurement defaults

- Use `default_buffer_feet` as distance from the line geometry.
- Use 100 feet where the project does not override it.
- Store whether measurements came from:
  - raw geometry.
  - buffered corridor.
  - nearest distance calculation.
  - source-specific buffer.
- Use buffered corridor geometry for floodplain acreage and polygon overlap acreage on line alternatives.

### 3.4 Relationship types

Support or preserve:

- `intersects`
- `crosses`
- `overlaps`
- `contains`
- `nearest_within_buffer`
- `source_available_no_overlap`
- `source_unavailable`
- `requires_manual_review`

### 3.5 No-overlap handling

- Generate no-overlap evidence only where report-relevant.
- Do not create one review item per no-overlap source.
- Summarize no-overlap context in section evidence and stubs.

## Workstream 4: Source-Specific Normalization

### 4.1 NWI wetlands and waterbodies

Add canonical mapping for:

- Freshwater Emergent Wetland.
- Freshwater Forested/Shrub Wetland.
- Freshwater Pond.
- Other wetland/waterbody classes for evidence only.

Mapping should inspect available fields such as:

- `ATTRIBUTE`
- `WETLAND_TYPE`
- `SYSTEM`
- `CLASS_NAME`
- normalized `review_assist_feature_type`
- normalized `review_assist_feature_subtype`

### 4.2 Hydrography crossings

- Count stream/hydrography crossing hits by comparison unit.
- Prefer true line crossing relationships where possible.
- Include waterbody area relationships as evidence but do not inflate stream crossing counts unless explicitly classified as a crossing.
- De-duplicate repeated source features by original ID where available.

### 4.3 FEMA flood hazard

Normalize:

- `FLD_ZONE`
- `ZONE_SUBTY`
- `SFHA_TF`
- `SOURCE_CIT`
- effective/panel dates where available.

Aggregation must store:

- comparison unit.
- flood zone classification.
- acreage.
- buffer distance.
- source feature IDs.

### 4.4 Census demographics

- Add Census TIGER/ACS source support for tract geometry and ACS values.
- Use 2024 ACS 5-year by default when configured.
- Require a Census API key for API calls.
- If the key is missing, generate stubs.
- Do not infer equity or impact conclusions.
- Preserve margins of error where available if implemented.

### 4.5 Community facilities

Normalize facility subtype enough to support figure targets:

- fire/EMS.
- government offices.
- schools and childcare.
- health care.
- places of worship.
- parks/recreation.

If a local source lacks a subtype, generate a source warning rather than inventing a class.

### 4.6 Cultural resources

- Use public cultural layers only.
- Do not expose restricted archaeology.
- Restricted MDAH review remains manual/stubbed unless reviewer-supplied.

### 4.7 Utilities and infrastructure

Normalize enough to support:

- public water supply.
- utility infrastructure.
- energy infrastructure.
- airports as stub/manual unless data exists.

## Workstream 5: Exact Deliverable Tables

### 5.1 Table service refactor

- Keep existing broad comparison tables as evidence artifacts.
- Add deliverable table generation from the matrix, likely:
  - `src/review_assist/deliverable_tables.py`
- Output:
  - `projects/<project_id>/deliverable/tables.json`
- Standard export/review queue should use deliverable tables, not raw comparison tables.

### 5.2 Table artifact fields

Each table should include:

- `table_id`
- `table_number`
- `title`
- `section_target_id`
- `columns`
- `rows`
- `row_count`
- `source_refs`
- `related_constraint_ids`
- `comparison_unit_ids`
- `provenance`
- `uncertainty_flags`
- `is_stub`
- `stub_text`
- `review_status`

### 5.3 Wetlands and waterbodies table

- One row per comparison unit.
- Columns exactly:
  - `Alternative`
  - `Stream Crossings`
  - `Freshwater Emergent Wetland`
  - `Freshwater Forested/Shrub Wetland`
  - `Freshwater Pond`
- Values:
  - `Alternative`: comparison unit name.
  - `Stream Crossings`: de-duplicated crossing count from hydrography.
  - Wetland columns: de-duplicated NWI feature counts mapped to canonical class.
- Store acreage and length details in provenance/evidence, not visible table columns.

### 5.4 Floodplains and floodways table

- One row per comparison unit and flood zone classification.
- Columns exactly:
  - `Alternative`
  - `Flood Zone Classification`
  - `Estimated Acreage`
- Values:
  - `Alternative`: comparison unit name.
  - `Flood Zone Classification`: FEMA class and subtype where available.
  - `Estimated Acreage`: rounded acreage of buffered corridor overlap.
- If no flood intersection exists, include a concise no mapped intersection row only if the matrix policy requires every comparison unit to appear.

### 5.5 Income demographics table

- Columns exactly:
  - `Census Tract`
  - `Population Below the Poverty Line`
- Include rows for:
  - intersecting census tracts.
  - citywide value when available.
  - county value when available.
- If Census source unavailable, generate table stub.

### 5.6 Demographic composition table

- Columns exactly:
  - `Geography`
  - `Black or African American`
  - `Asian`
  - `White`
- Include rows for:
  - intersecting census tracts.
  - citywide value when available.
  - county value when available.
- If Census source unavailable, generate table stub.

## Workstream 6: Exact Deliverable Figures

### 6.1 Figure service refactor

- Keep current source-context maps as evidence if useful.
- Add deliverable figure generation from the matrix, likely:
  - `src/review_assist/deliverable_figures.py`
- Output:
  - `projects/<project_id>/deliverable/figures.json`
  - PNGs under `projects/<project_id>/maps/figures/`
- Standard review queue should use deliverable figures.

### 6.2 Figure artifact fields

Each figure should include:

- `figure_id`
- `figure_number`
- `title`
- `section_target_id`
- `image_path`
- `caption`
- `source_note`
- `method_note`
- `shown_layers`
- `source_refs`
- `comparison_unit_ids`
- `provenance`
- `uncertainty_flags`
- `is_stub`
- `stub_text`
- `review_status`

### 6.3 Figure targets and source rules

Generate or stub:

- Wetlands and Waterbodies:
  - Project comparison units.
  - NAIP basemap if renderable.
  - NWI wetlands/waterbodies.
  - Hydrography where available.
- FEMA Flood Zones:
  - Project comparison units.
  - FEMA flood hazard zones.
  - NAIP basemap if renderable.
- Streams and 303(d) Impaired Waters:
  - Hydrography.
  - Impaired waters if source exists.
  - Stub impaired waters if unimplemented.
- Cultural Resources:
  - Public cultural resources only.
  - No restricted archaeology locations.
- Fire Stations:
  - Fire/EMS point layer where available.
- Government Offices:
  - Government facility layer where available.
- Schools and Childcare:
  - Education/childcare layer where available.
- Health Care Facilities:
  - Health care layer where available.
- Places of Worship:
  - Places of worship layer where available.
- Public Water Supply Wells:
  - Public water supply wells layer where available.
- Energy Infrastructure:
  - Transmission/substation/pipeline/energy infrastructure layer where available.
- Hazardous Waste Sites:
  - EPA/ECHO and MDEQ/manual contamination sources where available.
- Census Tracts:
  - Census tract polygons and project comparison units.

### 6.4 Panel maps

- Add panel map capability for Attachment A only.
- Do not create unlimited figure-list items.
- Use panels when the project extent is too large to read at the standard 6.5 inch map width.
- Store panel map records as attachment-supporting deliverable items.
- Panel generation can start with simple fixed-grid or extent slicing; do not overbuild.

### 6.5 Map styling

- Preserve existing draft/pre-review labeling.
- Use readable symbology by resource category.
- Include:
  - legend.
  - north arrow.
  - scale bar where CRS allows.
  - source note.
  - method note.
  - caption.
- Target 6.5 inch figure width for DOCX embedding.

## Workstream 7: Evidence Package Updates

### 7.1 Evidence package structure

Update `projects/<project_id>/evidence/evidence_package.json` to include:

- comparison-unit summaries.
- deliverable table refs.
- deliverable figure refs.
- source-backed constraint summary by section target.
- stub/manual/missing source status by section target.
- validation issues by section target.
- raw evidence artifact paths.

### 7.2 Section evidence classes

Preserve and use:

- `source_backed`
- `source_available_no_overlap`
- `stub_or_manual`
- `failed_or_missing`
- `test_fixture_blocked`

### 7.3 Evidence size control

- Do not embed full raw geometry.
- Do not embed root `sources/` paths in GPT payloads.
- Keep raw constraint IDs and source refs, not full feature dumps.
- Provide compact counts, acreage, length, and status summaries.

## Workstream 8: Tests

### 8.1 Unit tests

Add tests for:

- NAIP index creation.
- NAIP selected but not renderable when only `.sid` exists.
- Raster sidecar detection.
- NWI class mapping.
- Hydrography crossing de-duplication.
- FEMA classification aggregation.
- Flood acreage by buffered comparison unit.
- Deliverable table generation with source-backed data.
- Deliverable table stubs when source data missing.
- Figure target generation and stubs.
- Evidence package section refs.

### 8.2 Mocked source tests

Add tests for:

- Census API success with mocked response.
- Census API missing key creates stubs.
- FEMA optional/required behavior under example profile.
- Public cultural resource figure excludes restricted source details.

### 8.3 Integration tests

Add tests for:

- `populate-for-review` produces deliverable tables and figures.
- Standard generated deliverable table count is 4 for the example profile.
- Standard generated figure target count is 13 for the example profile.
- Raw comparison tables remain available as evidence but are not standard deliverable targets.

### 8.4 Verification command

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Sprint Acceptance Checklist

- Comparison-unit constraints exist and are used for report-facing outputs.
- Raw constraints remain available as evidence.
- Four deliverable table targets are generated or stubbed.
- Thirteen figure targets are generated or stubbed.
- NAIP basemap provenance is stored.
- Missing renderable NAIP sidecars do not break map generation.
- Evidence package references deliverable tables and figures.
- No standard report artifact includes every raw GIS relationship by default.
- Tests pass.
