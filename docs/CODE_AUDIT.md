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
- Added tests for the validation and orchestration cases above.

## Current Verification

- Unit/integration tests pass for KMZ/KML ingestion, geometry summaries, source registry validation, local source registration, CLI error handling, synthetic spatial checks, project context/source status artifacts, deterministic draft finding generation, review queue behavior, and populate-for-review orchestration.
- CLI smoke checks pass for:
  - `review-assist list-sources projects/trails`
  - `review-assist analyze-project projects/trails`
  - `review-assist analyze-project projects/conexon_projects`
  - `review-assist generate-findings projects/trails`
  - `review-assist populate-for-review projects/trails`
  - `review-assist populate-for-review projects/conexon_projects`
  - `review-assist list-review-queue projects/trails`
  - `review-assist list-review-queue projects/conexon_projects`

## Known Limits

- Local source layers are supported; live public downloads are not implemented.
- Spatial analysis produces relationship records only. Deterministic draft finding generation is a separate service.
- Draft findings are template-driven and cautious, but they are still report-shaped screening records. They are not final findings, field verification, recommendations, or report sections.
- The review queue stores draft finding, source status, missing-data, validation, no-mapped, and spatial relationship items. It does not yet produce maps, tables, narrative, or export packages.
- `populate-for-review` orchestrates current services only. It does not download sources, call LLMs, render maps, draft prose, or compile exports.
- KMZ/KML ingestion supports Point, LineString, and Polygon parsing only.
- Source layer schemas are not normalized yet; feature labels are inferred from a small set of common name/label fields.
- Geometry repair is not implemented yet. Invalid source geometries may require cleanup before reliable analysis.
- Raster source analysis is cataloged but not implemented.
- Large local source layers should remain outside Git under ignored project `layers/` folders.

## Archive Review

No active tracked documentation was stale enough to archive during this pass. The existing archive locations remain:

- `archive/` for general retained but inactive project files.
- `docs/archive/` for superseded or historical documentation.
