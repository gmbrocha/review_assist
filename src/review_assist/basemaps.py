"""Local basemap index and renderability helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .source_catalog import repo_root


AERIAL_BASEMAP_ROOT = Path("sources/aerial_base_maps/maris_naip_2025")
MARIS_NAIP_SOURCE_ID = "maris_naip_2025_imagery"
MARIS_NAIP_SOURCE_NAME = "MARIS/NAIP 2025 Imagery"
RENDERABLE_EXTENSIONS = {".tif", ".tiff", ".png"}


def build_basemap_index(root: Path | None = None) -> dict[str, Any]:
    """Index the local MARIS/NAIP warehouse without decoding MrSID rasters."""

    basemap_root = resolved_basemap_root(root)
    validation_issues: list[dict[str, Any]] = []
    candidates = _index_candidates(basemap_root)
    if not basemap_root.exists():
        validation_issues.append(
            _issue(
                "warning",
                "aerial_basemap_root_missing",
                "Local MARIS/NAIP aerial basemap root is not available.",
                str(basemap_root),
            )
        )
    return {
        "source_id": MARIS_NAIP_SOURCE_ID,
        "source_name": MARIS_NAIP_SOURCE_NAME,
        "basemap_root": str(basemap_root),
        "exists": basemap_root.exists(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "validation_issues": validation_issues,
    }


def index_maris_naip_basemaps(root: Path | None = None) -> list[dict[str, Any]]:
    """Return county candidate records for compatibility with project-area code."""

    return list(build_basemap_index(root)["candidates"])


def select_project_basemaps(project_dir: Path) -> dict[str, Any]:
    """Select already-indexed basemap candidates from an existing project-area artifact."""

    project_area_path = project_dir.resolve() / "context" / "project_area.json"
    if not project_area_path.exists():
        return {
            "source_id": MARIS_NAIP_SOURCE_ID,
            "project_area_path": str(project_area_path),
            "selected_candidates": [],
            "selected_basemap_paths": [],
            "renderable_basemap_paths": [],
            "basemap_rendering_status": "not_available",
            "validation_issues": [
                _issue(
                    "warning",
                    "project_area_unavailable_for_basemap_selection",
                    "Project area artifact is required before project basemap selection can be resolved.",
                    str(project_area_path),
                )
            ],
        }
    try:
        project_area = json.loads(project_area_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "source_id": MARIS_NAIP_SOURCE_ID,
            "project_area_path": str(project_area_path),
            "selected_candidates": [],
            "selected_basemap_paths": [],
            "renderable_basemap_paths": [],
            "basemap_rendering_status": "not_available",
            "validation_issues": [
                _issue(
                    "warning",
                    "project_area_invalid_for_basemap_selection",
                    f"Project area artifact could not be parsed for basemap selection: {exc}",
                    str(project_area_path),
                )
            ],
        }
    candidates = project_area.get("aerial_basemap_candidates", []) if isinstance(project_area, dict) else []
    county_names = project_area.get("county_names", []) if isinstance(project_area, dict) else []
    selected_candidates = select_basemap_candidates(
        [str(name) for name in county_names if str(name).strip()] if isinstance(county_names, list) else [],
        [dict(candidate) for candidate in candidates if isinstance(candidate, dict)] if isinstance(candidates, list) else [],
    )
    selected_paths = flatten_paths(selected_candidates, "sid_paths")
    renderable_paths = flatten_paths(selected_candidates, "renderable_sidecar_paths")
    return {
        "source_id": MARIS_NAIP_SOURCE_ID,
        "project_area_path": str(project_area_path),
        "selected_candidates": selected_candidates,
        "selected_basemap_paths": selected_paths,
        "renderable_basemap_paths": renderable_paths,
        "basemap_rendering_status": basemap_rendering_status(selected_candidates, selected_paths, renderable_paths),
        "validation_issues": [],
    }


def renderable_sidecars_for(candidate: dict[str, Any]) -> list[Path]:
    """Return renderable sidecar paths for a single indexed candidate."""

    values = candidate.get("renderable_sidecar_paths", [])
    if not isinstance(values, list):
        return []
    return [Path(str(value)) for value in values if str(value).strip()]


def select_basemap_candidates(county_names: list[str], basemap_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    county_keys = {county_key(name) for name in county_names}
    if not county_keys:
        return []
    return [candidate for candidate in basemap_candidates if county_key(str(candidate.get("county_name", ""))) in county_keys]


def flatten_paths(records: list[dict[str, Any]], key: str) -> list[str]:
    paths: list[str] = []
    for record in records:
        values = record.get(key, [])
        if isinstance(values, list):
            paths.extend(str(value) for value in values if str(value).strip())
    return sorted(paths)


def basemap_rendering_status(
    selected_candidates: list[dict[str, Any]],
    selected_basemap_paths: list[str],
    renderable_basemap_paths: list[str],
) -> str:
    if renderable_basemap_paths:
        return "renderable_sidecar_available"
    if selected_basemap_paths:
        return "selected_not_renderable"
    if selected_candidates:
        return "not_available"
    return "not_available"


def naip_metadata_counties(project_bbox: dict[str, Any], basemap_candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    matched: list[dict[str, Any]] = []
    for candidate in basemap_candidates:
        metadata_bbox = candidate.get("metadata_bbox_wgs84")
        if not isinstance(metadata_bbox, dict):
            continue
        if bboxes_intersect(project_bbox, metadata_bbox):
            matched.append(candidate)
    if not matched:
        return None
    return {
        "method": "naip_maris_metadata_extent",
        "county_names": sorted(format_county_name(str(candidate["county_name"])) for candidate in matched),
        "source_id": MARIS_NAIP_SOURCE_ID,
        "source_path": common_root([str(candidate["county_dir"]) for candidate in matched]),
        "candidate_count": len(matched),
        "confidence": "medium",
    }


def resolved_basemap_root(root: Path | None = None) -> Path:
    path = root or AERIAL_BASEMAP_ROOT
    if path.is_absolute():
        return path
    return (repo_root() / path).resolve()


def format_county_name(raw_name: str) -> str:
    name = " ".join(str(raw_name).replace("_", " ").split())
    if not name:
        return ""
    if name.lower().endswith(" county"):
        return name
    if name.lower().endswith(" co"):
        name = name[:-3].strip()
    return f"{name} County"


def county_key(name: str) -> str:
    normalized = format_county_name(name).lower()
    if normalized.endswith(" county"):
        normalized = normalized[: -len(" county")]
    return "".join(character for character in normalized if character.isalnum())


def common_root(paths: list[str]) -> str | None:
    if not paths:
        return None
    try:
        return str(Path(paths[0]).parent if len(paths) == 1 else Path(paths[0]).parents[1])
    except IndexError:
        return str(paths[0])


def bboxes_intersect(left: dict[str, Any], right: dict[str, Any]) -> bool:
    try:
        return not (
            float(left["east"]) < float(right["west"])
            or float(left["west"]) > float(right["east"])
            or float(left["north"]) < float(right["south"])
            or float(left["south"]) > float(right["north"])
        )
    except (KeyError, TypeError, ValueError):
        return False


def _index_candidates(basemap_root: Path) -> list[dict[str, Any]]:
    if not basemap_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for county_dir in sorted((path for path in basemap_root.iterdir() if path.is_dir()), key=lambda item: item.name.lower()):
        files = sorted((path for path in county_dir.rglob("*") if path.is_file()), key=lambda item: str(item).lower())
        sid_paths = [path for path in files if path.suffix.lower() == ".sid"]
        metadata_paths = [
            path
            for path in files
            if path.suffix.lower() in {".xml", ".txt"} or path.name.lower().endswith(".sid.aux.xml")
        ]
        world_file_paths = [path for path in files if path.suffix.lower() == ".sdw"]
        renderable_sidecar_paths = [path for path in files if path.suffix.lower() in RENDERABLE_EXTENSIONS]
        imagery_dir = _imagery_dir(county_dir, files)
        records.append(
            {
                "county_name": format_county_name(county_dir.name),
                "county_dir": str(county_dir),
                "imagery_dir": str(imagery_dir),
                "sid_paths": [str(path) for path in sid_paths],
                "metadata_paths": [str(path) for path in metadata_paths],
                "world_file_paths": [str(path) for path in world_file_paths],
                "renderable_sidecar_paths": [str(path) for path in renderable_sidecar_paths],
                "metadata_bbox_wgs84": _first_metadata_bbox(metadata_paths),
                "status": _candidate_status(sid_paths, renderable_sidecar_paths, metadata_paths),
            }
        )
    return records


def _imagery_dir(county_dir: Path, files: list[Path]) -> Path:
    for file_path in files:
        try:
            relative = file_path.relative_to(county_dir)
        except ValueError:
            continue
        if len(relative.parts) > 1:
            return county_dir / relative.parts[0]
    return county_dir


def _candidate_status(sid_paths: list[Path], renderable_paths: list[Path], metadata_paths: list[Path]) -> str:
    if renderable_paths:
        return "renderable_sidecar_available"
    if sid_paths:
        return "selected_not_renderable"
    if metadata_paths:
        return "metadata_only"
    return "empty"


def _first_metadata_bbox(metadata_paths: list[Path]) -> dict[str, float] | None:
    for path in metadata_paths:
        if path.suffix.lower() != ".xml":
            continue
        bbox = _metadata_bbox(path)
        if bbox is not None:
            return bbox
    return None


def _metadata_bbox(path: Path) -> dict[str, float] | None:
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None
    keys = {
        "westBoundLongitude": "west",
        "eastBoundLongitude": "east",
        "southBoundLatitude": "south",
        "northBoundLatitude": "north",
    }
    values: dict[str, float] = {}
    for element in root.iter():
        key = keys.get(_local_name(element.tag))
        if key is None:
            continue
        value = _first_float_descendant(element)
        if value is not None:
            values[key] = value
    if set(values) != {"west", "east", "south", "north"}:
        return None
    return values


def _first_float_descendant(element: ET.Element) -> float | None:
    for child in element.iter():
        if child.text is None:
            continue
        text = child.text.strip()
        if not text:
            continue
        try:
            return float(text)
        except ValueError:
            continue
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _issue(severity: str, code: str, message: str, location: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "location": location,
    }
