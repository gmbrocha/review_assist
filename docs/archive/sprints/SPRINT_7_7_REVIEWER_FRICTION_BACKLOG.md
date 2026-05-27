# Sprint 7.7: Reviewer Friction Backlog

## Status

Complete.

Populated from Sprint 7.4 intake, Sprint 7.5 smoke testing, and Sprint 7.6 output review. No product code, source truth, generated artifacts, review gates, export semantics, or GPT behavior was changed by this backlog pass.

## Purpose

Turn fresh-project testing findings into an actionable, triaged backlog that drives the next sprint planning cycle.

This subunit collects, categorizes, and prioritizes all findings from the Sprint 7 trial and UI review work into a structured backlog.

## Priority Levels

| Priority | Meaning |
|---|---|
| P0 | Blocks real reviewer testing - must fix before trial continues |
| P1 | Confusing or trust-reducing - degrades reviewer confidence |
| P2 | Useful polish or source expansion - improves usability |
| P3 | Later product or deployment hardening - non-urgent |

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

## Backlog

| Priority | Category | Finding | Source / location | Suggested direction | Origin |
|---|---|---|---|---|---|
| P1 | Export Polish | Default preview report body includes absolute project-local paths and package internals in "Generated Package Contents." | `projects/test_project_2/exports/environmental_constraints_report.md` lines 1067-1072. | Move package internals to manifest/advanced diagnostics or an explicitly developer-only appendix; keep default report body free of local paths. | 7.6 |
| P1 | Export Polish | Report body includes raw table IDs, figure IDs, source IDs, and "Map file" implementation lines. | Markdown body throughout; examples include `table-wetlands-waterbodies`, `figure-wetlands-waterbodies`, and raw `Source refs:` lines. | Render human source labels in report prose; keep IDs in manifest/advanced/debug output. | 7.6 |
| P1 | Report Inclusion And Discernment Issues | Same wetlands/waterbodies table and figure are repeated across section rollup and comparison-unit child subsections. | Wetlands/waterbodies export body around lines 182-400. | Render shared table/figure once at the rollup or first relevant location; child subsections should reference it without re-embedding unless explicitly needed. | 7.6 |
| P1 | UI Language | Some deterministic section prose still reads like evidence/package metadata instead of report prose. | Export body phrases include "Mapped-source evidence", "The evidence package includes", "bounded row(s)", "artifact limitations", and "Related figure artifact(s)." | Tighten deterministic section templates/export filtering so report body uses reviewer-facing environmental report language. | 7.6 |
| P1 | Manual Material Workflow | Manual/restricted items block export correctly, but reviewer actions are not specific enough per item. | Manual items include PEL relationship, protected species, archaeological sites, hazardous materials report, and agency consultation letters. | Add concise item-specific action guidance: what the reviewer must supply, where it will appear, and what happens if it remains unavailable. | 7.5, 7.6 |
| P1 | Export Polish | Preview package does not clearly distinguish the two accepted items from the remaining unreviewed preview items in the body. | Manifest records counts, but body largely relies on the internal preview caveat. | Keep preview warning, but add a compact review-state summary or visual marker strategy for preview exports only. | 7.6 |
| P2 | Missing Source Explanations | Census demographic tables and census tract figure are visible stubs, but the wording can read like broken output rather than deferred source setup. | Demographic Characteristics section and export QA `figure-census-tracts` warning. | Explain Census/TIGER/ACS setup as deferred/unavailable in plain language and point to required setup without overloading the report body. | 7.5, 7.6 |
| P2 | Figure Readability | Fourteen figure assets are present, but many are narrow/tall portrait maps and still need reviewer visual inspection for readability at DOCX size. | Export assets under `projects/test_project_2/exports/assets/figures/`. | Add a figure QA checklist or thumbnail review pass focused on size, labels, legend width, and map extent after report-shape cleanup. | 7.6 |
| P2 | Project Setup Flow | Populate logs include many repeated `existing_local_source_preserved` informational warnings. | Sprint 7.4 intake log; populate produced 68 warnings, mostly repeated preservation notices. | Group repeated source-materialization info lines into one summary in reviewer-facing logs while preserving full details in run artifacts. | 7.4, 7.5 |
| P2 | Manual Material Workflow | Attachment stubs include duplicate-looking hazardous-materials and agency-consultation entries. | Attachment section and included attachment IDs in preview export. | Clarify matrix attachment targets versus report attachment sections, or collapse duplicate-looking labels in reviewer-facing output. | 7.6 |
| P2 | Source Warehouse Gaps | Local businesses/economic nodes and some community/socioeconomic content remain deferred or source-limited. | `local-businesses-and-economic-nodes` review item and socioeconomic sections. | Decide whether these should remain explicit manual/deferred stubs or get a source-materialization/source-policy expansion in a future source sprint. | 7.5, 7.6 |
| P3 | GPT Prompt And Style Issues | GPT was intentionally skipped in Sprint 7.5, so real-project GPT tone and safety were not evaluated. | Sprint 7.5 smoke log. | Plan a later constrained GPT spot-check after deterministic/export body language is cleaner. | 7.5 |
| P3 | Export Polish | DOCX/Markdown report layout can be further polished after content-shape issues are addressed. | Preview DOCX has 685 paragraphs, 8 tables, and 26 inline shapes. | Defer richer DOCX layout/appendix presentation until report body content and inclusion are calmer. | 7.6 |

## Triage Summary

- P0: none.
- P1: six items, all suitable for the next sprint planning cycle rather than emergency patching.
- P2: five items, mostly polish/source-clarity improvements.
- P3: two items, later hardening.
- Deferred work propagation: no unresolved P0 was found. P1 items are expected to feed the next sprint planning cycle directly, so no new deferred-work entry was added in this pass.

## Tests

No automated tests are required for this subunit. This is a planning and triage output.

Any P0 fixes applied as part of closing this subunit must include focused regression tests.

## Definition Of Done

- All findings from Sprint 7.4, 7.5, and 7.6 are collected and categorized.
- Every finding has a priority level.
- P0 items are clearly identified; none were found.
- The backlog is structured for direct use in next sprint planning.
- No source truth or generated artifact content was changed by this subunit itself.
