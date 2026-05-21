# Sprint 7.4: Fresh Project Intake Trial

## Status

Parked draft for review. Do not implement until Sprint 7.1 through 7.3 are accepted and Monica has provided a project file for testing.

## Purpose

Validate that Review Assist is truly project-general and not accidentally tuned to the `projects/trails` fixture.

Stop validating only against `projects/trails`. Use a new real-ish project from Monica to expose any fixture-specific assumptions baked into the workflow.

## Input Needed

Ask Monica for an old site or project KMZ with actual features, preferably something safe to use for private POC testing.

The project file should have real geometry and ideally real feature context (site boundary, study area, or route corridor), but does not need to be a current active project.

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

## Tests

No automated tests are required for this subunit. This is an exploratory trial, not a product test run.

If fixture assumptions are found and patched during this subunit, add focused regression tests for each patched assumption before closing.

## Definition Of Done

- A new project has been created from Monica's project file using the current app workflow.
- The intake log documents success, workarounds, failures, and fixture assumptions encountered.
- Any fixture-specific hardcoding found is recorded with file location and flagged for Sprint 7.7 triage.
- `projects/trails` is not broken by any changes made during this subunit.
