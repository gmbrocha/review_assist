# Report Assembly

This document captures the likely future pipeline for assembling editable pre-review report packages.

No report assembly implementation exists yet.

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

## Findings-to-Report Pipeline

Likely pipeline:

1. Ingest project inputs.
2. Run deterministic checks.
3. Generate structured findings.
4. Attach implication candidates.
5. Generate comparison tables.
6. Generate maps/figures.
7. Draft narrative sections.
8. Insert source notes and limitations.
9. Compile appendices/reference material.
10. Export editable draft package.
11. Human reviewer edits and finalizes.

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

## Narrative Sources

Draft narrative should be grounded in:

- Structured findings.
- Source metadata.
- Spatial relationship records.
- Reviewer-supplied notes.
- Report taxonomy.
- Approved limitation language.

Draft narrative should not be generated directly from raw maps alone.

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

Every table, map, and narrative finding should be traceable to underlying source records and method records.

Possible citation strategy:

- Short source name in finding/table/map.
- Full source inventory appendix.
- Access date and published date where available.
- Source URL/path.
- Method note for derived measurements.

## Editable Export Concepts

Potential exports:

- DOCX draft report.
- Markdown report package.
- HTML review package.
- XLSX comparison tables.
- PNG/PDF map figures.
- GeoPackage review layers.

DOCX is likely important because the example deliverable is a Word report, but the first implementation path is not decided.

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

A future compiled package should include a manifest describing:

- Project.
- Inputs.
- Source layers.
- Methods run.
- Findings generated.
- Tables generated.
- Figures generated.
- Draft report path.
- Review status summary.
- Known missing data.
- Generation timestamp.

This manifest should support reproducibility and review.

## Open Questions

- Should the first formal report export be DOCX, Markdown, or HTML?
- How much formatting must match the example report?
- Should figures be embedded automatically or linked for manual insertion?
- How should reviewer edits round-trip back into structured findings?
- Which appendices are required for the first prototype?
