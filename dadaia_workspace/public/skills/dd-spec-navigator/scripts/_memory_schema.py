#!/usr/bin/env python3
"""The memory atom's frontmatter rules and the generated pair's path constants.

Stdlib only: `catalog generate`, `check` and the library lint (LINT-1, which loads this
module) parse an atom here alike, through the kernel's one frontmatter grammar, so they
reach one verdict per atom; LINT-1 then applies the JSON schema to the dict this returns.
"""

from __future__ import annotations

import re
from typing import Any

from _frontmatter import parse as parse_block
from _frontmatter import split

CODE = "LEDGER-MEMORY-SCHEMA"
PRODUCT = "memory/product"
INDEX = "memory/product/index.md"
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def parse(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """``(frontmatter, body, error)`` for one atom's text.

    The block is read by the kernel grammar; the atom rules are flat keys, each a
    single-line scalar or a list of them (an empty key is ``[]``).
    """
    parts = split(text)
    if parts is None:
        return None, "", "no YAML frontmatter found"
    try:
        data = parse_block(parts[0])
    except ValueError as exc:
        return None, "", f"frontmatter {exc}"
    for key, value in data.items():
        items = [] if value is None else value if isinstance(value, list) else [value]
        if not all(not isinstance(item, dict | list) and "\n" not in str(item) for item in items):
            return (
                None,
                "",
                f"frontmatter key {key!r} is not a flat single-line value or a list of them",
            )
        data[key] = [] if value is None else value
    return data, parts[1], None
