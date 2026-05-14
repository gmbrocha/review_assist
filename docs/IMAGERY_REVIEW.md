# Imagery Review

This document defines the future philosophy for aerial imagery, basemaps, and visual observations.

No imagery acquisition, computer vision, or production overlay workflow is implemented yet.

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

Imagery-observed features should be stored as review items until validated by a human reviewer.

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
5. Store observations as structured review items.
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

They should not appear as accepted facts until reviewer status supports that treatment.

## Open Questions

- Which imagery source should be default for v1?
- How should imagery dates be captured and displayed?
- Are Google Earth screenshots acceptable in draft or final deliverables?
- Should the system support manual annotation before automated imagery detection?
- How should reviewer-confirmed imagery observations be converted into accepted findings?
