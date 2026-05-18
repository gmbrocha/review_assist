# Sprint 2.1: Source Profile And Basemaps

## Purpose

Prepare source/profile behavior for the example-report-shaped pipeline and implement basemap selection/renderability support. This sub-sprint does not generate final deliverable tables or figures yet; it makes the source categories and basemap context available for them.

`PLAN_REDIRECT_NEW.md` is the canonical planning source for duplicated or conflicting workflow decisions.

## Outcome

By the end of Sprint 2.1:

- An example-report profile exists or the existing profile is updated to require all example deliverable categories.
- Missing required sources create stubs or visible source statuses, not blockers.
- MARIS/NAIP 2025 imagery is represented as local basemap context.
- Basemap selection and renderable sidecar detection are service-level behavior.
- Census source setup is represented for later table generation.

## Dependencies

Sprint 1 artifacts:

- deliverable matrix.
- input package.
- project area.
- comparison units.

Existing code:

- source catalog.
- report profiles.
- source status.
- source inventory.
- project area basemap candidates.

## Implementation Tasks

### 1. Example Report Profile

- Add or update a profile, likely `environmental_constraints_example`.
- The profile should be selected by default for the redirected trails/example workflow when appropriate.
- Do not remove existing profiles unless explicitly needed.
- Ensure required categories match deliverable needs, not only current source availability.

### 2. Required Categories

The example profile should require:

- `wetlands_waterbodies`
- `hydrography_crossings`
- `flood_hazard`
- `species_habitat`
- `cultural_historic`
- `community_socioeconomic`
- `transportation_utilities`
- `regulated_facilities`
- `imagery_basemaps`
- Census/demographic support through either:
  - a new `census_demographics` category, or
  - a distinct required source under `community_socioeconomic`.

### 3. Manual/Stub Categories

Represent as manual/restricted/stubbed when source data is not accessible:

- IPaC project report.
- MDWFP / state heritage context.
- MDAH restricted archaeology.
- MDEQ manual environmental context where no repeatable source exists.
- Public water supply wells if no source exists.
- airports if no source exists.
- oil wells if no source exists.
- local businesses/economic nodes if no source exists.
- hazardous materials support report.
- agency consultation letters.

### 4. Source Status Behavior

Update source status resolution to distinguish:

- `present`
- `registered_local`
- `local_materialized`
- `downloaded`
- `downloadable`
- `optional`
- `manual`
- `restricted`
- `missing`
- `failed`
- `unimplemented`
- `selected_not_renderable`

If changing status names would be too disruptive, map these concepts into existing statuses plus notes and uncertainty flags.

### 5. Stub Policy

For required categories with missing/unimplemented/manual/restricted data:

- Do not fail populate.
- Preserve status in source status artifact.
- Preserve status in source inventory/evidence.
- Later deliverable targets use exact stub:
  - `Empty stub for future implements whenever source data is accessible.`

### 6. MARIS/NAIP Catalog Entry

Update catalog/source config so MARIS/NAIP local imagery can be referenced.

Expected source concept:

- source ID: `maris_naip_2025_imagery` or similar.
- category: `imagery_basemaps`.
- access method: local file/manual warehouse.
- geometry type: raster.
- limitations:
  - imagery is basemap/context.
  - imagery observations are not authoritative facts.
  - `.sid` requires preconverted sidecar for rendering.

### 7. Basemap Service

Create or extend a service, likely `basemaps.py`.

Functions:

- `build_basemap_index(root: Path) -> dict`
- `select_project_basemaps(project_dir: Path) -> dict`
- `renderable_sidecars_for(candidate: dict) -> list[Path]`

The service should read from project area county names and the NAIP root.

### 8. Renderability Policy

- `.sid` files are selected source/provenance files.
- `.sid` files are not assumed renderable.
- Renderable sidecars:
  - `.tif`
  - `.tiff`
  - `.png`
- If no renderable sidecar exists:
  - status `selected_not_renderable`.
  - validation issue.
  - vector-only maps can still be generated later.

### 9. Optional Raster Dependency Decision

- Add `rasterio` only if Sprint 2.3 needs GeoTIFF rendering.
- Do not require GDAL/MrSID support.
- Do not attempt Google, ArcGIS, or paid basemap APIs.
- Do not automate imagery acquisition in this sub-sprint.

### 10. Census Source Setup

- Add source catalog/profile metadata for Census TIGER/ACS if not adequate.
- Represent API key requirement clearly.
- Add environment variable convention if needed:
  - `CENSUS_API_KEY`
- Missing key should lead to source status/stub, not crash.
- Do not implement full Census table generation here unless it is small and isolated; Sprint 2.2 handles table outputs.

## Tests

Add tests for:

- example profile loads.
- flood hazard is required in example profile.
- imagery/basemap category is required.
- required manual categories become visible source statuses.
- MARIS/NAIP catalog entry exists.
- basemap index handles 82 county directories when source root exists.
- `.sid`-only county returns selected but not renderable.
- renderable sidecar detection finds `.tif`, `.tiff`, or `.png`.
- missing basemap root produces warning, not crash.
- missing Census key creates source status/stub condition.

Suggested command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_source_status.py tests\test_source_inventory_and_tables.py tests\test_project_area.py
```

## Acceptance Checklist

- Example report source profile exists.
- Missing mandatory categories are non-blocking and visible.
- MARIS/NAIP imagery is cataloged.
- Basemap service/index exists.
- `.sid` renderability is handled honestly.
- Census source requirement is represented.
- No UI work is introduced.
- Focused tests pass.
