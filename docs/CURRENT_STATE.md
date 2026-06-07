# Current State

Last updated: 2026-06-07

## Summary

Review Assist is a local, service-first workflow for generating source-backed first-pass environmental constraints review packages for mandatory human review. It is not a recommendation engine, final environmental review, regulatory approval tool, or autonomous analyst.

## Current Status

V1.0 is implementation-complete. The current project mode is maintenance-oriented: testing, verification, bug fixing, documentation correction, source/data validation, and explicitly approved new-feature work only.

## Blockers

None.

## Current Decisions

Command Center reads this file as the project pulse for registration and re-entry. The detailed Review Assist implementation state remains in `docs/core/CURRENT_STATE.md`.

Command Center registration is manual from Settings by repository path. `.project-command/project.json` provides metadata only and does not create registry membership.

Review Assist uses the repo-local `.venv` as the only valid app environment.

## Assumptions

The current Command Center manifest shape is provisional. Required manifest values are source-grounded from `README.md`, `pyproject.toml`, `AGENTS.md`, and `docs/core/CURRENT_STATE.md`.

## Known Gaps

Command Center's final manifest schema is not implemented yet, so `.project-command/project.json` may need later review.

The local web UI is local-first and unauthenticated; no hosted deployment, multi-user workflow, archive flow, PDF export, advanced audit browser, or production hardening is implemented.

Deferred Review Assist limitations are tracked in `docs/governance/DEFERRED_WORK.md`.

## Next Actions

Use maintenance workflows unless the user explicitly approves new feature work.

When Command Center's final manifest schema is available, review `.project-command/project.json` against it.

## Recent Activity

- 2026-06-07: Added provisional Command Center metadata and current-state pulse documentation; metadata-only, no product behavior changed.

## Service Notes

Local web UI command: `.\\.venv\\Scripts\\review-assist-web.exe`

Default local URL: `http://127.0.0.1:8766`

The README documents `REVIEW_ASSIST_PROJECT_ROOT`, `REVIEW_ASSIST_WEB_HOST`, and `REVIEW_ASSIST_WEB_PORT` overrides. No dedicated health-check route was found during this setup pass.
