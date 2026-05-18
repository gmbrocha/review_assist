# Current State

## Current Project Goal

Review Assist is a service-first workflow for generating first-pass environmental constraints review packages. It should parse project inputs, build source-backed constraint evidence, produce bounded review items, require human review, and compile reviewed content into editable report packages.

The system is not a recommendation engine, final environmental review, regulatory approval tool, or autonomous analyst.

## Current Sprint/Subunit

- Completed: Sprint 1.1 Contract Foundation.
- Completed: Sprint 1.2 Project Intake Artifacts.
- Completed: Sprint 1.3 Comparison Units and Orchestration.
- Completed: Sprint 2.1 Source Profile And Basemaps.
- Active next implementation target: Sprint 2.2 Comparison Constraints And Tables.

## Active Architectural State

Implemented baseline:

- CLI/service-oriented backend, no production web app.
- Project workspaces under `projects/<project_id>/`.
- Input package classification, KMZ/KML inspection, normalized project geometry artifacts, and project area artifacts.
- Project context, comparison units, source status, source acquisition, local source materialization, source inventory, constraint analysis, findings, tables, vector-only maps, evidence packages, draft report sections, JSON review queue, Markdown/DOCX exports, demo/MVP package commands, populate-for-review orchestration.
- Static Sprint 1.1 deliverable matrix and report prompt contract validation.
- `environmental_constraints_example` is the default profile for `alternatives_review`; `environmental_constraints_basic` and `location_screening_basic` remain available for explicit use.
- Source status and source inventory now include per-source detail statuses for registered local, local materialized, downloaded, manual, restricted, failed, unimplemented, missing, optional, stubbed, and selected-but-not-renderable sources.
- MARIS/NAIP 2025 imagery is cataloged as context-only basemap provenance. `src/review_assist/basemaps.py` indexes county folders under `sources/aerial_base_maps/maris_naip_2025`, treats `.sid` files as provenance only, and recognizes `.tif`, `.tiff`, and `.png` sidecars as renderable candidates.
- Census TIGER/ACS is represented as metadata-only setup using `CENSUS_API_KEY` and 2024 ACS 5-year as the declared default future dataset; a missing key creates visible stub/status detail rather than a crash.

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
- `projects/<project_id>/review_queue/review_queue.json`
- `projects/<project_id>/exports/export_manifest.json`

## Known Immediate Constraints

- Do not implement product code during documentation architecture tasks.
- No web app is implemented yet.
- The canonical deliverable matrix validates but is not wired into report generation, table generation, figure generation, review queue generation, or export.
- The canonical prompt config validates but is not wired into section drafting.
- NAIP/MARIS basemap provenance and renderability are recorded in `project_area.json` and source status detail, but raster-backed map/figure rendering is not implemented in the current pipeline.
- Comparison units are generated and recorded by populate orchestration, but Sprint 2.2+ work still needs to wire them into report-facing constraint summaries, exact deliverable tables, figures, report item expansion, and export gating.
- Census source setup is visible, but ACS/TIGER table generation remains deferred to Sprint 2.2.
- Default export behavior still needs the future matrix-bounded review-complete gate.
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
