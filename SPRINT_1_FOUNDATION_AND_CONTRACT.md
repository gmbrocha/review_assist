# Sprint 1: Foundation And Deliverable Contract

## Purpose

Build the non-UI foundation for the redirected pipeline. This sprint does not implement the web app. It creates the static deliverable contract, prompt contract, input classification, project area artifact, and comparison-unit artifact that every later sprint uses.

`CANONICAL_PLAN.md` is the canonical planning source. Sprint 1 implements the non-UI foundation derived from that plan. Archived planning documents are historical references only.

## Sprint Outcome

By the end of this sprint, the repo should have:

- A machine-readable deliverable matrix derived from the canonical deliverable contract in `CANONICAL_PLAN.md`.
- A machine-readable prompt profile derived from the canonical prompt contract in `CANONICAL_PLAN.md`.
- A project input package classification artifact.
- A first processing artifact for bbox, counties, basemap paths, and project area provenance.
- A comparison-unit artifact separate from raw input features.
- Updated orchestration order so later steps can consume these artifacts.
- Tests proving the new contract exists and is stable.

## Non-UI Boundary

Do not implement:

- Web app screens.
- Upload widgets.
- Review detail views.
- Export buttons.
- Authentication or multi-user behavior.
- Any frontend framework.

The work is service/CLI only. UI-facing needs should be represented as structured artifacts and service APIs.

## Sub-Sprint Breakdown

- `SPRINT_1_1_CONTRACT_FOUNDATION.md`: deliverable matrix, prompt config, loaders, validation, and precedence docs.
- `SPRINT_1_2_PROJECT_INTAKE_ARTIFACTS.md`: input package classification, project area artifact, county detection, and NAIP/MARIS basemap provenance.
- `SPRINT_1_3_COMPARISON_UNITS_AND_ORCHESTRATION.md`: comparison-unit model, line/point grouping, populate integration, and Sprint 1 documentation/test completion.

## Workstream 1: Document And Precedence Alignment

### 1.1 Establish planning precedence

- Add a short precedence note to durable project docs during implementation:
  - `CANONICAL_PLAN.md` controls current planning, deliverable shape, prompt intent, review policy, and export direction.
  - `docs/WORKFLOW_MODEL.md` remains the aligned workflow model after it is updated to match the canonical plan.
- Search for duplicated conflicts in:
  - `docs/WORKFLOW_MODEL.md`
  - `docs/ARCHITECTURE.md`
  - `docs/ROADMAP.md`
  - `docs/REPORT_ASSEMBLY.md`
  - `docs/MAP_GENERATION.md`
  - `docs/CURRENT_STATE.md`
- Keep UI implementation planning out of Sprints 1 through 3 and leave it to Sprint 4.

### 1.2 Preserve product boundaries

- Confirm all changed docs preserve:
  - No ranking.
  - No scoring.
  - No preferred alternative.
  - No rejection of project features.
  - No field-verification claims.
  - No restricted source automation.
  - Deterministic GIS checks separate from GPT narrative drafting.
  - Review queue as the human-in-the-loop boundary.
- Add the exact stub language where relevant:
  - `Empty stub for future implements whenever source data is accessible.`

### 1.3 Documentation acceptance criteria

- A future engineer can read the root sprint docs plus `CANONICAL_PLAN.md` and know the near-term direction.
- No updated docs imply that raw GIS intersection volume is the report volume.
- No updated docs imply that default export can bypass review.
- No updated docs imply UI work is part of these three sprints.

## Workstream 2: Deliverable Matrix Config

### 2.1 Create the matrix config

- Add `config/deliverable_section_matrix.json`.
- Treat `CANONICAL_PLAN.md` as the human-readable source.
- Add a loader module, likely `src/review_assist/deliverable_matrix.py`.
- The loader must:
  - Read the config.
  - Validate required keys.
  - Return matrix targets in report order.
  - Assign table and figure numbers from matrix order.
  - Support deterministic IDs.
  - Support dynamic alternative subsection expansion.

### 2.2 Matrix top-level fields

Use a clear config shape with these concepts:

- `matrix_version`
- `profile_id`
- `title`
- `stub_text`
- `section_targets`
- `table_targets`
- `figure_targets`
- `attachment_targets`
- `source_category_requirements`
- `numbering_policy`
- `review_policy`

### 2.3 Section target fields

Each section target should include:

- `target_id`
- `target_type`
- `section_number`
- `title`
- `heading_level`
- `section_order`
- `export_group`
- `resource_category`
- `required`
- `prompt_key`
- `source_categories`
- `table_refs`
- `figure_refs`
- `attachment_refs`
- `dynamic_children`
- `stub_when_missing`
- `review_item_type`

### 2.4 Required section targets

Represent at least these section targets:

- Cover/title page.
- List of figures.
- List of tables.
- List of attachments.
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
- Dynamic 3.1.1.x comparison-unit subsections for wetlands and waterbodies.
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
- Attachment A: Project Maps.
- Attachment B: Hazardous Materials Report.
- Attachment C: Agency Consultation Letters.

### 2.5 Table targets

Add exactly four standard table targets for the example profile:

- Table 1:
  - Title: `Descriptions of Wetlands and Waterbodies Present within the Study Corridor`
  - Section: `3.1.1 Wetlands and Waterbodies`
  - Columns:
    - `Alternative`
    - `Stream Crossings`
    - `Freshwater Emergent Wetland`
    - `Freshwater Forested/Shrub Wetland`
    - `Freshwater Pond`
- Table 2:
  - Title: `FEMA Flood Zones within the Study Corridor`
  - Section: `3.1.2 Floodplains and Floodways`
  - Columns:
    - `Alternative`
    - `Flood Zone Classification`
    - `Estimated Acreage`
- Table 3:
  - Title: `Income Demographics of Census Tracts along the Study Corridor`
  - Section: `3.6.1 Demographic Characteristics`
  - Columns:
    - `Census Tract`
    - `Population Below the Poverty Line`
- Table 4:
  - Title: `Demographic Composition of Census Tracts along the Study Corridor`
  - Section: `3.6.1 Demographic Characteristics`
  - Columns:
    - `Geography`
    - `Black or African American`
    - `Asian`
    - `White`

### 2.6 Figure targets

Add exactly these standard figure targets in report order:

- Wetlands and Waterbodies in and near the Study Corridor.
- FEMA Flood Zones in and near the Study Corridor.
- Streams and 303(d) Impaired Waters within the Subwatersheds of the Study Corridor.
- Cultural Resources Sites in or near the Study Corridor.
- Fire Stations in or near the Study Corridor.
- Government Offices near the Study Corridor.
- Schools and Childcare Facilities in or near the Study Corridor.
- Health Care Facilities near the Study Corridor.
- Places of Worship in or near the Study Corridor.
- Public Water Supply Wells near the Study Corridor.
- Energy Infrastructure near the Study Corridor.
- Hazardous Waste Sites near the Study Corridor.
- Census Tracts along the Study Corridor.

### 2.7 Attachment targets

Add exactly these attachment targets:

- Attachment A: Environmental Constraints Maps.
- Attachment B: Hazardous Materials Report.
- Attachment C: Agency Consultation Letters.

### 2.8 Matrix validation rules

- All target IDs must be unique.
- All table refs must point to known table targets.
- All figure refs must point to known figure targets.
- All attachment refs must point to known attachment targets.
- All required targets must specify a fallback stub policy.
- Figure numbers must be assigned from matrix order.
- Table numbers must be assigned from matrix order.
- Dynamic comparison-unit subsections must have a template ID and an expansion rule.

## Workstream 3: Prompt Config

### 3.1 Create prompt config

- Add a machine-readable config, likely `config/report_generation_prompts.json`.
- Use the canonical prompt contract in `CANONICAL_PLAN.md` as the human-readable source.
- Keep prompts generic and structural.
- Do not include example-project facts as current-project evidence.

### 3.2 Prompt fields

Each prompt record should include:

- `prompt_key`
- `section_target_id`
- `system_prompt`
- `section_instruction`
- `allowed_inputs`
- `required_stub_text`
- `prohibited_claims`
- `citation_policy`
- `table_reference_policy`
- `figure_reference_policy`
- `output_style`

### 3.3 Global prompt constraints

The config must preserve:

- Use only current-project evidence.
- Do not reuse example project facts.
- Do not rank alternatives.
- Do not recommend alternatives.
- Do not select, reject, approve, clear, or determine impacts.
- Do not claim field verification.
- Do not claim jurisdictional determinations.
- Reference only known table, figure, attachment, source, and comparison-unit IDs.
- Use the exact stub when source data or implementation is missing.

### 3.4 GPT integration boundary

- Keep GPT downstream of deterministic evidence.
- GPT receives only structured section evidence.
- GPT never receives raw source files, raw root `sources/` paths, raw GeoJSON dumps, or unbounded geometry.
- GPT output remains a review item.
- Deterministic fallback remains available.

## Workstream 4: Input Package Classification

### 4.1 Add input package artifact

- Add `projects/<project_id>/context/input_package.json`.
- Add a service module, likely `input_package.py`.
- Add a CLI command only if useful for testing, such as:
  - `review-assist classify-input-package <project_dir>`
- Also run classification inside `populate-for-review`.

### 4.2 Artifact fields

The artifact should include:

- `project_id`
- `project_name`
- `created_at`
- `input_count`
- `required_kmz_present`
- `inputs`
- `validation_issues`
- `output_path`

Each input record should include:

- `path`
- `resolved_path`
- `exists`
- `extension`
- `manifest_role`
- `classification`
- `source_id`
- `source_category`
- `confidence`
- `requires_reviewer_confirmation`
- `notes`

### 4.3 Classification values

Use a compact set:

- `project_geometry`
- `source_layer`
- `agency_document`
- `supporting_report`
- `imagery_or_basemap`
- `reviewer_notes`
- `unknown`

### 4.4 Near-term rules

- At least one KMZ is required for the near-term workflow.
- If no KMZ exists, generate a validation issue.
- Non-KMZ project geometry support can remain available through existing services, but this sprint should make the near-term KMZ requirement visible.
- Supporting files must not silently alter project bounds unless explicitly marked project geometry.
- If multiple KMZ files are present, classify them and emit a reviewer-confirmation warning unless manifest roles make intent clear.

## Workstream 5: Project Area Artifact

### 5.1 Add project area service

- Add `projects/<project_id>/context/project_area.json`.
- Add a service module, likely `project_area.py`.
- Run it after project geometry normalization and before source status/materialization.
- It should consume:
  - Project manifest.
  - Geometry summary.
  - Project geometry artifact.
  - Project analysis bounds.
  - Optional MARIS boundary context when available.
  - Local NAIP basemap index when available.

### 5.2 Artifact fields

The artifact should include:

- `project_id`
- `project_name`
- `created_at`
- `analysis_crs`
- `default_buffer_feet`
- `bbox_wgs84`
- `bbox_analysis_crs`
- `county_names`
- `county_detection_method`
- `aerial_basemap_source`
- `aerial_basemap_candidates`
- `selected_basemap_paths`
- `renderable_basemap_paths`
- `basemap_rendering_status`
- `warnings`
- `provenance`
- `output_path`

### 5.3 County detection rule

- Prefer boundary-context intersection when a boundary layer is available.
- Use NAIP county folder coverage as a quick project-area helper and basemap selector.
- If the two sources disagree, record both and emit a validation issue.
- If a project crosses multiple counties, preserve all counties and all selected imagery candidates.

### 5.4 Basemap selection rule

- Select candidate county imagery folders from:
  - `sources/aerial_base_maps/maris_naip_2025`
- Store `.sid` paths as source/provenance paths.
- Do not require `.sid` rendering in this sprint.
- Store whether renderable sidecars exist:
  - `.tif`
  - `.tiff`
  - `.png`
- If only `.sid` files exist, mark status as `selected_not_renderable`.

## Workstream 6: Comparison Units

### 6.1 Add comparison-unit artifact

- Add `projects/<project_id>/intermediate/comparison_units.geojson`.
- Add optional metadata at `projects/<project_id>/intermediate/comparison_units.json`.
- Add a service module or extend `project_geometry.py` with a clear comparison-unit boundary.
- Preserve `project_features.geojson` for raw or semi-normalized features.
- Use comparison units for report-facing analysis.

### 6.2 Comparison-unit fields

Each feature should include:

- `comparison_unit_id`
- `comparison_unit_name`
- `comparison_unit_group`
- `comparison_unit_type`
- `geometry_role`
- `source_input`
- `source_feature_ids`
- `source_feature_count`
- `style_url`
- `style_color`
- `placemark_names`
- `candidate_labels`
- `grouping_method`
- `requires_reviewer_confirmation`

### 6.3 Line grouping rules

- Group line segments by stable KML identity in this order:
  - explicit placemark/folder alternative name if available.
  - style URL and candidate label.
  - placemark name.
  - fallback generated feature group.
- Merge connected line pieces when safe.
- Preserve disconnected pieces as multipart geometry.
- Do not invent missing connections.
- For the example trails project, support expected count 5.
- If expected count is set and not met, emit a validation issue.

### 6.4 Point grouping rules

- Preserve raw points as evidence.
- Group point-heavy projects by:
  - style/color.
  - explicit folder or group name.
  - service area label when available.
- The default report comparison unit is the group, not every point.
- Store point counts by group.
- Preserve individual point IDs for later audit/evidence.

### 6.5 Polygon and mixed rules

- Polygon projects use the polygon area as the comparison unit unless multiple named polygons exist.
- Mixed projects preserve per-role comparison units and emit reviewer-confirmation warnings.
- If explicit boundary and propositions are both present, boundary should define project area and propositions should define comparison units.

## Workstream 7: Orchestration Integration

### 7.1 Update populate order

Update service order to:

1. Classify input package.
2. Build project geometry.
3. Build project area.
4. Build comparison units.
5. Continue existing source materialization/acquisition/status flow.

### 7.2 Manifest updates

Update `populate_for_review_run.json` to include:

- `input_package_path`
- `project_area_path`
- `comparison_units_path`
- `comparison_unit_count`
- `project_county_names`
- `basemap_rendering_status`
- validation warnings from these new steps.

### 7.3 Backward compatibility

- Existing commands should continue to work.
- If comparison units do not exist, later services may fall back to project features only during Sprint 1.
- Sprint 2 should remove fallback from standard report-facing generation.

## Workstream 8: Tests

### 8.1 Unit tests

Add tests for:

- Deliverable matrix loads.
- Matrix validates unique IDs.
- Table and figure numbering are stable.
- Dynamic comparison-unit section templates validate.
- Prompt config loads.
- Input package classifies KMZ as project geometry.
- Missing KMZ creates a warning.
- Project area artifact records bbox.
- Project area artifact records NAIP selection status.
- Comparison-unit artifact is written.
- Trail KMZ resolves to expected alternatives or emits clear warning.
- Point-heavy KMZ groups by style/color.

### 8.2 Integration tests

Add tests for:

- `populate-for-review` manifest includes new artifact paths.
- Existing sample projects still run through the new foundation steps.
- New artifacts are JSON/GeoJSON and can be reloaded.

### 8.3 Verification command

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Sprint Acceptance Checklist

- `config/deliverable_section_matrix.json` exists and validates.
- `config/report_generation_prompts.json` exists and validates.
- `input_package.json` is generated.
- `project_area.json` is generated.
- `comparison_units.geojson` is generated.
- `populate_for_review_run.json` records the new artifacts.
- `CANONICAL_PLAN.md` precedence is reflected in updated docs.
- No UI work is introduced.
- No report export behavior is changed yet except artifact availability.
- Tests pass.
