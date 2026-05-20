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
- Active next implementation target: Sprint 4 Web App And Wiring.

## Active Architectural State

Implemented baseline:

- CLI/service-oriented backend plus a local-first Sprint 4 Flask/Jinja web UI shell.
- Project workspaces under `projects/<project_id>/`.
- Input package classification, KMZ/KML inspection, normalized project geometry artifacts, and project area artifacts.
- Project context, comparison units, source status, source acquisition, local source materialization, source inventory, constraint analysis, findings, tables, vector-only maps, evidence packages, draft report sections, JSON review queue, Markdown/DOCX exports, demo/MVP package commands, populate-for-review orchestration.
- Static Sprint 1.1 deliverable matrix and report prompt contract validation.
- Matrix-backed Sprint 2.2 deliverable table generation at `projects/<project_id>/deliverable/tables.json`, with four exact table targets generated or stubbed from `config/deliverable_section_matrix.json`.
- Matrix-backed Sprint 2.3 deliverable figure generation at `projects/<project_id>/deliverable/figures.json`, with 13 exact main figure targets generated or stubbed from `config/deliverable_section_matrix.json`.
- Matrix-backed Sprint 3.1 deliverable item generation at `projects/<project_id>/deliverable/deliverable_items.json`, including static report targets, dynamic wetlands/waterbodies comparison-unit child sections, deliverable table/figure/attachment items, prompt-contract metadata, source-gap validation summaries, and required stubs.
- Source-backed standard section_text deliverable items now use deterministic report-style candidate prose instead of scaffold/process summaries. Missing or deferred-source sections remain explicit source/data-gap stubs and generated prose still requires human review before export.
- The standard review queue now consumes `deliverable_items.json` by default and creates one bounded review item per deliverable item. Legacy raw finding/table/map/spatial/source-inventory queue behavior remains available only through explicit audit mode.
- A developer/test reset command and local Overview action can refresh deterministic review artifacts and rebuild the standard queue from current local inputs and registered source layers. The reset updates source status, constraints, tables, figures, maps, evidence, deterministic draft sections, deliverable items, and review queue without source acquisition, local source materialization, NAIP materialization, or GPT drafting; source data and project setup are preserved.
- Default reviewed-content export is gated by the standard bounded review queue. `export-report` without `--include-draft` blocks until every standard deliverable item is terminal or explicitly export-includable; `--include-draft` remains an internal/pre-review preview bypass. Export and package manifests record review gate status, review counts, matrix item counts, included table/figure/attachment IDs, stub counts, preview state, compactness budget, and final verification summary.
- DOCX export now applies Sprint 3.3 baseline page setup, core Word styles, matrix-ordered headings, title/front-matter metadata, bounded editable table previews, figure captions/source/method notes, missing-figure placeholders, attachment ordering, and DOCX readability checks while preserving Markdown/DOCX compactness guardrails.
- The Sprint 4 web UI exposes existing backend contracts through a thin adapter layer: draft project creation, staged uploads, committed input classification, setup/readiness/latest-run status, project workspace listing/selection, overview/source/populate status, bounded standard review queue, review item detail/actions, export readiness, preview/reviewed export triggers, compactness budget/final verification display, and manifest-listed package outputs. Route handlers call adapter/service functions and do not parse raw GIS/evidence artifacts or report assembly internals.
- Figure review items use a figure-specific web action form for edited captions, safe project-local replacement image uploads, and Accept Final. Report-ready figure PNGs are map panels only and do not embed captions, source notes, method notes, review/process instructions, or report-facing figure titles; those fields remain editable metadata/export text. Reviewer notes remain internal review metadata.
- `deliverable_figures.py` remains the orchestration entry point; figure target specs, artifact validation, basemap sidecar loading, and rendering/layout helpers are split into focused `deliverable_figure_*` modules.
- Report-facing comparison-unit constraint analysis at `projects/<project_id>/constraints/comparison_unit_constraints.json`; raw project-feature constraints remain available as evidence at `projects/<project_id>/constraints/constraint_results.json`.
- `environmental_constraints_example` is the default profile for `alternatives_review`; `environmental_constraints_basic` and `location_screening_basic` remain available for explicit use.
- Source status and source inventory now include per-source detail statuses for registered local, local materialized, downloaded, manual, restricted, failed, unimplemented, missing, optional, stubbed, selected-but-not-renderable, and warehouse-present-but-not-yet-materialized sources.
- The local `sources/` warehouse is normalized around stable app-facing source IDs with raw agency/download folder names preserved under `raw/`. `sources/source_warehouse_manifest.json` indexes per-source `source_manifest.json` files; bulk raw source data remains local/ignored.
- Local materialization now covers the previous working Mississippi warehouse sources plus seeded FEMA flood hazard, specific NHD flowlines/waterbodies/other areas, EPA FRS/MARIS regulated facility layers, Mississippi oil/gas wells, national wildlife refuges, and NRCS easements. The live `usgs_nhd_hydrography` and `epa_envirofacts_echo` IDs remain available as public download rollups, not required physical warehouse folders when specific local layers already satisfy the category. `mdeq_environmental_context` remains a manual residual context bucket.
- MARIS/NAIP 2025 imagery is cataloged as context-only basemap provenance. `src/review_assist/basemaps.py` indexes county folders under `sources/aerial_base_maps/maris_naip_2025`, treats `.sid` files as provenance only, recognizes `.tif`, `.tiff`, and `.png` sidecars as renderable candidates, and discovers project-local NAIP sidecars under `projects/<project_id>/basemaps/naip/`, including grouped figure-extent sidecars.
- Non-stub deliverable figures prefer selected MARIS/NAIP `.png`, `.tif`, or `.tiff` sidecars and project-local NAIP GeoTIFF sidecars when project-area metadata selects them. MrSID `.sid` files remain provenance only with explicit vector-only diagnostics. GeoTIFF rendering uses optional `rasterio` lazily when installed; the package does not hard-require rasterio for normal operation.
- `plan-figure-extents` writes a non-network `maps/figure_extent_plan.json` artifact that records per-figure core bounds, full render bounds, legend/collar layout, map-furniture placement, extent class, and grouped basemap materialization needs. `materialize-naip-basemap` remains explicit and optional; without flags it uses legacy project analysis bounds, and with `--for-figure-extents` it creates grouped project-local NAIP GeoTIFF/JSON sidecars for planned full render extents such as `small_direct` and `medium_context`. Both paths enforce AOI/tile/pixel/time limits, resample oversized native-resolution windows to fit the configured output-pixel cap, and record controlled failure status without changing normal populate behavior.
- Deliverable figure rendering now styles comparison units individually with preserved usable KML colors or deterministic visible fallbacks so close line alternatives do not collapse into one same-color project-feature layer. This does not change comparison-unit geometry or constraint analysis.
- Deliverable figure legends now use a bounded map-collar layout when needed: the rendered extent expands on a low-conflict side using measured legend bbox dimensions so the legend sits in adjacent mapped context rather than over the core project extent or in a large outside margin. When a planned render extent requires a collar, figure rendering requires any selected NAIP sidecar to cover the full render extent; insufficient sidecars are treated as vector-only fallback with explicit warnings instead of silently leaving blank collar space. Source layer symbology is lighter than project/comparison-unit symbology.
- Standard constraint, table, figure, evidence, deliverable-item, review-queue, and section-drafting artifacts now carry explicit extent-policy metadata. The metadata distinguishes project-area analysis bounds, direct intersections, screening buffers, nearby/community context, watershed context, county/regional context, figure render extent, and presentation-only legend/basemap collar extent. This is a contract/metadata pass only: it does not change query distances, source acquisition, source clipping, comparison-unit generation, or figure counts.
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
- The canonical prompt config validates and is wired into standard deliverable item section drafting payloads. Legacy `drafts/report_sections.json` remains available for compatibility/audit context.
- Compactness and DOCX fidelity regression tests protect the standard deliverable path from raw-artifact body dumps, unbounded table rendering, overlong generated section content, malformed DOCX output, and missing final verification status.
- Legacy `maps/map_manifest.json` remains a raw evidence/audit map manifest. Standard report-facing figures live in `deliverable/figures.json`.
- NAIP/MARIS basemap provenance and renderability are recorded in `project_area.json` and source status detail. Deliverable figure rendering can use selected renderable sidecars, but local `.sid`-only imagery still produces vector-only figures or explicit stubs/warnings. `populate-for-review --materialize-naip-basemap` can opt into failure-tolerant grouped NAIP sidecar materialization for planned figure render extents; plain populate does not acquire imagery.
- Named community, nearby, watershed, and county/regional extent metadata is now present, but separate expanded context queries are still deferred. Current automated evidence remains bounded by existing project-area/source materialization behavior unless a future pass explicitly adds named context extents.
- Comparison units are generated, recorded by populate orchestration, and used for report-facing constraint summaries, exact deliverable tables, exact deliverable figures, evidence refs, dynamic wetlands/waterbodies deliverable item sections, and matrix-backed export gating.
- Census source setup and table stubbing/local-source table generation are implemented; live ACS API calls, TIGER download/acquisition, and full margin-of-error handling remain future work.
- Sprint 3 is complete as the non-UI backend foundation for Sprint 4. Exact/pixel Word template fidelity, page-number fields, PDF export, and any web/UI behavior remain outside the completed Sprint 3 backend scope unless explicitly re-scoped.
- Missing/gated/manual/stale/failed sources must remain visible and reviewable.

## Context Routing

- Agent operating contract: `AGENTS.md`
- Architecture summary: `docs/core/ARCHITECTURE.md`
- Durable decisions: `docs/core/DECISIONS.md`
- Governance workflows: `docs/governance/`
- Domain doc index: `docs/domains/README.md`
- Sprint index: `docs/sprints/README.md`
- Deferred work registry: `docs/governance/DEFERRED_WORK.md`
- High-level canonical plan: `CANONICAL_PLAN.md` when deliverable shape or workflow direction is ambiguous
- Historical/cold docs: `docs/archive/README.md`
