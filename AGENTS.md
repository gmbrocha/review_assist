# Agent Instructions

This repository is an early scaffold for an alternatives review workflow tool. Future coding agents should keep changes narrow, inspectable, and aligned with the human-in-the-loop product boundary.

## Project Rules

- Before any large implementation, roadmap change, workflow change, report-generation change, source-acquisition change, review-queue change, export change, or architecture change, read `PLAN_REDIRECT_NEW.md` first. Treat it as the canonical drift-control document for this repo.
- Treat `env_constraints_report_20260511_EXAMPLE_ONLY.docx`, as summarized and normalized in `PLAN_REDIRECT_NEW.md`, as the structural destination for generated deliverables. The goal is to fill that template with project-specific constraint findings, source-backed copy, visuals, tables, caveats, and reviewed export content.
- If implementation direction feels ambiguous, return to `PLAN_REDIRECT_NEW.md` before coding. Align the change to the constraint engine plus review queue plus export path.
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
- Treat the review queue as the core domain model for the product. Every generated artifact should become a reviewable item with status, provenance, assumptions, editable content, and export eligibility.
- Treat `PLAN_REDIRECT_NEW.md` as the canonical planning source. Keep `docs/WORKFLOW_MODEL.md` aligned to the workspace -> source status set -> populate for review -> review queue -> accepted export flow.
- Keep future web app UI code thin. Put workflow and GIS/report logic in services underneath the UI rather than burying it in route handlers or view callbacks.
- Keep deterministic GIS/source checks separate from LLM-assisted synthesis.
- Add or update tests with each implementation phase and each behavior-changing code change.
- Run the relevant test suite before committing or pushing code changes. If tests cannot be run, state why and record the residual risk.
- Do not leave newly implemented workflow behavior covered only by manual inspection unless the user explicitly accepts that tradeoff.

## Current Phase

The project has Phase 1 ingestion, Phase 2 source/spatial-check/source-acquisition baselines, Phase 3 project context/source status artifacts, a Phase 4 JSON-backed review queue baseline, Phase 5 populate-for-review orchestration, deterministic findings/tables/maps/report sections, a constraint-engine baseline, and a first Markdown export compiler. Do not build the web app, wire broad external integrations, add authentication, implement ML/CV workflows, call LLMs, or create final PDF exports unless the user explicitly changes the scope.

## Sprint Execution Protocol

Use this protocol for each sprint subunit unless the user explicitly changes it:

1. Start with a checkpoint: inspect `git status`, commit the current accepted state, and push it.
2. Implement exactly one sprint subunit.
3. Run the relevant tests and smoke checks for that subunit.
4. Perform an audit/review pass on the implemented work.
5. Fix anything found during the audit and rerun affected tests.
6. Update affected documentation in the same work cycle.
7. Commit the completed subunit and push it before starting the next sprint subunit.

If the initial checkpoint or final push cannot be completed, stop and report the blocker before moving to the next subunit. Preserve unrelated user changes and do not stage or commit files outside the intended checkpoint/subunit scope unless the user asks for an all-inclusive checkpoint.

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

## Testing Discipline

Every implementation phase should include tests for the behavior it introduces. Keep tests close to the service or CLI boundary being changed, and prefer small synthetic geospatial fixtures for deterministic behavior.

Minimum expectations for behavior-changing code:

- Add or update unit tests for new services, data models, validation rules, and error paths.
- Add or update CLI tests when commands, options, output paths, or exit behavior change.
- Run `.\.venv\Scripts\python.exe -m pytest` before committing when the local environment is available.
- Run focused smoke checks against real project workspaces when a change affects `projects/trails` or `projects/conexon_projects` workflows.
- Document any skipped tests, blocked test runs, or known residual risk in the final task summary.
