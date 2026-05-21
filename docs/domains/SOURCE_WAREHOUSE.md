# Source Warehouse

The root `sources/` directory is a local, ignored source warehouse for manually seeded public data. Bulk raw files remain local, while `source_manifest.json` files and `sources/source_warehouse_manifest.json` describe the expected layout.

Stable source IDs are the app-facing contract. Agency/download folder names are preserved under each source's `raw/` directory for provenance.

## Layout Pattern

```text
sources/
  source_warehouse_manifest.json
  environmental/<source_id>/raw/<agency_download_folder>/
  hydrology/<source_id>/raw/<agency_download_folder>/
  water_quality/<source_id>/raw/<agency_download_folder>/
  conservation/<source_id>/raw/<agency_download_folder>/
  wetlands/<source_id>/raw/<agency_download_folder>/
  ecology/<source_id>/raw/<agency_download_folder>/
```

Existing MARIS/NAIP county imagery remains under `sources/aerial_base_maps/maris_naip_2025/` because the basemap indexer already uses that county-folder convention. Its manifest marks MrSID files as provenance/rendering context, not deterministic analysis input.

## Materialization Contract

`config/local_source_materializers.json` maps stable source IDs to warehouse raw paths. Materialization clips configured warehouse layers into:

```text
projects/<project_id>/layers/<source_id>/<source_id>.geojson
```

The project registry is then updated with `status: local_materialized`. Existing reviewer-supplied or previously materialized local project sources are preserved unless `--replace` is explicitly used.

## Logical Download Rollups

Not every catalog source ID is a physical warehouse source. `usgs_nhd_hydrography` and `epa_envirofacts_echo` are live public downloader rollups that can create project-local downloaded layers under `projects/<project_id>/source_acquisition/`. They should not be required as root `sources/` warehouse folders when specific seeded layers such as `usgs_nhd_flowlines`, `usgs_nhd_waterbodies`, `usgs_nhd_other_areas`, `epa_frs_facilities_ms`, or MARIS regulated facility layers already satisfy the review category.

`mdeq_environmental_context` is a manual residual context bucket for reviewer/source-agency material, not an automated warehouse layer.

Effective source status reconciliation treats the logical rollups as satisfied for report-facing caveats when their specific project-local/materialized child layers are available. Acquisition manifests may still record older download attempts for the rollup or for the same source ID; those records remain debugging/history, not report limitations unless no current local, materialized, or warehouse-available replacement exists. The manual residual `mdeq_environmental_context` bucket is intentionally excluded from rollup satisfaction so specific facility layers do not hide a separate manual/source-agency context need.

The source status artifact also records `section_source_needs`, a policy-derived trace from report sections to catalog/profile/warehouse truth. Warehouse-present sources are classified as `warehouse_available_not_materialized` until materialized into a project layer; logical rollups satisfied by current child layers are classified as `available_materialized`; public/coarse cultural or visual context remains distinct from restricted or reviewer-supplied material.

## Current Seeded Groups

- Environmental and regulated facilities: FEMA NFHL flood hazard, EPA FRS, MARIS brownfields, NPDES, landfills, Superfund, TRI, USTs, and Mississippi oil/gas wells.
- Hydrology: specific NHD flowlines, waterbodies, other areas, and MDEQ/MARIS November 2024 public water supply wells. The existing live-download rollup `usgs_nhd_hydrography` remains available as a downloader path, not a seeded physical source folder.
- Water quality: MDEQ 2024 303(d) impaired waters and TMDL-complete line/polygon layers. Watershed context is not derived from these layers; pair them with HUC/NHD layers when hydrologic context is needed.
- Conservation/public lands: national wildlife refuges, NRCS easements, and MARIS conservation/recreation lands.
- Existing baseline sources: NWI wetlands, Critical Habitat, SSURGO soils, MDOT/rail, public cultural context, community facilities, utility infrastructure, boundaries, and MARIS/NAIP basemap provenance.

Raw source paths are never sent to GPT-bound evidence payloads. Source provenance, materialization status, empty project intersections, missing raw paths, and non-renderable imagery remain explicit workflow/status facts for human review.
