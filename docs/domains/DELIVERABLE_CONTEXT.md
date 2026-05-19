# Deliverable Context

This file summarizes the expected deliverable pattern inferred from `docs/reference/env_constraints_report_20260511_EXAMPLE_ONLY.docx`.

The example report appears to be unfinished or partially reused from another project. It contains useful structure and report patterns, but its project names, locations, figures, and facts should not be treated as authoritative.

## Deliverable Type

The target deliverable is an Environmental Constraints Report or similar appendix-style report package that supports a broader planning study, such as a Planning and Environmental Linkages (PEL) study.

The report should identify, document, map, and describe environmental, cultural, community, infrastructure, contamination, socioeconomic, and business constraints that may affect project alternatives.

The deliverable supports human review and planning. It should not select a preferred alternative or replace later NEPA, permitting, agency consultation, field verification, or design decisions.

In the application workflow, deliverable content should be compiled from accepted or explicitly included reviewed queue items. Generated findings, narrative, tables, figures, caveats, and source notes should not bypass reviewer approval.

## Expected Package Structure

A full report package may include:

- Cover/title page with project name, study type, appendix title, date, project identifiers, and county/state.
- Executive summary.
- List of figures.
- List of tables.
- List of attachments.
- Introduction.
- Relationship to the broader planning study.
- Study area or alternatives description.
- Methodology.
- Data collection and sources.
- Mapping and analysis procedures.
- Limitations and data gaps.
- Environmental constraints inventory.
- Conclusion and next steps.
- Attachments for maps, hazardous materials reports, agency letters, or other supporting material.

## Inventory Sections

The example report organizes the constraints inventory by resource category.

### Natural and Ecological Resources

Potential subsections:

- Wetlands and waterbodies.
- Floodplains and floodways.
- Water quality.
- Protected species and critical habitat.

Expected content:

- Source and method used to identify resources.
- Spatial relationship to the project area or comparison units.
- Counts, acreage, crossing counts, or other screening-level measures where appropriate.
- Regulatory or design relevance, such as Clean Water Act permitting, floodplain coordination, stormwater management, or BMPs.
- Clear limitations that desktop data is not a jurisdictional or field-verified determination.

### Cultural and Historic Resources

Potential subsections:

- Archaeological sites.
- Historic structures and districts.

Expected content:

- Review of known cultural/historic records.
- Area of Potential Effects discussion if applicable.
- NRHP eligibility or known status where available.
- Need for Phase I survey, architectural survey, SHPO coordination, or other review if ROW acquisition, structural modification, or ground disturbance is expected.
- Treatment of restricted or gated sources as reviewer-supplied context, not public automated data.

### Community Resources

Potential subsections:

- Fire/EMS stations.
- Government buildings.
- Education facilities.
- Health care facilities.
- Places of worship.
- Parks and recreation areas.

Expected content:

- Identification of resources within or near the project area or relevant comparison units.
- Access, safety, traffic, construction disruption, emergency response, and public service implications.
- Notes on facilities that are outside direct project limits but may rely on affected routes.

### Utility and Infrastructure Considerations

Potential subsections:

- Public water supply.
- Utility infrastructure.
- Energy infrastructure.
- Airports.

Expected content:

- Public water supply wells or treatment facilities.
- Natural gas, petroleum, water, power, and transmission infrastructure.
- Required coordination with owners/operators.
- Safety and service continuity considerations during design and construction.

### Contamination Risks

Potential subsections:

- Hazardous materials sites.
- Oil wells.

Expected content:

- Summary of federal/state database review or separate hazardous materials report.
- Count of sites within, adjacent to, or near the relevant project area or disturbance area.
- Qualitative risk grouping such as moderate-risk or low-risk when supported by source review.
- Coordination needs with environmental agencies before excavation or construction.

### Socioeconomic and Business Considerations

Potential subsections:

- Demographic characteristics.
- Local businesses and economic nodes.

Expected content:

- Census tract or community-level demographic context.
- Income and race/ethnicity tables where relevant to planning and outreach.
- Business access, construction staging, and economic disruption considerations.
- Framing that supports engagement and design awareness rather than making final equity or business-impact conclusions.

## Alternative-Specific Treatment

When the project contains alternatives, the report may use resource-by-resource subsections or tables to compare alternatives descriptively.

Useful alternative-level measures may include:

- Stream or drainage crossing counts.
- Wetland or waterbody intersections.
- Floodplain/floodway acreage or crossings.
- Length through a resource layer.
- Acres within a relevant buffer or project area.
- Nearby community resources.
- Utility crossings.
- Known hazardous materials sites near disturbance areas.
- Overlap with existing disturbed corridors.
- Areas where new disturbance may be more likely.

These measures should support descriptive impact profiles, not ranking or preferred-alternative selection.

## Figure and Map Expectations

The example report includes many map figures and an attachment dedicated to project maps.

Potential map outputs:

- Overall environmental constraints inventory map.
- Panel index map.
- Detailed panel maps by project feature, corridor section, site cluster, or other useful project unit.
- Resource-specific maps for wetlands/waterbodies, FEMA flood zones, streams and impaired waters, cultural resources, community facilities, public water supply wells, energy infrastructure, hazardous materials sites, and census tracts.

Maps should be referenced directly in narrative sections and tables. Generated maps should preserve source names, dates when available, legends, scale/context, and whether the map is a draft/pre-review product.

## Table Expectations

The example report includes tables for resource summaries and demographic context.

Potential tables:

- Wetland/waterbody descriptions or counts by alternative.
- FEMA flood zone summaries by alternative.
- Census income demographics by tract.
- Census demographic composition by tract.
- Hazardous materials site summaries.
- Community resource inventories.
- Utility crossing summaries.

Tables should remain editable and traceable to source data.

## Common Writing Pattern

Most resource sections follow a repeatable pattern:

1. Define the resource and why it matters.
2. Identify the source data or agency coordination used.
3. Describe what was found in or near the study area or alternatives.
4. Reference a map, figure, or table.
5. Explain planning, design, permitting, coordination, or construction implications.
6. State limitations, uncertainty, and need for field verification or agency confirmation where relevant.

This pattern is more important than copying exact language from the example report.

## Limitations Language

Future generated deliverables should preserve limitations clearly:

- Desktop data is screening-level.
- NWI wetlands do not define jurisdictional boundaries.
- Field delineations may be required.
- Public GIS data may be stale, incomplete, or spatially imprecise.
- Aerial imagery observations are review items, not authoritative facts.
- Restricted cultural resource data may require manual reviewer input.
- Agency consultation may supersede automated findings.

## Attachment Pattern

The example report ends with attachment placeholders:

- Attachment A: Project maps.
- Attachment B: Hazardous materials report.
- Attachment C: Agency consultation letters.

Future deliverable generation should treat attachments as part of the package, not as final facts generated by the system. Attachments may be manually provided, generated from source data, or assembled after reviewer approval.

## Product Implications

The system should eventually support:

- Project-specific report profiles.
- Resource-by-resource finding summaries.
- Alternative-specific descriptive comparison tables.
- Draft narrative sections tied to findings.
- Map and figure inventory tracking.
- Source provenance and method notes.
- Reviewer status, edits, and uncertainty flags.
- Editable report export.
- Accepted-content-only export compilation.

The system should avoid:

- Calling reports final.
- Selecting or recommending a preferred alternative.
- Hiding uncertainty behind polished prose.
- Treating example report facts as reusable facts for other projects.
- Mixing deterministic GIS checks with AI-generated narrative without traceability.
