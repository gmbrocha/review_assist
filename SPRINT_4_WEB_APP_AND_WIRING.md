# Sprint 4: Web App And Wiring

## Purpose

Build the web app UI and wire it to the services completed in Sprints 1 through 3. This sprint should not invent new GIS, report, review, or export behavior in the UI. The web app is a thin operator surface over the canonical pipeline defined in `CANONICAL_PLAN.md`.

## Prerequisites

Sprint 4 should start only after these backend capabilities exist:

- Project input package classification.
- Project area artifact with bbox, counties, and basemap candidates.
- Comparison-unit artifact.
- Deliverable matrix and prompt config.
- Constraint summaries, canonical tables, canonical figures, and section evidence packages.
- Bounded review queue with one item per deliverable target.
- Review-complete export gate.
- Reviewed DOCX export package.
- Service and CLI tests for the non-UI pipeline.

Sprint 4 should not inherit unresolved backend deferred work from `docs/governance/DEFERRED_WORK.md` unless explicitly re-scoped. The web app should remain a thin operator surface over the completed Sprint 2/3 service contracts.

## Non-Goals

Do not use Sprint 4 to:

- Rebuild the constraint engine.
- Add new source downloaders unless explicitly approved.
- Add ranking, recommendation, scoring, or preferred-alternative behavior.
- Bypass the review-complete export gate.
- Put GIS/report logic in route handlers or frontend code.
- Add authentication, remote multi-user deployment, or hosted infrastructure unless explicitly approved.
- Build a standalone desktop GUI.

## Initial Stack Decision

Default initial direction:

- Use a local-first Python web app.
- Keep the backend service layer in `src/review_assist/`.
- Add a thin web layer that calls existing services.
- Prefer a conservative server-rendered UI with small static JavaScript where practical.
- Choose the final web framework at the start of Sprint 4 after checking current dependencies and user preference.

Framework decision criteria:

- Easy local launch for the reviewer.
- Simple file upload handling.
- Good testability for routes and service calls.
- Minimal new dependencies.
- No forced cloud deployment.
- Clean separation from GIS/report services.

Sprint 4 Pass 1 stack decision:

- Use Flask/Jinja for a local-first, server-rendered web UI shell.
- Keep UI access behind `review_assist.web.adapter`; route handlers should remain presentation/control flow only.
- Keep raw/audit artifacts out of the default workflow. Expose generated outputs only through manifest-listed artifact links with project-root path safety.

Sprint 4 Pass 1 implementation status:

- Implemented: app shell, left navigation, project list/selection, overview/source/populate status, bounded standard review queue, review item detail/actions, export readiness, preview/reviewed export triggers, package outputs, manifest-listed artifact links, and project-root path safety tests.

Sprint 4 Pass 2A implementation status:

- Implemented: safe draft project creation, staged uploads under `staging/uploads/`, commit into `inputs/` plus valid `config/project.json`, input classification through the existing input-package service, missing-input readiness blockers, and lightweight synchronous latest-run status for classify/populate/export actions.
- Remaining: richer progress handling, role correction UI, advanced audit browsing, UI polish, project archive flow, background execution, and any production/deployment concerns. These should stay thin over service contracts and should not make raw/audit artifacts part of the default review/export path.

## Information Architecture

The app should use left-side navigation with four main tabs:

- `Projects`
- `Overview`
- `Review`
- `Export Report`

Navigation rules:

- `Projects` is available without an active project.
- `Overview`, `Review`, and `Export Report` operate on the selected project.
- If no project is selected, downstream tabs should show an empty state that routes the user back to `Projects`.
- UI labels should match the review workflow language: create, upload, create review queue, review, accept, edit, replace, decline, export.

## Workstream 1: Web App Shell And Backend Boundary

### 1.1 Application shell

- Add a local web entrypoint.
- Add app startup configuration.
- Add a project-root aware path resolver.
- Add static asset handling.
- Add shared layout with left navigation.
- Add selected-project state.
- Add basic error pages.

### 1.2 Service boundary

- Route handlers should call service functions.
- Route handlers should not parse GIS files directly.
- Route handlers should not generate tables, maps, report text, or DOCX content directly.
- Route handlers should translate service exceptions into user-visible status messages.
- File paths exposed to the UI should be project-relative or artifact identifiers when practical.

### 1.3 API or route contract

Provide routes or API endpoints for:

- List projects.
- Create project.
- Archive project.
- Select project.
- List project inputs.
- Upload input files.
- Classify uploaded files.
- Run `Create Review Queue`.
- Get pipeline run status.
- List review queue items.
- Get review item details.
- Save review item edits.
- Accept review item.
- Replace review item content.
- Decline review item.
- Get export readiness.
- Run reviewed export.
- Open or download export package artifacts.

### 1.4 Tests

- Add route tests for happy paths and common error paths.
- Add service boundary tests using temporary project workspaces.
- Add tests that route handlers do not require real Mississippi source warehouse files for basic page rendering.

## Workstream 2: Projects Tab

### 2.1 Project list

- Show active projects under `projects/`.
- Show project name, last modified date, current pipeline status, review status, and export status when available.
- Provide a clear selected-project state.
- Provide an archive view or archive filter.

### 2.2 Create project

- Let the user create a project by name.
- Normalize the project folder name safely.
- Create the project workspace under `projects/<project_id>/`.
- Create initial project metadata.
- Do not allow duplicate active project IDs without confirmation.
- Surface validation errors for invalid names.

### 2.3 Archive project

- Allow archiving an active project.
- Preserve project artifacts.
- Move or mark archived projects according to the chosen project-storage convention.
- Do not delete project data.

### 2.4 Tests

- Project creation creates the expected workspace.
- Invalid names fail clearly.
- Duplicate names fail or require a defined confirmation path.
- Archived projects are not lost and remain discoverable.

## Workstream 3: Overview Tab

### 3.1 Upload and staging area

- Provide drag/drop or file picker upload.
- Show staged files before commit where practical.
- Show uploaded files after commit.
- Show file size, extension, role/classification, and status.
- Support KMZ as the required near-term project geometry input.
- Accept optional supporting files for future source/manual review workflows.

### 3.2 File classification controls

- Show inferred classifications:
  - `project_geometry`
  - `source_layer`
  - `agency_document`
  - `supporting_report`
  - `imagery_or_basemap`
  - `reviewer_notes`
  - `unknown`
- Allow reviewer confirmation or correction.
- Clearly flag when a required KMZ is missing.
- Clearly flag when multiple project-geometry candidates need confirmation.

### 3.3 Project overview artifacts

- Show project-area status:
  - bbox created.
  - county names detected.
  - aerial basemap candidates selected.
  - comparison units detected.
  - source status summary.
- Show validation warnings.
- Show artifact links where useful.

### 3.4 Create Review Queue action

- Add a primary button labeled `Create Review Queue`.
- Enable it only when the project has enough required input state or show a clear blocker.
- Run the full non-UI pipeline:
  - input classification.
  - geometry normalization.
  - project area/bbox/county/basemap selection.
  - comparison-unit creation.
  - source status/materialization/acquisition.
  - constraint processing.
  - table generation.
  - figure generation.
  - text/stub generation.
  - review queue creation.
- Show progress and final status.
- Do not generate a user-facing report from this action.

### 3.5 Tests

- Upload persists files under the selected project.
- KMZ absence blocks or warns according to the service contract.
- File classification updates are saved.
- `Create Review Queue` calls the pipeline service and records run status.

## Workstream 4: Review Tab

### 4.1 Review item list

- Show one row per deliverable matrix target.
- Do not show one row per raw GIS intersection by default.
- Show item type, title, section/table/figure/attachment number, status, source category, and last modified time.
- Provide filters by status, item type, section, and source category.
- Show total item count and remaining unreviewed count.

### 4.2 Review detail view

- Show generated content or stub text.
- Show editable content for text items.
- Show table preview for table items.
- Show figure preview for figure items.
- Show attachment placeholder or linked artifact for attachment items.
- Show source refs, provenance, assumptions, validation warnings, and related comparison units.
- Allow reviewer notes.

### 4.3 Review actions

- Accept as-is.
- Edit and accept.
- Replace fully with reviewer-provided content.
- Decline.
- Preserve previous generated content and reviewer edit history where practical.
- Do not allow a declined item to enter default export.

### 4.4 Status behavior

- Terminal states are accepted, edited, replaced, and declined.
- Unreviewed items block default export.
- Unable-to-verify items require explicit export eligibility if that state remains supported.
- Regeneration should preserve reviewer decisions where the deliverable target ID remains stable.

### 4.5 Tests

- List view is bounded by deliverable matrix targets.
- Accept/edit/replace/decline actions persist.
- Declined items are omitted from export readiness inclusion.
- Remaining unreviewed count updates correctly.

## Workstream 5: Export Report Tab

### 5.1 Readiness panel

- Show export readiness.
- Show total review items.
- Show reviewed terminal-state count.
- Show unreviewed blockers.
- Show declined item count.
- Show stub item count.
- Show latest queue generation run.

### 5.2 Export action

- Default export is disabled until every posted review item has a terminal review state.
- Export compiles reviewed queue items minus declined items.
- Export writes the reviewed DOCX package and manifest.
- Preview/internal draft export, if retained, must be clearly labeled and separate from default export.

### 5.3 Export outputs

- Show generated DOCX path.
- Show export manifest path.
- Show included table, figure, section, and attachment counts.
- Show warnings and residual limitations.
- Provide open/download affordances according to the local web-app runtime.

### 5.4 Tests

- Export is blocked with unreviewed items.
- Export succeeds when all items are accepted, edited, replaced, or declined.
- Declined items are omitted.
- Export manifest displays the expected counts and artifact paths.

## Workstream 6: Runtime Status, Logs, And Errors

### 6.1 Background execution

- Long-running pipeline work should not freeze the UI.
- Provide a run ID for `Create Review Queue`.
- Store run status in project artifacts.
- Show current step, warnings, and final result.

### 6.2 Error handling

- Missing sources should become visible statuses or stubs, not silent failures.
- Hard failures should show the failed step, message, and artifact/log location.
- The app should preserve partial artifacts that are safe to inspect.

### 6.3 Tests

- Failed pipeline run records failure status.
- Missing-source stubs remain reviewable.
- UI can reload and display prior run status.

## Workstream 7: Web App Documentation And Verification

### 7.1 Docs to update

- `README.md`
- `docs/core/CURRENT_STATE.md`
- `docs/core/ARCHITECTURE.md`
- `docs/domains/WORKFLOW_MODEL.md`
- `docs/sprints/ROADMAP.md`
- `docs/domains/REVIEW_POLICY.md`
- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/core/DECISIONS.md`

### 7.2 Verification

- Run full Python tests.
- Run route/API tests.
- Run a local smoke workflow against a synthetic project.
- Run a local smoke workflow against a real project workspace when source data is available.
- Verify the UI can create a project, upload KMZ, create a review queue, review all items, and export a DOCX.

## Sprint Acceptance Checklist

- Web app launches locally.
- `Projects` tab can create, select, list, and archive projects.
- `Overview` tab can upload/classify files and run `Create Review Queue`.
- `Review` tab lists bounded deliverable review items and supports accept/edit/replace/decline.
- `Export Report` tab blocks export until all items are reviewed and then generates reviewed DOCX output.
- UI code remains thin over backend services.
- No standalone desktop GUI is introduced.
- No ranking, recommendation, scoring, preferred alternative, or final-determination behavior is introduced.
- Tests and smoke checks pass or residual risks are documented.
