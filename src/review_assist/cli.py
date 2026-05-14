"""Command-line interface for local project inspection and source checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .inspection import ProjectInspectionError, inspect_project
from .source_catalog import (
    SourceCatalogError,
    load_project_source_registry,
    load_source_catalog,
    register_local_source,
)
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
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
