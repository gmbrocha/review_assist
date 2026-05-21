# Sprint 7.5: Real Project End-To-End Smoke Test

## Status

Parked draft for review. Do not implement until Sprint 7.4 intake trial is complete and the new project is successfully created in the app.

## Purpose

Run the full app workflow on the new project from Sprint 7.4 and produce a concrete testing log of what works, what confuses, and what breaks.

This subunit validates the full pipeline end to end on a real project, not just the intake step.

## Steps

Run each step in sequence and record results:

1. Create project (carry forward from Sprint 7.4 if already created).
2. Upload or import the source project file.
3. Run populate and materialization.
4. Generate the review queue.
5. Inspect figures — do they render, are they readable, do they cover the right area.
6. Inspect tables — are values present, are source limitations shown, are empty sections explained.
7. Inspect source-backed sections — is provenance visible, are caveats preserved.
8. Inspect manual and reviewer-supplied stubs — are gaps clearly surfaced, is guidance provided.
9. Optionally run GPT on one or two safe non-sensitive sections and inspect output quality.
10. Review and accept a small subset of items.
11. Generate an export preview or reviewed package.

## What To Record Per Step

For each step record:

- Did it succeed, fail, or require a workaround?
- What did the UI show?
- Was the output believable and reviewer-appropriate?
- What was confusing or trust-reducing?
- What was outright broken?

## Output

A concrete testing log with pass/fail/confusing/broken annotation for each step.

This log feeds directly into Sprint 7.7 (Reviewer Friction Backlog).

## Tests

No new automated tests are required for this subunit. This is a manual smoke test.

If regressions or clear bugs are found and patched during this subunit, add focused regression tests before closing.

## Definition Of Done

- All eleven steps have been attempted on the new real project.
- A testing log exists with per-step pass/fail/confusing/broken annotations.
- Any blocking issues found are recorded with file and line location and flagged for Sprint 7.7 P0 triage.
- `projects/trails` remains functional after any patches applied during this subunit.
