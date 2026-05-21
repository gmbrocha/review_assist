# Sprint 5.0: Planning Diff Lock And Numbering Decision

## Status

Accepted planning direction. This is the first Sprint 5 subunit and should complete before any implementation code changes.

## Goal

Lock the Sprint 5 scope, package diff, and numbering so implementation starts from a clear report-policy plan.

This subunit is planning/documentation only unless a tiny documentation correction is needed to prevent Codex from starting the wrong sprint.

## Inputs

- Extracted policy package under `pro_review_assist_policy_package_sprint_5/`
- Current root Sprint 5 planning docs
- Current app policy/config docs
- `docs/STABILIZATION_PASS_BEFORE_NEXT_SPRINT.md`
- `docs/core/CURRENT_STATE.md`
- `docs/sprints/README.md`

## Required Decisions To Record

- Sprint 5 is report-policy/source-truth/discernment work.
- Sprint 6 remains the future figure-editing sprint unless explicitly renumbered later.
- The extracted package is requirements-mining evidence, not a standard to copy.
- Existing `config/report_section_policy.json` is the current canonical policy file unless Sprint 5.1 explicitly migrates it.
- No source acquisition expansion, GPT expansion, figure editor work, or deliverable count change is approved by this planning subunit.

## Outputs

- Updated Sprint 5 overview and subunit docs.
- Current-state and sprint-index docs that point at Sprint 5 correctly.
- Stabilization report wording that distinguishes report-policy Sprint 5 from future Sprint 6 figure work.
- A human-decision list carried forward into the owning subunit docs.

## Guardrails

- Do not implement app behavior.
- Do not create new config files.
- Do not regenerate or commit project artifacts.
- Do not generalize trail/corridor or PEL material.
- Do not hide open methodology decisions.

## Acceptance Criteria

- Root Sprint 5 docs describe a dependency-aware Sprint 5.0 through Sprint 5.9 plan.
- No Sprint 5 doc tells Codex to implement figure editor/recipe/versioning work.
- Related docs no longer confuse report-policy Sprint 5 with future Sprint 6 figure work.
- Old broad prompts are narrowed or deferred in the revised subunit docs.
- Worktree contains only documentation/planning changes.

## Tests / Verification

- Search Markdown for stale wording that implies the active report-policy sprint is figure work, stale Sprint 4 active-target wording, and retired Sprint 5 filenames.
- `git diff --check`

No code tests are required for this documentation-only subunit.
