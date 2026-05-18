# Current State

## Current Project Goal

Review Assist is a service-first workflow for generating first-pass environmental constraints review packages. It should parse project inputs, build source-backed constraint evidence, produce bounded review items, require human review, and compile reviewed content into editable report packages.

The system is not a recommendation engine, final environmental review, regulatory approval tool, or autonomous analyst.

## Current Sprint/Subunit

- Completed: Sprint 1.1 Contract Foundation.
- Completed: Sprint 1.2 Project Intake Artifacts.
- Completed: Sprint 1.3 Comparison Units and Orchestration.
- Completed: Sprint 2.1 Source Profile And Basemaps.
- Completed: Sprint 2.2 Comparison Constraints And Tables.
- Completed: Sprint 2.3 Figures, Evidence, And Validation.
- Completed: Sprint 3.1 Deliverable Items And Review Queue.
- Active next implementation target: Sprint 3.2 Export Gate And Package Commands.

## Active Architectural State

Implemented baseline:

- CLI/service-oriented backend, no production web app.
- Project workspaces under `projects/<project_id>/`.
- Input package classification, KMZ/KML inspection, normalized project geometry artifacts, and project area artifacts.
- Project context, comparison units, source status, source acquisition, local source materialization, source inventory, constraint analysis, findings, tables, vector-only maps, evidence packages, draft report sections, JSON review queue, Markdown/DOCX exports, demo/MVP package commands, populate-for-review orchestration.
- Static Sprint 1.1 deliverable matrix and report prompt contract validation.
- Matrix-backed Sprint 2.2 deliverable table generation at `projects/<project_id>/deliverable/tables.json`, with four exact table targets generated or stubbed from `config/deliverable_section_matrix.json`.
- Matrix-backed Sprint 2.3 deliverable figure generation at `projects/<project_id>/deliverable/figures.json`, with 13 exact main figure targets generated or stubbed from `config/deliverable_section_matrix.json`.
- Matrix-backed Sprint 3.1 deliverable item generation at `projects/<project_id>/deliverable/deliverable_items.json`, including static report targets, dynamic wetlands/waterbodies comparison-unit child sections, deliverable table/figure/attachment items, prompt-contract metadata, source-gap validation summaries, and required stubs.
- The standard review queue now consumes `deliverable_items.json` by default and creates one bounded review item per deliverable item. Legacy raw finding/table/map/spatial/source-inventory queue behavior remains available only through explicit audit mode.
- `deliverable_figures.py` remains the orchestration entry point; figure target specs, artifact validation, basemap sidecar loading, and rendering/layout helpers are split into focused `deliverable_figure_*` modules.
- Report-facing comparison-unit constraint analysis at `projects/<project_id>/constraints/comparison_unit_constraints.json`; raw project-feature constraints remain available as evidence at `projects/<project_id>/constraints/constraint_results.json`.
- `environmental_constraints_example` is the default profile for `alternatives_review`; `environmental_constraints_basic` and `location_screening_basic` remain available for explicit use.
- Source status and source inventory now include per-source detail statuses for registered local, local materialized, downloaded, manual, restricted, failed, unimplemented, missing, optional, stubbed, and selected-but-not-renderable sources.
- MARIS/NAIP 2025 imagery is cataloged as context-only basemap provenance. `src/review_assist/basemaps.py` indexes county folders under `sources/aerial_base_maps/maris_naip_2025`, treats `.sid` files as provenance only, and recognizes `.tif`, `.tiff`, and `.png` sidecars as renderable candidates.
- Deliverable figures can render selected MARIS/NAIP `.png`, `.tif`, or `.tiff` sidecars when project-area metadata selects them. MrSID `.sid` files remain provenance only. GeoTIFF rendering uses optional `rasterio` lazily when installed; the package does not hard-require rasterio.
- The evidence package now includes deliverable table refs, deliverable figure refs, row/figure availability summaries, comparison-unit summaries, compact source-backed constraint summaries, source-gap status, validation issues, and raw artifact paths without exposing full geometries or raw feature dumps to GPT-bound evidence.
- Census TIGER/ACS table generation supports registered local Census-like tract/community polygon sources with ACS fields for the two demographic deliverable tables, and produces visible stubs when the source/API setup is unavailable. Live Census API/TIGER acquisition remains unimplemented.

Important current artifacts:

- `config/deliverable_section_matrix.json`
- `config/report_generation_prompts.json`
- `config/report_profiles.json`
- `config/source_catalog.json`
- `projects/<project_id>/context/input_package.json`
- `projects/<project_id>/intermediate/project_geometry.json`
- `projects/<project_id>/intermediate/project_features.geojson`
- `projects/<project_id>/intermediate/project_analysis_bounds.geojson`
- `projects/<project_id>/intermediate/comparison_units.geojson`
- `projects/<project_id>/intermediate/comparison_units.json`
- `projects/<project_id>/context/project_area.json`
- `projects/<project_id>/context/project_context.json`
- `projects/<project_id>/source_status/source_status_set.json`
- `projects/<project_id>/constraints/constraint_results.json`
- `projects/<project_id>/constraints/comparison_unit_constraints.json`
- `projects/<project_id>/deliverable/tables.json`
- `projects/<project_id>/deliverable/figures.json`
- `projects/<project_id>/deliverable/deliverable_items.json`
- `projects/<project_id>/maps/figures/*.png`
- `projects/<project_id>/evidence/evidence_package.json`
- `projects/<project_id>/review_queue/review_queue.json`
- `projects/<project_id>/exports/export_manifest.json`

## Known Immediate Constraints

- Do not implement product code during documentation architecture tasks.
- No web app is implemented yet.
- The canonical deliverable matrix validates and now drives exact deliverable table, figure, deliverable item, and bounded review queue generation. Sprint 3.2 still needs review-complete export gate and package manifest enforcement.
- The canonical prompt config validates and is wired into standard deliverable item section drafting payloads. Legacy `drafts/report_sections.json` remains available for compatibility/audit context.
- Legacy `maps/map_manifest.json` remains a raw evidence/audit map manifest. Standard report-facing figures live in `deliverable/figures.json`.
- NAIP/MARIS basemap provenance and renderability are recorded in `project_area.json` and source status detail. Deliverable figure rendering can use selected renderable sidecars, but local `.sid`-only imagery still produces vector-only figures or explicit stubs/warnings.
- Comparison units are generated, recorded by populate orchestration, and used for report-facing constraint summaries, exact deliverable tables, exact deliverable figures, evidence refs, and dynamic wetlands/waterbodies deliverable item sections. Sprint 3.2 still needs matrix-backed export gating.
- Census source setup and table stubbing/local-source table generation are implemented; live ACS API calls, TIGER download/acquisition, and full margin-of-error handling remain future work.
- Default export behavior still needs the future matrix-bounded review-complete gate and package command enforcement.
- Missing/gated/manual/stale/failed sources must remain visible and reviewable.

## Context Routing

- Agent operating contract: `AGENTS.md`
- Architecture summary: `docs/core/ARCHITECTURE.md`
- Durable decisions: `docs/core/DECISIONS.md`
- Governance workflows: `docs/governance/`
- Domain doc index: `docs/domains/README.md`
- Sprint index: `docs/sprints/README.md`
- Deferred work registry: `docs/governance/DEFERRED_WORK.md`
- High-level canonical plan: `CANONICAL_PLAN.md` when deliverable shape or workflow direction is ambiguous
- Historical/cold docs: `docs/archive/README.md`
