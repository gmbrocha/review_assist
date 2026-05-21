# Review Assist Codex Prompt Starters

## P0 - canonical report policy

Build `config/review_assist_report_policy.json` as the canonical report policy object. Every section must define `include_default`, `trigger`, `extent_type`, `visual_extent_class`, `comparison_unit_expansion`, `evidence_patterns`, `drafting_mode`, `required_caveat_bundles`, `prohibited_claim_bundles`, `allowed_sources`, `allowed_tables`, `allowed_figures`, and review requirements. Update report generation so a section cannot render unless its trigger, source status, extent type, caveat bundle, and allowed refs are satisfied.

## P0 - extent semantics

Add explicit `analysis_extent` and `visual_extent` fields to deliverable sections, figures, and evidence records. Update wording helpers so within, near, adjacent, downstream, watershed, county/regional, APE, corridor, and shown on map are only used when their configured semantics are satisfied. Add tests preventing a watershed or visual map extent from being described as a direct project intersection.

## P0 - GPT guardrails

Implement a GPT eligibility matrix from report policy. GPT drafting is allowed only for sections whose policy permits it and whose evidence packet contains the required source-backed records. Enforce prohibited claim bundles before and after generation. Block or review-gate final impact, no effect, jurisdictional, eligibility, contamination, permit, and commitment language.

## P1 - table/figure matrix

Create a deliverable table/figure matrix from policy. Wetland, waterbody, floodplain, hazmat, community-resource, utility, and demographic outputs should be generated only when required source classes and extent rules are satisfied. Overflow large feature lists into the evidence package rather than the report body.

## P1 - export QA

Add export QA checks for unresolved comments, blank required table cells, inconsistent figure/table numbering, captions that do not match policy, missing source references, and sections rendered without required caveats. Block final DOCX/Markdown export when QA fails unless reviewer explicitly overrides with a reason.
