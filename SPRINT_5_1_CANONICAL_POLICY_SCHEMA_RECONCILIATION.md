# Sprint 5.1: Canonical Policy Schema Reconciliation

## Status

Parked for implementation after Sprint 5.0 is accepted and the worktree is clean.

## Goal

Reconcile the extracted package's proposed policy object with the existing app policy contract.

The current app already uses `config/report_section_policy.json` as the canonical section policy. Do not create `config/review_assist_report_policy.json` unless this subunit explicitly decides and implements a versioned migration.

## Scope

This subunit may update:

- `config/report_section_policy.json`
- `src/review_assist/report_section_policy.py`
- `docs/domains/REPORT_POLICY.md`
- focused policy tests

## Policy Fields To Reconcile

Each matrix section should have an explicit, validated position on:

- section ID and title
- default/conditional/manual/deferred status
- trigger or activation condition
- source category and allowed source refs/categories
- extent policy
- visual extent class
- comparison-unit expansion policy
- evidence pattern
- allowed tables and figures
- output shape
- drafting mode
- GPT readiness
- required caveats
- prohibited claims
- manual/reviewer-supplied status
- review requirements

## Human Decisions Required

- Keep evolving `config/report_section_policy.json` or migrate to a new versioned policy file.
- Whether `relationship-with-pel-study` should remain required, become conditional/manual, or remain only as a reviewed stub.
- Whether `wetlands-waterbodies-alternative-detail` should remain default narrative children or become table-only/conditional.
- Which existing GPT-ready sections should be narrowed before any future GPT run.

## Non-Goals

- No source acquisition.
- No deliverable count change unless approved.
- No section rendering behavior changes beyond policy validation unless explicitly included.
- No GPT calls or GPT coverage expansion.

## Acceptance Criteria

- Every deliverable matrix section and figure has a policy or explicit exemption.
- Existing table/figure refs are allowed only where policy says they are allowed.
- Manual/reviewer-supplied sections are not GPT-ready by default.
- Conditional/custom sections are machine-readable rather than implied by prose.
- Policy validation fails on unknown section IDs, unknown refs, unsupported extent classes, unsupported GPT readiness, and GPT-ready sections without bounded evidence/caveats/prohibited claims.

## Required Tests

- `tests/test_report_section_policy.py`
- New focused tests for:
  - PEL section default/manual decision
  - comparison-unit expansion policy values
  - GPT-ready sections requiring caveats/prohibited claims/allowed refs
  - unknown table/figure/source ref rejection

## Documentation Updates

- `docs/domains/REPORT_POLICY.md`
- `docs/governance/DEFERRED_WORK.md` if a policy migration or major section behavior decision is deferred
