# Sprint 6.5: Regeneration Job

## Status

Completed and archived after Sprint 6.5 implementation. Regenerated outputs are review-only; approval and export integration remain deferred to later Sprint 6 subunits.

## Purpose

Implement deterministic figure regeneration from source data, analysis snapshot, figure recipe, and reviewer style overrides.

## Regeneration Inputs

```text
source data
+ analysis snapshot
+ figure recipe
+ reviewer style overrides
= regenerated figure
```

Inputs should be references to existing canonical artifacts where possible rather than copied raw datasets.

## Required Behavior

When a reviewer saves and regenerates a figure:

1. Save the current style override metadata.
2. Create a new figure render job.
3. Render the figure using frozen analysis/source inputs.
4. Apply style overrides during rendering.
5. Store the regenerated output as a new figure version.
6. Make the regenerated figure available for reviewer inspection, but do not make it export-active until a later approval/export integration subunit.

## Output Formats

Initial support:

- PNG

Preferred if practical:

- SVG

Deferred unless already easy:

- PDF

## Render Job States

Suggested states:

- queued
- running
- succeeded
- failed

The first implementation may run synchronously if the local app architecture does not have background jobs. Even synchronous jobs should be recorded as jobs for auditability.

## Failure Handling

Failed regeneration should:

- preserve the previous current/approved figure version
- record error details in the render job
- expose failure state in the UI
- not mutate source, analysis, recipe, or approved version records
- not leave a partial output as the export target

## Renderer Changes

Apply style overrides at render time only.

Supported override effects:

- hide/show layers
- apply z-index/layer ordering
- apply display names
- apply fill/stroke/point styling
- optionally apply label visibility/field if v1 label support is implemented

Do not change geometry or metrics.

## Tests

Add focused tests for:

- regeneration creates a render job
- successful regeneration creates a new figure version
- style overrides affect rendered style metadata/output path
- hidden layers are omitted from regenerated visual output and version metadata
- source and analysis artifacts remain unchanged
- failed render job preserves previous figure target
- PNG output is stored at a versioned path
- unsupported output formats are rejected or clearly deferred

## Definition Of Done

- Regeneration produces versioned PNG outputs from current source/analysis inputs and style overrides.
- Render jobs are auditable.
- Failure behavior is safe and visible.
- Regeneration does not mutate analytical truth.
