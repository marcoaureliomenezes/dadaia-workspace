"""Domain model for `dadaia import` — what one `spec-contexts.json` run did (FR13)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportResult:
    registered: tuple[str, ...]
    skipped: tuple[str, ...]
