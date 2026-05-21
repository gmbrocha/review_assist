# Sprint 5.2: Canonical Report Section Policy

## Status

Parked draft for review. Do not implement until Sprint 5.1 has produced accepted requirements and the Sprint 5 stabilization checkpoint is accepted.

## Goal

Create the machine-readable policy layer that tells the app what each report section means.

This policy should become the source that GPT, deliverable generation, inclusion logic, and tests trust.

## Policy Fields

Each section policy should include:

- Section ID and title.
- Source category.
- Extent policy.
- Visual extent class.
- Comparison-unit expansion policy.
- Evidence pattern.
- Table and figure expectations.
- Output shape.
- Drafting mode.
- GPT readiness.
- Required caveats.
- Prohibited claims.
- Manual/reviewer-supplied status.
- Default, conditional, custom, or deprecated status.

## Key Questions

- Which sections always exist?
- Which sections are conditional?
- Which sections are custom or project-specific?
- Which sections can have per-comparison-unit children?
- Which sections are table-only?
- Which sections should never be GPT-drafted by default?

## Policy Decisions To Capture

- PEL relationship section is conditional/custom, not generic.
- Wetlands expansion policy is explicit.
- Community/context sections are not treated as direct project impact.
- Manual/reviewer-supplied sections are clearly separated.

## Definition Of Done

- Every matrix section has policy or an explicit exemption.
- Required caveats and prohibited claims are machine-readable.
- GPT readiness is explicit and conservative.
- Policy supports later inclusion/discernment without bloating the report.
