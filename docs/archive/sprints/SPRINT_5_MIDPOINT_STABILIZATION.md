# Sprint 5 Midpoint Stabilization

## Summary

Midpoint stabilization reviewed Sprint 5.0 through Sprint 5.6 on branch `sprint-5` against the pre-Sprint-5 baseline `origin/main` at `6b15fb4`.

The pass focused on already-landed Sprint 5 behavior: canonical report policy, source-needs/effective-truth records, extent semantics, render gating, GPT caveat/prohibited-claim guardrails, table/figure policy alignment, review queue metadata, web review display, and export selection. It did not implement Sprint 5.7, Sprint 5.8, or Sprint 5.9 work.

One small policy validation gap was fixed. No generated project artifacts or source warehouse artifacts were committed or intentionally changed.

## Current Diff Reviewed

Baseline reviewed:

- `origin/main..HEAD`
- Current branch status before stabilization: clean except untracked `scratch_DO_NOT_DELETE.txt`.

Changed areas reviewed:

- Policy/config:
  - `config/report_section_policy.json`
  - `config/report_generation_prompts.json`
  - `config/report_style_context/environmental_constraints_report_style.md`
- Policy and extent runtime:
  - `src/review_assist/report_section_policy.py`
  - `src/review_assist/extent_policy.py`
- Source truth/runtime metadata:
  - `src/review_assist/source_status.py`
  - `src/review_assist/source_inventory.py`
- Deliverable artifacts and review:
  - `src/review_assist/deliverable_items.py`
  - `src/review_assist/deliverable_tables.py`
  - `src/review_assist/deliverable_figures.py`
  - `src/review_assist/deliverable_figure_contract.py`
  - `src/review_assist/evidence_package.py`
  - `src/review_assist/review_queue.py`
- GPT/review assist:
  - `src/review_assist/section_drafting.py`
  - `src/review_assist/gpt_interpretive_assist.py`
- Export and UI surfaces:
  - `src/review_assist/export_report.py`
  - `src/review_assist/web/adapter.py`
  - `src/review_assist/web/templates/review.html`
  - `src/review_assist/web/templates/review_detail.html`
- Tests:
  - `tests/test_report_section_policy.py`
  - `tests/test_deliverable_items.py`
  - `tests/test_deliverable_tables.py`
  - `tests/test_deliverable_figures.py`
  - `tests/test_review_queue.py`
  - `tests/test_export_report.py`
  - `tests/test_evidence_and_gpt.py`
  - `tests/test_gpt_interpretive_assist.py`
  - `tests/test_source_inventory_and_tables.py`
  - `tests/test_workflow_artifacts.py`
- Docs and sprint routing:
  - Sprint 5 root docs, ledger, archive indexes, current state, affected domain docs, and deferred work.

Generated/source artifact check:

- `git diff --name-status origin/main..HEAD -- projects sources` returned no tracked project or source artifact changes.
- Current working tree has only the stabilization code/test/report changes plus untracked `scratch_DO_NOT_DELETE.txt`.

## Bugs Fixed

- Fixed figure policy matrix validation. Table policies already verified that each matrix table target's `source_categories` were allowed by its matching table policy. Figure policies only checked unknown policy categories, so a figure policy could accidentally omit a matrix figure target source category without failing validation. `ReportSectionPolicyConfig.validate_against_matrix()` now validates matrix figure source categories against the matching figure policy.

## Tests Added Or Updated

- Added `test_figure_policy_matrix_coverage_and_categories_are_validated()` in `tests/test_report_section_policy.py`.
- The new test covers missing figure policy targets, unknown figure policy IDs, and figure policy source-category mismatch/unknown-category validation.

## Behavior Verified

- Policy/config integrity:
  - Report policy loads and validates against the deliverable matrix.
  - Section, table, and figure policy counts match the matrix: 44 sections, 4 tables, 15 figures.
  - Section activation fields reject unsupported enum values.
  - Unknown source refs/categories, table refs, figure refs, and required caveat IDs are rejected.
  - Manual/reviewer-supplied sections remain non-GPT by default.
  - PEL relationship policy remains conditional, reviewer-supplied, manual review, and non-GPT.
  - Table policies now have exact matrix coverage, compact preview caps, known source categories, and artifact overflow.
  - Figure policies now have exact matrix coverage, known source categories, and enforced matrix category allowance.
- Extent semantics:
  - Direct, context, watershed, county/regional, render, and presentation/collar extent metadata remain distinct.
  - Context-only wording and GPT validation reject direct project/intersection language.
  - APE language remains blocked unless reviewer-defined cultural/manual context is present.
  - Render/collar extent remains presentation-only and does not drive evidence counts or interpretation.
- Section rendering:
  - Render-policy metadata keeps body, table/figure-only, manual, deferred, restricted, missing-source, and attachment/status behavior explicit.
  - Body-ineligible generated placeholders do not export as normal reviewed body content unless reviewer-supplied exportable content exists.
  - Wetlands/waterbodies narrative children remain preserved.
- GPT guardrails:
  - GPT Interpretive Assist remains opt-in and filters to policy-approved, source-backed, report-body-eligible `section_text` items.
  - Manual/reviewer-supplied, missing-source, stub, body-ineligible, and non-section items are skipped.
  - Required caveat omissions and known prohibited claim families are rejected with deterministic fallback preserved.
  - Style context remains fact-free/non-evidence and cannot be cited as project evidence.
- Table/figure behavior:
  - Matrix counts remain stable: 4 tables, 15 figures, 3 attachments.
  - Table and figure artifacts propagate policy metadata into evidence, deliverable items, review queue/export summaries.
  - Table body previews remain bounded by policy cap; full rows stay in artifacts.
  - Missing/incomplete tables or figures remain stubs/review-visible limitations.
- Export/report behavior:
  - Review-complete export gate remains active for default export.
  - Draft export remains an internal/pre-review bypass.
  - Render-policy skipped reasons are retained for body-ineligible items.

## Implementation Vs Planned Behavior

Implemented now:

- Canonical policy remains `config/report_section_policy.json`.
- Section activation/review fields are parsed, validated, and propagated into source-needs, deliverable items, review queue items, web review metadata, and export metadata.
- Source-needs classes are recorded in `source_status/source_status_set.json`.
- Extent metadata and wording guardrails distinguish interpretation scope from presentation-only map/render scope.
- GPT guardrails enforce required caveat IDs, prohibited claim families, style-context non-evidence, source/table/figure citation bounds, context-only wording, APE restrictions, and deterministic fallback.
- Table policies and figure policies cover current matrix targets exactly and validate source-category alignment.

Not fully implemented yet:

- Sprint 5.7 manual/reviewer-supplied workflows are not complete. Current behavior keeps manual/restricted/deferred items visible and gated, but broader manual material types, restricted-source handling, and reviewer-supplied export workflows remain next-subunit work.
- Sprint 5.8 export QA is not complete. Required caveat checks, blank required table-cell checks, numbering consistency checks, final QA issue manifests, and reviewer override-with-reason policy remain planned for Sprint 5.8.
- Named nearby/community/watershed/county context extents are policy labels and wording guards, not new source-query implementations.
- New package-proposed table/figure counts, extra source acquisitions, live Census/TIGER/ACS acquisition, water-quality/TMDL acquisition, and broader public water supply/business-node acquisition remain deferred or require explicit approval.
- Legacy `generate-report-sections` remains a compatibility/audit path. The standard Sprint 5 policy-gated path is deliverable items -> standard review queue -> export. Future cleanup should keep this distinction visible so legacy draft sections are not mistaken for fully policy-gated reviewed report content.

## Deferred Issues

- Manual/reviewer-supplied material workflow:
  - Why deferred: It is explicitly Sprint 5.7 scope.
  - Blocks finishing Sprint 5: No, but it should be addressed before export QA finalization.
  - Follow-up: Implement narrow manual material state and reviewer-supplied content handling in Sprint 5.7.
- Export QA and override policy:
  - Why deferred: It depends on metadata now implemented through Sprint 5.6 and is explicitly Sprint 5.8 scope.
  - Blocks finishing Sprint 5: Yes for final Sprint 5 closure, not for continuing to 5.7.
  - Follow-up: Add policy-aware export QA with clear block/override behavior and tests in Sprint 5.8.
- Named context query implementation:
  - Why deferred: Sprint 5.2 intentionally added labels and wording protections without new spatial queries.
  - Blocks finishing Sprint 5: No, if docs keep the policy-label versus implemented-query distinction clear.
  - Follow-up: Future methodology/source-query hardening should implement separate context queries where approved.
- Source acquisition expansion:
  - Why deferred: Sprint 5 midpoint changes must not add new downloads or credentials.
  - Blocks finishing Sprint 5: No, if stubs/source-needs remain visible.
  - Follow-up: Future source acquisition hardening for Census, public water supply, water quality, parcels/property, and business nodes.
- Legacy report section draft path:
  - Why deferred: It is compatibility/audit behavior outside the standard matrix-backed review/export path.
  - Blocks finishing Sprint 5: No, but it is a fragile area for operator confusion.
  - Follow-up: Keep docs explicit; consider a later cleanup that marks legacy draft sections as audit-only or routes them through the same policy metadata if they remain user-facing.

## Risk Assessment

Current Sprint 5 foundation is usable but still policy-heavy. Fragile areas before continuing:

- `config/report_section_policy.json` is now large and central. Future edits should continue using validator-backed tests rather than manual inspection.
- GPT eligibility depends on multiple gates: policy readiness, report-body eligibility, source-backed status, stub status, and citation/caveat validation. Small changes should include focused skip-reason tests.
- Export QA is intentionally incomplete until Sprint 5.8. Do not treat current reviewed export as final QA-complete.
- Manual/restricted/reviewer-supplied handling is intentionally partial until Sprint 5.7. Do not let manual placeholders become normal body prose.
- Context extents remain labels and wording guards until future query implementation. Do not infer broader source queries from metadata alone.

## Commands Run

- `git status --short --branch` - passed; branch clean except untracked `scratch_DO_NOT_DELETE.txt` before stabilization.
- `git log --oneline --decorate -n 20` - passed; confirmed Sprint 5.0 through Sprint 5.6 commits.
- `git diff --stat origin/main..HEAD` - passed; reviewed Sprint 5 changed surface.
- `git diff --name-status origin/main..HEAD` - passed; reviewed changed files and archived sprint-doc moves.
- `git diff --dirstat=files,0 origin/main..HEAD` - passed; reviewed changed area distribution.
- `git diff --numstat origin/main..HEAD` - passed.
- `git diff --name-status origin/main..HEAD -- projects sources` - passed; no tracked generated/source artifact changes.
- Policy inspection script via `.\.venv\Scripts\python.exe` - passed; confirmed 44 sections, 4 tables, 15 figures, 6 manual sections, 17 policy-level GPT-eligible sections, and 5 deferred/stub sections.
- `.\.venv\Scripts\python.exe -m pytest tests/test_report_section_policy.py tests/test_deliverable_items.py tests/test_review_queue.py tests/test_evidence_and_gpt.py tests/test_export_report.py tests/test_workflow_artifacts.py tests/test_source_inventory_and_tables.py tests/test_deliverable_tables.py tests/test_deliverable_figures.py` - passed, 203 tests.
- `.\.venv\Scripts\review-assist.exe validate-deliverable-matrix` - passed; 44 sections, 4 tables, 15 figures, 3 attachments, 45 prompts.
- `.\.venv\Scripts\review-assist.exe validate-report-prompts --json` - passed.
- `.\.venv\Scripts\python.exe -m pytest` - passed, 483 tests.

## Continue Sprint 5?

CONTINUE WITH CAUTION

The current Sprint 5 foundation is stable enough to continue to Sprint 5.7. The caution is targeted: complete manual/reviewer-supplied handling and export QA in their planned subunits, keep legacy draft sections distinct from the standard policy-gated path, and do not treat context labels as implemented context queries.
