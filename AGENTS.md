# Agent Instructions

This repository builds a human-in-the-loop environmental constraints review workflow. Keep changes narrow, inspectable, source-backed, and aligned with review-before-export.

## Agent Context Loading Rule

Read minimally first.

Always load only:

- `AGENTS.md`
- `docs/core/CURRENT_STATE.md`
- the active sprint/subunit file
- any directly relevant domain doc for the subsystem being touched

Do not recursively load the entire docs tree unless explicitly requested. Only load additional docs when the task touches that area.

Context temperature:

- Hot context: `AGENTS.md`, `docs/core/CURRENT_STATE.md`, active sprint/subunit, directly relevant domain docs.
- Warm context: `CANONICAL_PLAN.md` when direction is ambiguous, `docs/core/DECISIONS.md`, `docs/core/ARCHITECTURE.md`, governance docs, `docs/governance/DEFERRED_WORK.md`, related sprint docs.
- Cold context: `docs/archive/`, completed sprint plans, historical notes, old implementation records, superseded decisions.

Cold context should not be loaded unless explicitly needed.

## Mandatory Workflows

- Truth Stabilization Pass: `docs/governance/TRUTH_STABILIZATION.md`
- Deferred Work Propagation: `docs/governance/DEFERRED_WORK.md`
- Sprint Resolution & Knowledge Migration: `docs/governance/SPRINT_RESOLUTION.md`

Before implementation, classify the change as `SAFE LAYER CHANGE`, `DOMAIN EXTENSION`, `DOMAIN CORRECTION`, or `DANGEROUS PATCH`. If a task risks hiding uncertainty/provenance, bypassing review, or implying unsupported authority, stop and request explicit approval.

## Product Boundaries

- The system generates first-pass draft review packages for human review.
- Do not call generated reports final.
- Do not rank, score, recommend, select, reject, approve, clear, or make regulatory determinations unless explicitly requested and documented as non-decisional support where applicable.
- Keep deterministic GIS/source checks separate from LLM-assisted narrative synthesis.
- Preserve source provenance, uncertainty, missing data, failed/gated/stale sources, buffer assumptions, and reviewer status.
- Treat imagery-observed features as reviewer context, not authoritative facts.
- The future web app should stay thin over service-layer workflow logic.

## Sprint Protocol

For each sprint subunit unless the user changes the protocol:

1. Inspect `git status`, commit the accepted checkpoint, and push.
2. Implement exactly one sprint subunit.
3. Run focused tests and then broader tests when appropriate.
4. Audit the work, fix issues, and rerun affected tests.
5. Update affected permanent docs and deferred work.
6. Move the completed sprint/subunit planning doc from the repo root into `docs/archive/sprints/`, update sprint/archive indexes, then commit and push the completed subunit before starting the next one.

## Documentation And Testing

Any behavior-changing code needs a documentation review. Update only the docs that own the affected subsystem; use `docs/domains/README.md` to route domain docs.

Run relevant tests before committing code changes when the local environment is available. If tests cannot be run, state why and record residual risk.
