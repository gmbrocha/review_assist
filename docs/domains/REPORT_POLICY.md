# Report Policy

This document explains the machine-readable report policy in `config/report_section_policy.json`.

## Purpose

The policy defines what each report section is allowed to mean before any GPT-assisted interpretation is expanded. It keeps spatial interpretation, figure presentation, evidence patterns, comparison-unit expansion, caveats, prohibited claims, and GPT readiness explicit and reviewable.

The policy is a contract layer. It does not download sources, change query distances, change comparison-unit generation, change analysis geometry, change deliverable counts, or bypass human review.

## Extent Rules

- `direct_project`: evidence may describe mapped relationships within submitted project features, comparison units, or current project-area analysis bounds.
- `screening_buffer`: evidence may describe features within a configured screening buffer; wording must not imply direct impact.
- `nearby_context` / `community_context`: evidence supports vicinity or community context only. It may use "near the project area" or "in the project vicinity"; it must not say direct impact.
- `watershed_context`: evidence supports watershed or subwatershed setting. It must not imply the whole watershed is directly affected. If watershed context is unavailable, the figure/section must remain deferred or stubbed.
- `county_or_regional_context`: evidence supports county, regional, tract, or similar demographic/context summaries. It must not imply project-level impact.
- `manual_reviewer_supplied`: the section depends on reviewer-supplied or restricted material and is not GPT-ready by default.
- `not_spatial`: front matter or workflow narrative that is exempt from spatial interpretation.

Presentation-only render/collar extent is never an interpretation extent. Figure render extent, basemap materialization extent, and legend/collar space may make a map readable, but they must not drive intersections, counts, evidence, tables, or report conclusions.

## Comparison-Unit Expansion

The policy distinguishes:

- `none`: no per-comparison-unit expansion.
- `table_only`: comparison-unit detail should stay in tables unless a later policy changes it.
- `narrative_children`: generate child narrative sections by comparison unit.
- `conditional`: expand only when source-backed evidence and report shape justify it.
- `context_summary_list`: use compact nearby/context summaries rather than per-alternative subsections.
- `manual_only`: reviewer-supplied material controls the section.

Current required narrative children are limited to wetlands/waterbodies comparison-unit details.

## GPT Readiness

GPT readiness is not execution. GPT calls remain disabled unless the reviewer/operator explicitly uses GPT Interpretive Assist.

Readiness values mean:

- `gpt_ready_now`: section policy is considered ready for a source-backed GPT candidate run.
- `gpt_ready_after_extent_metadata_verification`: section is eligible for explicit GPT Interpretive Assist when current artifacts provide source-backed evidence and extent metadata.
- `deterministic_only_for_now`: deterministic text should remain the path.
- `manual_reviewer_supplied_only`: reviewer material is required; GPT should not draft from placeholders.
- `blocked_by_missing_source_acquisition`: source/query work must happen first.
- `blocked_by_policy_ambiguity`: the scope or output shape needs another policy decision before GPT use.

Every GPT-eligible section must have bounded evidence refs, required caveats, and prohibited claims. Manual/reviewer-supplied sections are not GPT-ready by default. GPT Interpretive Assist still filters to source-backed `section_text` items, skips missing-source/P2 stubs by default, caches by evidence/policy/style/model fingerprint, and writes only unaccepted review candidates.

## Current P1 Alignments

- `demographic-characteristics` uses county/regional policy because its table and figure refs are county/regional context.
- `oil-wells` is explicit as `direct_check_with_context_figure`: direct checks and nearby/context figure presentation are distinct, and nearby records must not become direct-impact language.
- `figure-census-tracts` preserves `county_regional` visual semantics even though current rendering may reuse medium/context extent behavior internally.
