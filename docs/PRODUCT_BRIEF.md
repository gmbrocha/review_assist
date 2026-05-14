# Product Brief

## Problem

Professionals who review proposed project alternatives spend substantial time gathering GIS and contextual information, checking source layers, comparing impacts, and drafting report language.

This work can be repetitive, source-heavy, and difficult to keep consistent across alternatives.

## Solution

The alternatives review assistant should automate first-pass compilation and report drafting. It should help gather relevant source context, run repeatable spatial checks, and produce structured draft findings that a human reviewer can inspect, correct, accept, or reject.

The product direction is "no blank page." The system should eventually attempt to generate a comprehensive pre-review draft package, including findings, draft narrative, maps, comparison tables, contextual implications, and appendices/reference material where useful.

The workflow direction is workspace driven: create/open workspace, add project inputs, generate project context, resolve needed source statuses, populate for review, review queue, and accepted-content export.

## Product Boundary

The tool supports review. It does not make decisions.

It should not:

- Select a preferred alternative.
- Rank alternatives.
- Use hard scoring to imply a decision.
- Present uncertain observations as facts.
- Produce final reports without human review.

It should:

- Accelerate first-pass compilation.
- Preserve source provenance.
- Preserve uncertainty and missing-data flags.
- Support reviewer edits and review statuses.
- Route every generated artifact through the review queue before export.
- Separate deterministic GIS/source checks from AI-assisted narrative synthesis.

## Alternatives Framing

Alternatives may be compared by descriptive impact profiles rather than rankings.

Examples of alternatives include:

- Trails.
- Corridors.
- Sites.
- Alignments.
- Access routes.
- Infrastructure options.

## Finding Concepts

Implemented and future draft findings may include:

- Wetland intersection.
- Wetland adjacency buffer.
- Stream or river crossing.
- Possible bridge requirement.
- Existing disturbed corridor overlap.
- Pristine or low-disturbance area overlap.
- Nearby or overlapping protected species or critical habitat.
- Cultural resource lookup required.
- Visible pond or lake in imagery not present in available wetland data.
- Recent clearing or land disturbance visible in imagery.

The current deterministic baseline implements a subset through template-driven draft findings, comparison tables, vector-only maps, and deterministic draft report sections. Imagery observations, richer map/table findings, LLM-assisted synthesis, and export-ready report compilation remain future work.

## Current Example Projects

Current example project contexts:

- `trails`: five proposed trail alternatives requiring environmental/contextual profiles.
- `conexon_projects`: broadband installation spot review context.
