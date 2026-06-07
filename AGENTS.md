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
- Warm context: `docs/core/DECISIONS.md`, `docs/core/ARCHITECTURE.md`, governance docs, `docs/governance/DEFERRED_WORK.md`, related sprint docs when direction is ambiguous.
- Cold context: `docs/archive/`, completed sprint plans, historical notes, old implementation records, superseded decisions, including the archived former root `CANONICAL_PLAN.md`.

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

Current project mode: V1.0 implementation is complete and there is no active sprint. Default work should be testing, verification, bug fixing, documentation correction, and explicitly approved new-feature work only.

Use the sprint protocol only when the user explicitly starts a new sprint/subunit or asks to resume a named sprint plan. For each sprint subunit unless the user changes the protocol:

1. Inspect `git status`, commit the accepted checkpoint, and push.
2. Implement exactly one sprint subunit.
3. Run focused tests and then broader tests when appropriate.
4. Audit the work, fix issues, and rerun affected tests.
5. Update affected permanent docs and deferred work.
6. Move the completed sprint/subunit planning doc from the repo root into `docs/archive/sprints/`, update sprint/archive indexes, then commit and push the completed subunit before starting the next one.

## Documentation And Testing

Any behavior-changing code needs a documentation review. Update only the docs that own the affected subsystem; use `docs/domains/README.md` to route domain docs.

## Command Center Current-State Sync

Command Center reads `docs/CURRENT_STATE.md` as the project pulse for registration and re-entry. Command Center is read-only; the user or project agent updates project files, current-state docs, and manifests.

After any commit or git state change made during an agent session, update `docs/CURRENT_STATE.md` before the final response. Git state changes include commits, amended commits, merges, rebases, pulls, meaningful branch switches, commit-preparation staging changes, `.project-command/project.json` changes, and service/runtime metadata changes that Command Center reads.

Minimum sync behavior: update `Last updated: YYYY-MM-DD`, add one concise `Recent Activity` entry, and update `Current Status`, `Known Gaps`, `Next Actions`, or `Service Notes` only when materially changed. If the change is metadata-only, describe it as metadata-only. Do not imply product behavior changed. Do not invent project state; use `Unverified`, `Not reviewed`, or an explicit uncertainty note when needed.

## Python Environment Rule

Review Assist uses the repo-local `.venv` as the only valid app environment. Global or system Python is not valid for checks, imports, tests, scripts, migrations, or app startup.

On Windows/PowerShell, run Python through `.\\.venv\\Scripts\\python.exe`, for example:

```powershell
.\\.venv\\Scripts\\python.exe -c "import sys; print(sys.executable)"
.\\.venv\\Scripts\\python.exe -m pytest
```

Dependency, import, or test failures must be reproduced with `.\\.venv\\Scripts\\python.exe` before being treated as real code failures. Verify `sys.executable` before reporting dependency problems. If `.venv` is missing or broken, stop and report that the repo-local environment needs setup instead of installing packages globally.

Run relevant tests before committing code changes when the local environment is available. If tests cannot be run, state why and record residual risk.

## Post-Implementation Generated Artifact Rule

After any implementation that changes source/materialization/status/acquisition/caveats, project area or comparison units, constraints, deliverable tables or figures, evidence packages, deliverable items, review queue/reset behavior, GPT drafting or payloads, export/report assembly, UI adapter paths/review detail display, or canonical artifact paths, explicitly consider generated artifact freshness before closeout.

Required closeout:

1. State whether generated artifacts are affected.
2. Identify the minimum affected chain, for example source status -> constraints -> tables/figures -> evidence package -> deliverable items -> review queue -> export manifests.
3. Regenerate only necessary artifacts from current code with CLI commands, not a stale running server.
4. If the local Flask server is running and code changed, stop/restart it before relying on UI behavior or UI-triggered regeneration.
5. Confirm UI behavior reads canonical artifact paths.
6. Report exact regeneration commands run, or explain why regeneration was not needed.
7. Report generated artifacts intentionally left uncommitted. Do not commit generated project artifacts unless explicitly approved.
8. If human review state may be overwritten, use the dev/test reset flow only when appropriate and state that it is destructive to generated review candidates.

A passing code test does not prove the current local UI is showing fresh generated artifacts. Distinguish code correctness from sample-project artifact freshness. If the Flask/local web server was started before code changes, it may regenerate canonical artifacts using stale imported modules; restart it before using UI actions to regenerate or verify outputs.

Canonical generated artifact paths include `source_status/source_status_set.json`, `deliverable/tables.json`, `deliverable/figures.json`, `evidence/evidence_package.json`, `deliverable/deliverable_items.json`, `review_queue/review_queue.json`, `exports/export_manifest.json`, and `exports/deliverable_package_manifest.json`.

Implementation closeout must include:

- Generated artifacts affected: yes/no
- Server restart needed: yes/no
- Regeneration commands run:
- Canonical artifacts verified:
- UI verified from current server: yes/no/not applicable
- Generated artifacts intentionally uncommitted:
- Focused tests run:
- Full suite run: yes/no, reason
- Remaining stale-artifact risk:
