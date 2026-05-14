"""Command-line interface for local project inspection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .inspection import ProjectInspectionError, inspect_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="review-assist", description="Review Assist local workflow tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-project", help="Parse project KMZ/KML inputs and write geometry summaries.")
    inspect_parser.add_argument("project_dir", type=Path, help="Path to a project workspace directory.")
    inspect_parser.add_argument("--json", action="store_true", help="Print full JSON summary to stdout.")
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inspect-project":
        return inspect_project_command(args.project_dir, args.json)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

