#!/usr/bin/env python3
"""The memory atom's frontmatter reader and the generated pair's path constants.

The block is read without a YAML dependency, for the catalog writer alone: VALIDATING it
is the library lint's fact (`features/specs/memory_lint.py`, the doctor's LINT-1), and a
second validator here was a second decider of the same fact.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

CODE = "LEDGER-MEMORY-SCHEMA"
PRODUCT = "memory/product"
CATALOG = "memory/product/catalog.json"
INDEX = "memory/product/index.md"
_DELIMITER = "---"
_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s?(.*)$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def find_specs(start: Path) -> Path:
    """The nearest ``specs/`` at or above *start* whose parent holds ``.git``."""
    for candidate in (start, *start.parents):
        if (candidate / "specs").is_dir() and (candidate / ".git").exists():
            return candidate / "specs"
    print(f"error: no git-rooted specs/ at or above {start}", file=sys.stderr)
    print("fix: run this script again with --specs <path-to-specs>", file=sys.stderr)
    raise SystemExit(1)


def _scalar(raw: str) -> str | list[str]:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_unquote(item.strip()) for item in inner.split(",") if item.strip()]
    return _unquote(value)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """``(frontmatter, body, error)`` for one atom's text.

    The block is the lines between the first two ``---`` delimiters: one ``key: value``
    per line, a value being a plain scalar or an inline ``[a, b]`` list, plus the
    ``- item`` block-list form. Anything else is an error, not a guess.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != _DELIMITER:
        return None, "", "no YAML frontmatter found"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == _DELIMITER)
    except StopIteration:
        return None, "", "the frontmatter block is never closed by a '---' line"
    data: dict[str, Any] = {}
    key: str | None = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and key is not None:
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(_unquote(line.lstrip()[2:].strip()))
            continue
        match = _KEY_RE.match(line)
        if match is None:
            return None, "", f"frontmatter line {line!r} is not 'key: value'"
        key = match.group(1)
        data[key] = _scalar(match.group(2)) if match.group(2).strip() else []
    return data, "\n".join(lines[end + 1 :]), None
