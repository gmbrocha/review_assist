# Truth Stabilization Pass

The system exists to generate first-pass environmental/constraint review packages for human review.

The system does not:

- make final recommendations
- replace professional review
- imply regulatory approval
- imply authoritative completeness
- silently convert inferred findings into authoritative truth
- hide uncertainty, missing sources, failed downloads, gated sources, stale data, or unresolved statuses

## Core Invariants

- Human review remains mandatory before export/finalization.
- Outputs are draft/pre-review unless explicitly finalized by a reviewer.
- Source provenance must remain visible.
- Download failures, gated sources, stale data, and unresolved statuses must remain explicit.
- Inferred findings must remain distinguishable from authoritative GIS/source-backed findings.
- The system must preserve uncertainty and data gaps explicitly.
- Buffer assumptions, screening assumptions, and methodology assumptions must remain auditable.
- Reports should characterize impacts/constraints, not automatically rank or recommend alternatives.
- Temporary placeholders or incomplete tables must never silently appear authoritative.
- Reviewer edits and overrides should remain attributable and recoverable.
- Prefer explicit domain modeling over procedural report-generation patches.

## Change Classification

Before implementation, classify changes as:

- `SAFE LAYER CHANGE`: isolated support, validation, documentation, or wiring that preserves existing domain meaning.
- `DOMAIN EXTENSION`: adds a new modeled capability, source, artifact, workflow state, or review/export behavior.
- `DOMAIN CORRECTION`: changes existing domain semantics, methodology, source interpretation, uncertainty handling, or report behavior to be more accurate.
- `DANGEROUS PATCH`: hides uncertainty/provenance, bypasses review, implies unsupported authority, silently changes methodology, or patches report output without modeling the domain.

If a task risks collapsing uncertainty, hiding provenance, or implying unsupported authority, stop and request explicit approval before implementation.
