# Data Sources

This document defines the practical source stack for building the best-case source/context package for environmental and contextual review reports.

The current baseline includes a local source catalog, project source registries, source status sets, source warehouse manifests, local source materialization manifests, source acquisition manifests, and source inventory/provenance artifacts so reviewer-supplied, manually downloaded, locally warehoused, explicitly downloaded public layers, or explicitly materialized project-local basemap sidecars can be registered, inspected, and checked. `environmental_constraints_example` is the default source-requirement profile for alternatives review, while `environmental_constraints_basic` and `location_screening_basic` remain available for explicit use. USFWS NWI wetlands, USGS NHD hydrography, USFWS Critical Habitat, EPA/ECHO regulated facilities, and FEMA NFHL effective flood hazard zones are implemented public downloaders. The local Mississippi source warehouse now uses stable app-facing source IDs with raw agency/download folder names preserved under each source's `raw/` folder; its index lives at `sources/source_warehouse_manifest.json`. Seeded local materializers cover NWI wetlands, Critical Habitat, SSURGO soils, MDOT/rail transportation, utilities, administrative/boundary context, public cultural context, community facilities, conservation/recreation lands, FEMA flood hazard, specific NHD flowline/waterbody/area layers, MDEQ/MARIS public water supply wells, EPA FRS, MARIS brownfields, NPDES, landfills, Superfund, TRI, USTs, oil/gas wells, MDEQ 2024 303(d) impaired waters/TMDL-complete layers, national wildlife refuges, and NRCS easements. Broad IDs such as `usgs_nhd_hydrography` and `epa_envirofacts_echo` are live download rollups, not required physical warehouse folders when specific seeded or reviewer-supplied local layers satisfy the category. `mdeq_environmental_context` is manual residual context. `materialize-naip-basemap` is implemented as an explicit, optional, AOI-bounded renderable basemap sidecar workflow, not as a deterministic source-layer materializer. Other sources below remain candidates requiring validation for coverage, licensing, access method, update cadence, accuracy, attribution, and fitness for use.

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
- Track local source warehouse materialization where statewide or bulk datasets are clipped into project-ready files.
- Track source gap/acquisition status in the workspace source acquisition manifest.
- Preserve source uncertainty and stale-data warnings.
- Prefer deterministic GIS/source checks before AI narrative synthesis.
- Do not add paid services, credentials, or restricted integrations without explicit approval.
- Treat imagery-observed features as review items until validated by a human reviewer.
- Send every source-backed output into the review queue before export.

## Source Status Set

The canonical workflow resolves required report source categories into a `SOURCE_STATUS_SET`.

Effective source status is the report-facing status after reconciliation, not a raw copy of acquisition history. The resolver gives precedence to current project-local materialized layers, registered local files, and valid warehouse availability before it treats an older download failure as a report caveat. A failed historical acquisition remains available in source-acquisition/debug artifacts, but it should not produce a `source_not_downloaded` report/GPT caveat when the same `source_id` is currently available through a valid local or materialized source path.

Project-registered source categories that are not part of the base report profile can still appear in the source status set when the workspace has an enabled project source for that category. This keeps project-local materialized context such as `mdeq_303d_impaired_waters` visible to figures, evidence, and review diagnostics without making the broad report profile require that category for every project.

Sprint 5.3 also records a policy-derived `section_source_needs` manifest inside `source_status/source_status_set.json`. Each section record traces `config/report_section_policy.json` source categories and source refs to current catalog IDs, effective source statuses, and one of these source need classes: `available_materialized`, `warehouse_available_not_materialized`, `acquisition_candidate`, `optional`, `manual_reviewer_supplied`, `restricted_authorized_reviewer_supplied`, `public_coarse_screening_context`, `deferred`, or `deprecated_legacy`. These classes explain report-facing source truth; they do not start downloads, add query buffers, or imply final regulatory fitness.

Suggested statuses:

- `provided_locally`: user supplied a local layer, document, report, or map.
- `downloadable`: public data appears available but is not downloaded yet.
- `downloaded`: public data has been acquired for the workspace.
- `local_materialized`: local warehouse data has been clipped into the workspace.
- `failed`: a supported acquisition attempt failed and should remain visible as a caveat/review item.
- `gated`: access requires credentials, qualified access, agency request, or restricted handling.
- `restricted`: source requires restricted, sensitive, or qualified-access handling.
- `manual`: source requires manual lookup, manual download, a document attachment, or reviewer-supplied material.
- `unimplemented`: a public or repeatable source is identified, but no downloader/materializer is implemented yet.
- `stubbed`: a placeholder exists so report sections can include a review requirement or caveat.
- `selected_not_renderable`: a basemap/context source is selected as provenance but cannot be rendered without a preconverted sidecar.
- `warehouse_available`: local warehouse data is present but has not yet been clipped and registered for the project.
- `present_not_materialized`: local warehouse/source material is present but not yet configured as analysis-ready materialization.
- `missing`: expected source material is not available.
- `optional`: useful context but not required for the selected report profile.
- `needs_review`: source status or fitness for use requires reviewer confirmation.

Missing, failed, gated/restricted, manual, unimplemented, selected-not-renderable, and stubbed categories should not fail the workflow by default. They should create review queue items, uncertainty flags, and report caveats so the reviewer can decide how to proceed.

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
- Local source materializer config: `config/local_source_materializers.json`
- Local source warehouse index: `sources/source_warehouse_manifest.json`
- Per-source warehouse manifests: `sources/<warehouse_group>/<source_id>/source_manifest.json`
- Project source registries: `projects/<project_id>/config/sources.json`
- Report profile source requirements: `config/report_profiles.json`
- Generated input package classifications: `projects/<project_id>/context/input_package.json`
- Generated project area and basemap provenance: `projects/<project_id>/context/project_area.json`
- Generated NAIP basemap sidecars and provenance: `projects/<project_id>/basemaps/naip/`
- Generated source materialization manifests: `projects/<project_id>/source_materialization/local_source_materialization_manifest.json`
- Generated project-ready materialized layers: `projects/<project_id>/layers/<source_id>/<source_id>.geojson`
- Generated source acquisition manifests: `projects/<project_id>/source_acquisition/source_acquisition_manifest.json`
- Generated source acquisition downloads: `projects/<project_id>/source_acquisition/downloads/`
- Generated source status sets: `projects/<project_id>/source_status/source_status_set.json`
- Generated source inventories: `projects/<project_id>/source_inventory/source_inventory.json`
- Generated comparison tables: `projects/<project_id>/tables/comparison_tables.json`
- Generated comparison-unit constraints: `projects/<project_id>/constraints/comparison_unit_constraints.json`
- Generated exact deliverable tables: `projects/<project_id>/deliverable/tables.json`

## Source Acquisition Manifest

The source acquisition workflow compares the project input package, project source registry, report profile, and source catalog. It records whether each report-relevant source is:

- `provided_in_input`: tagged project input source layer exists and is registered where possible.
- `registered_local`: reviewer-supplied or manually registered local layer exists.
- `local_materialized`: local warehouse data is materialized for this workspace.
- `downloaded`: public source has been acquired into the workspace.
- `downloadable`: an implemented downloader can acquire it if the user requests downloads.
- `unsupported_download`: public data appears downloadable but no downloader exists yet.
- `gated`: restricted, sensitive, credentialed, or qualified-access source.
- `manual`: manual lookup/download or reviewer-supplied source.
- `stubbed`: setup exists, but a required key/source/document is missing; for Census this includes missing `CENSUS_API_KEY`.
- `optional`: not required for the selected report profile.
- `missing`: no supported source path exists.
- `failed`: a supported download attempt failed but did not block the rest of the workflow.

Live downloads are explicit only:

```powershell
.\.venv\Scripts\review-assist.exe resolve-source-gaps projects/trails
.\.venv\Scripts\review-assist.exe download-source projects/trails usfws_nwi_wetlands
.\.venv\Scripts\review-assist.exe download-source projects/trails usgs_nhd_hydrography
.\.venv\Scripts\review-assist.exe download-source projects/trails usfws_critical_habitat
.\.venv\Scripts\review-assist.exe download-source projects/trails epa_envirofacts_echo
.\.venv\Scripts\review-assist.exe download-source projects/trails fema_nfhl_flood_hazard
.\.venv\Scripts\review-assist.exe prepare-sources projects/trails
.\.venv\Scripts\review-assist.exe prepare-sources projects/trails --include-optional-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --prepare-sources --include-optional-sources
```

Running `populate-for-review` without `--prepare-sources` preserves the local/no-live-download behavior. Running `prepare-sources` or `populate-for-review --prepare-sources` without `--include-optional-sources` downloads supported required sources only. FEMA flood hazard remains optional under `environmental_constraints_basic`, but it is required by the default `environmental_constraints_example` alternatives-review profile. The `populate-for-review --include-optional-sources` flag is valid only when paired with `--prepare-sources`.

The Sprint 2.1 catalog also exposes review-visible manual or stub entries for IPaC report context, state heritage review, restricted archaeology, MDEQ/manual environmental context, public water supply wells, airports, oil wells, local businesses/economic nodes, hazardous materials support reports, and agency consultation letters. These entries are not automated determinations; they keep the missing or reviewer-supplied source need visible for later deliverable tables, figures, attachments, caveats, and review items.

The broad downloader IDs in the command examples are acquisition conveniences. They do not imply that a matching root `sources/<group>/<source_id>/` folder must exist, and they should not override more specific seeded warehouse IDs or reviewer-supplied project-local layers.

Report/GPT-facing caveats use effective status. Logical rollups such as `usgs_nhd_hydrography` and `epa_envirofacts_echo` are considered satisfied for caveat purposes when the relevant specific project-local layers are available. `mdeq_environmental_context` is not a logical rollup; it remains a manual residual context bucket for MDEQ material not represented by specific seeded source IDs. Optional, public/coarse, or visual-only context such as Google Earth visual review context should not appear as an alarming missing authoritative source when NAIP/MARIS/project-local basemap context is available. Manual and restricted sources remain visible as reviewer-supplied or restricted limitations rather than download failures.

The wetlands/waterbodies deliverable table has source-specific metric scoping. `Stream Crossings` is a crossing-event count from canonical `usgs_nhd_flowlines` only; `usgs_nhd_hydrography` remains a logical/download rollup for acquisition and caveat status, and `usgs_nhd_waterbodies` / `usgs_nhd_other_areas` remain hydrography context rather than stream-crossing count sources. The NWI wetland class columns are counted from `usfws_nwi_wetlands` only. This prevents hydrography category membership or logical rollups from changing the table metric contract.

## Local Source Materialization

The local materializer uses ignored root `sources/` storage as a Mississippi source warehouse. Stable source IDs are the app-facing folder names; raw agency/download names are preserved under `raw/` for provenance. The warehouse index and per-source manifests describe expected local layout without tracking bulk source files in Git. The materializer reads configured statewide or bulk datasets, clips them to the project analysis bounds, writes small project-ready GeoJSON files under `projects/<project_id>/layers/<source_id>/`, and registers those files as real `local_file` sources with `status: local_materialized`.

Configured materializers:

- `usfws_nwi_wetlands`: `sources/wetlands/usfws_nwi_wetlands/raw/MS_geopackage_wetlands/MS_geopackage_wetlands.gpkg`, layer `MS_Wetlands`.
- `usfws_critical_habitat`: `sources/ecology/usfws_critical_habitat/raw/critical_species_habitat_all_layers/CRITHAB_LINE.shp` plus `crithab_poly.shp`.
- `usda_nrcs_ssurgo_soils`: `sources/soils/usda_nrcs_ssurgo_soils/raw/wss_gsmsoil_MS_10_13_2016/spatial/gsmsoilmu_a_ms.shp`.
- `mdot_transportation_context`: roads, designated highways, railroad networks, railroad crossings, railroad bridges, and railroad junctions from `sources/transportation/mdot_transportation_context/raw/`.
- `local_utility_infrastructure`: electric substations and transmission lines from `sources/infrastructure/local_utility_infrastructure/raw/`.
- `maris_boundary_context`: county boundaries, state boundary, and detailed coastline from `sources/boundaries/maris_boundary_context/raw/`; county boundaries feed report study-area county names.
- `maris_public_cultural_context`: public cemeteries, National Register sites, and tribal land context from `sources/cultural/maris_public_cultural_context/raw/`; restricted archaeology remains manual/restricted.
- `maris_community_facilities`: communities, fire stations, and recreational facilities from `sources/community/maris_community_facilities/raw/`.
- `maris_conservation_recreation_lands`: easement areas, state parks, and wildlife management areas from `sources/conservation/maris_conservation_recreation_lands/raw/`.
- `fema_nfhl_flood_hazard`: seeded Mississippi DFIRM/FEMA flood hazard polygons from `sources/environmental/fema_nfhl_flood_hazard/raw/`.
- `usgs_nhd_flowlines`, `usgs_nhd_waterbodies`, and `usgs_nhd_other_areas`: specific seeded NHD layers from `sources/hydrology/`; the live downloader rollup `usgs_nhd_hydrography` remains available but is not a physical seeded source folder.
- `mdeq_public_water_supply_wells`: MDEQ/MARIS November 2024 Public Water Supply well points filtered from `MS_WaterWells_Nov2024` where `Beneficial` equals `PS`; source metadata states the data is a timestamp and not necessarily current.
- `epa_frs_facilities_ms`, `maris_brownfields`, `maris_npdes_facilities`, `maris_solid_waste_landfills`, `maris_superfund_sites`, `maris_tri_facilities`, `maris_underground_storage_tanks`, and `mississippi_oil_gas_wells`: seeded regulated facility/contamination context layers from `sources/environmental/`.
- `mdeq_303d_impaired_waters`: MDEQ 2024 active 303(d) impaired waters and TMDL-complete line/polygon layers from `sources/water_quality/`; this preserves original MDEQ fields but does not derive watershed context without HUC/NHD layers.
- `usfws_national_wildlife_refuges` and `usda_nrcs_easements`: seeded conservation/public lands context from `sources/conservation/`.

Commands:

```powershell
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usfws_nwi_wetlands
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usfws_critical_habitat
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usda_nrcs_ssurgo_soils
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails fema_nfhl_flood_hazard
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usgs_nhd_flowlines
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usgs_nhd_waterbodies
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails usgs_nhd_other_areas
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails epa_frs_facilities_ms
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_brownfields
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_npdes_facilities
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_underground_storage_tanks
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails mdeq_public_water_supply_wells
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails mdeq_303d_impaired_waters
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails mdot_transportation_context
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_boundary_context
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_public_cultural_context
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_community_facilities
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails maris_conservation_recreation_lands
.\.venv\Scripts\review-assist.exe materialize-local-source projects/trails local_utility_infrastructure
.\.venv\Scripts\review-assist.exe materialize-local-sources projects/trails
.\.venv\Scripts\review-assist.exe materialize-naip-basemap projects/trails
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --materialize-local-sources
.\.venv\Scripts\review-assist.exe populate-for-review projects/trails --materialize-naip-basemap
.\.venv\Scripts\review-assist.exe build-mvp-deliverable projects/trails --materialize-local-sources
```

All-source materialization treats missing warehouse files as nonfatal manifest warnings. Single-source materialization fails clearly when the requested warehouse source cannot be read. Existing reviewer-supplied local sources are preserved unless `--replace` is explicitly used. Source status can report local warehouse data as present but not yet materialized, so seeded public sources do not silently appear missing. Materialization runs before public source downloads when both `--materialize-local-sources` and `--prepare-sources` are used, so local warehouse data can satisfy source gaps before the app attempts live downloads.

NAIP basemap materialization is separate from local source materialization because it produces visual basemap sidecars, not project-ready vector layers for deterministic constraint checks. `materialize-naip-basemap` queries Microsoft Planetary Computer NAIP STAC by project analysis bounds, selects intersecting COG tiles deterministically, reads only the project-relevant window, and writes `projects/<project_id>/basemaps/naip/<year>/naip_project_basemap.tif` plus JSON provenance. The command reuses an existing sidecar unless `--refresh` or `--force` is supplied. It enforces tile, pixel, and timeout limits and records controlled failure status when optional imagery dependencies, network access, or source coverage are unavailable. `populate-for-review --materialize-naip-basemap` is opt-in and failure-tolerant; plain populate does not acquire imagery.

Materialized GeoJSON preserves original source attributes and adds normalized `review_assist_*` fields for source id/name/category, source layer, feature label/type/subtype/original id/date/quality/citation, and data authenticity. GPT drafting still receives only bounded evidence summaries; raw warehouse paths, full features, raw geometries, and root `sources/` paths are withheld from GPT payloads.

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

- `usgs_nhd_hydrography` is implemented as an explicit public downloader rollup, not as a required physical warehouse layer.
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

- `fema_nfhl_flood_hazard` is implemented as an explicit public downloader.
- The downloader queries the effective FEMA NFHL ArcGIS REST MapServer Flood Hazard Zones layer `28` by project analysis bounds and writes GeoJSON under `projects/<project_id>/source_acquisition/downloads/`.
- Successful downloads are registered as normal project `local_file` sources with `status: downloaded`, so constraint analysis, findings, flood hazard summary tables, source-context maps, report sections, and review queue generation consume them through the same path as reviewer-supplied data.
- FEMA remains optional under `environmental_constraints_basic`, but is required by the default `environmental_constraints_example` alternatives-review profile.
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
- The current basemap service indexes local MARIS/NAIP 2025 county folders under `sources/aerial_base_maps/maris_naip_2025`, records matching county source paths and renderability status in `project_area.json`, exposes source status detail under `maris_naip_2025_imagery`, and treats `.sid` files as source/provenance unless a renderable `.tif`, `.tiff`, or `.png` sidecar exists.
- This indexing does not perform MrSID decoding, raster rendering, imagery interpretation, source-layer materialization, or map generation.

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

Implementation status:

- `census_tiger_acs` is cataloged as metadata-only setup for future demographics table generation.
- `CENSUS_API_KEY` is the configured environment variable convention for future ACS API calls.
- 2024 ACS 5-year is the declared default future dataset.
- Missing `CENSUS_API_KEY` creates visible stub/source-status detail and uncertainty flags rather than crashing source status, acquisition, inventory, or populate workflows.
- Sprint 2.2 deliverable table generation can read a registered local `census_tiger_acs` polygon/table source with tract/community labels and ACS-like fields, then populate the income and demographic-composition table targets.
- If no registered local Census source is available, or Census setup is otherwise unavailable, the demographic deliverable tables are explicit review-needed stubs. Live Census API/TIGER acquisition and full margin-of-error handling remain unimplemented.

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

Current implementation status:

- `usfws_critical_habitat` is an implemented explicit public downloader.
- The downloader queries the USFWS Critical Habitat FeatureServer final layer `0` and proposed layer `2` by project analysis bounds and writes GeoJSON under `projects/<project_id>/source_acquisition/downloads/`.
- Successful downloads are registered as normal `local_file` sources with `status: downloaded`.
- Downloaded records preserve original attributes and add normalized Review Assist source/layer/label/type/subtype/original-id/date/quality/citation fields.
- Critical habitat constraints feed protected species/critical habitat findings, a critical habitat summary table, source-context maps, report sections, and review queue items.
- Critical habitat GIS is screening context only. It is not the legal boundary source, not a project species list, and not a replacement for IPaC or agency consultation.

Reference:

- https://ecos.fws.gov/ecp/
- https://services.arcgis.com/QVENGdaPbd4LUkLV/ArcGIS/rest/services/USFWS_Critical_Habitat/FeatureServer

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
- Public/coarse cultural context, including a future OpenContext/DINAA-style POC layer if approved, must remain separate from authorized or reviewer-supplied MDAH archaeological records.

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
- https://echo.epa.gov/tools/map-service
- https://echogeo.epa.gov/arcgis/rest/services/ECHO/Facilities/MapServer

Implementation status:

- `epa_envirofacts_echo` is implemented as an explicit public downloader rollup, not as a required physical warehouse layer.
- The downloader queries the public ECHO Facilities MapServer `All ECHO Facilities` layer `0` by project analysis bounds and writes GeoJSON under `projects/<project_id>/source_acquisition/downloads/`.
- Successful downloads are registered as normal project `local_file` sources with `status: downloaded`, so constraint analysis, findings, regulated facility summary tables, source-context maps, report sections, and review queue generation consume them through the same path as reviewer-supplied data.
- Downloaded records preserve original ECHO attributes and add normalized Review Assist source/layer/label/type/subtype/original-id/date/quality/citation fields where available.
- ECHO context is screening-level only. Facility locations, program flags, compliance status, and Detailed Facility Report links require reviewer QC and do not replace environmental due diligence, hazardous materials review, field verification, or professional judgment.

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
- The current local MARIS/NAIP workflow records selected `.sid` paths separately from renderable sidecars and marks `.sid`-only selections as `selected_not_renderable`.
- Project-local NAIP sidecars created by `materialize-naip-basemap` are recorded under `basemaps/naip/`, discovered by `project_area.json`, and preferred by deliverable figures when present.
- Do not implement Google API usage without explicit approval because Maps Static API requires API keys and billing.
- Google imagery requires visible attribution to Google Earth and third-party imagery providers when used.

References:

- NAIP: https://catalog.data.gov/dataset/national-agriculture-imagery-program-naip-imagery
- USGS imagery services: https://www.usgs.gov/faqs/what-are-base-map-services-or-urls-used-national-map
- ArcGIS basemap styles: https://developers.arcgis.com/documentation/mapping-and-location-services/mapping/basemaps/introduction-basemap-styles-service/
- Google Earth Studio attribution: https://earth.google.com/studio/docs/en_gb/attribution/
- Google Maps Static API: https://developers.google.com/maps/documentation/maps-static/start

## Best-Case First Stack for the Sample Alternatives Project

For the current sample alternatives fixture, prioritize:

1. Project alternatives/features KMZ.
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
- Which sources should be automated first for the sample alternatives workflow?
- What source download/cache location should the local web app workflow use?
- Should the app ship with a starter registry of URLs or require project-specific source folders?
- What level of Google Earth/Google Maps usage is permitted in draft or final deliverables?
- How should IPaC reports be generated, stored, and cited?
- How should restricted MDAH review be represented without exposing sensitive data?
- Which local/county data sources are required for the first Mississippi environmental constraints report?
