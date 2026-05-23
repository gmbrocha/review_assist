# Report Policy

This document explains the machine-readable report policy in `config/report_section_policy.json`.

## Purpose

The policy defines what each report section is allowed to mean before any GPT-assisted interpretation is expanded. It keeps spatial interpretation, figure presentation, evidence patterns, comparison-unit expansion, caveats, prohibited claims, and GPT readiness explicit and reviewable.

The policy is a contract layer. It does not download sources, change query distances, change comparison-unit generation, change analysis geometry, change deliverable counts, or bypass human review.

## Package Reconciliation Workflow

Sprint 5 used `docs/archive/sprints/SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md` to route proposals mined from `docs/archive/packages/pro_review_assist_policy_package_sprint_5/`. The package policy and docs remain archived requirements evidence, not replacement runtime config.

Reusable package proposals were mapped to current app IDs and classified as adopted, rejected, already covered, or deferred before product behavior consumed them. Example-specific, PEL-specific, trail/corridor-specific, unsupported, incomplete, or unsafe package content must remain out of generic Review Assist behavior unless reviewer-supplied project context supports it.

## Section Activation Fields

Each section policy records three activation/review fields in addition to source, extent, table, figure, caveat, and GPT controls:

- `section_role`: `evidence_section`, `umbrella_section`, `structural_heading`, `front_matter`, or `manual_item`.
- `inclusion_status`: `default`, `conditional`, `manual`, `deferred`, or `required_stub`.
- `activation_condition`: `always`, `source_backed_or_stub`, `manual_reviewer_supplied`, `reviewer_supplied_parent_study`, `deferred_source`, or `dynamic_comparison_units`.
- `review_requirement`: `standard_review`, `manual_review`, or `source_gap_review`.

These fields make the current report contract explicit. They do not by themselves add source acquisition, change matrix deliverable counts, or make a section GPT-ready.

`relationship-with-pel-study` is conditional/manual. It activates only when a parent study or equivalent reviewer-supplied context is present, requires manual review, is marked reviewer-supplied, and is not GPT-ready by default.

`umbrella_section` policies are structural report-orientation sections. They summarize report categories and child-section status at a high level, but they do not inherit every child source/table/figure validation issue as report-facing body text or parent blockers. Detailed source gaps, restricted/manual needs, render limitations, and stubbed artifact warnings remain attached to the relevant child section, table, figure, or attachment item.

`structural_heading` policies are outline-only report headings. They remain in matrix/report order and export as headings, but they do not create deliverable items or review queue items, do not aggregate evidence/source refs, do not require review-gate acceptance, and are never GPT-ready. `natural-and-ecological-resources` is currently heading-only; its child resource subsections carry the reviewable evidence and limitations.

## Extent Rules

- `direct_project`: evidence may describe mapped relationships within submitted project features, comparison units, or current project-area analysis bounds.
- `screening_buffer`: evidence may describe features within a configured screening buffer; wording must not imply direct impact.
- `nearby_context` / `community_context`: evidence supports vicinity or community context only. It may use "near the project area" or "in the project vicinity"; it must not say direct impact.
- `watershed_context`: evidence supports watershed or subwatershed setting. It must not imply the whole watershed is directly affected. If watershed context is unavailable, the figure/section must remain deferred or stubbed.
- `county_or_regional_context`: evidence supports county, regional, tract, or similar demographic/context summaries. It must not imply project-level impact.
- `manual_reviewer_supplied`: the section depends on reviewer-supplied or restricted material and is not GPT-ready by default.
- `not_spatial`: front matter or workflow narrative that is exempt from spatial interpretation.

Presentation-only render/collar extent is never an interpretation extent. Figure render extent, basemap materialization extent, and legend/collar space may make a map readable, but they must not drive intersections, counts, evidence, tables, or report conclusions.

Extent term semantics:

- `within`: direct intersection with a named analysis extent, or a named buffer explicitly stated in the sentence.
- `near`: outside direct extent but within configured screening/context evidence.
- `adjacent`: touches or is explicitly tagged adjoining; not generic nearby.
- `downstream`: hydrologic network evidence or reviewer-confirmed relationship.
- `watershed/subwatershed`: hydrologic context geography, not a direct project footprint or impact claim.
- `county/regional`: regional context geography, not a project-area impact or project-footprint demographic claim.
- `APE`: reviewer-defined cultural extent only; do not infer it from a generic buffer.
- `corridor`: use only when submitted project geometry or reviewer metadata supports corridor/route language.
- `shown on map`: presentation support only; map extent or collar space is not evidence of intersection or impact.

## Comparison-Unit Expansion

The policy distinguishes:

- `none`: no per-comparison-unit expansion.
- `table_only`: comparison-unit detail should stay in tables unless a later policy changes it.
- `narrative_children`: generate child narrative sections by comparison unit.
- `conditional`: expand only when source-backed evidence and report shape justify it.
- `context_summary_list`: use compact nearby/context summaries rather than per-alternative subsections.
- `manual_only`: reviewer-supplied material controls the section.

Current required narrative children are limited to wetlands/waterbodies comparison-unit details.

## Render Gating

Deliverable and review queue items carry policy-backed render metadata:

- `policy_inclusion_status`
- `policy_activation_condition`
- `policy_review_requirement`
- `policy_comparison_unit_expansion`
- `render_decision`
- `render_destination`
- `render_decision_reason`
- `report_body_eligible`

Supported render decisions are `include_body`, `table_figure_only`, `attachment_status`, `needs_reviewer_decision`, `blocked_missing_source`, `blocked_manual_or_restricted_source`, `custom_project_required`, and `audit_only`.

`include_body` sections may produce normal report-body review candidates. `table_figure_only` sections preserve related table/figure refs and stay out of normal body prose unless a reviewer supplies exportable body content. `attachment_status` items belong in the attachment export group. Manual, restricted, deferred, or missing-source sections remain visible in the review queue as status/stub items rather than unsupported generic prose.

Wetlands/waterbodies keep `narrative_children` as the current policy. The package `table_only` recommendation for wetlands/waterbodies was rejected for current behavior in Sprint 5.4 so comparison-unit child review items and deliverable counts remain stable.

Floodplains and floodways are an evidence-bearing body section supported by the FEMA flood-zone table and figure. Their comparison-unit detail remains table-oriented, but the section itself is report-body eligible when FEMA/NFHL evidence is available and must carry screening-level, non-regulatory floodplain limitations.

## Table And Figure Policies

`config/report_section_policy.json` also defines policy records for matrix-backed tables and figures.

`table_policies` must cover every current matrix table target exactly. Each table policy records the table ID, title, interpretation extent policy, allowed source categories, the maximum number of rows that may appear in normal report-body previews, and the overflow destination for full detail. The current compact default is `max_body_preview_rows: 5` with `overflow_destination: table_artifact`.

`figure_policies` must cover every current matrix figure target exactly. Each figure policy records the figure ID, title, interpretation extent policy, visual extent class, rendering extent class, presentation-only render-extent flag, and allowed source categories.

Policy validation rejects missing or unknown table/figure IDs, unknown source categories, section refs to unknown tables/figures, table policies with invalid extent policies, and non-positive table preview caps. Figure render extent remains presentation support only and must not be used as analysis evidence.

Sprint 5.6 preserves the current deliverable inventory: 4 tables, 15 figures, and 3 attachments. Package-proposed table or figure additions are rejected for current behavior when they would change counts, or deferred to future work when they require new source acquisition, methodology, or export-shape approval. Full table rows and figure metadata remain in artifacts and evidence; the report body receives bounded previews and review-visible policy metadata.

## GPT Readiness

GPT readiness is not execution. GPT calls remain disabled unless the reviewer/operator explicitly uses GPT Interpretive Assist.

Readiness values mean:

- `gpt_ready_now`: section policy is considered ready for a source-backed GPT candidate run.
- `gpt_ready_after_extent_metadata_verification`: section is eligible for explicit GPT Interpretive Assist when current artifacts provide source-backed evidence and extent metadata.
- `deterministic_only_for_now`: deterministic text should remain the path.
- `manual_reviewer_supplied_only`: reviewer material is required; GPT should not draft from placeholders.
- `blocked_by_missing_source_acquisition`: source/query work must happen first.
- `blocked_by_policy_ambiguity`: the scope or output shape needs another policy decision before GPT use.

Every GPT-eligible section must have bounded evidence refs, required caveats, and prohibited claims. Manual/reviewer-supplied sections are not GPT-ready by default. GPT Interpretive Assist still filters to source-backed `section_text` items, skips missing-source/P2 stubs by default, caches by evidence/policy/style/model fingerprint, and writes only unaccepted review candidates.

## Caveat And Claim Guardrails

`required_caveats` values are validated against an internal registry. A new caveat ID must be added to that registry before it can appear in `config/report_section_policy.json`; otherwise policy validation fails. This keeps caveat wording intentional without migrating the policy file into the package bundle schema.

`prohibited_claims` uses tuned family patterns for known unsafe claim families and literal fallback matching for section-specific claims. `inherit_global` / `inherit_global_guardrails` remain inheritance markers, not literal text to match.

Known prohibited families include final impact/no-impact/no-effect language, wetland/water jurisdictional determinations, cultural eligibility/effect/clearance, contamination extent/cleanup/liability conclusions, permit required/not-required conclusions, access/mitigation/construction commitments, alternative ranking/scoring/selection/rejection, and demographic impact conclusions.

## Current P1 Alignments

- `demographic-characteristics` uses county/regional policy because its table and figure refs are county/regional context.
- `oil-wells` is explicit as `direct_check_with_context_figure`: direct checks and nearby/context figure presentation are distinct, and nearby records must not become direct-impact language.
- `figure-census-tracts` preserves `county_regional` visual semantics even though current rendering may reuse medium/context extent behavior internally.
