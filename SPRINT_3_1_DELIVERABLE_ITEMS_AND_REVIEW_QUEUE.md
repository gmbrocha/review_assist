# Sprint 3.1: Deliverable Items And Review Queue

## Purpose

Create the bounded deliverable item layer and make the standard review queue use it. This sub-sprint turns the matrix-driven sections, tables, figures, attachments, and stubs into one review item per deliverable target.

`CANONICAL_PLAN.md` is the canonical planning source for duplicated or conflicting workflow decisions.

## Outcome

By the end of Sprint 3.1:

- `projects/<project_id>/deliverable/deliverable_items.json` exists.
- Standard review queue generation uses deliverable items.
- Raw GIS relationships and raw comparison tables are excluded from the standard queue.
- Terminal statuses include `accepted`, `edited`, `replaced`, and `declined`.
- Legacy `rejected` maps to `declined`.
- Reviewer state survives regeneration by stable target IDs.

## Dependencies

Sprint 1:

- deliverable matrix.
- prompt config.
- comparison units.

Sprint 2:

- deliverable tables.
- deliverable figures.
- evidence package.

Existing code:

- `report_sections.py`
- `section_drafting.py`
- `review_queue.py`

## Implementation Tasks

### 1. Deliverable Item Service

- Add `src/review_assist/deliverable_items.py`.
- Output:
  - `projects/<project_id>/deliverable/deliverable_items.json`
- Add functions:
  - `generate_deliverable_items(project_dir: Path) -> dict`
  - `load_deliverable_items(project_dir: Path) -> dict`
- Add error class:
  - `DeliverableItemsError`

### 2. Deliverable Item Artifact Shape

Top-level:

- `project_id`
- `project_name`
- `created_at`
- `matrix_version`
- `profile_id`
- `item_count`
- `expected_item_count`
- `items`
- `validation_issues`
- `upstream_artifacts`
- `output_path`

Each item:

- `deliverable_item_id`
- `target_id`
- `target_type`
- `review_item_type`
- `title`
- `section_number`
- `section_order`
- `heading_level`
- `export_group`
- `resource_category`
- `generated_content`
- `replacement_content`
- `table_id`
- `figure_id`
- `attachment_id`
- `source_refs`
- `related_finding_ids`
- `related_constraint_ids`
- `related_table_ids`
- `related_figure_ids`
- `comparison_unit_ids`
- `provenance`
- `assumptions`
- `uncertainty_flags`
- `is_stub`
- `stub_text`
- `review_status`
- `export_eligible`

### 3. Item Generation Sources

Compile deliverable items from:

- matrix section targets.
- dynamic comparison-unit section expansions.
- deliverable table records.
- deliverable figure records.
- attachment targets.
- evidence package section bundles.
- source status stubs.
- validation issues when tied to a deliverable target.

### 4. Section Text Generation

- Generate section deliverable item content from matrix targets.
- Keep deterministic fallback.
- Use GPT provider only when existing GPT controls enable it.
- GPT input must include only structured evidence.
- Do not send raw source paths, raw geometries, or full feature dumps.

### 5. Dynamic Alternative Subsections

- Expand wetlands/waterbodies alternative detail section once per comparison unit.
- Use comparison unit display name.
- Use matrix section-number template.
- Do not hard-code trail names.
- Preserve stable IDs:
  - base target ID plus comparison unit ID.

### 6. Stub Generation

- Required target with missing data or missing implementation gets exact generated content:
  - `Empty stub for future implements whenever source data is accessible.`
- Preserve source reason in provenance:
  - source missing.
  - source manual.
  - source restricted.
  - source unimplemented.
  - renderable asset missing.
- Stub items still enter review queue.

### 7. Standard Review Queue Source

- Update `generate-review-queue` default behavior to consume `deliverable_items.json`.
- Keep old raw/evidence item generation available only behind explicit audit flag if needed.
- Do not default to:
  - raw draft findings.
  - raw comparison tables.
  - raw spatial relationships.
  - source inventory notes.

### 8. Review Item Fields

Ensure review queue items preserve:

- `deliverable_item_id`
- `target_id`
- `section_order`
- `heading_level`
- `table_id`
- `figure_id`
- `attachment_id`
- `comparison_unit_ids`
- existing provenance/source/uncertainty fields.

### 9. Terminal Statuses

Add or validate support for:

- `accepted`
- `edited`
- `replaced`
- `declined`

Legacy mapping:

- `rejected` is accepted on load for backwards compatibility and normalized or treated as `declined`.

Non-terminal statuses:

- `draft`
- `needs_review`
- `needs_verification`
- `unable_to_verify`

### 10. Status Semantics

- `accepted`: export generated content.
- `edited`: export edited content.
- `replaced`: export replacement content.
- `declined`: omit from export.
- `unable_to_verify`: export only when explicitly export eligible and caveat language exists.
- `draft`, `needs_review`, `needs_verification`: block default export in Sprint 3.2.

### 11. Reviewer State Preservation

When regenerating:

- Preserve terminal statuses by `deliverable_item_id`.
- Preserve reviewer notes.
- Preserve edited content.
- Preserve replacement content.
- Preserve export eligibility where safe.
- If upstream evidence digest changes materially, add validation warning rather than silently resetting.

### 12. CLI Surface

Add command:

- `review-assist generate-deliverable-items <project_dir>`

Update:

- `populate-for-review` to run deliverable item generation before review queue generation.
- `generate-review-queue` to generate deliverable items first if missing.

## Tests

Add tests for:

- deliverable items artifact writes.
- item count matches matrix plus dynamic comparison-unit expansions.
- one review item per deliverable item.
- raw constraints excluded from standard queue.
- raw comparison tables excluded from standard queue.
- stubs become review items.
- dynamic alternative subsections become review items.
- accepted status is preserved through regeneration.
- edited content is preserved through regeneration.
- replacement content is preserved through regeneration.
- `rejected` maps to `declined`.
- `replaced` without replacement content creates validation issue.

Suggested command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_review_queue.py tests\test_report_sections.py
```

## Acceptance Checklist

- Deliverable item artifact exists.
- Standard queue is matrix bounded.
- Raw evidence no longer floods standard queue.
- Terminal statuses exist.
- Reviewer state is preserved.
- Populate manifest records deliverable items path.
- Focused tests pass.
