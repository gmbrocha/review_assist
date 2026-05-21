# Sprint 5.4: Report Inclusion And Discernment Pass

## Status

Parked draft for review. Do not implement until Sprint 5.2 and Sprint 5.3 are accepted.

## Goal

After broad screening, the system should recommend what should happen with each topic.

This is the product heart of Sprint 5: Review Assist should distinguish report body content from table-only, attachment-only, omitted, blocked, and reviewer-decision content.

## Recommendation Set

For each possible report topic, the app should recommend one of:

- Include in report body.
- Include as table/figure only.
- Include in attachment/status.
- Omit from report but keep in audit trail.
- Needs reviewer decision.
- Blocked by missing/manual/restricted source.
- Custom/project-specific section required.

Every recommendation must include a reason.

## Examples To Preserve

- Wetlands: include in body when direct source-backed evidence exists.
- Health care facilities: nearby context found, reviewer decision or context summary.
- Public water supply wells: include if found within relevant context; otherwise status-only or omit.
- Cultural resources: public context available, restricted MDAH source pending, reviewer decision required.
- PEL relationship: custom/project metadata required, do not include by default.

## Guardrails

- Nothing is auto-final.
- Human can confirm or override.
- Discernment should not bloat the report.
- Context-only evidence must not be presented as direct impact.
- Missing/manual/restricted sources must stay visible as review state, not hidden.

## Definition Of Done

- The app produces a report inclusion recommendation set.
- Each recommendation has a reason.
- Reviewer confirmation/override is supported.
- Report size remains controlled.
- Audit trail preserves omitted and deferred topics.
