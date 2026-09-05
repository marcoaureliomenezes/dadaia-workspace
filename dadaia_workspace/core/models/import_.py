"""Domain model for `dadaia import` — what one `spec-contexts.json` run did (FR13)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportResult:
    registered: tuple[str, ...]
    #: ``(name, reason)`` — ``"exists"`` for a known name, else the registry guard's refusal.
    skipped: tuple[tuple[str, str], ...]
