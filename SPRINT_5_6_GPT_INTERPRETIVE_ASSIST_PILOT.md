# Sprint 5.6: GPT Interpretive Assist Pilot

## Status

Parked draft for review. Do not implement until policy, source truth, discernment, and manual-completion workflow are accepted.

## Goal

Let GPT draft bounded review candidates after policy and discernment exist.

This is not full automation and not final report generation.

## Pilot Scope

Candidate pilot sections:

- `wetlands-and-waterbodies`
- One wetlands comparison-unit child.
- Floodplains if source-backed.
- Hazardous-materials-sites or contamination-risks.
- One community/context section, likely health-care-facilities.

## Rules

- Opt-in only.
- Max-call limited.
- Cached.
- Style-context guided.
- Policy-bound.
- Evidence-bounded.
- Validation enforced.
- Human review required.
- Deterministic fallback preserved.

## Required Behavior

- Output uses known refs only.
- Output respects extent scope.
- Output includes required limitations.
- Output does not make determinations or overclaims.
- Cache prevents duplicate calls.
- Reviewer can edit, accept, or reject through normal workflow.

## Definition Of Done

- One to five GPT drafts are generated safely.
- Drafts are bounded to approved/source-backed sections.
- Drafts remain review candidates, not final report content.
- Unsafe or unsupported output falls back to deterministic content.
