"""Pure push-range denylist matcher (SPEC v0.9.0 FR3/FR5/FR6).

Zero I/O, exactly like the rest of ``features/chokepoints/**``: this module NEVER
imports ``infrastructure`` and NEVER spawns a subprocess. Term sources — the operator
denylist, the packaged baseline patterns, and the foreign repo-slug set — are loaded by
the CLI (``cli/commands/ci.py``) via ``infrastructure.privacy_check``'s public
accessors and passed in here as plain data; :class:`BaselinePatternLike` is a
structural Protocol so this module can accept those instances without importing the
concrete type that produces them (features-no-infrastructure import-linter contract).

Masking (``first…last``) happens INSIDE this module so an unmasked term never leaves it
(FR5, CWE-532) — :attr:`Hit.masked_term` is the only term-shaped value this module ever
returns; the source blob's raw text is never echoed anywhere.

Per grill ADR #3b (SPEC FR4): there is no sanctioned-terms / amnesty list here or
anywhere in this release — a matched term always produces a hit.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from dadaia_workspace.core.protocols.git_object_reader import ScannedObject

__all__ = ["BaselinePatternLike", "Hit", "ScanOutcome", "scan_objects"]

_SOURCE_OPERATOR = "operator denylist"
_SOURCE_SLUG = "foreign repo slug"


class BaselinePatternLike(Protocol):
    """Structural shape a compiled baseline privacy pattern must satisfy.

    ``infrastructure.privacy_check.load_baseline_patterns()`` returns instances that
    already satisfy this shape (``id``, ``regex``, ``reason``, ``exclude``) — no import
    of the concrete type is needed on either side. Declared as read-only properties
    (not plain attributes) so a FROZEN dataclass — like the concrete
    ``_BaselinePattern`` — structurally satisfies it: a Protocol with plain attribute
    annotations implies read-write access, which a frozen dataclass cannot offer.
    """

    @property
    def id(self) -> str: ...

    @property
    def regex(self) -> re.Pattern[str]: ...

    @property
    def reason(self) -> str: ...

    @property
    def exclude(self) -> re.Pattern[str] | None: ...


@dataclass(frozen=True)
class Hit:
    """One offending blob's first denylist match (SPEC FR5 — one line per object)."""

    path: str
    line: int
    sha: str
    masked_term: str
    source_layer: str


@dataclass(frozen=True)
class ScanOutcome:
    """The matcher's verdict over one batch of :class:`ScannedObject`."""

    hits: tuple[Hit, ...]
    skipped_binary_count: int


def _mask(term: str) -> str:
    """``first…last`` masking (FR5) — never returns the term unmasked."""
    if not term:
        return term
    return f"{term[0]}…{term[-1]}"


def _compile_slug_patterns(slugs: Iterable[str]) -> list[tuple[str, re.Pattern[str]]]:
    """Word-boundary regex per slug (A3.3) — a short slug never matches inside a longer
    word. Case-insensitive (``re.IGNORECASE``), matching the operator-term layer's
    case-insensitive substring match — a foreign slug referenced with different casing
    (``MyClient`` vs ``myclient``) is still caught (code-reviewer LOW finding)."""
    return [
        (slug, re.compile(r"\b" + re.escape(slug) + r"\b", re.IGNORECASE)) for slug in slugs if slug
    ]


def _first_match(
    obj: ScannedObject,
    terms: list[tuple[str, str]],
    patterns: list[BaselinePatternLike],
    slug_patterns: list[tuple[str, re.Pattern[str]]],
) -> Hit | None:
    """The earliest-line match across all three term sources, or ``None``.

    Short-circuits at the first line that produces any candidate: lines are already
    iterated in ascending order, so that line's own first candidate (insertion order —
    operator terms, then baseline patterns, then foreign slugs) is the answer. Neither
    the rest of the blob nor a global sort is needed to find it (code-reviewer LOW
    performance finding: the previous version paid the full-blob cost plus an
    O(n log n) sort for a result already known at the first hit)."""
    for lineno, line_text in enumerate(obj.text.splitlines(), start=1):
        line_candidates: list[Hit] = []
        lowered = line_text.lower()
        for term, _reason in terms:
            if term and term.lower() in lowered:
                line_candidates.append(
                    Hit(obj.path, lineno, obj.sha, _mask(term), _SOURCE_OPERATOR)
                )
        for pattern in patterns:
            for match in pattern.regex.finditer(line_text):
                value = match.group(0)
                if pattern.exclude is not None and pattern.exclude.search(value):
                    continue
                line_candidates.append(
                    Hit(
                        obj.path,
                        lineno,
                        obj.sha,
                        _mask(value),
                        f"baseline pattern '{pattern.id}'",
                    )
                )
        for slug, compiled in slug_patterns:
            if compiled.search(line_text):
                line_candidates.append(Hit(obj.path, lineno, obj.sha, _mask(slug), _SOURCE_SLUG))
        if line_candidates:
            return line_candidates[0]
    return None


def scan_objects(
    objects: Iterable[ScannedObject],
    terms: Iterable[tuple[str, str]],
    patterns: Iterable[BaselinePatternLike],
    slugs: Iterable[str],
) -> ScanOutcome:
    """Match *objects* against the three FR3 term sources.

    * ``terms`` — operator denylist entries (``(term, reason)``), case-insensitive
      substring match.
    * ``patterns`` — compiled baseline structural patterns, ``exclude_regex`` honored.
    * ``slugs`` — foreign repo slugs (the pushed repo's own slug is expected to already
      be excluded by the caller), word-boundary matched.

    Undecodable (binary) objects are skipped and counted, never matched (FR6 row 3). At
    most one :class:`Hit` is returned per object — its first match by ascending line
    number — matching FR5's one-line-per-offending-object refusal shape.
    """
    term_list = list(terms)
    pattern_list = list(patterns)
    slug_patterns = _compile_slug_patterns(slugs)
    hits: list[Hit] = []
    skipped = 0
    for obj in objects:
        if not obj.decodable:
            skipped += 1
            continue
        hit = _first_match(obj, term_list, pattern_list, slug_patterns)
        if hit is not None:
            hits.append(hit)
    return ScanOutcome(hits=tuple(hits), skipped_binary_count=skipped)
