#!/usr/bin/env python3
"""`product add`: one new memory atom under its canon area directory.

The atom is born complete — the five frontmatter fields come from the command line, so
a freshly added atom passes `check` and enters the catalog on the next `catalog
generate` without a placeholder pass. Adding an atom that already exists is refused
rather than overwritten: an atom is current product truth, never a scaffold to reset.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _memory_catalog import Refusal  # noqa: E402
from _memory_schema import PRODUCT  # noqa: E402

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")
_AREA_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_TEMPLATE = """\
---
slug: {slug}
title: {title}
tldr: {tldr}
summary: {summary}
tags: [{tags}]
---

## Current truth

- Replace this line with what is true of `{slug}` today.

## Implementation

- Name the module that decides each fact above.
"""


def add(specs: Path, area: str, slug: str, values: dict[str, Any]) -> str:
    """Write `memory/product/<area>/<slug>.md` and return the one-line result."""
    if _SLUG_RE.match(slug) is None:
        raise Refusal(
            f"invalid slug {slug!r}: an atom slug is lowercase kebab-case, starting with "
            "a letter (^[a-z][a-z0-9-]+$)",
            f"re-run with a slug like {slug.lower().replace('_', '-')!r}",
        )
    if _AREA_RE.match(area) is None:
        raise Refusal(
            f"invalid area {area!r}: 'memory/product/{area}/{slug}.md' is not a v6-canon "
            "path — an area is lowercase letters/digits/hyphens/underscores",
            "re-run naming one of the areas under specs/memory/product/",
        )
    missing = [
        name for name in ("title", "tldr", "summary") if not (values.get(name) or "").strip()
    ]
    if missing:
        raise Refusal(
            f"an atom is born with its five frontmatter fields; missing: {', '.join(missing)}",
            "--title <title> --tldr <one sentence> --summary <1-2 sentences>",
        )
    path = specs / PRODUCT / area / f"{slug}.md"
    if path.exists():
        raise Refusal(
            f"{path.relative_to(specs).as_posix()} already exists — an atom is current "
            "truth, edited in place, never re-scaffolded",
            f"$EDITOR {path}",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    tags = ", ".join(tag.strip() for tag in (values.get("tags") or area).split(",") if tag.strip())
    path.write_text(
        _TEMPLATE.format(
            slug=slug,
            title=values["title"],
            tldr=values["tldr"],
            summary=values["summary"],
            tags=tags,
        ),  # fmt: skip
        encoding="utf-8",
    )
    return f"[ok] wrote {path.relative_to(specs).as_posix()}"
