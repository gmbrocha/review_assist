# Sprint 1.1: Contract Foundation

## Purpose

Create the static contracts that all redirected pipeline work depends on. This sub-sprint is intentionally configuration and validation heavy. It should not implement source analysis, maps, review queue changes, exports, or UI.

`CANONICAL_PLAN.md` is the canonical planning source. Sprint 1.1 turns its deliverable and prompt contracts into machine-readable configuration and validation.

## Outcome

By the end of Sprint 1.1:

- `config/deliverable_section_matrix.json` exists.
- `config/report_generation_prompts.json` exists.
- Loader/validator services exist for both configs.
- Tests prove IDs, numbering, references, stub policy, and dynamic comparison-unit section templates are stable.
- Docs state the precedence rule clearly.

## Implementation Tasks

### 1. Planning Precedence Alignment

- Add a concise precedence note to project docs touched in this sprint.
- Preserve this rule:
  - `CANONICAL_PLAN.md` controls current planning, deliverable shape, prompt intent, review policy, and export direction.
  - Archived planning docs are historical references only.
- Update only docs directly affected by Sprint 1.1 behavior.
- Keep non-negotiables intact:
  - no ranking.
  - no scoring.
  - no preferred alternative.
  - no project feature rejection.
  - no field verification claims.
  - no restricted source automation.
  - deterministic GIS/source checks stay separate from GPT drafting.

### 2. Deliverable Matrix Config

- Create `config/deliverable_section_matrix.json`.
- Add a loader module, likely `src/review_assist/deliverable_matrix.py`.
- Add a validation error class, likely `DeliverableMatrixError`.
- The loader should expose functions similar to:
  - `load_deliverable_matrix(path: Path | None = None) -> DeliverableMatrixConfig`
  - `resolve_deliverable_targets(profile_id: str | None = None) -> list[dict]`
  - `table_targets(config) -> list[dict]`
  - `figure_targets(config) -> list[dict]`
  - `attachment_targets(config) -> list[dict]`
- Use dataclasses only if they simplify validation; do not overbuild a framework.

### 3. Matrix Top-Level Shape

The matrix should include:

- `matrix_version`
- `profile_id`
- `title`
- `description`
- `source_documents`
- `stub_text`
- `section_targets`
- `table_targets`
- `figure_targets`
- `attachment_targets`
- `numbering_policy`
- `review_policy`

Use this exact `stub_text`:

`Empty stub for future implements whenever source data is accessible.`

### 4. Section Target Contract

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

Validation rules:

- `target_id` is required and unique.
- `target_type` must be one of:
  - `front_matter`
  - `section`
  - `subsection`
  - `dynamic_subsection_template`
  - `attachment`
- `heading_level` must be null or an integer 1 through 4.
- `section_order` must be numeric.
- Required targets must define `stub_when_missing`.
- `prompt_key` must exist in the prompt config after Sprint 1.1 is complete.

### 5. Required Section Targets

Represent the example report at this granularity:

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
- Dynamic 3.1.1.x wetlands/waterbodies comparison-unit subsection template.
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
- Attachment A.
- Attachment B.
- Attachment C.

### 6. Table Target Contract

Add four table targets:

- Table 1:
  - ID: `table-wetlands-waterbodies`
  - Title: `Descriptions of Wetlands and Waterbodies Present within the Study Corridor`
  - Columns:
    - `Alternative`
    - `Stream Crossings`
    - `Freshwater Emergent Wetland`
    - `Freshwater Forested/Shrub Wetland`
    - `Freshwater Pond`
- Table 2:
  - ID: `table-fema-flood-zones`
  - Title: `FEMA Flood Zones within the Study Corridor`
  - Columns:
    - `Alternative`
    - `Flood Zone Classification`
    - `Estimated Acreage`
- Table 3:
  - ID: `table-income-demographics`
  - Title: `Income Demographics of Census Tracts along the Study Corridor`
  - Columns:
    - `Census Tract`
    - `Population Below the Poverty Line`
- Table 4:
  - ID: `table-demographic-composition`
  - Title: `Demographic Composition of Census Tracts along the Study Corridor`
  - Columns:
    - `Geography`
    - `Black or African American`
    - `Asian`
    - `White`

Validation rules:

- Table IDs are unique.
- Table numbers are assigned from order.
- Table columns match exactly.
- Each table points to a known section target.

### 7. Figure Target Contract

Add thirteen figure targets in this order:

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

Validation rules:

- Figure IDs are unique.
- Figure numbers are assigned from order.
- Figure target section refs point to known section targets.
- Missing figure sources later create stubs, not omitted targets.

### 8. Attachment Target Contract

Add:

- Attachment A: Environmental Constraints Maps.
- Attachment B: Hazardous Materials Report.
- Attachment C: Agency Consultation Letters.

Validation rules:

- Attachment IDs are unique.
- Attachment letters are assigned from order.
- Attachment targets can produce stubs.

### 9. Prompt Config

- Create `config/report_generation_prompts.json`.
- Add a loader module or extend the deliverable matrix loader if the interface stays clean.
- Add a validation error class if separate, likely `ReportPromptConfigError`.
- Each prompt record should include:
  - `prompt_key`
  - `target_ids`
  - `system_prompt`
  - `section_instruction`
  - `allowed_inputs`
  - `required_stub_text`
  - `prohibited_claims`
  - `citation_policy`
  - `output_style`
- Include a global prompt record.
- Include prompt records for every section target with a prompt key.

### 10. Prompt Guardrails

The prompt config must explicitly prohibit:

- ranking.
- scoring.
- preferred alternative language.
- alternative selection.
- alternative rejection.
- field verification claims.
- jurisdictional determinations.
- agency approval or clearance claims.
- unsupported facts.
- example-project fact reuse.

The prompt config must require:

- use only current-project evidence.
- reference only known table IDs, figure IDs, source IDs, attachment IDs, and comparison-unit names.
- use exact stub text when source data or implementation is missing.

### 11. CLI Surface

Add CLI commands only if useful and low-friction:

- `review-assist validate-deliverable-matrix`
- `review-assist validate-report-prompts`

If command surface feels too large, skip new commands and test through loader functions.

## Tests

Add focused tests, likely `tests/test_deliverable_matrix.py` and `tests/test_report_prompt_config.py`.

Test cases:

- Matrix loads from default config.
- Matrix contains the exact stub text.
- Section target IDs are unique.
- Table target IDs are unique.
- Figure target IDs are unique.
- Attachment target IDs are unique.
- Table numbers resolve to 1 through 4.
- Figure numbers resolve to 1 through 13.
- Attachment letters resolve to A through C.
- Dynamic wetlands/waterbodies alternative subsection template exists.
- Invalid table ref raises validation error.
- Invalid figure ref raises validation error.
- Prompt config loads.
- Every matrix prompt key exists in prompt config.
- Prompt guardrail list includes ranking, selection, rejection, final determination, and field verification prohibitions.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_deliverable_matrix.py tests\test_report_prompt_config.py
```

## Acceptance Checklist

- Matrix config exists and validates.
- Prompt config exists and validates.
- Loader services exist and are unit tested.
- Dynamic comparison-unit section template is represented but not expanded yet.
- Docs reflect `CANONICAL_PLAN.md` precedence.
- No UI work is introduced.
- No report generation behavior changes yet.
- Focused tests pass.
