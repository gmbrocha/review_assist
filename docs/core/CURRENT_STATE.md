# Current State

## Current Project Goal

Review Assist is a service-first workflow for generating first-pass environmental constraints review packages. It should parse project inputs, build source-backed constraint evidence, produce bounded review items, require human review, and compile reviewed content into editable report packages.

The system is not a recommendation engine, final environmental review, regulatory approval tool, or autonomous analyst.

## Current Sprint/Subunit

- Completed: Sprint 1.1 Contract Foundation.
- Completed: Sprint 1.2 Project Intake Artifacts.
- Completed: Sprint 1.3 Comparison Units and Orchestration.
- Completed: Sprint 2.1 Source Profile And Basemaps.
- Completed: Sprint 2.2 Comparison Constraints And Tables.
- Completed: Sprint 2.3 Figures, Evidence, And Validation.
- Completed: Sprint 3.1 Deliverable Items And Review Queue.
- Completed: Sprint 3.2 Export Gate And Package Commands.
- Completed: Sprint 3.3 DOCX Fidelity Docs And Final Verification.
- Completed: Sprint 4 Web App And Wiring.
- Completed: Sprint 5.0 Planning Diff Lock And Numbering Decision.
- Completed: Sprint 5.1 Canonical Policy Schema Reconciliation.
- Completed: Sprint 5.2 Extent Semantics And Wording Enforcement.
- Completed: Sprint 5.3 Source Needs Manifest And Warehouse Alignment.
- Completed: Sprint 5.4 Report Inclusion And Discernment Pass.
- Completed: Sprint 5.5 Caveat Bundles, Prohibited Claims, And GPT Eligibility.
- Completed: Sprint 5.6 Table/Figure Policy Matrix Alignment.
- Completed: Sprint 5.7 Manual / Reviewer-Supplied Policy MVP.
- Completed: Sprint 5.8 Export QA And Override Policy.
- Completed: Sprint 5.9 End-To-End Trial, Docs, And Verification.
- Completed: Sprint 6.1 Existing Figure Flow Audit.
- Completed: Sprint 6.2 Figure Recipe And Override Model.
- Active next implementation target: Sprint 6.3 Reviewer Figure Editor UI.

## Active Architectural State

Implemented baseline:

- CLI/service-oriented backend plus a local-first Sprint 4 Flask/Jinja web UI shell.
- Project workspaces under `projects/<project_id>/`.
- Input package classification, KMZ/KML inspection, normalized project geometry artifacts, and project area artifacts.
- Project context, comparison units, source status, source acquisition, local source materialization, source inventory, constraint analysis, findings, tables, vector-only maps, evidence packages, draft report sections, JSON review queue, Markdown/DOCX exports, demo/MVP package commands, populate-for-review orchestration.
- Static Sprint 1.1 deliverable matrix and report prompt contract validation.
- Matrix-backed Sprint 2.2 deliverable table generation at `projects/<project_id>/deliverable/tables.json`, with four exact table targets generated or stubbed from `config/deliverable_section_matrix.json`.
- `config/report_section_policy.json` now includes explicit `table_policies` for the four matrix table targets. Table artifacts, evidence summaries, deliverable items, review metadata, and export summaries carry table policy metadata including interpretation extent, allowed source categories, body preview cap, and artifact overflow destination.
- `table-wetlands-waterbodies` uses an explicit metric contract: wetland class columns are counted only from `usfws_nwi_wetlands`, while Stream Crossings are counted only from canonical `usgs_nhd_flowlines` line-crossing events. The table excludes the `usgs_nhd_hydrography` logical rollup and NHD waterbody/other-area polygon context from the crossing metric, and comparison-unit constraints carry a relationship event location so duplicate overlapping flowline records can be deduped without mutating source geometry.
- Matrix-backed Sprint 2.3 deliverable figure generation at `projects/<project_id>/deliverable/figures.json`, with 15 exact main figure targets generated or stubbed from `config/deliverable_section_matrix.json`; regulated-facility content is split into hazardous/regulated sites, water-discharge/waste facilities, and oil/gas wells.
- Figure artifacts, evidence summaries, deliverable items, review metadata, and export summaries carry figure policy metadata including interpretation extent, visual extent class, rendering extent class, presentation-only render extent, and allowed source categories.
- Matrix-backed Sprint 3.1 deliverable item generation at `projects/<project_id>/deliverable/deliverable_items.json`, including static report targets, dynamic wetlands/waterbodies comparison-unit child sections, deliverable table/figure/attachment items, prompt-contract metadata, source-gap validation summaries, and required stubs.
- Source-backed standard section_text deliverable items now use deterministic report-style candidate prose instead of scaffold/process summaries. Missing or deferred-source sections remain explicit source/data-gap stubs and generated prose still requires human review before export.
- Deliverable items and standard review queue items now carry policy-backed render metadata: inclusion status, activation condition, review requirement, comparison-unit expansion policy, render decision, render destination, render decision reason, and report-body eligibility. PEL is conditional/manual and review-only until reviewer-supplied content exists; wetlands/waterbodies comparison-unit narrative children remain body-eligible; table-only/manual/restricted/deferred placeholders remain review-visible without becoming normal report-body prose by default.
- Deliverable items, standard review queue items, review detail summaries, and export manifest records now carry manual-material metadata for source-backed generated content, manual-required text, reviewer-supplied content, restricted reviewer-supplied needs, optional absent material, deferred source work, unable-to-verify content, supporting-document status, edited captions, and replacement figures. Sprint 5.7 did not add generalized document uploads; reviewer notes remain internal, existing edited/replacement content carries reviewer-supplied body text, and existing figure caption/replacement handling remains the only upload-style review path.
- The standard review queue now consumes `deliverable_items.json` by default and creates one bounded review item per deliverable item. Legacy raw finding/table/map/spatial/source-inventory queue behavior remains available only through explicit audit mode.
- A developer/test reset command and local Overview action can refresh deterministic review artifacts and rebuild the standard queue from current local inputs and registered source layers. The reset updates source status, constraints, tables, figures, maps, evidence, deterministic draft sections, deliverable items, and review queue without source acquisition, local source materialization, NAIP materialization, or GPT drafting; source data and project setup are preserved.
- Default reviewed-content export is gated by the standard bounded review queue. `export-report` without `--include-draft` blocks until every standard deliverable item is terminal or explicitly export-includable; `--include-draft` remains an internal/pre-review preview bypass. Export and package manifests record review gate status, review counts, matrix item counts, included table/figure/attachment IDs, stub counts, preview state, compactness budget, and final verification summary.
- Reviewed export skips body-ineligible generated placeholders with explicit policy render reasons unless a reviewer supplies edited or replacement content and marks the item export-eligible. Render policy fields propagate into included and skipped export manifest records and the local review UI summary/detail views.
- Default reviewed export now runs policy-aware export QA before writing new reviewed Markdown/DOCX outputs. Blocking QA errors cover unresolved gate state, manual/reviewer-supplied placeholders without reviewer content, unknown/disallowed source/table/figure refs, missing required caveats, blank required table cells, missing required figure metadata or image files unless explicitly reviewed as placeholder/status content, and severe compactness/final-verification failures. Export/package manifests and web export readiness expose QA status, counts, and top issues. `--include-draft` records QA status but remains an internal preview bypass. Reviewer override with required reason is deferred.
- DOCX export now applies Sprint 3.3 baseline page setup, core Word styles, matrix-ordered headings, title/front-matter metadata, bounded editable table previews, figure captions/source/method notes, missing-figure placeholders, attachment ordering, and DOCX readability checks while preserving Markdown/DOCX compactness guardrails.
- The Sprint 4 web UI exposes existing backend contracts through a thin adapter layer: draft project creation, staged uploads, committed input classification, setup/readiness/latest-run status, project workspace listing/selection, overview/source/populate status, bounded standard review queue, review item detail/actions, export readiness, preview/reviewed export triggers, compactness budget/final verification display, and manifest-listed package outputs. Route handlers call adapter/service functions and do not parse raw GIS/evidence artifacts or report assembly internals.
- Figure review items use a figure-specific web action form for edited captions, safe project-local replacement image uploads, and Accept Final. The review UI displays figure previews at a larger bounded review-only size while preserving aspect ratio and leaving export figure dimensions unchanged. Report-ready figure PNGs are map panels only and do not embed captions, source notes, method notes, review/process instructions, or report-facing figure titles; those fields remain editable metadata/export text. Reviewer notes remain internal review metadata.
- Project-local figure styling metadata can now be initialized from existing generated figure artifacts with `initialize-figure-style-model`. The model writes figure recipes, sparse style overrides, implicit autogenerated/stub `v1` figure versions, and render job metadata under `projects/<project_id>/maps/figure_*`. This is metadata-only: it does not apply overrides during rendering, change export resolution, alter review queue state, mutate source/analysis artifacts, or change figure counts.
- `deliverable_figures.py` remains the orchestration entry point; figure target specs, artifact validation, basemap sidecar loading, and rendering/layout helpers are split into focused `deliverable_figure_*` modules.
- Report-facing comparison-unit constraint analysis at `projects/<project_id>/constraints/comparison_unit_constraints.json`; raw project-feature constraints remain available as evidence at `projects/<project_id>/constraints/constraint_results.json`.
- `environmental_constraints_example` is the default profile for `alternatives_review`; `environmental_constraints_basic` and `location_screening_basic` remain available for explicit use.
- Source status and source inventory now include per-source detail statuses and source-need classifications for registered local, local materialized, downloaded, manual, restricted, failed, unimplemented, missing, optional, stubbed, missing render assets, warehouse-present-but-not-yet-materialized, public/coarse context, and deferred sources.
- Source status now distinguishes historical acquisition attempts from effective report-facing availability. Current project-local/materialized sources suppress stale failed-download caveats for the same source ID, logical rollups such as `usgs_nhd_hydrography` and `epa_envirofacts_echo` can be marked satisfied by specific materialized child layers, and report/GPT caveats use effective source status rather than raw acquisition history. `mdeq_environmental_context` remains a manual residual context bucket, not a logical rollup satisfied by unrelated regulated-facility child layers.
- Source status now writes `section_source_needs` records that trace canonical report section policy source categories/refs through the source catalog, active report profile, warehouse availability, effective source details, and source-need classes.
- The local `sources/` warehouse is normalized around stable app-facing source IDs with raw agency/download folder names preserved under `raw/`. `sources/source_warehouse_manifest.json` indexes per-source `source_manifest.json` files; bulk raw source data remains local/ignored.
- Local materialization now covers the previous working Mississippi warehouse sources plus seeded FEMA flood hazard, specific NHD flowlines/waterbodies/other areas, EPA FRS/MARIS regulated facility layers, Mississippi oil/gas wells, national wildlife refuges, and NRCS easements. The live `usgs_nhd_hydrography` and `epa_envirofacts_echo` IDs remain available as public download rollups, not required physical warehouse folders when specific local layers already satisfy the category. `mdeq_environmental_context` remains a manual residual context bucket.
- MARIS/NAIP 2025 imagery is cataloged as context-only basemap provenance. `src/review_assist/basemaps.py` indexes county folders under `sources/aerial_base_maps/maris_naip_2025`, treats `.sid` files as unsupported source metadata only, recognizes `.tif`, `.tiff`, and `.png` files as renderable candidates, and discovers project-local NAIP render assets under `projects/<project_id>/basemaps/naip/`, including grouped figure-extent assets.
- Non-stub deliverable figures prefer project-local NAIP GeoTIFF assets and supported `.png`, `.tif`, or `.tiff` render assets when project-area metadata selects them. MrSID `.sid` files are not selected as active visual basemaps; missing imagery now reports `basemap_render_asset_missing` or materialization failure instead of asking for MrSID sidecars. GeoTIFF rendering uses optional `rasterio` lazily when installed; the package does not hard-require rasterio for normal operation.
- `plan-figure-extents` writes a non-network `maps/figure_extent_plan.json` artifact that records per-figure core bounds, full render bounds, legend/collar layout, map-furniture placement, extent class, and grouped basemap materialization needs. `materialize-naip-basemap --for-figure-extents` creates grouped project-local NAIP GeoTIFF/JSON assets for planned full render extents such as `small_direct` and `medium_context`. Web Create Review Queue enables this durable project-local NAIP materialization path before figure rendering; the CLI keeps the explicit `populate-for-review --materialize-naip-basemap` flag for scripted runs. Both paths enforce AOI/tile/pixel/time limits, resample oversized native-resolution windows to fit the configured output-pixel cap, and record controlled failure status.
- Deliverable figure rendering now enforces figure-specific source scope declarations for required thematic, optional supporting, and excluded carryover source IDs so shared category/grouping logic does not bleed layers across figure themes. It also styles comparison units individually with saturated, high-separation deterministic colors. KML colors are used only when saturated/readable on aerial imagery and distinct from already assigned comparison-unit colors; otherwise the renderer uses stable high-contrast fallbacks without the old heavy white casing. Thematic source-layer styling uses a separate deterministic high-contrast palette that rejects black, washed-out, low-saturation, low-contrast olive/tan/brown, and green source-layer colors on aerial basemaps. This does not change comparison-unit geometry or constraint analysis.
- Deliverable figure legends now use a bounded map-collar layout when needed: the rendered extent expands on a low-conflict side using measured legend bbox dimensions so the legend sits in adjacent mapped context rather than over the core project extent or in a large outside margin. When a planned render extent requires a collar, figure rendering requires any selected NAIP sidecar to cover the full render extent; insufficient sidecars are treated as vector-only fallback with explicit warnings instead of silently leaving blank collar space. Source layer symbology is lighter than project/comparison-unit symbology.
- Standard constraint, table, figure, evidence, deliverable-item, review-queue, and section-drafting artifacts now carry explicit extent-policy metadata. The metadata distinguishes project-area analysis bounds, direct intersections, screening buffers, nearby/community context, watershed context, county/regional context, figure render extent, and presentation-only legend/basemap collar extent. This is a contract/metadata pass only: it does not change query distances, source acquisition, source clipping, comparison-unit generation, or figure counts.
- Extent term semantics now distinguish direct `within` claims from nearby/community context, watershed/subwatershed context, county/regional context, reviewer-defined APE, corridor language, and shown-on-map presentation support. Context-only deterministic wording avoids direct project-footprint phrasing, presentation/collar extent propagates through metadata merges, and GPT output validation rejects direct-project/intersection language for context-only metadata, APE language without reviewer-defined cultural context, and map extent treated as analysis evidence.
- `config/report_section_policy.json` is the canonical machine-readable report policy for section extent scope, visual extent class, comparison-unit expansion, evidence pattern, caveats, prohibited claims, and GPT readiness. It keeps demographics in county/regional context, makes the oil-wells direct-check/context-figure distinction explicit, and preserves county/regional figure semantics even when current rendering reuses medium-context behavior.
- GPT Interpretive Assist is now an explicit opt-in workflow, not part of normal populate/reset. The CLI command `draft-section-candidates` and the Overview UI toggle/action draft only eligible source-backed `section_text` review candidates, use `config/report_style_context/environmental_constraints_report_style.md` as non-evidence style guidance, cache accepted drafts by evidence/policy/style/prompt/model fingerprint, reject unsafe output, fall back to deterministic content, and keep all GPT-assisted items unaccepted until human review.
- Rejected or failed explicit GPT Interpretive Assist attempts preserve deterministic source-backed content and now record item-level fallback provenance for review detail display. Wetlands/waterbodies GPT drafting distinguishes the `wetlands-and-waterbodies` section rollup from dynamic comparison-unit narratives and prompts for interpretive screening-level report prose rather than evidence-manifest prose.
- Required caveat IDs in `config/report_section_policy.json` now validate against an internal guardrail registry, and GPT output validation blocks known prohibited claim families including final impact/no-impact/no-effect, wetland/water jurisdiction, cultural eligibility/effect/clearance, contamination cleanup/liability, permit required/not-required, access/mitigation/construction commitments, ranking/scoring/selection, and demographic impact language. GPT coverage was not expanded in Sprint 5.5.
- The evidence package now includes deliverable table refs, deliverable figure refs, row/figure availability summaries, comparison-unit summaries, compact source-backed constraint summaries, source-gap status, validation issues, and raw artifact paths without exposing full geometries or raw feature dumps to GPT-bound evidence.
- Census TIGER/ACS table generation supports registered local Census-like tract/community polygon sources with ACS fields for the two demographic deliverable tables, and produces visible stubs when the source/API setup is unavailable. Live Census API/TIGER acquisition remains unimplemented.

Important current artifacts:

- `config/deliverable_section_matrix.json`
- `config/report_generation_prompts.json`
- `config/report_profiles.json`
- `config/source_catalog.json`
- `projects/<project_id>/context/input_package.json`
- `projects/<project_id>/intermediate/project_geometry.json`
- `projects/<project_id>/intermediate/project_features.geojson`
- `projects/<project_id>/intermediate/project_analysis_bounds.geojson`
- `projects/<project_id>/intermediate/comparison_units.geojson`
- `projects/<project_id>/intermediate/comparison_units.json`
- `projects/<project_id>/context/project_area.json`
- `projects/<project_id>/context/project_context.json`
- `projects/<project_id>/source_status/source_status_set.json`
- `projects/<project_id>/constraints/constraint_results.json`
- `projects/<project_id>/constraints/comparison_unit_constraints.json`
- `projects/<project_id>/deliverable/tables.json`
- `projects/<project_id>/deliverable/figures.json`
- `projects/<project_id>/deliverable/deliverable_items.json`
- `projects/<project_id>/maps/figures/*.png`
- `projects/<project_id>/evidence/evidence_package.json`
- `projects/<project_id>/review_queue/review_queue.json`
- `projects/<project_id>/exports/export_manifest.json`
- `projects/<project_id>/exports/deliverable_package_manifest.json`

## Known Immediate Constraints

- Do not implement product code during documentation architecture tasks.
- The web UI is still local-first Sprint 4 work: no authentication, deployment, multi-user workflow, archive flow, PDF export, advanced audit browser, background job system, or raw/audit review workflow is implemented.
- The canonical deliverable matrix validates and now drives exact deliverable table, figure, deliverable item, bounded review queue generation, review-complete export gating, and package manifest review-gate summaries.
- The canonical prompt config validates and is wired into standard deliverable item section drafting payloads. Legacy `drafts/report_sections.json` remains available for compatibility/audit context. Explicit GPT Interpretive Assist updates the standard review queue only through a separate cached action/command and does not run from page load, queue regeneration, reset, or default populate.
- Compactness and DOCX fidelity regression tests protect the standard deliverable path from raw-artifact body dumps, unbounded table rendering, overlong generated section content, malformed DOCX output, and missing final verification status.
- Legacy `maps/map_manifest.json` remains a raw evidence/audit map manifest. Standard report-facing figures live in `deliverable/figures.json`.
- NAIP/MARIS basemap provenance and renderability are recorded in `project_area.json` and source status detail. Deliverable figure rendering can use selected renderable sidecars, but local `.sid`-only imagery still produces vector-only figures or explicit stubs/warnings. `populate-for-review --materialize-naip-basemap` can opt into failure-tolerant grouped NAIP sidecar materialization for planned figure render extents; plain populate does not acquire imagery.
- Named community, nearby, watershed, and county/regional extent metadata is now present, but separate expanded context queries are still deferred. Current automated evidence remains bounded by existing project-area/source materialization behavior unless a future pass explicitly adds named context extents.
- Comparison units are generated, recorded by populate orchestration, and used for report-facing constraint summaries, exact deliverable tables, exact deliverable figures, evidence refs, dynamic wetlands/waterbodies deliverable item sections, and matrix-backed export gating.
- Census source setup and table stubbing/local-source table generation are implemented; live ACS API calls, TIGER download/acquisition, and full margin-of-error handling remain future work.
- Sprint 3 is complete as the non-UI backend foundation for Sprint 4. Exact/pixel Word template fidelity, page-number fields, PDF export, and any web/UI behavior remain outside the completed Sprint 3 backend scope unless explicitly re-scoped.
- Missing/gated/manual/stale/failed sources must remain visible and reviewable.
- Sprint 5 is complete. Sprint 5.1 created the package reconciliation ledger, kept `config/report_section_policy.json` canonical, added explicit section activation/review fields, made `relationship-with-pel-study` conditional/manual reviewer-supplied policy, and strengthened policy validation against source/table/figure contracts. Sprint 5.2 tightened extent wording semantics and presentation-only map/collar guardrails. Sprint 5.3 added source-needs/effective-truth mapping without source acquisition expansion. Sprint 5.4 added render gating/export selection metadata while preserving wetlands/waterbodies narrative children and stable deliverable/review item counts. Sprint 5.5 tightened GPT caveat/prohibited-claim guardrails without expanding GPT coverage. Sprint 5.6 added explicit table policies and table/figure policy metadata while preserving the current 4 table, 15 figure, and 3 attachment counts. Sprint 5.7 added manual/reviewer-supplied material metadata and review/export propagation without adding generalized uploads or source acquisition. Sprint 5.8 added policy-aware export QA and hard-blocked reviewed export on blocking QA errors while leaving reviewer override deferred. Sprint 5.9 verified the end-to-end preview and reviewed-export paths, closed the package ledger, and archived Sprint 5 planning docs. Future work must not implement source acquisition expansion, GPT coverage expansion, or deliverable count changes without explicit approval.
- Sprint 6 has started as a constrained reviewer figure-styling workflow. Sprint 6.1 audited the existing figure generation/review/export flow and confirmed the immutable analytical boundaries for style-only edits. Sprint 6.2 added project-local recipe, style override, render job, and figure version metadata without changing figure rendering, export resolution, source truth, evidence counts, report policy, GPT behavior, or review-gate semantics. Sprint 6.3 is active next and should add the reviewer-facing figure editor UI over the metadata model without adding geometry/evidence editing.

## Context Routing

- Agent operating contract: `AGENTS.md`
- Architecture summary: `docs/core/ARCHITECTURE.md`
- Durable decisions: `docs/core/DECISIONS.md`
- Governance workflows: `docs/governance/`
- Domain doc index: `docs/domains/README.md`
- Sprint index: `docs/sprints/README.md`
- Completed Sprint 5 root plan: `docs/archive/sprints/SPRINT_5_REPORT_INTELLIGENCE_SOURCE_TRUTH_AND_DISCERNMENT.md`
- Completed Sprint 5 routing ledger: `docs/archive/sprints/SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md`
- Deferred work registry: `docs/governance/DEFERRED_WORK.md`
- High-level canonical plan: `CANONICAL_PLAN.md` when deliverable shape or workflow direction is ambiguous
- Historical/cold docs: `docs/archive/README.md`
