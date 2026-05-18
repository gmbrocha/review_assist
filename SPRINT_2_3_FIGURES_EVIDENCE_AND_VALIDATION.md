# Sprint 2.3: Figures, Evidence, And Validation

## Purpose

Generate exact deliverable figure targets from the matrix and align evidence packages to the new bounded report workflow. This sub-sprint completes Sprint 2 by replacing unbounded source-context figure behavior with matrix-driven figure artifacts for the standard report path.

`CANONICAL_PLAN.md` is the canonical planning source for duplicated or conflicting workflow decisions.

## Outcome

By the end of Sprint 2.3:

- Thirteen standard deliverable figure targets generate or stub.
- Figure records are tied to matrix targets.
- Renderable NAIP sidecars are used when available.
- Vector-only fallback/stub behavior is explicit.
- Evidence packages reference deliverable tables and figures.
- Raw map/source artifacts remain evidence, not standard report volume.

## Dependencies

Sprint 1:

- deliverable matrix.
- project area.
- comparison units.

Sprint 2.1:

- basemap service.
- source/profile updates.

Sprint 2.2:

- comparison-unit constraints.
- deliverable tables.

Existing code:

- `maps.py`
- `evidence_package.py`
- export figure asset conventions.

## Implementation Tasks

### 1. Deliverable Figure Service

- Add `src/review_assist/deliverable_figures.py` or cleanly extend `maps.py`.
- Output:
  - `projects/<project_id>/deliverable/figures.json`
- PNG output remains under:
  - `projects/<project_id>/maps/figures/`
- Standard report-facing figures should come from the matrix.

### 2. Figure Artifact Shape

Top-level:

- `project_id`
- `project_name`
- `created_at`
- `matrix_version`
- `figure_count`
- `figures`
- `validation_issues`
- `upstream_artifacts`
- `output_path`

Each figure:

- `figure_id`
- `figure_number`
- `title`
- `section_target_id`
- `image_path`
- `caption`
- `source_note`
- `method_note`
- `shown_layers`
- `source_refs`
- `comparison_unit_ids`
- `related_constraint_ids`
- `provenance`
- `uncertainty_flags`
- `is_stub`
- `stub_text`
- `review_status`

### 3. Figure Generation Rules

- Create a record for every matrix figure target.
- If required source data is available, render the figure.
- If source data is missing or implementation is absent, create a stub record.
- If vector data exists but basemap is not renderable, render vector-only and add warning if the figure can still be useful.
- Do not silently omit figure targets.

### 4. Basemap Rendering Rules

- Use renderable NAIP sidecars only:
  - `.tif`
  - `.tiff`
  - `.png`
- Do not decode `.sid` directly.
- If `rasterio` is added, use it only for GeoTIFF sidecars.
- If sidecar rendering fails:
  - create validation issue.
  - fall back to vector-only or stub depending on figure target.
- Always preserve source `.sid` path in provenance when selected.

### 5. Standard Figure Target Rules

Generate or stub:

- Wetlands and Waterbodies:
  - comparison units.
  - NWI wetlands/waterbodies.
  - hydrography when available.
  - NAIP basemap when renderable.
- FEMA Flood Zones:
  - comparison units.
  - FEMA flood hazard polygons.
- Streams and 303(d) Impaired Waters:
  - hydrography.
  - impaired waters if source exists; otherwise warning/stub for impaired-water portion.
- Cultural Resources:
  - public cultural resources only.
  - no restricted archaeology locations.
- Fire Stations:
  - fire/EMS facilities.
- Government Offices:
  - government/civic facilities where available.
- Schools and Childcare:
  - schools/childcare facilities where available.
- Health Care Facilities:
  - health care facilities where available.
- Places of Worship:
  - places of worship where available.
- Public Water Supply Wells:
  - public water supply source where available.
- Energy Infrastructure:
  - transmission/substations/pipelines/energy facilities where available.
- Hazardous Waste Sites:
  - EPA/ECHO and MDEQ/manual contamination sources where available.
- Census Tracts:
  - Census tract polygons and comparison units.

### 6. Panel Maps

- Add first-pass Attachment A panel support.
- Do not add panel maps to the 13 main figure targets unless the matrix explicitly does so later.
- Store panel maps as attachment-supporting records.
- Trigger panel maps when map extent would make the 6.5 inch report figure unreadable.
- Use simple generated panel extents; avoid complex cartographic automation.

### 7. Map Styling

Maintain:

- draft/pre-review label.
- legend.
- north arrow.
- scale bar where CRS allows.
- source note.
- method note.
- readable comparison unit overlay.
- resource category colors.

Target:

- 6.5 inch figure width.
- clear labels without overcrowding.
- no ranking or recommendation symbology.

### 8. Evidence Package Update

Update `evidence_package.py` so section evidence includes:

- comparison unit summaries.
- deliverable table IDs.
- deliverable figure IDs.
- deliverable table row summaries.
- figure availability/stub status.
- source-backed constraint summaries.
- missing/manual/gated source status.
- raw evidence artifact paths.

### 9. Evidence Size Controls

- Do not embed full geometries.
- Do not embed root `sources/` paths in GPT payloads.
- Do not embed raw feature dumps.
- Include compact IDs, counts, acreage, distances, source refs, and validation issues.

### 10. Validation Issues

Add clear issue codes:

- `figure_source_missing`
- `figure_source_unimplemented`
- `basemap_selected_not_renderable`
- `basemap_render_failed`
- `restricted_source_not_mapped`
- `figure_created_as_stub`
- `panel_map_generation_skipped`

## Tests

Add tests for:

- deliverable figure artifact writes.
- figure count is 13 for the example matrix.
- each figure has matrix target ID.
- missing source creates stub record.
- `.sid`-only basemap creates warning.
- renderable sidecar is selected when present.
- public cultural figure excludes restricted source details.
- Census tract figure stubs when Census source missing.
- panel records are attachment-supporting, not extra main figures.
- evidence package includes deliverable table refs.
- evidence package includes deliverable figure refs.
- GPT-bound evidence omits root source paths and full geometry.

Suggested command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_maps.py tests\test_evidence_and_gpt.py
```

Then run Sprint 2 verification:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Acceptance Checklist

- Deliverable figure artifact exists.
- Thirteen figure targets generate or stub.
- NAIP sidecar renderability is respected.
- Restricted cultural data is not exposed.
- Evidence package references deliverable tables/figures.
- Raw maps/tables remain evidence, not standard export volume.
- Populate manifest records deliverable figures and updated evidence package.
- Focused and full tests pass.
