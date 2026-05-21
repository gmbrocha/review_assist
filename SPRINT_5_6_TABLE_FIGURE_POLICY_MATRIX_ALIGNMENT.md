# Sprint 5.6: Table/Figure Policy Matrix Alignment

## Status

Parked for implementation after Sprint 5.1 through Sprint 5.5 are accepted.

## Goal

Align existing deliverable table and figure targets with report policy, source needs, extent classes, allowed refs, caveats, and compactness rules.

This subunit should not casually add, remove, or renumber deliverable tables or figures.

This subunit must consume the table, figure, attachment, visual extent, allowed-ref, and compactness rows from `SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md`. The package may propose additional targets or different figure/table concepts; those proposals must be mapped to existing matrix targets, explicitly approved as deliverable-count changes, rejected, or deferred.

## Current Baseline

The current standard deliverable matrix has:

- 4 table targets
- 15 figure targets
- 3 attachment targets

Those counts are protected unless a human explicitly approves a deliverable matrix change.

## Scope

This subunit may update:

- `config/deliverable_section_matrix.json`
- `config/report_section_policy.json`
- deliverable table/figure metadata generation
- evidence package refs
- tests for allowed refs, stubs, and compactness

## Policy Alignment Requirements

- Wetland, waterbody, floodplain, hazmat, community-resource, utility, and demographic outputs should render only when required source classes and extent rules are satisfied.
- Unavailable/missing/manual/restricted source cases should produce honest stubs or review-needed items.
- Large feature lists should remain in evidence/attachments, not report body.
- Figure visual extent may support readability but must not become analysis extent.
- Similar source layers may both appear only when their distinction is clear in the UI/report metadata.

## Non-Goals

- No figure editor.
- No figure recipe/override/versioning architecture.
- No new source acquisition.
- No full cartographic redesign.
- No panel-map production redesign unless already supported by current matrix policy.

## Acceptance Criteria

- All table/figure/attachment ledger rows are adopted, rejected, explicitly approved as matrix changes, or deferred with rationale.
- Every table/figure target has a matching policy entry and allowed source categories.
- Table/figure refs in sections are policy-allowed and matrix-known.
- Missing source tables/figures produce explicit stubs with source/status reasons.
- Generated table previews remain compact; overflow stays in artifacts/evidence.
- Figure captions/source notes/method notes align with extent and source policy.

## Required Tests

- Deliverable matrix validation.
- Report section policy validation against matrix.
- Table generation source/stub behavior.
- Figure generation source/stub behavior.
- Figure extent metadata and presentation-only render extent.
- Export compactness/no raw source dump protections.

## Documentation Updates

- `docs/domains/REPORT_POLICY.md`
- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/domains/MAP_GENERATION.md` if figure metadata behavior changes
- `docs/governance/DEFERRED_WORK.md` for deferred table/figure additions or source gaps
