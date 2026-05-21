# Sprint 7.7: Reviewer Friction Backlog

## Status

Parked draft for review. Do not populate until Sprint 7.4 through 7.6 testing logs and assessments are complete.

## Purpose

Turn fresh-project testing findings into an actionable, triaged backlog that drives the next sprint planning cycle.

This subunit collects, categorizes, and prioritizes all findings from the Sprint 7 trial and UI review work into a structured backlog.

## Priority Levels

| Priority | Meaning |
|---|---|
| P0 | Blocks real reviewer testing — must fix before trial continues |
| P1 | Confusing or trust-reducing — degrades reviewer confidence |
| P2 | Useful polish or source expansion — improves usability |
| P3 | Later product or deployment hardening — non-urgent |

## Finding Categories

Organize findings into the following buckets:

### UI Language
Issues with reviewer-facing labels, internal status strings leaking into the UI, or confusing status descriptions.

### Review Statuses
Issues with workflow status, readiness status, badge display, or ambiguous review action prompts.

### Missing Source Explanations
Cases where a source was unavailable, stale, or gated and the reviewer had no clear explanation of why.

### Figure Readability
Figure rendering failures, incorrect extents, unreadable scale or labels, or missing expected figures.

### Manual Material Workflow
Issues with how manual or reviewer-supplied material gaps are surfaced, entered, and tracked.

### Project Setup Flow
Issues with new project creation, KMZ import, input classification, or source materialization for a non-fixture project.

### Source Warehouse Gaps
Source types or datasets that are missing, inadequately covered, or producing unreliable outputs for the project type.

### Export Polish
Issues with export package structure, export-blocked item clarity, or reviewer-facing vs. internal content in the exported package.

### GPT Prompt And Style Issues
Output quality issues from GPT-assisted sections: tone, length, confidence calibration, unsupported claims, or reviewer-inappropriate language.

### Report Inclusion And Discernment Issues
Sections included that should have been omitted, sections omitted that should have been included, or inclusion logic that does not match the real project context.

## Output Format

Each backlog item should record:

- Priority (P0/P1/P2/P3)
- Category (from the buckets above)
- Short description of the finding
- Source file and line if a code location is known
- Suggested fix or direction if obvious
- Origin sprint subunit (7.4, 7.5, or 7.6)

## Relationship To Deferred Work

P0 and P1 items that cannot be resolved in the next sprint should be propagated to `docs/governance/DEFERRED_WORK.md` following the standard deferred work propagation workflow.

## Tests

No automated tests are required for this subunit. This is a planning and triage output.

Any P0 fixes applied as part of closing this subunit must include focused regression tests.

## Definition Of Done

- All findings from Sprint 7.4, 7.5, and 7.6 are collected and categorized.
- Every finding has a priority level.
- P0 items are clearly identified and either resolved or escalated to `DEFERRED_WORK.md`.
- The backlog is structured for direct use in next sprint planning.
- No source truth or generated artifact content is changed by this subunit itself.
