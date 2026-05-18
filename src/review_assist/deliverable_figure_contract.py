"""Contract validation for matrix-backed deliverable figure artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .deliverable_figure_specs import SUPPORTED_REVIEW_STATUSES
from .deliverable_matrix import REQUIRED_STUB_TEXT


class DeliverableFigureError(RuntimeError):
    """Raised when deliverable figure generation or loading cannot complete."""


def validate_deliverable_figures(data: dict[str, Any], location: str) -> None:
    figures = data.get("figures")
    if not isinstance(figures, list):
        raise DeliverableFigureError(f"Deliverable figures artifact requires a list field named 'figures': {location}")
    if data.get("figure_count") != len(figures):
        raise DeliverableFigureError(f"Deliverable figures artifact figure_count does not match figures: {location}")
    if len(figures) != 13:
        raise DeliverableFigureError(f"Deliverable figures artifact must contain exactly 13 main figures: {location}")
    if not isinstance(data.get("attachment_supporting_figures", []), list):
        raise DeliverableFigureError(f"Deliverable figures artifact attachment_supporting_figures must be a list: {location}")
    if data.get("attachment_supporting_figure_count", 0) != len(data.get("attachment_supporting_figures", [])):
        raise DeliverableFigureError(f"Attachment supporting figure count does not match records: {location}")
    if not isinstance(data.get("validation_issues", []), list):
        raise DeliverableFigureError(f"Deliverable figures artifact validation_issues must be a list: {location}")

    seen_ids: set[str] = set()
    for figure in figures:
        _validate_main_figure(figure, location, seen_ids)

    for figure in data.get("attachment_supporting_figures", []):
        _validate_attachment_figure(figure, location, seen_ids)


def _validate_main_figure(figure: Any, location: str, seen_ids: set[str]) -> None:
    required = {
        "figure_id",
        "type",
        "figure_type",
        "figure_number",
        "title",
        "section_target_id",
        "image_path",
        "file_format",
        "caption",
        "source_note",
        "method_note",
        "map_elements",
        "figure_group",
        "related_resource_categories",
        "shown_layers",
        "source_refs",
        "layer_refs",
        "related_constraint_ids",
        "comparison_unit_ids",
        "provenance",
        "uncertainty_flags",
        "is_stub",
        "stub_text",
        "review_status",
        "validation_issues",
    }
    figure_id = _validate_common_figure_record(
        figure,
        location,
        seen_ids,
        required=required,
        label="Deliverable figure",
    )
    if not isinstance(figure["is_stub"], bool):
        raise DeliverableFigureError(f"Deliverable figure '{figure_id}' is_stub must be boolean: {location}")
    if figure["is_stub"]:
        if figure.get("stub_text") != REQUIRED_STUB_TEXT:
            raise DeliverableFigureError(f"Deliverable figure '{figure_id}' stub_text does not match required stub text: {location}")
    else:
        _validate_existing_image_path(figure, location, figure_id, label="Deliverable figure")
    for list_field in (
        "map_elements",
        "related_resource_categories",
        "shown_layers",
        "source_refs",
        "layer_refs",
        "related_constraint_ids",
        "comparison_unit_ids",
        "uncertainty_flags",
        "validation_issues",
    ):
        if not isinstance(figure[list_field], list):
            raise DeliverableFigureError(f"Deliverable figure '{figure_id}' field '{list_field}' must be a list: {location}")


def _validate_attachment_figure(figure: Any, location: str, seen_ids: set[str]) -> None:
    required = {
        "figure_id",
        "type",
        "figure_type",
        "title",
        "section_target_id",
        "image_path",
        "file_format",
        "caption",
        "source_note",
        "method_note",
        "map_elements",
        "figure_group",
        "shown_layers",
        "source_refs",
        "provenance",
        "uncertainty_flags",
        "review_status",
        "validation_issues",
    }
    figure_id = _validate_common_figure_record(
        figure,
        location,
        seen_ids,
        required=required,
        label="Attachment supporting figure",
    )
    _validate_existing_image_path(figure, location, figure_id, label="Attachment supporting figure")
    for list_field in ("map_elements", "shown_layers", "source_refs", "uncertainty_flags", "validation_issues"):
        if not isinstance(figure[list_field], list):
            raise DeliverableFigureError(f"Attachment supporting figure '{figure_id}' field '{list_field}' must be a list: {location}")


def _validate_common_figure_record(
    figure: Any,
    location: str,
    seen_ids: set[str],
    *,
    required: set[str],
    label: str,
) -> str:
    if not isinstance(figure, dict):
        raise DeliverableFigureError(f"Each {label.lower()} must be an object: {location}")
    missing = sorted(required - set(figure))
    if missing:
        raise DeliverableFigureError(f"{label} is missing required fields {missing}: {location}")
    figure_id = figure["figure_id"]
    if not isinstance(figure_id, str) or not figure_id.strip():
        raise DeliverableFigureError(f"{label} requires a non-empty figure_id: {location}")
    if figure_id in seen_ids:
        raise DeliverableFigureError(f"Duplicate deliverable figure id '{figure_id}': {location}")
    seen_ids.add(figure_id)
    if figure["file_format"] != "png":
        raise DeliverableFigureError(f"{label} '{figure_id}' file_format must be png: {location}")
    if figure["review_status"] not in SUPPORTED_REVIEW_STATUSES:
        raise DeliverableFigureError(f"{label} '{figure_id}' has unsupported review_status: {location}")
    if not isinstance(figure["provenance"], dict):
        raise DeliverableFigureError(f"{label} '{figure_id}' provenance must be an object: {location}")
    return figure_id


def _validate_existing_image_path(figure: dict[str, Any], location: str, figure_id: str, *, label: str) -> None:
    image_path = str(figure.get("image_path", ""))
    if not image_path:
        raise DeliverableFigureError(f"{label} '{figure_id}' requires image_path: {location}")
    if not Path(image_path).exists():
        raise DeliverableFigureError(f"{label} '{figure_id}' image_path does not exist: {image_path}")
