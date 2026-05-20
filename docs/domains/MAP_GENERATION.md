# Map Generation

This document captures current and future map and figure generation workflows. A vector-only draft map baseline is implemented for legacy audit/context maps, and Sprint 2.3 adds matrix-backed deliverable figure artifacts. Project area generation records NAIP/MARIS basemap source-path provenance and renderability status; deliverable figures can use selected renderable `.png`, `.tif`, or `.tiff` sidecars, including optional project-local NAIP GeoTIFF sidecars, while `.sid` files remain provenance only. Production cartography, MrSID decoding, paid/proprietary basemap APIs, PDF/SVG map sheets, and final cartographic styling remain future work.

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

Current command:

```powershell
.\.venv\Scripts\review-assist.exe generate-maps projects/trails
.\.venv\Scripts\review-assist.exe generate-deliverable-figures projects/trails
```

Current artifacts:

- `projects/<project_id>/maps/map_manifest.json`
- `projects/<project_id>/maps/figures/*.png`
- `projects/<project_id>/deliverable/figures.json`
- `projects/<project_id>/context/project_area.json` records project-area basemap source candidates and renderability status for future map rendering.

Current behavior:

- Generates legacy `project-overview` from normalized project geometry.
- Generates legacy `source-context-<source_id>` for each analyzed local source clipped layer from `constraints/constraint_results.json` when present, with legacy `spatial_relationships.json` as a fallback.
- Generates legacy `environmental-constraints-overview` when analyzed source layers have mapped features inside the analysis bounds.
- Generates exactly 13 main deliverable figure records from `config/deliverable_section_matrix.json` in matrix order at `deliverable/figures.json`.
- Stores deliverable PNGs under `projects/<project_id>/maps/figures/`; unavailable or unsupported figures are explicit stubs with the canonical stub text.
- Renders comparison units with target-specific public/allowed layers for wetlands/NWI/hydrography, FEMA flood zones, hydrography with impaired-waters caveat, public cultural context, community facility subtypes, public water wells, energy/utility infrastructure, regulated facilities, and Census tracts when source data is available.
- Never renders or exposes `mdah_restricted_archaeology` locations. Restricted cultural status is preserved as `restricted_source_not_mapped`.
- Adds Attachment A supporting panel maps outside the 13 main figure count when the comparison-unit extent is too elongated for one readable figure.
- Uses GeoPandas and Matplotlib only.
- Adds compact export-facing map elements: abbreviated legend, north arrow, and scale bar when CRS units allow it. Review/process status stays in metadata and UI chrome, not in exported figure captions or on the map canvas. Detailed source counts, provenance, and CRS/method text remain in figure artifact caption/source/method fields rather than consuming the map canvas.
- Can use project-local NAIP GeoTIFF basemap sidecars created by the explicit `materialize-naip-basemap` command when present.
- Renders matrix-backed deliverable comparison units as individual visual units with preserved usable KML colors or deterministic visible fallbacks, while leaving analysis geometry and comparison-unit generation unchanged.
- Sizes deliverable figure canvas from the project/focus bounds so tall or narrow project geometries do not produce excessive empty width solely because of legend or note text.
- Stores figure captions, source notes, method notes, figure grouping, related resource categories, source refs, shown layers, provenance, uncertainty flags, validation issues, stub status, and review status in the relevant figure artifact.
- Adds `map_figure` review queue items with deterministic IDs such as `map-figure-project-overview`.
- Adds review queue validation items for map-generation warnings, including skipped or failed source-context figures.
- `populate-for-review` generates deliverable figures after deliverable tables and before the evidence package. Legacy map generation still runs and remains unchanged.

Current limits:

- No Google/ArcGIS basemap calls, proprietary basemap captures, or paid basemap APIs.
- NAIP COG sidecar materialization is explicit and optional. Normal figure generation and plain `populate-for-review` do not acquire imagery.
- No MrSID decoding. `.sid` files stay as source provenance only, with explicit diagnostics telling reviewers to provide a GeoTIFF/PNG sidecar when a visual aerial basemap is needed.
- GeoTIFF sidecar rendering depends on optional `rasterio`; if unavailable or rendering fails, figures fall back to vector-only output or explicit stubs with validation issues.
- PNG sidecars require usable project-area metadata/georeference; otherwise they warn and fall back.
- Panel maps are simple capped long-axis slices for Attachment A support, not final map sheets.
- No PDF/SVG map sheet export.
- No final cartographic styling.

## Likely Python Workflow

The likely open-source workflow is:

1. Load project geometry and source layers with GeoPandas.
2. Normalize CRS and clip layers to project extent.
3. Generate map extents from project footprint, alternatives, or panel grid.
4. Render layers with Matplotlib.
5. Add basemap or local raster imagery where appropriate.
6. Add legend, title, scale/context, source notes, and figure number.
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
- `materialize-naip-basemap` can create a project-local renderable GeoTIFF sidecar from public Microsoft Planetary Computer NAIP COG assets by project analysis bounds. The command records provenance and enforces AOI/tile/pixel/time limits.

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
- Hazardous materials sites.
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
