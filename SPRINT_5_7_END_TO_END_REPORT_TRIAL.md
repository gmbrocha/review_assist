# Sprint 5.7: End-To-End Report Trial

## Status

Parked draft for review. Do not implement until Sprint 5.1 through Sprint 5.6 are accepted enough to trial together.

## Goal

Run the whole loop on the sample project and inspect the actual report workflow.

## Trial Workflow

- Clean reset generated review artifacts.
- Materialize sources.
- Generate tables, figures, and evidence.
- Generate deliverable items and review queue.
- Run inclusion/discernment pass.
- Optionally run GPT on selected approved sections.
- Manually review a subset.
- Export Markdown/DOCX.
- Inspect report shape.

## Review Questions

- Is the report compact?
- Is evidence traceable?
- Does the reviewer decision stack make sense?
- Are missing/deferred/manual sources honest?
- Does export include only reviewed or explicitly allowed content?
- Are current product gaps clear?

## Guardrails

- Use the sample project as verification, not as hardcoded product logic.
- Do not introduce broad UI redesign in this trial.
- Do not treat optional GPT drafting as normal populate/reset behavior.
- Do not commit generated sample-project artifacts unless explicitly approved.

## Definition Of Done

- The app demonstrates the actual workflow.
- The report is compact.
- The evidence is traceable.
- Reviewer decisions are visible and understandable.
- Missing/deferred/manual sources are honest.
- The next actual product gaps are known.
