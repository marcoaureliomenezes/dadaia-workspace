"""The package's door to the one frontmatter grammar, ``dd-bug-resolution/scripts/_frontmatter.py``
A stdlib strict subset of YAML that equals ``yaml.safe_load`` or refuses.

A memory atom is not read here: its one grammar is the stdlib reader ``memory.py`` ships
(``features/specs/memory_canon.parse_atom``). A failure names its kind (no block, invalid
YAML at line N, not a mapping), never a blanket "missing delimiter".
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from dadaia_workspace.core.skill_owner import load_owner

__all__ = ["Frontmatter", "FrontmatterError", "parse", "split"]

_owner = load_owner("dd-bug-resolution", "_frontmatter")

#: ``(block, body)`` of the leading ``---`` block with a BOM and CRLF normalised, or ``None``.
split: Callable[[str], tuple[str, str] | None] = _owner.split


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
      carries the 1-based line number inside the block the owner's refusal names.
    * ``not_a_mapping`` — the block parses, but to a scalar/list, not a dict.
    """

    kind: Literal["missing_delimiter", "invalid_yaml", "not_a_mapping"]
    message: str
    line: int | None = None


def parse(text: str) -> Frontmatter | FrontmatterError:
    """Parse a leading ``--- ... ---`` frontmatter block out of ``text``.

    Never raises: every failure mode returns a :class:`FrontmatterError` naming its
    ``kind`` instead.
    """
    parts = split(text)
    if parts is None:
        return FrontmatterError(
            kind="missing_delimiter",
            message="No valid YAML frontmatter found (expected --- delimited block).",
        )
    block, body = parts
    try:
        data: dict[str, Any] = _owner.parse(block)
    except _owner.NotAMapping:
        return FrontmatterError(
            kind="not_a_mapping",
            message="Frontmatter block is present but does not parse to a YAML mapping.",
        )
    except ValueError as exc:
        found = re.match(r"line (\d+)", str(exc))
        line = int(found[1]) if found else None
        quoted = f" ({block.split(chr(10))[line - 1].strip()!r})" if line else ""
        return FrontmatterError(
            kind="invalid_yaml",
            message=f"Frontmatter block is present but its YAML is invalid: {exc}{quoted}",
            line=line,
        )
    return Frontmatter(data=data, body=body)
