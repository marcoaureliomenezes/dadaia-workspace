#!/usr/bin/env python3
"""The catalog's ONE writer: `memory/product/<area>/*.md` frontmatter -> `catalog.json`
and `index.md`'s `## Feature catalog`, the rest kept (`specs/memory/AGENTS.md` §Tree, format,
validation).

One module renders both, so the two cannot drift apart between two writers.

`rank` is the position in sorted-path order — an enumeration aid, NOT a priority.
`token_estimate` is COMPUTED (`word_count * 1.35`): a value both stored and derivable
drifts. `sources` is omitted, never emitted empty — the field arrives atom by atom, and an
empty list in every entry would rewrite a whole consumer catalog for no fact.
`generated_at` records when the CONTENT last changed, not when the command last ran, so
regenerating an unchanged catalog is idempotent to the byte and a clean tree stays clean.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _clock
from _memory_drift import atoms, feature
from _memory_schema import INDEX
from _platform import read_text
from _specs import CATALOG

Catalog = dict[str, Any]


def generate(specs: Path) -> Catalog:
    """The catalog dict for *specs*, `generated_at` carried over when nothing changed."""
    features = [feature(path, specs, rank) for rank, path in enumerate(atoms(specs), start=1)]
    stamp = _stamp(specs, features)
    return {"generated_at": stamp, "features": features}


def _stamp(specs: Path, features: list[dict[str, Any]]) -> str:
    try:
        previous = json.loads(read_text(specs / CATALOG))
    except (OSError, json.JSONDecodeError):
        previous = {}
    if previous.get("features") == features and isinstance(previous.get("generated_at"), str):
        return str(previous["generated_at"])
    return _clock.now_iso()


def catalog_text(catalog: Catalog) -> str:
    return json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"


#: The canonical, ANCHOR-STABLE catalog section heading. Backlog intents bind doc anchors
#: like `memory/product/index.md#feature-catalog` — regeneration never renames it.
HEADING = "## Feature catalog"
_TEMPLATE = """\
# Memory Catalog

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `memory.py catalog generate`; other
> sections of this file are preserved verbatim.

{heading}

{tables}
"""
# No trailing newline: sections are "\n".join-ed, so a trailing "\n" here would insert a
# blank line between the separator row and the first data row, breaking the GFM table.
_HEADER = "| slug | title | tldr |\n|------|-------|------|"


def _tables(catalog: Catalog) -> str:
    """One GFM table per area, areas alphabetical, rows in the catalog's own order."""
    by_area: dict[str, list[str]] = {}
    for entry in catalog.get("features", []):
        row = f"| `{entry['slug']}` | {entry.get('title', '')} | {entry.get('tldr', '')} |"
        by_area.setdefault(str(entry.get("area", "product")), []).append(row)
    sections = [
        f"### {area}\n\n{_HEADER}\n" + "\n".join(rows) for area, rows in sorted(by_area.items())
    ]
    return "\n\n".join(sections) if sections else "_No features found._"


def render(specs: Path, catalog: Catalog) -> str:
    """`index.md` as it should be: ONLY the exact `## Feature catalog` section's body is
    replaced (to the next `## ` heading or EOF); every other line survives verbatim, and an
    index without the section gains it at the end. A missing file is written from the
    template. Exactly one trailing newline: `generate` over a file it had just written must
    agree with `check`."""
    path = specs / INDEX
    rendered = _tables(catalog)
    if not path.is_file():
        return _TEMPLATE.format(heading=HEADING, tables=rendered).rstrip("\n") + "\n"
    lines = read_text(path).splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.strip() == HEADING), len(lines))
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("## ")),
        len(lines),
    )
    head = "".join(lines[:start])
    head = head.rstrip("\n") + "\n\n" if head and start == len(lines) else head
    text = "".join([head, f"{HEADING}\n\n{rendered}\n\n", *lines[end:]])
    return text.rstrip("\n") + "\n"
