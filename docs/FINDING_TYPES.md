# Finding Types

This document defines the implemented deterministic finding baseline and likely future finding/implication patterns.

Findings are structured review queue items or inputs to review queue items. They are not final conclusions until reviewed by a human professional.

## Finding Purpose

A finding should connect:

- A project or alternative.
- A source or observation.
- A spatial relationship.
- A reviewable implication.
- Uncertainty and provenance.
- A reviewer status.

The system should transform a spatial relationship into a contextual implication without selecting a preferred alternative.

Findings should not bypass the review queue or flow directly into export.

Example:

- Spatial relationship: Alternative 1A crosses a mapped stream.
- Finding: Stream crossing identified.
- Implication: Culvert, boardwalk, bridge, permitting, or design coordination may be needed depending on final design and field conditions.

## Evidence Classes

Findings should preserve the evidence class:

- Source-backed GIS finding.
- Derived spatial measurement.
- Imagery-observed review item.
- Reviewer-entered finding.
- Agency-consultation finding.
- LLM-assisted draft language tied to structured findings.

## Implemented Baseline Finding Fields

The Phase 6A deterministic finding baseline writes `projects/<project_id>/findings/draft_findings.json`.

Implemented draft finding records include:

- `finding_id`
- `project_id`
- `type`
  - This is the finding type, such as `wetland_or_waterbody_relationship`.
  - The older conceptual name `finding_type` is represented by `type` in the current JSON artifact.
  - Review queue items keep the original `finding_id` in item metadata.
  - Future schema revisions may add aliases if the GUI needs them.
  - Do not treat this as final report wording.
- `resource_category`
- `title`
- `summary`
- `details`
- `implication`
- `evidence_class`
- `source_ids`
- `related_record_ids`
- `assumptions`
- `provenance`
- `uncertainty_flags`
- `review_status`

Draft findings are generated from deterministic templates in `config/finding_templates.json`. They are not final conclusions and must still enter the review queue.

Reviewer notes, edited content, export eligibility, and review history live on review queue items, not inside `draft_findings.json`.

## Implemented Baseline Finding Types

The first deterministic template set covers:

- `wetland_or_waterbody_relationship`
- `stream_or_hydrography_crossing`
- `land_cover_or_disturbance_context`
- `soil_constraint_context`
- `regulated_facility_context`
- `cultural_or_historic_review_required`
- `utility_or_transportation_coordination`
- `community_context`
- `parcel_or_property_review`
- `imagery_review_context`
- `flood_hazard_context`
- `source_unavailable_or_deferred`
- `no_mapped_conflict_identified`

The implemented generator currently creates findings from:

- Source status records with `missing`, `gated`, `stubbed`, `downloadable`, or `needs_review` status.
- Deterministic spatial relationship records for supported source categories.
- Analyzed local sources with zero mapped relationships.

The finding generator does not generate imagery observations, report paragraphs, maps, LLM-assisted synthesis, or final report sections. Comparison tables and vector-only draft maps are generated as separate descriptive workflow artifacts.

## Spatial Relationship Types

Common spatial relationships:

- `intersects`
- `crosses`
- `overlaps`
- `touches`
- `within_buffer`
- `adjacent`
- `nearby`
- `contains`
- `downstream_context`
- `upstream_context`
- `visible_in_imagery`
- `missing_from_source_layer`
- `source_unavailable`
- `requires_manual_lookup`

## Natural and Ecological Findings

Potential finding types:

- Wetland intersection.
- Wetland adjacency buffer.
- Waterbody intersection.
- Stream or river crossing.
- Ditch or drainage crossing.
- Floodplain overlap.
- Floodway overlap.
- Impaired water downstream context.
- Protected species range overlap.
- Critical habitat overlap or nearby context.
- Hydric soil or soil constraint context.
- Land cover or forested area overlap.
- Existing disturbed corridor overlap.
- Low-disturbance or pristine area overlap.

Potential implications:

- Field verification needed.
- Wetland delineation may be needed.
- Clean Water Act permitting coordination likely.
- Stormwater/BMP review needed.
- Floodplain review needed.
- Hydraulic/hydrologic review may be needed.
- Bridge likely required.
- Culvert likely required.
- Boardwalk or avoidance design may be considered.
- Agency coordination likely.

## Cultural and Historic Findings

Potential finding types:

- Public historic resource nearby.
- Known architectural resource context.
- Property older than 50 years identified.
- Archaeological lookup required.
- Restricted cultural data unavailable.
- Restricted cultural data reviewed by qualified reviewer.
- APE may require survey.

Potential implications:

- Additional cultural review needed.
- SHPO/MDAH coordination likely.
- Phase I archaeological survey may be needed.
- Historic architectural survey may be needed.
- Reviewer-supplied restricted data required.
- Do not display sensitive site locations in public outputs.

## Community Resource Findings

Potential finding types:

- Fire/EMS facility nearby.
- School or childcare facility nearby.
- Health care facility nearby.
- Place of worship nearby.
- Park or recreation area nearby.
- Government facility nearby.
- Community access dependency identified.

Potential implications:

- Emergency access concerns.
- Traffic/access coordination needed.
- Construction disruption concerns.
- Pedestrian safety review needed.
- Public engagement focus area.
- Detour/staging review needed.

## Utility and Infrastructure Findings

Potential finding types:

- Public water supply well nearby.
- Water treatment facility nearby.
- Natural gas pipeline crossing.
- Petroleum pipeline crossing.
- Electric transmission crossing.
- Utility corridor overlap.
- Broadband/communications infrastructure context.
- Airport proximity context.

Potential implications:

- Utility coordination likely.
- Safety review needed.
- Service continuity planning needed.
- Design constraint likely.
- Excavation precautions needed.

## Contamination Findings

Potential finding types:

- Hazardous materials site in corridor.
- Hazardous materials site adjacent or nearby.
- Underground storage tank context.
- Cleanup/remediation site context.
- Oil/gas well context.

Potential implications:

- Environmental due diligence needed.
- MDEQ coordination likely.
- Soil/groundwater handling precautions may be needed.
- Construction risk review needed.
- Hazardous materials report appendix reference needed.

## Socioeconomic and Business Findings

Potential finding types:

- Census tract demographic context.
- Lower-income population context.
- Business access concern.
- Economic node proximity.
- Transportation dependency context.

Potential implications:

- Public engagement focus area.
- Access continuity review needed.
- Construction staging concern.
- Multimodal access review needed.
- Avoid final equity conclusion without reviewer assessment.

## Imagery Review Findings

Potential finding types:

- Visible pond not present in reviewed wetland layer.
- Recent clearing visible.
- Newer roadway visible.
- Disturbed area visible.
- Possible structure visible.
- Visible crossing concern.
- Imagery and GIS source discrepancy.

Potential implications:

- Reviewer verification needed.
- Field verification needed.
- Source layer may be stale.
- Add reviewer annotation.
- Consider updating map/context layers.

## No-Finding and Missing-Data Findings

Not every section will have a positive conflict.

Useful draft finding types:

- No mapped conflict identified in reviewed source.
- Source unavailable.
- Source stale or date unknown.
- Restricted source requires manual review.
- Not assessed in this pass.
- Unable to verify with available data.

These should be explicit so report sections are not blank and reviewers can see what was checked.

Missing-data and no-conflict records should still become review queue items so the reviewer can accept, edit, reject, or mark them for verification.

## Prohibited Finding Behavior

Findings should not:

- Select a preferred alternative.
- Rank alternatives.
- Present desktop checks as field verification.
- Treat imagery observations as authoritative facts.
- Hide missing data.
- Invent source-backed evidence from narrative context alone.
