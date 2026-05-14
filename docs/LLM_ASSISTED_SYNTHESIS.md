# LLM-Assisted Synthesis

This document captures likely future GPT/LLM insertion points.

No LLM workflow is implemented yet.

## Purpose

LLMs may help convert structured findings and source-status context into useful draft language, summaries, caveats, and reviewer prompts. They should reduce blank-page work without replacing source-backed analysis or human judgment.

## Allowed Future Use Cases

Potential use cases:

- Draft narrative generation.
- Findings summarization.
- Contextual implication drafting.
- Uncertainty phrasing.
- Missing/gated source caveat drafting.
- Report synthesis.
- Pre-review sanity checks.
- Structured finding normalization.
- Reviewer-note cleanup.
- Section completeness checks.

## Boundary

Deterministic GIS/source analysis must remain separate from LLM synthesis.

LLMs should not:

- Invent findings.
- Create source-backed facts without source data.
- Decide that an alternative is preferred.
- Rank alternatives.
- Hide missing data.
- Convert review items into authoritative facts.
- Produce final reports without human review.

## Suggested Architecture

LLM calls should receive structured inputs such as:

- Finding records.
- Source records.
- Method notes.
- Review statuses.
- Uncertainty flags.
- Report section target.
- Approved writing pattern.

LLM calls should return:

- Draft paragraphs.
- Bullet summaries.
- Suggested implication wording.
- Questions for reviewer.
- Consistency warnings.

Outputs should be stored separately from underlying findings and marked as draft narrative.

LLM outputs should become review queue items before export.

## Prompting Principles

Future prompts should:

- State that the output is pre-review draft language.
- Require source-backed statements to cite finding/source IDs.
- Require uncertainty to remain visible.
- Prohibit preferred-alternative recommendations.
- Prohibit field-verified language unless the input explicitly says field verified.
- Ask for gaps and reviewer questions when source data is missing.

## Sanity Checks

LLM-assisted pre-review checks may look for:

- Unsupported conclusions.
- Missing caveats.
- Inconsistent alternative names.
- Missing source references.
- Statements that imply final determinations.
- Statements that rank alternatives.
- Report sections with no finding or no missing-data explanation.
- Draft content that bypasses the review queue.

## Open Questions

- Which LLM tasks should be allowed in the first prototype?
- Should LLM calls happen before or after reviewer edits?
- How should prompts and outputs be logged for auditability?
- Should draft narrative be regenerated after finding edits, or manually maintained?
