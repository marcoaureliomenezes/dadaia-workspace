"""Pure push-range denylist matcher (SPEC v0.9.0 FR3/FR5/FR6; SPEC v0.11.0 FR1).

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

**v0.11.0 FR1 amnesty (supersedes the v0.9.0-era "a matched term always produces a
hit" absolute).** A candidate is now suppressed IFF the exact matched VALUE occurs
case-insensitively in the SAME path's published prior text, carried on
``ScannedObject.prior_text`` — never derived from a list, dict, set or constant of
sanctioned terms. Grill ADR #3b's invariant survives in its narrower, still-load-bearing
form: **no amnesty/allowlist LIST exists anywhere in this module** (A4.1's source-scan
contract test pins exactly that, unmodified) — the amnesty derives entirely from
published git state the adapter resolves, never from a static exception list.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from dadaia_workspace.core.protocols.git_object_reader import ScannedObject

__all__ = ["BaselinePatternLike", "Hit", "OversizedNote", "ScanOutcome", "scan_objects"]

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
class OversizedNote:
    """One oversized blob's honest partial-coverage report (SPEC v0.11.0 FR4).

    Distinct from the undecodable-binary skip count: an oversized blob whose scanned
    prefix decoded fine (``ScannedObject.decodable`` True) is genuinely partially
    scanned, not blindly skipped — this note is how that partial coverage is reported
    to every consumer, never conflated with the binary-blob wording.
    """

    path: str
    size_bytes: int
    scanned_bytes: int


@dataclass(frozen=True)
class ScanOutcome:
    """The matcher's verdict over one batch of :class:`ScannedObject`."""

    hits: tuple[Hit, ...]
    skipped_binary_count: int
    oversized_notes: tuple[OversizedNote, ...] = ()


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
    O(n log n) sort for a result already known at the first hit).

    SPEC v0.11.0 FR1 amnesty: a candidate is suppressed IFF the SAME layer's matcher,
    RE-RUN against ``obj.prior_text`` (the SAME path's published prior content; ``None``
    -> no base, nothing is ever suppressed, ADR D7), produces a matched occurrence whose
    value EQUALS (case-normalized) the current matched value. Keying on the value (not
    the source) is what stops the amnesty from becoming a smuggling path: a prior email
    address must NOT amnesty a brand-new one of the same baseline pattern id (grill
    R1/A1.3). Re-running the layer's own anchored matcher — rather than testing raw
    substring containment — is what stops a DIFFERENT, longer prior-published home-path
    value from amnestying an unrelated new value that merely happens to be one of its
    substrings, or a prior superstring like ``acmecorp`` from amnestying a new
    standalone ``acme`` that was never actually published at a word boundary
    (code-reviewer MEDIUM finding, v0.11.0 pre-PR review). The matched value is used
    for this predicate and then discarded — only ``masked_term`` leaves this module
    (A5.2 unaffected). Suppression is per-CANDIDATE, so a line whose every candidate is
    suppressed simply continues to the next line — the short-circuit property above is
    unchanged."""
    prior_text = obj.prior_text
    prior_lower = prior_text.lower() if prior_text is not None else None

    def _term_suppressed(term: str) -> bool:
        """Operator-term layer: FR3(1) defines "occurs" as a literal, case-insensitive
        substring — the SAME notion detection itself uses (``term.lower() in
        lowered``), so re-using it against the prior text is not an anchoring mismatch;
        it is the layer's own defined semantics, applied identically on both sides."""
        return prior_lower is not None and term.lower() in prior_lower

    def _pattern_suppressed(value: str, pattern: BaselinePatternLike) -> bool:
        """Baseline-pattern layer: suppressed only when the SAME anchored regex,
        re-run against the prior text, matches an occurrence whose value equals
        *value* case-insensitively — never a raw substring test."""
        if prior_text is None:
            return False
        value_lower = value.lower()
        return any(
            match.group(0).lower() == value_lower for match in pattern.regex.finditer(prior_text)
        )

    def _slug_suppressed(compiled: re.Pattern[str]) -> bool:
        """Foreign-slug layer: *compiled* is ``\\bslug\\b`` (case-insensitive) — a
        match against the prior text is already an anchored, exact-value occurrence of
        this SAME slug (the pattern IS the value), so a boolean search doubles as the
        value-equality check."""
        return prior_text is not None and compiled.search(prior_text) is not None

    for lineno, line_text in enumerate(obj.text.splitlines(), start=1):
        line_candidates: list[Hit] = []
        lowered = line_text.lower()
        for term, _reason in terms:
            if term and term.lower() in lowered and not _term_suppressed(term):
                line_candidates.append(
                    Hit(obj.path, lineno, obj.sha, _mask(term), _SOURCE_OPERATOR)
                )
        for pattern in patterns:
            for match in pattern.regex.finditer(line_text):
                value = match.group(0)
                if pattern.exclude is not None and pattern.exclude.search(value):
                    continue
                if _pattern_suppressed(value, pattern):
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
            if compiled.search(line_text) and not _slug_suppressed(compiled):
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

    Undecodable (binary) objects are skipped and counted, never matched (FR6 row 3).
    This class now ALSO covers an oversized blob whose scanned prefix failed to decode
    (SPEC v0.11.0 A4.6) — there is nothing honest to report about a scan that never
    ran, so it falls back to the SAME binary skip class, never a separate note. An
    oversized blob whose scanned prefix DID decode is genuinely, partially scanned like
    any other decodable object (v0.11.0 A4.1 — a match inside the scanned prefix still
    produces a hit) AND additionally contributes an :class:`OversizedNote` reporting
    the partial coverage, independent of whether a hit was found (A4.4). At most one
    :class:`Hit` is returned per object — its first match by ascending line number —
    matching FR5's one-line-per-offending-object refusal shape.
    """
    term_list = list(terms)
    pattern_list = list(patterns)
    slug_patterns = _compile_slug_patterns(slugs)
    hits: list[Hit] = []
    oversized_notes: list[OversizedNote] = []
    skipped = 0
    for obj in objects:
        if not obj.decodable:
            skipped += 1
            continue
        if obj.oversized:
            oversized_notes.append(
                OversizedNote(
                    path=obj.path, size_bytes=obj.size_bytes, scanned_bytes=obj.scanned_bytes
                )
            )
        hit = _first_match(obj, term_list, pattern_list, slug_patterns)
        if hit is not None:
            hits.append(hit)
    return ScanOutcome(
        hits=tuple(hits),
        skipped_binary_count=skipped,
        oversized_notes=tuple(oversized_notes),
    )
