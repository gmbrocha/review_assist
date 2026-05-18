# Sprint Index

Root-level sprint docs remain the active working style for not-yet-implemented sprints. This index is the routing layer so agents do not need to scan every sprint file.

## Active Sprint/Subunit

- Sprint 3.3: `SPRINT_3_3_DOCX_FIDELITY_DOCS_AND_FINAL_VERIFICATION.md`

## Planned Sprint/Subunits

- Sprint 3 overview: `SPRINT_3_REVIEW_EXPORT_AND_DOCX.md`
- Sprint 3.3: `SPRINT_3_3_DOCX_FIDELITY_DOCS_AND_FINAL_VERIFICATION.md`
- Sprint 4: `SPRINT_4_WEB_APP_AND_WIRING.md`
- Roadmap reference: `docs/sprints/ROADMAP.md`

## Completed Sprint/Subunits

- Sprint 1 Foundation and Deliverable Contract: `docs/archive/sprints/SPRINT_1_FOUNDATION_AND_CONTRACT.md`
  - Completed the non-UI Sprint 1 foundation across Sprint 1.1, 1.2, and 1.3.
- Sprint 1.1 Contract Foundation: `docs/archive/sprints/SPRINT_1_1_CONTRACT_FOUNDATION.md`
  - Implemented static deliverable matrix, report prompt config, loaders/validators, CLI validators, and focused tests.
- Sprint 1.2 Project Intake Artifacts: `docs/archive/sprints/SPRINT_1_2_PROJECT_INTAKE_ARTIFACTS.md`
  - Implemented input package classification, project area artifact generation, county detection, NAIP/MARIS basemap provenance/renderability status, CLI commands, populate integration, and focused tests.
- Sprint 1.3 Comparison Units and Orchestration: `docs/archive/sprints/SPRINT_1_3_COMPARISON_UNITS_AND_ORCHESTRATION.md`
  - Implemented comparison-unit artifacts, KML folder/style/color preservation, expected-count validation, CLI command, populate integration, and focused tests.
- Sprint 2 Constraints, Tables, And Figures: `docs/archive/sprints/SPRINT_2_CONSTRAINTS_TABLES_AND_FIGURES.md`
  - Completed Sprint 2 across source profile/basemaps, comparison-unit constraints and deliverable tables, matrix-backed deliverable figures, evidence refs, validation, and documentation.
- Sprint 2.1 Source Profile And Basemaps: `docs/archive/sprints/SPRINT_2_1_SOURCE_PROFILE_AND_BASEMAPS.md`
  - Implemented the example report source profile default, Sprint 2.1 source catalog stubs, per-source status detail, Census key stubbing, MARIS/NAIP 2025 basemap indexing, and renderable sidecar detection.
- Sprint 2.2 Comparison Constraints And Tables: `docs/archive/sprints/SPRINT_2_2_COMPARISON_CONSTRAINTS_AND_TABLES.md`
  - Implemented report-facing comparison-unit constraints, source-specific table normalization, four exact matrix-backed deliverable table targets, Census stubs/local-source table rows, CLI/populate wiring, and focused tests.
- Sprint 2.3 Figures, Evidence, And Validation: `docs/archive/sprints/SPRINT_2_3_FIGURES_EVIDENCE_AND_VALIDATION.md`
  - Implemented 13 exact matrix-backed deliverable figure targets, selected-sidecar basemap rendering/fallbacks, restricted cultural exclusion, Attachment A supporting panels, evidence package refs/summaries, CLI/populate wiring, and focused tests.
- Sprint 3.1 Deliverable Items And Review Queue: `docs/archive/sprints/SPRINT_3_1_DELIVERABLE_ITEMS_AND_REVIEW_QUEUE.md`
  - Implemented matrix-backed deliverable item generation, dynamic wetlands/waterbodies comparison-unit child sections, prompt-contract-backed section drafting payloads, bounded default review queue generation, legacy/audit queue opt-in, expanded reviewer statuses, CLI/populate wiring, and focused tests.
- Sprint 3.2 Export Gate And Package Commands: `docs/archive/sprints/SPRINT_3_2_EXPORT_GATE_AND_PACKAGE_COMMANDS.md`
  - Implemented review-complete default export gating from the standard bounded review queue, reviewed-content selection rules, structured CLI gate failures, preview bypass metadata, package manifest gate summaries, demo/MVP package behavior, and focused tests.

## Deferred Work Linked To Sprints

See `docs/governance/DEFERRED_WORK.md` for full detail.

- Sprint 3.3: DOCX fidelity docs and final verification.
- Sprint 4: no backend deferred item should be newly routed here by default; Sprint 4 should consume the resolved Sprint 2/3 service contracts through a thin UI.
