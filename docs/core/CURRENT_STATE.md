# Current State

## Current Project Goal

Review Assist is a service-first workflow for generating first-pass environmental constraints review packages. It should parse project inputs, build source-backed constraint evidence, produce bounded review items, require human review, and compile reviewed content into editable report packages.

The system is not a recommendation engine, final environmental review, regulatory approval tool, or autonomous analyst.

## Current Sprint/Subunit

- Completed: Sprint 1.1 Contract Foundation.
- Active next implementation target: Sprint 1.2 Project Intake Artifacts.
- Active Sprint 1.2 root doc: `SPRINT_1_2_PROJECT_INTAKE_ARTIFACTS.md`.
- Sprint 1.2 is not implemented in this checkout: `input_package.py`, `project_area.py`, their CLI commands, and populate integration are still absent.

## Active Architectural State

Implemented baseline:

- CLI/service-oriented backend, no production web app.
- Project workspaces under `projects/<project_id>/`.
- KMZ/KML inspection and normalized project geometry artifacts.
- Project context, source status, source acquisition, local source materialization, source inventory, constraint analysis, findings, tables, vector-only maps, evidence packages, draft report sections, JSON review queue, Markdown/DOCX exports, demo/MVP package commands, populate-for-review orchestration.
- Static Sprint 1.1 deliverable matrix and report prompt contract validation.

Important current artifacts:

- `config/deliverable_section_matrix.json`
- `config/report_generation_prompts.json`
- `projects/<project_id>/intermediate/project_geometry.json`
- `projects/<project_id>/intermediate/project_features.geojson`
- `projects/<project_id>/intermediate/project_analysis_bounds.geojson`
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
- NAIP/MARIS imagery exists as source material, but basemap provenance/renderability and raster-backed map rendering are not implemented in the current pipeline.
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
