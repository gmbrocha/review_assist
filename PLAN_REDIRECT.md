# Plan Redirect: Constraint Engine Plus Review Queue Plus Export

## Specific Goal

Build a local, workspace-based app that accepts a project input package, normalizes the project geometry, compares the input package against our developed source stack/data source catalog to determine which relevant layers are already present and which are missing, gathers or requests the missing relevant source layers, runs objective constraint overlap/proximity analysis, generates visuals and structured findings, uses GPT calls during report generation to draft aligned pre-review copy from those structured artifacts and visuals, routes every generated finding/table/map/section through a human review queue, and exports only reviewer-accepted content into an editable report package.

The app is a constraint engine plus a review queue plus an export compiler.

The app is not a recommendation engine. It must not choose, reject, rank, score, or recommend a trail, route, site, service location, service area, corridor, alternative, or project feature. It presents objective constraints so someone else can make decisions outside the tool.

The app is not trails-specific. Trails and Conexon are sample workspaces only. The system must work as a blank project machine that can accept point, line, polygon, or mixed project inputs.

The review queue is downstream of the constraint engine. Review queue item count is not a readiness metric. A useful run is one that correctly parses project geometry, builds analysis bounds, gathers source layers, identifies objective constraints, drafts useful report sections, preserves uncertainty, and lets the reviewer accept or edit small pieces independently.

## Workflow We Are Building Toward

1. Create or open a local project workspace.
2. Add project inputs such as KMZ/KML, GeoJSON, shapefiles, GeoPackages, reports, maps, imagery, notes, or PDFs.
3. Normalize project geometry into point/site, line/corridor, polygon/area, or mixed project features.
4. For line inputs, group segmented line strings into meaningful project features without inventing missing connections.
5. Preserve individual point features and style/color grouping metadata for point-heavy projects.
6. Derive project analysis bounds from normalized project features plus configured buffer assumptions.
7. Resolve the report profile and needed source categories.
8. Compare the user input package and registered project sources against the source stack/data source catalog.
9. Produce a clear missing-source set: layers already present, layers available locally, layers to seek from the catalog, layers requiring manual/restricted handling, and layers not available.
10. Acquire source layers by local registration first, then by approved public downloaders where implemented.
11. Track source status, source provenance, licensing/terms, dates, limitations, and uncertainty.
12. Crop source layers to the project analysis bounds.
13. Run deterministic constraint checks by project feature and source category.
14. Store first-class constraint results with relationship type, source labels, measurements, and provenance.
15. Generate draft findings from constraint results and report-relevant source gaps.
16. Generate comparison tables and draft maps from structured artifacts.
17. Use GPT-assisted report generation to draft pre-review copy that aligns with the structured findings, tables, visuals, map references, source gaps, and validation issues.
18. Generate small editable report sections from findings, tables, maps, source gaps, validation issues, and GPT-assisted draft copy where enabled.
19. Send findings, report sections, maps, tables, validation issues, and report-relevant caveats into the review queue.
20. Preserve reviewer edits, notes, status, and export eligibility across regeneration.
21. Export only accepted or explicitly included reviewed content into an editable report package.

## Deliverable Template From Example Report

The file `env_constraints_report_20260511_EXAMPLE_ONLY.docx` is a real structural template for the report we are trying to generate. We should use it to define report sections, subsections, table needs, visual needs, attachment needs, and export layout expectations. We should not reuse its project-specific facts, locations, conclusions, dates, or figure numbering as authoritative content.

The generated report should follow this deliverable shape unless a reviewer selects a different report profile.

### Front Matter

- Cover/title page.
- Project name.
- Project location/counties or service area.
- Report title, such as Environmental Constraints Report.
- Date.
- Project numbers or client/project identifiers when available.
- List of figures.
- List of tables.
- List of attachments.

### Executive Summary

Purpose:

- Summarize the project, reviewed project features, source stack used, main objective constraints, source gaps, and follow-up needs.
- Use GPT-assisted pre-review copy after constraint findings, tables, and visuals exist.
- Keep language objective and screening-level.

Visual/table needs:

- No required standalone visual in the example section.
- May reference key maps/tables generated later in the report.

### Introduction

Purpose:

- Introduce the project and explain that the report supports early constraints review.
- State that the report presents objective constraints only and does not choose, rank, reject, or recommend project features.

Subsections:

- Relationship with the broader study or planning process.
- Study Area.

Visual/table needs:

- Study Area should reference a project overview map when available.
- If the project has alternatives, routes, service points, service areas, sites, or polygons, this section should identify them in neutral descriptive language.

### Methodology

Purpose:

- Explain how the app parsed project inputs, compared them against the source stack/data source catalog, resolved missing sources, acquired or registered layers, cropped sources, ran constraint analysis, generated visuals, and created review queue items.

Subsections:

- Data Collection and Sources.
- Mapping and Analysis Procedures.
- Limitations and Data Gaps.

Visual/table needs:

- Data Collection and Sources should reference the source status/source inventory table.
- Mapping and Analysis Procedures should reference the project overview map and generated constraint maps.
- Limitations and Data Gaps should include report-relevant source gaps, gated sources, failed downloads, stale data warnings, and desktop-screening caveats.

### Environmental Constraints Inventory

Purpose:

- Present objective constraints by resource category and project feature.
- Adapt feature labels to the project type: trail alternatives, route corridors, service points, service areas, sites, polygons, or mixed project features.
- Do not force trail-specific wording when the input is not a trail project.

Overview visual needs:

- Overall Environmental Constraints Inventory Map.
- Panel Index Map when the project extent is too large for one detailed map.
- Panel Maps for corridor sections, site clusters, or service areas where detailed local review is needed.

### Natural and Ecological Resources

#### Wetlands and Waterbodies

Purpose:

- Summarize NWI/wetland/waterbody constraints and any desktop imagery context.
- Include project-feature-specific subsections where useful, such as each route, corridor, service area, or site group.

Visual/table needs:

- Figure slot: Wetlands and Waterbodies in and near the project area.
- Table slot: Descriptions of wetlands and waterbodies present within or near project features.

#### Floodplains and Floodways

Purpose:

- Summarize FEMA flood zones, floodways, and flood-related planning constraints where relevant.

Visual/table needs:

- Figure slot: FEMA Flood Zones in and near the project area.
- Table slot: FEMA Flood Zones within or near project features.

#### Water Quality

Purpose:

- Summarize streams, rivers, HUC/subwatershed context, crossings, impaired waters, and downstream water quality considerations.

Visual/table needs:

- Figure slot: Streams and impaired waters within relevant subwatersheds or near project features.

#### Protected Species and Critical Habitat

Purpose:

- Summarize federal/state species, critical habitat, IPaC, heritage program, and agency consultation status.
- Clearly distinguish GIS-checkable habitat layers from manual agency consultation/documents.

Visual/table needs:

- Figure slot when GIS species/habitat/critical habitat layers are available.
- Review item/caveat when source is manual, gated, or consultation-based.

### Cultural and Historic Resources

Purpose:

- Summarize public historic resources and restricted/manual cultural review status.
- Avoid exposing sensitive restricted archaeological information in inappropriate outputs.

Subsections:

- Archaeological Sites.
- Historic Structures and Districts.

Visual/table needs:

- Figure slot: Cultural Resources Sites in or near the project area, using only appropriate public or reviewer-approved data.
- Review item/caveat for restricted archaeology or manual SHPO/MDAH review.

### Community Resources

Subsections and visual needs:

- Fire/EMS Stations.
  - Figure slot: Fire Stations in or near the project area.
- Government Buildings.
  - Figure slot: Government Offices near the project area.
- Education Facilities.
  - Figure slot: Schools and Childcare Facilities in or near the project area.
- Health Care Facilities.
  - Figure slot: Health Care Facilities near the project area.
- Places of Worship.
  - Figure slot: Places of Worship in or near the project area.
- Parks and Recreation Areas.
  - Figure slot when parks/recreation resources are present or relevant.

Purpose:

- Present access-sensitive community resources objectively.
- Identify where project features intersect, cross, or are near community resources.
- Do not make final social impact conclusions without reviewer approval.

### Utility and Infrastructure Considerations

Subsections and visual needs:

- Public Water Supply.
  - Figure slot: Public Water Supply Wells or water infrastructure near the project area.
- Utility Infrastructure.
  - Figure slot: Utility crossings, corridors, or infrastructure near project features.
- Energy Infrastructure.
  - Figure slot: Energy Infrastructure near the project area.
- Airports.
  - Figure slot when airport/aviation constraints are present or relevant.

Purpose:

- Present objective utility/infrastructure crossings, overlaps, proximity, and coordination needs.

### Contamination Risks

Subsections and visual needs:

- Hazardous Materials Sites.
  - Figure slot: Hazardous Waste, regulated facility, cleanup, UST, or contamination sites near the project area.
- Oil Wells.
  - Figure slot when oil/gas well data is present or relevant.

Purpose:

- Present objective contamination/regulatory facility context.
- Preserve risk language as pre-review and screening-level unless reviewer-provided hazardous materials conclusions exist.

### Socioeconomic and Business Considerations

Subsections:

- Demographic Characteristics.
- Local Businesses and Economic Nodes.

Visual/table needs:

- Figure slot: Census Tracts along or near the project area.
- Table slot: Income demographics of relevant census areas.
- Table slot: Demographic composition of relevant census areas.
- Optional business/economic node map when source data is available.

Purpose:

- Present demographic and business access context without making final equity, impact, or recommendation conclusions.

### Conclusion and Next Steps

Purpose:

- Summarize objective constraint themes.
- Identify source gaps and review/coordination needs.
- Avoid choosing or recommending project features.
- State that future planning, design, agency coordination, field verification, and human decision-making occur outside the automated tool.

Visual/table needs:

- No required standalone visual in the example section.
- May reference accepted maps/tables and unresolved review queue items.

### Attachments

The example report uses attachments as part of the deliverable structure. The app should support attachment placeholders and eventually export packages.

- Attachment A: Project Maps.
  - Overall Environmental Constraints Inventory Map.
  - Panel Index Map.
  - Panel Maps by corridor section, site group, service area, or project feature cluster.
- Attachment B: Hazardous Materials Report.
  - Generated or reviewer-provided hazardous materials support, when available.
- Attachment C: Agency Consultation Letters.
  - Reviewer-provided or generated placeholder references for USFWS, SHPO/MDAH, MDWFP, FEMA, MDEQ, local agencies, or other relevant coordination.

### Visual Inventory From The Example Report

The example DOCX contains 13 embedded media files and captions/list entries that define the visual categories we should be able to produce or mark as needed:

- Wetlands and Waterbodies in and near the project area.
- FEMA Flood Zones in and near the project area.
- Streams and impaired waters within relevant subwatersheds.
- Cultural Resources Sites in or near the project area.
- Fire Stations in or near the project area.
- Government Offices near the project area.
- Schools and Childcare Facilities in or near the project area.
- Health Care Facilities near the project area.
- Places of Worship in or near the project area.
- Public Water Supply Wells near the project area.
- Energy Infrastructure near the project area.
- Hazardous Waste or regulated facility sites near the project area.
- Census Tracts along or near the project area.

The app should use these as map/figure target types. If the necessary source data is missing, the report section should get a reviewable caveat or visual-needed item instead of silently omitting the visual.

### Table Inventory From The Example Report

The example report identifies these table patterns:

- Wetlands and waterbodies description table.
- FEMA flood zone summary table.
- Income demographics table.
- Demographic composition table.

The app should generate these where source data is available and create reviewable missing-data placeholders where source data is absent or manual.

## Completed

- [x] Repository scaffold exists.
- [x] Project workspaces exist for `projects/trails` and `projects/conexon_projects`.
- [x] Root example KMZ files were copied into project-local `inputs/` folders.
- [x] Project manifests exist under each project `config/project.json`.
- [x] KMZ/KML ingestion exists.
- [x] KML XML parsing avoids relying on optional GDAL KML driver support.
- [x] Point, LineString, and Polygon input parsing exists.
- [x] Geometry inspection writes `intermediate/geometry_summary.json`.
- [x] Normalized input GeoJSON artifacts are generated under project `intermediate/`.
- [x] Source catalog exists at `config/source_catalog.json`.
- [x] Project source registries exist at `projects/<id>/config/sources.json`.
- [x] Local source registration exists through `review-assist import-source`.
- [x] Legacy raw spatial analysis exists through `review-assist analyze-project`.
- [x] Project context generation exists through `review-assist generate-context`.
- [x] Source status resolution exists through `review-assist resolve-sources`.
- [x] Source inventory/provenance generation exists through `review-assist generate-source-inventory`.
- [x] Deterministic draft finding generation exists through `review-assist generate-findings`.
- [x] Comparison table generation exists through `review-assist generate-tables`.
- [x] Vector-only map generation exists through `review-assist generate-maps`.
- [x] Deterministic report section generation exists through `review-assist generate-report-sections`.
- [x] JSON-backed review queue generation exists through `review-assist generate-review-queue`.
- [x] Review queue listing exists through `review-assist list-review-queue`.
- [x] Review queue status/note/export updates exist through `review-assist update-review-item`.
- [x] Populate orchestration exists through `review-assist populate-for-review`.
- [x] Project geometry normalization exists through `review-assist build-project-geometry`.
- [x] Project geometry artifacts are written to `intermediate/project_geometry.json`.
- [x] Normalized project features are written to `intermediate/project_features.geojson`.
- [x] Project analysis bounds are written to `intermediate/project_analysis_bounds.geojson`.
- [x] Geometry classification supports `point_site`, `line_corridor`, `polygon_area`, and `mixed`.
- [x] Segmented line strings are grouped by placemark name, style URL, then candidate label.
- [x] Connected line pieces are merged with Shapely line merge behavior.
- [x] Disconnected line pieces are preserved as multipart geometry instead of inventing connections.
- [x] Point-heavy projects preserve individual point features and style/color grouping metadata.
- [x] Analysis bounds use normalized project features plus configured default buffer.
- [x] First-class constraint analysis exists through `review-assist analyze-constraints`.
- [x] Constraint results are written to `projects/<id>/constraints/constraint_results.json`.
- [x] Constraint clipped layers are written under `projects/<id>/constraints/clipped_layers/`.
- [x] Constraint results preserve project feature id/name/group/geometry role.
- [x] Constraint results preserve source id/name/category.
- [x] Constraint results preserve relationship type.
- [x] Constraint results preserve source feature labels.
- [x] Constraint results preserve length/area/distance measurements where applicable.
- [x] Constraint results preserve screening provenance.
- [x] Constraint checks include `intersects`, `crosses`, `contains`, `overlaps`, and `nearest_within_buffer`.
- [x] `generate-findings` prefers `constraint_results.json` when present.
- [x] `generate-tables` includes a constraint summary table.
- [x] `generate-maps` prefers constraint clipped layers when constraint results exist.
- [x] `populate-for-review` now runs project geometry normalization before source/constraint/report/review artifacts.
- [x] `populate-for-review` now routes through constraint analysis instead of legacy raw spatial analysis.
- [x] `populate-for-review` records project geometry, project features, analysis bounds, and constraint results in the run manifest.
- [x] Review queue generation defaults to a lean queue.
- [x] Source inventory review notes are opt-in with `--include-source-inventory`.
- [x] Source status records are not default review queue volume.
- [x] Missing-source placeholders remain only as report-relevant caveats.
- [x] Legacy spatial relationship queue items are suppressed when first-class constraint results exist.
- [x] Reviewer state is preserved across regeneration.
- [x] Deterministic section drafting provider interface exists.
- [x] No live GenAI/API calls are made in the current section drafting slice.
- [x] `.gitignore` ignores generated project constraint artifacts.
- [x] `scripts/verify.ps1` exists as a repeatable readiness check.
- [x] Active sample workspace smoke tests exist.
- [x] Unit and integration tests cover project geometry normalization and constraint analysis.
- [x] Full test suite passes.
- [x] Local readiness script passes.
- [x] Example report structure from `env_constraints_report_20260511_EXAMPLE_ONLY.docx` is captured as the target deliverable section and visual map.
- [x] Source gap resolution exists through `review-assist resolve-source-gaps`.
- [x] Source acquisition manifests are written to `projects/<id>/source_acquisition/source_acquisition_manifest.json`.
- [x] Project source acquisition downloads are stored under ignored `projects/<id>/source_acquisition/downloads/`.
- [x] Project inputs tagged with `source_id` or unambiguous `source_category` can be registered as provided source layers.
- [x] USFWS NWI wetlands is implemented as the first public downloader.
- [x] NWI downloads preserve service URL, layer id, access date, output path, feature count, checksum, limitations, and warnings.
- [x] Successful NWI downloads are registered in the project source registry as normal `local_file` sources with `status: downloaded`.
- [x] Existing reviewer-supplied local source layers are preserved instead of being overwritten by downloads.
- [x] Source inventory records include source acquisition/download provenance when an acquisition manifest exists.
- [x] `review-assist download-source <project_dir> usfws_nwi_wetlands` exists.
- [x] `review-assist download-source <project_dir> usgs_nhd_hydrography` exists.
- [x] USGS NHD hydrography downloads query The National Map NHD MapServer large-scale flowline and area layers by project analysis bounds.
- [x] Downloaded NHD hydrography is combined into a project-local GeoJSON source layer and registered as a normal `local_file` source with `status: downloaded`.
- [x] Downloaded source layers preserve original attributes while adding lightweight normalized Review Assist source, layer, label, and type fields.
- [x] Hydrography constraints now feed stream/crossing findings, a hydrography crossing summary table, source-context maps, report sections, and review queue items.
- [x] `review-assist prepare-sources <project_dir>` exists.
- [x] `populate-for-review --prepare-sources` can resolve gaps and run supported source downloads before constraint analysis.
- [x] `populate-for-review` without `--prepare-sources` keeps the previous no-live-download behavior.
- [x] Report section templates now include front matter, executive summary, introduction/study area, methodology subsections, environmental constraints inventory, conclusion/next steps, and attachment placeholders.
- [x] Report section artifacts include export group metadata plus visual and table slots.
- [x] Review queue items include export group metadata for report assembly.
- [x] Markdown export compilation exists through `review-assist export-report`.
- [x] Export manifests are written to `projects/<id>/exports/export_manifest.json`.
- [x] Editable Markdown reports are written to `projects/<id>/exports/environmental_constraints_report.md`.
- [x] Default export includes accepted/edited review queue items and explicitly export-eligible unable-to-verify items only.
- [x] Preview export exists through `review-assist export-report --include-draft` and is clearly labeled as internal/pre-review.

## Still To Go

### 1. Downloadable Source Layer System

This milestone has started. The implemented baseline exists so the app can compare project inputs/registry against the catalog, acquire NWI and USGS NHD hydrography when explicitly requested, and feed those downloaded sources through the same constraint/report/review flow as local source layers.

- [x] Treat the source stack/data source catalog as the comparison baseline for deciding what the project input package does and does not already contain.
- [x] Add a source gap resolver that compares project inputs, registered local sources, and required report categories against the catalog.
- [x] Emit a missing-source set before acquisition: present, registered local, downloaded, downloadable, gated/restricted, manual/reviewer-supplied, optional, unavailable, and failed.
- [x] Add a source acquisition service that can download approved public source layers.
- [x] Keep local registration as a supported path; downloads should not replace reviewer-supplied local layers.
- [x] Add an acquisition manifest at `projects/<id>/source_acquisition/source_acquisition_manifest.json`.
- [x] Add a per-source download/cache directory under ignored project folders.
- [x] Add CLI commands for `resolve-source-gaps`, `download-source`, and `prepare-sources`.
- [x] Make `populate-for-review` optionally acquire downloadable sources before constraint analysis through `--prepare-sources`.
- [x] Record URL, access date, cache path, checksum where practical, per-layer provenance, and limitations for implemented downloaded sources.
- [x] Treat failed downloads as nonfatal source status/review caveats when the rest of the workflow can continue.
- [x] Extend implemented source catalog entries with basic downloader metadata: endpoint, format, query method, source layers, and expected label/type fields.
- [ ] Extend source catalog entries with complete attribution, license/terms, update date handling, refresh cadence, and full expected schema details.
- [ ] Do not silently call paid services.
- [ ] Do not use credentials or restricted systems without explicit approval.
- [ ] Record source date, terms/licensing, expected refresh cadence, and full schema normalization details for every downloaded source as each downloader is added.

First downloader candidates:

- [x] USFWS NWI wetlands/waterbodies.
- [x] USGS hydrography/stream data.
- [ ] FEMA NFHL flood hazard data where relevant.
- [ ] EPA regulated facility data where a stable public download path is practical.
- [ ] Census TIGER/ACS community context.
- [ ] Public critical habitat layers.

Downloader implementation rule:

Implement downloaders one source at a time, with tests, provenance, and a real sample run before adding the next source. Do not create a broad fake downloader layer that pretends sources are available.

### 2. Source Schema Normalization

- [x] Preserve original source attributes while adding lightweight normalized source/layer/label/type fields for downloaded sources.
- [x] Add source-specific label extraction rules for implemented NWI and NHD downloaders.
- [ ] Define the full normalized source feature contract: label, category, subtype, source date, confidence/quality flags, and original feature id.
- [ ] Add source-specific category/subtype mapping for wetlands, streams, flood zones, soils, facilities, parcels, utilities, and community resources.
- [ ] Add validation warnings for missing CRS, unknown schema, empty layers, invalid geometries, and stale source dates.

### 3. Constraint Engine Depth

- [ ] Expand geometry-specific checks by role: point/site, line/corridor, polygon/area, and mixed.
- [ ] Support configurable per-category buffers.
- [ ] Support source-specific buffers already in the registry more clearly in reports.
- [ ] Add better length summaries for line through polygon resources.
- [ ] Add crossing counts for line/line resources.
- [ ] Add acreage summaries for polygon/polygon overlaps.
- [ ] Add nearest-feature summaries for point/site review.
- [ ] Add grouped summaries by project feature and source category.
- [ ] Add no-overlap records where report-relevant, not as noisy queue volume.
- [ ] Add geometry repair/cleaning for common invalid source geometries.
- [ ] Add clear handling for very large source layers.

### 4. Project Input Generalization

- [ ] Support direct GeoJSON project inputs.
- [ ] Support shapefile project inputs.
- [ ] Support GeoPackage project inputs.
- [ ] Support reviewer correction of geometry role when automatic classification is wrong.
- [ ] Support project feature renaming/grouping before analysis.
- [ ] Support explicit project boundary inputs separate from route/site features.
- [ ] Support service area grouping for point-heavy projects such as broadband locations.
- [ ] Preserve KML/KMZ style metadata in a reviewer-friendly way.

### 5. GPT-Assisted Report Generation

- [ ] Add a GPT-backed report drafting provider alongside the deterministic provider.
- [ ] Feed GPT only structured inputs: constraint findings, source statuses, source provenance, table summaries, map/figure references, validation issues, report section purpose, and reviewer instructions.
- [ ] Generate pre-review copy that aligns with generated visuals and explicitly references relevant map/table/figure IDs where appropriate.
- [ ] Keep GPT output editable and reviewable as `report_section` items.
- [ ] Store prompt/provider/model/version metadata in provenance.
- [ ] Preserve source refs and related finding/table/figure IDs on GPT-drafted sections.
- [ ] Add checks that GPT copy does not introduce unsupported source facts.
- [ ] Add checks that GPT copy does not recommend, rank, choose, or reject alternatives.
- [ ] Add a deterministic fallback when GPT is unavailable or disabled.

### 6. Report Section Quality

- [x] Make report sections match the `env_constraints_report_20260511_EXAMPLE_ONLY.docx` structure more closely unless another report profile is selected.
- [x] Add table and map/visual slots to section artifacts for export placeholders.
- [x] Separate front matter, executive summary, introduction/study area, methodology, constraints inventory, resource sections, conclusion, attachments, and reviewer follow-up more cleanly.
- [ ] Improve resource-specific section language using constraint summaries and no-overlap/source-gap context.
- [ ] Add tables/map references into section content more deliberately beyond slot placeholders.
- [ ] Keep deterministic narrative available as the fallback path.
- [ ] Add an explicit "objective constraints only" statement to generated methodology/limitations language.

### 7. Review Queue UI Model

- [ ] Define the first desktop UI screens around the review queue.
- [ ] Show small editable sections, not one monolithic report.
- [ ] Support accept, reject, edit, notes, needs verification, and export eligibility.
- [ ] Show provenance and source refs next to every review item.
- [ ] Show map/table previews in review context.
- [ ] Preserve reviewer state through reruns.
- [ ] Make queue filters useful by type, status, source category, project feature, and export section.

### 8. Export Compiler

- [x] Define export package manifest.
- [x] Export accepted/explicitly included report sections.
- [x] Export accepted findings.
- [x] Export accepted tables.
- [x] Export accepted map figures.
- [x] Include source/provenance references.
- [x] Include known limitations and unresolved source gaps as export warnings.
- [x] Exclude rejected items.
- [x] Include unable-to-verify items only when explicitly export eligible.
- [x] Decide first export target: Markdown plus JSON manifest.
- [x] Preserve editability in the exported report.
- [ ] Add DOCX export once Markdown assembly proves ordering, filtering, source refs, caveats, and map/table reference behavior.

### 9. Map and Figure Improvements

- [ ] Add constraint-source maps from downloaded and registered layers.
- [ ] Add better symbology by project feature and source category.
- [ ] Add legends, scale bars, north arrows, source notes, and draft labels.
- [ ] Add panel maps or per-feature maps where needed.
- [ ] Add optional basemap/imagery only after terms and implementation path are clear.
- [ ] Keep imagery observations as review items, not authoritative facts.

### 10. GenAI Boundary

- [ ] Keep GenAI out of deterministic GIS/source checks.
- [ ] Use GPT during report generation to draft pre-review copy from structured findings, source gaps, visuals, map/table refs, and explicit report section purposes.
- [ ] Require GPT output to enter the review queue.
- [ ] Never let GenAI invent source-backed facts.
- [ ] Never let GenAI recommend, rank, choose, or reject alternatives.

### 11. Documentation and Drift Control

- [ ] Keep `PLAN_REDIRECT.md` aligned with the actual roadmap.
- [ ] Keep `docs/ROADMAP.md` implementation-focused.
- [ ] Keep `docs/WORKFLOW_MODEL.md` as the canonical workflow truth model.
- [ ] Keep `docs/CURRENT_STATE.md` honest about what exists and what does not.
- [ ] Update docs whenever a phase changes behavior.
- [ ] Avoid using review queue item count as a readiness signal.
- [ ] Keep "objective constraints only" language visible in product and report docs.

## Non-Negotiables

- The app must not choose a preferred alternative.
- The app must not reject a project feature.
- The app must not rank or score options.
- The app must not pretend desktop screening is field verification.
- The app must not hide missing or gated data.
- The app must not invent source-backed evidence.
- The app must not export unreviewed generated content.
- The app must not automate restricted data access without explicit approval.
- The app must stay project-type agnostic.
- The app must keep deterministic constraint analysis separate from narrative drafting.

## Immediate Next Move

Continue evidence depth after the NWI/NHD acquisition baseline, not review-queue volume for its own sake.

The practical next source milestone is:

1. Add the next highest-value public downloader one source at a time, likely FEMA NFHL, NLCD, soils, or critical habitat depending on report need.
2. Expand source schema normalization beyond lightweight label/type fields into a clear source-feature contract.
3. Improve constraint summaries by feature/category so report sections can cite counts, lengths, areas, and caveats cleanly.
4. Improve maps/figures toward template-ready visuals while preserving source provenance.
5. Keep every generated finding, table, map, caveat, and section behind the review queue before export.

GPT drafting and DOCX export come after the source-backed evidence and review-gated assembly path remain stable.
