# Sprint 6.8: QA And Scope-Control Pass

## Status

Completed and archived as the final Sprint 6 stabilization subunit.

## Purpose

Verify that reviewer figure styling improves presentation without altering analytical truth, source records, source geometry, derived metrics, or review/export gate semantics.

## QA Focus

Verify:

- source data unchanged
- source registry unchanged
- source status semantics unchanged except for expected artifact freshness metadata
- source materialization outputs unchanged
- comparison-unit geometry unchanged
- constraint results unchanged
- comparison-unit constraints unchanged
- deliverable table metrics unchanged
- evidence metrics unchanged
- report metrics unchanged
- only figure artifact/version/style metadata changes when style edits/regeneration occur

## Required Scenarios

At minimum, test or manually verify:

- wetland figure layer visibility/styling change
- streams/impaired-waters figure layer visibility/styling change
- hazardous/regulated figure styling change
- cultural/community figure styling change
- reset-to-default after draft override
- regenerate after draft override
- approve exact regenerated version
- export approved version
- later edit creates a new unapproved version without overwriting the approved one

Use sample projects only as validation fixtures. Do not hardcode trails-specific assumptions.

## Artifact Freshness

Because Sprint 6 changes deliverable figure rendering, review detail display, review queue figure metadata, and export figure selection, closeout must explicitly address generated artifacts.

Report:

- Generated artifacts affected: yes/no
- Minimum affected chain
- Regeneration commands run
- Canonical artifacts verified
- UI verified from current server: yes/no/not applicable
- Generated artifacts intentionally uncommitted
- Remaining stale-artifact risk

## Tests

Run focused tests first:

- figure model tests
- style override tests
- render job/regeneration tests
- version/approval tests
- web figure editor tests
- export resolver tests

Then run broader tests if shared export, review queue, or rendering contracts changed:

- deliverable figure tests
- deliverable item tests
- review queue tests
- export report tests
- web app tests
- compactness/DOCX fidelity tests if export behavior changes

## Documentation Updates

Update the minimum necessary permanent docs:

- `docs/domains/MAP_GENERATION.md`
- `docs/domains/REVIEW_POLICY.md`, if approval state affects review semantics
- `docs/domains/REPORT_ASSEMBLY.md`, if export resolution changes
- `docs/core/CURRENT_STATE.md`
- `docs/core/ARCHITECTURE.md`, if new service/artifact boundaries are added
- `docs/governance/DEFERRED_WORK.md`, if advanced styling/version comparison/template work remains deferred

## Explicit Out Of Scope

Do not add late-sprint scope for:

- GIS editing
- geometry edits
- advanced labels
- templates
- batch styling
- organization-wide symbology
- side-by-side comparison
- PDF export unless already supported cleanly

## Definition Of Done

- QA proves styling changes do not alter analytical truth.
- Export uses the intended figure version hierarchy.
- UI actions are constrained and auditable.
- Generated-artifact freshness is handled explicitly.
- Deferred cartography/editor ideas are recorded instead of being half-implemented.
