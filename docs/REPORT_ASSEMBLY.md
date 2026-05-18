# Report Assembly

This document captures the pipeline for assembling editable pre-review report packages.

A deterministic draft section baseline exists, optional GPT section drafting now runs from structured evidence when enabled, and the accepted-content export compiler writes Markdown, DOCX, and an export manifest. An internal demo deliverable command can run the current pipeline and create a visibly pre-review package without auto-accepting queue items. A stricter MVP deliverable command runs source preparation first and blocks client-facing packages that contain mock/test fixture source evidence or no real source layers.

Sprint 1.1 added static deliverable and prompt contracts at `config/deliverable_section_matrix.json` and `config/report_generation_prompts.json`, plus validation commands for those contracts. These configs define the future canonical report shape, but current report section generation still uses the existing report section templates until later sprint work wires the new matrix into generation.

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

## Current Section Baseline

The current CLI can generate draft report section artifacts:

- Command: `review-assist generate-report-sections <project_dir>`
- Deterministic override: `review-assist generate-report-sections <project_dir> --no-gpt-drafting`
- Output: `projects/<project_id>/drafts/report_sections.json`
- Template config: `config/report_section_templates.json`

The generator creates no-blank-page section drafts from existing structured artifacts:

- Project context.
- Source status.
- Source inventory.
- Draft findings.
- Comparison tables.
- Map manifest when available.
- Evidence package when available or generated.
- Validation issues.

Current section drafts follow the example report structure more closely: front matter, executive summary, introduction/study area, methodology/data sources, mapping and analysis procedures, limitations/data gaps, environmental constraints inventory, resource sections, comparison/maps, conclusion/next steps, attachments, and reviewer follow-up.

The active provider is deterministic unless root `.env` enables GPT with `GPT_DRAFTING=1`. When enabled, the OpenAI provider uses `OPENAI_API_KEY` and `OPENAI_INTERPRETER_MODEL`, sends only structured evidence and deterministic baseline copy, and stores provider/model/prompt/schema/input digest/output digest provenance. GPT calls default to two parallel section-drafting workers through `GPT_DRAFTING_WORKERS=2`. Raw source files, geometries, GeoJSON feature dumps, shapefile paths, and root `sources/` paths are withheld from GPT payloads. GPT output remains a `report_section` review queue item and is never auto-accepted.

Resource sections now cite related finding, table, and figure IDs where structured artifacts exist, including source-backed wetlands, hydrography, soils/SSURGO map units, flood hazard, USFWS critical habitat, and EPA/ECHO regulated facility summaries. Introduction/study-area/methodology sections reference the project overview figure, the constraints inventory references the combined environmental constraints overview when available, and resource sections reference matching source-context figures. Missing or failed source categories still generate caveats rather than unsupported conclusions.

GPT guardrails reject or flag unknown cited finding/table/figure/source IDs and prohibited recommendation/ranking/scoring/selection/rejection/final-determination/jurisdictional/field-verification language. If GPT is enabled but the API key is missing, the command fails clearly instead of silently pretending GPT ran. If GPT is disabled or `--no-gpt-drafting` is supplied, deterministic sections remain the active path.

These sections are not final exports. They become `report_section` review queue items and require human review before reviewed-content export.

## Evidence Package

The current CLI can build the evidence confidence package used by report drafting:

- Command: `review-assist build-evidence-package <project_dir>`
- Output: `projects/<project_id>/evidence/evidence_package.json`

The evidence package includes data lineage, source acquisition provenance, source status, source inventory refs, source-backed constraint counts, grouped section evidence, table IDs, figure IDs, validation issues, and section-level evidence classes:

- `source_backed`
- `source_available_no_overlap`
- `stub_or_manual`
- `failed_or_missing`
- `test_fixture_blocked`

The evidence package is the bridge between hard GIS/source artifacts and narrative drafting. GPT should read this structured package rather than raw source files, root `sources/` paths, raw geometries, or unbounded prose.

## Current Export Baseline

The current CLI can compile reviewed queue items into editable Markdown and DOCX packages:

- Command: `review-assist export-report <project_dir>`
- Preview command: `review-assist export-report <project_dir> --include-draft`
- Format option: `review-assist export-report <project_dir> --format markdown|docx|both`
- Manifest: `projects/<project_id>/exports/export_manifest.json`
- Markdown: `projects/<project_id>/exports/environmental_constraints_report.md`
- DOCX: `projects/<project_id>/exports/environmental_constraints_report.docx`

Default export includes only queue items with `accepted` or `edited` status and export eligibility. `unable_to_verify` items export only when explicitly marked export eligible. Draft, needs-review, needs-verification, and rejected items are skipped.

The `--include-draft` option is for internal preview only. It includes unaccepted non-rejected items and marks the Markdown/DOCX output as an internal preview, not an external report.

The export manifest records included/skipped item counts, status/type counts, unresolved required source gaps, missing accepted sections, missing accepted maps, output paths, included table ids, included map paths, copied figure asset paths, generated package contents, and `mvp_quality` counts. DOCX export now uses a more report-like MVP structure with a title page, internal-preview notice/header/footer for draft exports, major-section page breaks, front-matter figure/table/attachment lists, duplicate section-heading cleanup, inline referenced table/figure rendering, figure captions/source notes/method notes, placeholders when referenced evidence is missing, source refs, uncertainty flags, caveats, and package contents.

Export and deliverable manifests include `data_lineage` counts and records, the evidence package path, and GPT drafting status/counts when GPT-backed sections are present. The lineage model distinguishes project input geometry, registered local layers, user-provided input layers, downloaded public source layers, manual/gated/missing stubs, and test/mock records. Generated source-gap caveats are stubs, not source-backed records.

DOCX and Markdown exports include `Real Data Used` and `Stubs / Manual Review Needed` sections. These sections exist so a reviewer can tell which content came from real project/source material and which content is an honest placeholder for unavailable, manual, gated, failed, or reviewer-needed data.

## Demo Deliverable Package

The current CLI can create a client-showable internal preview package without touching the UI:

- Command: `review-assist build-demo-deliverable <project_dir>`
- Optional source acquisition: `--prepare-sources`
- Optional source inclusion: `--include-optional-sources`, only with `--prepare-sources`
- Format option: `--format markdown|docx|both`
- Manifest: `projects/<project_id>/exports/deliverable_package_manifest.json`

This command runs `populate-for-review`, then exports `--include-draft` content in the requested format. It does not accept, edit, or otherwise mutate review item statuses. The output exists to demonstrate the report shape and should not be treated as reviewed deliverable content.

## Real-Data MVP Deliverable Package

The current CLI can create a stricter MVP package intended to prove that the deliverable can be populated by real available data rather than mock records:

- Command: `review-assist build-mvp-deliverable <project_dir>`
- Optional source inclusion: `--include-optional-sources`
- Format option: `--format markdown|docx|both`
- Guardrail option: `--fail-on-no-downloaded-sources` / `--no-fail-on-no-downloaded-sources`
- Manifest: `projects/<project_id>/exports/deliverable_package_manifest.json`

This command runs `populate-for-review --prepare-sources`, then exports `--include-draft` content in the requested format. It does not mutate review item statuses or auto-accept anything.

By default, MVP export fails when no downloaded, provided, or registered real source layer is available. It also fails when included export content contains `test_fixture` provenance. The command may include clearly labeled stubs for missing, manual, gated, failed, or reviewer-needed categories, but those stubs are separated from source-backed evidence in the manifest and exported report. The deliverable manifest carries `mvp_quality` so reviewers can see real-source counts, source-backed constraint counts, copied figure assets, inline-rendered tables/figures, placeholder counts, unresolved source categories, GPT section counts, and warning counts.

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

DOCX is important because the example deliverable is a Word report. The current DOCX baseline proves package assembly and editability, renders referenced evidence more deliberately, and is closer to the example report shape, but it is still MVP formatting rather than final template fidelity.

Exports should compile accepted or explicitly included reviewed content only. Rejected items remain in the review record but should not export.

## LLM-Assisted Drafting Insertion Points

LLM calls currently help only with report-section draft copy after deterministic artifacts exist. Future LLM calls may also help:

- Draft section narratives from structured findings.
- Summarize alternative-specific findings.
- Convert implication tags into plain-language planning implications.
- Draft limitations and uncertainty wording.
- Identify contradictory or unsupported draft statements.
- Normalize reviewer notes into structured findings.

LLM calls must receive structured inputs and produce editable outputs. They should not create new source-backed facts, make recommendations, rank alternatives, claim final determinations, or bypass the review queue.

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
- DOCX report path.
- Demo package manifest path, when generated.
- Review status summary.
- Included/skipped queue item summaries.
- Known missing data.
- Data lineage and authenticity counts.
- Evidence package path.
- GPT drafting status, model, counts, and validation warnings when GPT is used.
- Generation timestamp.

This manifest should support reproducibility and review.

## Open Questions

- How much formatting must match the example report?
- How close must the first DOCX layout get to the example report before UI work starts?
- How should reviewer edits round-trip back into structured findings?
- Which appendices are required for the first prototype?
