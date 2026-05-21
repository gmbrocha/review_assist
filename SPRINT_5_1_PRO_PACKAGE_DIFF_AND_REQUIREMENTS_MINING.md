# Sprint 5.1: Pro Package Diff And Requirements Mining

## Status

Parked draft for review. Do not implement until the Sprint 5 stabilization checkpoint is accepted.

## Goal

Use the Pro-generated example-report extraction package as a requirements-mining artifact, not as gospel.

## Inputs

- Pro extraction package from the unfinished example report.
- Current Review Assist configs, docs, and code.
- Current source warehouse and source policy.
- Current deliverable matrix and report section policy.

## Outputs

- Structured diff between the package and the current app.
- Human decision list.
- Recommended P0/P1/P2/P3 plan.

## Classification Buckets

Each finding from the Pro package should be classified as one of:

- Already covered.
- Covered but wrong policy/source/extent.
- Missing and generalizable.
- Conditional.
- Manual/reviewer-supplied.
- Trail/corridor-specific.
- PEL/project-specific.
- Do not generalize.
- Deferred.

## Guardrails

- Treat the Pro package as evidence of report expectations, not as a replacement authority.
- Do not implement from the package during this subunit unless a tiny P0 is explicitly approved.
- Do not generalize trail-specific or PEL-specific material without human decision.
- Preserve Review Assist's source-backed, human-reviewed workflow boundaries.

## Definition Of Done

- We know what the example teaches us.
- We know what should not be generalized.
- We know which current app assumptions need correction.
- No implementation has occurred unless explicitly approved as a tiny P0.
