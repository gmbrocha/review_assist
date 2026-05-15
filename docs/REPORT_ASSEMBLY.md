# Report Assembly

This document captures the pipeline for assembling editable pre-review report packages.

A deterministic draft section baseline exists, and the first accepted-content export compiler now writes Markdown plus an export manifest. DOCX remains the next export target after the Markdown path proves ordering, filtering, provenance, and reviewer-state behavior.

## Goal

The system should produce a comprehensive first-pass draft package so the reviewer is not starting from a blank page.

The package may include:

- Structured findings.
- Draft narrative.
- Alternative comparison tables.
- Static map figures.
- Appendix references.
- Source/provenance notes.
- Review status indicators.
- Uncertainty and missing-data flags.

The package remains a pre-review draft.

Report assembly happens after review queue approval. Generated content should not flow directly from analysis or LLM drafting into exports.

## Review-Queue-to-Report Pipeline

Canonical pipeline:

1. Open/create workspace.
2. Add project inputs.
3. Generate project context.
4. Resolve source status set.
5. Build normalized project geometry and run objective constraint analysis from registered source layers.
6. Populate for review.
7. Create review queue items for findings, tables, figures, narrative, caveats, source notes, and missing-data placeholders.
8. Human reviewer edits, accepts, rejects, or marks items for verification.
9. Compile accepted or explicitly included reviewed items.
10. Export editable draft package.

## Section Assembly Pattern

Each report section can be assembled from:

- Section purpose.
- Source summary.
- Methods used.
- Findings by alternative or project area.
- Implication language.
- Map/table references.
- Limitations and uncertainty.
- Reviewer-needed actions.

A section should not be blank simply because data is missing. It can state that source data was unavailable, restricted, not assessed in this pass, or requires reviewer input.

These missing-data statements should be review queue items before they are included in export.

## Current Deterministic Section Baseline

The current CLI can generate draft report section artifacts:

- Command: `review-assist generate-report-sections <project_dir>`
- Output: `projects/<project_id>/drafts/report_sections.json`
- Template config: `config/report_section_templates.json`

The generator creates no-blank-page section drafts from existing structured artifacts:

- Project context.
- Source status.
- Source inventory.
- Draft findings.
- Comparison tables.
- Map manifest when available.
- Validation issues.

Current section drafts follow the example report structure more closely: front matter, executive summary, introduction/study area, methodology/data sources, mapping and analysis procedures, limitations/data gaps, environmental constraints inventory, resource sections, comparison/maps, conclusion/next steps, attachments, and reviewer follow-up. The active provider is deterministic only; the provider boundary is present so a future GenAI drafting provider can be added without replacing the constraint engine.

Resource sections now cite related finding, table, and figure IDs where structured artifacts exist, including source-backed wetlands, hydrography, flood hazard, USFWS critical habitat, and EPA/ECHO regulated facility summaries. Missing or failed source categories still generate caveats rather than unsupported conclusions.

These sections are not final exports. They become `report_section` review queue items and require human review before reviewed-content export.

## Current Markdown Export Baseline

The current CLI can compile reviewed queue items into an editable Markdown package:

- Command: `review-assist export-report <project_dir>`
- Preview command: `review-assist export-report <project_dir> --include-draft`
- Manifest: `projects/<project_id>/exports/export_manifest.json`
- Markdown: `projects/<project_id>/exports/environmental_constraints_report.md`

Default export includes only queue items with `accepted` or `edited` status and export eligibility. `unable_to_verify` items export only when explicitly marked export eligible. Draft, needs-review, needs-verification, and rejected items are skipped.

The `--include-draft` option is for internal preview only. It includes unaccepted non-rejected items and marks the Markdown output as an internal preview, not an external report.

The export manifest records included/skipped item counts, status/type counts, unresolved required source gaps, missing accepted sections, and missing accepted maps. Maps and tables are referenced by path/artifact metadata in this slice; binary embedding and DOCX formatting are deferred.

## Narrative Sources

Draft narrative should be grounded in:

- Structured findings.
- Source metadata.
- Constraint result records, with legacy spatial relationship records only as fallback context.
- Reviewer-supplied notes.
- Report taxonomy.
- Approved limitation language.

Draft narrative should not be generated directly from raw maps alone. The current deterministic section baseline may reference map manifest figure IDs and source refs, but maps do not create unsupported source facts.

## Comparison Matrices

Alternative comparison tables should describe profiles rather than rank alternatives.

Possible columns:

- Alternative.
- Resource category.
- Finding type.
- Count/length/acreage/distance.
- Review status.
- Implication.
- Uncertainty.
- Source.

Possible matrix values:

- Direct crossing.
- Intersects.
- Within buffer.
- Nearby.
- No mapped conflict identified.
- Source unavailable.
- Requires manual review.
- Unable to verify.

## Appendices

Potential appendices:

- Project maps.
- Hazardous materials report.
- Agency consultation letters.
- Source inventory.
- Finding register.
- Reviewer change log.
- Restricted-source review status summary.

Attachments may be generated, reviewer-provided, or externally authored. The system should not imply that unavailable appendices have been reviewed.

## Citation and Provenance Handling

Every table, map, and narrative finding should be traceable to underlying source records, method records, and review queue item IDs.

Possible citation strategy:

- Short source name in finding/table/map.
- Full source inventory appendix.
- Access date and published date where available.
- Source URL/path.
- Method note for derived measurements.

## Editable Export Concepts

Potential exports:

- Markdown report package.
- DOCX draft report.
- HTML review package.
- XLSX comparison tables.
- PNG/PDF map figures.
- GeoPackage review layers.

DOCX is important because the example deliverable is a Word report. The first implementation path is Markdown plus JSON manifest so the accepted-content assembly rules are testable before adding DOCX dependencies and layout concerns.

Exports should compile accepted or explicitly included reviewed content only. Rejected items remain in the review record but should not export.

## LLM-Assisted Drafting Insertion Points

LLM calls may help:

- Draft section narratives from structured findings.
- Summarize alternative-specific findings.
- Convert implication tags into plain-language planning implications.
- Draft limitations and uncertainty wording.
- Identify contradictory or unsupported draft statements.
- Normalize reviewer notes into structured findings.

LLM calls should receive structured inputs and produce editable outputs. They should not create new source-backed facts.

## Package Manifest

The compiled package manifest includes or should continue to include:

- Project.
- Inputs.
- Source layers.
- Methods run.
- Findings generated.
- Tables generated.
- Figures generated.
- Markdown report path.
- Review status summary.
- Included/skipped queue item summaries.
- Known missing data.
- Generation timestamp.

This manifest should support reproducibility and review.

## Open Questions

- How much formatting must match the example report?
- Should figures be embedded automatically or linked for manual insertion?
- How should reviewer edits round-trip back into structured findings?
- Which appendices are required for the first prototype?
