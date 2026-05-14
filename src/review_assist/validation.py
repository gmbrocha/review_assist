"""Validation issue helpers for reviewable pipeline outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class ValidationIssue:
    """A structured validation issue discovered during ingestion."""

    severity: Severity
    code: str
    message: str
    location: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)

