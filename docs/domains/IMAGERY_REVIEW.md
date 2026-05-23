# Imagery Review

This document defines the future philosophy for aerial imagery, basemaps, and visual observations.

No computer vision or production imagery-observation workflow is implemented yet. The current backend can index local MARIS/NAIP 2025 county folders through `src/review_assist/basemaps.py`, record unsupported legacy source metadata separately from renderable project assets in `context/project_area.json`, expose `maris_naip_2025_imagery` and `usda_naip_imagery` source status detail, and use project-local renderable NAIP GeoTIFF assets in matrix-backed deliverable figures when metadata is sufficient. `materialize-naip-basemap` can create project-local renderable NAIP GeoTIFF assets from public Microsoft Planetary Computer COG assets by project analysis bounds or planned figure extents.

## Purpose

Imagery can help reviewers identify conditions that official GIS datasets may not capture.

Examples:

- Visible pond not present in a wetland layer.
- Recent clearing.
- Newer roadway.
- Existing disturbed corridor.
- Possible structure.
- Visible crossing concern.
- Apparent land use change.

These observations are useful, but they are not authoritative facts by default.

## Review Item Rule

Imagery-observed features should be stored as review queue items until validated by a human reviewer.

Preferred language:

- "Recent imagery appears to show..."
- "Imagery review item..."
- "This feature was not identified in the reviewed source layer."
- "Reviewer verification is needed."

Avoid:

- "The pond exists" unless verified.
- "The area is jurisdictional wetland" based on imagery alone.
- "The source layer is wrong" without reviewer confirmation.

## Source Hierarchy

Possible imagery sources:

- NAIP.
- State orthophotos.
- County imagery.
- USGS imagery services.
- ArcGIS imagery basemaps.
- Google Earth visual review context.
- Historical aerial imagery.

Selection should consider:

- Capture date.
- Resolution.
- Coverage.
- Licensing/terms.
- Attribution.
- Repeatability.
- Export quality.

Current implemented selection context:

- `build-project-area` checks materialized MARIS boundary context, existing project context, and NAIP/MARIS metadata extents to identify county names.
- Matching county metadata under `sources/aerial_base_maps/maris_naip_2025` may be recorded as basemap provenance.
- Real MrSID `.sid`/`.sdw` payloads are not retained as active Review Assist assets. Legacy MrSID references are unsupported/stale provenance only, while `.tif`, `.tiff`, `.png`, `.jpg`, and `.jpeg` assets are tracked as renderable paths.
- Metadata-only or legacy MrSID-only provenance produces `render_asset_missing` warnings when no project-local NAIP/aerial render asset exists.
- `materialize-naip-basemap` queries NAIP STAC by project analysis bounds, reads only bounded COG windows, writes `projects/<project_id>/basemaps/naip/<year>/naip_project_basemap.tif`, and records adjacent JSON provenance.
- Web Create Review Queue enables failure-tolerant NAIP materialization before figure rendering; CLI/scripted `populate-for-review` runs opt in with `--materialize-naip-basemap`.
- `generate-deliverable-figures` may render selected `.png`, `.tif`, or `.tiff` sidecars into draft/pre-review figures. GeoTIFF support uses optional `rasterio` lazily; PNG support requires usable project-area metadata/georeference.
- If a render asset is unavailable, unreadable, unreferenced, or unsupported, the figure artifact records `basemap_render_asset_missing`, `naip_basemap_materialization_failed`, or `basemap_render_failed` and falls back to vector-only rendering or an explicit stub.
- This does not create imagery observations or authoritative source corrections.

## Imagery vs. Authoritative Layers

Imagery may be newer than a source layer, but a visual observation should not automatically override an authoritative GIS source.

Possible discrepancy outcomes:

- Flag as source/imagery discrepancy.
- Request reviewer validation.
- Add reviewer note.
- Add field-verification flag.
- Update source layer if authoritative updated data is available.

## Future Overlay Workflow

Potential workflow:

1. Acquire or load imagery for the project extent.
2. Crop imagery to footprint, alternative, buffer, or panel map extents.
3. Overlay alternatives and source layers.
4. Let reviewer mark observed features.
5. Store observations as structured review queue items.
6. Include selected observations in draft report with cautious phrasing.

## Future CV/ML Assistance

Computer vision or ML may eventually assist with:

- Detecting visible waterbodies.
- Detecting recent clearing.
- Detecting structures or roads.
- Highlighting imagery/source discrepancies.

This is not in scope now.

If added later, CV/ML outputs must:

- Remain review items.
- Include model/method metadata.
- Preserve uncertainty.
- Require human validation.
- Avoid final determinations.

## Map and Report Treatment

Imagery review items may appear in:

- Reviewer overlay maps.
- Draft finding lists.
- Map callouts.
- "Needs review" report notes.
- Data gap/uncertainty sections.

They should not appear as accepted facts until reviewer status supports that treatment. They should not export unless accepted or explicitly included with caveat language.

## Open Questions

- Which imagery source should be default for v1?
- How should imagery dates be captured and displayed?
- Are Google Earth screenshots acceptable in draft or final deliverables?
- Should the system support manual annotation before automated imagery detection?
- How should reviewer-confirmed imagery observations be converted into accepted findings?
