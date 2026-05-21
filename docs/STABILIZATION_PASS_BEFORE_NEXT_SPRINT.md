# Stabilization Pass Before Next Sprint

## Summary

This pass stabilized the current Review Assist baseline before Sprint 5 figure-editing work. The pass was audit-first and treated all implementation changes as `SAFE LAYER CHANGE`: no Sprint 5 figure recipe, override, regeneration job, versioning, or approval model was implemented.

The accepted dirty worktree was inventoried, committed, and pushed as checkpoint `944e3b5` before stabilization edits began. Current app health checks found the reset path, duplicate-output protections, route loading, artifact allowlist, figure/table source scoping, and review/export gates generally stable.

## Changes Made

- Fixed `scripts/verify.ps1` source-data guardrails so tracked source warehouse manifest JSON files are allowed while bulk source data remains blocked.
- Added explicit test coverage that `reset_review_queue(..., include_exports=True)` deletes generated export manifests, Markdown/DOCX outputs, and copied figure assets while rebuilding the standard review queue.
- Added web UI adapter test coverage that the Developer Testing Reset form passes `include_exports=True` when the export cleanup checkbox is selected.
- Updated `docs/domains/REPORT_ASSEMBLY.md` so developer reset examples show the current confirmation-safe command shape, including `--yes --include-exports`.
- Added this stabilization report with audit findings, verification commands, deferred issues, and readiness status.

## Bugs Fixed

- Readiness script guardrail mismatch: `verify.ps1 -SkipInstall` initially failed because intentionally tracked `sources/**/source_manifest.json` files were treated as bulk source data. Fixed by allowing only `sources/source_warehouse_manifest.json` and per-source `source_manifest.json`; bulk source files under `sources/` and project layer data remain blocked. Verification: `.\scripts\verify.ps1 -SkipInstall` passed.
- Reset export cleanup coverage gap: fixed by adding service and web tests for `--include-exports`. Verification: `tests/test_review_queue.py tests/test_web_app.py` passed.
- Reset documentation drift: fixed the report assembly domain doc so it no longer presents `--regenerate` as the primary command and now documents export cleanup directly. Verification: documentation reviewed against current CLI options.

No production code behavior bug required a source change in this pass.

## Code Hygiene And Documentation Issues

Fixed now:

- Missing targeted test coverage for destructive export cleanup in the developer reset path.
- Reset command documentation was technically supported but did not match the safer day-to-day CLI examples.
- `scripts/verify.ps1` source-data guardrail now matches the documented stable source warehouse manifest convention.

Safe follow-up:

- Add artifact fingerprint/freshness metadata so future generated review candidates can distinguish stale upstream inputs from current evidence without relying on destructive developer reset.
- Add browser-level smoke automation with console capture when the local toolchain includes Playwright or equivalent; current verification used Flask route tests and app test-client smoke.
- Add a small report command that audits duplicate source-layer concepts across figures and tables from generated artifacts for reviewer diagnostics.

Defer until after next sprint:

- Production-grade review-state migration across regenerated deliverable items and figure versions.
- Full cartographic redesign, figure editor workflows, style overrides, render jobs, figure version history, and export resolver changes.
- Larger state-model refactors that would restructure generated/source/reviewer artifacts.

Possible blocker before next sprint:

- None found. The next sprint should still begin from a clean committed baseline and should not reuse the developer reset as production review-state migration.

## Deferred Issues

- Review queue freshness/versioning remains deferred because solving it properly requires upstream fingerprints and production review-state migration. It does not block Sprint 5, but Sprint 5 should design figure versioning with explicit freshness/version references.
- Browser console verification was not run because no browser automation tool was used in this pass. It does not block Sprint 5 because Flask route and form coverage is strong, but adding browser smoke tests would reduce UI regression risk.
- Stream crossing counts remain methodology-sensitive. Existing code now counts canonical NHD flowline crossing events and documents the metric contract; matching manually prepared example counts would require a separate methodology decision. This does not block Sprint 5.

## Risks Remaining

- Sample generated artifacts can still become stale after source/table/figure code changes unless regenerated intentionally.
- The developer reset is destructive to generated review candidates and is not a production-safe review-state migration tool.
- The local web app is still a synchronous, local-first Flask shell; no authentication, background jobs, or production deployment hardening is present.
- Figure cartography is readable for POC review but not a full production cartographic workflow.

## Commands Run

- `git status --short` - passed; used for baseline inventory.
- `git diff --name-status` - passed; used for baseline inventory.
- `git diff --stat` - passed; used for baseline inventory.
- `git commit -m "Checkpoint before stabilization pass"` - passed; created `944e3b5`.
- `git push origin main` - passed.
- `.\.venv\Scripts\review-assist.exe validate-deliverable-matrix` - passed.
- `.\.venv\Scripts\review-assist.exe validate-report-prompts --json` - passed.
- `.\.venv\Scripts\review-assist.exe reset-review-queue projects/trails --dry-run --json` - passed.
- `.\.venv\Scripts\review-assist.exe list-review-queue projects/trails` - passed.
- Direct CLI smoke checks for inspect, geometry, source gaps, constraints, evidence, populate, preview export, demo deliverable, and review queue listing - passed.
- Flask test-client route smoke for `/projects`, `/setup`, `/overview`, `/review`, `/export`, `/outputs`, and one review detail route - passed.
- Generated artifact duplicate audit for `projects/trails` tables, figures, deliverable items, review queue, and figure shown-layer source IDs - passed.
- `.\.venv\Scripts\python.exe -m pytest tests/test_web_app.py tests/test_review_queue.py tests/test_deliverable_figures.py tests/test_deliverable_tables.py` - passed before stabilization edits: 115 passed, 2 pyogrio warnings.
- `.\.venv\Scripts\python.exe -m pytest tests/test_review_queue.py tests/test_web_app.py` - passed after edits: 60 passed, 2 pyogrio warnings.
- `.\.venv\Scripts\python.exe -m pytest tests/test_deliverable_figures.py tests/test_deliverable_tables.py` - passed after edits: 57 passed.
- `.\.venv\Scripts\python.exe -m pytest` - passed after edits: 464 passed, 7 GeoPandas/pyogrio warnings.
- `.\scripts\verify.ps1 -SkipInstall` - passed after guardrail fix; includes full pytest and CLI smoke checks.

## Generated Artifact Closeout

- Generated artifacts affected: no by product-code changes. Smoke verification regenerated ignored sample project artifacts.
- Minimum affected chain: not applicable.
- Server restart needed: no.
- Regeneration commands run: `populate-for-review projects/trails --no-gpt-drafting`, `populate-for-review projects/conexon_projects --no-gpt-drafting`, `export-report projects/trails --include-draft --format both`, and `build-demo-deliverable projects/trails --format both --no-gpt-drafting` through direct smoke checks and `verify.ps1`.
- Canonical artifacts verified: yes, by dry-run counts and duplicate audit for `deliverable/tables.json`, `deliverable/figures.json`, `deliverable/deliverable_items.json`, and `review_queue/review_queue.json`.
- UI verified from current server: not applicable; route health was verified through Flask test client, not a running browser server.
- Generated artifacts intentionally uncommitted: ignored generated artifacts under `projects/trails` and `projects/conexon_projects`, including refreshed review/export artifacts.
- Focused tests run: web app, review queue, deliverable figures, deliverable tables.
- Full suite run: yes, `464 passed`.
- Remaining stale-artifact risk: low for code correctness; sample UI artifacts can still become stale after future behavior changes unless regenerated from current code.

## Next Sprint Readiness

MOSTLY READY: the current app is stable enough to begin Sprint 5. Minor known issues remain around production-grade review-state freshness and browser-level UI automation, but they do not block the next sprint.
