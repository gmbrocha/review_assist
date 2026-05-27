# Report Assembly

This document captures the pipeline for assembling editable pre-review report packages.

A deterministic draft section baseline exists, explicit GPT Interpretive Assist can draft cached source-backed review candidates when invoked, and the reviewed-content export compiler writes Markdown, DOCX, and an export manifest after the standard review queue passes the review-complete gate. An internal demo deliverable command can run the current pipeline and create a visibly pre-review package without auto-accepting queue items. A stricter MVP deliverable command runs source preparation first, blocks packages that contain mock/test fixture source evidence or no real source layers, and records whether it produced reviewed output or internal preview output.

Sprint 1.1 added static deliverable and prompt contracts at `config/deliverable_section_matrix.json` and `config/report_generation_prompts.json`, plus validation commands for those contracts. Sprint 2.2 wires the deliverable matrix into exact standard table generation at `projects/<project_id>/deliverable/tables.json`. Sprint 2.3 wires the matrix into exact standard figure generation at `projects/<project_id>/deliverable/figures.json` and evidence package refs. Sprint 3.1 wires the matrix and prompt contract into standard deliverable item generation at `projects/<project_id>/deliverable/deliverable_items.json` and makes the bounded review queue consume that artifact by default. Sprint 3.2 wires the bounded queue into default export gating and package manifest review-gate summaries. Legacy `drafts/report_sections.json` remains available for compatibility/audit context.

`config/report_section_policy.json` is the canonical section policy layer for report interpretation. It defines each section's extent scope, visual extent class, comparison-unit expansion policy, evidence pattern, caveats, prohibited claims, and GPT readiness for deterministic drafting and explicit GPT Interpretive Assist.

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
- Legacy GPT opt-in: `review-assist generate-report-sections <project_dir> --gpt-drafting`
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

The legacy report-section generator remains deterministic unless explicitly run with `--gpt-drafting` and the GPT environment gate is enabled. Standard populate, web Create Review Queue, and developer reset are deterministic by default and do not call GPT from `GPT_DRAFTING` alone.

Resource sections now cite related finding, table, and figure IDs where structured artifacts exist, including source-backed wetlands, hydrography, soils/SSURGO map units, flood hazard, USFWS critical habitat, and EPA/ECHO regulated facility summaries. Introduction/study-area/methodology sections reference the project overview figure, the constraints inventory references the combined environmental constraints overview when available, and resource sections reference matching source-context figures. Missing or failed source categories still generate caveats rather than unsupported conclusions.

GPT guardrails reject or flag unknown cited finding/table/figure/source IDs and prohibited recommendation/ranking/scoring/selection/rejection/final-determination/jurisdictional/field-verification language. They also reject process labels, style-context citation, example/style fact leakage, raw rows/coordinates/GeoJSON/source paths, required-caveat omissions, section-policy prohibited claims, public cultural context overclaims, context-only direct-impact wording, no-effect/no-impact/final-impact language, permit required/not-required conclusions, cultural eligibility/effect/clearance claims, contamination cleanup/liability conclusions, access/mitigation/construction commitments, and demographic impact conclusions. If GPT is requested but the API key is missing, the command fails clearly instead of silently pretending GPT ran. If GPT is disabled or `--no-gpt-drafting` is supplied, deterministic sections remain the active path.

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

Report-facing and GPT-facing caveats use effective source status. Current local/materialized source availability and logical-rollup satisfaction are reconciled before caveats are copied into deliverable tables, evidence, deliverable items, review queue records, or GPT payloads. Historical source-acquisition attempts remain in acquisition/data-lineage artifacts for debugging, but a stale failed download should not become prose-facing `source_not_downloaded` when current evidence is sourced from a valid local/materialized layer.

Sprint 2.3 evidence also includes deliverable table refs, deliverable figure refs, compact row summaries, figure availability/stub status, comparison-unit summaries, compact source-backed constraint summaries, source-gap status, validation issue codes, and raw artifact paths. The GPT-bound evidence remains compact: no full geometries, no raw feature dumps, and no root `sources/` paths.

Evidence and downstream deliverable artifacts now preserve extent-policy metadata. Current fields distinguish the query extent actually used, the analysis or interpretation extent type, table/list/figure extent type, render extent type, whether render expansion is presentation-only, and a source-selection reason. Deliverable table and figure summaries also carry their table/figure policy metadata so evidence, review, GPT payloads, and export summaries can see interpretation scope, allowed source categories, preview caps, and presentation-only render behavior. This allows report prose and reviewer metadata to distinguish direct project-area evidence from nearby/community context, watershed context, county/regional context, and map-collar rendering. This metadata does not create new query buffers or broaden existing source materialization by itself.

Current named context extents are policy labels unless a source-query implementation explicitly exists. Nearby/community, watershed/subwatershed, and county/regional labels constrain wording and review metadata; they do not prove that a separate context query was run. Render extent, basemap materialization extent, and presentation collar extent are presentation-only and must not be described as source evidence, direct intersection, project footprint, or project impact.

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

This artifact contains the 15 matrix main figure targets in matrix order, including split regulated-facility figures for hazardous/regulated sites, water-discharge/waste facilities, and oil/gas wells. It consumes comparison units, `constraints/comparison_unit_constraints.json`, source status, and project-area basemap context. Legacy `maps/map_manifest.json` remains a raw evidence/audit artifact and is not replaced.

Unavailable source data or unsupported rendering produces explicit stubs with the canonical stub text and review-needed status. Rendered figures preserve source refs, related comparison-unit constraint IDs, comparison unit IDs, shown-layer summaries, provenance, uncertainty flags, validation issues, and draft review status. Report-ready generated PNGs are map panels only: they include the map, source layers, legend, north arrow, and scale bar, but do not embed captions, source notes, method notes, review/process instructions, or report-facing figure titles. Captions, source notes, and method notes remain editable figure metadata and are written below/near the figure as normal Markdown/DOCX text during export.

Deliverable figures may use selected MARIS/NAIP `.png`, `.jpg`, `.jpeg`, `.tif`, or `.tiff` sidecars when available, with project-local NAIP render assets preferred. Real MrSID `.sid`/`.sdw` payloads are not active Review Assist render assets. Restricted archaeology locations are never rendered or exposed; restricted cultural status is represented by `restricted_source_not_mapped`.

The existing public water supply wells and streams/impaired-waters figure targets can render project-local materialized MDEQ/MARIS public water supply wells, NHD hydrography layers, MDEQ 303(d)/TMDL water-quality layers, and materialized USGS WBD HUC-12 watershed/subwatershed context when those source IDs are registered and available. Public water supply wells remain mapped context only. The streams/impaired-waters figure can show available NHD and 303(d)/TMDL layers without pretending watershed context exists; when HUC-12 context is not materialized, the missing watershed/subwatershed layer remains an explicit limitation.

## Deliverable Items

The current CLI can generate the standard reviewable deliverable item layer from the canonical deliverable matrix:

- Command: `review-assist generate-deliverable-items <project_dir>`
- Output: `projects/<project_id>/deliverable/deliverable_items.json`

This artifact contains static section/front-matter/attachment-section targets, one dynamic wetlands/waterbodies child section per comparison unit, the four deliverable table targets, the 15 deliverable figure targets, and the three required attachment targets. Stable `deliverable_item_id` / `target_id` values are used as the standard review queue item IDs.

Deliverable items carry matrix target metadata, prompt key and prompt-contract constraints, source refs, table/figure/attachment refs, evidence refs, comparison-unit IDs, extent-policy fields, render-policy fields, manual-material metadata, table/figure policy metadata, compact source-gap and upstream validation summaries, provenance, uncertainty flags, stub state, review status, and export eligibility. Source-backed section_text items use deterministic report-style candidate prose for the standard review queue, including table/figure/source references and screening-level limitations where available. The standard review UI displays related table, figure, evidence refs, render policy, and manual-material status for source-backed or reviewer-supplied section_text items so supporting artifacts and policy gates are visible outside the prose body. Required missing or unimplemented content uses the canonical stub text and explicit source/data-gap wording rather than unsupported narrative.

Umbrella section_text items such as Environmental Constraints Inventory, Natural and Ecological Resources, Community Resources, Utility and Infrastructure Considerations, and Socioeconomic and Business Considerations are structural orientation items. They summarize the report categories and direct reviewers to child sections/items for detailed limitations. They do not inherit every child source gap, figure-render warning, stubbed table warning, restricted-source note, or basemap/presentation warning as parent body text or parent validation issues.

Heading-only section targets are separate from reviewable section_text items. `natural-and-ecological-resources` is currently a `structural_heading`: it is emitted in preview and reviewed exports from the matrix/policy outline, but it does not create a deliverable item, review queue item, source/evidence refs, candidate body text, or review-gate requirement. Child subsections under the heading remain normal reviewable items.

Mechanical front matter is deterministic. The standard List of Figures and List of Tables review items are generated from the current `deliverable/figures.json` and `deliverable/tables.json` artifacts in report order, not from GPT and not from hardcoded labels. Preview exports list the figure/table review items included by preview mode; reviewed exports list only figure/table items that pass the reviewed-content export gate.

Study Area is also deterministic project-context content. It is supported by submitted project geometry, comparison units, project-area analysis bounds, county context when available, and basemap/NAIP imagery as visual context only. Missing optional or terms-limited imagery, including Google Earth visual review context, should not convert Study Area into a source/data-gap placeholder when project geometry and context exist.

Render-policy metadata records `include_body`, `table_figure_only`, `attachment_status`, `needs_reviewer_decision`, `blocked_missing_source`, `blocked_manual_or_restricted_source`, `custom_project_required`, or `audit_only`, with destination, reason, activation/review policy, comparison-unit expansion policy, and report-body eligibility. The reviewer UI presents these as report roles such as Report body, Table/Figure support, Attachment/support, Reviewer decision needed, or Source/status review rather than raw enum values. PEL remains a conditional/manual reviewer-supplied item. Wetlands/waterbodies keep comparison-unit narrative child review items. Table-only, manual/restricted, deferred, or missing-source generated placeholders stay review-visible without becoming normal report-body prose by default.

Manual-material metadata records whether a review item is source-backed generated content, manual-required text, reviewer-supplied content, restricted reviewer-supplied material, optional absent material, deferred source work, unable-to-verify content, or not a manual-material item. The first implementation is metadata and review/export gating only: reviewer notes remain internal, existing edited/replacement content fields provide reviewer-supplied body text, and the existing figure caption/replacement flow remains the only upload-style surface.

GPT-enabled deliverable item drafting receives only structured evidence, prompt metadata, matrix target context, extent-policy labels, and reviewer-facing related labels for tables, figures, and sources. Raw geometries, full feature dumps, and root `sources/` paths remain excluded from GPT-bound payloads. GPT output is rejected if it cites unknown refs, prints internal table/figure/source IDs in report-facing prose, uses prohibited recommendation/determination language, copies review/process or pipeline/provenance labels such as "draft review candidate", "pre-review", "reviewer verification", "reviewer focus", "related table status", or project-local layer clipping details into export-facing content, or upgrades context-only extent evidence into direct project-impact language.

## GPT Interpretive Assist

GPT Interpretive Assist is the explicit standard-queue GPT path:

- CLI: `review-assist draft-section-candidates <project_dir> --provider gpt`.
- UI: Overview toggle `GPT Interpretive Assist`, then explicit `Generate GPT Drafts`.

Turning the UI toggle on does not call GPT. Page load, overview refresh, Create Review Queue, reset, and default populate do not call GPT. Dry runs report eligible/planned sections without API calls.

The service drafts only eligible source-backed `section_text` items by default. Front matter, final conclusion, table items, figure items, attachments, manual/reviewer-supplied sections, restricted/manual source placeholders, body-ineligible render-policy items, P2/missing-source stubs, and presentation-only collar/render content are ineligible by default. Existing human-reviewed terminal items are preserved.

Inputs include section policy, current project evidence, extent metadata, allowed/prohibited wording, source/table/figure refs, compact evidence summaries, source gaps/limitations, and `config/report_style_context/environmental_constraints_report_style.md`. The style context is non-evidence style guidance only. It must not be cited, and example-report facts, trail-specific assumptions, or PEL-specific assumptions must not be imported into project drafts.

Accepted GPT output updates `generated_content` only as an unaccepted review candidate, sets status to `needs_review`, sets `export_eligible` false, records GPT provenance, and keeps the export gate intact. Rejected GPT output is recorded in rejected run/cache metadata without replacing the last accepted cache entry, and deterministic content remains in place.

Drafts are cached under `projects/<project_id>/drafts/gpt_interpretive_assist_cache.json` by evidence payload hash, section-policy hash, prompt-contract hash, style-context hash, prompt version, and model. The default run skips current GPT drafts and reuses matching cached accepted output unless `--force-refresh` is supplied. Run/provenance metadata records token usage when the provider reports it.

## Developer Review Queue Reset

For local manual testing, a developer-only reset command is available:

- Command: `review-assist reset-review-queue <project_dir> --yes`
- Dry run: `review-assist reset-review-queue <project_dir> --dry-run`
- Optional export cleanup: `review-assist reset-review-queue <project_dir> --yes --include-exports`

The reset removes generated `deliverable/deliverable_items.json` and `review_queue/review_queue.json`, then reruns deterministic local artifact generation before rebuilding the standard queue. It refreshes current input classification, project geometry, project area, comparison units, source status, source inventory, constraints, comparison-unit constraints, draft findings, comparison tables, deliverable tables, deliverable figures, map manifest, evidence package, deterministic report sections, deliverable items, and review queue. This keeps reset-created section/table/figure review items tied to current local inputs and registered source layers rather than stale upstream artifacts.

The reset does not acquire sources, materialize local warehouse sources, materialize NAIP basemaps, run GPT drafting, delete project setup, delete project-local source layers, or reorganize source data. `--include-exports` additionally clears Markdown/DOCX/package outputs so stale preview/reviewed exports do not remain visible after the review artifacts are refreshed. The command is intended for POC testing and stale-artifact cleanup, not production review-state migration.

## Current Export Baseline

The current CLI can compile reviewed queue items into editable Markdown and DOCX packages:

- Command: `review-assist export-report <project_dir>`
- Preview command: `review-assist export-report <project_dir> --include-draft`
- Format option: `review-assist export-report <project_dir> --format markdown|docx|both`
- Manifest: `projects/<project_id>/exports/export_manifest.json`
- Markdown: `projects/<project_id>/exports/environmental_constraints_report.md`
- DOCX: `projects/<project_id>/exports/environmental_constraints_report.docx`

Default export is review-gated and fails before writing a reviewed-content package if any standard matrix-backed deliverable item is still `draft`, `needs_review`, `needs_verification`, `replaced` without replacement content, or `unable_to_verify` without explicit export eligibility and usable content. Gate failures are structured in CLI JSON mode and actionable in text mode, including unreviewed counts and a preview of blocking item IDs.

After the review gate passes, default reviewed export runs policy-aware export QA before writing new reviewed Markdown/DOCX outputs. Blocking QA errors include unresolved blocking review state, manual/reviewer-supplied body content exported from generated placeholders, unknown or disallowed source/table/figure refs, missing required caveat metadata, blank required table cells, missing required figure metadata or image files unless the item is explicitly reviewed as a placeholder/status item, table/figure ID inconsistencies, and severe compactness/final-verification errors. Reviewer override with a required reason is not implemented; it remains deferred.

For reviewed figure items, export image selection preserves the existing review gate and then resolves the package image path in this order: explicit reviewer replacement image, approved figure version, latest regenerated figure version, then the current generated/autogenerated image. Selected-version metadata is recorded on exported figure items and copied figure assets. Missing approved or regenerated version artifacts block reviewed export with QA issues instead of silently falling back to stale generated imagery.

When the gate passes, default export includes `accepted` generated content, `edited` reviewer content when present, `replaced` replacement content, and explicitly export-eligible `unable_to_verify` content for report-body eligible items. Body-ineligible generated placeholders are skipped with policy render reasons unless a reviewer supplies edited or replacement content and explicitly marks the item export-eligible. Manual-required and restricted placeholders do not become source-backed findings by being accepted; reviewer-supplied edited/replacement content is required for normal body export when policy marks the item body-ineligible. Attachment/supporting-document items may export reviewed status/limitation text according to attachment policy, but the export must not imply that absent documents exist. Figure review items use the reviewed caption and replacement image metadata when present instead of treating figure replacements as generic narrative body text; replacement figures keep the generated caption when no caption edit was supplied. Figure captions, source notes, and method notes are exported as editable Markdown/DOCX text outside the image. `edited` items without edited content fall back to generated content with a warning. `declined` and legacy `rejected` items are omitted.

The `--include-draft` option is for internal preview only. It includes unaccepted non-declined items and marks the Markdown/DOCX output as an internal preview, not an external report. Preview export records export QA status and issues, including a preview-bypass warning, but it does not apply the reviewed-export hard block.

The export manifest records review gate status, preview mode, export QA status/counts/issues, total/terminal/unreviewed/declined review item counts, included/skipped item counts, matrix version, expected/actual deliverable item counts, included table/figure/attachment IDs, render-policy fields and skipped policy reasons, manual-material status, stub counts, compactness budget counts, final verification status, unreviewed-item previews, status/type counts, unresolved required source gaps, missing accepted sections, missing accepted maps, output paths, included map paths, copied figure asset paths, generated package contents, and `mvp_quality` counts. DOCX export supports the bounded queue item types with a report-like editable structure: letter page setup, one-inch margins, core Word styles, title page metadata, internal-preview notice/header/footer for draft exports, major-section page breaks, matrix-ordered headings, front-matter figure/table/attachment lists, duplicate section-heading cleanup, inline referenced table/figure rendering, bounded editable table previews, figure captions/source notes/method notes, placeholders when referenced evidence is missing, source refs, uncertainty flags, caveats, and package contents.

Export and deliverable manifests include `data_lineage` counts and records, the evidence package path, and GPT drafting status/counts when GPT-backed sections are present. The lineage model distinguishes project input geometry, registered local layers, user-provided input layers, downloaded public source layers, manual/gated/missing stubs, and test/mock records. Generated source-gap caveats are stubs, not source-backed records.

Report-facing table rendering uses the table policy row-preview cap in Markdown/DOCX body output and leaves full table detail in the table artifact. The current compact policy cap is five body-preview rows with overflow to the table artifact. Deliverable item generation records a validation warning when generated section content exceeds the compactness budget so long draft prose cannot silently enter the standard deliverable path. Export final verification also records DOCX readability, raw legacy item presence, table preview caps, expected versus actual deliverable item counts, and over-budget body content warnings for later audit/UI consumption.

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

DOCX is important because the example deliverable is a Word report. The current DOCX baseline preserves editability, applies durable report styling, renders referenced evidence deliberately, and stays bounded by the compact deliverable contract. It is not a PDF renderer or a web/UI workflow.

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
