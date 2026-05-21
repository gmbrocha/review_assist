# Deferred Work

This file is mandatory tracked project state for deferred review-assist work. Every sprint planning pass must review it and update it when implementation needs, risks, unresolved questions, or follow-up work are postponed.

Every new sprint planning pass must review:

- this registry
- unresolved review methodology concerns
- known source limitations
- known uncertainty propagation gaps

## How To Record Deferred Items

Each deferred item should include:

- `Deferred item`: short name.
- `Why postponed`: reason it is not handled now.
- `Affected sections/workflows`: report sections, source workflows, review queue behavior, map/export behavior, or methodology affected.
- `Risk if forgotten`: what could become misleading, stale, unsupported, or operationally blocked.
- `Temporary simplification`: whether current outputs are simplified or incomplete because of the deferral.
- `Target sprint/subunit`: future sprint/subunit when known.
- `Status`: open, in progress, resolved, or superseded.

## Active Deferred Items

### Sprint 5 Package Proposals Routed Beyond 5.1 And 5.2

- `Deferred item`: Reusable proposals mined from `pro_review_assist_policy_package_sprint_5/` that require later Sprint 5 subunits before product behavior changes.
- `Why postponed`: Sprint 5.1 only reconciles the canonical policy schema and ledger, and Sprint 5.2 only tightens extent/wording semantics. Source truth changes, section render gating, comparison-unit expansion defaults, caveat/GPT eligibility changes, table/figure target changes, manual material workflows, and export QA changes are intentionally owned by later subunits.
- `Affected sections/workflows`: Wetlands/waterbodies comparison-unit detail defaults, source needs/effective truth mapping, source-gap wording, caveat/prohibited-claim bundles, GPT eligibility, table/figure/attachment alignment, manual/reviewer-supplied materials, export QA.
- `Risk if forgotten`: Package proposals could be partially copied without approval, causing generic Review Assist behavior to inherit example-specific, PEL-specific, trail/corridor-specific, unsupported, or unsafe assumptions.
- `Temporary simplification`: `config/report_section_policy.json` remains canonical; `SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md` records adopted, routed, rejected, and deferred package proposals.
- `Target sprint/subunit`: Sprint 5.3 through Sprint 5.9 as routed in the ledger.
- `Status`: open.

### Census Live Acquisition And MOE Handling

- `Deferred item`: Add live Census TIGER/ACS acquisition and fuller margin-of-error handling beyond registered local Census-like source tables.
- `Why postponed`: Sprint 2.2 implemented demographic deliverable table generation from registered local `census_tiger_acs` source rows and honest stubs when Census data/API setup is unavailable. It did not add a TIGER downloader, live ACS API client, or complete MOE presentation rules.
- `Affected sections/workflows`: Community/socioeconomic source status, source acquisition, source inventory, income demographics table, demographic composition table, report sections that cite demographic tables.
- `Risk if forgotten`: A project without a registered local Census source will correctly show table stubs, but future users may expect `CENSUS_API_KEY` alone to populate ACS rows or may later add ACS values without source year/geography/MOE caveats.
- `Temporary simplification`: Local/mock-ready Census source rows can populate the two demographic deliverable tables; otherwise the tables are explicit review-needed stubs.
- `Target sprint/subunit`: Future source acquisition/data-quality hardening.
- `Status`: open.

### EPA FRS State CSV Secondary Materialization

- `Deferred item`: Add optional CSV-to-point materialization for the EPA `state_single_ms` FRS extract preserved under the `epa_frs_facilities_ms` warehouse raw paths.
- `Why postponed`: The seeded MARIS EPA Facility Registry shapefile is analysis-ready and now materializes as `epa_frs_facilities_ms`; the broader EPA CSV is retained as raw provenance/supplemental context but is not needed to avoid losing the current GIS pipeline shape.
- `Affected sections/workflows`: Regulated facilities source materialization, source inventory/provenance, hazardous materials context.
- `Risk if forgotten`: Reviewers may expect the supplementary CSV to contribute additional FRS rows beyond the materialized shapefile.
- `Temporary simplification`: Default materialization uses the GIS-ready MARIS/EPA FRS shapefile. The CSV remains preserved under `raw/state_single_ms` with manifest notes.
- `Target sprint/subunit`: Future source warehouse/data-quality hardening.
- `Status`: open.

### Source Warehouse Completion And Rollup Semantics

- `Deferred item`: Finish source warehouse/source-status cleanup so broad catalog IDs remain logical downloader/manual rollups and specific seeded source IDs remain the physical warehouse/materialization contract.
- `Why postponed`: Effective source status now reconciles stale acquisition history and broad-rollup caveats before report/GPT-facing artifacts are generated, but the catalog/profile model still has broad rollups and specific physical sources in the same category list.
- `Affected sections/workflows`: Source catalog, source status, source inventory, local materialization, report profile mappings, reviewer source-gap interpretation.
- `Risk if forgotten`: `usgs_nhd_hydrography`, `epa_envirofacts_echo`, or `mdeq_environmental_context` could be mistaken for missing required physical source folders even when specific local layers already satisfy the category.
- `Temporary simplification`: Broad IDs remain visible as downloader/manual details and are marked satisfied for report-facing caveats when specific project-local/materialized layers satisfy the category. A later cleanup can split logical rollup requirements from physical source requirements more explicitly in catalog/profile config.
- `Target sprint/subunit`: Future source warehouse/data-quality hardening.
- `Status`: open.

### Stream Crossing Metric Calibration

- `Deferred item`: Decide whether the wetlands/waterbodies Stream Crossings column should remain a raw canonical NHD flowline crossing-event count or use a more review/engineering-oriented crossing-source contract.
- `Why postponed`: The current stabilization pass scoped the table metric to `usgs_nhd_flowlines`, excluded logical rollups and polygon hydrography context, and added duplicate event-location dedupe. The trails sample still shows many distinct NHD flowline crossing events above the example report counts, so matching the example would require a methodology decision or a supplemental authoritative crossing source rather than a safe source-scoping fix.
- `Affected sections/workflows`: `table-wetlands-waterbodies`, wetlands/waterbodies evidence package summaries, review queue table item, report/export table rendering.
- `Risk if forgotten`: Reviewers may interpret NHD source-feature crossing counts as engineered culvert/bridge crossing counts, or may expect parity with manually prepared example-report counts that appear to use a different counting methodology.
- `Temporary simplification`: The table now counts deterministic, auditable canonical NHD flowline crossing events once per deduped event location and preserves NWI wetland-class counts separately.
- `Target sprint/subunit`: Future wetlands/waterbodies methodology hardening.
- `Status`: open.

### Public And Restricted Cultural Resource Source Split

- `Deferred item`: Add any approved public/coarse cultural context source such as OpenContext/DINAA separately from authorized or reviewer-supplied MDAH archaeological/HSMT records.
- `Why postponed`: Public/coarse archaeological context and restricted MDAH records have different access, sensitivity, precision, and review requirements.
- `Affected sections/workflows`: Cultural/historic source status, source catalog, source warehouse, deliverable sections, review queue caveats, map exposure rules.
- `Risk if forgotten`: Public cultural context could be confused with authoritative restricted records, or sensitive archaeological locations could be exposed improperly.
- `Temporary simplification`: Current public cultural materialization is limited to MARIS public cultural context; MDAH restricted archaeology remains manual/restricted and not rendered.
- `Target sprint/subunit`: Future cultural resources/source governance pass.
- `Status`: open.

### Extent Semantics Query Implementation

- `Deferred item`: Implement separate nearby/community, watershed/subwatershed, county/regional, and other named context queries where needed.
- `Why postponed`: The current passes add extent-policy metadata and Sprint 5.2 wording guardrails only; they do not change query buffers, source clipping, or analysis geometry.
- `Affected sections/workflows`: Constraints, deliverable tables, evidence package, section drafting, review queue, figure metadata, report interpretation labels.
- `Risk if forgotten`: Metadata labels could imply context extents that were not actually queried, or rendered map/collar extents could be misread as analysis extents.
- `Temporary simplification`: Automated evidence remains bounded by current project-area/source materialization behavior unless a future pass explicitly adds named context extents. Nearby/community, watershed/subwatershed, and county/regional labels constrain wording but are not proof that a separate context query was run.
- `Target sprint/subunit`: Future methodology/source-query hardening.
- `Status`: open.

### Basemap And Imagery Rendering Decisions

- `Deferred item`: Decide whether to support MrSID conversion/decoding, additional basemap providers, and production imagery dependencies beyond optional NAIP GeoTIFF sidecars.
- `Why postponed`: The current workflow treats MrSID as provenance only and keeps NAIP sidecar materialization explicit and optional.
- `Affected sections/workflows`: Project area, source status, figure rendering, map generation, source warehouse, web status display.
- `Risk if forgotten`: Reviewers may overread MrSID provenance as a rendered basemap, or local imagery sidecars may remain inconsistent across workspaces.
- `Temporary simplification`: Figures render vector-only or use `.tif`, `.tiff`, or `.png` sidecars when present; no MrSID decoding dependency is required.
- `Target sprint/subunit`: Future cartography/basemap dependency decision.
- `Status`: open.

### Source Acquisition Expansion

- `Deferred item`: Add or harden source acquisition for public water supply wells, RCRA/hazardous materials support sources, Census TIGER/ACS, FEMA variants where needed, parcels/property age, and other report-profile sources.
- `Why postponed`: Current acquisition covers only the implemented explicit downloaders and seeded local warehouse materializers.
- `Affected sections/workflows`: Source gap resolution, source acquisition, source inventory, regulated facilities, community/socioeconomic tables, parcels/property-age context, report caveats.
- `Risk if forgotten`: Required deliverable stubs could be mistaken for implemented source-backed evidence, or users could expect unavailable public sources to populate automatically.
- `Temporary simplification`: Missing/manual/unimplemented sources remain visible as stubs, caveats, or reviewer-needed items.
- `Target sprint/subunit`: Future source acquisition/data-quality hardening.
- `Status`: open.

### Review Queue Freshness And Production Review-State Handling

- `Deferred item`: Add upstream artifact fingerprints or equivalent freshness markers so regenerated candidates and preserved human review state can be distinguished reliably.
- `Why postponed`: The current developer reset clears generated candidates for POC testing but does not implement production review-state migration.
- `Affected sections/workflows`: Deliverable item generation, review queue generation, web review UI, export gating, package manifests.
- `Risk if forgotten`: Stale deliverable items, review queue entries, or preview exports could survive upstream source/table/figure/evidence changes.
- `Temporary simplification`: A developer/test reset now refreshes deterministic upstream review artifacts and rebuilds the queue from current local inputs and registered source layers, but production-grade review-state migration/fingerprinting remains deferred.
- `Target sprint/subunit`: Future review-state/versioning pass.
- `Status`: open.

### GPT-Assisted Drafting Review Workflow Expansion

- `Deferred item`: Add reviewer-controlled GPT rewrite/refine flows, prompt/style tuning, production usage telemetry, and stronger unsupported-fact validation beyond the current explicit GPT Interpretive Assist path.
- `Why postponed`: Current GPT behavior is limited to explicit source-backed section candidate drafting with validation, cache/fingerprint reuse, style guidance, and tests. It does not support interactive rewrite management or production prompt operations.
- `Affected sections/workflows`: Section drafting, deliverable items, review UI, provenance, validation, export gate.
- `Risk if forgotten`: GPT output could be treated as more authoritative than deterministic evidence, reviewers may repeatedly spend API cost on unchanged evidence, or future rewrite tools could bypass human review expectations.
- `Temporary simplification`: GPT Interpretive Assist is opt-in, source-backed, cached, style-guided, validated, and review-gated; rejected output falls back to deterministic content.
- `Target sprint/subunit`: Future drafting/review UX pass.
- `Status`: open.

### Figure Cartography And Supporting Panels

- `Deferred item`: Continue figure cartographic polish, hazardous/regulated supporting panels, final sheet composition, and production map export formats.
- `Why postponed`: Current figure rendering is sufficient for bounded POC review but not production cartography.
- `Affected sections/workflows`: Deliverable figures, Attachment A panels, hazardous materials figures, DOCX/PDF export, map review UI.
- `Risk if forgotten`: Figures may remain readable but not publication-quality, and supporting panels may not cover all expected report needs.
- `Temporary simplification`: Matrix figures and optional supporting panels are reviewable artifacts with source/method notes and stubs where needed.
- `Target sprint/subunit`: Future cartography/export polish.
- `Status`: open.

### Web App Operations And Production Hardening

- `Deferred item`: Add advanced audit views, background jobs, role correction UI, project archive flow, PDF export, authentication, deployment, and production security hardening.
- `Why postponed`: Sprint 4 is a local Flask/Jinja operator shell over service-layer contracts, not a hosted production system.
- `Affected sections/workflows`: Web UI, project management, exports, long-running jobs, access control, deployment, security.
- `Risk if forgotten`: The POC UI could be mistaken for a multi-user production application or used without appropriate operational controls.
- `Temporary simplification`: The app remains local-first, unauthenticated, and thin over existing backend services.
- `Target sprint/subunit`: Future web/operations hardening.
- `Status`: open.

## Resolved Deferred Items

### Sprint 1.2 Project Intake Artifacts

- `Deferred item`: Implement the Sprint 1.2 project intake artifacts: `context/input_package.json`, `context/project_area.json`, input classification CLI, project area CLI, NAIP/MARIS basemap provenance, and populate integration.
- `Resolution`: Implemented as service-layer artifacts and CLI commands; `populate-for-review` now records input package and project area artifact paths, detected counties, basemap renderability status, and related warnings.
- `Remaining limitation`: Sprint 2.1 added the source catalog entry, example profile requirement, source status detail, and standalone basemap service for MARIS/NAIP 2025 provenance/renderability. Raster-backed map/figure rendering remains deferred.
- `Target sprint/subunit`: Sprint 1.2.
- `Status`: resolved.

### Sprint 2.1 Source Profile And Basemaps

- `Deferred item`: Implement the Sprint 2.1 source/profile/basemap setup for the example-report-shaped workflow.
- `Resolution`: Implemented `environmental_constraints_example` as the default alternatives-review profile; added Sprint 2.1 source catalog entries and attachment/manual stubs; exposed per-source status details; represented missing Census API key as a visible stub; cataloged `maris_naip_2025_imagery`; added service-level MARIS/NAIP basemap indexing and `.tif`/`.tiff`/`.png` sidecar detection.
- `Remaining limitation`: Sprint 2.2 resolved comparison-unit deliverable tables and Census table stubs/local-source rows. Raster-backed figures, panel maps, exact deliverable evidence wiring, and live Census acquisition remain deferred to their owning future work.
- `Target sprint/subunit`: Sprint 2.1.
- `Status`: resolved.

### Sprint 2.2 Comparison Constraints And Tables

- `Deferred item`: Implement the Sprint 2.2 comparison-unit constraints and exact deliverable table targets.
- `Resolution`: Implemented `constraints/comparison_unit_constraints.json`, source-specific normalization for NWI wetland classes, hydrography crossing de-duplication, FEMA flood-zone acreage aggregation, local Census-like ACS table rows, four exact matrix-backed deliverable tables at `deliverable/tables.json`, required stubs for unavailable sources, CLI commands, populate manifest wiring, docs, and focused tests.
- `Remaining limitation`: Review queue deliverable item expansion and export gating are resolved by Sprint 3.1 and Sprint 3.2. Live Census acquisition remains deferred to its owning future work item.
- `Target sprint/subunit`: Sprint 2.2.
- `Status`: resolved.

### Sprint 2.3 Figures, Evidence, And Validation

- `Deferred item`: Implement matrix-backed deliverable figures and align them with evidence package refs.
- `Resolution`: Implemented `deliverable/figures.json`, exact main figure records in matrix order, explicit source/implementation stubs, selected-sidecar basemap rendering/fallbacks, restricted cultural exclusion, split regulated-facility figure targets, Attachment A supporting panel maps outside the main figure count, CLI/populate wiring, evidence package table/figure refs, compact row/figure/constraint summaries, GPT-safe payload handling, docs, and focused tests.
- `Remaining limitation`: Export gates and reviewed-package manifest enforcement are resolved by Sprint 3.2. Local NAIP warehouses that are `.sid`-only remain provenance-only and produce vector-only figures or stubs; GeoTIFF rendering depends on optional `rasterio`.
- `Target sprint/subunit`: Sprint 2.3.
- `Status`: resolved.

### Sprint 3.1 Deliverable Items And Review Queue

- `Deferred item`: Implement matrix-backed deliverable item generation, prompt-contract section drafting payloads, dynamic wetlands/waterbodies comparison-unit child sections, and bounded default review queue generation.
- `Resolution`: Implemented `deliverable/deliverable_items.json`, generation/loading/validation service and CLI, dynamic wetlands/waterbodies children from comparison units, deliverable table/figure/attachment item refs, prompt-contract metadata in section drafting requests, compact validation summaries, default review queue generation from deliverable items, legacy/audit queue opt-in with `include_legacy_artifacts` / `--include-legacy-artifacts`, terminal statuses `accepted`, `edited`, `replaced`, and `declined`, legacy `rejected` normalization to `declined`, replacement-content validation, populate manifest wiring, docs, and focused tests.
- `Remaining limitation`: Sprint 3.3 resolved DOCX fidelity/final verification. Legacy `drafts/report_sections.json`, raw findings, raw comparison tables, and legacy `maps/map_manifest.json` remain available as compatibility/audit artifacts, not the standard queue source.
- `Target sprint/subunit`: Sprint 3.1.
- `Status`: resolved.

### Sprint 3.2 Export Gate And Package Commands

- `Deferred item`: Wire the Sprint 1.1 deliverable matrix into review-complete export gating and package manifests.
- `Resolution`: Implemented default export gating from the standard bounded `deliverable_items` review queue. Reviewed-content export now blocks until every standard deliverable item is terminal or explicitly export-includable; internal preview requires `--include-draft`. Export content selection now handles accepted, edited, replaced, declined, legacy rejected, and explicitly export-eligible unable-to-verify items. Export and deliverable package manifests record review gate status, review counts, matrix item counts, included table/figure/attachment IDs, stub counts, preview state, and unreviewed-item previews. Demo packages remain preview-only and do not mutate review state; MVP packages keep real-data guardrails and fall back to preview unless the queue is already review-complete.
- `Remaining limitation`: Sprint 3.3 resolved baseline DOCX formatting fidelity and final verification docs. Exact/pixel Word-template fidelity, page-number fields, PDF export, web/UI review behavior, and new deliverable targets remain outside Sprint 3.2.
- `Target sprint/subunit`: Sprint 3.2.
- `Status`: resolved.

### Sprint 3.3 DOCX Fidelity Docs And Final Verification

- `Deferred item`: Improve editable DOCX fidelity and add final verification status over the compact, reviewed export path.
- `Resolution`: Implemented Sprint 3.3 baseline DOCX page setup, core Word styles, title metadata, matrix-ordered headings, front matter lists, bounded editable table previews with truncation notices, figure placeholders/captions/source/method notes, attachment ordering, DOCX readability checks, manifest-level `final_verification`, package-manifest propagation, docs, focused tests, full pytest, and verify-script smoke checks.
- `Remaining limitation`: Exact/pixel Word-template fidelity and page-number fields remain later polish. PDF export and UI/web wiring remain out of scope. The UI should consume existing backend contracts rather than adding report/review/export logic.
- `Target sprint/subunit`: Sprint 3.3.
- `Status`: resolved.

### Canonical Prompt Contract Wiring

- `Deferred item`: Wire `config/report_generation_prompts.json` into GPT-assisted and deterministic section generation.
- `Resolution`: Sprint 3.1 wires prompt-config metadata into standard deliverable item section drafting requests, including matrix target metadata, prompt key, global/section constraints, allowed inputs, citation policy, and structured evidence only. GPT-safe evidence payload safeguards remain in place.
- `Remaining limitation`: Legacy `generate-report-sections` remains available for compatibility/audit context and may still use its existing report-section pathways. Future prompt tuning and reviewer-controlled rewrite flows remain outside Sprint 3.1.
- `Target sprint/subunit`: Sprint 3.1.
- `Status`: resolved.

### Dynamic Wetlands/Waterbodies Comparison-Unit Sections

- `Deferred item`: Expand the dynamic 3.1.1.x wetlands/waterbodies section template into one reviewable subsection per comparison unit.
- `Resolution`: Sprint 3.1 expands the matrix dynamic template into stable `wetlands-waterbodies-{comparison_unit_id}` deliverable items, with section numbers/titles derived from matrix patterns and comparison-unit IDs preserved for review/export context.
- `Remaining limitation`: Export completeness gating for these dynamic items is resolved by Sprint 3.2.
- `Target sprint/subunit`: Sprint 3.1.
- `Status`: resolved.

### Raster-Backed NAIP Figure Rendering

- `Deferred item`: Render NAIP/MARIS basemaps into deliverable figures only when renderable sidecars are available.
- `Resolution`: Sprint 2.3 deliverable figures can render selected `.png`, `.tif`, or `.tiff` sidecars when project-area metadata/georeference is usable. `.sid` files remain provenance only, and failures are preserved through `basemap_selected_not_renderable` or `basemap_render_failed`.
- `Remaining limitation`: No MrSID decoding, paid basemap API, or hard `rasterio` dependency. The current local NAIP warehouse may be `.sid`-only, so normal local runs may remain vector-only.
- `Target sprint/subunit`: Sprint 2.3.
- `Status`: resolved.
