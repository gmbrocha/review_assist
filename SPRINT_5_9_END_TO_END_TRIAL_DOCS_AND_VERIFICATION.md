# Sprint 5.9: End-To-End Trial, Docs, And Verification

## Status

Parked for implementation after Sprint 5.1 through Sprint 5.8 are accepted enough to trial together.

## Goal

Run the full policy-aware report workflow on sample fixtures and inspect the actual reviewer/export behavior.

This is a verification and cleanup subunit, not a feature-expansion subunit.

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

- Focused tests for all Sprint 5 changes pass.
- Full test suite or `scripts/verify.ps1 -SkipInstall` passes, or any inability is documented with risk.
- Final docs reflect implemented behavior and deferred issues.
- Generated artifacts affected by behavior changes are regenerated only as needed and left uncommitted unless explicitly approved.
- Sprint 5 completion state and next-step risks are clear.

## Commands To Consider

```powershell
.\.venv\Scripts\review-assist.exe validate-deliverable-matrix
.\.venv\Scripts\review-assist.exe validate-report-prompts --json
.\.venv\Scripts\review-assist.exe reset-review-queue projects/trails --dry-run --json
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --no-gpt-drafting
.\.venv\Scripts\review-assist.exe draft-section-candidates projects/trails --dry-run --json
.\.venv\Scripts\review-assist.exe export-report projects/trails --include-draft --format both
.\.venv\Scripts\python.exe -m pytest
.\scripts\verify.ps1 -SkipInstall
```

## Closeout Requirements

Report:

- generated artifacts affected: yes/no
- minimum affected chain
- server restart needed: yes/no
- regeneration commands run
- canonical artifacts verified
- UI verified from current server: yes/no/not applicable
- generated artifacts intentionally uncommitted
- focused tests run
- full suite run
- remaining stale-artifact risk
