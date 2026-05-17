# Deliverable Outline From Example Report

Source document: `env_constraints_report_20260511_EXAMPLE_ONLY.docx`

Purpose: capture the example report structure as a working outline for future static deliverable configuration. This file should guide section, table, figure, and attachment targets. It should not be treated as project-specific factual content for new reports.

Extraction notes:

- The DOCX contains 308 paragraphs, 4 Word tables, 13 embedded inline images, and 4 document sections.
- Heading styles do not consistently include visible section numbers in the extracted text. Numbering below is inferred from the document hierarchy and the known body structure.
- The list of figures and body captions have numbering/order inconsistencies. Those are captured under `Figure Inventory` and should be cleaned up in the generated template.

## Formatting Target From Example Report

Use the example report as the visual formatting target for generated DOCX exports. The report content should change by project, but the document styling can closely follow the client example.

Page setup:

- Page size: Letter, 8.5 in x 11 in.
- Margins: 1.0 in top, bottom, left, and right.
- Header distance: 0.5 in.
- Footer distance: 0.5 in.
- Sections start on new pages.
- Usable content width is approximately 6.5 in.

Default document text:

- Document default font size: 12 pt.
- Default paragraph spacing after: 8 pt.
- Default automatic line spacing: approximately 1.16.
- Main body paragraph style used in the document is named `Paragraph`.
- Main body paragraph font: Calibri.

Cover/title formatting:

- Title style:
  - Font: Calibri Light.
  - Size: 20 pt.
  - Alignment: right.
  - Space after: 0 pt.
- Subtitle style:
  - Font: Calibri Light.
  - Size: 16 pt.
  - Bold: yes.
  - Italic: yes.
  - Alignment: right.
  - Space after: 0 pt.
  - Example subtitle run color: `#0F4761`.
- Project identifier and county/location lines use Calibri Light in normal paragraphs.

Heading styles:

| Level | Word style | Font | Size | Color | Other style details |
| --- | --- | --- | ---: | --- | --- |
| Main sections | Heading 1 | Lato | 20 pt | `#0F4761` | Space before 18 pt; space after 4 pt; keep with next; numbered outline level 1 |
| Subsections | Heading 2 | Lato | 14 pt | `#0F4761` | Space before 20 pt; space after 4 pt; keep with next; numbered outline level 2 |
| Resource subsections | Heading 3 | Lato | Inherits default size | `#0F4761` | Italic; space before 8 pt; space after 4 pt; keep with next; numbered outline level 3 |
| Alternative/detail subsections | Heading 4 | Inherits default font | Inherits default size | `#4C94D8` | Italic; space before 4 pt; space after 2 pt; keep with next; numbered outline level 4 |

List headings:

- `LIST OF FIGURES`, `LIST OF TABLES`, and `LIST OF ATTACHMENTS` appear as normal paragraphs with Lato bold runs.
- List entries use the `table of figures` style:
  - Font: Calibri.
  - Space after: 2 pt.

Caption formatting:

- Caption style font: Calibri Light.
- Caption size: 11 pt.
- Caption color: `#0E2841`.
- Italic: yes.
- Alignment: centered.
- Line spacing: single.
- Space after: 10 pt.

Attachment title formatting:

- Style name: `Attachment Title`.
- Based on Subtitle.
- Alignment: centered.
- Color: `#0F4761`.

Table formatting:

- All extracted Word tables use `Table Grid`.
- Table cell paragraphs use the `Paragraph` style.
- Header rows are not visibly stored as a distinct custom style in the extracted table samples, so generated tables should use `Table Grid` first and then apply any needed header emphasis consistently.
- Table captions should use the same caption style as figure captions.

Figure/map formatting:

- The DOCX contains 13 embedded inline images.
- Main map figures are approximately 6.5 in wide by about 4.09 to 4.13 in high.
- Generated report maps should target 6.5 in width to fill the content area between 1 in margins.
- Smaller front/cover graphics in the example measured approximately 2.292 in x 0.855 in and 3.042 in x 0.492 in.

Footer formatting/content:

- Example body footer content includes project name/page number and report title.
- Extracted footer text examples:
  - `Tanglefoot Trail ExtensionPage 1`
  - `Environmental Constraints Report`
  - `Tanglefoot Trail ExtensionPage i`
  - `North Hills Street Improvements`
- Generated footers should use the current project name and report title, with page numbering handled by Word fields where practical.

Implementation notes:

- The exporter should reproduce styles rather than manually styling each paragraph where possible.
- Figure and table numbering should be assigned from the generated section matrix, not copied from the example.
- If Lato is unavailable on the target machine, the DOCX can still reference it; Word will substitute locally, but the intended style should remain Lato.

## Front Matter

Cover/title page:

- Planning and Environmental Linkage Study for [project name]
- Project route/location line
- Appendix A: Environmental Constraints Report
- Report date
- Project number or identifier
- County/counties and state

Lists:

- List of figures
- List of tables
- List of attachments

List of figures items:

- Wetlands and Waterbodies in and near the Study Corridor
- FEMA Flood Zones in and near the Study Corridor
- Streams and 303(d) Impaired Waters within the Subwatersheds of the Study Corridor
- Cultural Resources Sites in or near the Study Corridor
- Fire Stations in or near the Study Corridor
- Government Offices near the Study Corridor
- Schools and Childcare Facilities in or near the Study Corridor
- Health Care Facilities near the Study Corridor
- Places of Worship in or near the Study Corridor
- Public Water Supply Wells near the Study Corridor
- Energy Infrastructure near the Study Corridor
- Hazardous Waste Sites near the Study Corridor
- Census Tracts along the Study Corridor

List of tables items:

- Descriptions of Wetlands and Waterbodies Present within the Study Corridor
- FEMA Flood Zones within the Study Corridor
- Income Demographics of Census Tracts along the Study Corridor
- Demographic Composition of Census Tracts along the Study Corridor

Attachments list:

- Attachment A: Environmental Constraints Maps
- Attachment B: Hazardous Materials Report
- Attachment C: Agency Consultation Letters

Implementation notes:

- Generate title, location/counties, report title, date, and project identifiers from project metadata and early project-area processing.
- Generate figure/table/attachment lists from the final section matrix after figure and table numbering is assigned.

## Executive Summary

Section type: front-summary narrative.

Observed content blocks:

- Project/report purpose and study context.
- Natural/ecological resource summary.
- Cultural/historic resource summary.
- Community resource/access summary.
- Demographic/community context summary.
- Utility/infrastructure summary.
- Hazardous materials/contamination summary.
- Closing summary of how findings support later project phases.

Tables: none.

Figures: none.

Implementation notes:

- Generate only after section-level findings, tables, figures, source gaps, and caveats exist.
- Keep this concise and objective.
- Do not rank, recommend, or select alternatives.

## 1. Introduction

Section type: body narrative.

Tables: none.

Figures: none directly in the extracted text.

### 1.1 Relationship with the PEL Study

Purpose:

- Explain how the environmental constraints report supports the broader planning study.
- Describe the screening-level role of the report.

Tables: none.

Figures: none.

### 1.2 Study Area

Purpose:

- Describe where the project is located.
- Identify counties, termini, corridor/study area context, and the alternatives or project features considered.

Tables: none.

Figures: likely project overview/study area figure, although no distinct body caption was extracted for a project overview map.

Implementation notes:

- Populate county names from the first processing step.
- Reference project bbox, selected basemap, and KMZ-derived alternatives.

## 2. Methodology

Section type: body narrative.

Tables: none in the example.

Figures: none in the example.

### 2.1 Data Collection and Sources

Purpose:

- Describe source categories used for the environmental constraints review.
- Summarize public GIS, agency data, aerial imagery, and reviewer/manual sources.

Tables: none in the example.

Figures: none.

Implementation notes:

- This can cite a source inventory internally, but the example does not place a source status table here.

### 2.2 Mapping and Analysis Procedures

Purpose:

- Describe mapping, overlay, buffer/corridor, and screening procedures.
- Explain that resource-specific datasets were layered onto the study corridor or alternatives.

Tables: none.

Figures: none.

Implementation notes:

- Must document the configured buffer, CRS, and whether raw lines or buffered corridors were used for measurements.

### 2.3 Limitations and Data Gaps

Purpose:

- Describe screening-level limitations, incomplete/manual sources, source currency concerns, and field-verification needs.

Tables: none in the example.

Figures: none.

Implementation notes:

- Keep caveats concise.
- Do not produce pages of placeholder text.

## 3. Environmental Constraints Inventory

Section type: body parent section.

Purpose:

- Introduce the resource-by-resource inventory.
- Explain that constraints are arranged by natural/ecological, cultural/historic, community, utility/infrastructure, contamination, and socioeconomic categories.

Tables: none directly at this parent level.

Figures: overall environmental constraints inventory map is referenced in prose, but a distinct body caption was not extracted.

Implementation notes:

- This section should introduce the comparison units and direct readers to the section-specific tables and figures.

## 3.1 Natural and Ecological Resources

Section type: body parent subsection.

Tables: see resource subsections.

Figures: see resource subsections.

### 3.1.1 Wetlands and Waterbodies

Purpose:

- Summarize wetlands, mapped waterbodies, and related Clean Water Act screening considerations.
- Present alternative-specific subsections.

Subsections:

- 3.1.1.1 Alternative 1A
- 3.1.1.2 Alternative 1B
- 3.1.1.3 Alternative 2
- 3.1.1.4 Alternative 3
- 3.1.1.5 Alternative 4

Figures:

- Figure target: Wetlands and Waterbodies in and near the Study Corridor.
- Listed in the front matter as Figure 1.
- No body caption was extracted near the 3.1.1 text, but the figure appears in the list of figures.

Tables:

- Table 1: Descriptions of Wetlands and Waterbodies Present within the Study Corridor.

Table 1 schema:

| Column | Notes for generated table |
| --- | --- |
| Alternative | One row per comparison unit. |
| Stream Crossings | Count stream/hydrography crossing hits by alternative. |
| Freshwater Emergent Wetland | Aggregate NWI/wetland hits mapped to this class. |
| Freshwater Forested/Shrub Wetland | Aggregate NWI/wetland hits mapped to this class. |
| Freshwater Pond | Aggregate NWI/wetland hits mapped to this class. |

Observed example row labels:

- 1A
- 1B
- 2
- 3
- 4

Implementation notes:

- Table should be one row per alternative/comparison unit.
- Stream crossing values should come from hydrography crossing analysis.
- Wetland class values should come from NWI/wetland attributes mapped to canonical report categories.
- Raw wetland/waterbody features remain evidence records, not report rows.

### 3.1.2 Floodplains and Floodways

Purpose:

- Summarize FEMA flood zones, floodways, and floodplain screening context.

Figures:

- Figure target: FEMA Flood Zones in and near the Study Corridor.
- Listed in the front matter as Figure 2.

Tables:

- Table 2: FEMA Flood Zones within each Trail Alignment.
- The generated version should rename `Trail Alignment` to `Alternative` for project-type neutrality.

Table 2 schema:

| Column | Notes for generated table |
| --- | --- |
| Alternative | One or more rows per comparison unit, depending on display rule for multiple flood zones. |
| Flood Zone Classification | FEMA/NFHL flood zone classification. |
| Estimated Acreage | Acreage of the buffered corridor intersecting that classification. |

Observed example row labels:

- Alternative 1A
- Alternative 1B
- Alternative 2
- Alternative 3
- Alternative 4

Implementation notes:

- Store acreage by alternative and by flood zone classification.
- Use buffered corridor geometry for line alternatives.
- Current default buffer is 100 feet unless overridden.
- Store buffer distance, units, CRS, and measurement method in provenance.

### 3.1.3 Water Quality

Purpose:

- Summarize streams, subwatersheds, impaired waters, 303(d) context, and downstream water quality considerations.

Figures:

- Body caption: Figure 4. Streams and 303(d) Impaired Waters within the Subwatersheds of the Study Corridor.
- Front list labels this as Figure 3.

Tables: none in the example.

Implementation notes:

- Use hydrography and impaired-water/source water quality sources when available.
- Generated template should resolve the figure-number mismatch.

### 3.1.4 Protected Species and Critical Habitat

Purpose:

- Summarize federal/state species screening, critical habitat, IPaC, and agency coordination status.

Figures: none extracted in body.

Tables: none.

Implementation notes:

- Separate GIS-checkable critical habitat from manual IPaC and state heritage review.
- Manual agency consultation documents should become concise caveats or attachment references.

## 3.2 Cultural and Historic Resources

Purpose:

- Summarize public cultural/historic context and restricted archaeology/manual review status.

Figures:

- Body caption: Figure 5. Cultural Resources Sites in or near the Study Corridor.
- Front list labels cultural resources as Figure 4.

Tables: none.

Implementation notes:

- Generated template should resolve the figure-number mismatch.
- Restricted archaeological records must not be exposed unless explicitly approved.

### 3.2.1 Archaeological Sites

Purpose:

- Describe archaeological APE context and recorded archaeological resource review.

Tables: none.

Figures: uses the cultural resources figure.

### 3.2.2 Historic Structures and Districts

Purpose:

- Describe historic structures, districts, eligibility/status, and coordination implications.

Tables: none.

Figures: uses the cultural resources figure.

## 3.3 Community Resources

Purpose:

- Summarize community resources, emergency access, civic resources, schools, healthcare, places of worship, parks, and recreation areas.

Tables: none.

Figures: see subsections.

### 3.3.1 Fire/EMS Stations

Figures:

- Body caption: Figure 6. Fire Stations in or near the Study Corridor.
- Front list also labels fire stations as Figure 6.

Tables: none.

### 3.3.2 Government Buildings

Figures:

- Body caption: Figure 7. Government Offices near the Study Corridor.
- Front list labels government offices as Figure 5.

Tables: none.

Implementation notes:

- Generated template should resolve the figure-number mismatch.

### 3.3.3 Education Facilities

Figures:

- Body caption: Figure 8. Schools and Childcare Facilities in or near the Study Corridor.
- Front list labels schools and childcare as Figure 7.

Tables: none.

Implementation notes:

- Generated template should resolve the figure-number mismatch.

### 3.3.4 Health Care Facilities

Figures:

- Body caption: Figure 9. Health Care Facilities near the Study Corridor.
- Front list also labels health care facilities as Figure 9.

Tables: none.

### 3.3.5 Places of Worship

Figures:

- Body caption: Figure 10. Places of Worship in or near the Study Corridor.
- Front list labels places of worship as Figure 8.

Tables: none.

Implementation notes:

- Generated template should resolve the figure-number mismatch.

### 3.3.6 Parks and Recreation Areas

Figures: none extracted in body.

Tables: none.

Implementation notes:

- Generate a figure only when parks/recreation source data is available and report-relevant.

## 3.4 Utility and Infrastructure Considerations

Purpose:

- Summarize public water supply, utilities, energy infrastructure, and aviation constraints.

Tables: none.

Figures: see subsections.

### 3.4.1 Public Water Supply

Figures:

- Body caption: Figure 11. Public Water Supply Wells near the Study Corridor.
- Front list labels public water supply wells as Figure 10.

Tables: none.

Implementation notes:

- Generated template should resolve the figure-number mismatch.

### 3.4.2 Utility Infrastructure

Figures:

- Body text references utility infrastructure assets.
- Body caption near this subsection: Figure 12. Energy Infrastructure near the Study Corridor.
- Front list labels energy infrastructure as Figure 11.

Tables: none.

Implementation notes:

- The example appears to combine or closely place utility and energy infrastructure visuals.
- Generated matrix should define whether utility infrastructure and energy infrastructure are separate figure targets.

### 3.4.3 Energy Infrastructure

Figures:

- Figure target: Energy Infrastructure near the Study Corridor.
- Body caption: Figure 12.
- Front list: Figure 11.

Tables: none.

Implementation notes:

- Generated template should resolve figure numbering and place the caption under the correct subsection.

### 3.4.4 Airports

Figures: none extracted in body.

Tables: none.

Implementation notes:

- Generate only when airport/aviation constraints are present or relevant.

## 3.5 Contamination Risks

Purpose:

- Summarize hazardous materials, regulated facility, cleanup, UST, contamination, and oil/gas well context.

Tables: none in the main report.

Figures: see subsections.

### 3.5.1 Hazardous Materials Sites

Figures:

- Body caption: Figure 13. Hazardous Waste Sites near the Study Corridor.
- Front list labels hazardous waste sites as Figure 12.

Tables: none in main report.

Implementation notes:

- Detailed hazardous materials content may be placed in Attachment B.
- Generated template should resolve the figure-number mismatch.

### 3.5.2 Oil Wells

Figures: none extracted in body.

Tables: none.

Implementation notes:

- Generate only when oil/gas well source data is available and relevant.

## 3.6 Socioeconomic and Business Considerations

Purpose:

- Summarize demographic characteristics and local business/economic context.

Figures:

- Body caption: Figure 14. Census Tracts along the Study Corridor.
- Front list labels census tracts as Figure 13.

Tables:

- Table 3: Income Demographics of Census Tracts along the Study Corridor.
- Table 4: Demographic Composition of Census Tracts along the Study Corridor.

Implementation notes:

- Generated template should resolve the figure-number mismatch.

### 3.6.1 Demographic Characteristics

Figures:

- Census tracts figure.

Tables:

- Table 3: Income Demographics of Census Tracts along the Study Corridor.
- Table 4: Demographic Composition of Census Tracts along the Study Corridor.

Table 3 schema:

| Column | Notes for generated table |
| --- | --- |
| Census Tract | Census geography intersecting or near the study corridor. |
| Population Below the Poverty Line | Percent or count, depending on selected Census/ACS variable. |

Observed example comparison rows:

- Census tracts
- Citywide value
- County value

Table 4 schema:

| Column | Notes for generated table |
| --- | --- |
| Geography | The first column is blank in the example but functions as census tract/geography label. |
| Black or African American | Demographic percentage. |
| Asian | Demographic percentage. |
| White | Demographic percentage. |

Observed example comparison rows:

- Census tracts
- Citywide value
- County value

Implementation notes:

- Census table generation needs a source-specific schema and clear selected variables.
- Keep demographic context descriptive and avoid final equity conclusions.

### 3.6.2 Local Businesses and Economic Nodes

Figures: none extracted in body.

Tables: none.

Implementation notes:

- Generate only when business/economic node data is available and relevant.

## 4. Conclusion and Next Steps

Purpose:

- Summarize objective constraint themes.
- Identify coordination, permitting, agency consultation, design, and field-verification needs.
- Close the report without recommending or selecting an alternative.

Tables: none.

Figures: none.

Implementation notes:

- Generate after all section-level summaries are complete.
- Do not rank, score, reject, or recommend alternatives.

## Attachments

### Attachment A: Project Maps

Observed attachment title:

- `ATTACHMENT A: PROJECT MAPS`

Purpose:

- Hold environmental constraints maps or map package outputs.

Implementation notes:

- Should include accepted/selected maps only.
- Do not dump every generated map into the attachment by default.

### Attachment B: Hazardous Materials Report

Observed attachment title:

- `ATTACHMENT B: HAZARDOUS MATERIALS REPORT`

Purpose:

- Hold hazardous materials support report or reviewer-provided due diligence material.

Implementation notes:

- Main report should summarize contamination risks.
- Detailed hazardous materials backup can live here when available.

### Attachment C: Agency Consultation Letters

Observed attachment title:

- `ATTACHMENT C: AGENCY CONSULTATION LETTERS`

Purpose:

- Hold USFWS, SHPO/MDAH, MDWFP, FEMA, MDEQ, local agency, or other consultation records.

Implementation notes:

- Manual/reviewer-supplied documents should be referenced without inventing unavailable agency outcomes.

## Figure Inventory

Front-matter list of figures:

| Listed figure | Listed title |
| --- | --- |
| Figure 1 | Wetlands and Waterbodies in and near the Study Corridor |
| Figure 2 | FEMA Flood Zones in and near the Study Corridor |
| Figure 3 | Streams and 303(d) Impaired Waters within the Subwatersheds of the Study Corridor |
| Figure 4 | Cultural Resources Sites in or near the Study Corridor |
| Figure 6 | Fire Stations in or near the Study Corridor |
| Figure 5 | Government Offices near the Study Corridor |
| Figure 7 | Schools and Childcare Facilities in or near the Study Corridor |
| Figure 9 | Health Care Facilities near the Study Corridor |
| Figure 8 | Places of Worship in or near the Study Corridor |
| Figure 10 | Public Water Supply Wells near the Study Corridor |
| Figure 11 | Energy Infrastructure near the Study Corridor |
| Figure 12 | Hazardous Waste Sites near the Study Corridor |
| Figure 13 | Census Tracts along the Study Corridor |

Body captions extracted:

| Body caption | Section context |
| --- | --- |
| Figure 4. Streams and 303(d) Impaired Waters within the Subwatersheds of the Study Corridor | 3.1.3 Water Quality |
| Figure 5. Cultural Resources Sites in or near the Study Corridor | 3.2 Cultural and Historic Resources |
| Figure 6. Fire Stations in or near the Study Corridor | 3.3.1 Fire/EMS Stations |
| Figure 7. Government Offices near the Study Corridor | 3.3.2 Government Buildings |
| Figure 8. Schools and Childcare Facilities in or near the Study Corridor | 3.3.3 Education Facilities |
| Figure 9. Health Care Facilities near the Study Corridor | 3.3.4 Health Care Facilities |
| Figure 10. Places of Worship in or near the Study Corridor | 3.3.5 Places of Worship |
| Figure 11. Public Water Supply Wells near the Study Corridor | 3.4.1 Public Water Supply |
| Figure 12. Energy Infrastructure near the Study Corridor | 3.4.2/3.4.3 Utility/Energy Infrastructure |
| Figure 13. Hazardous Waste Sites near the Study Corridor | 3.5.1 Hazardous Materials Sites |
| Figure 14. Census Tracts along the Study Corridor | 3.6.1 Demographic Characteristics |

Figure numbering notes:

- The front list includes 13 figures, while body captions extracted as captions include Figure 4 through Figure 14.
- The DOCX has 13 inline images.
- The generated system should assign figure numbers from a single ordered matrix rather than relying on copied example numbering.

## Table Inventory

Front-matter list of tables:

| Listed table | Listed title |
| --- | --- |
| Table 1 | Descriptions of Wetlands and Waterbodies Present within the Study Corridor |
| Table 2 | FEMA Flood Zones within the Study Corridor |
| Table 3 | Income Demographics of Census Tracts along the Study Corridor |
| Table 4 | Demographic Composition of Census Tracts along the Study Corridor |

Extracted Word tables:

| Table | Rows | Columns | Section context |
| --- | ---: | ---: | --- |
| Table 1 | 6 | 5 | 3.1.1 Wetlands and Waterbodies |
| Table 2 | 6 | 3 | 3.1.2 Floodplains and Floodways |
| Table 3 | 8 | 2 | 3.6.1 Demographic Characteristics |
| Table 4 | 8 | 4 | 3.6.1 Demographic Characteristics |

Implementation notes:

- Generated reports should build these tables from explicit table definitions in the deliverable matrix.
- Standard export should include only section-approved tables.
- Raw GIS relationship tables should remain evidence artifacts unless an evidence appendix is explicitly requested.
