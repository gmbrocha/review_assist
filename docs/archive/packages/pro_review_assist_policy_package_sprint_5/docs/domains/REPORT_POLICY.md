# Review Assist Report Policy

This document explains the canonical policy approach captured in `config/review_assist_report_policy.json`.

## Principle

Review Assist should not render a report section merely because a sample report had that section. A section renders only when its policy trigger, source needs, extent semantics, caveats, allowed references, and review gate are satisfied.

## Core fields

- `include_default`: whether the section is part of the generic template.
- `trigger`: what source/project/reviewer condition activates the section.
- `extent_type`: the analysis extent driving the finding.
- `visual_extent_class`: the map frame or presentation extent.
- `comparison_unit_expansion`: none, table_only, context_summary_list, narrative_children, conditional, or manual_only.
- `evidence_patterns`: direct intersections, nearest-within-buffer, count/list context, watershed/downstream context, table summary, map support, or reviewer material.
- `drafting_mode`: deterministic only, GPT with source-backed evidence, GPT after reviewer confirmation, manual only, or disabled/deferred.
- `required_caveat_bundles`: reusable limitations and source warnings.
- `prohibited_claim_bundles`: language that must be blocked or review-gated.
- `allowed_sources`, `allowed_tables`, `allowed_figures`: prevents hallucinated references.

## Section rendering rule

A section may render only if:

1. Its trigger is satisfied.
2. Required source classes are available or manual material is supplied.
3. Its analysis extent is known.
4. Its caveat bundle is attached.
5. Its tables/figures are generated or explicitly omitted with a reason.
6. Its drafting mode permits the requested output.
7. Reviewer gates are satisfied for manual, restricted, cultural, agency, risk, or conclusion material.

## Extent rule

The analysis extent and visual extent may differ. This is allowed, but wording must state which extent drives the finding. A watershed map cannot become a direct project impact claim. A screening buffer count cannot be described as within the project unless the sentence names the buffer.

## GPT rule

GPT is style and synthesis support only. It cannot infer missing policy, missing sources, regulatory determinations, design commitments, or final conclusions.
