# Sprint 5.8: Export QA And Override Policy

## Status

Parked for implementation after Sprint 5.1 through Sprint 5.7 are accepted.

## Goal

Add policy-aware export QA after the required metadata exists.

The current export path already has review gating, compactness budget checks, DOCX readability checks, and final verification summaries. This subunit should extend that baseline instead of replacing it.

## Scope

This subunit may update:

- `src/review_assist/export_report.py`
- web export readiness display
- export/package manifest fields
- export tests and documentation

## QA Checks To Consider

- unresolved required review comments/statuses
- blank required table cells
- inconsistent figure/table numbering
- captions that do not match policy or missing required source/method notes
- missing source references for rendered source-backed sections
- sections rendered without required caveats
- sections citing disallowed table/figure/source refs
- export content that exceeds compactness/no-raw-dump rules
- manual/reviewer-supplied material exported without accepted review status

## Human Decision Required

Decide whether final export QA should:

- hard-block default reviewed export, or
- allow reviewer override with a required reason.

Preview exports may remain an internal bypass if clearly marked.

## Non-Goals

- No production approval workflow.
- No multi-user signoff.
- No PDF export.
- No new report standard.
- No bypass of the review-complete gate.

## Acceptance Criteria

- Export manifest records QA status, issue counts, and issue details.
- Default reviewed export follows the approved block/override policy.
- Preview export remains clearly marked as internal/pre-review.
- QA failures are specific enough for a reviewer/developer to fix.
- Existing compactness and DOCX verification remain intact.

## Required Tests

- Blank required table cell is flagged.
- Missing caption/source/method metadata is flagged where policy requires it.
- Missing required caveat is flagged.
- Disallowed table/figure/source ref is flagged.
- Manual material without accepted review status is blocked or flagged.
- Reviewer override requires a reason if override behavior is approved.
- Preview bypass remains marked as preview.

## Documentation Updates

- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/domains/REVIEW_POLICY.md` if review/override behavior changes
- `docs/core/CURRENT_STATE.md` after implementation
- `docs/governance/DEFERRED_WORK.md` for QA items deferred out of this subunit
