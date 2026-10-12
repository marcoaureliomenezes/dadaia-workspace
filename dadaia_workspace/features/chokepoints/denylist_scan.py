"""Pure push-range denylist matcher.

Zero I/O, exactly like the rest of ``features/chokepoints/**``: this module NEVER
imports ``infrastructure`` and NEVER spawns a subprocess. Term sources — the operator
denylist and the packaged baseline patterns, which carry no repo or context name — are
loaded by the CLI (``cli/commands/ci.py``) via ``infrastructure.privacy_check``'s public
accessors and passed in here as plain data; :class:`BaselinePatternLike` is a
structural Protocol so this module can accept those instances without importing the
concrete type that produces them (features-no-infrastructure import-linter contract).

Masking (``first…last``) happens INSIDE this module so an unmasked term never leaves it
(CWE-532): :attr:`Hit.masked_term` is the only term-shaped value this module ever
returns; the source blob's raw text is never echoed anywhere.

A candidate is suppressed IFF the exact matched value occurs case-insensitively in the
same path's published prior text, carried on ``ScannedObject.prior_text``. It is never
derived from a list, dict, set or constant of sanctioned terms: the amnesty derives
entirely from published git state the adapter resolves. No amnesty or allowlist list
exists anywhere in this module.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Protocol

from dadaia_workspace.core.models.git_scan import ScannedObject
from dadaia_workspace.core.redaction import (
    UNSAFE_FORMAT_CHARS_RE,
    fresh_matches,
    mask,
    published_matches,
)

__all__ = [
    "BaselinePatternLike",
    "Hit",
    "OversizedNote",
    "PathMasker",
    "ScanOutcome",
    "scan_objects",
]


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
    """One offending blob's first denylist match."""

    path: str
    line: int
    sha: str
    masked_term: str
    source_layer: str


@dataclass(frozen=True)
class OversizedNote:
    """One oversized blob's partial-coverage report.

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


def _first_match(
    obj: ScannedObject,
    terms: list[tuple[str, str]],
    patterns: list[BaselinePatternLike],
) -> Hit | None:
    """The earliest-line match of :func:`~dadaia_workspace.core.redaction.privacy_matches`
    (the one matcher: operator terms, then baseline patterns), or ``None``.

    A candidate is suppressed IFF the SAME matcher, re-run over ``obj.prior_text`` (the
    same path's published content; ``None`` suppresses nothing), yields the same value
    (case-normalized) from the same source; keyed on the value, so a prior email never
    amnesties a brand-new one. Only ``masked_term`` leaves this module."""
    published = published_matches(obj.prior_text, terms, patterns)
    # A control character never splits a term out of reach: stripped first.
    for lineno, line_text in enumerate(UNSAFE_FORMAT_CHARS_RE.sub("", obj.text).splitlines(), 1):
        for value, source, _reason in fresh_matches(line_text, published, terms, patterns):
            return Hit(obj.path, lineno, obj.sha, mask(value), source)
    return None


def scan_objects(
    objects: Iterable[ScannedObject],
    terms: Iterable[tuple[str, str]],
    patterns: Iterable[BaselinePatternLike],
) -> ScanOutcome:
    """Match *objects* against the term sources.

    * ``terms`` — operator denylist entries (``(term, reason)``), case-insensitive
      substring match.
    * ``patterns`` — compiled baseline structural patterns, ``exclude_regex`` honored.

    Undecodable (binary) objects are skipped and counted, never matched. An oversized
    blob whose scanned prefix failed to decode falls in the same skip class. An
    oversized blob whose prefix decoded is scanned like any other decodable object, and
    also yields an :class:`OversizedNote` reporting the partial coverage, whether or not
    a hit was found. At most one :class:`Hit` is returned per object: its first match by
    ascending line number.
    """
    term_list = list(terms)
    pattern_list = list(patterns)
    hits: list[Hit] = []
    oversized_notes: list[OversizedNote] = []
    skipped = 0
    for obj in objects:
        # A structural shape in the path refuses (a key file by its suffix, binary
        # or not), line 0; an operator term there is masked by PathMasker, not refused.
        path_hit = _first_match(replace(obj, text=obj.path, prior_text=None), [], pattern_list)
        if path_hit is not None:
            hits.append(replace(path_hit, line=0))
            continue
        if not obj.decodable:
            skipped += 1
            continue
        if obj.oversized:
            oversized_notes.append(
                OversizedNote(
                    path=obj.path, size_bytes=obj.size_bytes, scanned_bytes=obj.scanned_bytes
                )
            )
        hit = _first_match(obj, term_list, pattern_list)
        if hit is not None:
            hits.append(hit)
    return ScanOutcome(
        hits=tuple(hits),
        skipped_binary_count=skipped,
        oversized_notes=tuple(oversized_notes),
    )


#: A masked blob-path segment in a gate refusal or note; distinct from the
#: CLI's ``[REDACTED-CONTEXT-n]`` (``cli/redact.py``), a different channel.
_PATH_PLACEHOLDER_FMT = "[REDACTED-PATH-{n}]"


class PathMasker:
    """Masks the blob-path segments :func:`_first_match` flags; every gate string naming a
    blob path routes through :meth:`mask_path`.
    One instance per push-gate run: a repeated segment keeps its first-appearance
    ordinal. A path with no offending segment is returned byte-identical."""

    def __init__(
        self,
        denylist_terms: Iterable[tuple[str, str]],
        baseline_patterns: Iterable[BaselinePatternLike],
    ) -> None:
        self._terms = list(denylist_terms)
        self._patterns = list(baseline_patterns)
        self._map: dict[str, str] = {}

    def mask_path(self, path: str) -> str:
        """Return *path* with every offending segment replaced by its placeholder."""
        masked_segments: list[str] = []
        for segment in path.split("/"):
            probe = ScannedObject(path=segment, sha="", text=segment, decodable=True)
            if _first_match(probe, self._terms, self._patterns) is None:
                masked_segments.append(segment)
                continue
            placeholder = self._map.setdefault(
                segment, _PATH_PLACEHOLDER_FMT.format(n=len(self._map) + 1)
            )
            masked_segments.append(placeholder)
        return "/".join(masked_segments)
