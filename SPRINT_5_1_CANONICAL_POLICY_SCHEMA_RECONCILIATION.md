# Sprint 5.1: Canonical Policy Schema Reconciliation

## Status

Active next implementation target after Sprint 5.0 planning resolution. Begin only from a clean checkpoint with this subunit doc loaded.

## Goal

Create the traceable package-to-current-policy diff, then reconcile the extracted package's proposed policy object with the existing app policy contract.

The current app already uses `config/report_section_policy.json` as the canonical section policy. Do not create `config/review_assist_report_policy.json` unless this subunit explicitly decides and implements a versioned migration.

This subunit is not complete until it produces a reconciliation ledger that future Sprint 5 subunits can consume.

## Scope

This subunit may update:

- `SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md`
- `config/report_section_policy.json`
- `src/review_assist/report_section_policy.py`
- `docs/domains/REPORT_POLICY.md`
- focused policy tests

## Required Package Diff Pass

Before changing policy behavior, compare `pro_review_assist_policy_package_sprint_5/` against the current app contract:

- proposed `config/review_assist_report_policy.json`
- package report-policy and GPT-style docs
- package handoff/prompt notes
- current `config/report_section_policy.json`
- current `config/deliverable_section_matrix.json`
- current report profiles, source catalog, extent policy, GPT guardrails, and report-policy docs

Create `SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md` with one row or compact record per meaningful difference. Each record must include:

- package item or pattern
- current app equivalent, if any
- disposition: adopt-now, route-to-subunit, reject, already-covered, or defer
- owner subunit
- rationale
- approval needed, if any
- implementation target or permanent-doc target

The ledger must cover at least:

- section/default/trigger differences
- PEL and other parent-study/custom context behavior
- wetlands/waterbodies comparison-unit detail behavior
- extent vocabulary and visual extent classes
- source needs and source truth classes
- table, figure, and attachment support
- caveat bundles and prohibited-claim bundles
- GPT eligibility and style-context restrictions
- manual/reviewer-supplied and restricted material handling
- review/export gate requirements
- package items rejected as example-specific, PEL-specific, trail/corridor-specific, incomplete, unsupported, or unsafe

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
- Approve the package reconciliation ledger dispositions that affect canonical schema or behavior.
- Whether `relationship-with-pel-study` should remain required, become conditional/manual, or remain only as a reviewed stub.
- Whether `wetlands-waterbodies-alternative-detail` should remain default narrative children or become table-only/conditional.
- Which existing GPT-ready sections should be narrowed before any future GPT run.

## Non-Goals

- No source acquisition.
- No deliverable count change unless approved.
- No section rendering behavior changes beyond policy validation unless explicitly included.
- No GPT calls or GPT coverage expansion.

## Acceptance Criteria

- The package reconciliation ledger exists and compares the package policy object/docs to the current app policy, matrix, sources, extent, GPT, and export contracts.
- Every meaningful package proposal is classified as adopted, routed to a later Sprint 5 subunit, rejected, already covered, or deferred.
- Adopted 5.1 changes are applied to the current canonical policy contract rather than by wholesale package-file replacement unless a versioned migration is explicitly approved.
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

- `SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md`
- `docs/domains/REPORT_POLICY.md`
- `docs/governance/DEFERRED_WORK.md` if a policy migration or major section behavior decision is deferred
