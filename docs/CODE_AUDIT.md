# Code Audit

This document records the latest implementation audit for the current prototype codebase.

## Audit Date

2026-05-15

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
- Constraint-engine project geometry normalization and constraint overlap/proximity analysis.
- Markdown/DOCX export package generation, internal demo deliverable packaging, and real-data MVP deliverable guardrails.
- CLI commands for project inspection, source listing, local source registration, project analysis, project geometry, constraint analysis, review queue operations, Markdown/DOCX report export, demo deliverable export, and populate-for-review.
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
- Added active sample workspace smoke tests for `projects/trails` and `projects/conexon_projects`.
- Added `scripts/verify.ps1` as a repeatable local readiness check that installs dependencies, runs pytest, and smoke-checks current CLI workflows.
- Added normalized project geometry artifacts for point/site, line/corridor, polygon/area, and mixed project contexts.
- Added constraint result artifacts based on registered local source layers cropped to project analysis bounds.
- Added `build-project-geometry` and `analyze-constraints` CLI commands.
- Wired constraint results into draft findings, comparison tables, populate-for-review manifests, and lean review queue validation handling.
- Changed review queue generation to default to a lean queue; source inventory review items are now opt-in with `include_source_inventory` or `--include-source-inventory`.
- Added a deterministic section-drafting provider interface as the future GenAI insertion point.
- Added tests for the validation and orchestration cases above.
- Added catalog-driven source gap resolution and acquisition manifests under `projects/<project_id>/source_acquisition/`.
- Added opt-in USFWS NWI wetlands downloader using the public Wetlands REST MapServer layer.
- Added opt-in USGS NHD hydrography downloads using The National Map NHD flowline and area layers.
- Added opt-in USFWS Critical Habitat downloads using the public final and proposed Critical Habitat FeatureServer layers.
- Added optional FEMA NFHL effective Flood Hazard Zones downloads that run only when directly requested or optional source acquisition is explicitly included.
- Added normalized downloaded-source fields for implemented NWI, NHD, Critical Habitat, and FEMA layers while preserving original source attributes.
- Added `resolve-source-gaps`, `download-source`, and `prepare-sources` CLI commands.
- Added `populate-for-review --prepare-sources` so supported public downloads can run before source status, inventory, constraints, findings, tables, maps, sections, and review queue generation.
- Tightened `populate-for-review` CLI validation so `--include-optional-sources` cannot be used without `--prepare-sources`.
- Preserved reviewer-supplied local source layers so downloads do not overwrite them.
- Added support for project inputs tagged with `source_id` or unambiguous `source_category` as provided source layers.
- Added source acquisition provenance into source inventory records when an acquisition manifest exists.
- Added tests for mocked NWI, NHD, Critical Habitat, and FEMA download success/failure, non-overwrite behavior, optional-source behavior, prepare-sources integration, CLI commands, and populate-for-review opt-in download behavior.
- Expanded report section templates to mirror the environmental constraints report destination more closely, including front matter, executive summary, study area, methodology, constraints inventory, resource sections, conclusion/next steps, attachments, and reviewer follow-up.
- Added report section export grouping plus explicit visual/table slots so generated section artifacts can carry map, figure, and table needs into review and export.
- Added review queue export grouping metadata while preserving reviewer state across regeneration, including backward-compatible normalization for older generated queue files.
- Added Markdown/DOCX export package generation under `projects/<project_id>/exports/`, including `environmental_constraints_report.md`, `environmental_constraints_report.docx`, and `export_manifest.json`.
- Added `export-report <project_dir>` and `export-report <project_dir> --include-draft` CLI coverage. Default exports include accepted/edited review items plus explicitly export-eligible unable-to-verify items; preview exports are clearly marked non-final.
- Added `export-report --format markdown|docx|both` and `build-demo-deliverable <project_dir>` CLI coverage for internal preview deliverable packages that do not auto-accept review items.
- Added export validation warnings for missing accepted sections, missing accepted maps, and unresolved required source gaps.
- Added tests for export filtering, edited-content precedence, unable-to-verify eligibility, section ordering, preview export mode, reviewer edit preservation, and NWI-backed export flow.
- Added `data_lineage` summaries to export and deliverable manifests so real project inputs, registered local sources, provided-in-input sources, downloaded public sources, stubs, and test/mock records are visible.
- Added `data_authenticity` metadata for registered/provided/downloaded source layers, deterministic missing-source stubs, and test fixture download paths.
- Added `Real Data Used` and `Stubs / Manual Review Needed` sections to Markdown/DOCX exports.
- Added `build-mvp-deliverable <project_dir>` CLI coverage for real-data guarded MVP preview packages that run source preparation before export.
- Added MVP guardrails that fail when no real source layer is available by default and fail when included content contains test fixture/mock source provenance.
- Added tests for data lineage classification, MVP no-real-source blocking, test-fixture blocking, real provided-source success, and MVP CLI JSON output.
- Fixed failed supported source downloads so the source acquisition manifest propagates `failed` status into source status, deterministic findings, report sections, and review queue caveat items instead of falling back to generic `downloadable` language.
- Carried FEMA flood hazard datum and length-unit fields through the constraint-to-table path for report-ready flood summaries.
- Updated FEMA date-field fallbacks so effective, panel, and revert dates are considered before generic date fields.
- Removed an unused source-status review item helper from the lean review queue implementation.
- Simplified Markdown export item partitioning so inclusion/skipping rules are evaluated once per review queue item.
- Avoided double-counting existing reviewer-supplied local sources in lineage when a public download is skipped to preserve the local layer.
- Reviewed active documentation for stale export/source-status language and updated architecture, workflow, data-source, review-policy, roadmap, current-state, product, README, and agent guidance docs.

## Current Verification

- Unit/integration tests pass for KMZ/KML ingestion, geometry summaries, source registry validation, local source registration, CLI error handling, synthetic spatial checks, project geometry normalization, constraint analysis, active sample workspace smoke checks, project context/source status artifacts, source acquisition failure propagation, source inventory/provenance generation, deterministic draft finding generation, comparison table generation, vector-only map generation, deterministic draft report section generation, map render-error handling, review queue behavior, Markdown/DOCX export compilation, demo deliverable package generation, malformed artifact handling, and populate-for-review orchestration.
- Current full test run: `179 passed`.
- CLI smoke checks pass for:
  - `review-assist list-sources projects/trails`
  - `review-assist build-project-geometry projects/trails`
  - `review-assist build-project-geometry projects/conexon_projects`
  - `review-assist analyze-constraints projects/trails`
  - `review-assist analyze-constraints projects/conexon_projects`
  - `review-assist analyze-project projects/trails`
  - `review-assist analyze-project projects/conexon_projects`
  - `review-assist generate-source-inventory projects/trails`
  - `review-assist generate-findings projects/trails`
  - `review-assist generate-tables projects/trails`
  - `review-assist generate-maps projects/trails`
  - `review-assist generate-maps projects/conexon_projects`
  - `review-assist generate-report-sections projects/trails`
  - `review-assist generate-report-sections projects/conexon_projects`
  - `review-assist resolve-source-gaps projects/trails`
  - `review-assist populate-for-review projects/trails`
  - `review-assist populate-for-review projects/conexon_projects`
  - `review-assist export-report projects/trails --include-draft --format both`
  - `review-assist build-demo-deliverable projects/trails --format both`
  - `review-assist build-mvp-deliverable projects/trails --include-optional-sources`
  - `review-assist list-review-queue projects/trails`
  - `review-assist list-review-queue projects/conexon_projects`

## Known Limits

- Local source layers are supported; opt-in USFWS NWI, USGS NHD, USFWS Critical Habitat, and EPA/ECHO regulated facility downloads are implemented, and FEMA NFHL effective flood hazard downloads are implemented as optional explicit context. Other public downloaders are not implemented yet.
- Legacy spatial analysis produces relationship records only. The constraint engine now produces first-class constraint result records for the main populate-for-review flow.
- Draft findings are template-driven and cautious, but they are still report-shaped screening records. They are not final findings, field verification, recommendations, or final report sections.
- Source inventory, comparison table, map figure, and report section artifacts are descriptive workflow state. They are not final citations, final report tables, final report maps, or final report prose until reviewed.
- The review queue defaults to draft finding, comparison table, map figure, report section, report-relevant missing-data, validation, and no-mapped items. Source inventory/provenance items are opt-in for audit workflows, and legacy spatial relationship items remain available when those artifacts exist. Export compilation now uses review queue status and export eligibility instead of every generated artifact, and MVP deliverable generation additionally checks real-data lineage before packaging.
- `populate-for-review` orchestrates current services only. It downloads supported sources only when `--prepare-sources` is used; it does not call LLMs, render basemap/imagery-backed maps, or create final PDF/template-grade DOCX exports.
- KMZ/KML ingestion supports Point, LineString, and Polygon parsing only.
- Downloaded NWI, NHD, Critical Habitat, EPA/ECHO, and FEMA layers now receive normalized feature fields, but broader source schema normalization is not implemented for every cataloged source.
- Geometry repair is not implemented yet. Invalid source geometries may require cleanup before reliable analysis.
- Raster source analysis is cataloged but not implemented.
- Basemap/imagery acquisition, panel map sheets, PDF export, template-grade DOCX layout, and final map export packages are not implemented.
- Large local source layers should remain outside Git under ignored project `layers/` folders.

## Archive Review

No active tracked documentation was stale enough to archive during this pass. The existing archive locations remain:

- `archive/` for general retained but inactive project files.
- `docs/archive/` for superseded or historical documentation.
