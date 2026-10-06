"""Stdlib-pure privacy matching and masking primitives; zero I/O, zero internal import.

``public stage`` copies this file beside every ledger script as ``_privacy.py``, so the ledger
seam asks the push's own question: which matches are fresh against the published text, and
where "published" is (:func:`publication_boundaries`, git run by the caller).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Any

__all__ = [
    "UNSAFE_FORMAT_CHARS_RE",
    "Redactor",
    "PUBLISHED",
    "compile_candidates",
    "fresh_matches",
    "mask",
    "privacy_matches",
    "publication_boundaries",
    "published_matches",
]


def mask(term: str) -> str:
    """The one way a private match is shown: ``first…last``, never the term itself."""
    return f"{term[0]}…{term[-1]}" if term else term


def privacy_matches(
    text: str, terms: Iterable[tuple[str, str]], patterns: Iterable[Any]
) -> Iterator[tuple[str, str, str]]:
    """``(value, source, reason)`` for every private match in *text*: operator terms (a
    case-insensitive substring) first, then each baseline pattern (``id``, ``regex``,
    ``exclude``, ``reason``) whose match its ``exclude`` does not carve out."""
    text = UNSAFE_FORMAT_CHARS_RE.sub("", text)
    lowered = text.lower()
    for term, reason in terms:
        if term and term.lower() in lowered:
            yield term, "operator denylist", reason
    for pattern in patterns:
        for match in pattern.regex.finditer(text):
            value = match.group(0)
            if pattern.exclude is None or not pattern.exclude.search(value):
                yield value, f"baseline pattern '{pattern.id}'", pattern.reason


#: What "already published" means: reachable from a locally-known ``origin`` ref.
PUBLISHED = "--remotes=origin"


def publication_boundaries(
    git: Callable[[list[str]], list[str]], tip: str, exclusions: Sequence[str] = (PUBLISHED,)
) -> tuple[str, ...]:
    """Where *tip*'s history re-joins published history: the commits whose text at a path is
    that path's published text. *git* runs one git subcommand and returns its output lines,
    and RAISES on a failed run — empty output means "nothing outside published history".
    *tip* already published: *tip* itself. No shared history (bootstrap): none."""
    lines = git(["rev-list", "--boundary", tip, "--not", *exclusions, "--"])
    return tuple(line[1:] for line in lines if line.startswith("-")) if lines else (tip,)


def published_matches(
    prior_text: str | None, terms: Iterable[tuple[str, str]], patterns: Iterable[Any]
) -> set[tuple[str, str]] | None:
    """The amnesty set: ``(value.lower(), source)`` of every match in the published
    *prior_text*; ``None`` (no published text) amnesties nothing."""
    if prior_text is None:
        return None
    return {(v.lower(), src) for v, src, _ in privacy_matches(prior_text, terms, patterns)}


def fresh_matches(
    text: str,
    published: set[tuple[str, str]] | None,
    terms: Iterable[tuple[str, str]],
    patterns: Iterable[Any],
) -> Iterator[tuple[str, str, str]]:
    """The matches in *text* the push refuses: every one whose value (case-normalized) and
    source the *published* set (:func:`published_matches`) does not already carry."""
    for value, source, reason in privacy_matches(text, terms, patterns):
        if published is None or (value.lower(), source) not in published:
            yield value, source, reason


#: C0/C1/DEL minus TAB/LF/CR, plus U+2028/U+2029: line-fragmenting or terminal-forging
#: bytes. Deleted, never escaped, so a denylisted term split by one re-joins for the mask.
UNSAFE_FORMAT_CHARS_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\u2028\u2029]")


#: Word characters; hyphens included so a candidate never matches inside a hyphenated name.
_WORD_CHARS = "A-Za-z0-9_-"


def compile_candidates(terms: Iterable[str]) -> re.Pattern[str] | None:
    """Word-boundary alternation over *terms*, longest-first; ``None`` when there is none."""
    ordered = sorted({t for t in terms if t}, key=len, reverse=True)
    if not ordered:
        return None
    body = "|".join(
        rf"(?<![{_WORD_CHARS}]){re.escape(term)}(?![{_WORD_CHARS}])" for term in ordered
    )
    return re.compile(body)


class Redactor:
    """Per-pass masker with stable first-appearance ordinal placeholders: one instance per
    rendering pass, reused in rendering order."""

    def __init__(self, candidates: Iterable[str], *, placeholder_fmt: str) -> None:
        self._pattern = compile_candidates(candidates)
        self._placeholder_fmt = placeholder_fmt
        self._map: dict[str, str] = {}

    @property
    def active(self) -> bool:
        return self._pattern is not None

    def mask(self, value: str) -> str:
        if not value or self._pattern is None:
            return value

        def _sub(match: re.Match[str]) -> str:
            term = match.group(0)
            placeholder = self._map.get(term)
            if placeholder is None:
                placeholder = self._placeholder_fmt.format(n=len(self._map) + 1)
                self._map[term] = placeholder
            return placeholder

        return self._pattern.sub(_sub, value)
