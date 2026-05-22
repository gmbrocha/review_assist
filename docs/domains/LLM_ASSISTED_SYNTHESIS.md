# LLM-Assisted Synthesis

This document captures the current GPT/LLM boundary.

## Current Baseline

GPT-backed drafting is implemented for review-candidate section copy. The standard live path is explicit GPT Interpretive Assist over the bounded review queue; legacy report-section GPT support remains available for compatibility/audit runs. GPT runs only after deterministic project geometry, source acquisition/materialization when explicitly requested, source status, source inventory, constraint analysis, deliverable tables/figures, and evidence package generation.

Implemented controls:

- Root `.env` loading with `OPENAI_API_KEY`, `OPENAI_INTERPRETER_MODEL`, and `GPT_DRAFTING`.
- `GPT_DRAFTING=1`, `true`, `yes`, or `on` permits explicit GPT calls.
- `GPT_DRAFTING=0`, `false`, `no`, `off`, empty, or missing disables GPT drafting.
- `draft-section-candidates` is the standard explicit GPT Interpretive Assist command.
- `--gpt-drafting` is required for legacy report-section/package GPT paths; otherwise they stay deterministic.
- `--no-gpt-drafting` keeps deterministic legacy sections for a single run.
- Missing `OPENAI_API_KEY` fails clearly when GPT is enabled.
- `.env` is ignored by Git; `.env.example` contains placeholders only.

The active GPT task is pre-review section copy. GPT does not run source acquisition, geometry normalization, constraint analysis, measurements, review decisions, export acceptance, or source/evidence count generation. Standard populate, web Create Review Queue, developer reset, page load, and overview refresh do not call GPT.

## Structured Inputs

GPT section drafting receives a bounded request:

- Report section metadata and purpose.
- Matrix target metadata when drafting a deliverable item.
- Section policy from `config/report_section_policy.json`.
- Prompt key, global/section prompt constraints, allowed inputs, and citation policy from `config/report_generation_prompts.json`.
- Deterministic baseline copy.
- Related finding IDs.
- Related table IDs.
- Related figure IDs.
- Source refs.
- Reviewer-facing related labels for prose, such as `Table 1`, `Figure 1`, and source display names.
- Visual/table slots.
- Section evidence bundle from `projects/<project_id>/evidence/evidence_package.json`.
- Validation issues.
- Project context and reviewer instructions.
- Explicit objective-language constraints.
- Curated report style context from `config/report_style_context/environmental_constraints_report_style.md`.

The style context is tone/structure guidance only. It is not project evidence, must not be cited, and must not leak example-report facts, trail-specific assumptions, or PEL-specific assumptions into a current project draft. GPT should not read raw project files directly or infer facts outside the structured request.

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
- Process/status language in export-facing content.
- Internal table/figure/source IDs in report-facing prose; IDs are allowed only in the structured citation arrays.
- Pipeline/provenance phrasing such as project-local layer clipping details in report-facing prose.
- Direct-impact wording from context-only evidence.
- Style-context citation or example/style fact leakage.
- Raw rows, coordinates, GeoJSON, or local/source paths.
- Required caveat omissions.
- Public/coarse cultural context overclaims.
- Unknown required caveat IDs in the canonical policy.
- Final impact/no-impact/no-effect language.
- Jurisdictional wetland/water, cultural eligibility/effect/clearance, contamination/liability/cleanup, permit required/not-required, access/mitigation/construction commitment, ranking/scoring/selection, and demographic impact claim families.
- Body-ineligible render-policy items, manual/reviewer-supplied items, restricted/manual source placeholders, and missing-source stubs before any GPT call is planned.
- `section_source_needs` statuses that require manual or restricted reviewer material before a source-backed GPT candidate can be planned.

Rejected GPT output keeps the deterministic baseline content and records validation issues plus GPT provenance.

## Caching And Review Boundary

GPT Interpretive Assist stores accepted/rejected draft metadata under `drafts/gpt_interpretive_assist_cache.json`. Cache entries are keyed by evidence payload hash, section-policy hash, prompt-contract hash, style-context hash, prompt version, and model. Matching accepted cached output is reused by default and skipped when the current queue item already carries matching GPT provenance. Rejected outputs are kept under rejected-cache metadata so they do not overwrite the last accepted cache entry. `--force-refresh` intentionally calls GPT again.

Accepted GPT output updates only `generated_content` on eligible review queue items, marks them `needs_review`, and sets `export_eligible` false. Human review remains mandatory before export.

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
- Token usage when the provider reports it.

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

- Tune prompts/style context after source-backed smoke runs.
- Add stronger unsupported-fact detection beyond current ID, style, caveat, and prohibited-language checks.
- Expand UI provenance/guardrail display beyond the current Overview summary and review item provenance.
- Decide how reviewer edits should affect future GPT regeneration.
- Add optional reviewer-controlled rewrite requests after the review queue UI exists.
