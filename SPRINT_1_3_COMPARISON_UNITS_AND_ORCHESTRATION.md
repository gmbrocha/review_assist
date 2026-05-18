# Sprint 1.3: Comparison Units And Orchestration

## Purpose

Separate raw input features from report-facing comparison units and integrate the Sprint 1 foundation into the orchestration path. This sub-sprint is the main geometry-risk slice for Sprint 1.

`PLAN_REDIRECT_NEW.md` is the canonical planning source for duplicated or conflicting workflow decisions.

## Outcome

By the end of Sprint 1.3:

- `projects/<project_id>/intermediate/comparison_units.geojson` is generated.
- optional `projects/<project_id>/intermediate/comparison_units.json` metadata is generated.
- Trail line segments group into alternatives.
- Point-heavy projects group by style/color/service grouping while preserving raw point evidence.
- Populate orchestration records all Sprint 1 artifacts.
- Sprint 1 docs and tests are complete.

## Dependencies

Sprint 1.1:

- matrix loader.
- prompt config loader.

Sprint 1.2:

- input package artifact.
- project area artifact.

Existing code:

- `project_geometry.py`
- `inspection.py`
- `kml.py`
- `populate_for_review.py`

## Implementation Tasks

### 1. Comparison Unit Service

- Add a module, likely `src/review_assist/comparison_units.py`.
- Add constants:
  - `COMPARISON_UNITS_PATH = Path("intermediate/comparison_units.geojson")`
  - `COMPARISON_UNITS_METADATA_PATH = Path("intermediate/comparison_units.json")`
- Add functions:
  - `build_comparison_units(project_dir: Path) -> dict`
  - `load_comparison_units(project_dir: Path) -> dict`
- Add error class:
  - `ComparisonUnitError`

### 2. Artifact Shape

Metadata JSON should include:

- `project_id`
- `project_name`
- `project_dir`
- `created_at`
- `geometry_role`
- `analysis_crs`
- `default_buffer_feet`
- `comparison_unit_count`
- `raw_project_feature_count`
- `expected_comparison_unit_count`
- `expected_count_status`
- `comparison_units_path`
- `project_features_path`
- `validation_issues`
- `output_path`

GeoJSON feature properties should include:

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

### 3. Relationship To Project Features

- Preserve `project_features.geojson` as existing normalized geometry.
- Do not delete or repurpose raw/semi-normalized project features.
- Comparison units become the report-facing analysis units in Sprint 2.
- Sprint 1.3 only creates the artifact and records it in manifests.

### 4. Line Comparison-Unit Rules

For line/corridor projects:

- Group segmented line features into alternatives.
- Prefer grouping keys in this order:
  - explicit folder or placemark alternative name if available.
  - style URL plus candidate label.
  - placemark name.
  - candidate label.
  - fallback generated group.
- Merge connected line pieces.
- Preserve disconnected line pieces as multipart geometry.
- Do not invent missing connections.
- Preserve source feature IDs.
- Record grouping method.
- Emit reviewer-confirmation warning when grouping key is weak or fallback-based.

### 5. Trail Example Rule

- Add project assumption support:
  - `assumptions.expected_comparison_unit_count`
- Set or document the trails expected count as 5.
- If expected count exists:
  - `expected_count_status` is `matched` or `mismatch`.
  - mismatch creates validation issue code `comparison_unit_count_mismatch`.
- Do not hard-code trails-specific count in service logic.

### 6. Point Comparison-Unit Rules

For point-heavy projects:

- Preserve individual points in project features.
- Group report comparison units by:
  - KML style/color where available.
  - explicit folder or group name where available.
  - candidate label where available.
  - fallback all-points group only when no better grouping exists.
- Store point count as `source_feature_count`.
- Store raw point feature IDs.
- Preserve style/color metadata.
- Emit reviewer-confirmation warning when fallback grouping is used.

### 7. Polygon Comparison-Unit Rules

For polygon projects:

- If one named polygon exists, use one comparison unit.
- If multiple named polygons exist, use one comparison unit per name/group.
- If a polygon appears to be a project boundary and line/point propositions also exist, mark it as boundary context and do not treat it as an alternative unless manifest role says so.
- Emit reviewer-confirmation warning for mixed boundary/proposition ambiguity.

### 8. Mixed Geometry Rules

For mixed projects:

- Preserve geometry role per comparison unit.
- Group by geometry family first, then grouping key.
- Emit validation issue code `mixed_geometry_requires_review`.
- Do not discard any input geometry.

### 9. Style/Color Extraction

- Use fields already created by KML ingestion where available.
- If color is not currently preserved, add preservation in the smallest safe place.
- Do not add a large KML parser rewrite unless required.
- Store:
  - `style_url`
  - `style_color`
  - other existing style identifiers if available.

### 10. Populate Integration

Update populate order to:

1. classify input package.
2. build project geometry.
3. build project area.
4. build comparison units.
5. continue existing source flow.

Update populate manifest:

- `input_package_path`
- `project_area_path`
- `comparison_units_path`
- `comparison_units_metadata_path`
- `comparison_unit_count`
- `expected_comparison_unit_count`
- `expected_count_status`
- validation issues from all Sprint 1 steps.

### 11. CLI Surface

Add command if useful:

- `review-assist build-comparison-units <project_dir>`

Support `--json` if consistent with existing CLI patterns.

### 12. Documentation Updates

Update docs touched by Sprint 1 behavior:

- `docs/WORKFLOW_MODEL.md`
- `docs/CURRENT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `PLAN_REDIRECT_NEW.md` if Sprint 1 decisions need cleanup.

Docs should say:

- raw features and comparison units are separate.
- report-facing generation uses comparison units.
- raw segments/points remain evidence.
- expected comparison-unit count can warn before report generation.
- no UI has been implemented.

## Tests

Add tests, likely `tests/test_comparison_units.py`.

Test cases:

- Builds comparison units for line project.
- Merges connected line segments.
- Preserves disconnected line parts as multipart.
- Does not invent connecting geometry.
- Emits expected-count mismatch warning.
- Trails sample resolves to expected five alternatives if project config is set accordingly.
- Point-heavy sample groups by style/color.
- Raw point count is preserved in grouped unit.
- Polygon single geometry creates one comparison unit.
- Mixed geometry emits review warning.
- Comparison unit GeoJSON and metadata load correctly.
- Populate manifest records comparison unit paths/counts.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_comparison_units.py tests\test_populate_for_review.py
```

Then run full Sprint 1 verification:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Acceptance Checklist

- Comparison unit service exists.
- Comparison units are written as GeoJSON.
- Metadata JSON is written.
- Line alternatives are grouped without invented connections.
- Point-heavy inputs group by style/color where possible.
- Expected count warnings exist.
- Populate run includes all Sprint 1 artifacts.
- Docs are aligned.
- Focused and full tests pass.
