# Sprint 5: Report Policy, Source Truth, And Discernment

## Status

Sprint 5.0 planning resolution, Sprint 5.1 canonical policy schema reconciliation, Sprint 5.2 extent semantics enforcement, and Sprint 5.3 source needs/effective truth mapping are complete. Sprint 5.4 is the active next implementation target.

Before starting each Sprint 5 implementation subunit, confirm the current clean checkpoint and load the active subunit doc. This sprint is report-policy integration work, not figure editing.

This file and the linked active subunit files are root-level planning notes for human review. Sprint 5.0, Sprint 5.1, Sprint 5.2, and Sprint 5.3 are archived as completed; move each remaining subunit doc into `docs/archive/sprints/` only when that subunit is completed under the normal sprint protocol.

## Purpose

Integrate the extracted report-policy package into Review Assist as requirements intelligence, not as a template. Sprint 5 should make report sections, source needs, extent semantics, caveats, GPT eligibility, table/figure refs, manual material status, and export QA explicit while preserving human review.

The package derived from the example Environmental Constraints Report is a requirements-mining artifact. It must not import project facts, trail/corridor defaults, PEL defaults, unfinished draft content, or restricted/manual findings into generic Review Assist behavior.

## Package Reconciliation Rule

Sprint 5 must begin with an explicit package-to-current-policy reconciliation ledger, not a direct copy of the extracted package.

Sprint 5.1 must create `SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md` as the active routing ledger for the rest of Sprint 5. The ledger compares `pro_review_assist_policy_package_sprint_5/` against the current app contract, especially `config/report_section_policy.json`, `config/deliverable_section_matrix.json`, `config/report_profiles.json`, `config/source_catalog.json`, the existing extent/GPT validators, and current report-policy docs.

Every reusable package proposal must receive a disposition:

- adopt in Sprint 5.1 policy schema
- adopt in Sprint 5.2 extent wording
- route to Sprint 5.3 source truth
- route to Sprint 5.4 render gating
- route to Sprint 5.5 caveats/GPT eligibility
- route to Sprint 5.6 table/figure alignment
- route to Sprint 5.7 manual/reviewer-supplied policy
- route to Sprint 5.8 export QA
- verify in Sprint 5.9
- reject as example-specific, PEL-specific, trail/corridor-specific, unsupported, unsafe, or already covered
- defer with a documented reason

The current app policy remains canonical unless Sprint 5.1 explicitly approves and implements a versioned migration. Package content is evidence for upgrading the current policy, not a replacement policy file by default.

## Change Classification

Default classification: `SAFE LAYER CHANGE`.

Escalate to `DOMAIN CORRECTION` and get explicit approval before changing:

- section inclusion semantics
- comparison-unit expansion defaults
- deliverable counts
- source truth interpretation
- extent/wording methodology
- GPT eligibility
- export blocking behavior

Document instead of implementing any correction that is not clearly safe.

## Pre-Sprint Gate

The stabilization gate and Sprint 5.0 planning lock are complete. Before each implementation subunit:

- inspect `git status`
- confirm the accepted checkpoint is clean
- run the subunit's focused validation commands
- do not commit generated project artifacts unless explicitly approved

## Scope

Sprint 5 may:

- reconcile the extracted package with existing `config/report_section_policy.json` through a traceable package diff ledger
- preserve source truth and source/status distinctions
- enforce analysis extent versus visual/render extent wording
- gate section rendering by trigger, source, extent, caveat, and allowed refs
- keep GPT opt-in, bounded, source-backed, and review-gated
- align existing table/figure targets with policy
- represent manual/reviewer-supplied materials honestly
- add export QA after policy metadata exists

## Non-Goals

Sprint 5 must not become:

- a new source acquisition sprint
- a figure/GIS editor sprint
- a production deployment sprint
- a full cartographic redesign
- a trail-specific report generator
- a PEL-specific template implementation
- a GPT expansion sprint
- a generated artifact cleanup sprint beyond verification needs
- a deliverable count change without explicit approval

## Subunits

- Sprint 5.0: [Planning Diff Lock And Numbering Decision](docs/archive/sprints/SPRINT_5_0_PLANNING_DIFF_LOCK_AND_NUMBERING_DECISION.md) - completed and archived
- Sprint 5.1: [Canonical Policy Schema Reconciliation](docs/archive/sprints/SPRINT_5_1_CANONICAL_POLICY_SCHEMA_RECONCILIATION.md) - completed and archived
- Sprint 5.2: [Extent Semantics And Wording Enforcement](docs/archive/sprints/SPRINT_5_2_EXTENT_SEMANTICS_AND_WORDING_ENFORCEMENT.md) - completed and archived
- Sprint 5.3: [Source Needs And Effective Truth Mapping](docs/archive/sprints/SPRINT_5_3_SOURCE_NEEDS_MANIFEST_AND_WAREHOUSE_ALIGNMENT.md) - completed and archived
- Sprint 5.4: [Section Render Gating And Comparison-Unit Expansion](SPRINT_5_4_REPORT_INCLUSION_AND_DISCERNMENT_PASS.md)
- Sprint 5.5: [Caveat Bundles, Prohibited Claims, And GPT Eligibility](SPRINT_5_5_CAVEAT_BUNDLES_PROHIBITED_CLAIMS_AND_GPT_ELIGIBILITY.md)
- Sprint 5.6: [Table/Figure Policy Matrix Alignment](SPRINT_5_6_TABLE_FIGURE_POLICY_MATRIX_ALIGNMENT.md)
- Sprint 5.7: [Manual / Reviewer-Supplied Policy MVP](SPRINT_5_7_MANUAL_REVIEWER_SUPPLIED_POLICY_MVP.md)
- Sprint 5.8: [Export QA And Override Policy](SPRINT_5_8_EXPORT_QA_AND_OVERRIDE_POLICY.md)
- Sprint 5.9: [End-To-End Trial, Docs, And Verification](SPRINT_5_9_END_TO_END_TRIAL_DOCS_AND_VERIFICATION.md)

## Dependency Order

1. Lock planning and numbering.
2. Create the package reconciliation ledger and reconcile the canonical policy schema.
3. Tighten extent semantics and wording from ledger dispositions.
4. Map source needs to effective source truth from ledger dispositions.
5. Gate section rendering and comparison-unit expansion from policy decisions.
6. Align caveats, prohibited claims, and GPT eligibility from ledger dispositions.
7. Align existing table/figure targets with policy.
8. Represent manual/reviewer-supplied materials at policy/review-gate level.
9. Add export QA after required metadata exists.
10. Run the end-to-end trial and final verification, including ledger closure.

## Approval Gates

Human approval is required for:

- canonical policy file path/version
- PEL/default section behavior
- wetlands/waterbodies comparison-unit narrative default
- initial GPT-eligible sections
- manual/reviewer-supplied source class behavior
- export QA hard-block versus reviewer override with required reason
- any deliverable matrix count change

## Implementation Rules

- Treat package content as requirements-mining evidence only.
- Do not consume package content in product behavior until a ledger disposition maps it to current app IDs, records the owning subunit, and states whether it is adopted, routed, rejected, or deferred.
- Preserve feature neutrality; use project features, submitted features, comparison units, project geometry, study area, and project area language.
- Use trail/corridor/PEL language only when project metadata or reviewer-supplied context explicitly supports it.
- Keep deterministic GIS/source checks separate from GPT-assisted synthesis.
- Do not infer missing findings, permit conclusions, jurisdictional status, eligibility, no-effect/no-impact, contamination status, commitments, or final determinations.
- Keep report body output compact; raw records stay in evidence or attachments.
- Preserve reviewer review gates before export.

## Test Expectations

Each behavior-changing subunit should add focused tests before broader verification. Protect:

- package-diff ledger coverage and disposition closure
- policy validation and matrix alignment
- source truth/status reconciliation
- extent wording and context-only language
- section render gating
- GPT eligibility and prohibited-claim rejection
- table/figure allowed refs and compactness
- manual/reviewer-supplied material review state
- export QA and preview/override behavior

## Success Statement

At the end of Sprint 5, Review Assist should be able to say:

> We screened the source warehouse, identified what matters, explained what is missing, kept extent and source truth honest, let the human decide, and drafted only approved/source-backed pieces within strict policy.
