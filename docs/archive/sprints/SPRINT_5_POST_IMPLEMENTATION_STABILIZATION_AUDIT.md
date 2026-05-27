# Sprint 5 Post-Implementation Stabilization Audit

## A. Stabilization Verdict

Verdict: PAUSE for a small stabilization cleanup before Sprint 6 or Sprint 7 implementation.

Sprint 5 produced a coherent policy baseline in the main report/export path: policy validation passes, generated artifacts regenerate from current code, reviewed export hard-block behavior works in a disposable reviewed-export simulation, and the full test suite passes. The audit did not find a P0 source-truth, export, or review-gate break.

Two P1 issues should be reviewed and fixed before new implementation:

- GPT Interpretive Assist eligibility can list sections whose `section_source_needs` status is `manual_review_needed` or `restricted_review_needed`.
- `section_source_needs` status can understate a section's policy-level `deferred_source` activation when some broad source-category layers are available.

Both are narrow policy-consistency issues. Normal regeneration does not call GPT, manual placeholders remain review/export gated, and reviewed export simulation still passes with zero blocking QA errors.

Stabilization cleanup follow-up: accepted P1 cleanup was applied after this audit. GPT planning now reads `section_source_needs` and skips manual/restricted reviewer-needed section truth with explicit skip reasons. Section source-needs summaries now distinguish `fully_satisfied`, `partially_satisfied`, and `satisfied_with_deferred` so policy-level `deferred_source` activation is not hidden by available sibling evidence.

## B. Worktree Classification

Current branch: `sprint-5` at `92e187b Complete Sprint 5.9 end-to-end verification`, tracking `origin/sprint-5`.

Tracked worktree state before writing this report: clean.

Current dirty items:

| Item | Status | Classification | Action |
|---|---:|---|---|
| `scratch_DO_NOT_DELETE.txt` | untracked | scratch/temp | Omit. Leave untouched. |
| `docs/sprints/SPRINT_5_POST_IMPLEMENTATION_STABILIZATION_AUDIT.md` | untracked | audit report / human review artifact | Human decision before commit. |

Ignored/generated artifacts observed:

- `projects/trails/` generated artifact directories refreshed by this audit.
- Existing ignored `projects/conexon_projects/` generated artifact directories.
- Existing ignored local `sources/` raw/warehouse data.
- Existing ignored `outputs/review_assist_web*.log` files.
- `.venv/`, `.pytest_cache/`, `__pycache__/`, and `src/review_assist.egg-info/`.

Tracked sample fixture files remain only:

- `projects/trails/README.md`
- `projects/trails/config/project.json`
- `projects/trails/config/sources.json`
- `projects/trails/inputs/trail_route_alternatives.kmz`

`projects/trails/config/sources.json` registers 27 sources: 25 `local_materialized`, 2 `candidate_needs_local_layer` (`usgs_nhd_hydrography`, `mrlc_nlcd_land_cover`). It is sample-project state, not generated output.

## C. Sprint 5 Implementation Inventory

Sprint 5 changed 60 tracked files from baseline commit `6b15fb4`.

Major changed config:

- `config/report_section_policy.json`: expanded canonical policy to 44 section policies, 4 table policies, and 15 figure policies.
- `config/report_generation_prompts.json`: PEL/manual guardrail wording.
- `config/report_style_context/environmental_constraints_report_style.md`: non-evidence style context guardrails.

Major changed modules:

- `src/review_assist/report_section_policy.py`
- `src/review_assist/extent_policy.py`
- `src/review_assist/source_status.py`
- `src/review_assist/source_inventory.py`
- `src/review_assist/deliverable_tables.py`
- `src/review_assist/deliverable_figures.py`
- `src/review_assist/deliverable_figure_contract.py`
- `src/review_assist/evidence_package.py`
- `src/review_assist/deliverable_items.py`
- `src/review_assist/review_queue.py`
- `src/review_assist/section_drafting.py`
- `src/review_assist/gpt_interpretive_assist.py`
- `src/review_assist/export_report.py`
- `src/review_assist/web/adapter.py`
- `src/review_assist/web/templates/export.html`
- `src/review_assist/web/templates/review.html`
- `src/review_assist/web/templates/review_detail.html`

Major changed tests:

- `tests/test_report_section_policy.py`
- `tests/test_deliverable_items.py`
- `tests/test_deliverable_tables.py`
- `tests/test_deliverable_figures.py`
- `tests/test_evidence_and_gpt.py`
- `tests/test_gpt_interpretive_assist.py`
- `tests/test_review_queue.py`
- `tests/test_export_report.py`
- `tests/test_workflow_artifacts.py`
- `tests/test_source_inventory_and_tables.py`
- `tests/test_deliverable_matrix.py`

Major changed docs:

- `docs/core/CURRENT_STATE.md`
- `docs/domains/REPORT_POLICY.md`
- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/domains/DATA_SOURCES.md`
- `docs/domains/SOURCE_WAREHOUSE.md`
- `docs/domains/MAP_GENERATION.md`
- `docs/domains/LLM_ASSISTED_SYNTHESIS.md`
- `docs/domains/REVIEW_POLICY.md`
- `docs/domains/UNCERTAINTY_AND_PROVENANCE.md`
- `docs/governance/DEFERRED_WORK.md`
- `docs/sprints/SPRINT_5_MIDPOINT_STABILIZATION.md`
- archived Sprint 5 subunit docs.

No generated project artifacts are tracked for commit.

## D. Report Policy Audit Findings

Policy coverage:

- Matrix sections: 44.
- Policy sections: 44.
- Matrix tables: 4.
- Table policies: 4.
- Matrix figures: 15.
- Figure policies: 15.
- Missing policy sections: none.
- Unknown policy sections: none.
- Duplicate section IDs: none.
- Section title mismatches: none.
- Unknown generated source refs in tables/figures/items: none.

Every section policy has:

- `section_id`
- `title`
- `section_family`
- `source_category`
- `inclusion_status`
- `activation_condition`
- `review_requirement`
- `extent_policy`
- `visual_extent_class`
- `comparison_unit_expansion_policy`
- `evidence_pattern`
- `drafting_mode`
- `expected_output_shape`
- `required_caveats`
- `prohibited_claims`
- allowed source/table/figure refs
- `manual_or_reviewer_supplied`
- `gpt_readiness`

GPT-ready policy sections:

- Wetlands/waterbodies parent and dynamic child template.
- Floodplains/floodways.
- Cultural/historic public context sections.
- Community-resource context sections.
- Utility/energy context sections.
- Regulated facility/hazmat/oil-well sections.

Manual/reviewer-supplied sections are not GPT-ready by policy. PEL is conditional/manual and non-GPT.

P1 finding: GPT runtime eligibility does not currently use `section_source_needs` to filter out `manual_review_needed` or `restricted_review_needed` sections. See section L.

## E. Comparison-Unit Expansion Findings

Policy distribution:

- `none`: 14 section policies.
- `context_summary_list`: 19 section policies.
- `manual_only`: 6 section policies.
- `narrative_children`: 2 section policies.
- `conditional`: 2 section policies.
- `table_only`: 1 section policy.

Explicit narrative children are limited to:

- `wetlands-and-waterbodies`
- `wetlands-waterbodies-alternative-detail`

Generated output:

- Five wetlands/waterbodies dynamic comparison-unit child review items were produced.
- Per-comparison-unit children are not generated universally.
- `floodplains-and-floodways` is table/figure-only and body-ineligible by render policy.
- Watershed, county/regional, deferred, and manual sections do not generate per-alternative narrative children.

No evidence of the 640-page report failure mode was found. No generated section exceeded the audit's content-length concern threshold.

## F. Extent Semantics Findings

Extent metadata is present across:

- source-backed constraints
- deliverable tables
- deliverable figures
- evidence summaries
- deliverable items
- review queue items
- export manifests

Representative items:

| Item | Extent/result |
|---|---|
| `wetlands-and-waterbodies` | Direct/project interpretation; render/collar metadata present only as presentation support. |
| Wetlands dynamic child | Direct/project interpretation; body-eligible narrative child. |
| `floodplains-and-floodways` | Direct/project table/figure-only; body-ineligible. |
| `water-quality` | Watershed context label; blocked-missing-source/status stub; wording says current automated evidence remains limited to project-area bounds until watershed query implementation exists. |
| `cultural-and-historic-resources` | Nearby/context; public/coarse source only; restricted source not mapped. |
| `health-care-facilities` | Community context; not direct impact wording. |
| `hazardous-materials-sites` | Nearby/context; not contamination extent/liability wording. |
| `oil-wells` | Direct-check section with context figure distinction. |
| `demographic-characteristics` | County/regional context; Census figure/table stubs remain explicit. |
| Main figures | `render_extent_type: figure_render_extent`; most rendered figures carry `presentation_extent_type: presentation_only_collar_extent`; `render_extent_is_presentation_only: true`. |

Figure `figure-streams-impaired-waters` correctly records `figure_extent_context_deferred`: watershed/subwatershed render context is not implemented and current project-area presentation extent is not treated as watershed evidence.

P2 cleanup: Some deterministic preview body text repeats `source_selection_reason` strings verbosely, especially aggregate/context sections. It is review-gated and truthful, but reads like internal policy metadata rather than polished report prose.

## G. Source Truth / Source Needs Findings

Specific source audit:

| Source | Effective result |
|---|---|
| `usfws_nwi_wetlands` | `local_materialized`, `available_materialized`. |
| `usgs_nhd_hydrography` | `logical_rollup_satisfied` by `usgs_nhd_flowlines`, `usgs_nhd_other_areas`, `usgs_nhd_waterbodies`. |
| `usgs_nhd_flowlines` | `local_materialized`, used for stream crossing metrics. |
| `usgs_nhd_waterbodies` | `local_materialized`, waterbody context. |
| `usgs_nhd_other_areas` | `local_materialized`, hydrography context. |
| `mdeq_303d_impaired_waters` | `local_materialized`, optional water-quality context. |
| `mdeq_public_water_supply_wells` | `local_materialized`, PWS figure source. |
| `fema_nfhl_flood_hazard` | `local_materialized`. |
| `epa_envirofacts_echo` | `logical_rollup_satisfied` by specific regulated-facility child layers. |
| `epa_frs_facilities_ms` | `local_materialized`. |
| `mdeq_environmental_context` | `manual`, `manual_reviewer_supplied`; not rollup-satisfied. |
| MARIS regulated facility layers | `local_materialized`. |
| `mississippi_oil_gas_wells` | `local_materialized`. |
| `county_parcels_property_age` | `optional`, non-alarming. |
| `maris_public_cultural_context` | `public_coarse_screening_context`. |
| `mdah_restricted_archaeology` | `restricted_authorized_reviewer_supplied`. |

Source status category counts:

- `provided_locally`: 12.
- `stubbed`: 1.
- `optional`: 1.

Source need class counts:

- `available_materialized`: 26.
- `manual_reviewer_supplied`: 8.
- `public_coarse_screening_context`: 5.
- `restricted_authorized_reviewer_supplied`: 2.
- `deferred`: 2.
- `optional`: 1.

P1 finding: `section_source_needs` section status can conflict with section policy activation:

| Section | Policy activation | Source-needs status observed |
|---|---|---|
| `water-quality` | `deferred_source` | `source_backed_or_optional` before cleanup; `satisfied_with_deferred` after cleanup |
| `public-water-supply` | `deferred_source` | `manual_review_needed` |
| `airports` | `deferred_source` | `manual_review_needed` |
| `local-businesses-and-economic-nodes` | `deferred_source` | `manual_review_needed` |

Deliverable rendering still honors policy (`blocked_missing_source`, body-ineligible, `manual_material.material_status: deferred_source`). The issue is the source-needs manifest label, not export gating.

P2 finding: stale acquisition/download history is correctly marked as ignored, but the `stale_*_ignored` warnings are repeated into downstream validation arrays and preview manifests. They do not become availability failures, but they may create review noise.

## H. Deliverable Table Findings

Generated table count: 4.

| Table | Rows | Stub | Source refs | Finding |
|---|---:|---|---|---|
| `table-wetlands-waterbodies` | 5 | no | `usfws_nwi_wetlands`, `usgs_nhd_flowlines` | Correctly excludes broad `usgs_nhd_hydrography` rollup and polygon hydrography from stream crossing metric. |
| `table-fema-flood-zones` | 10 | no | `fema_nfhl_flood_hazard` | Source-backed. |
| `table-income-demographics` | 0 | yes | Census/community refs | Honest stub. |
| `table-demographic-composition` | 0 | yes | Census/community refs | Honest stub. |

No table validation issues. Body preview cap remains 5 rows. Known stream crossing metric calibration remains deferred in `DEFERRED_WORK.md`.

## I. Deliverable Figure Findings

Generated main figure count: 15. Supporting attachment figure count: 3.

Rendered/stubbed:

- Rendered main figures: 14.
- Stubbed main figures: 1 (`figure-census-tracts`).

Figure warnings are review-visible and expected:

- `figure_extent_context_deferred`: 1.
- `figure_source_unimplemented`: 8.
- `restricted_source_not_mapped`: 1.
- `figure_created_as_stub`: 1.

Representative source scoping:

- `figure-wetlands-waterbodies`: NWI, NHD waterbodies, NAIP sidecar; no broad rollup physical source ref.
- `figure-streams-impaired-waters`: NHD child layers, MDEQ 303(d), NAIP; watershed context explicitly deferred.
- `figure-public-water-supply-wells`: MDEQ/MARIS PWS wells and NAIP.
- Regulated figures use specific child layers, not `epa_envirofacts_echo`.
- Cultural figure uses public cultural context and records restricted-source non-rendering.

Captions/source/method notes are exported as text, not embedded in PNGs.

## J. Evidence Package Findings

Evidence package counts:

- `constraint_count`: 2547.
- `deliverable_table_count`: 4.
- `deliverable_figure_count`: 15.
- `deliverable_figure_stub_count`: 1.
- `source_backed_constraint_count`: 2547.
- `real_source_count`: 25.
- `stub_count`: 1.
- `section_evidence`: 35 section records.

Evidence includes raw artifact paths for audit lineage by design. The GPT dry-run artifact did not expose full raw feature dumps or root `sources/` paths. Tests cover GPT-bound payload stripping.

Validation issues are warnings/info only and mirror figure/source limitations.

## K. Deliverable Item / Review Queue Findings

Generated deliverable items: 70.

Generated review queue items: 70.

Render decision counts:

- `include_body`: 36.
- `needs_reviewer_decision`: 3.
- `table_figure_only`: 20.
- `blocked_missing_source`: 5.
- `attachment_status`: 6.

Manual material counts:

- `source_backed_generated`: 49.
- `not_used`: 8.
- `manual_required`: 8.
- `deferred_source`: 5.

Manual material types:

- `none`: 61.
- `supporting_document`: 6.
- `manual_text`: 3.

Reset dry-run:

- Would refresh canonical upstream artifacts and rebuild 70 queue items.
- Process-language audit reported false for deliverable items and review queue.
- Preserves source data, project setup, layers, source acquisition, materialization, basemaps, and exports unless flags request otherwise.

P2 cleanup: preview body content for status/manual/deferred sections is truthful but visibly status-like, for example `Render decision: blocked_missing_source`. This is acceptable for review/status items but should not be considered polished report body.

## L. GPT Readiness Findings

Verified:

- GPT is off by default.
- `populate-for-review projects/trails --no-gpt-drafting` produced `GPT drafting: False`.
- `draft-section-candidates --dry-run --json` made no live GPT calls.
- Dry run reported `completed_call_count: 0`.
- Tests prevent root `.env` from enabling live GPT/API runs.
- GPT output validation covers unknown refs, prohibited claim families, context overclaims, APE language without reviewer-defined context, style/example leakage, and deterministic fallback preservation.
- PEL is skipped as `manual_or_reviewer_supplied`.

P1 finding: dry-run `eligible_sections` includes sections with `section_source_needs` statuses that are not cleanly source-backed:

- `restricted_review_needed`: `cultural-and-historic-resources`, `historic-structures-and-districts`.
- `manual_review_needed`: community, utility, regulated facility, hazmat, oil-well sections.

Root cause: `_eligibility_skip_reason()` in `gpt_interpretive_assist.py` checks manual policy, body eligibility, GPT policy flags, stubs, presentation-only extent, and whether the item has at least one non-imagery source ref. It does not check `manual_material.material_status`, `section_source_needs.section_need_status`, or source need classes.

Risk: an explicit GPT run could draft from partial public/coarse/manual context sections. Review gate and validation still apply, but this is weaker than the stated Sprint 5 policy that manual/restricted/missing-source items should remain GPT-ineligible.

Smallest fix path:

- Load `section_source_needs` into GPT planning, or propagate section need status onto deliverable/review items.
- Skip GPT when section status is `manual_review_needed`, `restricted_review_needed`, `deferred_source`, `source_action_needed`, or when source need classes include manual/restricted/deferred/acquisition action classes, unless a future explicitly approved policy says otherwise.
- Add tests in `tests/test_gpt_interpretive_assist.py` and `tests/test_evidence_and_gpt.py`.

## M. Manual / Reviewer-Supplied Workflow Findings

Manual/reviewer-supplied cases are represented as metadata, not failed downloads:

- PEL relationship: `manual_text`, `manual_required`, review/status only.
- Protected species: `manual_text`, `manual_required`.
- Archaeological sites: `manual_text`, `manual_required`, restricted/public split preserved.
- Attachments B/C: `supporting_document`, `manual_required`.
- Optional parcel/property: `optional`, non-alarming source status.

Reviewed export simulation skipped 9 body-ineligible/manual/status items with policy reasons and still produced reviewed Markdown/DOCX with no blocking QA errors.

No generalized document upload exists; deferred work records that explicitly.

## N. UI / Export Findings

UI architecture:

- Routes remain thin and call `web.adapter`.
- Adapter owns summaries, review detail shaping, reset, GPT action, and export calls.
- No GIS/report/GPT logic was found in templates/routes.
- Web tests passed.
- UI was not live-verified from a running server in this audit; artifact regeneration used CLI to avoid stale server memory.

Export:

- Internal preview export: `package_status: internal_preview`, `review_gate_status: preview_bypassed`, `export_qa_status: failed`, `export_qa_blocking_error_count: 3`. This is expected because preview includes manual placeholders.
- Final verification for preview passed.
- Disposable reviewed-export simulation: `package_status: reviewed_content`, `review_gate_status: passed`, `export_qa_status: warning`, `export_qa_blocking_error_count: 0`, `final_verification_status: passed`, Markdown/DOCX/manifest existed, 61 included, 9 skipped.

## O. Docs Findings

Docs checked:

- `README.md`
- `AGENTS.md`
- `docs/core/CURRENT_STATE.md`
- `docs/domains/REPORT_POLICY.md`
- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/domains/DATA_SOURCES.md`
- `docs/domains/SOURCE_WAREHOUSE.md`
- `docs/domains/MAP_GENERATION.md`
- `docs/domains/LLM_ASSISTED_SYNTHESIS.md`
- `docs/governance/DEFERRED_WORK.md`

Docs correctly state:

- Review Assist is feature-neutral and `projects/trails` is a sample fixture.
- Human review remains required.
- GPT is opt-in, cached, policy-bound, and review-gated.
- Effective source status supersedes stale acquisition history for report-facing caveats.
- Render/collar extents are presentation-only.
- Manual/reviewer-supplied and restricted materials remain review states.
- Broader document management, source acquisition, reviewer override, source warehouse cleanup, context-query expansion, and cartography remain deferred.

No `.cursorrules` file was found.

Doc risk: docs claim GPT skips manual/restricted/missing-source items. The policy intent is documented correctly; the runtime eligibility P1 needs to catch up.

## P. Regeneration Result

Commands run:

```powershell
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --no-gpt-drafting
.\.venv\Scripts\review-assist.exe draft-section-candidates projects/trails --dry-run --json
.\.venv\Scripts\review-assist.exe export-report projects/trails --include-draft --format both
.\.venv\Scripts\review-assist.exe reset-review-queue projects/trails --dry-run --json
```

Regeneration result:

- Review queue items: 70.
- GPT drafting during populate: false.
- Populate warnings: 51, primarily known generated warning propagation plus GeoPandas county-column warnings.
- Tables: 4.
- Figures: 15 main, 14 rendered, 1 stubbed.
- Evidence constraints: 2547.
- Export preview: 70 included, 0 skipped, expected QA-failed preview state.

Server restart needed: no. UI behavior was not verified from a running server.

Generated artifacts intentionally uncommitted:

- Ignored `projects/trails` generated artifact directories.
- Disposable temp reviewed-export workspace outputs; temp workspace was removed.

## Q. Tests Run And Results

Always-run checks:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
git diff --check
.\.venv\Scripts\review-assist.exe validate-deliverable-matrix
.\.venv\Scripts\review-assist.exe validate-report-prompts --json
```

All passed.

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_report_section_policy.py tests/test_source_warehouse.py tests/test_source_materialization.py tests/test_source_inventory_and_tables.py tests/test_source_acquisition.py tests/test_deliverable_tables.py tests/test_deliverable_figures.py tests/test_evidence_and_gpt.py tests/test_deliverable_items.py tests/test_review_queue.py tests/test_gpt_interpretive_assist.py tests/test_export_report.py tests/test_deliverable_compactness.py tests/test_web_app.py tests/test_workflow_artifacts.py
```

Result: 332 passed, 2 pyogrio warnings.

Full suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result: 491 passed, 7 known GeoPandas/pyogrio warnings.

## R. P0 / P1 / P2 Issues

P0: none found.

P1:

1. GPT Interpretive Assist eligibility includes manual/restricted/manual-review-needed source contexts.
2. `section_source_needs` section status can conflict with policy activation for `deferred_source` sections.

P2:

1. Stale acquisition/download ignored warnings are repeated into downstream validation arrays and preview manifests.
2. Deterministic status/source-selection wording is truthful but verbose and sometimes duplicated in preview body content.
3. Full polished report prose is not yet the right expectation for internal preview output; reviewed export skips body-ineligible placeholders correctly.

## S. Files To Commit

None until this audit and cleanup plan are reviewed.

Candidate file after review:

- `docs/sprints/SPRINT_5_POST_IMPLEMENTATION_STABILIZATION_AUDIT.md`

## T. Files To Restore / Omit

Omit:

- `scratch_DO_NOT_DELETE.txt`
- ignored `projects/trails` generated artifacts
- ignored `projects/conexon_projects` generated artifacts
- ignored `sources/` raw/warehouse data
- ignored local logs and caches

No tracked files currently need restore.

## U. Human-Decision Files

- `docs/sprints/SPRINT_5_POST_IMPLEMENTATION_STABILIZATION_AUDIT.md`: decide whether to keep/commit this audit report.
- P1 cleanup scope: decide whether to fix GPT eligibility and source-needs label consistency immediately before Sprint 6/Sprint 7 work.

## V. Recommended Commit Grouping

No commit yet.

If approved:

1. `Stabilize Sprint 5 GPT source-need eligibility`
   - Tighten GPT eligibility against manual/restricted/deferred/source-action-needed section source statuses.
   - Add focused tests.
2. `Stabilize Sprint 5 source-needs section status`
   - Align `section_source_needs.section_need_status` with `deferred_source` activation.
   - Add focused tests.
3. `Document Sprint 5 stabilization audit`
   - Commit this report after cleanup results are added or explicitly accepted as-is.

## W. Recommendation

Ready for planning discussion only. Not ready for new Sprint 6/Sprint 7 implementation until the P1 cleanup path is accepted or explicitly deferred.

The current baseline is stable enough for review and planning: tests pass, regeneration works, and reviewed export hard-block behavior is intact. The smallest safe next step is a narrow stabilization cleanup for GPT eligibility and source-needs status semantics, not new product scope.
