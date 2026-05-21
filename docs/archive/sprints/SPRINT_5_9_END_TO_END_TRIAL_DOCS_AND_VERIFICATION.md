# Sprint 5.9: End-To-End Trial, Docs, And Verification

## Status

Completed on branch `sprint-5`.

## Goal

Run the full policy-aware report workflow on sample fixtures and inspect the actual reviewer/export behavior.

This is a verification and cleanup subunit, not a feature-expansion subunit.

This subunit must verify that `SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md` has no unresolved adopted/routed rows. Any remaining package differences must be rejected, documented as already covered, or deferred into permanent deferred-work records before Sprint 5 is closed.

## Trial Results

- `projects/trails` was regenerated with `populate-for-review --no-gpt-drafting`.
- GPT verification was dry-run only; no live GPT drafting was invoked.
- Internal preview export completed with expected preview-bypass QA metadata.
- A disposable temp copy of `projects/trails` was populated, review items were marked accepted/export-eligible in that temp workspace only, and default reviewed export produced Markdown/DOCX with `review_gate_status: passed`, `final_verification.status: passed`, and `export_qa_blocking_error_count: 0`.
- The trial found and fixed one narrow final-verification false positive for attachment section items that use matrix `attachment_refs` instead of direct `attachment_id`.
- Generated sample artifacts remain ignored and uncommitted.

## Trial Workflow

- Confirm clean worktree and accepted checkpoint.
- Clean/reset generated review artifacts only when appropriate for local testing.
- Materialize current local sources where the sample trial requires it.
- Populate deterministic artifacts.
- Generate tables, figures, evidence, deliverable items, and review queue.
- Run GPT eligibility dry run; invoke GPT only if explicitly approved for the trial.
- Manually review a bounded subset where needed.
- Export Markdown/DOCX preview or reviewed package as appropriate.
- Inspect report shape, evidence traceability, QA status, and reviewer decision stack.

## Review Questions

- Is the package reconciliation ledger closed, with durable decisions migrated into policy/docs/deferred work?
- Is the report compact?
- Is evidence traceable?
- Are extent semantics visible and honest?
- Do source-backed, manual, missing, deferred, and restricted statuses remain distinct?
- Does export include only reviewed or explicitly allowed content?
- Does GPT remain optional, bounded, and review-gated?
- Are table/figure refs accurate and policy-allowed?
- Are current product gaps documented?

## Guardrails

- Use `projects/trails` and other sample projects as fixtures only.
- Do not hardcode fixture-specific behavior.
- Do not treat optional GPT drafting as normal populate/reset behavior.
- Do not commit generated sample-project artifacts unless explicitly approved.
- Do not begin Sprint 6 figure-editing work.

## Acceptance Criteria

- Package ledger dispositions are closed or intentionally deferred, and permanent docs reflect adopted behavior.
- Focused tests for all Sprint 5 changes pass.
- Full test suite or `scripts/verify.ps1 -SkipInstall` passes, or any inability is documented with risk.
- Final docs reflect implemented behavior and deferred issues.
- Generated artifacts affected by behavior changes are regenerated only as needed and left uncommitted unless explicitly approved.
- Sprint 5 completion state and next-step risks are clear.

## Commands Run

```powershell
.\.venv\Scripts\review-assist.exe validate-deliverable-matrix
.\.venv\Scripts\review-assist.exe validate-report-prompts --json
.\.venv\Scripts\review-assist.exe reset-review-queue projects/trails --dry-run --json
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --no-gpt-drafting
.\.venv\Scripts\review-assist.exe draft-section-candidates projects/trails --dry-run --json
.\.venv\Scripts\review-assist.exe export-report projects/trails --include-draft --format both
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

All commands passed. Full pytest passed with 491 tests and known GeoPandas/pyogrio sample-data warnings. `scripts/verify.ps1 -SkipInstall` was not run because Sprint 5.9 used the user-approved targeted validator, regeneration, export, and full-pytest verification path instead.

## Closeout

- Generated artifacts affected: yes.
- Minimum affected chain: source status -> tables/figures -> evidence package -> deliverable items -> review queue -> export manifests and Markdown/DOCX outputs.
- Server restart needed: no.
- Regeneration commands run: `populate-for-review projects/trails --no-gpt-drafting`, `draft-section-candidates projects/trails --dry-run --json`, and `export-report projects/trails --include-draft --format both`.
- Canonical artifacts verified: source status, deliverable tables, deliverable figures, evidence package, deliverable items, review queue, and export manifest under `projects/trails`.
- UI verified from current server: not applicable.
- Generated artifacts intentionally uncommitted: ignored `projects/trails` generated artifact directories and disposable temp reviewed-export workspace outputs.
- Focused tests run: export-report regression tests plus matrix/prompt validators and Sprint 5.9 workflow commands.
- Full suite run: yes, 491 passed.
- Remaining stale-artifact risk: none expected; the reviewed-export simulation used a disposable temp copy and the sample project artifacts remain ignored.
