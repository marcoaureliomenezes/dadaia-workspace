"""The ONE frontmatter parser (v0.5.1 T-051-16, K10).

Before this module, seven files each carried their own copy of a ``--- ... ---``
delimiter regex plus a hand-rolled ``yaml.safe_load`` + dict-check loop:
``features/specs/{memory_lint,catalog,doctor_memory}.py``,
``features/panel/views/memory.py``, ``features/migrate/bugs_jsonl.py`` (deleted with
its module, T-051-16), ``core/specs_version.py``, and the projected
``public/scripts/generate-memory-catalog.py`` (deleted, T-051-16). Six of those
survive as consumers of THIS module; ``core/specs_version.py`` imports only
:data:`FRONTMATTER_RE` (never :func:`parse`) — its bare-``python3 -c`` CI shell-out
(``.github/scripts/pr-verdict-check.sh``) must import the module with zero
third-party dependencies, so ``import yaml`` here is deferred INSIDE :func:`parse`,
never at module level (A10.2).

Fixes bug ``memory-lint-blames-missing-delimiter-for-a-yaml-parse-error``: the old
``_parse_frontmatter`` copies collapsed every failure mode — no delimiter, a present
block with invalid YAML, a present block that parses to a non-mapping — into the
same ``None`` return, so the caller always blamed "no delimited block" even when a
YAML syntax error (with its own precise line/column) was the real cause. ``parse()``
below returns a :class:`FrontmatterError` that NAMES which of the three happened,
carrying the parser's own line number for the ``invalid_yaml`` case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

__all__ = ["Frontmatter", "FrontmatterError", "FRONTMATTER_RE", "missing_fields", "parse"]

#: The ONE compiled definition (A10.2 — ``rg '_FRONTMATTER_RE'`` names this line
#: alone). Leading delimiter, DOTALL-captured block, closing delimiter with an
#: OPTIONAL trailing newline (a frontmatter-only file, no body, still matches —
#: the leniency ``features/panel/views/memory.py``'s copy already relied on).
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


def missing_fields(data: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    """Every name in ``required`` absent from ``data``, in ``required`` order.

    A generic presence check — never a partial one. Exists because
    ``jsonschema.validate()`` (single-error) reports only the FIRST missing
    ``required`` property, which is the checker half of bug
    ``memory-trio-missing-required-frontmatter-fields``: an author fixing one
    missing field at a time never sees the next one until they re-run. Callers
    that want full schema conformance (patterns/enums/types) still validate
    against the JSON schema separately; this helper is for the "which field(s)
    are missing" question alone.
    """
    return [name for name in required if name not in data]
