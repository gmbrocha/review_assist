# Sprint Index

Active sprint docs live in this directory. Completed sprint docs move to `docs/archive/sprints/`.

## Active Sprint/Subunit

- Sprint 6.8 QA And Scope-Control Pass: `SPRINT_6_8_QA_AND_SCOPE_CONTROL_PASS.md`

`docs/sprints/SPRINT_4_WEB_APP_AND_WIRING.md` remains in this directory pending normal sprint-resolution/archive cleanup.

## Planned Sprint/Subunits

- Roadmap reference: `docs/sprints/ROADMAP.md`
- Sprint 6 root plan: `SPRINT_6_REVIEWER_FIGURE_STYLING_AND_REGENERATION.md`
- Sprint 6.8 QA And Scope-Control Pass: `SPRINT_6_8_QA_AND_SCOPE_CONTROL_PASS.md`

## Completed Sprint/Subunits

- Sprint 1 Foundation and Deliverable Contract: `docs/archive/sprints/SPRINT_1_FOUNDATION_AND_CONTRACT.md`
  - Completed the non-UI Sprint 1 foundation across Sprint 1.1, 1.2, and 1.3.
- Sprint 1.1 Contract Foundation: `docs/archive/sprints/SPRINT_1_1_CONTRACT_FOUNDATION.md`
  - Implemented static deliverable matrix, report prompt config, loaders/validators, CLI validators, and focused tests.
- Sprint 1.2 Project Intake Artifacts: `docs/archive/sprints/SPRINT_1_2_PROJECT_INTAKE_ARTIFACTS.md`
  - Implemented input package classification, project area artifact generation, county detection, NAIP/MARIS basemap provenance/renderability status, CLI commands, populate integration, and focused tests.
- Sprint 1.3 Comparison Units and Orchestration: `docs/archive/sprints/SPRINT_1_3_COMPARISON_UNITS_AND_ORCHESTRATION.md`
  - Implemented comparison-unit artifacts, KML folder/style/color preservation, expected-count validation, CLI command, populate integration, and focused tests.
- Sprint 2 Constraints, Tables, And Figures: `docs/archive/sprints/SPRINT_2_CONSTRAINTS_TABLES_AND_FIGURES.md`
  - Completed Sprint 2 across source profile/basemaps, comparison-unit constraints and deliverable tables, matrix-backed deliverable figures, evidence refs, validation, and documentation.
- Sprint 2.1 Source Profile And Basemaps: `docs/archive/sprints/SPRINT_2_1_SOURCE_PROFILE_AND_BASEMAPS.md`
  - Implemented the example report source profile default, Sprint 2.1 source catalog stubs, per-source status detail, Census key stubbing, MARIS/NAIP 2025 basemap indexing, and renderable sidecar detection.
- Sprint 2.2 Comparison Constraints And Tables: `docs/archive/sprints/SPRINT_2_2_COMPARISON_CONSTRAINTS_AND_TABLES.md`
  - Implemented report-facing comparison-unit constraints, source-specific table normalization, four exact matrix-backed deliverable table targets, Census stubs/local-source table rows, CLI/populate wiring, and focused tests.
- Sprint 2.3 Figures, Evidence, And Validation: `docs/archive/sprints/SPRINT_2_3_FIGURES_EVIDENCE_AND_VALIDATION.md`
  - Implemented exact matrix-backed deliverable figure targets, selected-sidecar basemap rendering/fallbacks, restricted cultural exclusion, Attachment A supporting panels, evidence package refs/summaries, CLI/populate wiring, and focused tests.
- Sprint 3.1 Deliverable Items And Review Queue: `docs/archive/sprints/SPRINT_3_1_DELIVERABLE_ITEMS_AND_REVIEW_QUEUE.md`
  - Implemented matrix-backed deliverable item generation, dynamic wetlands/waterbodies comparison-unit child sections, prompt-contract-backed section drafting payloads, bounded default review queue generation, legacy/audit queue opt-in, expanded reviewer statuses, CLI/populate wiring, and focused tests.
- Sprint 3.2 Export Gate And Package Commands: `docs/archive/sprints/SPRINT_3_2_EXPORT_GATE_AND_PACKAGE_COMMANDS.md`
  - Implemented review-complete default export gating from the standard bounded review queue, reviewed-content selection rules, structured CLI gate failures, preview bypass metadata, package manifest gate summaries, demo/MVP package behavior, and focused tests.
- Sprint 3 Review Queue, Export Gate, And DOCX Fidelity: `docs/archive/sprints/SPRINT_3_REVIEW_EXPORT_AND_DOCX.md`
  - Completed Sprint 3 across deliverable items, bounded review queue, terminal statuses, review-complete export gate, package manifests, compactness budget, DOCX fidelity, and final verification.
- Sprint 3.3 DOCX Fidelity Docs And Final Verification: `docs/archive/sprints/SPRINT_3_3_DOCX_FIDELITY_DOCS_AND_FINAL_VERIFICATION.md`
  - Implemented baseline DOCX page setup/styles, title/front matter/body/attachment assembly, bounded editable table previews, figure placeholders/captions/source/method notes, manifest-level final verification, package-manifest propagation, docs, and focused/full verification.
- Sprint 5.0 Planning Diff Lock And Numbering Decision: `docs/archive/sprints/SPRINT_5_0_PLANNING_DIFF_LOCK_AND_NUMBERING_DECISION.md`
  - Locked the Sprint 5 report-policy/source-truth/discernment sequence, numbering, non-goals, approval gates, and active pointer handoff to Sprint 5.1.
- Sprint 5.1 Canonical Policy Schema Reconciliation: `docs/archive/sprints/SPRINT_5_1_CANONICAL_POLICY_SCHEMA_RECONCILIATION.md`
  - Created the Sprint 5 package reconciliation ledger, kept `config/report_section_policy.json` canonical, added explicit section activation/review policy fields, made the PEL relationship section manual/conditional, and strengthened policy validation.
- Sprint 5.2 Extent Semantics And Wording Enforcement: `docs/archive/sprints/SPRINT_5_2_EXTENT_SEMANTICS_AND_WORDING_ENFORCEMENT.md`
  - Adopted reusable extent vocabulary, preserved presentation/collar extent metadata through merges, tightened deterministic context wording, and rejected unsafe GPT direct-project, APE, and map-as-evidence language.
- Sprint 5.3 Source Needs Manifest And Warehouse Alignment: `docs/archive/sprints/SPRINT_5_3_SOURCE_NEEDS_MANIFEST_AND_WAREHOUSE_ALIGNMENT.md`
  - Added policy-derived section source-needs records, per-source need classes, typed logical rollup/effective-truth handling, manual residual MDEQ context protection, source inventory metadata, docs, and focused tests.
- Sprint 5.4 Report Inclusion And Discernment Pass: `docs/archive/sprints/SPRINT_5_4_REPORT_INCLUSION_AND_DISCERNMENT_PASS.md`
  - Added render-policy metadata to deliverable items, review queue items, web review views, and export manifests; preserved wetlands/waterbodies narrative children; kept PEL/manual/restricted/deferred sections review-visible; and skipped body-ineligible generated placeholders from reviewed exports unless reviewer-supplied content is explicitly exportable.
- Sprint 5.5 Caveat Bundles, Prohibited Claims, And GPT Eligibility: `docs/archive/sprints/SPRINT_5_5_CAVEAT_BUNDLES_PROHIBITED_CLAIMS_AND_GPT_ELIGIBILITY.md`
  - Added an internal required-caveat guardrail registry, strengthened prohibited-claim family validation, preserved deterministic fallbacks for rejected GPT output, tightened style context as non-evidence, and kept GPT coverage unchanged.
- Sprint 5.6 Table/Figure Policy Matrix Alignment: `docs/archive/sprints/SPRINT_5_6_TABLE_FIGURE_POLICY_MATRIX_ALIGNMENT.md`
  - Added explicit table policy records for the current matrix tables, propagated table/figure policy metadata through artifacts, evidence, deliverable items, review/export summaries, preserved wetlands/waterbodies narrative children, and kept the current 4 table, 15 figure, and 3 attachment counts.
- Sprint 5.7 Manual / Reviewer-Supplied Policy MVP: `docs/archive/sprints/SPRINT_5_7_MANUAL_REVIEWER_SUPPLIED_POLICY_MVP.md`
  - Added manual-material metadata to deliverable items, review queue items, review detail summaries, and export manifest records; kept restricted/manual/optional/reviewer-supplied needs visible as review states; preserved reviewer notes as internal; and reused existing edited/replacement content and figure replacement/caption flows without adding generalized uploads.
- Sprint 5.8 Export QA And Override Policy: `docs/archive/sprints/SPRINT_5_8_EXPORT_QA_AND_OVERRIDE_POLICY.md`
  - Added policy-aware export QA manifest fields, hard-blocked default reviewed export on blocking QA errors before writing new reviewed outputs, surfaced QA readiness in export UI paths, kept internal preview as a QA-recording bypass, and deferred reviewer override-with-reason.
- Sprint 5.9 End-To-End Trial, Docs, And Verification: `docs/archive/sprints/SPRINT_5_9_END_TO_END_TRIAL_DOCS_AND_VERIFICATION.md`
  - Verified the Sprint 5 preview and reviewed-export paths, kept GPT verification dry-run only, closed the package reconciliation ledger, updated deferred work, and archived Sprint 5 planning docs.
- Sprint 5 Report Policy, Source Truth, And Discernment: `docs/archive/sprints/SPRINT_5_REPORT_INTELLIGENCE_SOURCE_TRUTH_AND_DISCERNMENT.md`
  - Completed Sprint 5 across policy schema, extent semantics, source truth, render gating, GPT guardrails, table/figure policy, manual material status, export QA, and final verification.
- Sprint 5 Policy Package Reconciliation Ledger: `docs/archive/sprints/SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md`
  - Historical package-to-policy disposition record for adopted, rejected, already-covered, and deferred Sprint 5 package proposals.
- Sprint 6.1 Existing Figure Flow Audit: `docs/archive/sprints/SPRINT_6_1_EXISTING_FIGURE_FLOW_AUDIT.md`
  - Audited the current figure generation, review queue, caption/replacement, export-image resolution, and safe integration points for future figure recipes, sparse style overrides, render jobs, versions, approval state, and export resolution.
- Sprint 6.2 Figure Recipe And Override Model: `docs/archive/sprints/SPRINT_6_2_FIGURE_RECIPE_AND_OVERRIDE_MODEL.md`
  - Added project-local figure recipes, sparse style overrides, implicit autogenerated/stub v1 figure versions, render-job metadata, and a CLI initializer without changing rendering, export resolution, source truth, review queue semantics, GPT behavior, or figure counts.
- Sprint 6.3 Reviewer Figure Editor UI: `docs/archive/sprints/SPRINT_6_3_REVIEWER_FIGURE_EDITOR_UI.md`
  - Added a figure-only review detail link and editor page showing the current preview, style model status, layer controls, active draft override summary, version summary, render-job summary, and disabled deferred regenerate/approve controls.
- Sprint 6.4 Style Override Save Logic: `docs/archive/sprints/SPRINT_6_4_STYLE_OVERRIDE_SAVE_LOGIC.md`
  - Added validated sparse style override save/reset behavior with audit-preserving superseded/reset statuses while leaving rendering, review queue state, export eligibility, and figure images unchanged.
- Sprint 6.5 Regeneration Job: `docs/archive/sprints/SPRINT_6_5_REGENERATION_JOB.md`
  - Added synchronous review-only PNG regeneration from saved/default figure style metadata with auditable render jobs and version records while preserving source, analysis, review queue, deliverable figure, and export artifacts.
- Sprint 6.6 Figure Versioning And Approval: `docs/archive/sprints/SPRINT_6_6_FIGURE_VERSIONING_AND_APPROVAL.md`
  - Added exact-version figure approval metadata, approved-version resolver helpers, editor approval actions, and version history display while keeping review queue status, deliverable figure paths, export selection, and review gates unchanged.
- Sprint 6.7 Export Integration: `docs/archive/sprints/SPRINT_6_7_EXPORT_INTEGRATION.md`
  - Added reviewed-export figure resolution through replacement images, approved figure versions, latest regenerated versions, and autogenerated/current generated figures while preserving review-gate semantics and recording selected version metadata in export items and figure assets.

## Deferred Work Linked To Sprints

See `docs/governance/DEFERRED_WORK.md` for full detail.

- Sprint 4: no backend deferred item should be newly routed here by default; Sprint 4 should consume the resolved Sprint 2/3 service contracts through a thin UI.
- Sprint 5: route source acquisition expansion, production review-state migration, GPT rewrite UX, and future figure work to deferred/future sprint items unless explicitly approved in the active subunit.
