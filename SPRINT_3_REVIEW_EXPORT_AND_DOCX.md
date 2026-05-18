# Sprint 3: Review Queue, Export Gate, And DOCX Fidelity

## Purpose

Finish the redirected non-UI pipeline by converting the matrix-driven deliverable package into bounded review items and reviewed exports. This sprint enforces the review gate, supports accepted/edited/replaced/declined outcomes, keeps draft preview internal, and improves DOCX output to match the example report format.

`CANONICAL_PLAN.md` is the canonical planning source for duplicated or conflicting workflow decisions. If older docs or current service behavior conflict with it, follow `CANONICAL_PLAN.md`.

## Sprint Outcome

By the end of this sprint, the repo should:

- Generate one standard review item per deliverable target.
- Stop default export until all standard deliverable items have terminal review status.
- Export accepted, edited, and replaced items.
- Omit declined items.
- Keep draft preview as internal/pre-review only.
- Produce DOCX output with example-report formatting targets.
- Keep raw evidence available without flooding the report.
- Update docs and tests to match the new workflow.

## Non-UI Boundary

Do not implement:

- Web app review rows.
- Detail view screens.
- Export tab.
- Browser download behavior.
- Visual drag/drop upload.

The review and export behavior should be service/CLI only.

## Sub-Sprint Breakdown

- `SPRINT_3_1_DELIVERABLE_ITEMS_AND_REVIEW_QUEUE.md`: deliverable item artifact, matrix-driven section text, bounded review queue, and terminal status behavior.
- `SPRINT_3_2_EXPORT_GATE_AND_PACKAGE_COMMANDS.md`: default export review gate, export inclusion rules, preview behavior, package commands, and export manifest updates.
- `SPRINT_3_3_DOCX_FIDELITY_DOCS_AND_FINAL_VERIFICATION.md`: DOCX formatting fidelity, docs alignment, and full end-to-end verification.

## Sprint 1 And 2 Dependencies

This sprint assumes these artifacts exist:

- `config/deliverable_section_matrix.json`
- `config/report_generation_prompts.json`
- `projects/<project_id>/context/input_package.json`
- `projects/<project_id>/context/project_area.json`
- `projects/<project_id>/intermediate/comparison_units.geojson`
- `projects/<project_id>/deliverable/tables.json`
- `projects/<project_id>/deliverable/figures.json`
- updated `projects/<project_id>/evidence/evidence_package.json`

## Workstream 1: Deliverable Items Artifact

### 1.1 Add deliverable item generation

- Add a service module, likely `deliverable_items.py`.
- Output:
  - `projects/<project_id>/deliverable/deliverable_items.json`
- This artifact is the standard source for review queue generation.
- It should compile:
  - section text targets.
  - dynamic comparison-unit subsection targets.
  - table targets.
  - figure targets.
  - attachment targets.
  - required stubs.

### 1.2 Artifact fields

The top-level artifact should include:

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

Each deliverable item should include:

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

### 1.3 Item count policy

- Generate exactly one review item per deliverable target.
- Expected count should be about:
  - 37ish section/subsection targets, including dynamic alternative subsections.
  - 13 figure targets.
  - 4 table targets.
  - 3 attachment targets.
- Do not create one item per raw constraint.
- Do not create one item per source feature.
- Do not create one item per raw geometry segment.

### 1.4 Stub policy

- If a target is required but source data or implementation is missing, generated content must be exactly:
  - `Empty stub for future implements whenever source data is accessible.`
- The item should preserve why it is a stub in provenance or assumptions.
- Stub items are still reviewable.
- Stub items can be accepted, edited, replaced, or declined by the reviewer.

## Workstream 2: Section Text Generation

### 2.1 Matrix-driven sections

- Replace or extend current report section generation so standard section targets come from the matrix.
- Preserve deterministic fallback.
- Preserve optional GPT drafting.
- Generate one section deliverable item per section target.

### 2.2 Dynamic alternative subsections

- For wetlands and waterbodies alternative detail subsections:
  - Generate one child subsection per comparison unit.
  - Use comparison-unit names from `comparison_units.geojson`.
  - Do not hard-code `1A`, `1B`, `2`, `3`, or `4`.
  - For the example trail project, the comparison unit names should naturally produce the five alternative subsections.

### 2.3 Text input package

Each section drafting request should receive:

- section target metadata.
- global prompt.
- section prompt.
- comparison-unit summaries.
- related deliverable table summaries.
- related deliverable figure summaries.
- relevant source statuses.
- relevant source provenance.
- relevant constraint summary.
- validation issues.
- required stub status.

### 2.4 Prohibited text behavior

Generated text must not:

- Rank alternatives.
- Recommend alternatives.
- Select a preferred alternative.
- Reject a project feature.
- Claim field verification.
- Claim agency approval.
- Claim jurisdictional determination.
- Hide missing source data.
- Invent source-backed facts.

### 2.5 GPT guardrail extension

- Validate GPT output against deliverable target IDs.
- Validate cited table IDs.
- Validate cited figure IDs.
- Validate cited source IDs.
- Validate cited comparison-unit names.
- Reject or flag prohibited wording.
- Fall back to deterministic or stub content when GPT output fails.

## Workstream 3: Review Queue Generation

### 3.1 Standard review queue input

- Make standard `generate-review-queue` consume `deliverable_items.json`.
- Keep an explicit audit/evidence mode for current raw findings/tables/maps if needed.
- Default queue must not include raw source inventory, raw comparison tables, or raw constraint relationships.

### 3.2 Review item fields

Ensure review queue items preserve:

- `id`
- `project_id`
- `type`
- `title`
- `generated_content`
- `edited_content`
- `replacement_content`
- `status`
- `export_eligible`
- `export_section`
- `export_group`
- `assumptions`
- `provenance`
- `source_refs`
- `uncertainty_flags`
- `reviewer_notes`
- `created_at`
- `updated_at`
- `deliverable_item_id`
- `target_id`
- `section_order`
- `table_id`
- `figure_id`
- `attachment_id`

### 3.3 Terminal statuses

Support terminal review statuses:

- `accepted`
- `edited`
- `replaced`
- `declined`

Map legacy status:

- `rejected` maps to `declined`.

Keep non-terminal statuses:

- `draft`
- `needs_review`
- `needs_verification`
- `unable_to_verify`

### 3.4 Status behavior

- `accepted` exports generated content.
- `edited` exports edited content.
- `replaced` exports replacement content.
- `declined` omits the item from export.
- `unable_to_verify` exports only if explicitly export eligible and caveat language is present.
- `draft`, `needs_review`, and `needs_verification` block default export.

### 3.5 Reviewer state preservation

When regenerating:

- Preserve accepted, edited, replaced, declined, and reviewer notes if the target ID is stable.
- Do not overwrite reviewer replacement content.
- If source evidence changes materially, add a validation warning rather than silently resetting status.
- Preserve old status by `deliverable_item_id` and `target_id`.

## Workstream 4: Export Gate

### 4.1 Default export gate

Default `export-report` must fail if any standard deliverable review item is non-terminal.

The error should include:

- total review items.
- reviewed item count.
- unreviewed item count.
- first several unreviewed item IDs/titles.
- instruction that internal preview requires `--include-draft`.

### 4.2 Export inclusion rules

Default export includes:

- `accepted`
- `edited`
- `replaced`
- `unable_to_verify` only when explicitly export eligible.

Default export excludes:

- `declined`
- `draft`
- `needs_review`
- `needs_verification`
- non-export-eligible `unable_to_verify`

### 4.3 Internal preview behavior

`--include-draft` remains available for internal preview only.

It must:

- include draft/unreviewed content when requested.
- visibly label Markdown and DOCX as internal/pre-review.
- record preview mode in export manifest.
- not mutate review statuses.
- not imply content is final or reviewed.

### 4.4 Export manifest updates

Manifest should include:

- `review_gate_status`
- `review_item_count`
- `terminal_review_item_count`
- `unreviewed_item_count`
- `declined_item_count`
- `included_item_count`
- `skipped_item_count`
- `deliverable_matrix_version`
- `expected_deliverable_item_count`
- `actual_deliverable_item_count`
- `included_table_ids`
- `included_figure_ids`
- `included_attachment_ids`
- `stub_item_count`
- `preview_mode`

## Workstream 5: DOCX Fidelity

### 5.1 Page setup

Match the canonical deliverable and style contract in `CANONICAL_PLAN.md`:

- Letter size, 8.5 x 11 inches.
- 1 inch margins.
- header distance 0.5 inch.
- footer distance 0.5 inch.
- content width about 6.5 inches.

### 5.2 Fonts and styles

Implement or refine Word styles:

- Body:
  - Calibri.
  - 12 pt.
  - about 1.16 line spacing.
  - 8 pt spacing after.
- Heading 1:
  - Lato.
  - 20 pt.
  - color `#0F4761`.
  - keep with next.
- Heading 2:
  - Lato.
  - 14 pt.
  - color `#0F4761`.
  - keep with next.
- Heading 3:
  - Lato.
  - italic.
  - color `#0F4761`.
  - keep with next.
- Heading 4:
  - italic.
  - color `#4C94D8`.
  - keep with next.
- Caption:
  - Calibri Light.
  - 11 pt.
  - italic.
  - centered.
  - color `#0E2841`.
- Attachment Title:
  - centered.
  - color `#0F4761`.

### 5.3 Title page

Generate:

- Planning/study title when available.
- Project name.
- Route/location descriptor.
- Appendix/report title.
- Report date.
- Project identifiers when available.
- County/state context.
- Right-aligned title formatting.
- Draft/internal preview label only when preview mode is used.

### 5.4 Front matter lists

Generate from accepted/included deliverable items:

- List of figures.
- List of tables.
- List of attachments.

Do not copy inconsistent example numbering.

### 5.5 Section ordering

- Use matrix section order.
- Use section numbers from matrix.
- Use dynamic alternative subsections in comparison-unit order.
- Avoid duplicate headings when generated content starts with the same heading.
- Start major sections on new pages where appropriate.

### 5.6 Tables

- Use Word `Table Grid`.
- Apply consistent header emphasis.
- Add table captions with caption style.
- Render only accepted/included table items.
- Do not render raw evidence tables in the standard report.
- Keep table widths inside 6.5 inch content width.
- Handle long text by wrapping, not overflowing.

### 5.7 Figures

- Embed PNG figures at 6.5 inch width when available.
- Add figure captions with caption style.
- Add source note and method note below figures where available.
- Render stubs/placeholders for accepted figure stubs.
- Copy figure assets into export package assets.
- Preserve original map artifact provenance in the manifest.

### 5.8 Footer

- Include project name and report title.
- Include page numbering where practical.
- Preserve internal/pre-review label in preview exports.

## Workstream 6: CLI And Package Commands

### 6.1 CLI behavior

Update or add commands as needed:

- `generate-deliverable-items`
- `generate-review-queue`
- `export-report`
- `populate-for-review`
- `build-demo-deliverable`
- `build-mvp-deliverable`

### 6.2 Populate for review

The standard populate workflow should run:

1. input package classification.
2. project geometry.
3. project area.
4. comparison units.
5. source materialization/acquisition/status.
6. source inventory.
7. comparison-unit constraints.
8. deliverable tables.
9. deliverable figures.
10. evidence package.
11. report sections.
12. deliverable items.
13. review queue.

### 6.3 Demo deliverable

- Keep demo deliverable as internal preview.
- Do not auto-accept review items.
- Use `--include-draft`.
- Make pre-review labeling unmistakable.

### 6.4 MVP deliverable

- Keep real-data guardrails.
- Fail on mock/test fixture evidence.
- Allow stubs if clearly labeled.
- Do not auto-accept review items.
- Keep preview mode separate from default reviewed export.

## Workstream 7: Documentation Updates

### 7.1 Required docs to review/update

Update docs affected by behavior:

- `CANONICAL_PLAN.md`
- `docs/WORKFLOW_MODEL.md`
- `docs/CURRENT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/REPORT_ASSEMBLY.md`
- `docs/REVIEW_POLICY.md`
- `docs/MAP_GENERATION.md`
- `docs/LLM_ASSISTED_SYNTHESIS.md`
- `docs/DATA_SOURCES.md`

### 7.2 Documentation themes

Docs must reflect:

- `CANONICAL_PLAN.md` precedence for duplicated near-term decisions.
- Web app is future/out of scope for these sprints.
- Default report export is review-gated.
- Review queue item volume is deliverable-matrix bounded.
- Raw evidence remains available but not exported by default.
- Stubs are required for missing mandatory deliverable targets.
- Preview export is internal/pre-review.
- MrSID basemap rendering requires preconverted sidecars.

## Workstream 8: Tests

### 8.1 Review queue tests

Add tests proving:

- Queue is generated from deliverable items.
- Queue item count matches matrix targets.
- Raw constraints do not become default review items.
- Raw comparison tables do not become default review items.
- Existing reviewer status is preserved through regeneration.
- `rejected` maps to `declined`.
- `replaced` requires replacement content.

### 8.2 Export gate tests

Add tests proving:

- Default export fails with unreviewed items.
- Failure reports unreviewed counts.
- Accepted items export.
- Edited items export edited content.
- Replaced items export replacement content.
- Declined items are omitted.
- Draft preview works only with `--include-draft`.
- Preview export is labeled internal/pre-review.

### 8.3 DOCX tests

Add smoke tests proving:

- DOCX is created.
- Title page exists.
- Front matter lists exist.
- Heading styles are present.
- Table captions are present.
- Figure captions are present when figures are included.
- Included tables render inline.
- Included figures render inline.
- Stub items render as stub text when accepted/included.

### 8.4 End-to-end smoke tests

Run a smoke workflow on `projects/trails`:

```powershell
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --materialize-local-sources --prepare-sources --include-optional-sources --no-gpt-drafting
```

Then test:

- default export fails before review completion.
- marking all items accepted allows export.
- DOCX and Markdown are generated.
- manifest reports expected item counts.

### 8.5 Full verification

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Sprint Acceptance Checklist

- `deliverable_items.json` exists.
- Standard review queue is matrix bounded.
- Review terminal statuses work.
- Default export is blocked until all deliverable items are terminal.
- Declined items do not export.
- Replaced items export replacement content.
- Internal preview remains available and visibly labeled.
- DOCX formatting moves materially closer to the example report.
- Docs are updated for the new behavior.
- Tests pass.
