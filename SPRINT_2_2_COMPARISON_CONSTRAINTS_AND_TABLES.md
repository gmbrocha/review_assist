# Sprint 2.2: Comparison Constraints And Tables

## Purpose

Move report-facing analysis from raw project features to comparison units and generate the exact standard deliverable tables. This sub-sprint is the main deterministic analysis and aggregation slice.

`PLAN_REDIRECT_NEW.md` is the canonical planning source for duplicated or conflicting workflow decisions.

## Outcome

By the end of Sprint 2.2:

- Standard report-facing constraints run by comparison unit.
- Raw constraint records remain evidence.
- Source-specific normalization supports table aggregation.
- Four deliverable table targets generate or stub.
- Wetlands and floodplain tables match the example report schema.

## Dependencies

Sprint 1:

- comparison units.
- deliverable matrix.
- project area.

Sprint 2.1:

- example profile.
- source status updates.
- basemap/source profile setup.

Existing code:

- `constraints.py`
- `tables.py`
- `source_materialization.py`
- source acquisition/downloaders.

## Implementation Tasks

### 1. Report-Facing Constraint Service

- Either extend `constraints.py` or add `deliverable_constraints.py`.
- Consume `comparison_units.geojson`.
- Preserve existing raw/project-feature constraint behavior for evidence and backwards compatibility.
- Output standard comparison-unit constraint artifact if separate, likely:
  - `projects/<project_id>/constraints/comparison_unit_constraints.json`

### 2. Constraint Record Fields

Each report-facing constraint record should include:

- `constraint_id`
- `comparison_unit_id`
- `comparison_unit_name`
- `comparison_unit_group`
- `comparison_unit_type`
- `geometry_role`
- `raw_feature_ids`
- `raw_feature_count`
- `source_id`
- `source_name`
- `source_category`
- `source_layer`
- `source_feature_label`
- `source_feature_type`
- `source_feature_subtype`
- `source_feature_original_id`
- `relationship_type`
- `buffer_feet`
- `analysis_geometry_kind`
- `measurement_crs`
- `measurements`
- `source_feature_values`
- `provenance`
- `uncertainty_flags`

### 3. Geometry Measurement Policy

- Use the project `default_buffer_feet` as distance from geometry.
- Default remains 100 feet unless overridden.
- Use buffered corridor geometry for area calculations on line alternatives.
- Store whether measurement used:
  - raw line.
  - buffered corridor.
  - polygon.
  - nearest distance.
- Store units for:
  - feet.
  - acres.
  - CRS.

### 4. No-Overlap Evidence

- Generate no-overlap context only at source/category/comparison-unit summary level.
- Do not create one row per no-overlap source feature.
- Do not create review items here.

### 5. NWI Normalization

Add canonical wetland class mapping:

- Freshwater Emergent Wetland.
- Freshwater Forested/Shrub Wetland.
- Freshwater Pond.
- Other/Unmapped class for evidence only.

Use available fields in this order:

- normalized `review_assist_feature_type`
- normalized `review_assist_feature_subtype`
- `ATTRIBUTE`
- `WETLAND_TYPE`
- `SYSTEM`
- `CLASS_NAME`

De-duplicate by:

- original feature ID if present.
- source feature label plus geometry hash fallback.

### 6. Hydrography Crossing Normalization

- Count stream/hydrography crossings by comparison unit.
- Prefer `crosses` relationships.
- Include `intersects` only when geometry types indicate a crossing-like line relationship.
- Do not count waterbody area overlap as a stream crossing.
- De-duplicate by original hydrography feature ID where available.

### 7. FEMA Flood Normalization

Normalize fields:

- flood zone classification from `FLD_ZONE` or normalized type.
- zone subtype from `ZONE_SUBTY`.
- SFHA flag.
- source citation.
- effective/panel date when present.

Aggregate by:

- comparison unit.
- flood zone classification.

Measure:

- acreage of buffered comparison-unit corridor overlap.

### 8. Census Normalization

- Implement enough Census data handling for table stubs or mocked success.
- Use 2024 ACS 5-year as default.
- Require `CENSUS_API_KEY` for live API calls.
- If key or source is missing, deliverable demographic tables become stubs.
- Do not make final equity or demographic impact conclusions.

### 9. Deliverable Table Service

- Add `src/review_assist/deliverable_tables.py`.
- Output:
  - `projects/<project_id>/deliverable/tables.json`
- Consume:
  - deliverable matrix.
  - comparison units.
  - comparison-unit constraints.
  - source status.
  - project area.
  - Census data where available.

### 10. Deliverable Table Artifact Shape

Top-level fields:

- `project_id`
- `project_name`
- `created_at`
- `matrix_version`
- `table_count`
- `tables`
- `validation_issues`
- `upstream_artifacts`
- `output_path`

Each table:

- `table_id`
- `table_number`
- `title`
- `section_target_id`
- `columns`
- `rows`
- `row_count`
- `source_refs`
- `related_constraint_ids`
- `comparison_unit_ids`
- `provenance`
- `uncertainty_flags`
- `is_stub`
- `stub_text`
- `review_status`

### 11. Wetlands/Waterbodies Table

Exact columns:

- `Alternative`
- `Stream Crossings`
- `Freshwater Emergent Wetland`
- `Freshwater Forested/Shrub Wetland`
- `Freshwater Pond`

Rules:

- One row per comparison unit.
- Stream crossings from hydrography crossing counts.
- Wetland columns are de-duplicated NWI feature counts by class.
- If NWI or hydrography source is missing, populate available fields and preserve uncertainty, or stub the table if the matrix requires all source inputs.
- Do not include raw source feature rows.

### 12. Floodplains/Floodways Table

Exact columns:

- `Alternative`
- `Flood Zone Classification`
- `Estimated Acreage`

Rules:

- One row per comparison unit plus flood classification.
- Multiple flood zones create multiple rows for that alternative.
- Estimated acreage is rounded consistently.
- If no flood overlap, use a no mapped intersection row only if matrix policy requires every comparison unit represented.
- If FEMA source is missing/unimplemented, generate table stub.

### 13. Demographic Tables

Income table:

- `Census Tract`
- `Population Below the Poverty Line`

Composition table:

- `Geography`
- `Black or African American`
- `Asian`
- `White`

Rules:

- Generate from Census source when available.
- Include tract rows and broader comparison rows when available.
- Stub when source/API not available.

### 14. CLI/Orchestration

Add command if useful:

- `review-assist generate-deliverable-tables <project_dir>`

Update populate after constraint analysis:

- generate deliverable tables.
- record `deliverable_tables_path`.

## Tests

Add tests for:

- comparison-unit constraints use comparison unit IDs.
- raw feature IDs are preserved.
- line buffer acreage uses `default_buffer_feet`.
- NWI class mapping.
- hydrography crossing de-duplication.
- FEMA classification acreage aggregation.
- wetlands table exact columns.
- wetlands table one row per comparison unit.
- flood table exact columns.
- flood table multiple classifications.
- Census missing key produces stubs.
- deliverable tables artifact validates and loads.
- populate manifest includes deliverable tables path.

Suggested command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_project_geometry_and_constraints.py tests\test_source_inventory_and_tables.py
```

## Acceptance Checklist

- Comparison-unit constraints exist.
- Raw evidence remains available.
- Deliverable table artifact exists.
- Four standard tables generate or stub.
- Wetlands and flood table schemas match exactly.
- Census tables stub cleanly when data unavailable.
- Populate manifest records deliverable tables.
- Focused tests pass.
