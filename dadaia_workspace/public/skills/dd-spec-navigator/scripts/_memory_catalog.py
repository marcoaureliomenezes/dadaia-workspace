#!/usr/bin/env python3
"""The generated pair's ONE writer: `memory/product/<area>/*.md` frontmatter ->
`catalog.json` and `index.md`.

Both files are written in one act, so one module renders both: two renderers in two
files were two writers of one fact, and the pair drifted apart between them.

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
    """`index.md` as it should be: ONLY the catalog section's body is replaced (to the next
    `## ` heading or EOF), so every other heading — and every derivable doc anchor — survives
    verbatim; a missing file is written from the template. Exactly one trailing newline in
    either branch: they once differed by a blank line at EOF, and `generate` over a file it
    had just written disagreed with `check` forever."""
    path = specs / INDEX
    existing = read_text(path) if path.is_file() else None
    rendered = _tables(catalog)
    if existing and HEADING in existing:
        lines = existing.splitlines(keepends=True)
        start = next(i for i, line in enumerate(lines) if line.strip() == HEADING)
        end = next(
            (i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("## ")),
            len(lines),
        )
        text = "".join([*lines[:start], f"{HEADING}\n\n{rendered}\n\n", *lines[end:]])
    else:
        text = _TEMPLATE.format(heading=HEADING, tables=rendered)
    return text.rstrip("\n") + "\n"
