# Sprint 7.6: Output Review And Report Shape Check

## Status

Complete.

Implemented as a qualitative output review of the Sprint 7.5 internal preview package from `projects/test_project_2`. No source truth, generated artifact content, review gate, or export behavior was changed.

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

## Reviewed Package

- Workspace: `projects/test_project_2`.
- Preview Markdown: `projects/test_project_2/exports/environmental_constraints_report.md`.
- Preview DOCX: `projects/test_project_2/exports/environmental_constraints_report.docx`.
- Export manifest: `projects/test_project_2/exports/export_manifest.json`.
- Review state: internal preview, `review_gate_status: preview_bypassed`, `export_qa_status: failed`.
- Gate/QA interpretation: expected for this review because only two of 69 review items were terminal and manual/restricted placeholders still need reviewer-supplied content.
- Package size observed: Markdown about 78k characters / 1,086 lines; DOCX about 12 MB with 685 paragraphs, 8 tables, and 26 inline shapes.

## Assessment

### Compactness

- Severity: P1.
- The package is inspectable and bounded, but not yet compact enough for a calm reviewer workflow. The preview includes 70 items, 40 section_text entries, 15 figures, four tables, and six attachments.
- Several section candidates still read like artifact/process summaries rather than report prose. Examples include "Mapped-source evidence", "The evidence package includes", "contains bounded row(s)", "Related figure artifact(s)", and "Render decision: blocked_missing_source."
- Wetlands/waterbodies support content is repeated across the section rollup and each comparison-unit subsection. The same table and figure are rendered repeatedly, which makes the report feel longer than the underlying evidence warrants.
- The "Generated Package Contents" section exposes project-local paths and package internals in the Markdown/DOCX body. This is useful for diagnostics, but should not be in normal reviewer-facing report output.

### Figures

- Severity: P1/P2 mixed.
- Fourteen figure assets were copied into export assets; `figure-census-tracts` remains an explicit placeholder with no image, which is correctly disclosed.
- Figure assets are present but many are narrow/tall portrait maps. They are usable for inspection, but the output review should include visual review before relying on them for a reviewer package.
- Figure captions/source/method notes are present. The cultural figure preserves restricted-source safety by surfacing `restricted_source_not_mapped` rather than rendering restricted archaeological locations.
- Figure IDs and map file paths appear in report body text. Those are useful in advanced/debug views but create a more developer-facing export.

### Tables

- Severity: P1/P2 mixed.
- Wetlands/waterbodies and FEMA table values are present and bounded. FEMA table preview correctly caps the body at five of ten rows and points to the table artifact.
- Census demographic tables are empty stubs. The absence is visible, but the reviewer-facing explanation should be clearer that live Census/TIGER/ACS setup remains deferred rather than broken.
- Internal table IDs such as `table-wetlands-waterbodies` appear in the report body. That is traceable but too implementation-facing for default export text.

### Manual And Reviewer-Supplied Gaps

- Severity: P1.
- Manual/restricted gaps are surfaced and correctly block reviewed export: Relationship with PEL Study, Protected Species and Critical Habitat, Archaeological Sites, and attachment/supporting-document items require reviewer input.
- Guidance is directionally useful but not specific enough for an actual reviewer. The report says reviewer-supplied content is required, but does not give a compact action checklist per manual item.
- Attachment stubs clearly state missing support, but duplicate-looking attachment entries for hazardous materials and agency consultation letters may confuse reviewers.

### Source Limitations

- Severity: P1/P2 mixed.
- Source limitations are honest and visible. Missing, manual, restricted, deferred, and placeholder conditions are not silently omitted.
- Some limitation text is too internal for report prose. Examples include source IDs, source refs, uncertainty flags, render decisions, and artifact status language.
- Source refs appear in many sections as raw IDs. That is useful for auditability but should be moved to manifest/advanced diagnostics or translated into human source labels for default report output.

### Export Shape

- Severity: P1.
- The export is a useful internal preview and correctly marks itself as "INTERNAL PREVIEW / NOT REVIEWED."
- It avoids raw feature dumps and does not expose restricted archaeological locations.
- It still includes internal package contents, absolute local paths, raw source IDs, table/figure IDs, and implementation phrases in body text. Those should not appear in a reviewer-facing package by default.
- Reviewer-accepted items are not visually distinguished from unreviewed preview items in the body beyond the preview caveat and manifest metadata. This is acceptable for internal preview, but reviewed/export-ready packages need cleaner status separation.

## Severity Summary

- P0: none found.
- P1: developer-facing/internal language in report body; repeated rendering of the same table/figure; manual-material guidance not actionable enough; preview/export body includes package paths and raw IDs.
- P2: Census placeholder clarity; figure visual/readability review; source-materialization warning grouping.
- P3: later package polish such as richer report-layout controls and non-preview diagnostic appendix strategy.

## Tests

No automated tests are required for this subunit. This is a qualitative review of generated outputs.

## Definition Of Done

- All check categories were assessed against the real project package from Sprint 7.5.
- Specific findings are recorded per category.
- Findings are categorized by severity for Sprint 7.7 triage.
- No source truth or generated artifact content was changed by this review.
