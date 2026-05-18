# LLM-Assisted Synthesis

This document captures the current GPT/LLM boundary.

## Current Baseline

GPT-backed drafting is implemented for pre-review section copy used by legacy report sections and standard matrix-backed deliverable items. It runs after deterministic project geometry, source acquisition, source status, source inventory, constraint analysis, deliverable tables/figures, and evidence package generation.

Implemented controls:

- Root `.env` loading with `OPENAI_API_KEY`, `OPENAI_INTERPRETER_MODEL`, and `GPT_DRAFTING`.
- `GPT_DRAFTING=1`, `true`, `yes`, or `on` enables GPT drafting.
- `GPT_DRAFTING=0`, `false`, `no`, `off`, empty, or missing disables GPT drafting.
- `--no-gpt-drafting` forces deterministic sections for a single run.
- Missing `OPENAI_API_KEY` fails clearly when GPT is enabled.
- `.env` is ignored by Git; `.env.example` contains placeholders only.

The active GPT task is pre-review section copy. GPT does not run source acquisition, geometry normalization, constraint analysis, measurements, review decisions, review queue status changes, or export acceptance.

## Structured Inputs

GPT section drafting receives a bounded request:

- Report section metadata and purpose.
- Matrix target metadata when drafting a deliverable item.
- Prompt key, global/section prompt constraints, allowed inputs, and citation policy from `config/report_generation_prompts.json`.
- Deterministic baseline copy.
- Related finding IDs.
- Related table IDs.
- Related figure IDs.
- Source refs.
- Visual/table slots.
- Section evidence bundle from `projects/<project_id>/evidence/evidence_package.json`.
- Validation issues.
- Project context and reviewer instructions.
- Explicit objective-language constraints.

GPT should not read raw project files directly or infer facts outside the structured request.

## Structured Outputs

GPT must return structured section output with:

- Draft section content.
- Cited finding IDs.
- Cited table IDs.
- Cited figure IDs.
- Cited source refs.
- Caveats.

Generated sections become reviewable `section_text` deliverable items in the standard queue or legacy `report_section` review queue items in audit/compatibility flows. They are not auto-accepted and do not bypass reviewer status, reviewer edits, replacement content, or export eligibility.

## Guardrails

The implementation validates GPT output for:

- Unknown cited finding IDs.
- Unknown cited table IDs.
- Unknown cited figure IDs.
- Unknown source refs.
- Preferred-alternative language.
- Best/worst/ranking/scoring language.
- Reject/select language.
- Final-determination language.
- Jurisdictional-certainty language.
- Field-verification claims.

Rejected GPT output keeps the deterministic baseline content and records validation issues plus GPT provenance.

## Provenance

GPT-drafted sections store:

- Provider.
- Model.
- Prompt version.
- Response schema version.
- Generated timestamp.
- Input digest.
- Output digest.
- Evidence package path.
- Validation warnings.

Export and deliverable manifests summarize GPT drafting status and counts when GPT-backed sections are present. Deliverable item provenance also records prompt-contract metadata and structured-evidence request digests.

## Boundaries

LLMs must not:

- Invent findings.
- Create source-backed facts without source data.
- Decide that an alternative is preferred.
- Rank, score, select, or reject alternatives.
- Hide missing data.
- Convert review items into authoritative facts.
- Claim field verification or final jurisdictional determinations.
- Produce final reports without human review.

## Future Work

- Improve prompts against the example report template after MVP smoke runs.
- Add stronger unsupported-fact detection beyond ID and prohibited-language checks.
- Show GPT provenance and guardrail warnings in the future UI.
- Decide how reviewer edits should affect future GPT regeneration.
- Add optional reviewer-controlled rewrite requests after the review queue UI exists.
