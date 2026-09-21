#!/usr/bin/env python3
"""The `index.md` renderer: one GFM table per area, merged anchor-stably.

When the file already carries the canonical `## Feature catalog` heading, ONLY that
section's body is replaced (up to the next `## ` heading or EOF) — every other heading,
and therefore every derivable doc anchor, survives regeneration verbatim. A missing file
is written fresh from the template below.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _memory_schema import INDEX  # noqa: E402

#: The canonical, ANCHOR-STABLE catalog section heading. Backlog intents bind doc
#: anchors like `memory/product/index.md#feature-catalog` — regeneration never renames it.
HEADING = "## Feature catalog"
_TEMPLATE = """\
# Memory Catalog — {context}

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `memory.py catalog generate`; other
> sections of this file are preserved verbatim.

{heading}

{tables}
"""
_ROW = "| `{slug}` | {title} | {tldr} |"
# No trailing newline: sections are "\n".join-ed, so a trailing "\n" here would insert a
# blank line between the separator row and the first data row, breaking the GFM table.
_HEADER = "| slug | title | tldr |\n|------|-------|------|"


def tables(catalog: dict[str, Any]) -> str:
    by_area: dict[str, list[dict[str, Any]]] = {}
    for entry in catalog.get("features", []):
        by_area.setdefault(str(entry.get("area", "product")), []).append(entry)
    sections: list[str] = []
    for area in sorted(by_area):
        lines = [f"### {area}\n", _HEADER]
        lines.extend(
            _ROW.format(slug=e["slug"], title=e["title"], tldr=e.get("tldr", ""))
            for e in by_area[area]
        )
        sections.append("\n".join(lines))
    return "\n\n".join(sections) if sections else "_No features found._"


def merge(existing: str | None, rendered: str, context: str) -> str:
    """The regenerated tables inside *existing*, anchor-stable."""
    if existing and HEADING in existing:
        lines = existing.splitlines(keepends=True)
        start = next(i for i, line in enumerate(lines) if line.strip() == HEADING)
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if lines[index].lstrip().startswith("## "):
                end = index
                break
        return "".join([*lines[:start], f"{HEADING}\n\n{rendered}\n\n", *lines[end:]])
    return _TEMPLATE.format(context=context, heading=HEADING, tables=rendered)


def render(specs: Path, catalog: dict[str, Any]) -> str:
    path = specs / INDEX
    existing = path.read_text(encoding="utf-8") if path.is_file() else None
    text = merge(existing, tables(catalog), str(catalog.get("context", "")))
    # Exactly one trailing newline, whichever branch `merge` took: the fresh template and
    # the section-replacement path used to differ by a blank line at EOF, so `generate`
    # over a file it had just written disagreed with `check` forever.
    return text.rstrip("\n") + "\n"
