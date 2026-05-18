# Sprint 1.2: Project Intake Artifacts

## Purpose

Create the first runtime artifacts after a project workspace receives inputs: input classification and project area context. This sub-sprint makes the required KMZ, bbox, county names, and NAIP/MARIS basemap source selection explicit before deeper source analysis.

`CANONICAL_PLAN.md` is the canonical planning source for duplicated or conflicting workflow decisions.

## Outcome

By the end of Sprint 1.2:

- `projects/<project_id>/context/input_package.json` is generated.
- `projects/<project_id>/context/project_area.json` is generated.
- The pipeline records bbox, county names, basemap candidates, selected basemap source paths, and basemap renderability status.
- The workflow can warn about missing KMZ, multiple ambiguous KMZs, missing basemap folders, and non-renderable `.sid` imagery.
- Tests cover the sample workspaces and synthetic cases.

## Dependencies

Sprint 1.1 should already provide:

- deliverable matrix loader.
- prompt config loader.
- precedence docs.

This sub-sprint consumes existing services:

- project manifest loading.
- KMZ/KML inspection.
- project geometry generation.
- source materialization conventions.

## Implementation Tasks

### 1. Input Package Service

- Add a module, likely `src/review_assist/input_package.py`.
- Add constants:
  - `INPUT_PACKAGE_PATH = Path("context/input_package.json")`
- Add functions:
  - `classify_input_package(project_dir: Path) -> dict`
  - `load_input_package(project_dir: Path) -> dict`
- Add an error class:
  - `InputPackageError`

### 2. Input Package Artifact Shape

Top-level fields:

- `project_id`
- `project_name`
- `project_dir`
- `created_at`
- `input_count`
- `required_kmz_present`
- `project_geometry_input_count`
- `source_layer_input_count`
- `unknown_input_count`
- `inputs`
- `validation_issues`
- `output_path`

Each input record:

- `path`
- `resolved_path`
- `exists`
- `extension`
- `manifest_role`
- `description`
- `classification`
- `source_id`
- `source_category`
- `confidence`
- `requires_reviewer_confirmation`
- `notes`
- `validation_issues`

### 3. Input Classification Rules

Classification values:

- `project_geometry`
- `source_layer`
- `agency_document`
- `supporting_report`
- `imagery_or_basemap`
- `reviewer_notes`
- `unknown`

Rules:

- Manifest inputs with `source_id` or `source_category` classify as `source_layer`.
- `.kmz` and `.kml` without source IDs classify as `project_geometry`.
- `.geojson`, `.gpkg`, `.shp`, `.zip` can classify as `source_layer` only when manifest metadata says source; otherwise `unknown` or project geometry with reviewer-confirmation warning.
- `.pdf`, `.docx`, `.doc`, `.txt` classify by role/description if clear, otherwise `supporting_report` or `reviewer_notes`.
- `.sid`, `.tif`, `.tiff`, `.png`, `.jpg`, `.jpeg` classify as `imagery_or_basemap`.
- Missing files create warning validation issues.

### 4. Required KMZ Rule

- For near-term redirected workflow, at least one KMZ must be present.
- If no KMZ exists:
  - artifact still writes.
  - `required_kmz_present` is false.
  - validation issue code: `required_kmz_missing`.
- If multiple project-geometry KMZ files exist:
  - artifact still writes.
  - validation issue code: `multiple_project_kmz_inputs`.
  - `requires_reviewer_confirmation` true on ambiguous records unless manifest role disambiguates.

### 5. Project Area Service

- Add a module, likely `src/review_assist/project_area.py`.
- Add constants:
  - `PROJECT_AREA_PATH = Path("context/project_area.json")`
- Add functions:
  - `build_project_area(project_dir: Path) -> dict`
  - `load_project_area(project_dir: Path) -> dict`
- Add error class:
  - `ProjectAreaError`

### 6. Project Area Inputs

The service should consume:

- project manifest.
- input package artifact.
- project geometry artifact.
- project analysis bounds GeoJSON.
- existing project context if available.
- materialized boundary context if available.
- local NAIP/MARIS basemap folders.

If project geometry is missing, build it using existing `build_project_geometry`.

### 7. Project Area Artifact Shape

Top-level fields:

- `project_id`
- `project_name`
- `project_dir`
- `created_at`
- `analysis_crs`
- `default_buffer_feet`
- `bbox_wgs84`
- `bbox_analysis_crs`
- `county_names`
- `county_detection_method`
- `county_detection_sources`
- `aerial_basemap_source`
- `aerial_basemap_root`
- `aerial_basemap_candidates`
- `selected_basemap_paths`
- `renderable_basemap_paths`
- `basemap_rendering_status`
- `warnings`
- `validation_issues`
- `provenance`
- `output_path`

### 8. Bbox Rules

- Read `project_analysis_bounds.geojson`.
- Record bounds in WGS84.
- Record bounds in project analysis CRS.
- Preserve default buffer used to create bounds.
- If bounds cannot be read:
  - raise when project geometry is required.
  - include path in error.

### 9. County Detection Rules

Preferred order:

1. Materialized MARIS boundary context when available.
2. Existing county names in project context when available.
3. NAIP/MARIS county folder candidate names based on spatial availability or project hints.

Implementation detail:

- Boundary-context intersection is more authoritative than folder names.
- NAIP folder names are acceptable as basemap selection hints.
- If county sources disagree, preserve both and emit validation issue code `county_source_disagreement`.
- If no county can be detected, `county_names` is empty and validation issue code `county_detection_unavailable` is emitted.

### 10. NAIP/MARIS Basemap Index

Add a lightweight index helper in this sprint, even if full rendering comes later.

Root:

- `sources/aerial_base_maps/maris_naip_2025`

Index records should include:

- `county_name`
- `county_dir`
- `imagery_dir`
- `sid_paths`
- `metadata_paths`
- `world_file_paths`
- `renderable_sidecar_paths`
- `status`

Recognized file types:

- source/provenance:
  - `.sid`
  - `.sdw`
  - `.xml`
  - `.txt`
- renderable sidecars:
  - `.tif`
  - `.tiff`
  - `.png`

### 11. Basemap Selection Rules

- If detected counties match NAIP county folders, select those folders.
- If no county match exists, do not guess from neighboring counties.
- Store `.sid` paths as selected source paths.
- Store renderable sidecars separately.
- If only `.sid` exists, set `basemap_rendering_status` to `selected_not_renderable`.
- If renderable sidecars exist, set status to `renderable_sidecar_available`.
- If no basemap candidate exists, set status to `not_available`.

### 12. CLI Surface

Add commands if they fit current CLI patterns:

- `review-assist classify-input-package <project_dir>`
- `review-assist build-project-area <project_dir>`

Both should support `--json` if consistent with existing commands.

### 13. Populate Integration

Update `populate-for-review` order to run:

1. input package classification.
2. project geometry.
3. project area.

Update the populate manifest with:

- `input_package_path`
- `project_area_path`
- `project_county_names`
- `basemap_rendering_status`
- validation warnings from both steps.

Do not change later analysis behavior in this sub-sprint.

## Tests

Add tests, likely:

- `tests/test_input_package.py`
- `tests/test_project_area.py`
- focused populate test additions.

Test cases:

- Trails project marks KMZ present.
- Conexon project marks KMZ present.
- Missing KMZ creates `required_kmz_missing`.
- Multiple KMZ files create `multiple_project_kmz_inputs`.
- Source-layer manifest input classifies as `source_layer`.
- Missing input path creates validation issue.
- Project area records WGS84 bbox.
- Project area records analysis CRS bbox.
- Project area handles no county boundary context with warning, not crash.
- NAIP index sees the 82 county folders when local source exists.
- `.sid`-only county imagery returns `selected_not_renderable`.
- Project area artifact can be loaded after write.
- Populate manifest includes input package and project area artifact paths.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_input_package.py tests\test_project_area.py tests\test_populate_for_review.py
```

## Acceptance Checklist

- `input_package.json` writes and loads.
- `project_area.json` writes and loads.
- Missing or ambiguous KMZ states are visible.
- Bbox is recorded.
- County names are recorded when available.
- Basemap candidates and renderability are recorded.
- Populate manifest includes new artifacts.
- No UI work is introduced.
- No map rendering changes are required yet.
- Focused tests pass.
