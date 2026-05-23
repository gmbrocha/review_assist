# Review Assist Environmental Constraints Extraction Package

Prepared: 2026-05-21

## Source posture
This package extracts reusable design intelligence from the uploaded example Environmental Constraints Report and the Review Assist framing notes. The example report is treated as a working draft and target-shape reference, not a finished template or source of reusable project facts. Project-specific, trail/corridor-specific, PEL-specific, incomplete, and restricted/manual material are explicitly separated from generalizable policy.

## Executive implementation stance
Review Assist should become a configurable environmental constraints report engine where every section knows its source requirements, evidence grain, spatial extent, visual extent, figure/table support, caveat bundle, prohibited claims, comparison-unit behavior, drafting mode, and review gate. The first implementation move should be a canonical machine-readable policy object that blocks sections from rendering unless their policy triggers and source conditions are satisfied.

## Contents
1. Report Structure Inventory
2. Section Policy Table
3. Source Needs by Section
4. Figure Needs
5. Table Needs
6. Alternative / Comparison-Unit Logic
7. Spatial Scope / Extent Semantics
8. Wording and Caveat Library
9. Manual / Reviewer-Supplied Materials
10. Generalizable vs Project-Specific
11. Diff Against Current Review Assist App
12. Recommended Implementation Moves
13. Suggested Machine-Readable Policy Shape
14. GPT Style Context Recommendations
15. Codex Prompt Starters

## 1. Report Structure Inventory
| Section | Purpose | Classification | Output shape | Backing type | Default? | Trigger / omit logic |
| --- | --- | --- | --- | --- | --- | --- |
| Cover / title | Package identity | Generalizable shape; project-specific content | Cover metadata | Project metadata | Yes | Always; generated from project metadata |
| Executive Summary | High-level constraints summary | Generalizable shape; generated after review | Compact narrative | Reviewed evidence + reviewer approval | Yes | Render only after sections/tables reviewed |
| TOC / lists | Document navigation | Generalizable | Auto-generated/static lists | Presentation only | Yes | Generate when corresponding figures/tables/attachments exist |
| 1 Introduction | Introduce review purpose and project context | Generalizable, but narrative is custom | Paragraph | Reviewer/project metadata | Yes | Always, but keep neutral and compact |
| 1.1 Relationship with PEL Study | Tie report to a PEL process | PEL-specific / conditional / manual | Manual narrative | Reviewer-written | No | Only if parent_study.type is PEL or reviewer adds it |
| 1.2 Study Area / Project Area | Describe project geography and comparison units | Generalizable concept; trail-specific sample execution | Paragraph + optional map/list | Project geometry + metadata | Yes | Use neutral project area / comparison units language |
| 2 Methodology | Explain source, mapping, and limits | Generalizable | Short narrative + source refs | Source manifest + app config | Yes | Always; reflect actual app workflow |
| 2.1 Data Collection and Sources | Name data types and provenance | Generalizable | Paragraph + source list/ref | Source manifest | Yes | Always; generated from sources actually used |
| 2.2 Mapping and Analysis Procedures | Explain overlays, basemaps, panels | Generalizable; tool names are app-specific | Paragraph/bullets | Figure policy + app config | Yes | Do not copy ArcGIS version unless true |
| 2.3 Limitations and Data Gaps | Desktop-review caveats | Generalizable | Caveat paragraph/list | Caveat library + source status | Yes | Always; insert source-specific caveats |
| 3 Environmental Constraints Inventory | Parent inventory section | Generalizable | Intro + attachment ref | Section matrix | Yes | Include if any modules are enabled |
| 3.1 Natural and Ecological Resources | Parent natural resources category | Generalizable family | Short intro | Source-backed | Conditional | Include when natural modules are enabled |
| 3.1.1 Wetlands and Waterbodies | NWI wetlands, streams, ponds, crossings | Generalizable module; per-alt narrative conditional | Paragraph + table + figure | Source-backed | Conditional/default if sources exist | Trigger on NWI/hydrography sources |
| 3.1.1.x Alternative subsections | Route-specific wetlands narratives | Trail/corridor-specific + incomplete | Narrative children | Source-backed + design assumptions | No | Only if reviewer enables narrative comparison |
| 3.1.2 Floodplains and Floodways | FEMA flood zones/floodways | Generalizable module | Paragraph + table + figure | Source-backed | Conditional/default if source exists | Trigger on FEMA/NFHL/DFIRM source |
| 3.1.3 Water Quality | HUC, 303(d), TMDL, downstream context | Conditional/generalizable | Paragraph + watershed map | Source-backed | Conditional | Trigger on impaired waters/TMDL/watershed source or relevance |
| 3.1.4 Protected Species and Critical Habitat | Agency/source species summary | Conditional/manual | Paragraph + letter/source ref | Agency/reviewer supplied | No default | Include with IPaC/state source or agency letters |
| 3.2 Cultural and Historic Resources | Cultural compliance context | Conditional; sensitive data | Short intro + restricted refs | Restricted/manual/public context separated | Conditional | Only with cultural module or manual source |
| 3.2.1 Archaeological Sites | APE and recorded sites | Restricted/manual | Manual paragraph/attachment | Authorized records | No default public drafting | Only with authorized records and reviewer-defined APE |
| 3.2.2 Historic Structures and Districts | Architectural APE and older properties | Conditional/manual | Paragraph/map/table if authorized | Authorized records + optional property age | Conditional | Include with architecture/cultural source |
| 3.3 Community Resources | Access-sensitive community facilities | Conditional | Intro + lists/maps | Source-backed + reviewer context | Conditional | Trigger on community-facility sources or project relevance |
| 3.3.1 Fire/EMS Stations | Emergency access sensitivity | Conditional | Paragraph/list/map | Source-backed + review | Conditional | Trigger on nearby facilities |
| 3.3.2 Government Buildings | Public-service access | Conditional | Paragraph/list/map | Source-backed | Conditional | Trigger on nearby facilities |
| 3.3.3 Education Facilities | School/childcare access | Conditional | Paragraph/list/map | Source-backed | Conditional | Trigger on nearby schools/childcare |
| 3.3.4 Health Care Facilities | Medical access/noise sensitivity | Conditional | Paragraph/list/map | Source-backed + review | Conditional | Trigger on nearby healthcare facilities |
| 3.3.5 Places of Worship | Community-gathering access | Conditional | Paragraph/list/map | Source-backed, often coarse | Conditional | Trigger on nearby facilities; avoid exhaustive claims |
| 3.3.6 Parks and Recreation Areas | Recreation access/context | Conditional | Paragraph/list/map | Source-backed | Conditional | Trigger on nearby/direct parks/recreation resources |
| 3.4 Utility and Infrastructure Considerations | Utility/infrastructure context | Conditional | Intro + lists/maps | Source-backed/manual | Conditional | Include if utility/infrastructure sources or reviewer flags exist |
| 3.4.1 Public Water Supply | Wells/water facilities | Conditional | Paragraph + map | Source-backed | Conditional | Trigger on nearby wells/facilities |
| 3.4.2 Utility Infrastructure | Pipelines/utilities | Conditional; sensitive | Paragraph/list/map | Source-backed + provider coordination | Conditional | Trigger on crossings/nearby assets; sensitivity rules |
| 3.4.3 Energy Infrastructure | Transmission lines/substations | Conditional | Paragraph/list/map | Source-backed + provider coordination | Conditional | Trigger on nearby/intersecting assets |
| 3.4.4 Airports | Airport proximity | Conditional | Short paragraph/map if relevant | Source-backed | No default | Trigger if airport within threshold or aviation relevance |
| 3.5 Contamination Risks | Regulatory/hazmat context | Generalizable/conditional | Intro | Source-backed/manual | Conditional/default if hazmat enabled | Include if regulated-facility sources configured |
| 3.5.1 Hazardous Materials Sites | Facility database/risk summary | Generalizable module; risk ranking review-gated | Paragraph + table + map + attachment ref | Source-backed + specialist/reviewer | Conditional/default if sources exist | Risk labels require policy/review |
| 3.5.2 Oil Wells | Oil/gas well screening | Conditional by geography/source | Short paragraph/table/map if findings | Source-backed | Conditional | Include where oil/gas source configured |
| 3.6 Socioeconomic and Business Considerations | Demographics and economic context | Conditional | Intro + tables/prose | Source-backed + manual | Conditional | Trigger on planning/access/community context |
| 3.6.1 Demographic Characteristics | Census tract/community context | Conditional/generalizable | Tables + short interpretation | Source-backed | Conditional | Trigger on Census/ACS source |
| 3.6.2 Local Businesses and Economic Nodes | Commercial access context | Project-specific/manual | Manual narrative/list/map optional | Reviewer/local context | No default | Only if reviewer supplies or business source enabled |
| 4 Conclusion and Next Steps | Reviewed summary and action path | Generalizable shape; reviewer judgment | Narrative | Reviewed evidence + decisions | Yes but gated | Generate after review; no new findings |
| 5 References | Bibliography of used sources | Generalizable | Reference list | Source manifest | Yes | Only cite sources actually used |
| Attachments | Maps, hazmat report, agency letters | Generalizable package model; contents conditional | Attachment list/package | Figure matrix + manual sources | Conditional | Include only generated/supplied attachments |

## 2. Section Policy Table
| section_id | Family | Extent type | Visual extent | Comparison-unit policy | Evidence pattern | Drafting mode | Output shape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| exec_summary | summary | presentation-only | presentation-only | none | reviewed section summaries | GPT only after reviewer confirmation | Compact narrative |
| intro.project_overview | intro | manual/project metadata | presentation-only | context_summary_list | project metadata | GPT after reviewer confirmation | Paragraph |
| intro.parent_study_relationship | planning context | manual/reviewer-supplied | presentation-only | manual_only | reviewer-supplied material | manual only | Paragraph |
| intro.project_area_comparison_units | project geography | direct project/comparison-unit extent | medium/context | context_summary_list | project geometry + comparison-unit metadata | GPT after reviewer confirmation | Paragraph + optional map |
| method.sources | methodology | presentation-only | presentation-only | none | source status/table summary | deterministic only | Paragraph + source appendix ref |
| method.mapping_analysis | methodology | presentation-only | presentation-only | none | figure/map support | deterministic only | Paragraph/bullets |
| method.limitations | limitations | presentation-only | presentation-only | none | caveat library + source status | deterministic only | Caveat paragraph/list |
| inventory.overview | inventory | presentation-only | attachment/panel | context_summary_list | table summary + figure support | deterministic + reviewed polish | Section intro |
| natural.wetlands_waterbodies | natural | direct extent; optional screening buffer | small/direct | table_only default | direct intersections; crossing counts; table summary; map support | GPT with source-backed evidence | Paragraph + table + figure |
| natural.floodplains_floodways | natural | direct project/comparison-unit extent | small/direct | table_only | direct intersections; acreage by zone; figure support | GPT with source-backed evidence | Paragraph + table + figure |
| natural.water_quality | natural | watershed/subwatershed + downstream context | large/watershed | context_summary_list | watershed membership; downstream context; impaired-water list | GPT with source-backed evidence | Paragraph + watershed map |
| natural.protected_species | natural | county/regional; screening buffer; manual | county/regional or attachment | manual_only | agency/reviewer material; optional screening | GPT only after reviewer confirmation | Paragraph + letter ref |
| cultural.archaeology | cultural | APE/direct disturbance; manual | attachment/panel | manual_only | authorized records; reviewer material | manual only | Paragraph/attachment |
| cultural.architectural | cultural | APE + visual/noise/vibration context | medium/context or attachment | manual_only | authorized records; optional property age | manual or GPT after confirmation | Paragraph/map/table if authorized |
| community.fire_ems | community | nearby/community context | medium/context | context_summary_list | nearest-within-buffer; count/list | GPT with evidence + review | Paragraph/list/map |
| community.government | community | nearby/community context | medium/context | context_summary_list | nearest-within-buffer; count/list | GPT with evidence + review | Paragraph/list/map |
| community.education_childcare | community | nearby/community context | medium/context | context_summary_list | nearest-within-buffer; count/list | GPT with evidence + review | Paragraph/list/map |
| community.healthcare | community | nearby/community context | medium/context | context_summary_list | nearest-within-buffer; count/list | GPT with evidence + review | Paragraph/list/map |
| community.places_of_worship | community | nearby/community context | medium/context | context_summary_list | nearest-within-buffer; count/list | GPT with evidence + review | Paragraph/list/map |
| community.parks_recreation | community | direct/adjacent + nearby context | medium/context | context_summary_list | nearest-within-buffer; count/list | GPT with evidence + review | Paragraph/list/map |
| infrastructure.public_water_supply | infrastructure | nearby context; optional buffer | medium/context | context_summary_list | nearest-within-buffer; figure support | GPT with evidence + review | Paragraph/map |
| infrastructure.utilities | infrastructure | direct intersections + nearby context | small/direct or medium/context | table_only or context_summary_list | direct intersections; list context | GPT only after reviewer confirmation | Paragraph/list/map |
| infrastructure.energy | infrastructure | direct intersections + nearby context | small/direct or medium/context | table_only or context_summary_list | direct intersections; list context | GPT only after reviewer confirmation | Paragraph/list/map |
| infrastructure.airports | infrastructure | county/regional; nearest-within-buffer | county/regional | none | nearest-within-buffer | deterministic or GPT with evidence | Short paragraph |
| contamination.hazmat_sites | contamination | screening buffer + direct extent | medium/context | table_only + facility list | nearest-within-buffer; risk table; attachment | GPT with evidence; risk labels review-gated | Paragraph + table + map |
| contamination.oil_gas_wells | contamination | direct extent + screening buffer | small/direct | table_only if findings | direct intersections/nearest | deterministic or GPT with evidence | Short paragraph/map |
| socio.demographics | socioeconomic | census/community + county/regional comparison | county/regional | none | table summary; census membership | GPT with source-backed evidence | Paragraph + tables + map |
| socio.business_nodes | socioeconomic | nearby/community; manual | medium/context | manual_only | reviewer-supplied; optional POI context | manual or GPT after confirmation | Paragraph/list |
| conclusion.next_steps | conclusion | presentation-only | presentation-only | none | reviewed findings only | GPT only after reviewer confirmation | Narrative |
| references | references | presentation-only | presentation-only | none | source manifest | deterministic only | Reference list |

### Required caveats and prohibited claims
| Section | Required caveats | Prohibited claims | Allowed refs |
| --- | --- | --- | --- |
| exec_summary | Screening-level; human-reviewed; based on available sources | New facts not in reviewed sections; final impact/no-impact conclusions | Reviewed sections, tables, figures, source status |
| natural.wetlands_waterbodies | NWI non-jurisdictional; field delineation required | Jurisdictional wetland; no wetlands; no impacts without review | NWI, NHD, wetlands table, wetlands figure |
| natural.floodplains_floodways | FEMA mapped hazard; local/H&H coordination design-dependent | Permit determination; flood risk guarantee | FEMA/NFHL/DFIRM table and figure |
| natural.water_quality | Direct vs downstream distinction; BMP/permit planning only | Direct impairment if only downstream; pollutant causation | NHD, HUC, 303(d)/TMDL source, watershed figure |
| natural.protected_species | Agency/source date; habitat/effect confirmation needed | No effect; no species present; no suitable habitat without confirmation | Agency letters, IPaC/state source |
| cultural.* | Authorized vs public/coarse source separation; reviewer-defined APE | Public context as MDAH/SHPO; eligibility/effect without authorized records | Restricted records, reviewer letters, public context labeled |
| community.* | Facility lists may not be exhaustive; planning context only | All facilities; safe access ensured; unsupported operational impacts | Community source table and maps |
| infrastructure.* | Utility data may be incomplete/sensitive; owner coordination needed | Conflict resolved; exact sensitive details if restricted | Utility source, owner data, maps |
| contamination.hazmat_sites | Database screening; risk tiers reviewed; not Phase I unless report supplied | Cleanup status overclaim; no contamination; site safe | EPA/state datasets, hazmat table, Appendix B |
| socio.demographics | Census geographies extend beyond project; context only | Disproportionate impact/EJ determination without analysis | ACS/Decennial, census map, demographic tables |
| conclusion.next_steps | No new evidence; reviewer judgment | Binding commitments; final regulatory findings | Reviewed sections and review decisions |

## 3. Source Needs by Section
| Section | Source | Category | Likely public/source candidate | Need type | Supports | Output support | Current app coverage | Gap? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Project area | Project geometry/comparison units | Project metadata | Reviewer-uploaded geometry | Required/reviewer-supplied | Direct analysis | Prose, maps, comparison units | Covered conceptually | Needs comparison-unit policy |
| Basemaps | Aerial imagery/topographic data | Basemap | NAIP/topo/terrain services | Required/optional | Presentation/support | Figures | Covered via NAIP sidecars | Needs source-status display |
| Wetlands/waterbodies | USFWS NWI | Wetlands | USFWS NWI | Required for module | Direct + nearby | Table, figure, prose, caveat | Covered | Needs caveat + table policy |
| Wetlands/waterbodies | NHD streams/waterbodies | Hydrography | USGS NHD/NHDPlus/local hydro | Required for crossings | Direct intersections | Table/prose | Covered | Needs crossing-count policy |
| Floodplains | FEMA DFIRM/NFHL | Flood hazard | FEMA NFHL/DFIRM | Required for module | Direct intersections | Table, figure, prose | Covered | Needs floodway/zone acreage policy |
| Water quality | HUC-12 subwatersheds | Hydrology context | USGS WBD/HUC | Required for water-quality context | Watershed/subwatershed | Figure/prose | Partial via hydrography | Gap if WBD not materialized |
| Water quality | 303(d) impaired waters | Water quality | State impaired-waters/TMDL lists | Required if module | Watershed/downstream | Prose, figure, caveat | Not listed | Gap |
| Water quality | TMDLs/stressors | Water quality | State TMDL database | Optional/conditional | Downstream context | Prose/caveat | Not listed | Gap |
| Protected species | USFWS/IPaC/critical habitat | Species/habitat | USFWS IPaC/critical habitat | Manual/optional source | Regional/range + review | Prose, letter attachment | Not listed | Gap/manual |
| Protected species | State species/natural heritage | Species/habitat | State agency/natural heritage | Restricted/manual | Buffer/regional | Prose, letter attachment | Not listed | Gap/manual |
| Cultural | MDAH/SHPO inventory | Cultural/restricted | Authorized SHPO/MDAH records | Restricted/reviewer-supplied | APE/direct/nearby | Prose/restricted figure/attachment | Future placeholder | Needs strict policy |
| Cultural | Public/coarse cultural context | Cultural/public context | MARIS/public layers/OpenContext/DINAA-style | Optional/public-coarse | Screening context only | Caveat/prose | Covered conceptually | Needs guardrails |
| Cultural | APE geometry | Project/reviewer | Reviewer-defined APE | Required for cultural module | Manual/direct | Prose/map | Not explicit | Gap/manual |
| Community resources | Fire/EMS, government, schools, childcare, healthcare, worship, parks | Community facilities | HIFLD, local GIS, NCES, state licensing, OSM, PAD-US | Optional/conditional | Nearby/community | List/map/prose | Not listed | Gap |
| Public water supply | Water treatment plant/public wells | Infrastructure/water | State health/environmental data; SDWIS context | Optional/conditional | Nearby context | Figure/prose | Not listed | Gap |
| Utilities/energy | Pipelines/transmission/substations | Utility/energy | NPMS/HIFLD/state/local/owner supplied | Conditional/sensitive/manual | Direct + nearby | List/map/prose | Not listed | Gap/manual |
| Airports | Nearby airports | Transportation infrastructure | FAA airport data | Optional/conditional | Regional/nearest | Prose/map | Not listed | Gap |
| Hazmat | EPA/state regulatory databases | Regulated/hazardous | EPA FRS, Brownfields, NPDES, Superfund, TRI, UST, solid waste | Required for module | Screening buffer/nearby | Table, figure, prose | Covered well as class | Needs risk-ranking policy |
| Hazmat | Hazardous Materials Assessment Report | Technical report | Reviewer-supplied report | Manual/conditional | Attachment support | Attachment/body summary | Evidence package supports | Needs attachment workflow |
| Oil/gas | State oil/gas well database | Oil/gas | State oil/gas board wells | Conditional/state-specific | Direct/screening buffer | Prose/map/table | Covered as source class | Needs state source config |
| Demographics | Census tracts and ACS/Decennial data | Socioeconomic | Census TIGER/ACS/Decennial | Conditional | Community/regional | Map/table/prose | Not listed | Gap |
| Business nodes | Commercial districts/local businesses | Socioeconomic/economic | Reviewer knowledge, parcels, POI, business registry | Manual/optional | Nearby/community | Prose/list/map | Parcels optional only | Gap/manual |
| Agency letters | Agency consultation letters | Manual agency material | Reviewer upload | Manual/reviewer-supplied | Attachment support | Attachment + summary | Review queue supports | Needs source type + citation policy |

## 4. Figure Needs
| Figure purpose/title | Section | Likely source layers | Extent | Body/attachment | Matrix-backed? | Requirement | Evidence relation | Current support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Project location / study area / comparison units | Intro | Project geometry, basemap, jurisdictions | medium/context | Main body | Yes | Recommended default | Presentation + direct geometry | Likely supported; needs policy |
| Overall Environmental Constraints Inventory Map | Inventory / Attachment A | All active constraints layers | large/project-wide | Attachment/support | Yes | Conditional | Presentation/support | Figure generation supports class |
| Panel Index Map | Attachment A | Project extent, panel footprints | attachment/panel | Attachment | Yes | Conditional | Presentation/support | Needs panel policy |
| Detailed Panel Maps | Attachment A | All active constraints layers + basemap | attachment/panel | Attachment | Yes | Conditional, especially long corridors | Presentation/support | App supports figures; needs paneling |
| Wetlands and Waterbodies | 3.1.1 | NWI, NHD/waterbodies, project geometry, basemap | small/direct or medium/context | Main body | Yes | Conditional/default if source enabled | Direct evidence + nearby context | Supported |
| FEMA Flood Zones | 3.1.2 | FEMA/NFHL/DFIRM, project geometry | small/direct | Main body | Yes | Conditional/default if source enabled | Direct evidence | Supported |
| Streams and 303(d) Impaired Waters within Subwatersheds | 3.1.3 | NHD, WBD/HUC-12, 303(d), TMDL, project geometry | large/watershed | Main or attachment | Yes | Conditional | Watershed/downstream context | Hydro supported; 303(d)/WBD gap |
| Protected species / critical habitat | 3.1.4 | Critical habitat/range/source letters/project geometry | county/regional or attachment | Usually attachment/manual | Yes if source exists | Conditional/manual | Screening context | Gap |
| Cultural resources | 3.2 | Restricted cultural records, APE, project geometry | attachment/restricted | Attachment/restricted | Yes with access controls | Manual/restricted | Authorized records | Placeholder only; needs policy |
| Community resource maps | 3.3.x | Fire/EMS, government, schools, childcare, healthcare, worship, parks | medium/context | Main or attachment | Yes | Conditional | Nearby/community context | Gap |
| Public Water Supply Wells | 3.4.1 | Public wells, water facilities, project geometry | medium/context | Main or attachment | Yes | Conditional | Nearby infrastructure context | Gap |
| Utility/Energy Infrastructure | 3.4.2-3.4.3 | Pipelines, transmission lines, substations | small/direct or medium/context | Main or attachment with sensitivity controls | Yes | Conditional/manual | Direct crossings + nearby context | Gap |
| Airports | 3.4.4 | FAA airports, project geometry | county/regional | Usually no figure unless triggered | Yes | Optional | Nearest/regional context | Gap |
| Hazardous/Regulated Sites | 3.5.1 | EPA/state hazardous layers, project buffer | medium/context | Main + support appendix | Yes | Conditional/default if hazmat enabled | Nearby/screening-buffer evidence | Source class supported |
| Oil/Gas Wells | 3.5.2 | State oil/gas wells, project geometry/buffer | small/direct | Optional main/attachment | Yes | Conditional | Direct/screening evidence | Source class supported |
| Census Tracts | 3.6.1 | Census tracts, project geometry | county/regional | Main body | Yes | Conditional | Community/regional context | Gap |
| Business/economic nodes | 3.6.2 | Parcels, POI/business data, commercial areas | medium/context | Optional/manual | Yes if source-backed | Manual/conditional | Community/economic context | Parcels optional; business gap |

## 5. Table Needs
| Table purpose/title | Section | Source data needed | Likely columns | Row type | Body/attachment | Requirement | Current support |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Wetlands/waterbodies by comparison unit | 3.1.1 | NWI, NHD, project/comparison geometries | Unit; stream crossings; wetland class; acres/count; notes; source date | Per comparison unit | Body if compact; attachment if large | Conditional/default if module enabled | Table system exists; needs spec |
| Wetland/waterbody feature inventory | 3.1.1 | NWI/NHD intersections | Feature type; name; source ID; unit; acreage/length; direct/buffer flag | Per source feature | Evidence attachment unless small | Optional/supporting | Evidence package likely supports |
| FEMA flood zones by comparison unit | 3.1.2 | FEMA/NFHL/DFIRM | Unit; zone; floodway flag; acreage/linear crossing; notes | Per comparison unit + zone | Body if compact | Conditional/default if flood module enabled | Needs policy |
| Flood hazard feature inventory | 3.1.2 | FEMA intersections | Zone; BFE if available; floodway; source panel; unit; acreage | Per source feature/zone | Evidence attachment | Optional | Needs table spec |
| Water quality / watershed context | 3.1.3 | WBD/HUC, NHD, 303(d), TMDL | HUC; waterbody; direct/downstream; impairment; TMDL status; notes | Summary/waterbody rows | Body if small; attachment otherwise | Conditional | Gap source + table spec |
| Protected species consultation summary | 3.1.4 | Agency letters/IPaC/state species | Agency/source; date; finding; conditions; reviewer status | Reviewer-supplied source row | Body or attachment | Manual/conditional | Needs manual material handling |
| Cultural resource summary | 3.2 | Authorized MDAH/SHPO/reviewer data | Resource type; count; relation to APE; eligibility/status; caveat | Summary rows; restricted details in attachment | Restricted attachment | Manual/restricted | Needs access policy |
| Community resources facility table | 3.3 | Community facility sources | Facility type; name; distance/relation; access sensitivity; source | Per facility | Attachment; compact body list if small | Conditional | Gap |
| Utility crossings table | 3.4.2-3.4.3 | Pipeline/transmission/substation sources | Asset type; owner if allowed; crossing/nearby; location unit; coordination flag | Per source feature/crossing | Attachment/body if small | Conditional/manual | Gap |
| Public water supply wells table | 3.4.1 | Well/facility source | Facility/well ID; source; relation; protection notes; caveat | Per facility | Body/attachment | Conditional | Gap |
| Hazardous/regulated facilities risk table | 3.5.1 | EPA/state databases + reviewer risk rules | Facility; program/source; distance/relation; status; risk tier; reviewer note | Per facility | Body for elevated-risk subset; full list attachment | Conditional/default if hazmat enabled | Source class covered; risk rules gap |
| Oil/gas wells table | 3.5.2 | State oil/gas wells | Well ID/name; status; relation; source date | Per source feature | Body if findings; otherwise no table | Conditional | Covered class; state config needed |
| Income demographics | 3.6.1 | ACS/Decennial/Census geography | Geography; poverty/low-income metric; comparison geography | Summary rows | Body if compact | Conditional | Gap |
| Demographic composition | 3.6.1 | ACS/Decennial | Geography; selected race/ethnicity groups; comparison geography | Summary rows | Body if compact | Conditional | Gap |
| Source status / evidence audit | Method/attachment | App source status | Source ID; title; effective truth; acquisition status; sections; caveats | Per source | Evidence package, not report body | Required internally | App likely supports; needs doc shape |
| Review queue decisions | Evidence/review package | Review queue | Item; evidence; reviewer action; final text state | Per deliverable item | Evidence/review package | Required internally | App supports |

## 6. Alternative / Comparison-Unit Logic
Use this expansion ladder: none -> table_only -> context_summary_list -> narrative_children -> manual_only. Default should be table_only, not narrative children.
| Section | Sample behavior | Generalize? | Recommended Review Assist behavior |
| --- | --- | --- | --- |
| Study Area / Project Area | Per-alternative narrative descriptions | Trail/corridor-specific | Use generic comparison-units summary. Support alternatives, parcels, sites, corridors, polygons, etc. |
| Wetlands/waterbodies | Per-alternative subsection attempted; comparison table used; several subsections blank | Conditional + incomplete | Default to table-only per comparison unit. Narrative children only if reviewer enables and evidence differs materially. |
| Floodplains/floodways | Comparison table by trail alignment; no per-alt narrative children | Conditional | Table-only per comparison unit by default. |
| Water quality | Project-wide HUC/downstream context | Generalizable context pattern | Summarize together by watershed; per-unit only when watersheds/receiving waters differ materially. |
| Protected species | Project-wide agency/range discussion | Manual/conditional | No automatic per-alt expansion unless source findings are unit-specific. |
| Cultural resources | APE-based, not per alternative | Conditional/manual | APE controls; reviewer defines APEs. |
| Community resources | Facility/access discussion, not alternative comparison | Conditional | Nearby context list; optionally relate facility to comparison unit. |
| Utilities/infrastructure | Direct crossings/nearby infrastructure | Conditional | Use table/list by asset; group by comparison unit if direct intersections differ. |
| Hazmat | Facility/risk list by corridor/buffer | Generalizable hazmat pattern | Use facility-level risk table; optionally relate each facility to comparison unit. |
| Demographics | Census tracts along corridor | Conditional | Summarize by census geographies; per-unit only if units traverse different communities. |
| Business nodes | Commercial node narrative | Manual/project-specific | Manual/reviewer-supplied unless POI/business source enabled. |

## 7. Spatial Scope / Extent Semantics
| Section | Spatial terms | Implied extent type | Map extent larger? | Table/list alignment | Wording rule |
| --- | --- | --- | --- | --- | --- |
| Introduction | project, corridor, planning area | Direct project/study area | Maybe | N/A | Use project area/study area from supplied geometry. |
| PEL relationship | broader PEL, future NEPA | Manual/reviewer context | N/A | N/A | Keep custom; do not imply every report is PEL-linked. |
| Study Area | trail alternatives, corridor, terminus, route | Direct comparison-unit extent | Overview likely medium/context | Alternative descriptions not source-table aligned | Use comparison unit generically. |
| Methodology | within alignments, maps, Appendix panels | Direct + presentation | Yes | N/A | Distinguish analysis extent from map frame. |
| Wetlands/waterbodies | within, along, adjacent, low-lying | Direct + nearby/adjacent | Likely yes | Table direct-ish but incomplete | Use mapped/intersect/occur within; do not say jurisdictional. |
| Floodplains/floodways | within, locations, Zone AE, Zone X | Direct project extent | Figure says in/near; analysis says within | Table should use direct intersection only | Separate mapped within project from shown near project. |
| Water quality | crosses HUC-12s, downstream, subwatersheds | Watershed + downstream | Yes | List is watershed/downstream | Never say impaired waters are within if only downstream. |
| Protected species | within range, two-mile radius, habitat | Regional/range + buffer + manual | Maybe | Letter findings are not GIS-only | Only state agency/reviewer findings when source supplied. |
| Cultural | near, APE, within APE, adjacent, visual/noise/vibration | Manual APE + nearby context | Cultural maps may be restricted | Must match APE definition | Public context is not authorized SHPO/MDAH records. |
| Community resources | along, near, just outside, within or near | Nearby/community context | Yes | Lists mix direct and nearby | Label within vs near/outside; avoid exhaustive claims. |
| Utilities/energy | intersect, cross, nearby | Direct + nearby | Map may be context | List direct and nearby | Label crossing vs nearby asset; require owner coordination. |
| Hazmat | within, 0.1 mile, adjoining, nearby | Screening buffer + adjacency | Yes | Counts use multiple extents | Every count must carry its extent. |
| Oil wells | within project limits | Direct extent | No unless figure | No-finding direct only | Do not imply broader county absence. |
| Demographics | census tracts along, citywide, county | Census/community/regional | Yes | Tables use tracts + city/county comparisons | Census context, not direct impact area. |
| Business nodes | along corridor, commercial district | Manual/community context | Context | Narrative only | Manual/reviewer context unless source-backed. |

### Extent language rules
| Term | Use only when |
| --- | --- |
| within | Feature geometry intersects the project/comparison-unit extent or a named buffer stated in the sentence |
| near | Feature is outside direct extent but within a configured screening distance |
| adjacent | Parcel/feature touches or is explicitly tagged adjoining; do not use for generic nearby |
| in the vicinity | Avoid unless extent is named |
| downstream | Hydrologic network or reviewer confirms flow relationship |
| watershed/subwatershed | HUC/WBD context drives the analysis, not direct footprint |
| APE | Reviewer defines cultural APE; do not infer from generic buffer unless policy says so |
| county/city/regional | Demographics/species/airport context; never imply direct project impact |
| corridor | Only if project geometry is a corridor/route; otherwise use project area or comparison unit |
| shown on map | Figure support only; not evidence of direct intersection |

## 8. Wording and Caveat Library
### Wetlands / NWI
Reusable pattern: Desktop screening identified mapped wetlands and/or waterbodies from configured sources within or near the named extent. These mapped features are useful for early planning but do not establish jurisdictional limits. Final boundaries and jurisdictional status require field delineation and agency coordination.
Avoid: jurisdictional wetlands are present; no wetlands are present; NWI confirms boundaries; impacts will or will not occur.

### Hydrography / water quality
Reusable pattern: Hydrography and watershed datasets identify streams, drainage crossings, receiving waters, and watershed context. If impaired waters are downstream rather than intersecting the project, describe them as downstream/contextual.
Avoid: impaired streams are within the project when only downstream; project will affect water quality without design facts; no water-quality concerns based only on no direct 303(d) intersections.

### Floodplain / floodway
Reusable pattern: FEMA flood hazard data identify mapped flood zones/floodways within the named extent. Work in mapped flood hazard areas may require local floodplain review and hydrologic/hydraulic analysis depending on final design.
Avoid: permit required unless confirmed; no flood risk; minimal hazard means no drainage concern.

### Protected species / critical habitat
Reusable pattern: Protected species and habitat findings are based on named source/agency material. Desktop range or database screening does not by itself determine project effect.
Avoid: no effect; no species present; no suitable habitat unless agency/reviewer-confirmed.

### Cultural resources / restricted records
Reusable pattern: Separate authorized agency/reviewer-supplied records from public/coarse screening context. Sensitive details should remain in restricted evidence unless approved for disclosure.
Avoid: public/coarse data as SHPO/MDAH records; no historic properties affected without Section 106 basis; all archaeological resources identified.

### Community resources
Reusable pattern: Identified nearby community resources may be sensitive to access, detours, noise, or construction staging. Lists are planning-level screens and should be verified with local stakeholders where operations may be affected.
Avoid: all facilities; safe access will be maintained unless committed.

### Regulated / hazardous facilities
Reusable pattern: Regulatory database screening identifies facilities within the named extent/buffer. Database presence indicates possible due-diligence considerations and does not establish contamination, liability, cleanup status, or construction risk.
Avoid: site is contaminated without source support; no contamination risk; Phase I ESA conclusion without a Phase I or hazmat report.

### Utility / infrastructure
Reusable pattern: Mapped utility and infrastructure features are planning coordination inputs. Locations and ownership should be verified with providers before design or construction; sensitive details require access controls.
Avoid: conflict resolved; utility location confirmed; service disruption likely without design evidence.

### Socioeconomic / demographics
Reusable pattern: Census data provide community context for planning and outreach. Census geographies may extend beyond the project area, so tract-level data should not be described as direct project-area demographics without qualification.
Avoid: environmental justice impact; disproportionate effect; all affected residents.

### Screening-only / no determination
Reusable pattern: The report is a screening-level constraints review. It does not replace field surveys, agency determinations, permitting, design-level impact analysis, legal conclusions, or regulatory findings.
Avoid: compliance determination; final impact conclusion; binding commitment.

## 9. Manual / Reviewer-Supplied Materials
| Component | Why manual/reviewer-supplied | Recommended app handling |
| --- | --- | --- |
| Relationship with PEL Study | Parent-study relationship is project context | Manual section; conditional |
| Project purpose/background | Usually project narrative, not GIS-derived | Reviewer-supplied metadata/narrative |
| Alternatives narrative | Design/planning context | Comparison-unit metadata; no GPT facts unless supplied |
| Agency consultation letters | External agency records | Upload as manual_source; summarize only after review |
| Protected species findings | Agency/reviewer confirmation needed | Manual/attachment-backed |
| SHPO/MDAH cultural records | Restricted/authorized records | Restricted source type; no public substitution |
| APE definition | Reviewer/cultural specialist defines | Required manual geometry/notes |
| Hazardous Materials Assessment Report | Specialist report/risk ranking | Attachment + reviewed summary |
| Hazmat risk categories | Requires policy/specialist judgment | Review-gated; no GPT-only ranking |
| Utility owner coordination | Provider/design coordination | Manual flags + owner contact notes |
| Business/economic node narrative | Local context often not dataset-complete | Manual/reviewer-supplied |
| Prior studies | Project record | Manual source upload |
| Field verification status | Human fieldwork | Manual evidence |
| Final conclusions/next steps | Reviewer judgment | Review-gated; no new facts |
| Commitments/mitigation | Agency/project commitments | Manual only |

## 10. Generalizable vs Project-Specific
| Bucket | Elements | Action |
| --- | --- | --- |
| Generalizable template elements | Cover metadata, executive-summary shape, TOC/list generation, intro, methodology, source/data procedures, limitations, resource-category inventory, references, attachment list, map/table/evidence model, caveat library | Keep as generic structure |
| Conditional elements | Wetlands, floodplains, water quality, protected species, cultural, community resources, utilities, contamination, socioeconomic, business nodes, panel maps, hazmat attachment, agency letters | Include by source/project triggers |
| Project-specific elements | Project names, place names, named facilities, exact counts, addresses, dates, local creek/facility descriptions | Do not copy into reusable policy |
| Trail/corridor-specific elements | Trail alternatives, stream crossings by alignment, rail/highway/nature corridor language, panel maps split by corridor sections, boardwalk/culvert trail wording | Support only as comparison-unit/corridor mode |
| PEL-specific elements | Relationship with PEL Study, PEL team framing, transition into NEPA from PEL, PEL public/stakeholder process language | Conditional/manual; not default |
| Incomplete/uncertain elements | Blank table cells, unresolved comments, broken references/figure numbering, placeholder attachments, mixed project identities | Mark draft-only; do not generalize |
| Do-not-generalize elements | Exact regulatory conclusions, agency findings, exact facility lists, private-facility PEL rule, ArcGIS version, no-significant-impact language | Ban or review-gate |

### Specific call: Relationship with the PEL Study
Do not include this section in the default Review Assist template. Treat it as `intro.parent_study_relationship`, with `include_default: false`, `drafting_mode: manual_reviewer_supplied_only`, and a trigger such as `parent_study.type in ["PEL", "planning_study", "corridor_study"]`.

## 11. Diff Against Current Review Assist App
| Target item | App diff classification | Notes |
| --- | --- | --- |
| Generic report structure | App has export package but needs policy/matrix | Add canonical section policy |
| Source status / effective truth | App covers this well | Surface in methodology/references |
| Compact report body + evidence package | App covers this well | Preserve; no raw dumps |
| Wetlands/NWI | App has source | Needs section policy, caveat, table spec |
| Hydrography/NHD | App has source | Needs crossing metrics and waterbody table policy |
| FEMA flood hazard | App has source | Needs floodway/flood-zone metrics, table, caveats |
| Water quality 303(d)/TMDL | App has hydro source but lacks water-quality source | Add state impaired-waters/TMDL source class |
| HUC/WBD watershed context | Partial/unclear | Add explicit watershed source and policy |
| Protected species/critical habitat | App lacks needed source | Add future/manual/IPaC/critical habitat/state species support |
| Agency consultation letters | Manual/reviewer-supplied only | Add manual source type + attachment summary workflow |
| Public/coarse cultural context | App has source class | Needs strict wording guard |
| Restricted MDAH/SHPO | Future placeholder | Needs access controls + manual source policy |
| APE logic | App likely lacks policy | Add reviewer-defined APE geometry/material |
| Community resources | App lacks source/section | Add optional modules or defer |
| Public water supply wells | App lacks source | Add later state/EPA source |
| Utility/pipeline/electric infrastructure | App lacks source | Add manual/sensitive/deferred first |
| Airports | App lacks source | Add FAA source if useful |
| Hazmat database screening | App covers source class | Needs risk/ranking and attachment policy |
| Oil/gas wells | App has source class | Needs state config and no-finding wording |
| Demographics/Census/ACS | App lacks source | Add TIGER/ACS/Decennial module |
| Business/economic nodes | Manual/reviewer-supplied only | Optional parcels/POI later |
| Figures | App has figure generation | Needs figure matrix, extent classes, panel policy |
| Tables | App has deliverable tables | Needs per-section table specs |
| Comparison-unit expansion | App needs policy | Default table_only; narrative only if triggered |
| GPT Interpretive Assist | App wiring is right | Needs per-section drafting modes/prohibited claims |
| DOCX export quality | App exports but needs QA gate | Add caption/cross-ref/empty-table/comment/render checks |

## 12. Recommended Implementation Moves
| Priority | Move | Why |
| --- | --- | --- |
| P0 | Create canonical review_assist_report_policy.json | Provides section/source/figure/table/caveat policy spine |
| P0 | Make extent_type and visual_extent_class first-class | Prevents map extent from becoming analysis claim |
| P0 | Add comparison-unit expansion guard | Default table_only; narrative children only when enabled |
| P0 | Add caveat and prohibited-claim libraries | Keeps deterministic and GPT drafting aligned |
| P0 | Add source-needs manifest by section | Prevents sections from rendering without adequate sources |
| P0 | Add source truth/status wording | Labels incomplete, stale, deferred, manual data honestly |
| P0 | Segregate cultural source classes | Public/coarse context must not become authorized SHPO/MDAH records |
| P0 | Add manual/restricted source types | Needed for letters, hazmat reports, cultural records |
| P0 | Add GPT eligibility matrix | GPT only where evidence + policy + caveats exist |
| P0 | Add export QA checks | Catch empty tables, comments, broken captions, figure numbering, stale refs |
| P1 | Build figure/table matrix from policy | Makes deliverables predictable and testable |
| P1 | Add wetland, flood, waterbody table specs | High-value and already source-backed |
| P1 | Add hazmat facility table/risk review workflow | Current sources exist but risk wording needs guardrails |
| P1 | Add water-quality context policy | Avoids wrong direct/downstream language before full source expansion |
| P1 | Replace sample Study Area with neutral Project Area and Comparison Units | Keeps app feature-neutral |
| P1 | Add attachment manifest | Tracks maps, evidence package, manual attachments, agency letters |
| P1 | Connect review queue to sections/tables/figures | Human decisions stay explicit |
| P2 | Add WBD/HUC + state 303(d)/TMDL sources | Needed for water-quality module |
| P2 | Add species/critical habitat/manual agency letter support | Needed for protected species |
| P2 | Add Census/ACS module | Needed for socioeconomic section |
| P2 | Add community facilities and public water supply sources | Needed for community/infrastructure sections |
| P2 | Add utility/energy/FAA sources as manual/sensitive/deferred | Useful but needs careful source policy |
| P3 | Add GPT style context file | Tone/shape only; no project facts |
| P3 | Polish report rendering, captions, TOC, panels, glossary | Better UX after core policy works |

### GPT pilot recommendations
| Good GPT pilot | Why |
| --- | --- |
| Methodology source summary | Deterministic source list can bound it |
| Limitations/Data gaps | Caveat library controlled |
| Wetlands/NWI summary | Strong source + strong caveat |
| FEMA floodplain summary | Strong source + deterministic table |
| Hazmat database context | Useful if risk labels are reviewer-gated |
| Community resource context | Useful but must say identified nearby |
| Demographic context | Good if no EJ/disproportionate-impact conclusions |
Avoid early GPT for cultural determinations, protected species effect language, agency consultation interpretation, hazmat risk rankings, final commitments, PEL relationship, and business/economic impacts.

## 13. Suggested Machine-Readable Policy Shape
Use one canonical file: `config/review_assist_report_policy.json`, plus one concise explanatory doc: `docs/domains/REPORT_POLICY.md`. Avoid premature config sprawl.

Recommended top-level JSON shape:
```json
{
  "version": "0.1",
  "report_profile": "environmental_constraints_screening",
  "defaults": {
    "drafting_mode": "deterministic_only",
    "comparison_unit_expansion": "table_only",
    "body_compactness": {
      "max_body_rows_per_table": 12,
      "overflow_destination": "evidence_attachment"
    },
    "extent_terms": {
      "within": "direct_intersection",
      "near": "screening_buffer",
      "downstream": "hydrologic_network_or_reviewer_confirmed",
      "ape": "reviewer_defined"
    }
  },
  "sections": "see config/review_assist_report_policy.json",
  "sources": "see config/review_assist_report_policy.json",
  "figures": "see config/review_assist_report_policy.json",
  "tables": "see config/review_assist_report_policy.json",
  "caveat_bundles": "see config/review_assist_report_policy.json",
  "prohibited_claim_bundles": "see config/review_assist_report_policy.json"
}
```

## 14. GPT Style Context Recommendations
The GPT style context should guide tone and shape only. It should not contain project facts, place names, counts, facility names, agency findings, dates, trail/PEL-specific content, or unfinished draft content.

Include: compact environmental constraints prose; cautious source-backed language; direct vs nearby vs downstream vs watershed vs regional vs APE distinctions; table/figure refs only when allowed; no final impact/effect/eligibility/permit determinations; manual material labels; no trail/corridor language unless project type supports it.

Exclude: project names, named creeks/facilities/addresses, alternative 1A/1B/2/3/4 content, agency letter findings, cultural resource counts/eligibility, exact sample tables/figures, ArcGIS version, no-significant-impact phrasing, and Mississippi-only assumptions.

### GPT style mini-template
```text
Write concise, screening-level environmental constraints prose.

Use only the evidence supplied in the section evidence packet. Do not infer missing source findings, regulatory determinations, design commitments, permit requirements, cultural eligibility, species effect, contamination status, or final impacts.

Preserve extent semantics:
- within = direct intersection with named analysis extent
- near = within configured screening buffer
- downstream = hydrologic relationship supported by source or reviewer
- watershed/subwatershed = contextual hydrologic geography
- APE = reviewer-defined cultural extent
- shown on figure = presentation support, not impact evidence

Use cautious phrases such as desktop screening identified, mapped features indicate, based on available source data, may require field verification or agency coordination, and should be reviewed as design advances.

Avoid confirmed, no impact, no effect, jurisdictional, eligible/ineligible, all facilities, safe access ensured, permit required, contamination present/absent, and disproportionate impact.

Keep the report body compact. Refer detailed records to tables, figures, attachments, or the evidence package.
```

## 15. Codex Prompt Starters
### P0 policy object prompt
```text
Build config/review_assist_report_policy.json as the canonical report policy object. Every section must define include_default, trigger, extent_type, visual_extent_class, comparison_unit_expansion, evidence_patterns, drafting_mode, required_caveat_bundles, prohibited_claim_bundles, allowed_sources, allowed_tables, allowed_figures, and review requirements. Update report generation so a section cannot render unless its trigger, source status, extent type, caveat bundle, and allowed refs are satisfied.
```

### P0 extent semantics prompt
```text
Add explicit analysis_extent and visual_extent fields to deliverable sections, figures, and evidence records. Update wording helpers so within, near, adjacent, downstream, watershed, county/regional, APE, corridor, and shown on map are only used when their configured semantics are satisfied. Add tests preventing a watershed or visual map extent from being described as a direct project intersection.
```

### P0 GPT guardrail prompt
```text
Implement a GPT eligibility matrix from report policy. GPT drafting is allowed only for sections whose policy permits it and whose evidence packet contains the required source-backed records. Enforce prohibited claim bundles before and after generation. Block or review-gate final impact, no effect, jurisdictional, eligibility, contamination, permit, and commitment language.
```
