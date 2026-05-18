# Report Assembly

This document captures the pipeline for assembling editable pre-review report packages.

A deterministic draft section baseline exists, optional GPT section drafting now runs from structured evidence when enabled, and the reviewed-content export compiler writes Markdown, DOCX, and an export manifest after the standard review queue passes the review-complete gate. An internal demo deliverable command can run the current pipeline and create a visibly pre-review package without auto-accepting queue items. A stricter MVP deliverable command runs source preparation first, blocks packages that contain mock/test fixture source evidence or no real source layers, and records whether it produced reviewed output or internal preview output.

Sprint 1.1 added static deliverable and prompt contracts at `config/deliverable_section_matrix.json` and `config/report_generation_prompts.json`, plus validation commands for those contracts. Sprint 2.2 wires the deliverable matrix into exact standard table generation at `projects/<project_id>/deliverable/tables.json`. Sprint 2.3 wires the matrix into exact standard figure generation at `projects/<project_id>/deliverable/figures.json` and evidence package refs. Sprint 3.1 wires the matrix and prompt contract into standard deliverable item generation at `projects/<project_id>/deliverable/deliverable_items.json` and makes the bounded review queue consume that artifact by default. Sprint 3.2 wires the bounded queue into default export gating and package manifest review-gate summaries. Legacy `drafts/report_sections.json` remains available for compatibility/audit context.

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
7. Create matrix-backed deliverable items for sections, dynamic comparison-unit subsections, tables, figures, attachments, caveats, source gaps, and required stubs.
8. Create a bounded review queue with one item per deliverable item.
9. Human reviewer edits, accepts, replaces, declines, or marks items for verification.
10. Compile accepted, edited, replaced, or explicitly export-includable reviewed items.
11. Export editable reviewed package, or use `--include-draft` for internal/pre-review preview only.

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

The active provider is deterministic unless root `.env` enables GPT with `GPT_DRAFTING=1`. When enabled, the OpenAI provider uses `OPENAI_API_KEY` and `OPENAI_INTERPRETER_MODEL`, sends only structured evidence and deterministic baseline copy, and stores provider/model/prompt/schema/input digest/output digest provenance. GPT calls default to two parallel section-drafting workers through `GPT_DRAFTING_WORKERS=2`. Raw source files, geometries, GeoJSON feature dumps, shapefile paths, and root `sources/` paths are withheld from GPT payloads. GPT output remains draft/pre-review content on a standard deliverable item or legacy `report_section` item and is never auto-accepted.

Resource sections now cite related finding, table, and figure IDs where structured artifacts exist, including source-backed wetlands, hydrography, soils/SSURGO map units, flood hazard, USFWS critical habitat, and EPA/ECHO regulated facility summaries. Introduction/study-area/methodology sections reference the project overview figure, the constraints inventory references the combined environmental constraints overview when available, and resource sections reference matching source-context figures. Missing or failed source categories still generate caveats rather than unsupported conclusions.

GPT guardrails reject or flag unknown cited finding/table/figure/source IDs and prohibited recommendation/ranking/scoring/selection/rejection/final-determination/jurisdictional/field-verification language. If GPT is enabled but the API key is missing, the command fails clearly instead of silently pretending GPT ran. If GPT is disabled or `--no-gpt-drafting` is supplied, deterministic sections remain the active path.

These legacy sections are not final exports. The standard review queue now uses matrix-backed deliverable items; legacy `report_section` items remain available for compatibility/audit workflows and still require human review before any reviewed-content export.

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

Sprint 2.3 evidence also includes deliverable table refs, deliverable figure refs, compact row summaries, figure availability/stub status, comparison-unit summaries, compact source-backed constraint summaries, source-gap status, validation issue codes, and raw artifact paths. The GPT-bound evidence remains compact: no full geometries, no raw feature dumps, and no root `sources/` paths.

## Deliverable Tables

The current CLI can generate the exact standard table targets from the canonical deliverable matrix:

- Command: `review-assist generate-deliverable-tables <project_dir>`
- Output: `projects/<project_id>/deliverable/tables.json`

This artifact contains the four matrix table targets: wetlands/waterbodies, FEMA flood zones, income demographics, and demographic composition. It consumes comparison units and `constraints/comparison_unit_constraints.json`; raw `constraint_results.json` and broad `tables/comparison_tables.json` remain evidence/backward-compatible artifacts rather than standard deliverable rows.

Unavailable, missing, restricted, manual, failed, unimplemented, or Census-key-missing sources produce explicit stubs with the canonical stub text and review-needed status. Source-backed rows preserve source refs, related comparison-unit constraint IDs, comparison unit IDs, provenance, uncertainty flags, buffer assumptions, and draft review status.

## Deliverable Figures

The current CLI can generate the exact standard figure targets from the canonical deliverable matrix:

- Command: `review-assist generate-deliverable-figures <project_dir>`
- Output: `projects/<project_id>/deliverable/figures.json`
- PNG directory: `projects/<project_id>/maps/figures/`

This artifact contains the 13 matrix main figure targets in matrix order. It consumes comparison units, `constraints/comparison_unit_constraints.json`, source status, and project-area basemap context. Legacy `maps/map_manifest.json` remains a raw evidence/audit artifact and is not replaced.

Unavailable source data or unsupported rendering produces explicit stubs with the canonical stub text and review-needed status. Rendered figures preserve source refs, related comparison-unit constraint IDs, comparison unit IDs, shown-layer summaries, provenance, uncertainty flags, validation issues, and draft review status.

Deliverable figures may use selected MARIS/NAIP `.png`, `.tif`, or `.tiff` sidecars when available. `.sid` paths are provenance only. Restricted archaeology locations are never rendered or exposed; restricted cultural status is represented by `restricted_source_not_mapped`.

## Deliverable Items

The current CLI can generate the standard reviewable deliverable item layer from the canonical deliverable matrix:

- Command: `review-assist generate-deliverable-items <project_dir>`
- Output: `projects/<project_id>/deliverable/deliverable_items.json`

This artifact contains static section/front-matter/attachment-section targets, one dynamic wetlands/waterbodies child section per comparison unit, the four deliverable table targets, the 13 deliverable figure targets, and the three required attachment targets. Stable `deliverable_item_id` / `target_id` values are used as the standard review queue item IDs.

Deliverable items carry matrix target metadata, prompt key and prompt-contract constraints, source refs, table/figure/attachment refs, comparison-unit IDs, compact source-gap and upstream validation summaries, provenance, uncertainty flags, stub state, review status, and export eligibility. Required missing or unimplemented content uses the canonical stub text rather than unsupported narrative.

GPT-enabled deliverable item drafting receives only structured evidence, prompt metadata, and matrix target context. Raw geometries, full feature dumps, and root `sources/` paths remain excluded from GPT-bound payloads.

## Current Export Baseline

The current CLI can compile reviewed queue items into editable Markdown and DOCX packages:

- Command: `review-assist export-report <project_dir>`
- Preview command: `review-assist export-report <project_dir> --include-draft`
- Format option: `review-assist export-report <project_dir> --format markdown|docx|both`
- Manifest: `projects/<project_id>/exports/export_manifest.json`
- Markdown: `projects/<project_id>/exports/environmental_constraints_report.md`
- DOCX: `projects/<project_id>/exports/environmental_constraints_report.docx`

Default export is review-gated and fails before writing a reviewed-content package if any standard matrix-backed deliverable item is still `draft`, `needs_review`, `needs_verification`, `replaced` without replacement content, or `unable_to_verify` without explicit export eligibility and usable content. Gate failures are structured in CLI JSON mode and actionable in text mode, including unreviewed counts and a preview of blocking item IDs.

When the gate passes, default export includes `accepted` generated content, `edited` reviewer content when present, `replaced` replacement content, and explicitly export-eligible `unable_to_verify` content. `edited` items without edited content fall back to generated content with a warning. `declined` and legacy `rejected` items are omitted.

The `--include-draft` option is for internal preview only. It includes unaccepted non-declined items and marks the Markdown/DOCX output as an internal preview, not an external report.

The export manifest records review gate status, preview mode, total/terminal/unreviewed/declined review item counts, included/skipped item counts, matrix version, expected/actual deliverable item counts, included table/figure/attachment IDs, stub counts, unreviewed-item previews, status/type counts, unresolved required source gaps, missing accepted sections, missing accepted maps, output paths, included map paths, copied figure asset paths, generated package contents, and `mvp_quality` counts. DOCX export supports the bounded queue item types with a report-like MVP structure: title page, internal-preview notice/header/footer for draft exports, major-section page breaks, front-matter figure/table/attachment lists, duplicate section-heading cleanup, inline referenced table/figure rendering, figure captions/source notes/method notes, placeholders when referenced evidence is missing, source refs, uncertainty flags, caveats, and package contents.

Export and deliverable manifests include `data_lineage` counts and records, the evidence package path, and GPT drafting status/counts when GPT-backed sections are present. The lineage model distinguishes project input geometry, registered local layers, user-provided input layers, downloaded public source layers, manual/gated/missing stubs, and test/mock records. Generated source-gap caveats are stubs, not source-backed records.

DOCX and Markdown exports include `Real Data Used` and `Stubs / Manual Review Needed` sections. These sections exist so a reviewer can tell which content came from real project/source material and which content is an honest placeholder for unavailable, manual, gated, failed, or reviewer-needed data.

## Demo Deliverable Package

The current CLI can create a client-showable internal preview package without touching the UI:

- Command: `review-assist build-demo-deliverable <project_dir>`
- Optional source acquisition: `--prepare-sources`
- Optional source inclusion: `--include-optional-sources`, only with `--prepare-sources`
- Format option: `--format markdown|docx|both`
- Manifest: `projects/<project_id>/exports/deliverable_package_manifest.json`

This command runs `populate-for-review`, then exports `--include-draft` content in the requested format. It does not accept, edit, or otherwise mutate review item statuses. Its package manifest records the review-gate preview summary. The output exists to demonstrate the report shape and should not be treated as reviewed deliverable content.

## Real-Data MVP Deliverable Package

The current CLI can create a stricter MVP package intended to prove that the deliverable can be populated by real available data rather than mock records:

- Command: `review-assist build-mvp-deliverable <project_dir>`
- Optional source inclusion: `--include-optional-sources`
- Format option: `--format markdown|docx|both`
- Guardrail option: `--fail-on-no-downloaded-sources` / `--no-fail-on-no-downloaded-sources`
- Manifest: `projects/<project_id>/exports/deliverable_package_manifest.json`

This command runs `populate-for-review --prepare-sources`, then attempts default reviewed export if the standard queue is already review-complete. If the gate blocks, it falls back to `--include-draft` internal preview. It does not mutate review item statuses or auto-accept anything.

By default, MVP export fails when no downloaded, provided, or registered real source layer is available. It also fails when included export content contains `test_fixture` provenance. The command may include clearly labeled stubs for missing, manual, gated, failed, or reviewer-needed categories, but those stubs are separated from source-backed evidence in the manifest and exported report. The deliverable manifest carries review gate fields and `mvp_quality` so reviewers can see preview/reviewed status, real-source counts, source-backed constraint counts, copied figure assets, inline-rendered tables/figures, placeholder counts, unresolved source categories, GPT section counts, and warning counts.

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

Exports should compile accepted or explicitly included reviewed content only. Declined items remain in the review record but should not export.

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
- Review gate status, preview state, and unreviewed item preview.
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
