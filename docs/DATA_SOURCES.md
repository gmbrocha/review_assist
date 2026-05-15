# Data Sources

This document defines the practical source stack for building the best-case source/context package for environmental and contextual review reports.

The current baseline includes a local source catalog, project source registries, source status sets, source acquisition manifests, and source inventory/provenance artifacts so reviewer-supplied, manually downloaded, or explicitly downloaded public layers can be registered, inspected, and checked. USFWS NWI wetlands, USGS NHD hydrography, and optional FEMA NFHL effective flood hazard zones are the first implemented public downloaders. Other sources below remain candidates requiring validation for coverage, licensing, access method, update cadence, accuracy, attribution, and fitness for use.

## Source Philosophy

The system should build reports from source-backed context wherever possible.

Public datasets from government agencies, educational institutions, and authoritative public infrastructure sources can serve as reliable baseline screening data. They still require provenance and caveats because desktop review is not field verification.

The system should preserve:

- Source name.
- Publisher.
- Access URL or local path.
- Access date.
- Published or metadata date where available.
- Geometry type and CRS.
- Use restrictions and attribution.
- Known limitations.
- Review status.

## Source Handling Principles

- Record source name, publisher, access URL/path, access date, published date if available, CRS, geometry type, and usage constraints.
- Distinguish downloaded local layers from remote services.
- Distinguish public sources from restricted, authenticated, or reviewer-supplied sources.
- Track source category status in the workspace source status set.
- Track source gap/acquisition status in the workspace source acquisition manifest.
- Preserve source uncertainty and stale-data warnings.
- Prefer deterministic GIS/source checks before AI narrative synthesis.
- Do not add paid services, credentials, or restricted integrations without explicit approval.
- Treat imagery-observed features as review items until validated by a human reviewer.
- Send every source-backed output into the review queue before export.

## Source Status Set

The canonical workflow resolves required report source categories into a `SOURCE_STATUS_SET`.

Suggested statuses:

- `provided_locally`: user supplied a local layer, document, report, or map.
- `downloadable`: public data appears available but is not downloaded yet.
- `downloaded`: public data has been acquired for the workspace.
- `failed`: a supported acquisition attempt failed and should remain visible as a caveat/review item.
- `gated`: access requires credentials, qualified access, agency request, or restricted handling.
- `stubbed`: a placeholder exists so report sections can include a review requirement or caveat.
- `missing`: expected source material is not available.
- `optional`: useful context but not required for the selected report profile.
- `needs_review`: source status or fitness for use requires reviewer confirmation.

Missing, failed, gated, and stubbed categories should not fail the workflow by default. They should create review queue items, uncertainty flags, and report caveats so the reviewer can decide how to proceed.

## Phase 2A/2B Source Priority

The implemented Phase 2A catalog is intentionally broader than the first automated checks. The catalog records major source categories now, while Phase 2B initially analyzes local files only.

First-pass automated spatial checks should prioritize:

- Wetlands and mapped waterbodies.
- Hydrography, streams, rivers, ditches, and crossings.
- Land cover, impervious surface, forested area, disturbed area, and low-disturbance context.
- Soils, hydric soils, prime farmland, and related soil constraints.

Important cataloged categories that remain manual, semi-automated, or later-phase include:

- Species and habitat, including IPaC reports, critical habitat GIS, and state heritage placeholders.
- Cultural and historic resources, including public historic resources and restricted MDAH archaeological placeholders.
- Hazardous materials and regulated facilities.
- Community resources and socioeconomic context.
- Transportation, utilities, infrastructure, corridors, parcels, property age, and ROW context.
- Imagery and basemaps for visual review and report figures.

Flood hazard/floodplain data remains a valid optional source category, but it is secondary for the first useful implementation and should not crowd out water, land, and disturbance context. FEMA NFHL is now implemented as an optional explicit downloader.

Current local configuration files:

- Global catalog: `config/source_catalog.json`
- Project source registries: `projects/<project_id>/config/sources.json`
- Report profile source requirements: `config/report_profiles.json`
- Generated source acquisition manifests: `projects/<project_id>/source_acquisition/source_acquisition_manifest.json`
- Generated source acquisition downloads: `projects/<project_id>/source_acquisition/downloads/`
- Generated source status sets: `projects/<project_id>/source_status/source_status_set.json`
- Generated source inventories: `projects/<project_id>/source_inventory/source_inventory.json`
- Generated comparison tables: `projects/<project_id>/tables/comparison_tables.json`

## Source Acquisition Manifest

The source acquisition workflow compares the project input package, project source registry, report profile, and source catalog. It records whether each report-relevant source is:

- `provided_in_input`: tagged project input source layer exists and is registered where possible.
- `registered_local`: reviewer-supplied or manually registered local layer exists.
- `downloaded`: public source has been acquired into the workspace.
- `downloadable`: an implemented downloader can acquire it if the user requests downloads.
- `unsupported_download`: public data appears downloadable but no downloader exists yet.
- `gated`: restricted, sensitive, credentialed, or qualified-access source.
- `manual`: manual lookup/download or reviewer-supplied source.
- `optional`: not required for the selected report profile.
- `missing`: no supported source path exists.
- `failed`: a supported download attempt failed but did not block the rest of the workflow.

Live downloads are explicit only:

```powershell
.\.venv\Scripts\review-assist.exe resolve-source-gaps projects/trails
.\.venv\Scripts\review-assist.exe download-source projects/trails usfws_nwi_wetlands
.\.venv\Scripts\review-assist.exe download-source projects/trails usgs_nhd_hydrography
.\.venv\Scripts\review-assist.exe download-source projects/trails fema_nfhl_flood_hazard
.\.venv\Scripts\review-assist.exe prepare-sources projects/trails
.\.venv\Scripts\review-assist.exe prepare-sources projects/trails --include-optional-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources --include-optional-sources
```

Running `populate-for-review` without `--prepare-sources` preserves the local/no-live-download behavior. Running `prepare-sources` or `populate-for-review --prepare-sources` without `--include-optional-sources` downloads supported required sources only, so FEMA flood hazard remains optional unless directly requested.

## Source Tiers

### Tier 1: Automated Baseline Sources

Sources that are likely candidates for repeatable local or remote ingestion after validation.

Examples:

- USGS The National Map.
- USFWS NWI wetlands.
- FEMA National Flood Hazard Layer.
- USDA NRCS soils / SSURGO.
- USDA NAIP imagery.
- MRLC / NLCD land cover.
- U.S. Census TIGER/Line and ACS.
- MARIS / Mississippi Geospatial Clearinghouse.

Use:

- Deterministic spatial checks.
- Baseline map layers.
- Comparison tables.
- Source-backed review queue findings.

### Tier 2: Semi-Automated or Manual Review Sources

Sources that may support workflow but may require manual downloads, generated reports, reviewer input, or careful access handling.

Examples:

- USFWS IPaC project reports.
- MDWFP / Mississippi Natural Heritage Program context.
- MDEQ interactive maps and datasets.
- County GIS and parcel/tax assessor data.
- MDOT project documents or transportation layers.
- Existing environmental assessments or design plans.

Use:

- Supplemental findings.
- Reviewer-attached source files.
- Agency coordination context.
- Review items requiring human confirmation.

### Tier 3: Restricted or Reviewer-Supplied Sources

Sources that should not be automated until explicitly approved and access is understood.

Examples:

- MDAH archaeological records.
- MDAH GIS/HSMT restricted data.
- Consultant-provided cultural resource KMZ/GIS exports.
- Agency consultation letters.
- Internal hazardous materials reports.

Use:

- Reviewer-supplied context.
- Restricted-source review status.
- Findings with controlled visibility.

Important rule:

- Do not implement authentication, scraping, or restricted access workflows without explicit approval.

### Tier 4: Context-Only or Visual Review Sources

Sources useful for visual awareness but not authoritative by default.

Examples:

- Google Earth.
- Historical aerial imagery.
- GBIF biodiversity occurrence records.
- iDigBio specimen records.
- NatureServe species status context.

Use:

- Imagery-observed review items.
- Data gap discovery.
- Supplemental context.
- Human reviewer prompts.

Important rule:

- Visual observations remain review items until validated.

## Core National Sources

### USGS The National Map

Likely uses:

- Hydrography.
- Elevation.
- Transportation context.
- Structures and boundaries.
- Topographic and imagery basemaps.

Potential findings:

- Stream/river crossings.
- Waterbody context.
- Elevation/drainage context.
- Nearby structures or transportation context.

References:

- https://www.usgs.gov/the-national-map-data-delivery/gis-data-download
- https://www.usgs.gov/faqs/what-are-base-map-services-or-urls-used-national-map

Implementation status:

- `usgs_nhd_hydrography` is implemented as an explicit public downloader.
- The downloader queries The National Map NHD MapServer by project analysis bounds, using large-scale Flowline layer `6` and large-scale Area layer `9`.
- Downloaded hydrography is written as a combined GeoJSON under `projects/<project_id>/source_acquisition/downloads/` with normalized Review Assist source fields added while preserving original attributes.
- Successful downloads are registered as normal project `local_file` sources with `status: downloaded`, so the constraint engine, findings, hydrography crossing summary table, maps, report sections, and review queue consume the layer through the same path as reviewer-supplied data.
- Failed downloads remain nonfatal and propagate into source status, draft findings, report sections, and review queue caveat items.
- Existing reviewer-supplied local hydrography layers are preserved and not overwritten.

### USFWS National Wetlands Inventory

Likely uses:

- Wetland screening.
- Deepwater habitat screening.
- Wetland/waterbody map figures.

Potential findings:

- Wetland intersection.
- Wetland adjacency.
- Freshwater pond or waterbody context.
- Field verification needed.

Important caveat:

- NWI data does not define jurisdictional wetland boundaries.

Implementation status:

- `usfws_nwi_wetlands` is implemented as an explicit public downloader.
- The downloader queries the public Wetlands REST MapServer layer by project analysis bounds and writes GeoJSON under `projects/<project_id>/source_acquisition/downloads/`.
- Successful downloads are registered as normal project `local_file` sources with `status: downloaded`, so constraint analysis, findings, maps, tables, report sections, and review queue generation consume them through the existing source path.
- Failed downloads remain nonfatal and propagate into source status, draft findings, report sections, and review queue caveat items.
- Existing reviewer-supplied local NWI layers are preserved and not overwritten.

References:

- https://www.fws.gov/program/national-wetlands-inventory/data-download
- https://www.fws.gov/apps/program/national-wetlands-inventory/wetlands-mapper
- https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest

### FEMA National Flood Hazard Layer

Likely uses:

- Flood zone overlays.
- Floodway screening.
- Floodplain map figures.

Potential findings:

- Floodplain overlap.
- Floodway overlap.
- Floodplain review needed.
- Hydraulic/hydrologic review may be needed.

Important caveat:

- Effective, preliminary, and pending data have different official uses. Official-purpose map display requires appropriate basemap accuracy and interpretation.

References:

- https://hazards.fema.gov/femaportal/resources/flood_map_svc.htm
- https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer

Implementation status:

- `fema_nfhl_flood_hazard` is implemented as an optional explicit public downloader.
- The downloader queries the effective FEMA NFHL ArcGIS REST MapServer Flood Hazard Zones layer `28` by project analysis bounds and writes GeoJSON under `projects/<project_id>/source_acquisition/downloads/`.
- Successful downloads are registered as normal project `local_file` sources with `status: downloaded`, so constraint analysis, findings, flood hazard summary tables, source-context maps, report sections, and review queue generation consume them through the same path as reviewer-supplied data.
- FEMA remains optional unless the reviewer runs `download-source ... fema_nfhl_flood_hazard`, `prepare-sources --include-optional-sources`, or `populate-for-review --prepare-sources --include-optional-sources`.
- Failed FEMA downloads remain nonfatal and propagate into source status, draft findings, report sections, and review queue caveat items.
- Existing reviewer-supplied local FEMA/flood hazard layers are preserved and not overwritten.

Official caveats preserved in the app:

- This downloader uses effective NFHL data only; preliminary and pending NFHL services remain out of scope.
- Not all effective FIRMs have GIS data available.
- Official-purpose map display should use other map data that meets FEMA map accuracy standards.

### USDA NRCS Soils / SSURGO / Web Soil Survey

Likely uses:

- Soils context.
- Hydric soil screening.
- Prime farmland or other soil-related constraints where relevant.

Potential findings:

- Hydric soil context.
- Soil constraint context.
- Field verification or design review needed.

Reference:

- https://www.nrcs.usda.gov/resources/data-and-reports/web-soil-survey

### USDA NAIP Imagery

Likely uses:

- Aerial basemap.
- Imagery review.
- Disturbed-area context.
- Cropped project imagery.

Potential findings:

- Visible pond not present in source layer.
- Recent clearing visible.
- Disturbed corridor visible.
- New road or infrastructure visible.

Important caveat:

- Imagery observations are review items, not authoritative facts.

Reference:

- https://catalog.data.gov/dataset/national-agriculture-imagery-program-naip-imagery

### MRLC / NLCD Land Cover

Likely uses:

- Land cover classification.
- Developed vs. forested or low-disturbance context.
- Impervious surface context.

Potential findings:

- Existing disturbed corridor overlap.
- Forested area overlap.
- Developed land overlap.
- Low-disturbance area context.

Reference:

- https://www.mrlc.gov/data

### U.S. Census TIGER/Line and ACS

Likely uses:

- Census tracts/block groups.
- Demographics.
- Income and socioeconomic context.
- Community profile tables.

Potential findings:

- Demographic context by tract.
- Lower-income population context.
- Public engagement focus area.
- Transportation dependency context.

References:

- https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html
- https://www.census.gov/programs-surveys/acs/data.html

## Species, Habitat, and Ecology Sources

### USFWS IPaC

Likely uses:

- Project species list.
- Critical habitat context.
- Migratory bird and conservation context.
- Federal consultation support.

Potential findings:

- Federally listed species may occur in project area.
- Critical habitat overlap or nearby context.
- Agency coordination needed.
- Review/consultation document needed.

Important caveat:

- IPaC outputs may be report/document based and may need to be attached or entered as source material rather than treated as a simple GIS layer.

Reference:

- https://ipac.ecosphere.fws.gov/

### USFWS ECOS / Critical Habitat

Likely uses:

- Listed species status context.
- Critical habitat GIS boundaries.

Potential findings:

- Critical habitat intersection.
- Critical habitat nearby.
- Listed species context.

Reference:

- https://ecos.fws.gov/ecp/

### MDWFP / Mississippi Natural Heritage Program

Likely uses:

- State species of concern.
- Rare species and ecological communities context.
- Project-specific biological review support.

Potential findings:

- State species of concern context.
- Natural heritage review needed.
- Agency coordination needed.

Important caveat:

- Sensitive species data may be restricted or request-based.

Reference:

- https://www.mdwfp.com/ms-museum-nature-science/mississippi-natural-heritage-program/about-natural-heritage-database

### NOAA Fisheries

Likely uses:

- Coastal and marine listed species context where relevant.

Potential findings:

- NOAA-jurisdiction species context.
- Consultation needed for coastal/marine resources.

Reference:

- https://www.fisheries.noaa.gov/southeast/consultations/threatened-and-endangered-species-list-mississippi

### Supplemental Biodiversity Context

Candidate sources:

- NatureServe.
- GBIF.
- iDigBio.

Likely uses:

- Supplemental species occurrence/context review.
- Conservation status context.
- Data gap exploration.

Important caveat:

- These should not replace regulatory species consultation sources.

References:

- https://explorer.natureserve.org/
- https://www.gbif.org/
- https://www.idigbio.org/

## Mississippi and Local Sources

### MARIS / Mississippi State GIS

Likely uses:

- Statewide GIS layers.
- Community resources.
- Transportation context.
- Aerial photography.
- Hydrology and infrastructure context.
- Statewide reference layers.

Reference:

- https://www.mississippi.gov/Agencies/automated-resource-information-system-maris

### Mississippi Geospatial Clearinghouse

Likely uses:

- Statewide source discovery.
- Downloadable GIS datasets.
- Cross-agency source lookup.
- Metadata lookup.

Reference:

- https://www.ms.gov/Agencies/geospatial-clearinghouse-mgc

### MDEQ

Likely uses:

- Interactive maps.
- Public water supply context.
- UST/hazardous site context.
- Water quality context.
- Boreholes, mines, geology, dams, and related state environmental context.

Potential findings:

- Public water supply well nearby.
- UST or hazardous materials site nearby.
- Water quality review needed.
- MDEQ coordination likely.

Important caveat:

- Interactive map outputs may need validation, manual export, or reviewer-attached source documents.

Reference:

- https://www.mdeq.ms.gov/about-mdeq/interactive-maps/

### MDAH Public and Restricted Cultural Resources

Public context:

- Historic Resources Inventory.
- Public historic property context.
- National Register context.
- County tax parcel or property-age clues.

Restricted context:

- Archaeological records.
- HSMT/GIS data.
- Consultant-provided KMZ/GIS exports.
- Agency consultation context.

Potential findings:

- Public historic resource nearby.
- Property older than 50 years.
- Archaeological lookup required.
- Restricted cultural review needed.
- SHPO/MDAH coordination likely.

Important caveat:

- Keep public historic context separate from restricted archaeological data.
- Restricted data may require qualified users, subscriptions, appointments, or reviewer-supplied files.
- MDAH restricted integration is a placeholder/stub only.

References:

- https://www.apps.mdah.ms.gov/Public/search.aspx
- https://mdah.ms.gov/historic-preservation/archaeological-records-research

### County GIS / Parcel and Tax Assessor Data

Likely uses:

- Property age screening.
- Ownership context.
- Local facility verification.
- ROW/access context.

Potential findings:

- Property older than 50 years may require review.
- ROW acquisition may trigger cultural review.
- Local resource or access issue identified.

Important caveat:

- County data availability, licensing, schemas, and freshness vary.

### MDOT and Local Transportation Sources

Likely uses:

- Roads.
- ROW context.
- Recent project plans.
- Existing environmental assessments.
- New alignments not visible in stale imagery.

Potential findings:

- Existing disturbed transportation corridor overlap.
- New roadway/context update needed.
- Design/ROW coordination needed.

## Hazardous Materials and Regulated Facility Sources

### EPA NEPAssist

Likely uses:

- Environmental screening reference.
- Cross-source project context.

Potential findings:

- Screening context item.
- Source discovery for other EPA datasets.

Reference:

- https://www.epa.gov/nepa/nepassist

### EPA Envirofacts

Likely uses:

- Facilities and regulated sites.
- Waste, air, water, toxic release, and compliance context.

Potential findings:

- Regulated facility nearby.
- Hazardous materials review item.
- Agency coordination may be needed.

Reference:

- https://www.epa.gov/enviro/envirofacts-overview

### EPA ECHO

Likely uses:

- Compliance and enforcement records.
- NPDES and facility data.

Potential findings:

- Discharge or regulated facility nearby.
- Compliance context.

Reference:

- https://echo.epa.gov/tools/data-downloads

### Mississippi State Oil and Gas Board

Likely uses:

- Oil/gas well context.

Potential findings:

- Oil/gas well near project area.
- Excavation or coordination review needed.

Reference:

- https://www.ogb.state.ms.us/

## Infrastructure and Community Sources

### BTS National Transportation Atlas Database

Likely uses:

- Transportation networks and facilities.
- National transportation context.

Reference:

- https://www.bts.gov/ntad

### FAA Aeronautical Data

Likely uses:

- Airport proximity context.
- Aviation-related constraints where relevant.

Reference:

- https://www.faa.gov/data/aero_data

### HIFLD / Infrastructure Data

Likely uses:

- Hospitals.
- Schools.
- Fire stations.
- Utilities.
- Infrastructure context.

Important caveat:

- Public availability and access conditions should be validated before relying on HIFLD as a repeatable source.

Reference:

- https://www.dhs.gov/gmo/hifld

### Local Government and Open Data Portals

Likely uses:

- Fire/EMS.
- Schools.
- Parks.
- Government buildings.
- Utilities.
- Local plans and capital projects.

Important caveat:

- These sources are valuable but inconsistent across jurisdictions.

## Aerial Imagery and Basemap Sources

Candidate imagery sources may include NAIP, state orthophotos, county imagery, ArcGIS basemaps, USGS imagery services, and Google Earth visual review context.

Potential use:

- Basemap and map figure context.
- Cropped project imagery.
- Visual QC against stale GIS layers.
- Imagery-observed review items.

Important limitations:

- Imagery observations should remain review items, not authoritative facts.
- Source, capture date, tile/service, attribution, and licensing constraints must be tracked where available.
- Do not implement Google API usage without explicit approval because Maps Static API requires API keys and billing.
- Google imagery requires visible attribution to Google Earth and third-party imagery providers when used.

References:

- NAIP: https://catalog.data.gov/dataset/national-agriculture-imagery-program-naip-imagery
- USGS imagery services: https://www.usgs.gov/faqs/what-are-base-map-services-or-urls-used-national-map
- ArcGIS basemap styles: https://developers.arcgis.com/documentation/mapping-and-location-services/mapping/basemaps/introduction-basemap-styles-service/
- Google Earth Studio attribution: https://earth.google.com/studio/docs/en_gb/attribution/
- Google Maps Static API: https://developers.google.com/maps/documentation/maps-static/start

## Best-Case First Stack for Trails Project

For the initial trails example, prioritize:

1. Trail alternatives KMZ.
2. Project footprint/study area if available.
3. USFWS NWI wetlands.
4. USGS hydrography / NHD or successor datasets.
5. FEMA NFHL flood zones/floodways.
6. NAIP or MARIS/state imagery.
7. NLCD land cover.
8. NRCS soils.
9. USFWS IPaC project species list.
10. USFWS critical habitat GIS.
11. MDWFP / Mississippi Natural Heritage context.
12. MDAH public Historic Resources Inventory.
13. Manual placeholder for restricted MDAH archaeological/HSMT review.
14. MDEQ UST/hazardous materials/public water supply/water quality context.
15. EPA Envirofacts/ECHO regulated facility context.
16. Census TIGER/ACS demographic context.
17. County parcel/tax assessor data for property age and ROW context.
18. MDOT/local transportation context for recent roads, ROW, and project plans.

## How Sources Feed the Review Queue

Each source-backed output should become a review queue item or support one.

Examples:

- NWI intersection -> wetland finding card.
- NHD crossing -> stream crossing finding card.
- FEMA floodway overlap -> floodplain/floodway finding card.
- IPaC report attached -> species context card.
- MDAH restricted data unavailable -> cultural review required card.
- NAIP discrepancy -> imagery review item.
- Census table -> socioeconomic table preview card.
- MDEQ UST site nearby -> contamination risk finding card.
- Map export -> map preview card with source/provenance notes.

Nothing should skip the review queue.

## Source Registry Fields

Current source registry entries include:

- `source_id`
- `access_method`
- `enabled`
- `path`
- `role`
- `buffer_feet`
- `notes`
- `status`
- optional `metadata`

The optional `metadata` object currently supports:

- `citation`
- `license_or_terms`
- `attribution`
- `published_date`
- `metadata_date`
- `access_date`
- `source_url`
- `review_notes`

Source inventory generation merges those project-supplied metadata fields with the global catalog, source status, and local file inspection. Missing metadata should remain blank rather than being invented.

Future source registry or inventory records may also need:

- `coverage`
- `refresh_frequency`
- `requires_credentials`
- authoritative source update cadence.

## Source Validation Questions

- What is the authoritative source for each layer?
- What access restrictions apply?
- How current is the data?
- What geographic coverage is available?
- What usage or redistribution limits apply?
- What attribution is required in maps or reports?
- Is the source suitable for deterministic analysis or only visual review?
- How should source provenance be cited in draft findings?
- How should stale, missing, restricted, or unavailable data be represented in findings?
- Which sources should be automated first for the trails prototype?
- What source download/cache location should the desktop app use?
- Should the app ship with a starter registry of URLs or require project-specific source folders?
- What level of Google Earth/Google Maps usage is permitted in draft or final deliverables?
- How should IPaC reports be generated, stored, and cited?
- How should restricted MDAH review be represented without exposing sensitive data?
- Which local/county data sources are required for the first Mississippi trail report?
