# Sprint Index

Root-level sprint docs remain the active working style for not-yet-implemented sprints. This index is the routing layer so agents do not need to scan every sprint file.

## Active Sprint/Subunit

- No active sprint/subunit is selected after Sprint 1.3 completion.

## Planned Sprint/Subunits

- Sprint 2 overview: `SPRINT_2_CONSTRAINTS_TABLES_AND_FIGURES.md`
- Sprint 2.1: `SPRINT_2_1_SOURCE_PROFILE_AND_BASEMAPS.md`
- Sprint 2.2: `SPRINT_2_2_COMPARISON_CONSTRAINTS_AND_TABLES.md`
- Sprint 2.3: `SPRINT_2_3_FIGURES_EVIDENCE_AND_VALIDATION.md`
- Sprint 3 overview: `SPRINT_3_REVIEW_EXPORT_AND_DOCX.md`
- Sprint 3.1: `SPRINT_3_1_DELIVERABLE_ITEMS_AND_REVIEW_QUEUE.md`
- Sprint 3.2: `SPRINT_3_2_EXPORT_GATE_AND_PACKAGE_COMMANDS.md`
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

## Deferred Work Linked To Sprints

See `docs/governance/DEFERRED_WORK.md` for full detail.

- Sprint 2.2: canonical deliverable matrix wiring into comparison-unit constraints and exact deliverable tables.
- Sprint 2.3: canonical deliverable matrix wiring into exact deliverable figures and evidence package refs.
- Sprint 3.1: canonical deliverable matrix and prompt contract wiring into deliverable items, dynamic comparison-unit sections, section drafting, and bounded review queue generation.
- Sprint 3.2: canonical deliverable matrix wiring into review-complete export gate and package manifests.
- Sprint 4: no backend deferred item should be newly routed here by default; Sprint 4 should consume the resolved Sprint 2/3 service contracts through a thin UI.
