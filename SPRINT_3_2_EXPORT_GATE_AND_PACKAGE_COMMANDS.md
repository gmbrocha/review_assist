# Sprint 3.2: Export Gate And Package Commands

## Purpose

Enforce the review-complete export gate and align package commands with the new bounded deliverable workflow. This sub-sprint changes export behavior but not DOCX styling fidelity beyond labels and manifest updates.

`CANONICAL_PLAN.md` is the canonical planning source for duplicated or conflicting workflow decisions.

## Outcome

By the end of Sprint 3.2:

- Default `export-report` fails until all standard deliverable review items have terminal statuses.
- Accepted, edited, and replaced items export.
- Declined items are omitted.
- Internal preview remains available through `--include-draft`.
- Export manifest records review gate status and deliverable counts.
- Demo/MVP package commands remain preview flows and do not auto-accept items.

## Dependencies

Sprint 3.1:

- deliverable item artifact.
- matrix-bounded review queue.
- terminal statuses.

Existing code:

- `export_report.py`
- `deliverable.py`
- CLI package commands.

## Implementation Tasks

### 1. Review Completeness Check

- Add a review gate helper, likely in `export_report.py` or a small service module.
- The helper should evaluate standard deliverable queue items.
- Terminal statuses:
  - `accepted`
  - `edited`
  - `replaced`
  - `declined`
- Non-terminal:
  - `draft`
  - `needs_review`
  - `needs_verification`
  - `unable_to_verify` unless explicitly export eligible under caveat policy.

### 2. Default Export Failure

Default `export-report` must fail if non-terminal items remain.

Error should include:

- total deliverable item count.
- terminal item count.
- unreviewed item count.
- declined count.
- first several unreviewed item IDs and titles.
- message that `--include-draft` is internal preview only.

### 3. Export Inclusion Rules

Default export includes:

- `accepted`
- `edited`
- `replaced`
- export-eligible `unable_to_verify` if caveat content is present.

Default export excludes:

- `declined`
- `draft`
- `needs_review`
- `needs_verification`
- non-export-eligible `unable_to_verify`

### 4. Content Selection Rules

- `accepted`: use `generated_content`.
- `edited`: use `edited_content`.
- `replaced`: use `replacement_content`.
- `unable_to_verify`: use edited/replacement content if available, otherwise generated caveat content.
- `declined`: omit.

If `edited` has no edited content:

- either fall back to generated content with warning, or reject export for that item.
- Prefer warning and generated fallback only if existing behavior already does this.
- Preserve decision in tests.

If `replaced` has no replacement content:

- treat as non-terminal or validation error.
- Do not export blank replacement.

### 5. Internal Preview Mode

`--include-draft` should:

- bypass review completeness check.
- include draft/unreviewed non-declined content.
- visibly label Markdown and DOCX as internal/pre-review.
- mark manifest `preview_mode: true`.
- not mutate statuses.
- not claim review completion.

### 6. Export Manifest Updates

Add or update manifest fields:

- `review_gate_status`
- `preview_mode`
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
- `unreviewed_items_preview`

### 7. Markdown Export Updates

- Use matrix/deliverable ordering.
- Omit declined items.
- Render accepted stubs exactly as accepted content.
- Include internal preview warning only when `--include-draft`.
- Do not render raw evidence sections by default.
- Keep real-data/stub lineage sections if still required by MVP package policy.

### 8. Demo Package Command

Update `build-demo-deliverable`:

- run populate.
- run export with `--include-draft`.
- do not auto-accept items.
- mark package as internal/pre-review.
- include review gate summary in manifest.

### 9. MVP Package Command

Update `build-mvp-deliverable`:

- keep real-data guardrails.
- fail on mock/test fixture evidence.
- allow clearly labeled stubs.
- do not auto-accept items.
- use preview export unless reviewer statuses are already complete.
- mark manifest clearly as preview when review gate not complete.

### 10. CLI UX

- Ensure export errors are readable in CLI.
- `--json` output should include the gate failure details if available.
- Avoid stack traces for ordinary unreviewed export attempts.

## Tests

Add tests for:

- default export fails when any item is draft.
- default export fails when any item is needs_review.
- default export fails when any item is needs_verification.
- accepted items export generated content.
- edited items export edited content.
- replaced items export replacement content.
- declined items are omitted.
- rejected legacy items are omitted as declined.
- unable_to_verify exports only when export eligible.
- preview export includes draft content.
- preview export labels Markdown as internal/pre-review.
- preview export labels DOCX as internal/pre-review.
- export manifest records review gate status.
- demo package does not mutate statuses.
- MVP package keeps real-data guardrails.

Suggested command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_export_report.py tests\test_review_queue.py
```

## Acceptance Checklist

- Default export is review-gated.
- Error output is actionable.
- Accepted/edited/replaced behavior works.
- Declined behavior works.
- Preview mode remains internal.
- Demo/MVP commands do not auto-accept.
- Manifest contains gate summary.
- Focused tests pass.
