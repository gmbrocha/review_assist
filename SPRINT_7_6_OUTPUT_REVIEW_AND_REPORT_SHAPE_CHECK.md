# Sprint 7.6: Output Review And Report Shape Check

## Status

Parked draft for review. Do not implement until Sprint 7.5 smoke test is complete.

## Purpose

Inspect whether the generated package from the real project feels like a usable environmental review package, and identify report shape problems before building the friction backlog.

This subunit is an analytical review of outputs, not a code implementation step.

## Check List

Review the generated package against each question below and record findings:

### Compactness

- Does the report stay compact?
- Are sections included or omitted sensibly based on source availability and project context?
- Are any sections that should be omitted still appearing as empty or placeholder stubs?

### Figures

- Are figures readable at the expected output size?
- Do figures cover the correct geographic extent?
- Are relevant features visible and labeled appropriately?
- Are any figures missing that should be present given the project type?

### Tables

- Are table values believable and sourced?
- Are source limitations and caveats noted where relevant?
- Are empty or low-confidence table rows explained rather than silently blank?

### Manual And Reviewer-Supplied Gaps

- Are manual gaps surfaced clearly in the review queue?
- Is the reviewer guidance for manual items specific enough to act on?
- Do manual stubs look like meaningful placeholders rather than generic errors?

### Source Limitations

- Are source limitations honest and specific?
- Are failed, gated, or stale sources identified rather than silently omitted?
- Are buffer assumptions or geographic assumptions stated?

### Export Shape

- Does the export look like something a reviewer could work from?
- Does the package avoid raw data dumps or internal artifact listings?
- Are reviewer-accepted items distinguished from unreviewed items in the export?

## Output

A short written assessment covering each check category with specific findings, not just pass/fail.

This assessment feeds directly into Sprint 7.7 (Reviewer Friction Backlog) and may identify items for `docs/governance/DEFERRED_WORK.md`.

## Tests

No automated tests are required for this subunit. This is a qualitative review of generated outputs.

## Definition Of Done

- All check categories have been assessed against the real project package from Sprint 7.5.
- Specific findings are recorded per category.
- Findings are categorized by severity for Sprint 7.7 triage.
- No source truth or generated artifact content is changed by this review.
