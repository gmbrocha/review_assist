"""Command-line interface for local project inspection and source checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .findings import FindingGenerationError, generate_draft_findings
from .inspection import ProjectInspectionError, inspect_project
from .populate_for_review import PopulateForReviewError, populate_for_review
from .project_context import ProjectContextError, generate_project_context
from .review_queue import (
    ReviewQueueError,
    generate_review_queue,
    summarize_review_queue,
    update_review_item,
)
from .source_catalog import (
    SourceCatalogError,
    load_project_source_registry,
    load_source_catalog,
    register_local_source,
)
from .source_status import SourceStatusError, resolve_source_status_set
from .spatial_analysis import SpatialAnalysisError, analyze_project


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

    analyze_parser = subparsers.add_parser("analyze-project", help="Run local source-layer spatial checks for a project.")
    analyze_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    analyze_parser.add_argument("--json", action="store_true", help="Print full JSON analysis result to stdout.")

    context_parser = subparsers.add_parser("generate-context", help="Generate persistent project context for a workspace.")
    context_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    context_parser.add_argument("--json", action="store_true", help="Print full JSON context artifact to stdout.")

    sources_parser = subparsers.add_parser("resolve-sources", help="Resolve project source category statuses for a workspace.")
    sources_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    sources_parser.add_argument("--json", action="store_true", help="Print full JSON source status set to stdout.")

    findings_parser = subparsers.add_parser("generate-findings", help="Generate deterministic draft finding records.")
    findings_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    findings_parser.add_argument("--json", action="store_true", help="Print full JSON draft findings artifact to stdout.")

    queue_parser = subparsers.add_parser("generate-review-queue", help="Generate review queue items from workflow artifacts.")
    queue_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    queue_parser.add_argument("--json", action="store_true", help="Print full JSON review queue to stdout.")

    list_queue_parser = subparsers.add_parser("list-review-queue", help="List review queue items and counts.")
    list_queue_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    list_queue_parser.add_argument("--json", action="store_true", help="Print full JSON review queue summary to stdout.")

    update_item_parser = subparsers.add_parser("update-review-item", help="Update review status and notes for one item.")
    update_item_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    update_item_parser.add_argument("item_id", help="Review queue item id.")
    update_item_parser.add_argument("--status", required=True, help="New review status.")
    update_item_parser.add_argument("--note", help="Reviewer note to append.")
    update_item_parser.add_argument(
        "--export-eligible",
        choices=("true", "false"),
        help="Whether the item is eligible for export.",
    )
    update_item_parser.add_argument("--json", action="store_true", help="Print updated item JSON to stdout.")

    populate_parser = subparsers.add_parser("populate-for-review", help="Run the current workflow into the review queue.")
    populate_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
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


def import_source_command(project_dir: Path, source_id: str, source_path: Path) -> int:
    try:
        registry = register_local_source(project_dir, source_id, source_path)
    except SourceCatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    registered = registry.by_source_id()[source_id]
    print(f"Registered source '{source_id}' for project '{registry.project_id}': {registered.path}")
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


def generate_review_queue_command(project_dir: Path, print_json: bool) -> int:
    try:
        queue = generate_review_queue(project_dir)
    except ReviewQueueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(queue, indent=2))
        return 0

    print(f"Generated review queue: {queue['project_id']} ({queue['project_name']})")
    print(f"Items: {queue['item_count']}")
    print(f"Output: {queue['output_path']}")
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
    print_json: bool,
) -> int:
    try:
        item = update_review_item(
            project_dir,
            item_id,
            status=status,
            note=note,
            export_eligible=_optional_bool(export_eligible),
        )
    except ReviewQueueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(item, indent=2))
        return 0

    print(f"Updated review item: {item['id']} [{item['status']}; export={item['export_eligible']}]")
    return 0


def populate_for_review_command(project_dir: Path, print_json: bool) -> int:
    try:
        result = populate_for_review(project_dir)
    except PopulateForReviewError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if print_json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Populated for review: {result['project_id']} ({result['project_name']})")
    print(f"Review queue items: {result['review_queue_item_count']}")
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
        return import_source_command(args.project_dir, args.source_id, args.path)
    if args.command == "analyze-project":
        return analyze_project_command(args.project_dir, args.json)
    if args.command == "generate-context":
        return generate_context_command(args.project_dir, args.json)
    if args.command == "resolve-sources":
        return resolve_sources_command(args.project_dir, args.json)
    if args.command == "generate-findings":
        return generate_findings_command(args.project_dir, args.json)
    if args.command == "generate-review-queue":
        return generate_review_queue_command(args.project_dir, args.json)
    if args.command == "list-review-queue":
        return list_review_queue_command(args.project_dir, args.json)
    if args.command == "update-review-item":
        return update_review_item_command(
            args.project_dir,
            args.item_id,
            args.status,
            args.note,
            args.export_eligible,
            args.json,
        )
    if args.command == "populate-for-review":
        return populate_for_review_command(args.project_dir, args.json)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "true"


if __name__ == "__main__":
    raise SystemExit(main())
