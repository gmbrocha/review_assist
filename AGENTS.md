# Agent Instructions

This repository is an early scaffold for an alternatives review workflow tool. Future coding agents should keep changes narrow, inspectable, and aligned with the human-in-the-loop product boundary.

## Project Rules

- Do not implement broad features without explicit confirmation.
- Keep scope narrow and tied to the requested task.
- Prefer simple, inspectable code over complex frameworks or premature abstraction.
- Do not add external APIs, credentials, paid services, or large dependencies without approval.
- Preserve human-in-the-loop assumptions throughout the product and code.
- Do not call generated reports final.
- Do not implement ranking, recommendation, optimization, or preferred-alternative logic unless explicitly requested.
- Do not add hard scoring unless explicitly requested and documented as non-decisional support.
- Separate deterministic GIS/source checks from AI-assisted narrative synthesis.
- Treat imagery-observed features as review items, not authoritative facts.
- Preserve source provenance, uncertainty, and review status in future data models.
- Preserve the "no blank page" direction: future implementation should aim for comprehensive pre-review draft packages, not sparse isolated outputs.
- Treat the review queue as the core domain model for the desktop app. Every generated artifact should become a reviewable item with status, provenance, assumptions, editable content, and export eligibility.
- Treat `docs/WORKFLOW_MODEL.md` as the canonical workflow truth model. Align future architecture, code, and docs to the workspace -> source status set -> populate for review -> review queue -> accepted export flow.
- Keep desktop GUI code thin. Put workflow and GIS/report logic in services underneath the GUI rather than burying it in button callbacks.
- Keep deterministic GIS/source checks separate from LLM-assisted synthesis.

## Current Phase

The project has Phase 1 ingestion and an initial Phase 2 source/spatial-check baseline. The canonical workflow is still being refined. Do not build the full desktop application, wire external integrations, add authentication, implement ML/CV workflows, persist a review queue, or generate reports unless the user explicitly changes the scope.

## Directory Conventions

- Use `projects/` for active project workspaces.
- Use `archive/` for general archived files that should be retained but are not active project materials.
- Use `docs/archive/` for superseded or historical documentation.
- Do not move active planning docs into an archive folder unless explicitly requested.

## Documentation Update Rule

Any code change must include a documentation review.

Before finishing a task, check whether the change affects:

- project behavior
- architecture
- data models
- workflows
- setup instructions
- source/layer assumptions
- review policy
- report output behavior
- known limitations
- roadmap status

If yes, update the relevant docs in the same commit/task.

Relevant docs may include:

- README.md
- docs/CURRENT_STATE.md
- docs/WORKFLOW_MODEL.md
- docs/ARCHITECTURE.md
- docs/FIRST_VERSION_PLAN.md
- docs/DATA_SOURCES.md
- docs/REVIEW_POLICY.md
- docs/DECISIONS.md
- docs/ROADMAP.md
- docs/OVERALL_CONTEXT.md
- docs/REPORT_TAXONOMY.md
- docs/FINDING_TYPES.md
- docs/UNCERTAINTY_AND_PROVENANCE.md
- docs/MAP_GENERATION.md
- docs/REPORT_ASSEMBLY.md
- docs/IMAGERY_REVIEW.md
- docs/LLM_ASSISTED_SYNTHESIS.md

Do not leave documentation stale after code changes.

If no documentation update is needed, explicitly note why in the task summary.
