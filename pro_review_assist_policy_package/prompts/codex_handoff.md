You are reviewing a Review Assist requirements-mining package derived from an example Environmental Constraints Report.

This package is NOT a finished standard, NOT a universal template, and NOT something to blindly implement. It is a structured extraction artifact meant to help identify reusable report-policy, source, figure/table, caveat, extent, and workflow patterns for Review Assist.

The example report was an unfinished, project-specific, trail/corridor-oriented Environmental Constraints Report. It contains useful design intelligence, but also project-specific facts, PEL-specific framing, trail-specific alternative logic, incomplete draft sections, broken/inconsistent references, and example-only content. Treat the package as a decision-support artifact, not gospel.

CRITICAL IMPLEMENTATION BOUNDARY:
Do not edit files yet.
Do not implement changes yet.
Do not add new sources yet.
Do not expand GPT coverage yet.
Do not change deliverable matrix counts casually.
Do not create document sprawl.
Do not commit generated project artifacts.
First produce the requested diff and plan only. After the plan is reviewed, small, clearly justified P0/P1 changes may be approved for implementation separately.

Package location:
- Use the extracted package directory if present, likely:
  - review_assist_policy_package/
- Or the unzipped contents of:
  - review_assist_policy_package.zip

The package likely includes:
- review_assist_extraction_package.docx
- review_assist_extraction_package.pdf
- review_assist_extraction_package.md
- config/review_assist_report_policy.json
- docs/domains/REPORT_POLICY.md
- docs/domains/GPT_STYLE_CONTEXT.md
- prompts/codex_prompt_starters.md
- README.md

If the package is not present, stop and report that the package could not be located. Do not invent package contents.

Your task is to read the extracted package carefully, inspect the current Review Assist implementation, and produce a structured comparison and implementation plan.

Review Assist context:
Review Assist is a private proof-of-concept environmental constraints/report review assistant. It should help reviewers screen broadly, organize source-backed evidence, surface human decisions, and produce compact, human-reviewed Environmental Constraints Report packages.

Core principles:
- Automation assists; humans decide.
- Outputs remain reviewable.
- Do not fake findings.
- Do not dump raw source records into the report body.
- Keep the report body compact; retain evidence/audit material separately.
- Incomplete data is allowed only when labeled honestly.
- Public/coarse screening sources may be used for private POC context.
- Restricted or reviewer-supplied sources can be swapped in later for real use.
- Public/coarse cultural context must not be represented as authorized MDAH/SHPO/SHPO-equivalent records.
- Source truth, extent semantics, and report wording must stay aligned.
- Review Assist is feature-neutral. It is not a trails app.
- projects/trails is only a sample fixture.

Preferred generic language:
- project features
- submitted features
- comparison units
- alternatives
- project geometry
- study area
- project area

Avoid making generic app language trail-specific. Trail/corridor/PEL concepts must be conditional/custom, not default.

============================================================
1. READ THE EXTRACTED PACKAGE CAREFULLY
============================================================

Read the extracted package before inspecting implementation details.

Pay attention to these package components:

A. Report structure inventory
- Section and subsection inventory.
- Whether each section is generalizable, conditional, project-specific, trail/corridor-specific, incomplete/uncertain, or do-not-generalize.
- Expected output shape: paragraph, table, figure, bullet list, attachment reference, manual text, etc.
- Whether content is source-backed, reviewer-written, project-specific narrative, or manual/restricted.

B. Section policy suggestions
- Suggested section IDs.
- Section families/categories.
- Extent type.
- Visual extent class.
- Comparison-unit expansion policy.
- Evidence pattern.
- Drafting mode.
- Required caveats.
- Prohibited claims.
- Allowed source/table/figure refs.

C. Source needs by section
- Source/data needs implied by the sample report.
- Which sources are required, optional, manual, restricted, reviewer-supplied, public/coarse, or project-specific.
- Whether the source supports direct analysis, nearby context, watershed context, regional context, attachment support, tables, figures, prose, bullets, or caveats.
- Whether the source class appears already covered by Review Assist.
- Whether it is an app gap.

D. Figure needs
- Figure purposes/titles.
- Supported sections.
- Source layers.
- Intended extent types.
- Main report vs attachment/supporting panel.
- Required/conditional/manual status.
- Whether each figure supports direct evidence, nearby context, watershed context, or presentation/support.

E. Table needs
- Table purposes/titles.
- Supported sections.
- Source data needed.
- Likely rows/columns.
- Row grain: per comparison unit, per facility, per source feature, or summary row.
- Body vs attachment placement.
- Required/conditional/manual status.

F. Alternative / comparison-unit expansion logic
- Where the example report discusses alternatives individually.
- Where it uses comparison tables only.
- Where it summarizes alternatives together.
- Where it does not compare alternatives.
- Which behavior is universal, conditional, trail/corridor-specific, or not generalized.

G. Extent / spatial scope policy
- Scope terms such as within, near, adjacent, vicinity, downstream, watershed, county, city, corridor, APE.
- Whether each term implies direct analysis, buffer screening, nearby/community context, watershed context, regional context, manual/reviewer-supplied context, or presentation-only rendering.
- Whether map extent may be larger than analysis extent.
- Wording rules needed to avoid overclaiming.

H. Wording and caveat library
- Wetlands/NWI limitations.
- Hydrography/water quality caveats.
- Floodplain caveats.
- Cultural/restricted-records caveats.
- Public/coarse cultural context caveats.
- Community resource context wording.
- Regulated/hazardous facility context wording.
- Utility/infrastructure caveats.
- Socioeconomic/demographic context caveats.
- No-determination/screening-only language.
- Agency coordination/field verification language.
- Reviewer-supplied material language.
- Phrases to avoid because they overclaim.

I. Manual / reviewer-supplied materials
- Agency coordination letters.
- Hazardous materials support reports.
- Restricted archaeology/cultural-resource records.
- Project relationship/context sections.
- Prior studies.
- Project-specific methodology details.
- Custom project background.
- Final conclusions/next steps requiring reviewer judgment.

J. Generalizable vs project-specific classification
- Generalizable template elements.
- Conditional elements.
- Project-specific elements.
- Trail/corridor-specific elements.
- PEL-specific elements.
- Incomplete/uncertain elements.
- Do-not-generalize elements.
- Specifically inspect the treatment of “Relationship with the PEL Study.”

K. Diff/recommendations against Review Assist
- App already covers this well.
- App has source but needs policy/mapping.
- App has policy but lacks source.
- App has figure/table but wrong extent or wording.
- App lacks needed section.
- Example item should not be generalized.
- Manual/reviewer-supplied only.
- Future/deferred.

============================================================
2. INSPECT CURRENT REVIEW ASSIST IMPLEMENTATION
============================================================

Inspect the current app and repo structure. Likely relevant files include, but are not limited to:

Configuration:
- config/deliverable_section_matrix.json
- config/report_section_policy.json, if present
- config/source_catalog.json
- config/report_profiles.json
- config/report_generation_prompts.json
- any source-needs, figure/table, deliverable, or profile config files

Extent/source/report policy:
- src/review_assist/extent_policy.py
- source materialization modules
- source status/effective truth modules
- source warehouse modules
- project-local source materialization modules

Deliverables:
- deliverable table modules
- deliverable figure modules
- deliverable evidence package modules
- deliverable item modules
- review queue modules
- report assembly/export modules
- compactness guard modules

GPT/drafting:
- GPT interpretive assist modules
- deterministic drafting modules
- section drafting modules
- prompt assembly modules
- GPT eligibility/review-gate logic

Documentation:
- docs/domains/REPORT_POLICY.md
- docs/domains/REPORT_ASSEMBLY.md
- docs/domains/DATA_SOURCES.md
- docs/domains/SOURCE_WAREHOUSE.md
- docs/governance/DEFERRED_WORK.md
- related README or architecture docs

Tests:
- tests for report section policy
- tests for deliverable matrix behavior
- tests for source catalog/source status
- tests for extent policy/scope wording
- tests for figure/table generation
- tests for GPT drafting/eligibility
- tests for review queue/manual source handling
- tests for compactness/no raw dump behavior

Use repo search to locate equivalent files if paths differ.

Do not assume missing files are absent until you search for related names and code paths.

============================================================
3. PRODUCE A STRUCTURED DIFF
============================================================

For each recommendation, pattern, section, source, figure, table, policy rule, caveat, and workflow item from the package, classify the current app state using one of these labels:

- Already covered correctly
- Covered but needs policy/config cleanup
- Covered but wrong source mapping
- Covered but wrong extent/scope wording
- Covered but wrong comparison-unit expansion behavior
- Covered but wrong figure/table placement
- Missing and should be added
- Useful but conditional/project-type dependent
- Manual/reviewer-supplied only
- POC-only / public-context-only
- Example-specific / do not generalize
- Trail/corridor-specific / conditional only
- PEL-specific / custom project context only
- Deferred source acquisition
- Needs human decision

Be strict. When uncertain, do not generalize. Mark the item conditional, manual/reviewer-supplied, deferred, or needs human decision.

The diff should explicitly cover at least:

Report structure:
- Executive summary
- Introduction
- Relationship with PEL Study
- Project/study area and comparison units
- Methodology
- Data collection and sources
- Mapping and analysis procedures
- Limitations/data gaps
- Environmental constraints inventory
- Natural/ecological resources
- Cultural/historic resources
- Community resources
- Utility/infrastructure considerations
- Contamination risks
- Socioeconomic/business considerations
- Conclusion/next steps
- References
- Attachments

Section policy:
- Section IDs
- Inclusion triggers
- Extent type
- Visual extent class
- Evidence pattern
- Drafting mode
- Required caveats
- Prohibited claims
- Allowed sources/tables/figures
- Review-gate status

Source needs:
- NWI wetlands
- Hydrography/NHD
- FEMA flood hazard
- HUC/WBD watershed context
- 303(d)/TMDL water quality
- Protected species/critical habitat
- State species / natural heritage / agency letters
- Public/coarse cultural context
- Restricted/authorized cultural records
- Community resources/facilities
- Public water supply/wells
- Utility/pipeline/electric infrastructure
- Airports
- Hazardous/regulated facilities
- Oil/gas wells
- Census/ACS/demographics
- Business/economic nodes
- Reviewer-supplied attachments

Figures:
- Project area/comparison units
- Overall constraints map
- Panel index/panel maps
- Wetlands/waterbodies
- FEMA flood zones
- Streams/impaired waters/watershed context
- Cultural resources
- Community resources
- Public water supply
- Energy/utility infrastructure
- Hazardous/regulated sites
- Oil/gas wells
- Census tracts/demographics

Tables:
- Wetlands/waterbodies by comparison unit
- FEMA flood zones by comparison unit
- Water quality/watershed context
- Protected species/agency consultation summary
- Cultural resource summary
- Community resources/facility table
- Utility crossings/assets table
- Public water supply wells table
- Hazardous/regulated facilities table
- Oil/gas wells table
- Demographic tables
- Source status/evidence audit
- Review queue decisions

Comparison-unit behavior:
- No expansion
- Table-only expansion
- Narrative children
- Conditional/context summary
- Manual only

Extent/scope wording:
- within
- near
- adjacent
- downstream
- watershed/subwatershed
- county/regional
- APE
- map extent vs analysis extent
- presentation-only figures

Wording/caveats:
- Desktop screening
- NWI non-jurisdictional
- Flood hazard caveats
- Direct vs downstream water quality
- Public/coarse cultural context
- Restricted cultural records
- Hazardous database screening
- Utilities/provider verification
- Demographic/census geography limitations
- No final impact/effect/permit claims

============================================================
4. PROTECT FEATURE-NEUTRALITY
============================================================

Review Assist is not a trails app.

The sample project and projects/trails fixture are diagnostic/sample material only. Do not make the generic app assume:
- trails
- corridors
- routes
- alignments
- trail alternatives
- railroad corridors
- highway corridors
- PEL studies
- corridor panel maps
- stream crossing narratives
- boardwalk/culvert/bridge trail language

Generic policy and prose should prefer:
- project features
- submitted features
- comparison units
- alternatives, only when project metadata defines alternatives
- project geometry
- study area
- project area

Classify trail/corridor-specific patterns as:
- Trail/corridor-specific / conditional only

Classify PEL-specific patterns as:
- PEL-specific / custom project context only

The “Relationship with the PEL Study” section must not become a default generic section. It may be represented as a conditional/manual parent-study/context section only.

============================================================
5. FOCUS ON RECOMMENDATIONS, NOT IMPLEMENTATION
============================================================

Recommend changes to the following areas, but do not implement them yet:

- report section policy
- comparison-unit expansion policy
- extent policy / scope metadata
- source needs manifest
- source catalog/report profile mappings
- figure/table target mappings
- drafting/caveat wording rules
- GPT readiness by section
- manual/reviewer-supplied sections
- deferred work routing
- tests needed

For each recommended change, identify:
- target file(s)
- reason
- priority
- expected behavior
- risk if not changed
- tests needed
- whether human approval is required before implementation

Do not add new source acquisition unless explicitly approved.
Do not expand GPT coverage yet.
Do not create new config/doc files unless there is a strong reason. Prefer updating existing policy/config/docs.
Do not create document sprawl.
Do not commit generated reports, PDFs, rendered pages, cache files, or sample project artifacts.

============================================================
6. PRIORITIZE CHANGES
============================================================

Classify recommendations into:

P0:
Must fix before GPT interpretation or further manual testing because the current app may misrepresent source truth, spatial scope, report wording, or review status.

Examples:
- Missing/incorrect extent semantics.
- Map extent treated as analysis extent.
- “within”/“near”/“downstream” wording overclaims.
- Public/coarse cultural context represented as authorized cultural records.
- GPT allowed to infer policy/regulatory findings.
- Missing caveats for NWI/FEMA/hazmat/cultural/demographic context.
- Per-alternative narrative expansion happening by default.
- Manual/reviewer-supplied material treated as automated evidence.
- Report body dumping raw source records.
- Section renders despite unmet source requirements.

P1:
Should fix soon because it improves policy alignment, source mapping, report fidelity, reviewability, or config clarity.

Examples:
- Better section IDs and inclusion triggers.
- Better source/table/figure mappings.
- Better caveat bundles.
- Better references/source-status behavior.
- Better attachment handling.
- Better no-finding wording.
- Better tests for policy behavior.

P2:
Useful later source expansion, table/figure additions, or workflow improvements. Do not implement P2 now.

Examples:
- New 303(d)/TMDL acquisition.
- Census/ACS expansion.
- Community facilities sources.
- Public water supply well sources.
- Airports source.
- Utility/pipeline/electric infrastructure source expansion.
- Business/economic node source expansion.

P3:
Polish or future product refinement. Do not implement P3 now.

Examples:
- Report rendering polish.
- Panel map styling.
- Glossary/acronym refinements.
- Optional appendix formatting.
- Advanced UX improvements.

Do not implement P2/P3 in this pass.

============================================================
7. TEST RECOMMENDATIONS
============================================================

Recommend tests for any proposed policy/source/report changes.

Tests should cover:

Section policy coverage:
- Sections only render when triggers/source requirements are satisfied.
- Conditional/manual sections do not render by default.
- PEL relationship section is not default.

Extent/scope wording:
- Direct intersections use “within.”
- Buffer/context results use “near” or equivalent.
- Watershed/downstream context does not become direct intersection language.
- Map extent is not treated as analysis extent.
- APE is reviewer-defined only.

Comparison-unit expansion:
- Default is table-only where appropriate.
- Narrative children do not appear unless policy enables them.
- Trail-specific alternative language does not leak into generic projects.
- Arbitrary feature types are supported.

Source needs mappings:
- Sources map to correct sections.
- Source status/effective truth is reflected.
- Missing/deferred/manual/restricted sources are labeled.
- Public/coarse sources are not overclaimed.

GPT eligibility:
- GPT only runs for sections with allowed drafting mode.
- GPT cannot invent missing policy/regulatory findings.
- GPT cannot cite prohibited source/table/figure refs.
- GPT cannot render prohibited claims.
- GPT coverage is not expanded in this pass.

Manual/reviewer-supplied handling:
- Agency letters are manual/reviewer-supplied.
- Hazardous materials support reports are manual/reviewer-supplied unless generated by an approved workflow.
- Restricted cultural records are not replaced by public/coarse data.
- Final conclusions/commitments require reviewer approval.

No trail-specific drift:
- Generic docs/config avoid trail-only language.
- projects/trails remains a sample fixture.
- Report policy uses project features/submitted features/comparison units/project area language.

Compactness/no raw-dump protections:
- Body tables remain compact.
- Overflow goes to evidence/attachment package.
- Raw source records are not dumped into the report body.

Figure/table placement:
- Main report vs attachment placement follows policy.
- Figure/table refs are allowed only for generated/available deliverables.
- Empty/incomplete tables are not rendered as finished report content.

Deferred work:
- New source acquisition recommendations are routed to deferred work unless explicitly approved.
- P2/P3 items are not implemented.

============================================================
8. REQUIRED OUTPUT FORMAT
============================================================

Produce the following output. Be specific and implementation-oriented.

A. PACKAGE SUMMARY
Summarize what the extracted package contains and how you used it.
Explicitly state that it is a requirements-mining artifact, not a standard to blindly implement.

B. CURRENT APP COMPARISON
Summarize the current Review Assist implementation as inspected.
List the files/modules reviewed.
Call out any relevant files that were expected but missing.

C. STRUCTURED DIFF
Provide a table with columns:
- Package item / pattern
- Current app location or missing
- Classification
- Recommended action
- Priority
- Notes / risk

Use the classification labels listed above.

D. P0 / P1 / P2 / P3 PLAN
Provide prioritized recommendations.
For each item include:
- target file(s)
- change summary
- why it matters
- implementation risk
- required tests
- whether human approval is needed

E. RECOMMENDED CONFIG / DOC / TEST CHANGES
Separate recommendations into:
- Config changes
- Code changes
- Documentation changes
- Test changes

Do not edit yet. This is a plan only.

F. HUMAN-DECISION ITEMS
List decisions that need human/product/reviewer input before implementation.
Include at least:
- Whether to create or update a canonical report policy file.
- Whether source-needs manifest should be separate or integrated.
- Which sections are allowed to use GPT initially.
- Which sources are manual/reviewer-supplied only.
- Which source expansions should remain deferred.
- How to handle PEL/custom parent-study context.
- How to handle public/coarse cultural context vs restricted records.

G. IMPLEMENTATION RECOMMENDATION
End with a clear recommendation:
- Whether to implement now or wait.
- Which P0/P1 changes are safest to implement first after approval.
- Which changes should be deferred.
- Which items should be ignored because they are example-specific, trail/corridor-specific, PEL-specific, incomplete, or unsafe to generalize.

Reminder:
Do not implement until this plan is reviewed and approved.