# Sprint 5: Report Intelligence, Source Truth, And Discernment

## Status

Parked draft for review. Do not start Sprint 5 implementation until the stabilization checkpoint below is clean and accepted.

This file and the linked subunit files are root-level planning notes for human review. Move them into the sprint docs area only after review.

## Purpose

Move Review Assist from a pipeline that can generate artifacts to a system that understands what should be reviewed, included, omitted, drafted, or deferred.

The sprint should happen after the current stabilization checkpoint is clean. No Pro package diff, GPT expansion, or new large policy changes should start until the repo is stabilized and committed.

## Pre-Sprint Gate: Stabilization Checkpoint

This gate is not part of Sprint 5. It is the entry ticket.

Definition of done:

- Stale Flask/server issue is documented in governance.
- Canonical artifact paths are confirmed.
- Dev reset/regenerate flow works.
- New water sources are honestly wired or explicitly deferred.
- Source truth/caveat reconciliation is complete enough that stale acquisition failures do not leak into report/GPT-facing content.
- `projects/trails` can be regenerated cleanly from current code.
- Dirty generated/local artifacts are separated from commit-worthy work.
- Checkpoint commit or commits exist.

No new sprint work should begin until this is true. Otherwise Sprint 5 will build on unstable generated state.

## Subunits

- Sprint 5.1: [Pro Package Diff And Requirements Mining](SPRINT_5_1_PRO_PACKAGE_DIFF_AND_REQUIREMENTS_MINING.md)
- Sprint 5.2: [Canonical Report Section Policy](SPRINT_5_2_CANONICAL_REPORT_SECTION_POLICY.md)
- Sprint 5.3: [Source Needs Manifest And Warehouse Alignment](SPRINT_5_3_SOURCE_NEEDS_MANIFEST_AND_WAREHOUSE_ALIGNMENT.md)
- Sprint 5.4: [Report Inclusion And Discernment Pass](SPRINT_5_4_REPORT_INCLUSION_AND_DISCERNMENT_PASS.md)
- Sprint 5.5: [Reviewer-Supplied Materials And Manual Completion Workflow](SPRINT_5_5_REVIEWER_SUPPLIED_MATERIALS_AND_MANUAL_COMPLETION_WORKFLOW.md)
- Sprint 5.6: [GPT Interpretive Assist Pilot](SPRINT_5_6_GPT_INTERPRETIVE_ASSIST_PILOT.md)
- Sprint 5.7: [End-To-End Report Trial](SPRINT_5_7_END_TO_END_REPORT_TRIAL.md)

## Explicit Non-Goals

Avoid using Sprint 5 for:

- Production auth or deployment.
- PDF export.
- Perfect cartography.
- Advanced audit UI.
- Full GPT rollout.
- All-source acquisition completeness.
- Live restricted-source workflows.
- Broad UI redesign.
- Making the app trail-specific.
- Blindly implementing everything from the example report.

## Success Statement

At the end of this sprint, Review Assist should be able to say:

> We screened the source warehouse, identified what matters, explained what is missing, recommended what belongs in the report, let the human decide, and drafted only the approved/source-backed pieces within strict policy.

That is the bridge from artifact generator to actual Review Assist.
