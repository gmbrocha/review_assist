# Sprint Index

Active sprint docs live in this directory. Completed sprint docs move to `docs/archive/sprints/`.

## Active Sprint/Subunit

- Sprint 5.0 planning is the active next target and currently lives in root-level planning docs:
  - `SPRINT_5_REPORT_INTELLIGENCE_SOURCE_TRUTH_AND_DISCERNMENT.md`
  - `SPRINT_5_0_PLANNING_DIFF_LOCK_AND_NUMBERING_DECISION.md`

`docs/sprints/SPRINT_4_WEB_APP_AND_WIRING.md` remains in this directory pending normal sprint-resolution/archive cleanup.

## Planned Sprint/Subunits

- Roadmap reference: `docs/sprints/ROADMAP.md`
- Sprint 5 report-policy/source-truth/discernment subunits currently live as root-level planning docs until they are implemented and archived.

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
  - Implemented exact matrix-backed deliverable figure targets, selected-sidecar basemap rendering/fallbacks, restricted cultural exclusion, Attachment A supporting panels, evidence package refs/summaries, CLI/populate wiring, and focused tests.
- Sprint 3.1 Deliverable Items And Review Queue: `docs/archive/sprints/SPRINT_3_1_DELIVERABLE_ITEMS_AND_REVIEW_QUEUE.md`
  - Implemented matrix-backed deliverable item generation, dynamic wetlands/waterbodies comparison-unit child sections, prompt-contract-backed section drafting payloads, bounded default review queue generation, legacy/audit queue opt-in, expanded reviewer statuses, CLI/populate wiring, and focused tests.
- Sprint 3.2 Export Gate And Package Commands: `docs/archive/sprints/SPRINT_3_2_EXPORT_GATE_AND_PACKAGE_COMMANDS.md`
  - Implemented review-complete default export gating from the standard bounded review queue, reviewed-content selection rules, structured CLI gate failures, preview bypass metadata, package manifest gate summaries, demo/MVP package behavior, and focused tests.
- Sprint 3 Review Queue, Export Gate, And DOCX Fidelity: `docs/archive/sprints/SPRINT_3_REVIEW_EXPORT_AND_DOCX.md`
  - Completed Sprint 3 across deliverable items, bounded review queue, terminal statuses, review-complete export gate, package manifests, compactness budget, DOCX fidelity, and final verification.
- Sprint 3.3 DOCX Fidelity Docs And Final Verification: `docs/archive/sprints/SPRINT_3_3_DOCX_FIDELITY_DOCS_AND_FINAL_VERIFICATION.md`
  - Implemented baseline DOCX page setup/styles, title/front matter/body/attachment assembly, bounded editable table previews, figure placeholders/captions/source/method notes, manifest-level final verification, package-manifest propagation, docs, and focused/full verification.

## Deferred Work Linked To Sprints

See `docs/governance/DEFERRED_WORK.md` for full detail.

- Sprint 4: no backend deferred item should be newly routed here by default; Sprint 4 should consume the resolved Sprint 2/3 service contracts through a thin UI.
- Sprint 5: route source acquisition expansion, production review-state migration, GPT rewrite UX, and future figure work to deferred/future sprint items unless explicitly approved in the active subunit.
