# Sprint 7.5: Real Project End-To-End Smoke Test

## Status

Complete.

Implemented as a safe real-project smoke pass continuing from `projects/test_project_2`. Generated project/export artifacts remain local/uncommitted.

## Purpose

Run the full app workflow on the new project from Sprint 7.4 and produce a concrete testing log of what works, what confuses, and what breaks.

This subunit validates the full pipeline end to end on a real project, not just the intake step.

## Steps

Run each step in sequence and record results:

1. Create project (carry forward from Sprint 7.4 if already created).
2. Upload or import the source project file.
3. Run populate and materialization.
4. Generate the review queue.
5. Inspect figures - do they render, are they readable, do they cover the right area.
6. Inspect tables - are values present, are source limitations shown, are empty sections explained.
7. Inspect source-backed sections - is provenance visible, are caveats preserved.
8. Inspect manual and reviewer-supplied stubs - are gaps clearly surfaced, is guidance provided.
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

## Smoke Test Log

- Environment: repo-local `.venv` verified at `F:\Desktop\review_assist\.venv\Scripts\python.exe`.
- Workspace: `projects/test_project_2`, kept untracked and not committed.
- Step 1, create/select project: passed by selecting the existing fresh trial workspace through the web route.
- Step 2, upload/import source file: passed by verifying committed input `inputs/Routes_20260202.kmz`; no new upload was needed during this pass.
- Step 3, populate and materialization: passed through `POST /overview/populate`; source materialization preserved existing local project layers and populate completed.
- Step 4, generate review queue: passed; standard queue rendered in the web UI with 69 review items.
- Step 5, inspect figures: passed at workflow level; figure detail and figure style editor rendered. Fourteen exportable figure assets were copied during preview export; `figure-census-tracts` remains a placeholder without an image and is correctly surfaced as a warning.
- Step 6, inspect tables: passed; four deliverable table targets exist. Census demographic tables currently have zero rows because Census/TIGER/ACS source setup remains deferred/stubbed.
- Step 7, inspect source-backed sections: passed; review detail rendered full content and source/provenance remains available through advanced/debug mode.
- Step 8, inspect manual and reviewer-supplied stubs: passed; manual/restricted placeholders surfaced in export QA as blocking issues requiring reviewer-supplied content.
- Step 9, GPT spot check: skipped intentionally; no GPT/API calls were made during this smoke pass.
- Step 10, review and accept subset: passed; one non-figure item and one figure item were accepted through web review actions.
- Step 11, export preview/reviewed package: preview export passed and produced Markdown/DOCX/package artifacts. Reviewed export remains correctly blocked because most review items are unreviewed and three manual/restricted body items lack reviewer-supplied content.

## Findings

- Expected gate behavior: export readiness remains blocked after accepting only a small subset of items.
- Expected QA behavior: internal preview export records `export_qa_status: failed` due to manual-material blockers and the census placeholder figure, while still producing preview outputs.
- Reviewer-friction candidate for Sprint 7.7: repeated informational source-materialization warnings are noisy and should be grouped or summarized in reviewer-facing logs.
- Reviewer-friction candidate for Sprint 7.7: census demographic table/figure placeholders are understandable but prominent; future UI copy could better distinguish deferred source setup from broken generation.
- No small code regression was found that justified a patch in this subunit.

## Tests

No new automated tests are required for this subunit. This is a manual smoke test.

If regressions or clear bugs are found and patched during this subunit, add focused regression tests before closing.

## Definition Of Done

- All eleven steps were attempted on the real-ish trial project.
- A testing log exists with per-step pass/fail/confusing/broken annotations.
- No P0 blocking implementation issue was found; friction items are recorded for Sprint 7.7 triage.
- No product code changes were made, so `projects/trails` behavior was not altered by this subunit.
