"""The YAML frontmatter parser for the constitution and release documents.

A memory atom is not read here: its one grammar is the stdlib reader ``memory.py`` ships
(``features/specs/memory_canon.parse_atom``). ``import yaml`` is deferred inside
:func:`parse` so :data:`FRONTMATTER_RE` stays importable with no third-party dependency.
A failure names its kind (no block, invalid YAML at line N, not a mapping), never a
blanket "missing delimiter".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

__all__ = ["Frontmatter", "FrontmatterError", "FRONTMATTER_RE", "parse"]

#: The ONE compiled definition (A10.2 — ``rg '_FRONTMATTER_RE'`` names this line
#: alone). Leading delimiter, DOTALL-captured block, closing delimiter with an
#: OPTIONAL trailing newline (a frontmatter-only file, no body, still matches —
#: the leniency the retired copies relied on).
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)


@dataclass(frozen=True, slots=True)
class Frontmatter:
    """A successfully parsed frontmatter block plus the body text after it."""

    data: dict[str, Any]
    body: str


@dataclass(frozen=True, slots=True)
class FrontmatterError:
    """Why :func:`parse` could not produce a :class:`Frontmatter`.

    ``kind`` distinguishes the three failure shapes a caller needs different
    guidance for:

    * ``missing_delimiter`` — no ``---``-delimited block at the start of the text.
    * ``invalid_yaml`` — a block is present but its YAML fails to parse; ``line``
      carries the 1-based line number inside the block when PyYAML's
      ``problem_mark`` supplies one.
    * ``not_a_mapping`` — the block parses, but to a scalar/list, not a dict.
    """

    kind: Literal["missing_delimiter", "invalid_yaml", "not_a_mapping"]
    message: str
    line: int | None = None


def parse(text: str) -> Frontmatter | FrontmatterError:
    """Parse a leading ``--- ... ---`` YAML frontmatter block out of ``text``.

    Never raises: every failure mode returns a :class:`FrontmatterError` naming its
    ``kind`` instead.
    """
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return FrontmatterError(
            kind="missing_delimiter",
            message="No valid YAML frontmatter found (expected --- delimited block).",
        )

    raw_yaml = match.group(1)
    body = text[match.end() :]

    import yaml  # deferred: keeps this module stdlib-only at import time (A10.2)

    try:
        data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = (mark.line + 1) if mark is not None else None
        location = f" at line {line}" if line is not None else ""
        return FrontmatterError(
            kind="invalid_yaml",
            message=f"Frontmatter block is present but its YAML is invalid{location}: {exc}",
            line=line,
        )

    if not isinstance(data, dict):
        return FrontmatterError(
            kind="not_a_mapping",
            message="Frontmatter block is present but does not parse to a YAML mapping.",
        )

    return Frontmatter(data=data, body=body)
