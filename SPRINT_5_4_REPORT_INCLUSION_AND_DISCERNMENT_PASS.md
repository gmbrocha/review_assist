# Sprint 5.4: Section Render Gating And Comparison-Unit Expansion

## Status

Parked for implementation after Sprint 5.1 through Sprint 5.3 are accepted.

## Goal

Make section inclusion and comparison-unit expansion obey policy instead of relying on broad default matrix shape.

This is the first implementation subunit that may change which generated review candidates render as normal body sections versus stubs, table-only content, attachment/status content, or reviewer-decision items. Treat those changes as `DOMAIN CORRECTION` unless the behavior is explicitly approved and easy to verify.

## Scope

This subunit may update:

- deliverable item generation
- deterministic section candidate generation
- review queue item metadata
- report assembly/export selection checks
- policy validation tests

## Recommendation Set

For each possible report topic, the app should be able to represent one of:

- include in report body
- include as table/figure only
- include in attachment/status
- omit from report but keep in audit/evidence
- needs reviewer decision
- blocked by missing/manual/restricted source
- custom/project-specific section required

Every recommendation or render decision must have a reason.

## Decisions Required Before Code Changes

- Whether `relationship-with-pel-study` remains required or becomes conditional/manual.
- Whether wetlands/waterbodies comparison-unit child narratives remain default or become table-only/conditional.
- Whether any required matrix item may remain a required reviewed stub instead of normal body prose.
- How to preserve review queue count stability if a section is gated out of body rendering.

## Guardrails

- Nothing is auto-final.
- Human review remains required.
- Context-only evidence must not be presented as direct impact.
- Missing/manual/restricted sources must stay visible as review state.
- Do not silently collapse legitimately distinct comparison units or sources.
- Do not make the app trail-specific.

## Acceptance Criteria

- Section candidates carry policy-backed render/inclusion status.
- Conditional/custom/manual sections do not render as generic source-backed facts by default.
- Table-only sections do not spawn narrative children unless policy and evidence justify it.
- Per-comparison-unit expansion is explicit, test-covered, and not trail-specific.
- Reviewer-facing queue items remain understandable and export-gated.

## Required Tests

- PEL/custom section is not generic default body content unless approved.
- Wetlands/waterbodies narrative children follow the approved policy.
- Table-only sections preserve table refs without duplicate prose.
- Missing/manual/restricted sections remain review-visible.
- Export excludes or labels gated sections according to policy.
- Existing `projects/trails` sample remains a fixture, not a source of hardcoded logic.

## Documentation Updates

- `docs/domains/REPORT_POLICY.md`
- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/governance/DEFERRED_WORK.md` for any render-gating decisions not implemented
