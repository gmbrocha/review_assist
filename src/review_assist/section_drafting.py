"""Section drafting provider interface.

The current implementation is deterministic. This interface exists so a future
GenAI-backed provider can be added without changing report-section data flow.
"""

from __future__ import annotations

from typing import Protocol


class SectionDraftProvider(Protocol):
    provider_id: str

    def draft(self, *, section_id: str, section_type: str, deterministic_content: str) -> str:
        """Return draft section content for review."""


class DeterministicSectionDraftProvider:
    provider_id = "deterministic"

    def draft(self, *, section_id: str, section_type: str, deterministic_content: str) -> str:
        return deterministic_content


def default_section_draft_provider() -> SectionDraftProvider:
    return DeterministicSectionDraftProvider()
