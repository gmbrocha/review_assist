# Map Generation

This document captures likely future map and figure generation workflows. No production map-generation pipeline is implemented yet.

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

## Likely Python Workflow

The likely open-source workflow is:

1. Load project geometry and source layers with GeoPandas.
2. Normalize CRS and clip layers to project extent.
3. Generate map extents from project footprint, alternatives, or panel grid.
4. Render layers with Matplotlib.
5. Add basemap or local raster imagery where appropriate.
6. Add legend, title, scale/context, source notes, draft label, and figure number.
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
- Draft/pre-review label.
- Figure ID.
- Generated timestamp.

## Report-Ready Export Concepts

Potential output formats:

- PNG for embedded draft figures.
- PDF for print-ready map sheets.
- SVG for editable vector maps where feasible.
- GeoPackage/GeoJSON for reviewer GIS layers.

Generated figures should be stored outside Git-tracked source code, likely under project-specific outputs or ignored `outputs/` paths.

Only accepted or explicitly included reviewed figures should be compiled into report exports.

## Open Questions

- Which basemap should be the default for internal draft reports?
- Do report maps need to match an existing client/agency map style?
- What DPI/page size is expected for DOCX/PDF output?
- Should map generation run entirely offline after sources are cached?
- What is the first acceptable source for current aerial imagery?
- Are Google Earth screenshots permissible in internal drafts, final appendices, or only manual review?
