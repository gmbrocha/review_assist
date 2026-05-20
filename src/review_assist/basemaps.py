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
USDA_NAIP_SOURCE_ID = "usda_naip_imagery"
USDA_NAIP_SOURCE_NAME = "USDA NAIP Project Basemap"
PROJECT_LOCAL_NAIP_ROOT = Path("basemaps/naip")
PROJECT_LOCAL_NAIP_FILENAME = "naip_project_basemap.tif"
PROJECT_LOCAL_NAIP_METADATA_FILENAME = "naip_project_basemap.json"
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
    project_local_basemaps = _project_local_basemaps_from_area(project_area, project_area_path.parent.parent)
    selected_paths = flatten_paths(selected_candidates, "sid_paths")
    renderable_paths = _dedupe_paths(
        [
            *[record["path"] for record in project_local_basemaps if record.get("path")],
            *flatten_paths(selected_candidates, "renderable_sidecar_paths"),
        ]
    )
    return {
        "source_id": MARIS_NAIP_SOURCE_ID,
        "source_ids": _dedupe_strings(
            [MARIS_NAIP_SOURCE_ID, *[str(record.get("source_id")) for record in project_local_basemaps if record.get("source_id")]]
        ),
        "project_area_path": str(project_area_path),
        "project_local_basemaps": project_local_basemaps,
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


def discover_project_local_naip_basemaps(project_dir: Path) -> list[dict[str, Any]]:
    """Return renderable NAIP basemap sidecars materialized inside a project workspace."""

    project_dir = project_dir.resolve()
    root = project_dir / PROJECT_LOCAL_NAIP_ROOT
    if not root.exists():
        return []
    records: list[dict[str, Any]] = []
    for metadata_path in sorted(root.glob(f"**/{PROJECT_LOCAL_NAIP_METADATA_FILENAME}")):
        record = _project_local_record_from_metadata(project_dir, metadata_path)
        if record is not None:
            records.append(record)
    for tif_path in sorted(root.glob(f"**/{PROJECT_LOCAL_NAIP_FILENAME}")):
        if any(Path(str(record.get("path"))).resolve() == tif_path.resolve() for record in records):
            continue
        records.append(_minimal_project_local_record(project_dir, tif_path))
    return sorted(records, key=lambda item: (str(item.get("extent_class") or ""), str(item.get("year") or ""), str(item.get("path") or "")), reverse=True)


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


def _project_local_record_from_metadata(project_dir: Path, metadata_path: Path) -> dict[str, Any] | None:
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(metadata, dict):
        return None
    output_path = _metadata_output_path(project_dir, metadata, metadata_path)
    if output_path is None or not output_path.exists() or output_path.suffix.lower() not in RENDERABLE_EXTENSIONS:
        return None
    output_bounds = metadata.get("output_bounds_wgs84") or metadata.get("aoi_bounds_wgs84")
    record: dict[str, Any] = {
        "source_id": str(metadata.get("source_id") or USDA_NAIP_SOURCE_ID),
        "source_name": str(metadata.get("display_name") or USDA_NAIP_SOURCE_NAME),
        "provider": str(metadata.get("provider") or "Microsoft Planetary Computer"),
        "path": str(output_path),
        "metadata_path": str(metadata_path),
        "year": metadata.get("naip_year"),
        "source_datetime": metadata.get("source_datetime"),
        "status": "renderable_sidecar_available",
        "renderable": True,
        "visual_use": "rendered_basemap",
    }
    if str(metadata.get("extent_class") or "").strip():
        record["extent_class"] = str(metadata["extent_class"])
    if str(metadata.get("aoi_source") or "").strip():
        record["aoi_source"] = str(metadata["aoi_source"])
    for key in ("core_extent", "full_render_extent", "collar_side", "render_extent_is_presentation_only"):
        if key in metadata:
            record[key] = metadata[key]
    if isinstance(output_bounds, dict):
        record["metadata_bbox_wgs84"] = output_bounds
    item_ids = metadata.get("item_ids")
    if isinstance(item_ids, list):
        record["item_ids"] = [str(item_id) for item_id in item_ids if str(item_id).strip()]
    return record


def _metadata_output_path(project_dir: Path, metadata: dict[str, Any], metadata_path: Path) -> Path | None:
    raw_path = metadata.get("output_path")
    if isinstance(raw_path, str) and raw_path.strip():
        candidate = Path(raw_path)
        return candidate if candidate.is_absolute() else project_dir / candidate
    fallback = metadata_path.with_name(PROJECT_LOCAL_NAIP_FILENAME)
    return fallback


def _minimal_project_local_record(project_dir: Path, tif_path: Path) -> dict[str, Any]:
    relative_parts: tuple[str, ...] = ()
    try:
        relative_parts = tif_path.relative_to(project_dir / PROJECT_LOCAL_NAIP_ROOT).parts
    except ValueError:
        relative_parts = ()
    year: Any = None
    extent_class: str | None = None
    if len(relative_parts) >= 2:
        if relative_parts[0].isdigit():
            year = relative_parts[0]
        else:
            extent_class = relative_parts[0]
            year = relative_parts[1] if relative_parts[1].isdigit() else None
    return {
        "source_id": USDA_NAIP_SOURCE_ID,
        "source_name": USDA_NAIP_SOURCE_NAME,
        "provider": "Microsoft Planetary Computer",
        "path": str(tif_path),
        "metadata_path": None,
        "year": year,
        "status": "renderable_sidecar_available",
        "renderable": True,
        "visual_use": "rendered_basemap",
        **({"extent_class": extent_class} if extent_class else {}),
    }


def _project_local_basemaps_from_area(project_area: dict[str, Any], project_dir: Path) -> list[dict[str, Any]]:
    records = project_area.get("project_local_basemaps", [])
    if isinstance(records, list):
        cleaned = [dict(record) for record in records if isinstance(record, dict) and str(record.get("path") or "").strip()]
        if cleaned:
            return cleaned
    return discover_project_local_naip_basemaps(project_dir)


def _dedupe_paths(paths: list[str]) -> list[str]:
    return sorted(_dedupe_strings(paths))


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


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
