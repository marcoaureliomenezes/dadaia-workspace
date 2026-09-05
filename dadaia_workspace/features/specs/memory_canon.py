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
from pathlib import Path

from dadaia_workspace.core.fixed_sections import (
    FIXED_SECTIONS,
    extract_fixed_section,
    render_fixed_section,
)

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

#: ``specs/``-relative file -> fixed-section id, the lookup view of :data:`FIXED_SECTIONS`.
FIXED_SECTION_BY_PATH: dict[str, str] = dict(FIXED_SECTIONS)

__all__ = [
    "FIXED_SECTIONS",
    "FIXED_SECTION_BY_PATH",
    "FORBIDDEN_MEMORY_HEADING_RE",
    "MEMORY_REQUIRED_FILES",
    "MEMORY_SINGLE_FILE_SLUGS",
    "MEMORY_TOPLEVEL_FILES",
    "WIKILINK_RE",
    "extract_fixed_section",
    "is_forbidden_memory_heading",
    "read_fixed_fragment",
    "render_fixed_section",
]


def read_fixed_fragment(public_dir: Path, section_id: str) -> str:
    """The library fragment of *section_id*: ``<public_dir>/data/fixed/<id>.md``."""
    return (public_dir / "data" / "fixed" / f"{section_id}.md").read_text(encoding="utf-8")


def is_forbidden_memory_heading(heading: str) -> bool:
    """True when *heading* (H2 text, unstripped ok) violates the atomicity contract."""
    return FORBIDDEN_MEMORY_HEADING_RE.search(heading.strip()) is not None
