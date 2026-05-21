# Sprint 5.5: Caveat Bundles, Prohibited Claims, And GPT Eligibility

## Status

Active next implementation target after Sprint 5.4 completion.

## Goal

Align caveats, prohibited claim bundles, and GPT eligibility with policy, source status, extent semantics, and render gating.

This is a guardrail subunit. It is not a GPT expansion sprint.

This subunit must consume the caveat bundle, prohibited-claim bundle, GPT eligibility, and GPT style-context rows from `SPRINT_5_POLICY_PACKAGE_RECONCILIATION_LEDGER.md`. Package wording can strengthen guardrails, but it must not expand GPT coverage by default.

## Scope

This subunit may update:

- `config/report_section_policy.json`
- `config/report_generation_prompts.json`
- `config/report_style_context/environmental_constraints_report_style.md`
- `src/review_assist/section_drafting.py`
- `src/review_assist/gpt_interpretive_assist.py`
- GPT/policy documentation and tests

## Required Guardrails

GPT drafting is allowed only when:

- the section policy allows GPT
- the review item is source-backed
- required source status and caveats are present
- extent metadata supports the requested wording
- allowed table/figure/source refs exist in current evidence
- the output remains an unaccepted review candidate

GPT drafting must remain blocked or manual for:

- PEL/custom parent-study relationship
- protected species effect language
- agency consultation interpretation
- archaeology/restricted cultural records
- cultural eligibility/effect determinations
- hazmat risk ranking or Phase I conclusions
- business/economic impact conclusions
- conclusion/next steps commitments
- final impact/no-effect/no-impact language

## Prohibited Claim Families

Block or review-gate:

- final impact or no-impact conclusions
- no effect / species effect determinations
- jurisdictional wetland or water determinations
- cultural eligibility/effect/clearance determinations
- contamination presence/absence or liability conclusions
- permit required/not-required conclusions
- access, mitigation, or construction commitments
- preferred alternative, ranking, scoring, selection, or rejection language

## Non-Goals

- No new GPT sections by default.
- No GPT calls from populate/reset/page load.
- No GPT use for manual/restricted sections.
- No final report generation from GPT output.

## Acceptance Criteria

- All caveat/prohibited-claim/GPT ledger rows are adopted, rejected, or deferred with explicit rationale.
- GPT eligibility is derived from policy plus current evidence, not from section title alone.
- Manual/restricted/stub/presentation-only sections are ineligible.
- Required caveats are enforced before and after generation.
- Prohibited claims are rejected or flagged before replacing deterministic candidates.
- Rejected GPT output preserves deterministic content and records validation issues.

## Required Tests

- GPT dry-run eligibility only lists approved source-backed sections.
- GPT cannot draft manual/restricted/stub sections.
- GPT output with unknown refs is rejected.
- GPT output with final/no-effect/jurisdictional/eligibility/permit/commitment language is rejected.
- GPT output cannot upgrade context-only extent evidence into direct project impact language.
- GPT output cannot cite style context or package/example facts as evidence.

## Documentation Updates

- `docs/domains/LLM_ASSISTED_SYNTHESIS.md`
- `docs/domains/REPORT_POLICY.md`
- `docs/domains/REPORT_ASSEMBLY.md`
- `docs/governance/DEFERRED_WORK.md` for deferred GPT workflow expansion
