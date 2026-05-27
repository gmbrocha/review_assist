# Sprint 7.4: Fresh Project Intake Trial

## Status

Complete.

Implemented as a safe trial/stabilization pass using the local `projects/test_project_2` workspace as the real-ish project input. Generated project artifacts remain local/uncommitted.

## Purpose

Validate that Review Assist is truly project-general and not accidentally tuned to the `projects/trails` fixture.

Stop validating only against `projects/trails`. Use a new real-ish project from Monica to expose any fixture-specific assumptions baked into the workflow.

## Input Needed

Ask Monica for an old site or project KMZ with actual features, preferably something safe to use for private POC testing.

The project file should have real geometry and ideally real feature context (site boundary, study area, or route corridor), but does not need to be a current active project.

For this pass, Monica approved using existing local workspace `projects/test_project_2`, which contains `inputs/Routes_20260202.kmz`.

## Workflow

Run the following steps in sequence on the new project:

1. Create a brand-new project through the app.
2. Upload or import the KMZ.
3. Classify inputs.
4. Materialize sources.
5. Generate project area and comparison units.
6. Generate tables, figures, and evidence.
7. Generate the review queue.
8. Inspect what breaks, what is missing, and what is confusing.

## What To Look For

During intake, note:

- Any hardcoded paths, IDs, or names that reference `trails`
- Any geometry processing assumptions that fail on the new project's shape or CRS
- Any source materialization that errors on a project with different feature types
- Any template or label that reads oddly for a non-trail project
- Any review queue items that are nonsensical for this project type
- Any figure or table that errors or produces an empty output

## Output

Produce a short intake log documenting:

- Which steps succeeded cleanly
- Which steps required workarounds
- Which steps failed
- Any hardcoded fixture assumptions found and their file locations

This log feeds directly into Sprint 7.7 (Reviewer Friction Backlog).

## Intake Log

- Environment: repo-local `.venv` verified at `F:\Desktop\review_assist\.venv\Scripts\python.exe`.
- Workspace: `projects/test_project_2`, kept untracked and not committed.
- Project selection: passed through the Flask web route with status 200.
- Setup page: passed; manifest exists, one committed input, zero staged inputs, zero setup blockers.
- Input classification: passed through `POST /setup/classify`; `context/input_package.json` reports one project geometry input and no validation issues.
- Materialization/populate/review queue generation: passed through `POST /overview/populate`; populate completed with 69 review items.
- Project area: passed; project area available, counties detected as Tippah County and Union County, basemap status `renderable_sidecar_available`.
- Comparison units: passed; five comparison units generated with `expected_count_status: not_configured`.
- Tables/figures/evidence/review queue: passed; four deliverable tables and 15 deliverable figures were generated or stubbed as expected, and the standard review queue rendered in the web UI.
- Hardcoded fixture assumptions: no active code hardcoding to `projects/trails` was found during this trial. Remaining `trails` references are in tests, archived docs, domain examples, or generic prohibited-claim wording.
- Workarounds: none required for intake. Existing local materialized source layers were preserved instead of overwritten, producing expected informational warnings.
- Confusing or follow-up items for Sprint 7.7: the 68 populate warnings are mostly repeated `existing_local_source_preserved` informational messages and may be too noisy for a reviewer-facing process log.

## Tests

No automated tests are required for this subunit. This is an exploratory trial, not a product test run.

If fixture assumptions are found and patched during this subunit, add focused regression tests for each patched assumption before closing.

## Definition Of Done

- A new real-ish project workspace was verified using the current app workflow.
- The intake log documents success, workarounds, failures, and fixture assumptions encountered.
- No active fixture-specific hardcoding requiring a patch was found.
- No product code changes were made, so `projects/trails` behavior was not altered by this subunit.
