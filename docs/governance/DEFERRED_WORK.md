# Deferred Work

This file is mandatory tracked project state for deferred review-assist work. Every sprint planning pass must review it and update it when implementation needs, risks, unresolved questions, or follow-up work are postponed.

Every new sprint planning pass must review:

- this registry
- unresolved review methodology concerns
- known source limitations
- known uncertainty propagation gaps

## How To Record Deferred Items

Each deferred item should include:

- `Deferred item`: short name.
- `Why postponed`: reason it is not handled now.
- `Affected sections/workflows`: report sections, source workflows, review queue behavior, map/export behavior, or methodology affected.
- `Risk if forgotten`: what could become misleading, stale, unsupported, or operationally blocked.
- `Temporary simplification`: whether current outputs are simplified or incomplete because of the deferral.
- `Target sprint/subunit`: future sprint/subunit when known.
- `Status`: open, in progress, resolved, or superseded.

## Active Deferred Items

### Canonical Deliverable Contract Wiring

- `Deferred item`: Wire the Sprint 1.1 deliverable matrix into report-facing generation.
- `Why postponed`: Sprint 1.1 intentionally added static config, loaders, validators, tests, and CLI validation only. It did not change report generation, review queue generation, table generation, figure generation, or export behavior.
- `Affected sections/workflows`: Report section generation, deliverable tables, deliverable figures, deliverable items, review queue generation, export assembly, GPT-assisted section drafting.
- `Risk if forgotten`: The legacy report profile/templates can continue to drive output while the canonical matrix only validates on the side, allowing output volume, section coverage, stub policy, and table/figure inventory to drift away from the redirected workflow.
- `Temporary simplification`: Current outputs can still use `config/report_section_templates.json` and existing report/map/table artifacts rather than the canonical matrix-backed deliverable targets.
- `Target sprint/subunit`: Sprints 2.2, 2.3, 3.1, and 3.2.
- `Status`: open.

### Canonical Prompt Contract Wiring

- `Deferred item`: Wire `config/report_generation_prompts.json` into GPT-assisted and deterministic section generation.
- `Why postponed`: Sprint 1.1 created and validated the prompt contract but did not replace the existing section drafting prompt flow.
- `Affected sections/workflows`: GPT-assisted report sections, deterministic section fallback, evidence package inputs, review queue section items.
- `Risk if forgotten`: Prompt guardrails may remain validated but inactive, increasing the chance that section drafting behavior diverges from the canonical no-ranking, no-selection, no-final-determination, source-backed-only contract.
- `Temporary simplification`: The prompt contract is machine-readable and test-covered, but current report drafting still uses existing implementation pathways.
- `Target sprint/subunit`: Sprint 3.1.
- `Status`: open.

### Dynamic Wetlands/Waterbodies Comparison-Unit Sections

- `Deferred item`: Expand the dynamic 3.1.1.x wetlands/waterbodies section template into one reviewable subsection per comparison unit.
- `Why postponed`: Sprint 1.1 represented the template in the matrix only. Comparison-unit generation is planned for Sprint 1.3, and deliverable item expansion is planned for Sprint 3.1.
- `Affected sections/workflows`: Section 3.1.1 Wetlands and Waterbodies, dynamic 3.1.1.x subsections, Table 1, Figure 1, review queue item count control.
- `Risk if forgotten`: Raw segments or individual hits could continue to appear as report/review units, reintroducing the oversized-report failure mode the redirect is meant to prevent.
- `Temporary simplification`: The dynamic target is validated as a template and is not expanded into runtime section items yet.
- `Target sprint/subunit`: Sprints 1.3 and 3.1.
- `Status`: open.

### Sprint 1.2 Project Intake Artifacts Not Present In Current Checkout

- `Deferred item`: Implement the Sprint 1.2 project intake artifacts: `context/input_package.json`, `context/project_area.json`, input classification CLI, project area CLI, NAIP/MARIS basemap provenance, and populate integration.
- `Why postponed`: The Sprint 1.2 plan exists, but the current `main` checkout does not contain `src/review_assist/input_package.py`, `src/review_assist/project_area.py`, the related CLI commands, tests, or populate integration.
- `Affected sections/workflows`: Project setup, required KMZ validation, bbox/county detection, NAIP basemap provenance, populate-for-review manifest, source/profile preparation for later tables and figures.
- `Risk if forgotten`: Later sprints may assume project area, county names, and basemap status artifacts exist when they do not, hiding missing-KMZ and basemap renderability issues from the workflow.
- `Temporary simplification`: The current workflow still uses existing project context and project geometry artifacts directly; it does not yet create the explicit input package or project area context required by the redirected workflow.
- `Target sprint/subunit`: Sprint 1.2.
- `Status`: open.
