# Current State

## Phase

Phase 0 scaffold/planning is complete. Phase 1 KMZ/KML ingestion and geometry inspection is implemented for the current prototype baseline. The first Phase 2A/2B baseline is also implemented: source catalog, project source registries, local source registration, and local spatial relationship checks. The Phase 2C catalog-driven source acquisition baseline is implemented with explicit USFWS NWI, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard downloaders. Phase 3 project context/source status artifacts, the first Phase 4 JSON-backed review queue baseline, Phase 5 populate-for-review orchestration, Phase 6A deterministic finding generation, Phase 6B source provenance/comparison tables, Phase 6C vector-only map/figure generation, Phase 6D deterministic draft report section generation, the first Markdown export compiler, and the first constraint-engine baseline are implemented.

The repository currently contains documentation, project workspaces, sample KMZ/KML preview utilities, project manifests, project-local input copies, Python service/CLI implementation for Phase 1 inspection, Phase 2 source catalog/spatial check/source acquisition services, project geometry normalization, constraint overlap/proximity analysis, workflow-native project context/source status services, source inventory/provenance artifacts, deterministic draft finding generation, comparison table artifacts including grouped, hydrography, flood hazard, critical habitat, and regulated facility summaries, vector-only map artifacts, deterministic draft report section artifacts, JSON review queue services, Markdown export services, and populate-for-review orchestration. No production workflow has been implemented.

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
- DOCX/PDF export assembly pipelines.
- Public source downloads beyond the explicit, opt-in NWI, USGS NHD, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL public downloaders.
- Desktop GUI.
- LLM-assisted narrative synthesis.
- Basemap-backed, raster, panel-sheet, or final cartographic map rendering.
- ML or computer vision detection.
- Scoring, ranking, or preferred alternative selection.
- Final DOCX/PDF report export generation.
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
- Project source registry format: JSON at `projects/<project_id>/config/sources.json`.
- Source population strategy: local source-layer registration first; live downloads are explicit and opt-in.
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
- `review-assist generate-source-inventory <project_dir>`
- `review-assist generate-findings <project_dir>`
- `review-assist generate-tables <project_dir>`
- `review-assist generate-maps <project_dir>`
- `review-assist generate-report-sections <project_dir>`
- `review-assist generate-review-queue <project_dir>`
- `review-assist list-review-queue <project_dir>`
- `review-assist update-review-item <project_dir> <item_id> --status <status>`
- `review-assist export-report <project_dir>`
- `review-assist export-report <project_dir> --include-draft`
- `review-assist populate-for-review <project_dir>`
- `review-assist populate-for-review <project_dir> --prepare-sources`
- `review-assist populate-for-review <project_dir> --prepare-sources --include-optional-sources`

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
- Source inventory output: JSON at `projects/<project_id>/source_inventory/source_inventory.json`.
- Constraint results output: JSON at `projects/<project_id>/constraints/constraint_results.json`.
- Draft findings output: JSON at `projects/<project_id>/findings/draft_findings.json`.
- Comparison tables output: JSON at `projects/<project_id>/tables/comparison_tables.json`.
- Map manifest output: JSON at `projects/<project_id>/maps/map_manifest.json`.
- Draft map figures output: PNG files under `projects/<project_id>/maps/figures/`.
- Draft report sections output: JSON at `projects/<project_id>/drafts/report_sections.json`.
- Review queue output: JSON at `projects/<project_id>/review_queue/review_queue.json`.
- Export manifest output: JSON at `projects/<project_id>/exports/export_manifest.json`.
- Markdown report output: Markdown at `projects/<project_id>/exports/environmental_constraints_report.md`.
- Populate run manifest: JSON at `projects/<project_id>/populate_for_review/populate_for_review_run.json`.
- Generated context, source status, source acquisition, source inventory, constraint results, draft findings, comparison tables, draft maps, draft report sections, review queue, and populate artifacts are ignored by Git.
- The current implementation creates normalized project geometry artifacts that classify inputs as point/site, line/corridor, polygon/area, or mixed context.
- The current implementation creates objective constraint results from registered local source layers, cropped to project analysis bounds and compared to normalized project features.
- The current implementation can explicitly prepare sources by resolving catalog gaps, downloading NWI, USGS NHD hydrography, USFWS Critical Habitat, and EPA/ECHO regulated facilities when needed, optionally downloading FEMA NFHL flood hazard when requested, preserving acquisition provenance, and registering downloaded layers as normal project sources.
- Failed supported source downloads are nonfatal and now propagate as `failed` source status, uncertainty, finding, section, and review queue caveat context.
- The current implementation creates deterministic draft findings from source status records, constraint results, spatial relationships, and no-mapped-relationship checks.
- The current implementation creates descriptive comparison tables from source status, constraint result, grouped constraint, hydrography crossing, flood hazard, critical habitat, regulated facility, spatial relationship, and draft finding artifacts.
- The current implementation creates vector-only draft map figures from normalized project geometry and analyzed local source clipped layers.
- The current implementation creates deterministic draft report sections from project context, source status, source inventory, draft findings, comparison tables, map manifests, and validation issues.
- The current implementation creates a lean review queue by default from deterministic draft findings, comparison tables, map figures, report sections, report-relevant missing-data placeholders, map/report/constraint warnings, and validation issues. Source inventory notes are optional.
- The current implementation can export accepted/edited review queue items into a Markdown report package and export manifest. The preview option can include unaccepted non-rejected items and is explicitly marked as internal/pre-review.
- `populate-for-review` runs context generation, project geometry normalization, optional source preparation, source status resolution, source inventory generation, tolerant constraint analysis, deterministic draft finding generation, comparison table generation, map generation, report section generation, and lean review queue generation into one inspectable run manifest. Optional source acquisition remains explicit through `--include-optional-sources`.

Current audit status:

- The codebase has passing tests for ingestion, source registry validation, local source registration, source acquisition with mocked NWI, USGS NHD, USFWS Critical Habitat, EPA/ECHO, and FEMA NFHL responses, failed-download propagation, synthetic spatial checks, project geometry normalization, constraint analysis, active sample workspace smoke checks, project context/source status artifacts, source inventory/provenance artifacts, draft finding generation, comparison table artifacts including grouped, hydrography crossing, flood hazard, critical habitat, and regulated facility summaries, vector-only map artifacts, draft report section artifacts, Markdown export compilation, render-error handling, review queue generation/update behavior, malformed optional artifact handling, and populate-for-review orchestration.
- The implementation validates source registry booleans, duplicate source IDs, project/source registry ID mismatches, non-object manifest entries, optional source metadata, source inventory record counts, comparison table counts/statuses, and negative buffer values.
- `scripts/verify.ps1` provides a repeatable local readiness check that creates the virtual environment when needed, installs development dependencies, runs pytest, and smoke-checks the current CLI workflows.
- See `docs/CODE_AUDIT.md` for latest audit notes.

## Archive Directories

- `archive/`: general archive for retained but inactive project-level files.
- `docs/archive/`: archive for superseded or historical documentation.
