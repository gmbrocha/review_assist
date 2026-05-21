# Sprint 5.7: Manual / Reviewer-Supplied Policy MVP

## Status

Active next implementation target after completed Sprint 5.6 table/figure policy alignment.

## Goal

Represent manual, restricted, optional, and reviewer-supplied report materials as first-class review states without building a broad document-management system.

This subunit should turn source gaps into clear reviewer actions while preserving provenance and export gates.

This subunit must consume the manual/reviewer-supplied, restricted material, attachment support, and parent-study/PEL context rows from `SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md`.

## Scope

The first implementation should be narrow. Prefer policy/status/review-gate support over large UI expansion.

This subunit may update:

- report/source policy for manual completion
- source status categories
- review queue item metadata/status handling
- existing review detail surfaces where small changes are needed
- export behavior for accepted manual/reviewer-supplied content
- focused file-safety tests only when uploads are touched

## Manual Material Types

Represent, as policy/review metadata where needed:

- `manual_text`
- `replacement_figure`
- `edited_caption`
- `manual_table`
- `supporting_document`
- `reviewer_note`

The current figure caption/replacement flow already exists. Do not rebuild it unless a clear stabilization bug is found.

## Required Source Status Distinctions

- `source_backed_generated`
- `manual_required`
- `reviewer_supplied`
- `restricted_reviewer_supplied_required`
- `optional_absent`
- `not_used`
- `unable_to_verify`
- `deferred_source`

Manual/restricted sources should not appear as failed downloads.

## Key Use Cases

- Restricted/reviewer-supplied cultural records.
- Public/coarse cultural context that does not substitute for authorized records.
- Agency consultation letters.
- Hazardous materials support report.
- Optional parcel/property context.
- Project-specific parent-study/PEL context when supplied by reviewer.

## Non-Goals

- No production authentication or permissions.
- No permanent document management system.
- No OCR.
- No automatic interpretation of restricted cultural records.
- No live MDAH/SHPO access.
- No broad source acquisition.
- No full attachment package redesign.
- No PDF export.

## Acceptance Criteria

- All manual/reviewer-supplied ledger rows are adopted, rejected, or deferred with explicit rationale.
- Manual-required items remain incomplete until a reviewer chooses a terminal status allowed by policy.
- Reviewer-supplied material carries provenance and review status.
- Reviewer notes remain internal unless policy explicitly says otherwise.
- Declined/not-provided/unable-to-verify manual items do not export as source-backed findings.
- Accepted manual material exports only according to item type and policy.
- Restricted/public/manual distinctions remain visible.

## Required Tests

- Manual-required item appears with correct status.
- Restricted/reviewer-supplied cultural item is not a failed download.
- Optional parcel absence is non-alarming.
- Figure caption/replacement export behavior remains intact.
- Unsafe filenames/path traversal are rejected if new uploads are touched.
- Manual material remains review-gated.
- Reviewer notes do not export as report content unless explicitly intended.
- Review queue target IDs remain stable.

## Documentation Updates

- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/domains/DATA_SOURCES.md`
- `docs/domains/SOURCE_WAREHOUSE.md`
- `docs/domains/UNCERTAINTY_AND_PROVENANCE.md`
- `docs/governance/DEFERRED_WORK.md` for deferred broad manual workflow pieces
