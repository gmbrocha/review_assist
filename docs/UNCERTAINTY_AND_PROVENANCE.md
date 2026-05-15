# Uncertainty and Provenance

This document defines the project approach to source traceability, uncertainty, and review status.

## Core Rule

Every generated review item should eventually be traceable to:

- Source.
- Method.
- Geometry assumptions.
- Review status.
- Uncertainty flags.

Generated findings, maps, tables, narrative, caveats, source notes, and reports are pre-review drafts until a human reviewer accepts, edits, rejects, marks them for verification, or marks them unable to verify.

## Source Reliability Tiers

### Authoritative Public GIS Baseline

Examples:

- FEMA flood layers.
- USFWS NWI wetlands.
- USGS hydrography/elevation/transportation.
- NRCS soils.
- MARIS or Mississippi Geospatial Clearinghouse layers.
- Public agency infrastructure data.

Treatment:

- Generally reliable for screening-level baseline review.
- Preserve source date, access date, and metadata.
- Do not treat as field-verified project findings.

### Restricted or Reviewer-Supplied Source

Examples:

- MDAH archaeological/HSMT data.
- Consultant-supplied cultural resource KMZ/GIS exports.
- Agency letters.
- Internal hazardous materials reports.

Treatment:

- Preserve restricted/public distinction.
- Do not automate access without approval.
- Avoid exposing sensitive locations in public outputs.
- Mark findings as based on reviewer-supplied or restricted source.

### Derived Spatial Measurement

Examples:

- Crossing counts.
- Overlap acreage.
- Length through resource.
- Distance to nearest feature.
- Buffer intersection.

Treatment:

- Store method and parameters.
- Store CRS and measurement units.
- Store buffer/corridor assumptions.
- Keep measurements as screening-level unless independently verified.

### Imagery-Observed Review Item

Examples:

- Possible pond visible in imagery.
- Recent clearing.
- New road not reflected in source layer.
- Disturbed corridor.
- Possible structure or access concern.

Treatment:

- Not authoritative by default.
- Requires reviewer validation.
- Preserve imagery source/date if known.
- Use cautious language.

### AI-Assisted Narrative

Examples:

- Draft report paragraph.
- Finding summary.
- Implication phrasing.
- Section synthesis.

Treatment:

- Must be grounded in structured findings.
- Must remain editable.
- Must not create unsupported conclusions.
- Should preserve uncertainty and citations.

## Suggested Provenance Fields

Future source records may include:

- `source_id`
- `source_name`
- `publisher`
- `source_type`
- `public_or_restricted`
- `source_url`
- `local_path`
- `access_date`
- `published_date`
- `metadata_date`
- `license_or_terms`
- `attribution`
- `crs`
- `geometry_type`
- `coverage_area`
- `known_limitations`

Future method records may include:

- `method_id`
- `method_name`
- `operation`
- `input_source_ids`
- `input_geometry_ids`
- `buffer_distance`
- `buffer_units`
- `measurement_crs`
- `output_units`
- `software_library`
- `software_version`
- `run_date`

## Uncertainty Flags

Suggested flags:

- `desktop_screening_only`
- `field_verification_needed`
- `source_date_unknown`
- `source_may_be_stale`
- `source_unavailable`
- `restricted_source_required`
- `geometry_uncertain`
- `buffer_assumption`
- `imagery_observation`
- `imagery_date_unknown`
- `manual_review_required`
- `agency_coordination_required`
- `unable_to_verify`

## Source Status and Uncertainty

The workflow should distinguish source status from finding uncertainty.

Suggested source statuses:

- `provided_locally`
- `downloadable`
- `downloaded`
- `failed`
- `gated`
- `stubbed`
- `missing`
- `optional`
- `needs_review`

Missing, failed, gated, and stubbed source categories should create reviewable placeholders and caveat items rather than causing the workflow to fail by default.

## Confidence Language

Use cautious language for draft outputs.

Preferred:

- "The reviewed source layer indicates..."
- "Desktop review identified..."
- "Available data suggest..."
- "This should be verified by the reviewer."
- "Agency coordination may be needed."
- "Field verification may be required."

Avoid:

- "This is definitively..."
- "This proves..."
- "This area is jurisdictional..."
- "This alternative is best..."
- "This impact is final..."

## Buffer and Geometry Assumptions

Buffer widths should be configurable.

Early trail discussions suggest likely corridor assumptions in the 50 to 100 foot range, but this is not a fixed product rule.

Findings should record:

- Whether the original geometry or a buffered corridor was used.
- Buffer width and units.
- CRS used for buffering.
- Whether the buffer represents trail width, study corridor, review distance, or another assumption.

## MDAH and Cultural Resource Uncertainty

MDAH integration is currently a placeholder.

Public context:

- Historic Resources Inventory can support public historic resource context.
- Rural property locations may be approximate due to privacy concerns.

Restricted context:

- Archaeological records and MDAH GIS/HSMT access may require qualified users, subscriptions, appointments, and approvals.
- Restricted data should not be treated as available public data.

Future workflow assumptions:

- The system may allow a qualified reviewer to upload restricted-source exports.
- The system may represent restricted review as a status without storing sensitive details in public report outputs.
- The system should never attempt to bypass access controls.

## Review Status Relationship

Uncertainty is separate from review status.

Example:

- A finding can be `accepted` and still include `desktop_screening_only`.
- A finding can be `edited` and still require agency coordination.
- A finding can be `unable_to_verify` because a restricted source was unavailable.

Review statuses are defined in `docs/REVIEW_POLICY.md`. Source status categories are defined in `docs/WORKFLOW_MODEL.md`.
