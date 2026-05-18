# Review Assist Canonical Plan

This is the canonical planning source for the current Review Assist implementation direction. It supersedes the older root planning documents for active planning; archived copies are retained only for historical context. If another active document duplicates or conflicts with this plan, this plan controls.

`docs/domains/WORKFLOW_MODEL.md` remains an important workflow model and should be aligned to this plan during implementation. When the two duplicate a current workflow decision, this plan is the source of truth unless a later approved decision updates it.

The immediate product concern is that the current generated deliverable can become far too large, such as a 640-page package. The redirected workflow should identify the discrete deliverable items first, then generate only the source-backed items needed for those deliverables, with reviewer control over what enters export.

## Canonical Source Hierarchy

Active source hierarchy:

- `CANONICAL_PLAN.md` is the canonical planning source.
- Sprint documents are implementation breakdowns derived from this plan.
- `docs/domains/WORKFLOW_MODEL.md`, `docs/core/ARCHITECTURE.md`, `docs/domains/REPORT_ASSEMBLY.md`, `docs/domains/MAP_GENERATION.md`, and related docs should be updated as implementation changes land.
- Archived planning documents under `docs/archive/` are retained for history and should not drive new work.
- `env_constraints_report_20260511_EXAMPLE_ONLY.docx` remains the structural and visual target for generated deliverables, but it is not project evidence for future reports.

Implementation precedence:

- The deliverable shape, table/figure inventory, attachment inventory, formatting target, prompt rules, and review/export rules are all captured in this document.
- Implementation should turn those canonical rules into machine-readable config, service artifacts, tests, and export behavior.
- Any generated report content must use current project evidence only. Example-report language may guide structure, pacing, and voice, but not facts.

## Canonical Deliverable And Style Contract

Source model:

- The example deliverable is an Environmental Constraints Report appendix-style package.
- The generated package should follow the example report's section shape, figure/table inventory, attachment shape, and DOCX visual style.
- The generated package should not copy example project facts, locations, counts, dates, agency outcomes, or conclusions.
- Figure and table numbering should be assigned by the deliverable matrix, not copied from inconsistent example numbering.
- Raw GIS relationship tables and raw source hits are evidence artifacts, not default report pages.

Formatting target from the example report:

- Page size: Letter, 8.5 in x 11 in.
- Margins: 1.0 in top, bottom, left, and right.
- Header distance: 0.5 in.
- Footer distance: 0.5 in.
- Usable content width: approximately 6.5 in.
- Default body font: Calibri, 12 pt.
- Default paragraph spacing after: 8 pt.
- Default line spacing: approximately 1.16.
- Cover title: Calibri Light, 20 pt, right aligned.
- Cover subtitle: Calibri Light, 16 pt, bold, italic, right aligned, color `#0F4761`.
- Main section headings: Lato, 20 pt, color `#0F4761`, numbered outline level 1.
- Subsection headings: Lato, 14 pt, color `#0F4761`, numbered outline level 2.
- Resource subsection headings: Lato, italic, color `#0F4761`, numbered outline level 3.
- Alternative/detail subsection headings: italic, color `#4C94D8`, numbered outline level 4.
- Captions: Calibri Light, 11 pt, italic, centered, color `#0E2841`, single spacing, 10 pt after.
- Tables: Word `Table Grid` style, with consistent generated header emphasis.
- Main map figures: target 6.5 in wide and approximately 4.1 in high.
- Footer: current project name, report title, and page number where practical.

Front matter:

- Cover/title page:
  - Planning and Environmental Linkage Study for the current project name.
  - Project route/location line.
  - Appendix A: Environmental Constraints Report.
  - Report date.
  - Project number or identifier when available.
  - County/counties and state.
- List of figures.
- List of tables.
- List of attachments.

List of figures, in canonical report order:

| Figure | Title |
| --- | --- |
| Figure 1 | Wetlands and Waterbodies in and near the Study Corridor |
| Figure 2 | FEMA Flood Zones in and near the Study Corridor |
| Figure 3 | Streams and 303(d) Impaired Waters within the Subwatersheds of the Study Corridor |
| Figure 4 | Cultural Resources Sites in or near the Study Corridor |
| Figure 5 | Fire Stations in or near the Study Corridor |
| Figure 6 | Government Offices near the Study Corridor |
| Figure 7 | Schools and Childcare Facilities in or near the Study Corridor |
| Figure 8 | Health Care Facilities near the Study Corridor |
| Figure 9 | Places of Worship in or near the Study Corridor |
| Figure 10 | Public Water Supply Wells near the Study Corridor |
| Figure 11 | Energy Infrastructure near the Study Corridor |
| Figure 12 | Hazardous Waste Sites near the Study Corridor |
| Figure 13 | Census Tracts along the Study Corridor |

List of tables, in canonical report order:

| Table | Title | Section | Columns |
| --- | --- | --- | --- |
| Table 1 | Descriptions of Wetlands and Waterbodies Present within the Study Corridor | 3.1.1 Wetlands and Waterbodies | Alternative; Stream Crossings; Freshwater Emergent Wetland; Freshwater Forested/Shrub Wetland; Freshwater Pond |
| Table 2 | FEMA Flood Zones within the Study Corridor | 3.1.2 Floodplains and Floodways | Alternative; Flood Zone Classification; Estimated Acreage |
| Table 3 | Income Demographics of Census Tracts along the Study Corridor | 3.6.1 Demographic Characteristics | Census Tract; Population Below the Poverty Line |
| Table 4 | Demographic Composition of Census Tracts along the Study Corridor | 3.6.1 Demographic Characteristics | Geography; Black or African American; Asian; White |

Attachment targets:

- Attachment A: Environmental Constraints Maps.
- Attachment B: Hazardous Materials Report.
- Attachment C: Agency Consultation Letters.

Canonical section outline:

- Executive Summary.
- 1. Introduction.
- 1.1 Relationship with the PEL Study.
- 1.2 Study Area.
- 2. Methodology.
- 2.1 Data Collection and Sources.
- 2.2 Mapping and Analysis Procedures.
- 2.3 Limitations and Data Gaps.
- 3. Environmental Constraints Inventory.
- 3.1 Natural and Ecological Resources.
- 3.1.1 Wetlands and Waterbodies.
- Dynamic 3.1.1.x comparison-unit subsections under wetlands and waterbodies.
- 3.1.2 Floodplains and Floodways.
- 3.1.3 Water Quality.
- 3.1.4 Protected Species and Critical Habitat.
- 3.2 Cultural and Historic Resources.
- 3.2.1 Archaeological Sites.
- 3.2.2 Historic Structures and Districts.
- 3.3 Community Resources.
- 3.3.1 Fire/EMS Stations.
- 3.3.2 Government Buildings.
- 3.3.3 Education Facilities.
- 3.3.4 Health Care Facilities.
- 3.3.5 Places of Worship.
- 3.3.6 Parks and Recreation Areas.
- 3.4 Utility and Infrastructure Considerations.
- 3.4.1 Public Water Supply.
- 3.4.2 Utility Infrastructure.
- 3.4.3 Energy Infrastructure.
- 3.4.4 Airports.
- 3.5 Contamination Risks.
- 3.5.1 Hazardous Materials Sites.
- 3.5.2 Oil Wells.
- 3.6 Socioeconomic and Business Considerations.
- 3.6.1 Demographic Characteristics.
- 3.6.2 Local Businesses and Economic Nodes.
- 4. Conclusion and Next Steps.
- Attachment A: Project Maps / Environmental Constraints Maps.
- Attachment B: Hazardous Materials Report.
- Attachment C: Agency Consultation Letters.

Section target notes:

- Executive Summary: generated last from reviewed/generated section summaries, tables, figures, source gaps, and caveats. Keep concise and objective.
- 1 Introduction: explain the report's screening role and current project context without final impact conclusions.
- 1.1 Relationship with the PEL Study: describe the report as a planning appendix or supporting screening document. If no formal PEL context exists, use generic broader planning language.
- 1.2 Study Area: use project bbox, county names, termini or service-area labels, comparison-unit names, and available overview/basemap context.
- 2 Methodology: describe input geometry, source layers, deterministic GIS checks, table/figure generation, and human review.
- 2.1 Data Collection and Sources: summarize GIS layers, agency/public data, aerial imagery, reviewer-supplied material, and source gaps.
- 2.2 Mapping and Analysis Procedures: document KMZ parsing, comparison-unit creation, bbox/source clipping, buffers, CRS, measurements, overlays, and map production.
- 2.3 Limitations and Data Gaps: concise caveats for screening limitations, missing/manual/restricted sources, stale sources, and field-verification needs.
- 3 Environmental Constraints Inventory: introduce the resource-by-resource organization and comparison-unit basis.
- 3.1 Natural and Ecological Resources: bridge into wetlands/waterbodies, floodplains/floodways, water quality, and protected species/critical habitat.
- 3.1.1 Wetlands and Waterbodies: use Table 1 and Figure 1; summarize wetland/waterbody categories and stream crossings by comparison unit.
- Dynamic 3.1.1.x subsections: one concise wetlands/waterbodies paragraph per comparison unit.
- 3.1.2 Floodplains and Floodways: use Table 2 and Figure 2; store acreage by comparison unit and flood classification, using the configured line buffer for line alternatives.
- 3.1.3 Water Quality: use hydrography, stream, subwatershed, impaired-water, and 303(d) evidence; reference Figure 3.
- 3.1.4 Protected Species and Critical Habitat: separate GIS-checkable critical habitat from IPaC, state heritage, and agency/manual review.
- 3.2 Cultural and Historic Resources: use Figure 4 when public cultural context is available; keep restricted archaeology and MDAH/SHPO review gated/manual.
- 3.2.1 Archaeological Sites: use only available public or reviewer-approved evidence; do not expose sensitive records.
- 3.2.2 Historic Structures and Districts: use public historic resource context and reviewed eligibility/status fields when available.
- 3.3 Community Resources: introduce fire/EMS, government, education, health care, worship, parks, and recreation without final social impact conclusions.
- 3.3.1 Fire/EMS Stations: use Figure 5.
- 3.3.2 Government Buildings: use Figure 6.
- 3.3.3 Education Facilities: use Figure 7.
- 3.3.4 Health Care Facilities: use Figure 8.
- 3.3.5 Places of Worship: use Figure 9.
- 3.3.6 Parks and Recreation Areas: generate from available park/recreation/conservation evidence or create the required stub.
- 3.4 Utility and Infrastructure Considerations: describe water supply, utilities, energy infrastructure, and aviation constraints without claiming utility conflicts unless supported.
- 3.4.1 Public Water Supply: use Figure 10.
- 3.4.2 Utility Infrastructure: use utility/corridor/crossing evidence and relevant figure context when available.
- 3.4.3 Energy Infrastructure: use Figure 11.
- 3.4.4 Airports: generate from aviation evidence or create the required stub.
- 3.5 Contamination Risks: introduce regulated facilities, cleanup sites, USTs, contamination, hazardous materials, and oil/gas context as screening-level topics.
- 3.5.1 Hazardous Materials Sites: use Figure 12 and Attachment B when reviewed support material exists.
- 3.5.2 Oil Wells: generate from oil/gas well evidence or create the required stub.
- 3.6 Socioeconomic and Business Considerations: introduce demographic and economic context without final EJ, equity, or economic impact conclusions.
- 3.6.1 Demographic Characteristics: use Figure 13, Table 3, and Table 4.
- 3.6.2 Local Businesses and Economic Nodes: generate from business/economic node evidence or create the required stub.
- 4 Conclusion and Next Steps: summarize objective constraint themes and future coordination/review needs without ranking or recommending alternatives.
- Attachments: include only reviewed/accepted attachment content or the required stub.

Required stub text:

`Empty stub for future implements whenever source data is accessible.`

All current-profile section, table, figure, and attachment targets are mandatory review targets. Missing, inaccessible, gated, or unimplemented data creates a stub review item using the exact required stub text. Missing source categories do not block review queue creation.

## Canonical Report-Generation Prompt Contract

Global prompt rules:

- Draft pre-review Environmental Constraints Report content for a project screening workflow.
- Use the example report only for structure, voice, pacing, section organization, and formatting expectations.
- Do not reuse example project facts, place names, counts, dates, agencies contacted, conclusions, or source-specific findings unless those facts are explicitly present in the current project evidence package.
- Use only the provided current-project evidence package.
- Evidence may include comparison-unit summaries, generated tables, generated figures, source-backed constraint summaries, source status, source provenance, review assumptions, validation warnings, missing-source stubs, and reviewer instructions.
- Write in a professional environmental planning style.
- Keep language objective, screening-level, concise, and suitable for human review.
- Do not rank alternatives.
- Do not recommend an alternative.
- Do not select, reject, approve, clear, or determine project impacts.
- Do not claim field verification, jurisdictional determination, agency approval, final design, or final environmental clearance.
- Reference only known table IDs, figure IDs, source IDs, attachment IDs, and comparison-unit names supplied in the evidence package.
- If a relevant figure or table is provided, reference it naturally by assigned number.
- If source data is missing or a section is unimplemented, use exactly: `Empty stub for future implements whenever source data is accessible.`
- Prefer concise paragraphs over long lists.
- Summarize patterns by comparison unit and resource category.
- Treat raw GIS intersections as evidence inputs, not report paragraphs.
- Preserve uncertainty, assumptions, data limitations, and reviewer-needed caveats.

Section prompt intent:

- Front matter prompts generate title, lists of figures, lists of tables, and lists of attachments from project metadata and reviewed matrix items only.
- Executive Summary follows the example sequence: report purpose, natural/ecological themes, cultural/historic themes, community themes, demographic/socioeconomic themes, utility/infrastructure themes, contamination themes, and later-phase planning support.
- Introduction prompts explain early screening purpose, current project type, comparison units, and support for later planning/design/coordination/review.
- Relationship to PEL prompts describe the report as a planning appendix or supporting screening document, adapting to generic broader planning language when no formal PEL exists.
- Study Area prompts use bbox, county names, termini/service-area labels, comparison-unit names, and available overview/basemap context.
- Methodology prompts describe deterministic GIS/source checks, source layering, mapping, buffering, CRS/measurement assumptions, and human review.
- Data Collection prompts summarize source categories and provenance without inventing source dates or agency outcomes.
- Mapping and Analysis prompts explain KMZ parsing, comparison-unit creation, source selection/clipping, overlays, buffers, and table/figure generation.
- Limitations prompts keep source gaps, stale data, manual/restricted review, and field-verification caveats concise.
- Inventory prompts organize constraints by resource category and comparison unit without treating review queue volume as an impact metric.
- Wetlands/waterbodies prompts use stream crossing counts, NWI/wetland category mappings, Table 1, and Figure 1; they must not state jurisdictional determinations.
- Alternative-detail prompts summarize only the named comparison unit's evidence and must not repeat full tables or rank alternatives.
- Floodplain prompts use FEMA/NFHL classification, corridor buffer assumptions, acreage by classification, Table 2, and Figure 2; they must not claim final floodplain/floodway determinations.
- Water quality prompts use hydrography, streams, subwatersheds, impaired waters, TMDL/303(d) evidence, and Figure 3 when available.
- Protected species prompts distinguish critical habitat GIS, IPaC, state heritage/manual review, and agency consultation records.
- Cultural prompts summarize public cultural/historic context and restricted/manual review status without exposing sensitive archaeology or claiming clearance.
- Community prompts summarize fire/EMS, government, education, health care, places of worship, parks, and recreation with descriptive planning language.
- Utility/infrastructure prompts summarize public water, utility, energy, transportation, and aviation evidence without claiming conflicts or relocations unless evidence supports that wording.
- Contamination prompts summarize regulated facility, hazardous materials, cleanup, UST, and oil/gas context without final due diligence conclusions.
- Socioeconomic prompts use Census/ACS table and figure evidence descriptively and avoid final EJ, equity, or economic impact conclusions.
- Conclusion prompts summarize objective constraint themes and future coordination, source review, field verification, agency consultation, design review, and permitting needs supported by evidence.
- Attachment prompts include accepted reviewed attachment content or the exact required stub.

## Carried-Forward Product Boundary

These durable rules are part of the canonical plan and should remain true unless explicitly replaced by a later approved decision:

- The product is a constraint engine plus a review queue plus an export compiler.
- The product is not a recommendation engine.
- The product must present objective constraints so reviewers and project teams can make decisions outside the tool.
- The product must stay project-type agnostic. Trails and Conexon-style workspaces are examples, not hard-coded product boundaries.
- The system should accept point, line, polygon, and mixed project inputs over time.
- The system must not choose a preferred alternative, reject a project feature, rank options, score options, or recommend a route/site/service area/corridor.
- The system must not pretend desktop screening is field verification.
- The system must not hide missing, gated, failed, stale, or unavailable data.
- The system must not invent source-backed evidence.
- The system must not present unreviewed generated content as reviewed, final, or externally ready.
- The system must not include mock or test fixture source records as client-facing evidence.
- The system must not automate restricted data access without explicit approval.
- Deterministic GIS/source checks must remain separate from GPT-assisted narrative drafting.
- Generated reports should be treated as editable pre-review or reviewed export packages, not final determinations.

Discussion items:

- Archived planning language mentions a local app and desktop GUI. The carried-forward product boundary remains valid, but the UI direction in this document supersedes the desktop GUI direction with a web-app-only direction.
- Internal preview exports may still be useful for development, but they must remain clearly labeled as internal/pre-review and must not be the default user-facing report path.

## Current Baseline To Preserve

The old redirect records an important implementation baseline that should not be lost while changing the workflow shape:

- Project workspaces already exist under `projects/<project_id>/`.
- KMZ/KML ingestion exists, including point, line, and polygon parsing.
- Geometry summary, normalized input GeoJSON, normalized project features, and analysis bounds artifacts already exist under project `intermediate/` folders.
- Source catalog, project source registries, local source registration, and local source materialization already exist.
- The ignored root `sources/` warehouse is the local-only bulk data storage location.
- Local materializers already support several Mississippi source packages, including NWI wetlands, critical habitat, soils, MDOT/rail transportation context, utilities, boundary context, public cultural context, community facilities, and conservation/recreation lands.
- Public downloaders already exist for USFWS NWI, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard data.
- FEMA is optional unless explicitly downloaded or requested through optional-source acquisition.
- Source acquisition and materialization preserve provenance and register project-local source layers.
- Deterministic constraint analysis exists and can feed findings, grouped summaries, tables, maps, report sections, and review queue items.
- Evidence package generation exists.
- JSON-backed review queue generation, listing, and item update operations exist.
- Populate-for-review orchestration exists.
- Markdown and DOCX export exist, including inline figure/table rendering where practical.
- Optional GPT-backed report drafting exists after deterministic evidence generation, with deterministic fallback and a `--no-gpt-drafting` override.
- GPT drafting already receives structured evidence bundles rather than raw source files or raw geometry paths.
- GPT guardrails already check for unknown citations and prohibited recommendation/ranking/selection/final-determination language.
- Existing generated maps are vector-only and include draft map elements such as legends, source notes, CRS/method notes, and draft/pre-review labeling.

Discussion items:

- The new workflow should narrow which artifacts become review/export targets, but it should reuse the existing services where possible.
- Existing raw/detail tables and findings should become evidence artifacts by default, not standard report pages.
- Existing preview-export behavior should be treated as development/internal behavior unless it is changed to satisfy the review-complete export gate.

## Source And Provenance Rules

Planned workflow:

- Local registration remains the first-class path for reviewer-supplied or locally maintained data.
- Approved public downloaders may fill source gaps where implemented.
- Paid services, credentials, restricted systems, and sensitive data sources require explicit approval before automation.
- Failed downloads should be nonfatal when the rest of the workflow can continue, but the failure must create a visible source status, caveat, or stub.
- Every source used in constraints, tables, figures, or text should preserve source name, source category, path or endpoint, access/materialization date, original attributes where practical, normalized labels/types/subtypes, limitations, and source citation.
- Missing, manual, gated, restricted, stale, or unimplemented sources should be visible in source status artifacts and review items.
- Public cultural data must remain limited to public context layers. Restricted archaeology/SHPO/MDAH review remains manual, gated, or reviewer-supplied unless explicitly approved otherwise.
- Imagery should support basemaps and reviewer visual context. Imagery-observed features are not authoritative facts unless promoted through a reviewed output item.
- MVP/client-facing outputs must be real-data guarded. Stubs are acceptable; mock/test fixture evidence is not.

Discussion items:

- Source availability should not automatically create report volume. The deliverable matrix should decide what becomes a review target.
- Each source category needs a normalization contract before it can reliably populate table fields, figure labels, and section prose.
- Source status should distinguish at least: present, registered local, materialized local, downloaded, downloadable, optional, manual/reviewer-supplied, restricted/gated, unavailable, failed, stale, and unimplemented.

## Review And Export Rules To Preserve

Planned workflow:

- The review queue remains the core domain model between generation and export.
- Generated text, tables, figures, attachments, caveats, and reviewer-needed stubs become reviewable items.
- Review items must preserve status, reviewer edits, replacement content, notes, assumptions, provenance, related source refs, related table/figure IDs, and export eligibility.
- Reviewer state should survive regeneration where practical.
- Export should include only accepted, edited, replaced, or otherwise explicitly included reviewed content.
- Declined items should be omitted from the generated report.
- Unreviewed generated content must not enter the default export path.
- Unable-to-verify items should enter export only when explicitly marked export eligible or converted into accepted reviewer caveats.

Discussion items:

- Current statuses such as `rejected` may need to be renamed or mapped to the new user-facing `declined` language.
- Queue filters should eventually support type, status, source category, project feature/comparison unit, and export section.
- The review queue should expose provenance and previews without forcing the reviewer to review every raw GIS relationship.

## Geometry And Comparison-Unit Rules To Preserve

Planned workflow:

- Raw input features and report comparison units should be modeled separately.
- For line inputs, segmented line strings should be grouped into meaningful project features without inventing missing connections.
- For point-heavy projects, preserve individual point features and style/color grouping metadata, but use meaningful groups/service areas as comparison units by default.
- Reviewer correction of geometry role, comparison-unit naming, and grouping should be supported before analysis over time.
- Explicit project boundary inputs should eventually be supported separately from routes, sites, service areas, or other feature propositions.

Discussion items:

- The current project geometry services already move in this direction, but the deliverable workflow needs to depend on comparison units rather than raw features.
- The example trail project should validate to five comparison units before standard report generation.
- Point-heavy projects should summarize individual points by group unless a reviewer explicitly asks for point-level evidence appendices.

## Implementation Discipline

Carried-forward repo rules:

- Keep changes narrow, inspectable, and tied to the requested task.
- Prefer simple service-level implementation over logic buried in UI callbacks.
- Keep deterministic GIS/source analysis separate from GPT-assisted synthesis.
- Do not add external APIs, credentials, paid services, or large dependencies without approval.
- Add or update tests for behavior-changing implementation work.
- Run the relevant test suite before committing or summarize why tests were not run.
- Review docs for every code change and update affected docs in the same task.
- Keep `docs/domains/WORKFLOW_MODEL.md` aligned with this canonical plan.

Sprint execution protocol:

- Work through one sprint subunit at a time.
- Before implementing a subunit, create and push a checkpoint commit of the current accepted state.
- Implement the subunit only; do not opportunistically start the next subunit.
- Run the relevant tests and smoke checks for the subunit.
- Perform an audit/review pass and fix anything found.
- Update affected documentation in the same work cycle.
- Commit and push the completed subunit before moving to the next sprint subunit.
- If a checkpoint, test run, audit fix, commit, or push is blocked, record the blocker and do not proceed to the next subunit until the user decides how to handle it.

Discussion items:

- `CANONICAL_PLAN.md` is the canonical planning source. Future implementation docs should be reconciled to it as behavior changes land.
- Future code changes should treat this document's canonical deliverable and prompt contracts as the human-readable source until machine-readable configs are created.

## Known Gaps Brought Forward

- Census TIGER/ACS source acquisition and table generation remain future work.
- Full source catalog attribution, licensing/terms, refresh cadence, source-date handling, and schema normalization remain incomplete.
- Source-specific category/subtype mappings still need refinement for wetlands, streams, flood zones, soils, facilities, utilities, parcels, and community resources.
- Validation warnings need to improve for missing CRS, unknown schemas, empty layers, invalid geometries, stale source dates, and very large source layers.
- Geometry-specific constraint checks need more depth for point/site, line/corridor, polygon/area, and mixed inputs.
- Per-category buffers need to be configurable and report-visible.
- Line-through-polygon length summaries, line/line crossing counts, polygon overlap acreage, and nearest-feature summaries need to align to deliverable table needs.
- No-overlap records should exist where report-relevant without becoming noisy review queue volume.
- Project input support should expand beyond KMZ/KML to direct GeoJSON, shapefile, and GeoPackage inputs.
- Reviewer-facing GPT provenance display remains future UI work.
- DOCX fidelity needs continued improvement for template-grade layout, numbering, headers/footers, polished tables, polished figures, and eventual PDF export.
- Map generation still needs panel maps, per-feature maps where useful, and integration of the MARIS/NAIP aerial basemap source.
- The web app itself is not implemented.

## Project Workspace Intake

Planned workflow:

- A user eventually selects `New Project` in the web app UI.
- The app creates a new subdirectory under `projects/` using the project name supplied by the user.
- The project workspace becomes the local container for inputs, source status, intermediate geometry, source materialization, generated findings, generated maps/tables, review queue state, and exports.
- The user can drop one or more files into the project workspace.
- At least one input must be a KMZ file for the current intended workflow.
- The required KMZ represents the project alternatives that will eventually be mapped and checked against the full set of considerations.
- The first cheap win from the KMZ is not full alternative interpretation. It is deriving the project bounding box so the pipeline immediately knows the project area.

Current pipeline check:

- The repo already uses `projects/<project_id>/` workspaces.
- Current sample workspaces include `projects/trails` and `projects/conexon_projects`.
- Current CLI services can create project manifests and parse KMZ/KML geometry.
- Current geometry services write normalized project artifacts under `projects/<project_id>/intermediate/`, including project features and analysis bounds.
- UI project creation is not implemented.
- The current system can ingest KMZ/KML, but the new working rule should make the KMZ requirement explicit for the near-term workflow.

Discussion items:

- The required near-term KMZ should be treated as alternatives/routes input, with bbox extraction as the first processing output.
- Decide where uploaded files should live in the workspace. The current convention is `projects/<project_id>/inputs/`; the future web app should preserve that rather than scattering files at project root.
- Decide whether non-KMZ support remains available but secondary, or whether the UI should block populate-for-review until a KMZ is present.
- Add a validation step that reports: KMZ present, geometry parsed, geometry role inferred or reviewer-confirmed, analysis bounds created, and required source categories resolved.

## Sprint 4: Web App UI Direction

This section belongs to Sprint 4 only. It is intentionally out of scope for Sprints 1 through 3, which should remain focused on non-UI pipeline, constraints, review queue, export, and DOCX behavior.

Planned workflow:

- The product UI should be a web app only.
- Do not build a standalone desktop GUI.
- The web app should provide project creation, file upload/drop, processing status, source/status review, generated table/figure previews, draft section review, and export controls.
- The backend can still use local project workspaces under `projects/` for now unless a later architecture decision changes storage.
- The web app should call thin backend services rather than burying workflow logic in UI handlers.
- The pipeline should remain service-first so CLI/tests can still exercise ingestion, constraint processing, table generation, figure generation, text generation, review state, and export without the UI.

Initial web app navigation:

- Left-side navigation with these main tabs:
  - `Projects`
  - `Overview`
  - `Review`
  - `Export Report`

`Projects` tab:

- User can create/add a project.
- User can see past projects.
- User can access archived projects.
- User can select an existing project.
- Selecting a project makes the rest of the tabs operate on that project workspace.

`Overview` tab:

- Shows the selected project.
- Provides the project file upload/drop area.
- Shows files staged for upload.
- Shows files already uploaded.
- Shows upload/file-processing state.
- Provides file classification controls so uploaded files can be tied to pipeline needs, such as required KMZ alternatives input, source evidence, agency document, supporting report, imagery, or notes.
- Provides a pipeline trigger button after uploads/classification are ready.
- Button label should be something like `Create Review Queue`.
- Pressing `Create Review Queue` runs the full pipeline through project area setup, comparison-unit processing, source/constraint processing, table generation, figure generation, section text generation, stub creation, and review queue creation.

`Review` tab:

- Shows all generated review items as rows.
- Review item rows should correspond to deliverable matrix targets, not raw GIS intersections.
- Each row links to a detailed review view.
- Detail view supports accept as-is, edit, fully replace, or decline.
- Detail view should show relevant context, such as section/table/figure target, source refs, assumptions, figure/table preview, provenance, and generated draft content.
- Review tab should show completion state and remaining unreviewed item count.

`Export Report` tab:

- Shows export readiness.
- Blocks report generation until all review items are accepted, edited, replaced, or declined.
- Generates the report from reviewed queue items minus declined items.
- Provides access to generated DOCX and any later supported export package outputs.

Current pipeline check:

- Current implementation is service/CLI-first.
- No production UI exists.
- Archived docs may refer to a desktop app or desktop GUI direction.
- The backend already has service boundaries that can support a future web app.
- Current review queue services already support row-like item listing and item updates, but not a web detail view.
- Current export services already support DOCX output, but default export behavior must be changed to enforce the review-complete gate for the working web-app flow.

Discussion items:

- Decide the initial web stack before implementation.
- Decide whether the first web app runs only locally or supports remote/multi-user deployment.
- Decide how web uploads map to `projects/<project_id>/inputs/`.
- Decide how generated artifacts under ignored project folders are exposed for preview/download.
- Treat any remaining desktop GUI or PyInstaller packaging references in archived docs as historical only.
- Decide the exact pipeline trigger label: `Create Review Queue`, `Build Review Queue`, or similar.
- Decide whether file classification is required before enabling `Create Review Queue`, or whether the backend can infer obvious types and ask only for ambiguous files.

## First Processing Step: KMZ Bounds, County Names, and Aerial Basemap

Planned workflow:

- After the user adds input files, the first processing step parses the required KMZ enough to derive the project bounding box.
- This step happens before full alternative interpretation, full source acquisition, constraint analysis, report generation, or review queue generation.
- The bbox is stored as a first-class project artifact for downstream clipping, source selection, map setup, and report context.
- The bbox is used to identify the county or counties where the project is located.
- County names are resolved by checking the bbox against the local georeferenced aerial basemap dataset under `F:\Desktop\review_assist\sources\aerial_base_maps\maris_naip_2025\`.
- During the same pass, the workflow stores the selected aerial basemap path or prepares a temporary/cropped basemap file for use in deliverable visuals.
- The selected aerial basemap source and bbox should be recorded with provenance so every generated visual can cite the basemap source.

Current pipeline check:

- Current geometry processing can parse KMZ/KML and create project analysis bounds.
- Current county-name context is currently tied to materialized boundary context, not to the new MARIS/NAIP aerial basemap folder.
- The MARIS/NAIP 2025 aerial imagery has been organized under `sources/aerial_base_maps/maris_naip_2025/`, but it is not yet wired into the source catalog, source materialization, map generation, or project context generation.
- Current vector-only maps do not use aerial basemaps.

Discussion items:

- County detection from aerial file coverage may work as a quick source-local lookup if each county folder is reliable and complete, but it should be checked against a boundary layer before becoming the only authoritative county-name method.
- The project should store both the bbox and the selected basemap path. If a cropped temporary basemap is created, store its path separately from the source path.
- The basemap selection step needs a rule for projects crossing multiple counties. It may need to select multiple county imagery folders, mosaic/crop them, or keep a list of source paths for map generation.
- This first step should create a compact artifact such as `projects/<project_id>/context/project_area.json` or extend the existing project geometry/context artifacts with bbox, county names, basemap source paths, and processing warnings.
- Imagery use in visuals is different from imagery interpretation. This step should prepare a visual basemap, not generate authoritative observations from imagery.

## Comparison Units, Not Raw Geometry Pieces

Planned workflow:

- The pipeline must distinguish raw input geometries from report comparison units.
- For the example trail project, the required KMZ contains five trail alternatives. Those five alternatives are the comparison units.
- Polyline segments inside a trail alternative should be joined or grouped into the single alternative they belong to before constraint checks drive deliverable tables.
- The report should compare approximately `5 alternatives x consideration categories`, not `every line segment x every source feature`.
- For point-heavy projects such as the Conexon-style sample, individual points may exist in the KMZ, but the report comparison units should be the color/style groups or service areas, not every individual point by default.
- Individual segments and individual points should remain traceable as evidence-level detail, but they should not automatically become exported report rows.
- The default deliverable should summarize by comparison unit and consideration/resource category.

Current pipeline check:

- Current project geometry normalization already attempts to group segmented line features by placemark name, style URL, then candidate label, and merge line pieces.
- Current point-heavy handling preserves individual point features and style/color grouping metadata.
- Current constraint analysis runs against `project_features.geojson`, so if project features are too granular, every downstream constraint, table, finding, and map can become too granular.
- Current table generation includes a grouped constraint summary by `project_feature_id x source_category`, which is closer to the desired deliverable shape.
- Current table generation also includes raw and source-specific summaries that can emit one row per project feature/source feature relationship. Those tables can explode in page count if exported directly.
- The 640-page first-pass deliverable is likely caused by exporting raw relationship/detail tables, source-specific detail rows, or unmerged geometry units instead of a compact comparison-unit summary.

Discussion items:

- The project geometry artifact should explicitly record two levels: raw input features and comparison units.
- For trail alternatives, comparison-unit creation should validate that the result is the expected five alternatives for the example project, or flag a reviewer issue before report generation.
- For point-heavy projects, style/color groups should become service-area comparison units, with individual points summarized by counts and retained as detail.
- Export should default to grouped summary tables, not raw constraint tables.
- Raw relationship tables should be treated as audit/evidence artifacts and excluded from standard report export unless the reviewer explicitly requests an evidence appendix.
- The review queue may keep detailed items available, but the deliverable should not include all detail items by default.
- The pipeline needs a size guardrail: if comparison-unit count is far above the expected project shape, stop or warn before generating a DOCX preview.

## Constraint-First Runtime Workflow

Planned workflow:

- Once input data is available, the workflow should treat it as two main things: project area and feature propositions.
- The project area comes first from the KMZ-derived bbox and supports county detection, basemap selection, source clipping, and map setup.
- Feature propositions are then divided into comparison units, such as `Trail 1` through `Trail 5` for the example project.
- Each comparison unit is run individually against the constraint workflow.
- Constraint checks include the current consideration categories such as wetlands, waterbodies, hydrography/crossings, floodplain, soils, protected species/critical habitat, cultural resources, community resources, utilities/infrastructure, regulated facilities, socioeconomic context, and imagery/basemap context where applicable.
- Deterministic GIS intersections are treated as screening facts for runtime purposes. They do not need hundreds of individual reviewer decisions before they can support section generation.
- Reviewer review happens at the output layer: report sections, summary tables, figures, caveats, and selected evidence. The reviewer should not have to accept or reject every raw intersection record.
- Every constraint run should save enough metadata for later text, table, and figure generation.
- Runtime metadata should preserve comparison unit, source category, source ID/name, source feature labels or types, relationship type, measurements, buffer assumptions, analysis CRS, source path/provenance, uncertainty flags, and any validation warnings.
- Runtime metadata must be sufficient to populate the section/table/figure needs identified in this document's canonical deliverable contract.
- Raw intersection records remain available as evidence, but the standard workflow uses them to create compact section-level deliverables.

Current pipeline check:

- Current constraint analysis already writes `projects/<project_id>/constraints/constraint_results.json` with project feature IDs/names, source categories, relationship types, measurements, source labels, method, CRS, source path, and provenance.
- Current table generation already creates both raw/detail tables and grouped summaries.
- Current findings, maps, report sections, review queue, and export steps exist, but they can currently expose too many low-level artifacts.
- Current review queue is useful as a storage/review mechanism, but it should not force a reviewer to process every raw GIS relationship as its own decision.

Discussion items:

- Define the runtime constraint store as the authoritative evidence layer for text/table/map generation.
- Keep raw GIS intersections deterministic and source-backed. Do not run LLMs during the constraint-check step.
- Decide which raw intersection details are retained only in JSON/evidence and which are promoted into summary tables.
- Check each source/layer comparison against the deliverable matrix so the workflow stores the exact fields needed later, such as wetland category totals, stream crossing counts, flood zone classification acreages, critical habitat species/unit fields, cultural resource labels/status, community facility counts/locations, utility crossings, regulated facility proximity, and census variables.
- Add a workflow gate: do not generate a report until constraint metadata, section table inputs, section figure inputs, and section narrative inputs are ready.
- Add a compact run summary after constraints: comparison-unit count, source category count, total raw constraint records, grouped summary count, missing/gated/manual source count, and warnings.

## Section Generation Units: Text, Tables, and Figures

Planned workflow:

- After all comparison units have been run through constraints, the workflow has three section-generation tasks.
- First: generate text per report header/section.
- Second: generate tables per report header/section.
- Third: generate maps/figures per report header/section.
- Text, tables, and figures should be generated from the same stored constraint metadata so they stay aligned.
- Tables should be identified by table number and tied to their report section/header.
- Maps should be identified by figure number and tied to their report section/header.
- The example deliverable should be used to identify which sections expect tables and which sections expect figures.
- This example-derived section/table/figure information should be stored beforehand as a static config file, not inferred ad hoc during every run.
- This document's canonical deliverable contract is the current human-readable source for this static config.
- Report section generation should reference the generated table and figure IDs rather than independently inventing content.
- If a section has no source-backed content, it should receive concise caveat or no-data language rather than a long placeholder section.
- Standard report generation should wait until section text inputs, table inputs, and figure inputs are ready.
- For the current working profile, every section, subsection, table, figure, and attachment target in this document's canonical deliverable contract is mandatory as a review item.
- If source data is not accessible or not implemented yet, still create the required section/subsection/table/figure/attachment review item as a stub with this exact statement: `Empty stub for future implements whenever source data is accessible.`

Current pipeline check:

- `config/report_section_templates.json` already records section IDs, titles, export groups, visual slots, and table slots.
- Current report sections can carry related table and figure IDs.
- Current exports can render referenced tables and figures inline.
- Current ordering and numbering are not yet treated as a strict section-level deliverable contract.
- Current maps are vector-only and are not yet tied to the new aerial basemap source.
- Current preview/export can include too many draft items before the section-level deliverable package is coherent.

Discussion items:

- Convert the example deliverable into a practical section-output matrix: section/header, required text, expected table IDs, expected figure IDs, required sources, optional sources, and fallback caveat.
- Store that matrix in a config artifact such as `config/deliverable_section_matrix.json` or a similarly named static report profile file.
- Number tables and figures after the section matrix is assembled so numbering follows report order.
- Prevent table/figure generation from producing unlimited detail rows by default.
- Make section text generation consume table and figure summaries, not raw rows directly, except when a concise detail is needed.
- Standard export should include only section-approved table/figure artifacts, not every table and map artifact generated during analysis.
- Replace the earlier "optional/profile-driven" distinction for this profile with a strict example-report target list. Everything in the example deliverable matrix appears in the review queue; missing pieces become stubs.

## Text Generation Workflow

Planned workflow:

- Text generation happens after deterministic constraint processing and after section-level table and figure inputs are ready.
- The example report prose can be used as structure, formatting, tone, and voice guidance.
- The example report prose must not be used as factual content for a new project.
- Store example-derived text guidance as prompt/reference material keyed by section/header, not as reusable report facts.
- For each section, send GPT a section-specific evidence package that includes:
  - section ID, section title, and section purpose from the deliverable matrix;
  - expected voice/structure guidance from the example;
  - comparison-unit summaries;
  - generated table summaries and table IDs;
  - generated figure summaries and figure IDs;
  - source-backed constraint summaries;
  - source refs and provenance summaries;
  - assumptions such as buffer distance and analysis CRS;
  - missing/manual/gated source caveats;
  - reviewer instructions when present.
- GPT should generate concise report text for the section/header that references the appropriate table and figure numbers.
- GPT must not invent facts beyond the structured evidence package.
- GPT must not rank, recommend, select, reject, or identify a preferred alternative.
- GPT output remains draft/pre-review section text and must be editable.

Current pipeline check:

- Optional GPT-backed report section drafting already exists when `GPT_DRAFTING=1`.
- Current GPT drafting receives structured evidence bundles and deterministic baseline copy.
- Current guardrails reject unknown cited IDs and prohibited recommendation/final-determination language.
- Current prompt path is not yet driven by a complete static deliverable matrix derived from this canonical plan.
- Current section drafting may occur before section-level table/figure packages are fully coherent.

Discussion items:

- Create section-specific prompt templates from the example report that describe voice and structure without including project-specific facts as reusable evidence.
- Store example text snippets or summaries in a controlled reference file with explicit labels such as `style_only`, `structure_only`, and `do_not_reuse_facts`.
- Build a section evidence package after tables and figures are generated, then pass that package into GPT.
- GPT should see table/figure IDs and summaries, not giant raw tables unless the section genuinely needs row-level detail.
- Add a validation step that checks generated text only cites known table IDs, figure IDs, source IDs, and comparison units.
- Add a validation step that checks generated text does not include facts from the example report unless they are also present in current project evidence.

## Static Deliverable Matrix And Example Section Tables

Planned workflow:

- Before runtime report generation, the system should know the expected report headers, subsection headers, text needs, table needs, and figure needs from a static deliverable matrix derived from the example deliverable.
- This document's canonical deliverable contract is the current working human-readable source for this matrix.
- The static matrix should define the section path, title, generated text requirement, table definitions, figure definitions, required source categories, optional source categories, aggregation rules, and fallback caveat behavior.
- Runtime processing should fill this matrix from stored constraint metadata.
- Report generation should happen only after the section matrix has populated text inputs, table inputs, and figure inputs or clear caveats for missing/unavailable sources.
- For the current working profile, all outline items are required review targets. Missing or unimplemented source data should not remove the item from the matrix.
- The default missing/unimplemented text for required stubs is exactly: `Empty stub for future implements whenever source data is accessible.`

Current pipeline check:

- `config/report_section_templates.json` already defines section IDs, titles, visual slots, and table slots.
- It does not yet define exact table schemas, section numbering, figure numbering, or aggregation rules from the example deliverable.
- Current table generation has source-specific summary tables, but it does not yet treat the example deliverable tables as strict output targets.
- This document now captures the example report outline, table schemas, figure inventory, attachment structure, and formatting target in a human-editable form.

Discussion items:

- The static matrix should be more specific than the current section template file.
- The current section template can remain useful for high-level section ordering, but table schemas and figure schemas need their own explicit definitions.
- The system should support replacing example-specific labels such as `trail alignment` with generic labels such as `alternative`.
- Cultural/heritage data from MDAH is one known example of a required deliverable topic that may need to be stubbed until source access or workflow implementation exists.

### Section 3.1.1 Wetlands and Waterbodies

Example deliverable structure:

- Section 3: Environmental Constraints Inventory.
- Section 3.1: Natural and Ecological Resources.
- Section 3.1.1: Wetlands and Waterbodies.
- Subsections under 3.1.1 are per alternative for the current trail input, such as `Alternative 1A`, `Alternative 1B`, `Alternative 2`, `Alternative 3`, and `Alternative 4`.
- Section 3.1.1 needs an overview table referenced by table number in the section text.

Table target:

| Field | Runtime source / aggregation rule |
| --- | --- |
| Alternative | Comparison unit name from the KMZ-derived alternatives |
| Stream Crossings | Count hydrography/stream crossing hits for that alternative |
| Freshwater Emergent Wetland | Aggregate NWI/wetland hits classified as freshwater emergent wetland for that alternative |
| Freshwater Forested/Shrub Wetland | Aggregate NWI/wetland hits classified as freshwater forested/shrub wetland for that alternative |
| Freshwater Pond | Aggregate NWI/wetland hits classified as freshwater pond for that alternative |

Processing notes:

- Each wetland/waterbody source feature that intersects or crosses the overall comparison-unit geometry should be stored with the alternative ID/name and wetland/waterbody classification.
- Wetland categories that are combined in the table, such as freshwater forested/shrub wetland, must be mapped intentionally from source attributes rather than merged by display text after the fact.
- Stream crossings should come from hydrography crossing relationships, not from unrelated wetland polygon overlaps.
- The table should be one row per alternative.
- Raw intersecting wetland polygons, waterbody polygons, and stream features remain evidence records, not report rows.
- Section text should reference the table number and summarize the pattern by alternative without ranking alternatives.

Current pipeline check:

- NWI wetland source support exists through local materialization and public download.
- USGS NHD hydrography source support exists through public download.
- Current normalized source feature fields preserve labels/types/subtypes that can support category mapping.
- Current grouped tables do not yet produce this exact example table schema.

Discussion items:

- Define canonical wetland/waterbody class mappings for NWI attributes, including freshwater emergent wetland, freshwater forested/shrub wetland, and freshwater pond.
- Decide whether wetland table values are counts, acreage, length, or presence/absence by category. The example field names imply counts/occurrences for stream crossings and category totals for wetland types; the static matrix should make this explicit.
- Decide whether the wetland/waterbody table uses the raw alternative geometry or the configured corridor buffer.

### Section 3.1.2 Floodplains and Floodways

Example deliverable structure:

- Section 3.1.2: Floodplains and Floodways.
- The example table label `trail alignment` should become `Alternative` to match the rest of the redirected workflow.
- Section 3.1.2 needs a floodplain/floodway table referenced by table number in the section text.

Table target:

| Field | Runtime source / aggregation rule |
| --- | --- |
| Alternative | Comparison unit name from the KMZ-derived alternatives |
| Flood Zone Classification | FEMA/NFHL flood zone classification intersecting that alternative or buffered corridor |
| Estimated Acreage | Acreage of the alternative corridor/buffer intersecting that flood zone classification |

Processing notes:

- Flood zone processing must store acreage by alternative and by flood zone classification so classifications are not mixed together.
- If an alternative intersects multiple flood classifications, the table should either create multiple rows for that alternative or store a clear classification-to-acreage summary in the row. The static matrix should define the display rule.
- For line alternatives, floodplain acreage should be calculated from a buffered corridor geometry rather than the zero-area line itself.
- Use the current 100-foot default buffer as the initial reasonable corridor/review buffer unless a project/report profile overrides it.
- The buffer distance, units, CRS, and whether the measurement came from raw geometry or buffered corridor must be stored with the table provenance.
- Flood zone relationships are screening-level GIS facts, not final floodplain determinations.

Current pipeline check:

- FEMA NFHL flood hazard zone downloading exists as an optional supported source.
- Current constraints can measure intersection area and store acreage in `intersection_area_acres`.
- Current project manifests already support `assumptions.default_buffer_feet`, and current sample projects use `100`.
- Current flood hazard table exists, but it is source-detail oriented rather than a strict section 3.1.2 table with `Alternative`, `Flood Zone Classification`, and `Estimated Acreage`.

Discussion items:

- Flood hazard should remain optional or profile-driven unless the selected deliverable requires it.
- Decide whether floodplain acreage should use 100 feet total corridor width, 100 feet on each side, or the current implementation's `buffer(100 feet)` behavior around the line. The current code treats `default_buffer_feet` as the buffer distance from the geometry.
- Decide how to display multiple flood zone classifications for one alternative without making the table long.

## Project Input Package

Planned workflow:

- Required near-term input: at least one KMZ file.
- Optional inputs may include GIS layers, GeoJSON, shapefiles, GeoPackages, PDFs, prior reports, maps, imagery, notes, and manually acquired agency documents.
- The input package should be inspected before source acquisition or report generation.
- The app should identify which files are project geometry, which files are source evidence, and which files are supporting documents.

Current pipeline check:

- KMZ/KML ingestion exists.
- Source status resolution can compare project inputs and registered sources against the source catalog.
- Manual/reviewer-supplied documents are represented in the source catalog for items such as IPaC, restricted cultural review, and local sources.
- The current workflow is still mostly CLI/service-driven, so dropped-file classification is not a polished user-facing workflow.

Discussion items:

- We need a clear input classification artifact before populate-for-review. It should say what each uploaded file is believed to be and whether reviewer confirmation is needed.
- The project boundary derived from KMZ should drive clipping and source selection. Supporting files should not silently change the analysis bounds unless explicitly marked as boundary/project geometry.
- If multiple KMZ files are supplied, the workflow needs a rule for selecting or combining the project geometry.

## Discrete Deliverable Items

The example deliverable should be treated as a structural template, not as project-specific content. The workflow should generate discrete reviewable deliverable items rather than a monolithic report draft.

Core deliverable items:

- Cover/title page with project name, location/counties or service area, report title, date, and project identifiers.
- List of figures.
- List of tables.
- List of attachments.
- Executive summary.
- Introduction.
- Study area description.
- Project overview map.
- Methodology: data collection and sources.
- Methodology: mapping and analysis procedures.
- Methodology: limitations and data gaps.
- Environmental constraints inventory overview.
- Overall environmental constraints inventory map.
- Panel index map when needed.
- Panel maps when needed.
- Wetlands and waterbodies section.
- Wetlands and waterbodies figure.
- Wetlands and waterbodies description table.
- Floodplains and floodways section when relevant.
- FEMA flood zones figure when available/relevant.
- FEMA flood zone summary table when available/relevant.
- Streams, hydrography, water quality, and crossings section.
- Streams/impaired waters figure when source data supports it.
- Protected species and critical habitat section.
- Species/critical habitat figure when GIS-checkable layers are available.
- IPaC or agency consultation placeholder/review item when the source is manual.
- Cultural and historic resources section.
- Public cultural resources figure where appropriate.
- Restricted archaeology/manual SHPO or MDAH review caveat.
- Community resources section.
- Fire/EMS stations figure.
- Government offices figure.
- Schools and childcare facilities figure.
- Health care facilities figure.
- Places of worship figure.
- Parks and recreation figure when relevant.
- Utility and infrastructure section.
- Public water supply/wells figure when available.
- Utility infrastructure figure.
- Energy infrastructure figure.
- Airports/aviation constraints figure when relevant.
- Contamination risks section.
- Hazardous materials/regulated facilities figure.
- Oil/gas wells figure when available/relevant.
- Socioeconomic and business considerations section.
- Census tracts figure.
- Income demographics table.
- Demographic composition table.
- Optional business/economic node map when source data is available.
- Conclusion and next steps.
- Attachment A: project maps.
- Attachment B: hazardous materials support.
- Attachment C: agency consultation letters or placeholders.
- Reviewer follow-up list for unresolved validation issues, missing sources, and caveats.

Current pipeline check:

- `config/report_section_templates.json` already contains many corresponding report sections and expected visual/table slots.
- Current export supports Markdown and DOCX.
- Current export can render referenced tables and figures inline and avoid duplicate standalone rendering for included artifacts.
- Current review queue can represent findings, report sections, tables, maps, missing-data placeholders, and validation issues.
- Current map generation is vector-only. It does not yet use the newly organized MARIS/NAIP imagery as a basemap source.
- Current deliverable generation can overproduce pages because it may include too many draft items, placeholders, repeated evidence, or broad source/context content.
- Current generation should be redirected so the report is not generated until section-level text, table, and figure inputs are ready.

Discussion items:

- The deliverable inventory should become an export contract: generate at most the sections, maps, tables, attachments, and caveats needed for the selected profile.
- A section should not automatically expand into a long appendix of every individual feature relationship unless the reviewer asks for detail.
- Maps and tables should summarize by project feature and source category, with detailed records kept in evidence artifacts rather than exported by default.
- Attachment content should be curated. The export should not dump every generated map/table/finding into attachments.
- The review queue should stay comprehensive, but export should stay concise.
- The report assembly step should be downstream of complete per-section text/table/figure generation, not an early preview of whatever artifacts happen to exist.

## Source Files Needed For Deliverable Items

Near-term source stack needed to produce the example-style deliverable:

| Deliverable item | Source files / source categories needed |
| --- | --- |
| Project title, location, study area, overview map | Required KMZ project geometry; project metadata; MARIS boundary/county context |
| Environmental constraints inventory | Normalized project features; analysis bounds; all accepted source categories used in constraints |
| Wetlands and waterbodies | USFWS NWI wetlands/waterbodies; local or downloaded wetland layers; optional imagery review context |
| Streams, hydrography, crossings, water quality | USGS NHD hydrography; impaired waters/source water quality layers when available; project geometry |
| Floodplains and floodways | FEMA NFHL flood hazard zones when relevant or explicitly included |
| Soils | USDA NRCS SSURGO soil map units |
| Protected species and critical habitat | USFWS critical habitat GIS; IPaC project report; state heritage/manual review status |
| Cultural and historic resources | Public MDAH/MARIS cultural context; restricted archaeology/SHPO or MDAH review placeholder or reviewer-supplied document |
| Community resources | MARIS community facilities; HIFLD or local facilities where available; schools, health care, fire/EMS, places of worship, parks/recreation |
| Utility and infrastructure | MDOT/local transportation context; utility infrastructure; energy infrastructure; public water supply/wells; airports when relevant |
| Contamination risks | EPA ECHO/Envirofacts; MDEQ environmental context; oil/gas wells where available |
| Socioeconomic context | Census TIGER/Line geography; ACS demographic/income tables |
| Imagery/basemap context | MARIS/NAIP 2025 aerial base maps under `sources/aerial_base_maps/maris_naip_2025/`; other approved basemap sources only if terms and workflow are clear |
| Attachments | Accepted maps; hazardous materials support; agency consultation letters or placeholders; reviewer-supplied documents |

Current pipeline check:

- Implemented or configured local materializers cover NWI wetlands, USFWS Critical Habitat, SSURGO soils, MDOT/rail transportation context, utilities, administrative/boundary context, public cultural context, community facilities, and conservation/recreation lands.
- Implemented public downloaders cover USFWS NWI, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and optional FEMA NFHL flood hazard.
- Census/ACS remains a future downloader/source workflow.
- IPaC, state heritage, restricted archaeology, some MDEQ layers, parcels/property, and many local utility/government sources remain manual, reviewer-supplied, gated, or placeholder-driven.
- MARIS/NAIP 2025 imagery now exists locally as a source warehouse dataset, but it is not yet integrated into map generation or source materialization.

Discussion items:

- We should separate source availability from export necessity. A source can be present and useful without producing a report section or page by default.
- The new NAIP source should probably be cataloged as a local imagery/basemap source before it is used in generated maps.
- NAIP imagery should serve both as the basemap for generated visuals and as reviewer-only visual context.
- Imagery-observed features must remain reviewer-only visual context unless and until a specific reviewed output item promotes them.
- Manual/gated sources should produce concise caveats and reviewer tasks, not pages of placeholder text.
- Census/ACS may be needed for the example deliverable shape, but adding it should be deliberate because it can create large tables and long narrative.

## Review Queue And Export Gate

Planned workflow:

- The review queue should contain exactly one review item per deliverable thing required by the static matrix.
- Review items should map to the needed text sections/subsections, list-of-figures figure targets, list-of-tables table targets, and attachment targets.
- The review queue should not include one item per raw GIS intersection or one item per source feature hit.
- For the example-report working profile, expected review volume should be roughly the deliverable target count: about 37 text section/subsection items, 13 figure items, 4 table items, and 3 attachment items.
- This should be approximately 57 review items, subject to final outline cleanup, not hundreds or thousands.
- Each review item can be accepted as-is, edited, fully replaced with reviewer-provided content, or declined.
- Declined items are removed from the generated report.
- Report generation must not proceed until every posted review item has been accepted, edited, replaced, or declined.
- Once all review items have a reviewed terminal state, the report is generated from stored queued items minus declined items.
- No default report should be generated before review decisions are complete.

Current pipeline check:

- Current review queue can store generated findings, tables, maps, report sections, caveats, source notes, and validation issues.
- Current export can filter accepted/edited items and omit rejected items.
- Current preview export can include drafts, which conflicts with this stricter working direction for default report generation.
- Current queue may still include too many low-level items if raw/detail artifacts are promoted.

Discussion items:

- Define terminal review states clearly: accepted, edited, replaced, declined.
- Map current statuses such as `rejected` to `declined` or decide whether to rename them.
- Disable or clearly separate any internal draft preview path from the default user-facing report generation path.
- Add a queue completeness check before export.
- Add a queue target count check against the deliverable matrix so unexpected item explosion is visible immediately.

## Report Size Control

Goal:

- The export should be a concise, reviewable environmental constraints report package, not a 640-page dump of every generated artifact.
- Default report tables should be based on comparison units, not raw geometry segments or individual source-feature intersections.
- The workflow should not generate a report until the constraint metadata and section-level text/table/figure packages are ready.
- Text generation should produce one coherent draft per section/header target in the deliverable matrix, not one text item per raw constraint.
- The review queue item count should be bounded by the deliverable matrix, not by raw evidence count.
- Default report export should be blocked until all deliverable review items are reviewed.

Current pipeline check:

- Current architecture already separates review queue generation from accepted-content export.
- Preview exports can include draft content and may become very large.
- DOCX export can inline tables and figures, which is useful but can amplify volume if every artifact is included.
- Current grouped constraint tables are closer to the desired report shape than raw constraint summary tables.

Discussion items:

- Define a target page range or export budget for MVP preview packages.
- Separate `review queue completeness` from `deliverable export inclusion`.
- Consider export modes such as `summary`, `standard report`, and `full evidence appendix`.
- Keep detailed evidence in JSON and workspace artifacts; export only summarized accepted content unless a reviewer explicitly includes appendices.
- Add page/section/item counts to export manifests so oversize deliverables are visible before opening the DOCX.
- Add a pre-export warning when raw/detail table row counts exceed a threshold.
- Standard export should prefer one row per comparison unit per consideration/resource category where practical.
- Treat raw constraint records as evidence store rows, not report rows.
- Treat raw constraint records as evidence inputs for text generation, not as separate report paragraphs.
- Add a pre-export hard stop if any deliverable review item is still unreviewed.
- Add a generation warning if review item count exceeds the expected deliverable matrix count.

## Immediate Working Questions

- Resolved for now: the required KMZ represents alternatives/routes input. The first processing output from it is the project bbox, followed by county-name detection and aerial basemap selection before deeper alternative parsing.
- Resolved for now: the example trail project has five comparison units, one per trail alternative. Raw polyline segments are not report comparison units.
- Resolved for now: point-heavy projects should compare style/color/service-area groups by default, not every individual point.
- Resolved for now: deterministic GIS intersections can support generation as source-backed screening facts; reviewer attention should focus on the generated section/table/figure outputs rather than every raw intersection record.
- Resolved for now: report generation should wait until section text, table, and figure inputs are ready.
- Resolved for now: this canonical plan is the working reference for deliverable shape, expected tables/figures, attachments, and formatting.
- Resolved for now: example report text may guide GPT structure and voice, but its project-specific content must not be reused as facts.
- Resolved for now: for the current working profile, every item in the example-report deliverable outline is mandatory as a review target. Items without source data or implementation become stubs with this exact statement: `Empty stub for future implements whenever source data is accessible.`
- Resolved for now: no source category should block generation right now. Missing/unimplemented source categories create required stubs, and the blocking rules can be revisited later.
- Restated old caveat question: "Which missing or uncertain source categories should appear only as short warning/reviewer-note text instead of creating a full report section, table, or figure?" For the current working profile, the answer is none when the item exists in the example deliverable outline; create the required stub instead.
- Resolved for now: NAIP imagery is both the basemap source for generated visuals and a reviewer-only visual context source.
- Resolved for now: default report export should not generate any report until all posted review items have been accepted, edited, replaced, or declined. The final report is generated from reviewed queued items minus declined items.
