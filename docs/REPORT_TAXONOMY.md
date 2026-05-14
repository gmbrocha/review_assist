# Report Taxonomy

This document captures the likely report structure for future pre-review draft packages.

It is based on the example environmental constraints report, the client conversation, and current project framing. The example report is a structural reference only. Its facts, project names, figure numbers, and conclusions should not be reused as authoritative content.

## Deliverable Goal

The system should eventually produce a comprehensive pre-review draft package: findings, draft narrative, maps, comparison tables, contextual implications, and appendices/reference material where available.

The goal is no blank page. The reviewer should start from an editable draft and then correct, remove, add, accept, reject, and finalize.

Report taxonomy should inform the workspace source-status resolution step: the selected report profile determines which source categories are required, optional, gated, or stubbed.

## Package-Level Components

A complete package may include:

- Cover/title page.
- Executive summary.
- List of figures.
- List of tables.
- List of attachments.
- Introduction.
- Relationship to broader planning process.
- Study area and alternatives description.
- Methodology.
- Data collection and sources.
- Mapping and analysis procedures.
- Limitations and data gaps.
- Environmental/contextual constraints inventory.
- Alternative comparison tables.
- Conclusion and next steps.
- Attachments and reference material.

## Project Metadata

Project-level metadata may include:

- Project name.
- Study type.
- Client/agency context.
- Project identifier.
- County/state.
- Date.
- Project footprint.
- Alternatives list.
- Prepared-by/reviewed-by fields.
- Draft/review status.

## Study Area and Alternatives

For alternatives projects, the report should describe:

- Overall project footprint or corridor.
- Each alternative name and geometry type.
- Functional purpose of each alternative.
- Key route/corridor/site distinctions.
- Known relationship to existing roads, rail, disturbed corridors, communities, or facilities.

Alternatives should be described as options with impact profiles, not ranked recommendations.

## Methodology

The methodology section should explain:

- Input files used.
- Source layers used.
- Coordinate system and measurement approach.
- Corridor/buffer assumptions.
- Spatial checks performed.
- Map-generation workflow.
- Review status and limitations.
- Distinction between source-backed checks and imagery-observed review items.

## Inventory Categories

### Natural and Ecological Resources

Likely subsections:

- Wetlands and waterbodies.
- Streams, rivers, ditches, and crossings.
- Floodplains and floodways.
- Water quality and impaired waters.
- Protected species and critical habitat.
- Soils, land cover, and disturbance context.

Common outputs:

- Crossings.
- Intersections.
- Buffer/adjoining features.
- Length/acreage summaries.
- Field-verification flags.
- Permit or agency-coordination implications.

### Cultural and Historic Resources

Likely subsections:

- Archaeological resources.
- Historic structures.
- Historic districts.
- Properties older than 50 years.
- Restricted cultural resource lookup status.

Common outputs:

- Public cultural context.
- Restricted-data placeholder status.
- SHPO/MDAH coordination implications.
- Survey required/possible flags.

### Community Resources

Likely subsections:

- Fire/EMS stations.
- Government buildings.
- Schools and childcare.
- Health care facilities.
- Places of worship.
- Parks and recreation.
- Other community anchors.

Common outputs:

- Nearby resource inventory.
- Access and traffic concerns.
- Emergency access concerns.
- Construction disruption concerns.

### Utility and Infrastructure Considerations

Likely subsections:

- Public water supply.
- Water and wastewater utilities.
- Electric transmission/distribution.
- Natural gas and petroleum pipelines.
- Communications/broadband infrastructure.
- Airports or aviation constraints where relevant.

Common outputs:

- Utility crossings.
- Facility proximity.
- Coordination needed.
- Safety and service continuity concerns.

### Contamination Risks

Likely subsections:

- Hazardous materials sites.
- Underground storage tanks.
- Cleanup/remediation sites.
- Oil/gas wells.
- Other regulated sites.

Common outputs:

- Sites in corridor.
- Sites adjacent or nearby.
- Qualitative risk review status.
- Agency coordination needed.

### Socioeconomic and Business Considerations

Likely subsections:

- Demographic characteristics.
- Income and transportation dependency context.
- Local businesses.
- Economic nodes.
- Access-dependent services.

Common outputs:

- Census/geographic summary tables.
- Business access concerns.
- Public engagement implications.
- Construction staging concerns.

## Figure Types

Likely figure types:

- Overall environmental constraints inventory map.
- Panel index map.
- Detailed panel maps.
- Wetlands and waterbodies map.
- Flood zones map.
- Streams and impaired waters map.
- Cultural resources map.
- Community resources map.
- Public water supply map.
- Utility/energy infrastructure map.
- Hazardous materials map.
- Census/demographic context map.
- Imagery review overlay map.

Figures should include draft/pre-review labels, source notes, and clear legends.

## Table Types

Likely table types:

- Alternatives summary.
- Wetland/waterbody counts by alternative.
- Stream crossing counts by alternative.
- Floodplain/floodway summaries.
- Cultural review status by alternative.
- Community resource proximity summary.
- Utility crossing summary.
- Hazardous materials site summary.
- Demographic context by tract or area.
- Findings matrix by resource and alternative.

Tables should be editable and traceable to source findings.

Tables should become review queue items before export.

## Narrative Pattern

A reusable section pattern:

1. Define the resource and why it matters.
2. Identify the source data and method.
3. Summarize what was found.
4. Reference maps/tables.
5. Describe reviewable implications.
6. State uncertainty, limitations, and next steps.

Generated language should avoid unsupported certainty and should remain editable.

Generated narrative sections should become review queue items before export.

Current baseline:

- Deterministic section templates live at `config/report_section_templates.json`.
- Draft section artifacts are written to `projects/<project_id>/drafts/report_sections.json`.
- The implemented baseline creates project overview, methodology/data sources, limitations/missing data, resource sections, comparison summary, maps/figures, and reviewer follow-up sections.
- Generated sections become `report_section` review queue items before any future export.

## Section Complexity

The system should attempt to generate a draft for every relevant section even when evidence is thin.

Possible draft outcomes:

- Source-backed finding available.
- No mapped conflict identified in reviewed sources.
- Source unavailable.
- Restricted source requires manual reviewer input.
- Imagery review item identified.
- Field verification required.
- Section requires reviewer completion.

The goal is a useful draft, not a perfect or final report.
