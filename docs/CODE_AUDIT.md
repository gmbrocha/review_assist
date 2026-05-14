# Code Audit

This document records the latest implementation audit for the current prototype codebase.

## Audit Date

2026-05-14

## Scope Reviewed

- Phase 1 KMZ/KML ingestion and geometry inspection services.
- Phase 2A source catalog and project source registry services.
- Phase 2B local source-layer spatial relationship analysis.
- Phase 3 project context/source status services.
- Phase 4 review queue generation/update services.
- Phase 5 populate-for-review orchestration.
- Phase 6A deterministic draft finding generation.
- Phase 6B source inventory/provenance and comparison table generation.
- Phase 6C vector-only map/figure generation.
- Phase 6D deterministic draft report section generation.
- CLI commands for project inspection, source listing, local source registration, project analysis, review queue operations, and populate-for-review.
- Tests and active documentation.

## Fixes Made

- Tightened project manifest validation so input entries must be JSON objects and `assumptions` must be an object.
- Tightened project source registry validation:
  - `enabled` must be a real JSON boolean, not a string such as `"false"`.
  - `source_id` values cannot be duplicated in a project registry.
  - Project source registry `project_id` must match the project manifest.
  - Source entries must be JSON objects.
  - Local source paths cannot be blank when present.
  - Access methods must be non-empty strings.
  - Source-specific buffer overrides must be zero or greater.
- Tightened catalog validation so category entries must be JSON objects.
- Tightened spatial analysis validation so project default buffers must be zero or greater.
- Added tolerant spatial analysis behavior for populate-for-review while keeping `analyze-project` strict.
- Added populate run manifests with step status, artifact paths, review queue count, warnings, and critical error text.
- Added deterministic draft finding generation from source status records, spatial relationships, and analyzed local sources with no mapped relationships.
- Added finding template config validation and draft finding artifact validation, including required fields, duplicate finding IDs, status validation, and list/object field checks.
- Added draft finding review queue items with deterministic item IDs so existing reviewer status and notes survive regeneration.
- Added `generate-findings` CLI coverage and wired finding generation into `populate-for-review`.
- Tightened no-mapped finding generation to tolerate malformed relationship-count values in JSON artifacts.
- Added optional project source registry metadata for citation, attribution, licensing/terms, source URL, date fields, and reviewer notes.
- Added source inventory generation that merges catalog, project registry, source status, local file metadata, and validation issues.
- Added comparison table generation for source status, spatial relationships, and draft finding summaries.
- Added source inventory and comparison table review queue items with deterministic IDs and preview metadata.
- Wired source inventory and comparison tables into `populate-for-review`.
- Tightened source inventory artifact validation so `record_count` must match the record list.
- Tightened comparison table artifact validation so `table_count`, row counts, and table review statuses are checked clearly.
- Hardened review queue generation against malformed nonnumeric relationship/table counts and non-list optional validation fields in local JSON artifacts.
- Hardened numeric validation so JSON booleans are not accepted as `section_order`, source-specific `buffer_feet`, or project `default_buffer_feet` values.
- Added vector-only map generation with Matplotlib, including project overview and local source-context PNG figures.
- Added map manifest validation for figure count, required figure fields, duplicate figure IDs, PNG paths, review status, provenance, and list fields.
- Added map figure review queue items with deterministic IDs and image preview metadata.
- Wired map generation into `populate-for-review` before review queue generation.
- Kept map-generation warnings aggregated at the manifest level to avoid duplicate populate run warnings.
- Hardened map rendering so project-overview render failures fail clearly, source-context render failures become nonfatal validation issues, and Matplotlib figures close even when rendering fails.
- Added review queue validation issue items for map-generation warnings so failed or skipped source-context figures remain reviewable.
- Added deterministic draft report section generation from project context, source status, source inventory, draft findings, comparison tables, map manifests, and validation issues.
- Added report section template config validation and report section artifact validation, including required fields, duplicate section IDs, section counts, status validation, and list/object field checks.
- Added report section review queue items with deterministic IDs and section metadata so reviewer state survives regeneration.
- Wired report section generation into `populate-for-review` after map generation and before review queue generation.
- Kept report section top-level validation issues empty unless section generation itself creates a new issue, so upstream validation issues do not become duplicate populate warnings or duplicate validation queue items.
- Tightened limitations and reviewer follow-up section statuses so unresolved missing/gated/stubbed source categories require review or verification instead of remaining draft.
- Hardened review queue regeneration so accepted/edited/rejected/noted reviewer state is preserved, while untouched stale generated `draft` statuses can be upgraded by stricter regenerated defaults.
- Removed an unused report-section slug helper/import during the interim audit.
- Added tests for the validation and orchestration cases above.

## Current Verification

- Unit/integration tests pass for KMZ/KML ingestion, geometry summaries, source registry validation, local source registration, CLI error handling, synthetic spatial checks, project context/source status artifacts, source inventory/provenance generation, deterministic draft finding generation, comparison table generation, vector-only map generation, deterministic draft report section generation, map render-error handling, review queue behavior, malformed artifact handling, and populate-for-review orchestration.
- Current full test run: `111 passed`.
- CLI smoke checks pass for:
  - `review-assist list-sources projects/trails`
  - `review-assist analyze-project projects/trails`
  - `review-assist analyze-project projects/conexon_projects`
  - `review-assist generate-source-inventory projects/trails`
  - `review-assist generate-findings projects/trails`
  - `review-assist generate-tables projects/trails`
  - `review-assist generate-maps projects/trails`
  - `review-assist generate-maps projects/conexon_projects`
  - `review-assist generate-report-sections projects/trails`
  - `review-assist generate-report-sections projects/conexon_projects`
  - `review-assist populate-for-review projects/trails`
  - `review-assist populate-for-review projects/conexon_projects`
  - `review-assist list-review-queue projects/trails`
  - `review-assist list-review-queue projects/conexon_projects`

## Known Limits

- Local source layers are supported; live public downloads are not implemented.
- Spatial analysis produces relationship records only. Deterministic draft finding generation is a separate service.
- Draft findings are template-driven and cautious, but they are still report-shaped screening records. They are not final findings, field verification, recommendations, or final report sections.
- Source inventory, comparison table, map figure, and report section artifacts are descriptive workflow state. They are not final citations, final report tables, final report maps, final report prose, or export packages until reviewed.
- The review queue stores source inventory, draft finding, comparison table, map figure, report section, source status, missing-data, validation, no-mapped, and spatial relationship items. It does not yet compile export packages.
- `populate-for-review` orchestrates current services only. It does not download sources, call LLMs, render basemap/imagery-backed maps, or compile exports.
- KMZ/KML ingestion supports Point, LineString, and Polygon parsing only.
- Source layer schemas are not normalized yet; feature labels are inferred from a small set of common name/label fields.
- Geometry repair is not implemented yet. Invalid source geometries may require cleanup before reliable analysis.
- Raster source analysis is cataloged but not implemented.
- Basemap/imagery acquisition, panel map sheets, and final map export packages are not implemented.
- Large local source layers should remain outside Git under ignored project `layers/` folders.

## Archive Review

No active tracked documentation was stale enough to archive during this pass. The existing archive locations remain:

- `archive/` for general retained but inactive project files.
- `docs/archive/` for superseded or historical documentation.
