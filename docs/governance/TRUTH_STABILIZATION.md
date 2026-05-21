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

## Post-Implementation Generated Artifact Rule

After any implementation that changes one or more of these areas, the agent must explicitly consider whether generated artifacts are stale:

- source warehouse or source materialization
- source status or effective source truth
- source acquisition or source caveats
- project area or comparison units
- constraints or comparison-unit constraints
- deliverable tables
- deliverable figures or map rendering
- evidence package
- deliverable item generation
- review queue generation
- review queue reset behavior
- GPT drafting, GPT payloads, or GPT cache
- export or report assembly
- UI adapter paths or review detail display
- canonical artifact paths

Required closeout steps:

1. State whether the change affects generated artifacts.
2. If yes, identify the minimum affected artifact chain, such as source status -> constraints -> tables/figures -> evidence package -> deliverable items -> review queue -> export manifests.
3. Regenerate only the necessary artifacts from current code using CLI commands, not a stale running server.
4. If the local Flask server is running and code changed, stop/restart it before relying on UI behavior or UI-triggered regeneration.
5. Confirm the UI is reading canonical artifact paths when UI behavior is part of the claim.
6. Report exact regeneration commands run.
7. Report which generated artifacts were intentionally left uncommitted.
8. Do not commit generated project artifacts unless explicitly approved.
9. If artifacts were not regenerated, explain why regeneration is not needed.
10. If human review state may be overwritten, use the dev/test reset flow only when appropriate and state that it is destructive to generated review candidates.

A passing code test does not prove the current local UI is showing fresh generated artifacts. Agents must distinguish code correctness from sample-project artifact freshness.

If the Flask/local web server was started before code changes, it may regenerate canonical artifacts using stale imported modules. Restart the server before using UI actions to regenerate or verify outputs.

Do not assume artifacts are stale-path bugs without checking canonical paths. Review Assist expects generated artifacts at canonical nested paths such as:

- `source_status/source_status_set.json`
- `deliverable/tables.json`
- `deliverable/figures.json`
- `evidence/evidence_package.json`
- `deliverable/deliverable_items.json`
- `review_queue/review_queue.json`
- `exports/export_manifest.json`
- `exports/deliverable_package_manifest.json`

Implementation closeout:

- Generated artifacts affected: yes/no
- Server restart needed: yes/no
- Regeneration commands run:
- Canonical artifacts verified:
- UI verified from current server: yes/no/not applicable
- Generated artifacts intentionally uncommitted:
- Focused tests run:
- Full suite run: yes/no, reason
- Remaining stale-artifact risk:
