"""Memory-canon facts — ONE home (F011, 20260830-design-bug-surface-audit).

Leaf module (stdlib only): the memory tree's shape facts were multiplied across
``canon.py`` (CanonEntry rows), ``doctor_structural.py`` (TREE-3 list),
``doctor_memory.py`` (top-level trio + forbidden-heading regex + wikilink regex),
``memory_lint.py`` (already-divergent exact-match heading frozenset + slug→file map +
wikilink regex) and ``catalog.py`` (wikilink regex). Every consumer now imports these
objects; a re-typed copy is the duplicated-decider class the bug ledger's fix-induced
chains grew from.
"""

from __future__ import annotations

import re

#: Memory slug → canonical top-level filename (the three ADR-gated Part-1/Part-2 docs).
#: The ONE table; the file tuples below are derived views, never hand-kept copies.
MEMORY_SINGLE_FILE_SLUGS: dict[str, str] = {
    "architecture": "ARCHITECTURE.md",
    "tech-stack": "TECHSTACK.md",
    "quality-assurance": "QUALITY.md",
}

#: Top-level memory files (.md canonical source; v6 canon FR1/A1.5/A1.6, T-050-06).
MEMORY_TOPLEVEL_FILES: tuple[str, ...] = tuple(MEMORY_SINGLE_FILE_SLUGS.values())

#: Memory files that must exist (TREE-3): the top-level trio plus the product index.
MEMORY_REQUIRED_FILES: tuple[str, ...] = (*MEMORY_TOPLEVEL_FILES, "product/index.md")

#: Forbidden memory H2 headings: changelog/history sections violate the atomicity
#: contract (specs/memory/AGENTS.md §3) regardless of prose policy. Prefix match,
#: case-insensitive, accented and unaccented forms — the ONE matcher (the retired
#: memory_lint frozenset silently passed singular 'Version' and 'Historico').
FORBIDDEN_MEMORY_HEADING_RE = re.compile(
    r"^(Changelog|History|Hist[óo]rico|Versions?)\b", re.IGNORECASE
)

#: Wikilink grammar for memory atoms: ``[[slug]]``.
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def is_forbidden_memory_heading(heading: str) -> bool:
    """True when *heading* (H2 text, unstripped ok) violates the atomicity contract."""
    return FORBIDDEN_MEMORY_HEADING_RE.search(heading.strip()) is not None
