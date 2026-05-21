"""Command-line interface for local project inspection and source checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .comparison_units import ComparisonUnitError, build_comparison_units
from .constraints import ConstraintAnalysisError, analyze_constraints
from .deliverable_constraints import ComparisonUnitConstraintError, analyze_comparison_unit_constraints
from .deliverable_matrix import (
    DeliverableMatrixError,
    ReportPromptConfigError,
    ReportSectionPolicyConfigError,
    load_report_prompt_config,
    validate_deliverable_contract,
)
from .deliverable_figures import DeliverableFigureError, generate_deliverable_figures, generate_figure_extent_plan
from .deliverable_items import DeliverableItemsError, generate_deliverable_items
from .deliverable_tables import DeliverableTableError, generate_deliverable_tables
from .deliverable import DemoDeliverableError, MvpDeliverableError, build_demo_deliverable, build_mvp_deliverable
from .evidence_package import EvidencePackageError, build_evidence_package
from .export_report import ExportGateError, ExportQAError, ExportReportError, export_report
from .findings import FindingGenerationError, generate_draft_findings
from .gpt_interpretive_assist import GptInterpretiveAssistError, draft_section_candidates
from .input_package import InputPackageError, classify_input_package
from .inspection import ProjectInspectionError, inspect_project
from .maps import MapGenerationError, generate_maps
from .naip_basemap_materialization import (
    DEFAULT_MAX_PIXELS,
    DEFAULT_MAX_TILES,
    DEFAULT_TIMEOUT_SECONDS,
    materialize_naip_basemap,
)
from .populate_for_review import PopulateForReviewError, populate_for_review
from .project_context import ProjectContextError, generate_project_context
from .project_area import ProjectAreaError, build_project_area
from .project_geometry import ProjectGeometryError, build_project_geometry
from .report_sections import ReportSectionGenerationError, generate_report_sections
from .review_queue import (
    ReviewQueueError,
    generate_review_queue,
    summarize_review_queue,
    update_review_item,
)
from .review_queue_reset import RESET_WARNING, ReviewQueueResetError, reset_review_queue
from .source_inventory import SourceInventoryError, generate_source_inventory
from .source_materialization import (
    SourceMaterializationError,
    materialize_local_source,
    materialize_local_sources,
)
from .source_acquisition import (
    SourceAcquisitionError,
    download_source,
    prepare_sources,
    resolve_source_gaps,
)
from .source_catalog import (
    SourceCatalogError,
    copy_and_register_local_source,
    load_project_source_registry,
    load_source_catalog,
    register_local_source,
)
from .source_status import SourceStatusError, resolve_source_status_set
from .spatial_analysis import SpatialAnalysisError, analyze_project
from .tables import TableGenerationError, generate_comparison_tables


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="review-assist", description="Review Assist local workflow tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-project", help="Parse project KMZ/KML inputs and write geometry summaries.")
    inspect_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    inspect_parser.add_argument("--json", action="store_true", help="Print full JSON summary to stdout.")

    list_parser = subparsers.add_parser("list-sources", help="List source catalog entries and optional project status.")
    list_parser.add_argument("project_dir", nargs="?", type=Path, help="Optional project workspace directory.")
    list_parser.add_argument("--json", action="store_true", help="Print full JSON source listing to stdout.")

    import_parser = subparsers.add_parser("import-source", help="Register a local source layer for a project.")
    import_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    import_parser.add_argument("source_id", help="Source id from the global source catalog.")
    import_parser.add_argument("path", type=Path, help="Local path to a geospatial source layer.")
    import_parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy a file-based source layer into projects/<id>/layers/<source_id>/ before registering it.",
    )
    import_parser.add_argument(
        "--replace",
        action="store_true",
        help="With --copy, replace an existing copied project layer for this source id.",
    )

    analyze_parser = subparsers.add_parser("analyze-project", help="Run local source-layer spatial checks for a project.")
    analyze_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    analyze_parser.add_argument("--json", action="store_true", help="Print full JSON analysis result to stdout.")

    geometry_parser = subparsers.add_parser("build-project-geometry", help="Normalize project geometry for constraint analysis.")
    geometry_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    geometry_parser.add_argument("--json", action="store_true", help="Print full JSON project geometry artifact to stdout.")

    comparison_units_parser = subparsers.add_parser(
        "build-comparison-units",
        help="Build report-facing comparison units from normalized project inputs.",
    )
    comparison_units_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    comparison_units_parser.add_argument("--json", action="store_true", help="Print full JSON comparison unit metadata to stdout.")

    input_package_parser = subparsers.add_parser(
        "classify-input-package",
        help="Classify configured project inputs and write the input package artifact.",
    )
    input_package_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    input_package_parser.add_argument("--json", action="store_true", help="Print full JSON input package artifact to stdout.")

    project_area_parser = subparsers.add_parser(
        "build-project-area",
        help="Build project area, county, and basemap provenance context.",
    )
    project_area_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    project_area_parser.add_argument("--json", action="store_true", help="Print full JSON project area artifact to stdout.")

    constraints_parser = subparsers.add_parser("analyze-constraints", help="Run constraint overlap/proximity checks for a project.")
    constraints_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    constraints_parser.add_argument("--json", action="store_true", help="Print full JSON constraint result to stdout.")

    comparison_unit_constraints_parser = subparsers.add_parser(
        "analyze-comparison-unit-constraints",
        help="Run report-facing constraint checks by comparison unit.",
    )
    comparison_unit_constraints_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    comparison_unit_constraints_parser.add_argument("--json", action="store_true", help="Print full JSON comparison-unit constraint result to stdout.")

    context_parser = subparsers.add_parser("generate-context", help="Generate persistent project context for a workspace.")
    context_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    context_parser.add_argument("--json", action="store_true", help="Print full JSON context artifact to stdout.")

    sources_parser = subparsers.add_parser("resolve-sources", help="Resolve project source category statuses for a workspace.")
    sources_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    sources_parser.add_argument("--json", action="store_true", help="Print full JSON source status set to stdout.")

    gaps_parser = subparsers.add_parser("resolve-source-gaps", help="Compare project inputs and registry against the source catalog.")
    gaps_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    gaps_parser.add_argument("--json", action="store_true", help="Print full JSON source acquisition manifest to stdout.")

    download_parser = subparsers.add_parser("download-source", help="Download one supported public source into a project workspace.")
    download_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    download_parser.add_argument("source_id", help="Supported source id to download.")
    download_parser.add_argument("--json", action="store_true", help="Print full JSON source acquisition manifest to stdout.")

    prepare_parser = subparsers.add_parser("prepare-sources", help="Resolve gaps and download supported missing sources.")
    prepare_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    prepare_parser.add_argument(
        "--include-optional-sources",
        action="store_true",
        help="Also download supported optional sources such as FEMA NFHL flood hazard.",
    )
    prepare_parser.add_argument("--json", action="store_true", help="Print full JSON source acquisition manifest to stdout.")

    materialize_parser = subparsers.add_parser(
        "materialize-local-source",
        help="Extract one configured local warehouse source into a project-ready GeoJSON layer.",
    )
    materialize_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    materialize_parser.add_argument("source_id", help="Configured local materializer source id.")
    materialize_parser.add_argument("--replace", action="store_true", help="Replace an existing project-local materialized source.")
    materialize_parser.add_argument("--json", action="store_true", help="Print full JSON materialization manifest to stdout.")

    materialize_all_parser = subparsers.add_parser(
        "materialize-local-sources",
        help="Extract all configured local warehouse sources into project-ready GeoJSON layers.",
    )
    materialize_all_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    materialize_all_parser.add_argument("--replace", action="store_true", help="Replace existing project-local materialized sources.")
    materialize_all_parser.add_argument("--json", action="store_true", help="Print full JSON materialization manifest to stdout.")

    naip_basemap_parser = subparsers.add_parser(
        "materialize-naip-basemap",
        help="Materialize an AOI-clipped project-local NAIP basemap sidecar.",
    )
    naip_basemap_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    naip_basemap_parser.add_argument("--year", type=int, help="Restrict NAIP selection to one acquisition year.")
    naip_basemap_parser.add_argument("--max-pixels", type=int, default=DEFAULT_MAX_PIXELS, help="Maximum output raster pixels to allow.")
    naip_basemap_parser.add_argument("--max-tiles", type=int, default=DEFAULT_MAX_TILES, help="Maximum intersecting NAIP tiles to read.")
    naip_basemap_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Network timeout for STAC and COG access.",
    )
    naip_basemap_parser.add_argument("--refresh", action="store_true", help="Overwrite an existing project-local NAIP sidecar.")
    naip_basemap_parser.add_argument("--force", action="store_true", help="Alias for --refresh.")
    naip_basemap_parser.add_argument(
        "--for-figure-extents",
        action="store_true",
        help="Materialize grouped NAIP sidecars for planned full figure render extents.",
    )
    naip_basemap_parser.add_argument(
        "--extent-class",
        choices=["small_direct", "medium_context", "large_watershed"],
        help="Restrict --for-figure-extents materialization to one planned extent class.",
    )
    naip_basemap_parser.add_argument("--json", action="store_true", help="Print full JSON materialization manifest to stdout.")

    figure_extent_parser = subparsers.add_parser(
        "plan-figure-extents",
        help="Plan presentation-only figure render extents and basemap materialization groups.",
    )
    figure_extent_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    figure_extent_parser.add_argument("--json", action="store_true", help="Print full JSON figure extent plan to stdout.")

    inventory_parser = subparsers.add_parser("generate-source-inventory", help="Generate source inventory and provenance records.")
    inventory_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    inventory_parser.add_argument("--json", action="store_true", help="Print full JSON source inventory artifact to stdout.")

    findings_parser = subparsers.add_parser("generate-findings", help="Generate deterministic draft finding records.")
    findings_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    findings_parser.add_argument("--json", action="store_true", help="Print full JSON draft findings artifact to stdout.")

    tables_parser = subparsers.add_parser("generate-tables", help="Generate comparison table artifacts.")
    tables_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    tables_parser.add_argument("--json", action="store_true", help="Print full JSON comparison tables artifact to stdout.")

    deliverable_tables_parser = subparsers.add_parser(
        "generate-deliverable-tables",
        help="Generate exact matrix-backed deliverable table targets.",
    )
    deliverable_tables_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    deliverable_tables_parser.add_argument("--json", action="store_true", help="Print full JSON deliverable tables artifact to stdout.")

    deliverable_figures_parser = subparsers.add_parser(
        "generate-deliverable-figures",
        help="Generate exact matrix-backed deliverable figure targets.",
    )
    deliverable_figures_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    deliverable_figures_parser.add_argument("--json", action="store_true", help="Print full JSON deliverable figures artifact to stdout.")

    deliverable_items_parser = subparsers.add_parser(
        "generate-deliverable-items",
        help="Generate matrix-backed deliverable item targets for bounded review.",
    )
    deliverable_items_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    deliverable_items_parser.add_argument("--gpt-drafting", action="store_true", help="Explicitly enable legacy GPT section drafting for this run.")
    deliverable_items_parser.add_argument("--no-gpt-drafting", action="store_true", help="Keep deterministic drafting for this run.")
    deliverable_items_parser.add_argument("--gpt-model", help="Override OPENAI_INTERPRETER_MODEL for this run.")
    deliverable_items_parser.add_argument("--json", action="store_true", help="Print full JSON deliverable items artifact to stdout.")

    gpt_drafts_parser = subparsers.add_parser(
        "draft-section-candidates",
        help="Explicitly generate cached GPT-assisted section review candidates.",
    )
    gpt_drafts_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    gpt_drafts_parser.add_argument("--provider", default="gpt", choices=("gpt",), help="Drafting provider to use.")
    gpt_drafts_parser.add_argument("--model", help="Override OPENAI_INTERPRETER_MODEL for this run.")
    gpt_drafts_parser.add_argument("--sections", help="Comma-separated section/target IDs to draft.")
    gpt_drafts_parser.add_argument("--max-calls", type=int, default=5, help="Maximum GPT API calls for this run.")
    gpt_drafts_parser.add_argument("--dry-run", action="store_true", help="Report planned GPT calls without calling the API.")
    gpt_drafts_parser.add_argument("--skip-existing", action=argparse.BooleanOptionalAction, default=True, help="Skip sections with current cached GPT draft provenance.")
    gpt_drafts_parser.add_argument("--source-backed-only", action=argparse.BooleanOptionalAction, default=True, help="Draft only source-backed eligible section_text items.")
    gpt_drafts_parser.add_argument("--force-refresh", action="store_true", help="Ignore cached drafts and call GPT again.")
    gpt_drafts_parser.add_argument("--style-context", type=Path, help="Optional curated style context markdown path.")
    gpt_drafts_parser.add_argument("--json", action="store_true", help="Print full JSON GPT drafting run manifest to stdout.")

    maps_parser = subparsers.add_parser("generate-maps", help="Generate draft static map/figure artifacts.")
    maps_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    maps_parser.add_argument("--json", action="store_true", help="Print full JSON map manifest to stdout.")

    sections_parser = subparsers.add_parser("generate-report-sections", help="Generate draft report section artifacts.")
    sections_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    sections_parser.add_argument("--gpt-drafting", action="store_true", help="Explicitly enable legacy GPT section drafting for this run.")
    sections_parser.add_argument("--no-gpt-drafting", action="store_true", help="Keep deterministic drafting for this run.")
    sections_parser.add_argument("--gpt-model", help="Override OPENAI_INTERPRETER_MODEL for this run.")
    sections_parser.add_argument("--json", action="store_true", help="Print full JSON report sections artifact to stdout.")

    evidence_parser = subparsers.add_parser("build-evidence-package", help="Build source evidence confidence package for report drafting.")
    evidence_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    evidence_parser.add_argument("--json", action="store_true", help="Print full JSON evidence package artifact to stdout.")

    export_parser = subparsers.add_parser("export-report", help="Export reviewed queue items into an editable report package.")
    export_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    export_parser.add_argument(
        "--include-draft",
        action="store_true",
        help="Create an internal preview export that includes unaccepted draft items except rejected items.",
    )
    export_parser.add_argument(
        "--format",
        dest="output_format",
        choices=("markdown", "docx", "both"),
        default="markdown",
        help="Editable export format to generate.",
    )
    export_parser.add_argument("--json", action="store_true", help="Print full JSON export manifest to stdout.")

    demo_parser = subparsers.add_parser(
        "build-demo-deliverable",
        help="Run populate-for-review and export an internal preview deliverable package.",
    )
    demo_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    demo_parser.add_argument(
        "--prepare-sources",
        action="store_true",
        help="Resolve source gaps and run supported public downloaders before constraint analysis.",
    )
    demo_parser.add_argument(
        "--materialize-local-sources",
        action="store_true",
        help="Materialize configured local warehouse sources before public source downloads.",
    )
    demo_parser.add_argument(
        "--include-optional-sources",
        action="store_true",
        help="When used with --prepare-sources, also download supported optional sources.",
    )
    demo_parser.add_argument(
        "--format",
        dest="output_format",
        choices=("markdown", "docx", "both"),
        default="both",
        help="Editable export format to generate for the demo package.",
    )
    demo_parser.add_argument("--gpt-drafting", action="store_true", help="Explicitly enable legacy GPT section drafting during this package run.")
    demo_parser.add_argument("--no-gpt-drafting", action="store_true", help="Keep deterministic drafting for this run.")
    demo_parser.add_argument("--gpt-model", help="Override OPENAI_INTERPRETER_MODEL for this run.")
    demo_parser.add_argument("--json", action="store_true", help="Print full JSON demo deliverable manifest to stdout.")

    mvp_parser = subparsers.add_parser(
        "build-mvp-deliverable",
        help="Run source-backed populate-for-review and export an internal real-data MVP deliverable package.",
    )
    mvp_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    mvp_parser.add_argument(
        "--include-optional-sources",
        action="store_true",
        help="Also download supported optional sources such as FEMA NFHL flood hazard.",
    )
    mvp_parser.add_argument(
        "--materialize-local-sources",
        action="store_true",
        help="Materialize configured local warehouse sources before public source downloads.",
    )
    mvp_parser.add_argument(
        "--fail-on-no-downloaded-sources",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail when no downloaded, provided-in-input, or registered local source layer is available.",
    )
    mvp_parser.add_argument(
        "--format",
        dest="output_format",
        choices=("markdown", "docx", "both"),
        default="both",
        help="Editable export format to generate for the MVP package.",
    )
    mvp_parser.add_argument("--gpt-drafting", action="store_true", help="Explicitly enable legacy GPT section drafting during this package run.")
    mvp_parser.add_argument("--no-gpt-drafting", action="store_true", help="Keep deterministic drafting for this run.")
    mvp_parser.add_argument("--gpt-model", help="Override OPENAI_INTERPRETER_MODEL for this run.")
    mvp_parser.add_argument("--json", action="store_true", help="Print full JSON MVP deliverable manifest to stdout.")

    queue_parser = subparsers.add_parser("generate-review-queue", help="Generate review queue items from workflow artifacts.")
    queue_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    queue_parser.add_argument(
        "--include-source-inventory",
        action="store_true",
        help="Audit mode add-on: include source inventory note items with legacy raw-artifact queue generation.",
    )
    queue_parser.add_argument(
        "--include-legacy-artifacts",
        action="store_true",
        help="Generate legacy/audit queue items from raw findings, tables, maps, report sections, and validation artifacts.",
    )
    queue_parser.add_argument("--json", action="store_true", help="Print full JSON review queue to stdout.")

    list_queue_parser = subparsers.add_parser("list-review-queue", help="List review queue items and counts.")
    list_queue_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    list_queue_parser.add_argument("--json", action="store_true", help="Print full JSON review queue summary to stdout.")

    reset_queue_parser = subparsers.add_parser(
        "reset-review-queue",
        help="Developer/test helper: refresh generated review artifacts and rebuild the standard queue.",
    )
    reset_queue_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    reset_queue_parser.add_argument(
        "--regenerate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refresh deterministic review artifacts and rebuild the standard review queue after deletion.",
    )
    reset_queue_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed and regenerated.")
    reset_queue_parser.add_argument(
        "--include-evidence",
        action="store_true",
        help="Deprecated compatibility flag; evidence is refreshed whenever reset regeneration is enabled.",
    )
    reset_queue_parser.add_argument(
        "--include-exports",
        action="store_true",
        help="Also clear export/package manifests and generated Markdown/DOCX outputs.",
    )
    reset_queue_parser.add_argument("--yes", action="store_true", help="Skip the destructive reset confirmation prompt.")
    reset_queue_parser.add_argument("--json", action="store_true", help="Print full JSON reset summary to stdout.")

    update_item_parser = subparsers.add_parser("update-review-item", help="Update review status and notes for one item.")
    update_item_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    update_item_parser.add_argument("item_id", help="Review queue item id.")
    update_item_parser.add_argument("--status", required=True, help="New review status.")
    update_item_parser.add_argument("--note", help="Reviewer note to append.")
    update_item_parser.add_argument("--edited-content", help="Reviewer-edited content for edited review items.")
    update_item_parser.add_argument("--replacement-content", help="Reviewer replacement content for replaced review items.")
    update_item_parser.add_argument(
        "--export-eligible",
        choices=("true", "false"),
        help="Whether the item is eligible for export.",
    )
    update_item_parser.add_argument("--json", action="store_true", help="Print updated item JSON to stdout.")

    matrix_parser = subparsers.add_parser("validate-deliverable-matrix", help="Validate the deliverable matrix contract.")
    matrix_parser.add_argument("--json", action="store_true", help="Print full JSON validation summary to stdout.")

    prompts_parser = subparsers.add_parser("validate-report-prompts", help="Validate the report prompt contract.")
    prompts_parser.add_argument("--json", action="store_true", help="Print full JSON validation summary to stdout.")

    populate_parser = subparsers.add_parser("populate-for-review", help="Run the current workflow into the review queue.")
    populate_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    populate_parser.add_argument(
        "--prepare-sources",
        action="store_true",
        help="Resolve source gaps and run supported public downloaders before constraint analysis.",
    )
    populate_parser.add_argument(
        "--materialize-local-sources",
        action="store_true",
        help="Materialize configured local warehouse sources before public source downloads.",
    )
    populate_parser.add_argument(
        "--materialize-naip-basemap",
        action="store_true",
        help="Optionally materialize a project-local NAIP basemap sidecar before figure generation.",
    )
    populate_parser.add_argument(
        "--include-optional-sources",
        action="store_true",
        help="When used with --prepare-sources, also download supported optional sources.",
    )
    populate_parser.add_argument("--gpt-drafting", action="store_true", help="Explicitly enable legacy GPT section drafting during populate.")
    populate_parser.add_argument("--no-gpt-drafting", action="store_true", help="Keep deterministic drafting for this run.")
    populate_parser.add_argument("--gpt-model", help="Override OPENAI_INTERPRETER_MODEL for this run.")
    populate_parser.add_argument("--json", action="store_true", help="Print full JSON populate run manifest to stdout.")
    return parser


def inspect_project_command(project_dir: Path, print_json: bool) -> int:
    try:
        summary = inspect_project(project_dir)
    except ProjectInspectionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Inspected project: {summary['project_id']} ({summary['project_name']})")
    print(f"Summary: {summary['summary_path']}")
    for input_summary in summary["inputs"]:
        print(
            "Input: "
            f"{input_summary['input_path']} "
            f"[{input_summary['role']}] - "
            f"{input_summary['feature_count']} features; "
            f"{input_summary['geometry_type_counts']}"
        )
        issues = input_summary.get("validation_issues", [])
        if issues:
            print(f"  Validation issues: {len(issues)}")
    return 0


def list_sources_command(project_dir: Path | None, print_json: bool) -> int:
    try:
        catalog = load_source_catalog()
        registry = load_project_source_registry(project_dir.resolve()) if project_dir else None
    except SourceCatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    project_sources = registry.by_source_id() if registry else {}
    listing = {
        "catalog_version": catalog.catalog_version,
        "project_id": registry.project_id if registry else None,
        "sources": [
            {
                "source_id": source.source_id,
                "name": source.name,
                "category": source.category,
                "publisher": source.publisher,
                "priority": source.priority,
                "access_methods": source.access_methods,
                "project_enabled": project_sources.get(source.source_id).enabled if source.source_id in project_sources else False,
                "project_status": project_sources.get(source.source_id).status if source.source_id in project_sources else "not_registered",
                "project_path": project_sources.get(source.source_id).path if source.source_id in project_sources else None,
            }
            for source in catalog.sorted_sources()
        ],
    }

    if print_json:
        print(json.dumps(listing, indent=2))
        return 0

    project_label = f" for project {registry.project_id}" if registry else ""
    print(f"Source catalog{project_label}: {len(listing['sources'])} entries")
    current_category = None
    for source in listing["sources"]:
        if source["category"] != current_category:
            current_category = source["category"]
            print(f"\n{current_category}")
        status = source["project_status"]
        enabled = "enabled" if source["project_enabled"] else "disabled"
        print(f"  {source['source_id']} - {source['name']} [{source['priority']}; {enabled}; {status}]")
    return 0


def import_source_command(project_dir: Path, source_id: str, source_path: Path, copy_source: bool = False, replace: bool = False) -> int:
    try:
        if copy_source:
            registry = copy_and_register_local_source(project_dir, source_id, source_path, replace=replace)
        else:
            registry = register_local_source(project_dir, source_id, source_path)
    except SourceCatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    registered = registry.by_source_id()[source_id]
    action = "Copied and registered" if copy_source else "Registered"
    print(f"{action} source '{source_id}' for project '{registry.project_id}': {registered.path}")
    return 0


def analyze_project_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = analyze_project(project_dir)
    except SpatialAnalysisError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    relationship_count = len(result["relationships"])
    analyzed_count = sum(1 for source in result["sources"] if source["status"] == "analyzed")
    print(f"Analyzed project: {result['project_id']} ({result['project_name']})")
    print(f"Spatial relationships: {relationship_count}")
    print(f"Analyzed local sources: {analyzed_count}")
    print(f"Output: {result['output_path']}")
    return 0


def build_project_geometry_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = build_project_geometry(project_dir)
    except ProjectGeometryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Built project geometry: {result['project_id']} ({result['project_name']})")
    print(f"Geometry role: {result['geometry_role']}")
    print(f"Features: {result['feature_count']}")
    print(f"Output: {result['output_path']}")
    return 0


def build_comparison_units_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = build_comparison_units(project_dir)
    except ComparisonUnitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Built comparison units: {result['project_id']} ({result['project_name']})")
    print(f"Comparison units: {result['comparison_unit_count']}")
    print(f"Expected count status: {result['expected_count_status']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def classify_input_package_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = classify_input_package(project_dir)
    except InputPackageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Classified input package: {result['project_id']} ({result['project_name']})")
    print(f"Inputs: {result['input_count']}")
    print(f"Required KMZ present: {result['required_kmz_present']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def build_project_area_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = build_project_area(project_dir)
    except ProjectAreaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Built project area: {result['project_id']} ({result['project_name']})")
    print(f"Counties: {', '.join(result['county_names']) if result['county_names'] else '(none detected)'}")
    print(f"Basemap rendering: {result['basemap_rendering_status']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def analyze_constraints_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = analyze_constraints(project_dir)
    except ConstraintAnalysisError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    analyzed_count = sum(1 for source in result["sources"] if source["status"] == "analyzed")
    print(f"Analyzed constraints: {result['project_id']} ({result['project_name']})")
    print(f"Constraints: {result['constraint_count']}")
    print(f"Analyzed local sources: {analyzed_count}")
    print(f"Output: {result['output_path']}")
    return 0


def analyze_comparison_unit_constraints_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = analyze_comparison_unit_constraints(project_dir, tolerate_source_errors=True)
    except ComparisonUnitConstraintError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    analyzed_count = sum(1 for source in result["sources"] if source["status"] == "analyzed")
    print(f"Analyzed comparison-unit constraints: {result['project_id']} ({result['project_name']})")
    print(f"Constraints: {result['constraint_count']}")
    print(f"Analyzed local sources: {analyzed_count}")
    print(f"Output: {result['output_path']}")
    return 0


def generate_context_command(project_dir: Path, print_json: bool) -> int:
    try:
        context = generate_project_context(project_dir)
    except ProjectContextError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(context, indent=2))
        return 0

    print(f"Generated context: {context['project_id']} ({context['project_name']})")
    print(f"Report profile: {context['report_profile']['profile_id']}")
    print(f"Inputs: {len(context['detected_inputs'])}")
    print(f"Validation issues: {len(context['validation_issues'])}")
    print(f"Output: {context['context_path']}")
    return 0


def resolve_sources_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = resolve_source_status_set(project_dir)
    except SourceStatusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    counts: dict[str, int] = {}
    for item in result["statuses"]:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print(f"Resolved sources: {result['project_id']} ({result['project_name']})")
    print(f"Report profile: {result['report_profile']['profile_id']}")
    print(f"Statuses: {counts}")
    print(f"Output: {result['output_path']}")
    return 0


def resolve_source_gaps_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = resolve_source_gaps(project_dir)
    except SourceAcquisitionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Resolved source gaps: {result['project_id']} ({result['project_name']})")
    print(f"Gap statuses: {result['gap_status_counts']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def download_source_command(project_dir: Path, source_id: str, print_json: bool) -> int:
    try:
        result = download_source(project_dir, source_id)
    except SourceAcquisitionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    latest = result["downloads"][-1] if result.get("downloads") else {}
    print(f"Downloaded source workflow: {result['project_id']} ({result['project_name']})")
    print(f"Source: {source_id} [{latest.get('status', 'not_attempted')}]")
    print(f"Features: {latest.get('feature_count', 0)}")
    print(f"Output: {result['output_path']}")
    return 0


def prepare_sources_command(project_dir: Path, print_json: bool, include_optional_sources: bool = False) -> int:
    try:
        result = prepare_sources(project_dir, include_optional_sources=include_optional_sources)
    except SourceAcquisitionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Prepared sources: {result['project_id']} ({result['project_name']})")
    print(f"Gap statuses: {result['gap_status_counts']}")
    print(f"Downloads: {result['download_count']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def materialize_local_source_command(project_dir: Path, source_id: str, replace: bool, print_json: bool) -> int:
    try:
        result = materialize_local_source(project_dir, source_id, replace=replace)
    except SourceMaterializationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    latest = result["sources"][-1] if result.get("sources") else {}
    print(f"Materialized local source workflow: {result['project_id']} ({result['project_name']})")
    print(f"Source: {source_id} [{latest.get('status', 'not_attempted')}]")
    print(f"Features: {latest.get('feature_count', 0)}")
    print(f"Output: {result['output_path']}")
    return 0


def materialize_local_sources_command(project_dir: Path, replace: bool, print_json: bool) -> int:
    try:
        result = materialize_local_sources(project_dir, replace=replace)
    except SourceMaterializationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Materialized local sources: {result['project_id']} ({result['project_name']})")
    print(f"Statuses: {result['status_counts']}")
    print(f"Materialized: {result['materialized_count']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def materialize_naip_basemap_command(
    project_dir: Path,
    *,
    year: int | None,
    max_pixels: int,
    max_tiles: int,
    timeout_seconds: int,
    refresh: bool,
    for_figure_extents: bool,
    extent_class: str | None,
    print_json: bool,
) -> int:
    result = materialize_naip_basemap(
        project_dir,
        year=year,
        max_pixels=max_pixels,
        max_tiles=max_tiles,
        timeout_seconds=timeout_seconds,
        refresh=refresh,
        for_figure_extents=for_figure_extents,
        extent_class=extent_class,
    )
    if print_json:
        print(json.dumps(result, indent=2))
    elif result.get("success"):
        print(f"NAIP basemap materialization: {result['status']}")
        print(f"Source: {result['source_id']}")
        if for_figure_extents:
            print(f"Figure extent plan: {result.get('figure_extent_plan_path')}")
            print(f"Extent groups: {len(result.get('group_results', []))}")
        print(f"Sidecar: {result.get('sidecar_path')}")
        print(f"Metadata: {result.get('metadata_path')}")
        print(f"Output: {result.get('output_path')}")
    else:
        print(f"error: {result.get('message') or 'NAIP basemap materialization failed.'}", file=sys.stderr)
        print(f"Output: {result.get('output_path')}", file=sys.stderr)
    return 0 if result.get("success") else 1


def plan_figure_extents_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = generate_figure_extent_plan(project_dir)
    except DeliverableFigureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if print_json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"Planned figure extents: {result['project_id']} ({result['project_name']})")
    print(f"Figures: {result['figure_count']}")
    print(f"Basemap groups: {len(result.get('basemap_materialization_groups', []))}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def generate_review_queue_command(
    project_dir: Path,
    include_source_inventory: bool,
    include_legacy_artifacts: bool,
    print_json: bool,
) -> int:
    try:
        queue = generate_review_queue(
            project_dir,
            include_source_inventory=include_source_inventory,
            include_legacy_artifacts=include_legacy_artifacts,
        )
    except ReviewQueueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(queue, indent=2))
        return 0

    print(f"Generated review queue: {queue['project_id']} ({queue['project_name']})")
    print(f"Mode: {queue.get('queue_mode', 'deliverable_items')}")
    print(f"Items: {queue['item_count']}")
    print(f"Output: {queue['output_path']}")
    return 0


def reset_review_queue_command(
    project_dir: Path,
    *,
    regenerate: bool,
    dry_run: bool,
    include_evidence: bool,
    include_exports: bool,
    yes: bool,
    print_json: bool,
) -> int:
    if not dry_run and not yes:
        print(f"WARNING: {RESET_WARNING}", file=sys.stderr)
        print("This will overwrite generated deterministic review artifacts and standard review queue state.", file=sys.stderr)
        response = input("Type RESET to continue: ")
        if response.strip() != "RESET":
            print("Reset cancelled.", file=sys.stderr)
            return 2
    try:
        result = reset_review_queue(
            project_dir,
            regenerate=regenerate,
            dry_run=dry_run,
            include_evidence=include_evidence,
            include_exports=include_exports,
        )
    except ReviewQueueResetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    action = "Would reset" if dry_run else "Reset"
    print(f"{action} generated review artifacts.")
    print(f"Warning: {result['warning']}")
    print(f"Before: {result['before'].get('deliverable_item_count', 0)} deliverable items, {result['before'].get('review_queue_item_count', 0)} review items")
    if dry_run:
        print("Would delete:")
        for record in result["would_delete"]:
            print(f"  - {record['relative_path']}")
    else:
        print("Deleted:")
        for record in result["deleted"]:
            print(f"  - {record['relative_path']}")
        print("Regenerated:")
        for record in result["regenerated"]:
            print(f"  - {record['artifact']}: {record.get('item_count', 0)} items")
    after = result["after"]
    print(f"After: {after.get('deliverable_item_count', 0)} deliverable items, {after.get('review_queue_item_count', 0)} review items")
    process_language = result["process_language"]["after"]
    print(f"Process-language remains: {process_language.get('has_process_language', False)}")
    return 0


def generate_source_inventory_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = generate_source_inventory(project_dir)
    except SourceInventoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated source inventory: {result['project_id']} ({result['project_name']})")
    print(f"Records: {result['record_count']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def generate_findings_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = generate_draft_findings(project_dir)
    except FindingGenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated draft findings: {result['project_id']} ({result['project_name']})")
    print(f"Findings: {result['finding_count']}")
    print(f"Output: {result['output_path']}")
    return 0


def generate_tables_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = generate_comparison_tables(project_dir)
    except TableGenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated comparison tables: {result['project_id']} ({result['project_name']})")
    print(f"Tables: {result['table_count']}")
    print(f"Output: {result['output_path']}")
    return 0


def generate_deliverable_tables_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = generate_deliverable_tables(project_dir)
    except DeliverableTableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated deliverable tables: {result['project_id']} ({result['project_name']})")
    print(f"Tables: {result['table_count']}")
    print(f"Output: {result['output_path']}")
    return 0


def generate_deliverable_figures_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = generate_deliverable_figures(project_dir)
    except DeliverableFigureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated deliverable figures: {result['project_id']} ({result['project_name']})")
    print(f"Figures: {result['figure_count']}")
    print(f"Attachment supporting figures: {result['attachment_supporting_figure_count']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def generate_deliverable_items_command(
    project_dir: Path,
    print_json: bool,
    gpt_drafting: bool = False,
    no_gpt_drafting: bool = False,
    gpt_model: str | None = None,
) -> int:
    if gpt_drafting and no_gpt_drafting:
        print("error: choose either --gpt-drafting or --no-gpt-drafting, not both.", file=sys.stderr)
        return 1
    try:
        result = generate_deliverable_items(project_dir, gpt_drafting=bool(gpt_drafting and not no_gpt_drafting), gpt_model=gpt_model)
    except DeliverableItemsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated deliverable items: {result['project_id']} ({result['project_name']})")
    print(f"Items: {result['item_count']}")
    print(f"Expected items: {result['expected_item_count']}")
    print(f"GPT drafting: {result.get('gpt_drafting', {}).get('enabled', False)}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def draft_section_candidates_command(
    project_dir: Path,
    *,
    provider: str,
    model: str | None,
    sections: str | None,
    max_calls: int,
    dry_run: bool,
    skip_existing: bool,
    source_backed_only: bool,
    force_refresh: bool,
    style_context: Path | None,
    print_json: bool,
) -> int:
    try:
        result = draft_section_candidates(
            project_dir,
            provider=provider,
            model=model,
            sections=_comma_list(sections),
            max_calls=max_calls,
            dry_run=dry_run,
            skip_existing=skip_existing,
            source_backed_only=source_backed_only,
            force_refresh=force_refresh,
            style_context_path=style_context,
        )
    except GptInterpretiveAssistError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    mode = "dry run" if dry_run else "GPT draft run"
    print(f"Completed {mode}: {result.get('project_id')} ({result.get('project_name')})")
    print(f"Model: {result.get('model', '')}")
    print(f"Eligible sections: {len(result.get('eligible_sections', []))}")
    print(f"Planned calls: {result.get('planned_call_count', 0)}")
    print(f"Completed calls: {result.get('completed_call_count', 0)}")
    print(f"Accepted GPT drafts: {result.get('accepted_gpt_draft_count', 0)}")
    print(f"Rejected GPT drafts: {result.get('rejected_gpt_draft_count', 0)}")
    print(f"Deterministic fallbacks: {result.get('deterministic_fallback_count', 0)}")
    print(f"Cache hits: {result.get('cache_hit_count', 0)}")
    token_usage = result.get("token_usage", {}) if isinstance(result.get("token_usage"), dict) else {}
    if token_usage:
        print(f"Token usage: {token_usage.get('total_tokens', 0)} total ({token_usage.get('input_tokens', 0)} input, {token_usage.get('output_tokens', 0)} output)")
    print(f"Output: {result.get('output_path', '')}")
    for row in result.get("planned_sections", []):
        if isinstance(row, dict):
            print(f"  - {row.get('target_id')}: {row.get('title')}")
    return 0


def generate_maps_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = generate_maps(project_dir)
    except MapGenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated maps: {result['project_id']} ({result['project_name']})")
    print(f"Figures: {result['figure_count']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def build_evidence_package_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = build_evidence_package(project_dir)
    except EvidencePackageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Built evidence package: {result['project_id']} ({result['project_name']})")
    print(f"Real source records: {result['real_source_count']}")
    print(f"Source-backed constraints: {result['source_backed_constraint_count']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def generate_report_sections_command(
    project_dir: Path,
    print_json: bool,
    gpt_drafting: bool = False,
    no_gpt_drafting: bool = False,
    gpt_model: str | None = None,
) -> int:
    if gpt_drafting and no_gpt_drafting:
        print("error: choose either --gpt-drafting or --no-gpt-drafting, not both.", file=sys.stderr)
        return 1
    try:
        result = generate_report_sections(project_dir, gpt_drafting=bool(gpt_drafting and not no_gpt_drafting), gpt_model=gpt_model)
    except ReportSectionGenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated report sections: {result['project_id']} ({result['project_name']})")
    print(f"Sections: {result['section_count']}")
    print(f"GPT drafting: {result.get('gpt_drafting', {}).get('enabled', False)}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    print(f"Output: {result['output_path']}")
    return 0


def export_report_command(project_dir: Path, include_draft: bool, output_format: str, print_json: bool) -> int:
    try:
        result = export_report(project_dir, include_draft=include_draft, output_format=output_format)
    except ExportGateError as exc:
        if print_json:
            print(json.dumps(exc.details, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
            for item in exc.details.get("unreviewed_items_preview", []):
                if isinstance(item, dict):
                    print(
                        f"  - {item.get('id') or 'unknown'} [{item.get('status', 'unknown')}]: {item.get('title', '')}",
                        file=sys.stderr,
                    )
        return 1
    except ExportQAError as exc:
        if print_json:
            print(json.dumps(exc.details, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
            for issue in exc.details.get("export_qa_issues", [])[:10]:
                if isinstance(issue, dict):
                    suffix = f" on {issue.get('item_id')}" if issue.get("item_id") else ""
                    print(f"  - {issue.get('code', 'export_qa_issue')}{suffix}: {issue.get('message', '')}", file=sys.stderr)
        return 1
    except ExportReportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    label = "preview export" if include_draft else "reviewed-content export"
    print(f"Generated {label}: {result['project_id']} ({result['project_name']})")
    print(f"Review gate: {result.get('review_gate_status', 'unknown')}")
    print(f"Included items: {result['included_count']}")
    print(f"Skipped items: {result['skipped_count']}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    if result.get("markdown_path"):
        print(f"Markdown: {result['markdown_path']}")
    if result.get("docx_path"):
        print(f"DOCX: {result['docx_path']}")
    print(f"Manifest: {result['output_path']}")
    return 0


def build_demo_deliverable_command(
    project_dir: Path,
    print_json: bool,
    prepare_sources_flag: bool = False,
    include_optional_sources: bool = False,
    materialize_local_sources_flag: bool = False,
    output_format: str = "both",
    gpt_drafting: bool = False,
    no_gpt_drafting: bool = False,
    gpt_model: str | None = None,
) -> int:
    if gpt_drafting and no_gpt_drafting:
        print("error: choose either --gpt-drafting or --no-gpt-drafting, not both.", file=sys.stderr)
        return 1
    try:
        result = build_demo_deliverable(
            project_dir,
            prepare_sources=prepare_sources_flag,
            include_optional_sources=include_optional_sources,
            materialize_local_sources=materialize_local_sources_flag,
            output_format=output_format,
            gpt_drafting=bool(gpt_drafting and not no_gpt_drafting),
            gpt_model=gpt_model,
        )
    except DemoDeliverableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated demo deliverable: {result['project_id']} ({result['project_name']})")
    print(f"Included items: {result['included_count']}")
    print(f"GPT drafting: {result.get('gpt_drafting', {}).get('enabled', False)}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    if result.get("markdown_path"):
        print(f"Markdown: {result['markdown_path']}")
    if result.get("docx_path"):
        print(f"DOCX: {result['docx_path']}")
    print(f"Manifest: {result['output_path']}")
    return 0


def build_mvp_deliverable_command(
    project_dir: Path,
    print_json: bool,
    include_optional_sources: bool = False,
    fail_on_no_downloaded_sources: bool = True,
    materialize_local_sources_flag: bool = False,
    output_format: str = "both",
    gpt_drafting: bool = False,
    no_gpt_drafting: bool = False,
    gpt_model: str | None = None,
) -> int:
    if gpt_drafting and no_gpt_drafting:
        print("error: choose either --gpt-drafting or --no-gpt-drafting, not both.", file=sys.stderr)
        return 1
    try:
        result = build_mvp_deliverable(
            project_dir,
            include_optional_sources=include_optional_sources,
            fail_on_no_downloaded_sources=fail_on_no_downloaded_sources,
            materialize_local_sources=materialize_local_sources_flag,
            output_format=output_format,
            gpt_drafting=bool(gpt_drafting and not no_gpt_drafting),
            gpt_model=gpt_model,
        )
    except MvpDeliverableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Generated MVP deliverable: {result['project_id']} ({result['project_name']})")
    print(f"Included items: {result['included_count']}")
    print(f"GPT drafting: {result.get('gpt_drafting', {}).get('enabled', False)}")
    print(f"Validation issues: {len(result['validation_issues'])}")
    lineage = result.get("data_lineage", {}) if isinstance(result.get("data_lineage"), dict) else {}
    print(f"Real source records: {lineage.get('real_source_count', 0)}")
    print(f"Source-backed constraints: {lineage.get('source_backed_constraint_count', 0)}")
    if result.get("markdown_path"):
        print(f"Markdown: {result['markdown_path']}")
    if result.get("docx_path"):
        print(f"DOCX: {result['docx_path']}")
    print(f"Manifest: {result['output_path']}")
    return 0


def list_review_queue_command(project_dir: Path, print_json: bool) -> int:
    try:
        summary = summarize_review_queue(project_dir)
    except ReviewQueueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Review queue: {summary['project_id']} ({summary['project_name']})")
    print(f"Items: {summary['item_count']}")
    print(f"Statuses: {summary['status_counts']}")
    print(f"Types: {summary['type_counts']}")
    for item in summary["items"]:
        print(f"  {item['id']} - {item['title']} [{item['status']}; export={item['export_eligible']}]")
    return 0


def update_review_item_command(
    project_dir: Path,
    item_id: str,
    status: str,
    note: str | None,
    export_eligible: str | None,
    edited_content: str | None,
    replacement_content: str | None,
    print_json: bool,
) -> int:
    try:
        item = update_review_item(
            project_dir,
            item_id,
            status=status,
            note=note,
            export_eligible=_optional_bool(export_eligible),
            edited_content=edited_content,
            replacement_content=replacement_content,
        )
    except ReviewQueueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(item, indent=2))
        return 0

    print(f"Updated review item: {item['id']} [{item['status']}; export={item['export_eligible']}]")
    return 0


def validate_deliverable_matrix_command(print_json: bool) -> int:
    try:
        matrix = validate_deliverable_contract()
        prompts = load_report_prompt_config()
    except (DeliverableMatrixError, ReportPromptConfigError, ReportSectionPolicyConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary = _deliverable_contract_summary(matrix, prompts)
    if print_json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Validated deliverable matrix: {summary['profile_id']} ({summary['matrix_version']})")
    print(f"Sections: {summary['section_target_count']}")
    print(f"Tables: {summary['table_target_count']}")
    print(f"Figures: {summary['figure_target_count']}")
    print(f"Attachments: {summary['attachment_target_count']}")
    print(f"Prompts: {summary['prompt_count']}")
    return 0


def validate_report_prompts_command(print_json: bool) -> int:
    try:
        matrix = validate_deliverable_contract()
        prompts = load_report_prompt_config()
    except (DeliverableMatrixError, ReportPromptConfigError, ReportSectionPolicyConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary = _deliverable_contract_summary(matrix, prompts)
    if print_json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Validated report prompts: {summary['profile_id']} ({summary['prompt_version']})")
    print(f"Prompts: {summary['prompt_count']}")
    print(f"Matrix sections covered: {summary['section_target_count']}")
    print(f"Stub text: {summary['stub_text']}")
    return 0


def _deliverable_contract_summary(matrix, prompts) -> dict[str, object]:
    return {
        "profile_id": matrix.profile_id,
        "matrix_version": matrix.matrix_version,
        "prompt_version": prompts.prompt_version,
        "stub_text": matrix.stub_text,
        "section_target_count": len(matrix.section_targets),
        "table_target_count": len(matrix.table_targets),
        "figure_target_count": len(matrix.figure_targets),
        "attachment_target_count": len(matrix.attachment_targets),
        "prompt_count": len(prompts.prompts),
    }


def populate_for_review_command(
    project_dir: Path,
    print_json: bool,
    prepare_sources_flag: bool = False,
    include_optional_sources: bool = False,
    materialize_local_sources_flag: bool = False,
    materialize_naip_basemap_flag: bool = False,
    gpt_drafting: bool = False,
    no_gpt_drafting: bool = False,
    gpt_model: str | None = None,
) -> int:
    if gpt_drafting and no_gpt_drafting:
        print("error: choose either --gpt-drafting or --no-gpt-drafting, not both.", file=sys.stderr)
        return 1
    try:
        result = populate_for_review(
            project_dir,
            prepare_sources=prepare_sources_flag,
            include_optional_sources=include_optional_sources,
            materialize_local_sources=materialize_local_sources_flag,
            materialize_naip_basemap=materialize_naip_basemap_flag,
            gpt_drafting=bool(gpt_drafting and not no_gpt_drafting),
            gpt_model=gpt_model,
        )
    except PopulateForReviewError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Populated for review: {result['project_id']} ({result['project_name']})")
    print(f"Review queue items: {result['review_queue_item_count']}")
    print(f"GPT drafting: {result.get('gpt_drafting', {}).get('enabled', False)}")
    print(f"Warnings: {len(result['warnings'])}")
    print(f"Output: {result['output_path']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inspect-project":
        return inspect_project_command(args.project_dir, args.json)
    if args.command == "list-sources":
        return list_sources_command(args.project_dir, args.json)
    if args.command == "import-source":
        if args.replace and not args.copy:
            parser.error("--replace requires --copy for import-source.")
        return import_source_command(args.project_dir, args.source_id, args.path, args.copy, args.replace)
    if args.command == "analyze-project":
        return analyze_project_command(args.project_dir, args.json)
    if args.command == "build-project-geometry":
        return build_project_geometry_command(args.project_dir, args.json)
    if args.command == "build-comparison-units":
        return build_comparison_units_command(args.project_dir, args.json)
    if args.command == "classify-input-package":
        return classify_input_package_command(args.project_dir, args.json)
    if args.command == "build-project-area":
        return build_project_area_command(args.project_dir, args.json)
    if args.command == "analyze-constraints":
        return analyze_constraints_command(args.project_dir, args.json)
    if args.command == "analyze-comparison-unit-constraints":
        return analyze_comparison_unit_constraints_command(args.project_dir, args.json)
    if args.command == "generate-context":
        return generate_context_command(args.project_dir, args.json)
    if args.command == "resolve-sources":
        return resolve_sources_command(args.project_dir, args.json)
    if args.command == "resolve-source-gaps":
        return resolve_source_gaps_command(args.project_dir, args.json)
    if args.command == "download-source":
        return download_source_command(args.project_dir, args.source_id, args.json)
    if args.command == "prepare-sources":
        return prepare_sources_command(args.project_dir, args.json, args.include_optional_sources)
    if args.command == "materialize-local-source":
        return materialize_local_source_command(args.project_dir, args.source_id, args.replace, args.json)
    if args.command == "materialize-local-sources":
        return materialize_local_sources_command(args.project_dir, args.replace, args.json)
    if args.command == "materialize-naip-basemap":
        if args.extent_class and not args.for_figure_extents:
            parser.error("--extent-class requires --for-figure-extents for materialize-naip-basemap.")
        return materialize_naip_basemap_command(
            args.project_dir,
            year=args.year,
            max_pixels=args.max_pixels,
            max_tiles=args.max_tiles,
            timeout_seconds=args.timeout_seconds,
            refresh=args.refresh or args.force,
            for_figure_extents=args.for_figure_extents,
            extent_class=args.extent_class,
            print_json=args.json,
        )
    if args.command == "plan-figure-extents":
        return plan_figure_extents_command(args.project_dir, args.json)
    if args.command == "generate-source-inventory":
        return generate_source_inventory_command(args.project_dir, args.json)
    if args.command == "generate-findings":
        return generate_findings_command(args.project_dir, args.json)
    if args.command == "generate-tables":
        return generate_tables_command(args.project_dir, args.json)
    if args.command == "generate-deliverable-tables":
        return generate_deliverable_tables_command(args.project_dir, args.json)
    if args.command == "generate-deliverable-figures":
        return generate_deliverable_figures_command(args.project_dir, args.json)
    if args.command == "generate-deliverable-items":
        return generate_deliverable_items_command(args.project_dir, args.json, args.gpt_drafting, args.no_gpt_drafting, args.gpt_model)
    if args.command == "draft-section-candidates":
        return draft_section_candidates_command(
            args.project_dir,
            provider=args.provider,
            model=args.model,
            sections=args.sections,
            max_calls=args.max_calls,
            dry_run=args.dry_run,
            skip_existing=args.skip_existing,
            source_backed_only=args.source_backed_only,
            force_refresh=args.force_refresh,
            style_context=args.style_context,
            print_json=args.json,
        )
    if args.command == "generate-maps":
        return generate_maps_command(args.project_dir, args.json)
    if args.command == "build-evidence-package":
        return build_evidence_package_command(args.project_dir, args.json)
    if args.command == "generate-report-sections":
        return generate_report_sections_command(args.project_dir, args.json, args.gpt_drafting, args.no_gpt_drafting, args.gpt_model)
    if args.command == "export-report":
        return export_report_command(args.project_dir, args.include_draft, args.output_format, args.json)
    if args.command == "build-demo-deliverable":
        if args.include_optional_sources and not args.prepare_sources:
            parser.error("--include-optional-sources requires --prepare-sources for build-demo-deliverable.")
        return build_demo_deliverable_command(
            args.project_dir,
            args.json,
            args.prepare_sources,
            args.include_optional_sources,
            args.materialize_local_sources,
            args.output_format,
            args.gpt_drafting,
            args.no_gpt_drafting,
            args.gpt_model,
        )
    if args.command == "build-mvp-deliverable":
        return build_mvp_deliverable_command(
            args.project_dir,
            args.json,
            args.include_optional_sources,
            args.fail_on_no_downloaded_sources,
            args.materialize_local_sources,
            args.output_format,
            args.gpt_drafting,
            args.no_gpt_drafting,
            args.gpt_model,
        )
    if args.command == "generate-review-queue":
        return generate_review_queue_command(args.project_dir, args.include_source_inventory, args.include_legacy_artifacts, args.json)
    if args.command == "list-review-queue":
        return list_review_queue_command(args.project_dir, args.json)
    if args.command == "reset-review-queue":
        return reset_review_queue_command(
            args.project_dir,
            regenerate=args.regenerate,
            dry_run=args.dry_run,
            include_evidence=args.include_evidence,
            include_exports=args.include_exports,
            yes=args.yes,
            print_json=args.json,
        )
    if args.command == "update-review-item":
        return update_review_item_command(
            args.project_dir,
            args.item_id,
            args.status,
            args.note,
            args.export_eligible,
            args.edited_content,
            args.replacement_content,
            args.json,
        )
    if args.command == "validate-deliverable-matrix":
        return validate_deliverable_matrix_command(args.json)
    if args.command == "validate-report-prompts":
        return validate_report_prompts_command(args.json)
    if args.command == "populate-for-review":
        if args.include_optional_sources and not args.prepare_sources:
            parser.error("--include-optional-sources requires --prepare-sources for populate-for-review.")
        return populate_for_review_command(
            args.project_dir,
            args.json,
            args.prepare_sources,
            args.include_optional_sources,
            args.materialize_local_sources,
            args.materialize_naip_basemap,
            args.gpt_drafting,
            args.no_gpt_drafting,
            args.gpt_model,
        )
    parser.error(f"Unknown command: {args.command}")
    return 2


def _optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "true"


def _comma_list(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
