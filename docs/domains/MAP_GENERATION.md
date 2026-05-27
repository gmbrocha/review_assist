# Map Generation

This document captures current and future map and figure generation workflows. A vector-only draft map baseline is implemented for legacy audit/context maps, and Sprint 2.3 adds matrix-backed deliverable figure artifacts. Project area generation records NAIP/MARIS basemap provenance and renderability status; deliverable figures can use project-local NAIP GeoTIFF render assets and supported `.png`, `.jpg`, `.jpeg`, `.tif`, or `.tiff` rasters, while real MrSID `.sid`/`.sdw` payloads are not retained as active Review Assist assets. Production cartography, paid/proprietary basemap APIs, PDF/SVG map sheets, and final cartographic styling remain future work.

## Purpose

The system should eventually generate repeatable, report-ready static figures and review overlays for project areas and alternatives.

Expected outputs:

- Overall project maps.
- Resource-specific maps.
- Panel index maps.
- Detailed panel maps.
- Cropped aerial imagery.
- Alternative comparison figures.
- Appendix map sets.

Maps are draft/pre-review artifacts until reviewed. Generated map and figure previews should become review queue items before export.

## Current Baseline

Current commands:

```powershell
.\.venv\Scripts\review-assist.exe generate-maps projects/trails
.\.venv\Scripts\review-assist.exe plan-figure-extents projects/trails
.\.venv\Scripts\review-assist.exe generate-deliverable-figures projects/trails
```

Current artifacts:

- `projects/<project_id>/maps/map_manifest.json`
- `projects/<project_id>/maps/figure_extent_plan.json`
- `projects/<project_id>/maps/figures/*.png`
- `projects/<project_id>/deliverable/figures.json`
- `projects/<project_id>/maps/figure_recipes/figure_recipes.json`
- `projects/<project_id>/maps/figure_style_overrides/figure_style_overrides.json`
- `projects/<project_id>/maps/figure_versions/figure_versions.json`
- `projects/<project_id>/maps/figure_render_jobs/figure_render_jobs.json`
- `projects/<project_id>/context/project_area.json` records project-area basemap source candidates and renderability status for future map rendering.

Current behavior:

- Generates legacy `project-overview` from normalized project geometry.
- Generates legacy `source-context-<source_id>` for each analyzed local source clipped layer from `constraints/constraint_results.json` when present, with legacy `spatial_relationships.json` as a fallback.
- Generates legacy `environmental-constraints-overview` when analyzed source layers have mapped features inside the analysis bounds.
- Generates exactly 15 main deliverable figure records from `config/deliverable_section_matrix.json` in matrix order at `deliverable/figures.json`.
- `initialize-figure-style-model` can initialize project-local figure recipe, sparse style override, figure version, and render-job metadata from existing `deliverable/figures.json` records without regenerating figures or mutating source/analysis/review/export artifacts.
- The figure style editor can save sparse style overrides and synchronously regenerate review-only PNG figure versions under `projects/<project_id>/maps/figures/versions/<figure_id>/vN.png`. These versions are visible in the editor with render-job metadata and are not export-active until later approval/export integration.
- Stores deliverable PNGs under `projects/<project_id>/maps/figures/`; unavailable or unsupported figures are explicit stubs with the canonical stub text.
- Renders comparison units with target-specific public/allowed layers for wetlands/NWI, FEMA flood zones, hydrography with impaired-waters caveat, public cultural context, community facility subtypes, public water wells, energy/utility infrastructure, split regulated-facility groups, oil/gas wells, and Census tracts when source data is available.
- Enforces figure-specific source scope declarations for required thematic source IDs, optional supporting source IDs, and excluded carryover source IDs. For example, the wetlands/waterbodies figure is centered on `usfws_nwi_wetlands` and may show only explicitly allowed limited waterbody support; full NHD flowline/other-area context belongs in the streams/impaired-waters figure with `mdeq_303d_impaired_waters`.
- Never renders or exposes `mdah_restricted_archaeology` locations. Restricted cultural status is preserved as `restricted_source_not_mapped`.
- Adds Attachment A supporting panel maps outside the 15 main figure count when the comparison-unit extent is too elongated for one readable figure.
- Uses GeoPandas and Matplotlib only.
- Adds compact export-facing map elements: abbreviated legend, north arrow, and scale bar when CRS units allow it. Legends use a bounded map-collar/legend-bay layout that expands the visual extent enough to place the measured rendered legend inside adjacent map context, not over the core project extent or in a plain white margin. Report-ready PNGs are map panels only: captions, report-facing figure titles, source notes, method notes, and review/process status stay in metadata, UI chrome, and export text rather than being baked into the map canvas.
- Figure extent planning writes a non-network `maps/figure_extent_plan.json` artifact before rendering. The plan records each target's extent class, core bounds, full render bounds, collar side/bounds, map-furniture placement, and grouped NAIP materialization need. Small/direct and medium/context figure groups can request distinct basemap sidecars. Large/watershed figure targets use materialized USGS WBD HUC-12 subwatershed polygons for watershed context when available; otherwise they preserve an explicit watershed-context limitation and do not infer watershed context from project-area bounds.
- Figure artifacts record figure-policy and extent-policy metadata for the source/query extent, figure extent, render extent, presentation-only collar extent, visual extent class, rendering extent class, and allowed source categories. The render extent and collar extent are explicitly presentation-only and do not drive source clipping, evidence counts, findings, table rows, or narrative interpretation.
- County/regional figure targets preserve `county_regional` visual semantics in figure planning metadata. Current rendering may reuse medium/context bounds behavior until separate county/regional query and cartographic rules are implemented.
- Non-stub matrix deliverable figures prefer project-local NAIP GeoTIFF basemap assets created by `materialize-naip-basemap --for-figure-extents` or web Create Review Queue when present. A selected render asset must cover the full planned render extent, including any collar; insufficient assets produce vector-only fallback plus `basemap_sidecar_extent_insufficient` warnings rather than blank collar space.
- Renders matrix-backed deliverable comparison units as individual visual units with saturated, high-separation deterministic colors. Usable KML colors are preserved only when they are saturated/readable on aerial imagery and not too similar to already assigned route colors; route/line styling remains a clean single-color line without the earlier heavy white casing while leaving analysis geometry and comparison-unit generation unchanged.
- Uses high-contrast source marker fills, compact marker sizes, light marker halos/dark outlines, and saturated water/wetland overlay colors so source layers remain visible on aerial imagery without overpowering comparison units. Thematic source styling uses a separate high-contrast palette contract that rejects black, washed-out, low-saturation, low-contrast olive/tan/brown, and green source-layer colors on aerial basemaps.
- Sizes deliverable figure canvas from the project/focus bounds so tall or narrow project geometries do not produce excessive empty width solely because of legend or note text. Source line/point/polygon styling is intentionally lighter than project/comparison-unit styling so context layers remain readable without overpowering submitted project geometry.
- Stores figure captions, source notes, method notes, figure grouping, related resource categories, source refs, shown layers, provenance, uncertainty flags, validation issues, stub status, and review status in the relevant figure artifact.
- Figure recipes are derived from generated figure metadata, especially `shown_layers`, figure policy, extent metadata, source refs, layer refs, image paths, and provenance. Existing autogenerated/stub figures become implicit version `v1` records. Sparse style overrides are presentation metadata only and do not change source layers, geometries, analysis outputs, evidence counts, table metrics, review status, or export image resolution.
- Figure review detail links figure items to a presentation-only figure style editor at `/review/<item_id>/figure-style`. The editor shows the current preview, review/export status, source refs, evidence refs, validation warnings, figure caption/source/method metadata, basemap/render status, recipe/model status, editable layer list, active draft override summary, version summary, and render-job summary. Comparison units are edited as individual comparison-feature rows; basemap/provenance layers are reported in status metadata but excluded from editable controls. Save/reset actions write only sparse project-local style override metadata and preserve override audit history; Save and Regenerate creates a review-only regenerated PNG version. Figure approval and export integration remain disabled/deferred.
- Adds `map_figure` review queue items with deterministic IDs such as `map-figure-project-overview`.
- Adds review queue validation items for map-generation warnings, including skipped or failed source-context figures.
- `populate-for-review` generates deliverable figures after deliverable tables and before the evidence package. Legacy map generation still runs and remains unchanged.

Current limits:

- No Google/ArcGIS basemap calls, proprietary basemap captures, or paid basemap APIs.
- NAIP COG materialization is durable and project-local. Web Create Review Queue enables `populate-for-review` with NAIP basemap materialization so figure rendering can use `projects/<project_id>/basemaps/naip/.../naip_project_basemap.tif`; CLI/scripted runs still opt in with `populate-for-review --materialize-naip-basemap`.
- No MrSID decoding or MrSID active visual selection. Real `.sid`/`.sdw` payloads are removed from active project/test resources; diagnostics point to missing project-local render assets or NAIP materialization failures. Tests may create tiny runtime dummy `.sid` fixtures only to verify unsupported-source behavior.
- GeoTIFF sidecar rendering depends on optional `rasterio`; if unavailable or rendering fails, figures fall back to vector-only output or explicit stubs with validation issues.
- PNG sidecars require usable project-area metadata/georeference; otherwise they warn and fall back.
- Panel maps are simple capped long-axis slices for Attachment A support, not final map sheets.
- No PDF/SVG map sheet export.
- No final cartographic styling.
- Figure style save/reset does not approve figures, alter review/export eligibility, or apply style overrides during export. Save and Regenerate can create review-only regenerated PNG versions from saved overrides; version approval and export integration remain deferred.

## Likely Python Workflow

The likely open-source workflow is:

1. Load project geometry and source layers with GeoPandas.
2. Normalize CRS and clip layers to project extent.
3. Generate map extents from project footprint, alternatives, or panel grid.
4. Render layers with Matplotlib.
5. Add basemap or local raster imagery where appropriate.
6. Add legend, scale/context, and north arrow to the map panel; preserve title, caption, source notes, method notes, and figure number as metadata/export text outside the PNG.
7. Export PNG/PDF/SVG outputs.
8. Register figure metadata as a review queue item and later in the package manifest if accepted.

Potential supporting libraries:

- GeoPandas for vector data handling and plotting.
- Matplotlib for static figure rendering.
- Contextily for web or local tile basemap integration with Matplotlib.
- Rasterio for raster/imagery reading and clipping.
- PyProj/Shapely for CRS and geometry operations through GeoPandas.

References:

- GeoPandas mapping: https://geopandas.org/en/stable/docs/user_guide/mapping.html
- Contextily basemaps: https://contextily.readthedocs.io/en/stable/reference.html

## Basemap Source Options

### NAIP

Useful for:

- Aerial review.
- Existing disturbance context.
- Cropped imagery.
- Report figures where current enough.

Notes:

- NAIP is a USDA imagery program.
- Acquisition timing and resolution vary by year and state.
- Source date and resolution should be preserved.
- `materialize-naip-basemap` can create a project-local renderable GeoTIFF sidecar from public Microsoft Planetary Computer NAIP COG assets by project analysis bounds. With `--for-figure-extents`, it first plans figure render extents and writes grouped sidecars such as `basemaps/naip/small_direct/<year>/naip_project_basemap.tif` and `basemaps/naip/medium_context/<year>/naip_project_basemap.tif`. The command records provenance, extent class, core extent, full render extent, collar side, source items, CRS, bounds, resolution, and limits. The shared default tile cap is 100 NAIP tiles, with controlled fallback warnings if the cap is exceeded. Oversized native-resolution windows are resampled to fit `--max-pixels`; the command does not lift limits or download whole county/state imagery.

Reference: https://catalog.data.gov/dataset/national-agriculture-imagery-program-naip-imagery

### USGS Imagery and The National Map

Useful for:

- Topographic context.
- USGS imagery basemaps.
- Hydrography/topo overlays.
- Repeatable public basemap services.

Reference: https://www.usgs.gov/faqs/what-are-base-map-services-or-urls-used-national-map

### State Orthophotos and County Imagery

Useful for:

- More recent or higher-resolution local context.
- County-level updates not captured in national imagery.

Notes:

- Source availability and terms vary.
- Date, resolution, and licensing must be tracked.

### ArcGIS Basemaps

Useful for:

- Streets, light gray, navigation, imagery, and other cartographic basemap contexts.
- Interactive preview or static rendering if terms and access are acceptable.

Notes:

- ArcGIS basemap styles are served in Web Mercator.
- Attribution and access terms must be reviewed.

Reference: https://developers.arcgis.com/documentation/mapping-and-location-services/mapping/basemaps/introduction-basemap-styles-service/

### Google Earth / Google Maps

Useful for:

- Visual review context.
- Manual QC.
- Identifying potential recent features not present in source layers.

Notes:

- Treat as visual review context unless a specific approved API/export workflow is selected.
- Google Maps Static API requires an API key and billing.
- Google Earth imagery requires visible attribution to Google Earth and third-party imagery providers where applicable.
- Do not implement Google API access without explicit approval.

References:

- https://earth.google.com/studio/docs/en_gb/attribution/
- https://developers.google.com/maps/documentation/maps-static/start

## Overlay Types

Common overlays:

- Project footprint.
- Alternatives.
- Corridor/buffer geometries.
- Wetlands and waterbodies.
- Streams and river crossings.
- FEMA flood zones and floodways.
- Cultural resource context.
- Community facilities.
- Public water supply wells.
- Utility and pipeline infrastructure.
- Hazardous/regulated sites, water-discharge/waste facilities, and oil/gas wells as split regulated-facility figures.
- Census tracts or demographic context.
- Imagery-observed review items.

## Panel Map Concept

Panel maps are useful when a corridor is too long or complex for one readable map.

Possible workflow:

1. Generate an overall map.
2. Create a panel index grid or corridor sections.
3. Render each panel at a consistent scale.
4. Use consistent legends and symbology.
5. Reference panel numbers in findings and report narrative.

Open questions:

- Should panels be fixed-size map sheets or generated from route segmentation?
- Should panels follow alternatives, project mileposts, road intersections, or arbitrary extents?
- What page size and DPI are required?

## Legend and Figure Metadata

Each figure should eventually include or preserve:

- Figure title.
- Project name.
- Alternative(s) shown.
- Resource layers shown.
- Legend.
- Scale or scale context.
- North arrow if appropriate.
- Source names.
- Source dates where available.
- Access date for remote layers where appropriate.
- Review status in metadata/UI, not in exported figure content.
- Figure ID.
- Generated timestamp.

For report-ready deliverable PNGs, this information is preserved in the figure artifact and export package rather than embedded as editable-report text inside the image.

## Report-Ready Export Concepts

Potential output formats:

- PNG for embedded draft figures.
- PDF for print-ready map sheets.
- SVG for editable vector maps where feasible.
- GeoPackage/GeoJSON for reviewer GIS layers.

Generated workflow figures are stored under ignored project `maps/figures/`. During report export, included figure PNGs are copied into ignored `projects/<project_id>/exports/assets/figures/` so Markdown/DOCX packages can reference package-local assets while preserving original map artifact provenance.

Only accepted or explicitly included reviewed figures should be compiled into report exports.

## Open Questions

- Which basemap should be the default for internal draft reports?
- Do report maps need to match an existing client/agency map style?
- What DPI/page size is expected for template-grade DOCX and future PDF output?
- Should map generation run entirely offline after sources are cached?
- What is the first acceptable source for current aerial imagery?
- Are Google Earth screenshots permissible in internal drafts, final appendices, or only manual review?
