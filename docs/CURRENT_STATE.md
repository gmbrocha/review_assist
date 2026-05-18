# Current State

## Phase

Phase 0 scaffold/planning is complete. Phase 1 KMZ/KML ingestion and geometry inspection is implemented for the current prototype baseline. The first Phase 2A/2B baseline is also implemented: source catalog, project source registries, local source registration, local Mississippi source warehouse materialization, and local spatial relationship checks. The Phase 2C catalog-driven source acquisition baseline is implemented with explicit USFWS NWI, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard downloaders. Local materializers now include NWI wetlands, USFWS Critical Habitat, SSURGO soils, aggregated MDOT/rail transportation context, utilities, administrative/boundary context, public cultural context, community facilities, and conservation/recreation lands. Phase 3 project context/source status artifacts, the first Phase 4 JSON-backed review queue baseline, Phase 5 populate-for-review orchestration, Phase 6A deterministic finding generation, Phase 6B source provenance/comparison tables, Phase 6C vector-only map/figure generation with report-ready metadata and export-local PNG assets, Phase 6D report section generation with deterministic and optional GPT drafting, evidence package generation, the Markdown/DOCX export compiler, internal demo deliverable package command, real-data MVP deliverable package command, MVP package quality metadata, and the first constraint-engine baseline are implemented.

The repository currently contains documentation, project workspaces, sample KMZ/KML preview utilities, project manifests, project-local input copies, Python service/CLI implementation for Phase 1 inspection, Phase 2 source catalog/spatial check/source acquisition/source materialization services, project geometry normalization, constraint overlap/proximity analysis, workflow-native project context/source status services, source inventory/provenance artifacts, deterministic draft finding generation, comparison table artifacts including grouped, hydrography, flood hazard, critical habitat, and regulated facility summaries, vector-only map artifacts, evidence package artifacts, deterministic/GPT draft report section artifacts, JSON review queue services, Markdown/DOCX export services, internal demo deliverable package orchestration, real-data guarded MVP deliverable orchestration, and populate-for-review orchestration. No production workflow has been implemented.

The current direction is clearer than the initial scaffold: the system should eventually create a comprehensive pre-review draft package so the reviewer does not start from a blank page. The canonical workflow is now workspace driven: open/create workspace, add inputs, generate project context, resolve source status, populate for review, review every generated item, and export accepted content.

## Known Input Expectation

Initial inputs may include KMZ or KML files containing:

- A project footprint or study area.
- Multiple proposed alternatives.
- Alternative geometries that may represent trails, corridors, sites, alignments, access routes, infrastructure options, or other project options.

The exact input schema, naming conventions, and validation requirements are not yet defined.

Current real example inputs in the repository include:

- `trail_route_alternatives.kmz`, representing the trail alternatives context.
- `conexon_projects_color_coded.kmz`, representing broadband installation spot context.
- `env_constraints_report_20260511_EXAMPLE_ONLY.docx`, an example environmental constraints report used for deliverable structure research only.

Project-local copies are now expected under:

- `projects/trails/inputs/trail_route_alternatives.kmz`
- `projects/conexon_projects/inputs/conexon_projects_color_coded.kmz`

## Known Future Output Goal

The future goal is an editable pre-review report package that may include:

- Structured findings for each alternative.
- Maps and tables.
- Draft narrative.
- Contextual implications.
- Appendices or reference material.
- Source provenance for each finding.
- Method notes.
- Uncertainty and missing-data flags.
- Reviewer status for each finding.
- Reviewer edits and acceptance or rejection history.

All outputs are pre-review drafts until reviewed by a human professional.

The review queue is the required control point before export. Findings, paragraphs, maps, tables, caveats, source notes, and missing-data placeholders should all become review queue items.

## Not Implemented

- Production GIS pipelines or full environmental analysis.
- External API integrations beyond the explicit, opt-in NWI, USGS NHD, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL public downloaders.
- Basemap or imagery acquisition workflows.
- PDF export assembly pipelines.
- Public source downloads beyond the explicit, opt-in NWI, USGS NHD, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL public downloaders.
- Web app UI.
- UI-facing GPT review screens, prompt editing, or accepted-edit round-tripping. The backend has optional GPT section drafting only.
- Basemap-backed, raster, panel-sheet, or final cartographic map rendering.
- ML or computer vision detection.
- Scoring, ranking, or preferred alternative selection.
- Final PDF report export generation.
- Authentication or production deployment workflows.

## Current Project Workspaces

- `projects/trails`: trail alternative review context.
- `projects/conexon_projects`: broadband installation spot review context.

The root-level KMZ files are retained as reference originals. Phase 1 project manifests point to copied project-local inputs.

## Phase 1 Implementation Defaults

- Implementation surface: reusable services plus CLI.
- Geospatial stack: GeoPandas with Shapely, PyProj, Pyogrio, and Pandas.
- Project manifest format: JSON.
- Intermediate geometry format: GeoJSON.
- Geometry summary format: JSON.
- Generated project intermediates are ignored by Git.

## Phase 2A/2B Implementation Defaults

- Source catalog format: JSON at `config/source_catalog.json`.
- Local source materializer config: JSON at `config/local_source_materializers.json`.
- Project source registry format: JSON at `projects/<project_id>/config/sources.json`.
- Source population strategy: local source-layer registration first; live downloads are explicit and opt-in.
- Local source warehouse strategy: ignored root `sources/` may hold Mississippi-wide/bulk datasets; materialization clips configured warehouse layers to project analysis bounds and registers small project-ready GeoJSON outputs under ignored `projects/<project_id>/layers/`.
- Source acquisition strategy: compare project inputs and project registry against the catalog, then download only supported public sources when requested.
- Implemented downloaders: USFWS NWI wetlands through the public Wetlands REST MapServer layer; USGS NHD hydrography through The National Map NHD MapServer large-scale flowline and area layers; USFWS Critical Habitat through the public Critical Habitat FeatureServer final and proposed layers; EPA/ECHO regulated facilities through the public ECHO Facilities MapServer layer 0; FEMA NFHL effective Flood Hazard Zones through public NFHL MapServer layer 28.
- First spatial-check priority: wetlands/waterbodies, hydrography/crossings, land cover/disturbance, and soils.
- Flood hazard is retained as a secondary optional source category, not a first-pass driver for every project, and is downloaded only by direct `download-source` or optional-source acquisition.
- Generated spatial relationship outputs are JSON and GeoJSON under ignored project `intermediate/` directories.
- Source layers under `projects/<project_id>/layers/` are ignored by Git because they may be large, licensed, or project-specific.

Current CLI commands:

- `review-assist inspect-project <project_dir>`
- `review-assist list-sources [project_dir]`
- `review-assist import-source <project_dir> <source_id> <path>`
- `review-assist analyze-project <project_dir>`
- `review-assist build-project-geometry <project_dir>`
- `review-assist analyze-constraints <project_dir>`
- `review-assist generate-context <project_dir>`
- `review-assist resolve-sources <project_dir>`
- `review-assist resolve-source-gaps <project_dir>`
- `review-assist download-source <project_dir> usfws_nwi_wetlands`
- `review-assist download-source <project_dir> usgs_nhd_hydrography`
- `review-assist download-source <project_dir> usfws_critical_habitat`
- `review-assist download-source <project_dir> epa_envirofacts_echo`
- `review-assist download-source <project_dir> fema_nfhl_flood_hazard`
- `review-assist prepare-sources <project_dir>`
- `review-assist prepare-sources <project_dir> --include-optional-sources`
- `review-assist materialize-local-source <project_dir> usfws_nwi_wetlands`
- `review-assist materialize-local-source <project_dir> usfws_critical_habitat`
- `review-assist materialize-local-source <project_dir> usda_nrcs_ssurgo_soils`
- `review-assist materialize-local-source <project_dir> mdot_transportation_context`
- `review-assist materialize-local-source <project_dir> maris_boundary_context`
- `review-assist materialize-local-source <project_dir> maris_public_cultural_context`
- `review-assist materialize-local-source <project_dir> maris_community_facilities`
- `review-assist materialize-local-source <project_dir> maris_conservation_recreation_lands`
- `review-assist materialize-local-source <project_dir> local_utility_infrastructure`
- `review-assist materialize-local-sources <project_dir>`
- `review-assist generate-source-inventory <project_dir>`
- `review-assist generate-findings <project_dir>`
- `review-assist generate-tables <project_dir>`
- `review-assist generate-maps <project_dir>`
- `review-assist build-evidence-package <project_dir>`
- `review-assist generate-report-sections <project_dir>`
- `review-assist generate-report-sections <project_dir> --no-gpt-drafting`
- `review-assist generate-review-queue <project_dir>`
- `review-assist list-review-queue <project_dir>`
- `review-assist update-review-item <project_dir> <item_id> --status <status>`
- `review-assist export-report <project_dir>`
- `review-assist export-report <project_dir> --include-draft`
- `review-assist export-report <project_dir> --format markdown|docx|both`
- `review-assist build-demo-deliverable <project_dir>`
- `review-assist build-demo-deliverable <project_dir> --materialize-local-sources`
- `review-assist build-demo-deliverable <project_dir> --no-gpt-drafting`
- `review-assist build-mvp-deliverable <project_dir>`
- `review-assist build-mvp-deliverable <project_dir> --materialize-local-sources`
- `review-assist build-mvp-deliverable <project_dir> --include-optional-sources`
- `review-assist build-mvp-deliverable <project_dir> --include-optional-sources --no-gpt-drafting`
- `review-assist populate-for-review <project_dir>`
- `review-assist populate-for-review <project_dir> --materialize-local-sources`
- `review-assist populate-for-review <project_dir> --prepare-sources`
- `review-assist populate-for-review <project_dir> --materialize-local-sources --prepare-sources`
- `review-assist populate-for-review <project_dir> --prepare-sources --include-optional-sources`
- `review-assist populate-for-review <project_dir> --prepare-sources --no-gpt-drafting`

For `populate-for-review`, optional source acquisition is only valid when `--include-optional-sources` is paired with `--prepare-sources`.

## Workflow Artifact Defaults

- Report profile config: JSON at `config/report_profiles.json`.
- Finding template config: JSON at `config/finding_templates.json`.
- Report section template config: JSON at `config/report_section_templates.json`.
- Project context output: JSON at `projects/<project_id>/context/project_context.json`.
- Project geometry output: JSON at `projects/<project_id>/intermediate/project_geometry.json`.
- Project feature output: GeoJSON at `projects/<project_id>/intermediate/project_features.geojson`.
- Project analysis bounds output: GeoJSON at `projects/<project_id>/intermediate/project_analysis_bounds.geojson`.
- Source status output: JSON at `projects/<project_id>/source_status/source_status_set.json`.
- Source acquisition output: JSON at `projects/<project_id>/source_acquisition/source_acquisition_manifest.json`.
- Source acquisition downloads: GeoJSON under `projects/<project_id>/source_acquisition/downloads/`.
- Source materialization output: JSON at `projects/<project_id>/source_materialization/local_source_materialization_manifest.json`.
- Source materialized layers: GeoJSON under `projects/<project_id>/layers/<source_id>/`.
- Source inventory output: JSON at `projects/<project_id>/source_inventory/source_inventory.json`.
- Constraint results output: JSON at `projects/<project_id>/constraints/constraint_results.json`.
- Draft findings output: JSON at `projects/<project_id>/findings/draft_findings.json`.
- Comparison tables output: JSON at `projects/<project_id>/tables/comparison_tables.json`.
- Map manifest output: JSON at `projects/<project_id>/maps/map_manifest.json`.
- Draft map figures output: PNG files under `projects/<project_id>/maps/figures/`.
- Exported figure assets: copied PNG files under `projects/<project_id>/exports/assets/figures/` for included map figures.
- Evidence package output: JSON at `projects/<project_id>/evidence/evidence_package.json`.
- Draft report sections output: JSON at `projects/<project_id>/drafts/report_sections.json`.
- Review queue output: JSON at `projects/<project_id>/review_queue/review_queue.json`.
- Export manifest output: JSON at `projects/<project_id>/exports/export_manifest.json`.
- Markdown report output: Markdown at `projects/<project_id>/exports/environmental_constraints_report.md`.
- DOCX report output: Word document at `projects/<project_id>/exports/environmental_constraints_report.docx`.
- Demo deliverable manifest output: JSON at `projects/<project_id>/exports/deliverable_package_manifest.json`.
- Real-data MVP deliverable output: same Markdown/DOCX/export manifest paths, plus `deliverable_package_manifest.json` with package status, data lineage, and MVP quality metadata.
- Data lineage and quality output: embedded `data_lineage` and `mvp_quality` objects in export and deliverable manifests.
- Populate run manifest: JSON at `projects/<project_id>/populate_for_review/populate_for_review_run.json`.
- Generated context, source status, source acquisition, source materialization, source inventory, constraint results, draft findings, comparison tables, draft maps, evidence packages, draft report sections, review queue, and populate artifacts are ignored by Git.
- The current implementation creates normalized project geometry artifacts that classify inputs as point/site, line/corridor, polygon/area, or mixed context.
- The current implementation creates objective constraint results from registered local source layers, cropped to project analysis bounds and compared to normalized project features.
- The current implementation can materialize configured root `sources/` warehouse layers for NWI wetlands, USFWS Critical Habitat line/polygon data, SSURGO soil map units, MDOT/rail transportation context, utilities, administrative/boundary context, public cultural context, community facilities, and conservation/recreation lands into project-ready GeoJSON, preserving original attributes plus normalized Review Assist source fields.
- Materialized county-boundary context is read into `project_context.json` when available, and the study-area report section can cite the intersecting Mississippi county or counties.
- The current implementation can explicitly prepare sources by resolving catalog gaps, downloading NWI, USGS NHD hydrography, USFWS Critical Habitat, and EPA/ECHO regulated facilities when needed, optionally downloading FEMA NFHL flood hazard when requested, preserving acquisition provenance, and registering downloaded layers as normal project sources.
- Failed supported source downloads are nonfatal and now propagate as `failed` source status, uncertainty, finding, section, and review queue caveat context.
- The current implementation creates deterministic draft findings from source status records, constraint results, spatial relationships, and no-mapped-relationship checks.
- The current implementation creates descriptive comparison tables from source status, constraint result, grouped constraint, hydrography crossing, flood hazard, critical habitat, regulated facility, spatial relationship, and draft finding artifacts.
- The current implementation creates vector-only draft map figures from normalized project geometry and analyzed local source clipped layers, including project overview, source-context figures, and a combined environmental constraints overview when analyzed source layers contain mapped features. Figures include captions, source/method notes, related resource categories, legend, north arrow, draft label, and scale bar where CRS units allow it.
- The current implementation creates an evidence package from source lineage, source acquisition provenance, source status, source inventory, constraint results, findings, tables, maps, and section-level evidence bundles.
- The current implementation creates draft report sections from project context, source status, source inventory, draft findings, comparison tables, map manifests, evidence packages, and validation issues. The default provider is deterministic unless `GPT_DRAFTING=1`; the GPT provider drafts only from structured evidence and stores GPT provenance/guardrail warnings.
- The current implementation creates a lean review queue by default from deterministic draft findings, comparison tables, map figures, report sections, report-relevant missing-data placeholders, map/report/constraint warnings, and validation issues. Source inventory notes are optional.
- The current implementation can export accepted/edited review queue items into Markdown and DOCX report packages plus an export manifest. The preview option can include unaccepted non-rejected items and is explicitly marked as internal/pre-review. Included map PNGs are copied into the export asset folder and referenced from the Markdown/DOCX package while original map artifact provenance is preserved.
- The current implementation can build an internal demo deliverable package with `build-demo-deliverable`, which runs populate-for-review and preview export without changing review queue statuses.
- The current implementation can build a real-data guarded MVP deliverable package with `build-mvp-deliverable`, which runs source preparation before preview export, records data lineage and MVP quality counts, fails by default when no real source layer is available, and blocks test fixture/mock source records from MVP outputs.
- `populate-for-review` runs context generation, project geometry normalization, optional local source materialization, optional source preparation, source status resolution, source inventory generation, tolerant constraint analysis, deterministic draft finding generation, comparison table generation, map generation, evidence package generation, report section generation, and lean review queue generation into one inspectable run manifest. Optional source acquisition remains explicit through `--include-optional-sources`.
- GPT drafting uses root `.env` values: `OPENAI_API_KEY`, `OPENAI_INTERPRETER_MODEL`, and `GPT_DRAFTING`. `--no-gpt-drafting` forces deterministic behavior for individual runs.

Current audit status:

- The codebase has passing tests for ingestion, source registry validation, local source registration, local source materialization, county-boundary context enrichment, source acquisition with mocked NWI, USGS NHD, USFWS Critical Habitat, EPA/ECHO, and FEMA NFHL responses, failed-download propagation, synthetic spatial checks, project geometry normalization, constraint analysis, active sample workspace smoke checks, project context/source status artifacts, source inventory/provenance artifacts, draft finding generation, comparison table artifacts including grouped, hydrography crossing, flood hazard, critical habitat, and regulated facility summaries, vector-only map artifacts, evidence package generation, deterministic/GPT draft report section artifacts, Markdown/DOCX export compilation, inline export table/figure rendering, internal demo deliverable packaging, real-data MVP deliverable guardrails and quality metadata, render-error handling, review queue generation/update behavior, malformed optional artifact handling, and populate-for-review orchestration.
- The implementation validates source registry booleans, duplicate source IDs, project/source registry ID mismatches, non-object manifest entries, optional source metadata, source inventory record counts, comparison table counts/statuses, and negative buffer values.
- `scripts/verify.ps1` provides a repeatable local readiness check that creates the virtual environment when needed, installs development dependencies, runs pytest, and smoke-checks the current CLI workflows.
- See `docs/CODE_AUDIT.md` for latest audit notes.

## Archive Directories

- `archive/`: general archive for retained but inactive project-level files.
- `docs/archive/`: archive for superseded or historical documentation.
