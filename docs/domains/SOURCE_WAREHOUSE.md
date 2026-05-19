# Source Warehouse

The root `sources/` directory is a local, ignored source warehouse for manually seeded public data. Bulk raw files remain local, while `source_manifest.json` files and `sources/source_warehouse_manifest.json` describe the expected layout.

Stable source IDs are the app-facing contract. Agency/download folder names are preserved under each source's `raw/` directory for provenance.

## Layout Pattern

```text
sources/
  source_warehouse_manifest.json
  environmental/<source_id>/raw/<agency_download_folder>/
  hydrology/<source_id>/raw/<agency_download_folder>/
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

## Current Seeded Groups

- Environmental and regulated facilities: FEMA NFHL flood hazard, EPA FRS, MARIS brownfields, NPDES, landfills, Superfund, TRI, USTs, and Mississippi oil/gas wells.
- Hydrology: specific NHD flowlines, waterbodies, and other areas. The existing live-download rollup `usgs_nhd_hydrography` remains available.
- Conservation/public lands: national wildlife refuges, NRCS easements, and MARIS conservation/recreation lands.
- Existing baseline sources: NWI wetlands, Critical Habitat, SSURGO soils, MDOT/rail, public cultural context, community facilities, utility infrastructure, boundaries, and MARIS/NAIP basemap provenance.

Raw source paths are never sent to GPT-bound evidence payloads. Source provenance, materialization status, empty project intersections, missing raw paths, and non-renderable imagery remain explicit workflow/status facts for human review.
