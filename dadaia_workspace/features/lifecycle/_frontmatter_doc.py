"""Shared frontmatter-document base for the lifecycle loaders (loader DRY).

Both the fragment library (``fragments/loader.py``) and the persona library
(``personas/loader.py``) are markdown documents with a YAML frontmatter block and
a harness-universal body. The three mechanics they share — splitting the
frontmatter, validating the str/list typed keys, and linting the body for
harness-specific tokens — live here ONCE so neither loader re-implements them
(architect MEDIUM — preferred over recording the duplication as deliberate).

Each loader parameterizes the base with its own schema (required / str / list keys),
its own validation-error class, and a noun used verbatim in the diagnostic messages,
so the per-loader messages stay precise and byte-identical to the pre-refactor text.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FRONTMATTER_DELIM = "---"

#: Case-insensitive harness-specific tokens forbidden in a universal document body.
#: Each entry is a literal substring matched case-insensitively against the body. A
#: fragment OR a persona body that names one of these must read identically across PI,
#: Codex, and Claude workers, so the token is rejected.
_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "read tool",
    "write tool",
    "edit tool",
    "bash tool",
    "codex exec",
    "pi --mode",
    "pi --model",
    "claude code",
    "claude-code",
    ".claude/",
    ".codex/",
    ".opencode/",
    "--output-last-message",
    "message_end",
    "apply_patch",
    "--ignore-user-config",
)

_HARNESS_TOKEN_RE = re.compile("|".join(re.escape(t) for t in _FORBIDDEN_TOKENS), re.IGNORECASE)


def forbidden_token_in(text: str) -> str | None:
    """Return the first forbidden harness-specific token found in *text*, else None."""
    match = _HARNESS_TOKEN_RE.search(text)
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# Base loader
# ---------------------------------------------------------------------------


class FrontmatterDocLoader:
    """Generic frontmatter-document loader: split + key validation + token lint.

    Subclasses MUST set the following class attributes:

    * ``_NOUN`` / ``_NOUN_PLURAL`` — the singular/plural noun used in messages
      (e.g. ``"fragment"`` / ``"fragments"``).
    * ``_ERROR`` — the :class:`Exception` subclass raised on a validation failure.
    * ``_REQUIRED_KEYS`` — the required frontmatter keys, in declaration order.
    * ``_STR_KEYS`` — keys whose value must be a non-empty ``str``.
    * ``_LIST_KEYS`` — keys whose value must be a ``list`` of ``str``.

    The base provides ``_split_frontmatter``, ``_validate_metadata``, and
    ``_lint_body``; concrete loaders compose them in their own ``_load_path``.
    """

    _NOUN: str = "document"
    _NOUN_PLURAL: str = "documents"
    _ERROR: type[Exception] = ValueError
    _REQUIRED_KEYS: tuple[str, ...] = ()
    _STR_KEYS: frozenset[str] = frozenset()
    _LIST_KEYS: frozenset[str] = frozenset()

    # -- frontmatter split ----------------------------------------------------

    def _split_frontmatter(self, text: str, path: Path) -> tuple[dict[str, object], str]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
            raise self._ERROR(
                f"{path}: {self._NOUN} is missing the opening YAML frontmatter delimiter '---'"
            )
        buffer: list[str] = []
        body_start: int | None = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == _FRONTMATTER_DELIM:
                body_start = index + 1
                break
            buffer.append(line)
        if body_start is None:
            raise self._ERROR(
                f"{path}: {self._NOUN} frontmatter is not closed by a second '---' line"
            )
        try:
            parsed = yaml.safe_load("\n".join(buffer))
        except yaml.YAMLError as exc:
            raise self._ERROR(f"{path}: invalid YAML frontmatter: {exc}") from exc
        if not isinstance(parsed, dict):
            raise self._ERROR(
                f"{path}: {self._NOUN} frontmatter must be a YAML mapping, "
                f"got {type(parsed).__name__}"
            )
        body = "\n".join(lines[body_start:]).strip()
        return parsed, body

    # -- metadata validation --------------------------------------------------

    def _validate_metadata(self, meta: dict[str, object], path: Path) -> None:
        missing = [key for key in self._REQUIRED_KEYS if key not in meta]
        if missing:
            raise self._ERROR(
                f"{path}: {self._NOUN} metadata is missing required key(s): {', '.join(missing)}"
            )
        for key in self._STR_KEYS:
            value = meta[key]
            if not isinstance(value, str) or not value.strip():
                raise self._ERROR(
                    f"{path}: {self._NOUN} metadata key '{key}' must be a non-empty string, "
                    f"got {type(value).__name__}"
                )
        for key in self._LIST_KEYS:
            value = meta[key]
            if not isinstance(value, list):
                raise self._ERROR(
                    f"{path}: {self._NOUN} metadata key '{key}' must be a list, "
                    f"got {type(value).__name__}"
                )
            for item in value:
                if not isinstance(item, str):
                    raise self._ERROR(
                        f"{path}: {self._NOUN} metadata key '{key}' must contain only strings, "
                        f"found {type(item).__name__}"
                    )

    # -- harness-universal token lint -----------------------------------------

    def _lint_body(self, body: str, path: Path) -> None:
        haystack = body.lower()
        for token in _FORBIDDEN_TOKENS:
            if token in haystack:
                raise self._ERROR(
                    f"{path}: {self._NOUN} body contains harness-specific token '{token}' — "
                    f"{self._NOUN_PLURAL} must read identically across PI, Codex, and "
                    "Claude workers"
                )
