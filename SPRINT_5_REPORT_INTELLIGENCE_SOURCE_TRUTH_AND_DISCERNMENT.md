# Sprint 5: Report Policy, Source Truth, And Discernment

## Status

Accepted planning direction; implementation has not started.

Do not start Sprint 5 implementation until the current clean checkpoint is confirmed and the active subunit doc is loaded. This sprint is report-policy integration work, not figure editing.

This file and the linked subunit files are root-level planning notes for human review. Move completed subunit docs into `docs/archive/sprints/` only when each subunit is completed under the normal sprint protocol.

## Purpose

Integrate the extracted report-policy package into Review Assist as requirements intelligence, not as a template. Sprint 5 should make report sections, source needs, extent semantics, caveats, GPT eligibility, table/figure refs, manual material status, and export QA explicit while preserving human review.

The package derived from the example Environmental Constraints Report is a requirements-mining artifact. It must not import project facts, trail/corridor defaults, PEL defaults, unfinished draft content, or restricted/manual findings into generic Review Assist behavior.

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

The stabilization gate is complete enough to begin planning and then Sprint 5.0. Before each implementation subunit:

- inspect `git status`
- confirm the accepted checkpoint is clean
- run the subunit's focused validation commands
- do not commit generated project artifacts unless explicitly approved

## Scope

Sprint 5 may:

- reconcile the extracted package with existing `config/report_section_policy.json`
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

- Sprint 5.0: [Planning Diff Lock And Numbering Decision](SPRINT_5_0_PLANNING_DIFF_LOCK_AND_NUMBERING_DECISION.md)
- Sprint 5.1: [Canonical Policy Schema Reconciliation](SPRINT_5_1_CANONICAL_POLICY_SCHEMA_RECONCILIATION.md)
- Sprint 5.2: [Extent Semantics And Wording Enforcement](SPRINT_5_2_EXTENT_SEMANTICS_AND_WORDING_ENFORCEMENT.md)
- Sprint 5.3: [Source Needs And Effective Truth Mapping](SPRINT_5_3_SOURCE_NEEDS_MANIFEST_AND_WAREHOUSE_ALIGNMENT.md)
- Sprint 5.4: [Section Render Gating And Comparison-Unit Expansion](SPRINT_5_4_REPORT_INCLUSION_AND_DISCERNMENT_PASS.md)
- Sprint 5.5: [Caveat Bundles, Prohibited Claims, And GPT Eligibility](SPRINT_5_5_CAVEAT_BUNDLES_PROHIBITED_CLAIMS_AND_GPT_ELIGIBILITY.md)
- Sprint 5.6: [Table/Figure Policy Matrix Alignment](SPRINT_5_6_TABLE_FIGURE_POLICY_MATRIX_ALIGNMENT.md)
- Sprint 5.7: [Manual / Reviewer-Supplied Policy MVP](SPRINT_5_7_MANUAL_REVIEWER_SUPPLIED_POLICY_MVP.md)
- Sprint 5.8: [Export QA And Override Policy](SPRINT_5_8_EXPORT_QA_AND_OVERRIDE_POLICY.md)
- Sprint 5.9: [End-To-End Trial, Docs, And Verification](SPRINT_5_9_END_TO_END_TRIAL_DOCS_AND_VERIFICATION.md)

## Dependency Order

1. Lock planning and numbering.
2. Reconcile the canonical policy schema.
3. Tighten extent semantics and wording.
4. Map source needs to effective source truth.
5. Gate section rendering and comparison-unit expansion.
6. Align caveats, prohibited claims, and GPT eligibility.
7. Align existing table/figure targets with policy.
8. Represent manual/reviewer-supplied materials at policy/review-gate level.
9. Add export QA after required metadata exists.
10. Run the end-to-end trial and final verification.

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
- Preserve feature neutrality; use project features, submitted features, comparison units, project geometry, study area, and project area language.
- Use trail/corridor/PEL language only when project metadata or reviewer-supplied context explicitly supports it.
- Keep deterministic GIS/source checks separate from GPT-assisted synthesis.
- Do not infer missing findings, permit conclusions, jurisdictional status, eligibility, no-effect/no-impact, contamination status, commitments, or final determinations.
- Keep report body output compact; raw records stay in evidence or attachments.
- Preserve reviewer review gates before export.

## Test Expectations

Each behavior-changing subunit should add focused tests before broader verification. Protect:

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
