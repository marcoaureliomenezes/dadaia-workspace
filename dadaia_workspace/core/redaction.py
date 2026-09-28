"""Stdlib-pure privacy matching and masking primitives; zero I/O, zero internal import.

- :func:`privacy_matches` — THE matcher of a private term in text: the push gate
  (``denylist_scan``), the public doctor (``privacy_check``) and the ledger seam run it.
  ``public stage`` copies this file beside every ledger script as ``_privacy.py``, so the
  seam refuses exactly what the push refuses (sa-ledger-write-seam-redacts-less-than-push-refuses).

- :func:`mask` — the one ``first…last`` rendering of a private match; used by
  ``features/chokepoints/denylist_scan`` (the hits ``push_gate.push_gate_decision``
  renders) and ``infrastructure/privacy_check`` (``public doctor``).
- :class:`Redactor` — word-boundary, longest-first, ordinal-placeholder masking; used by
  ``cli/redact`` (``--redact``) and ``features/certification``.
- :func:`redact_text` — control-character stripping and home-path/IP scrubbing for
  ``--redact`` display (``cli/redact``); never a ledger write.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator, Mapping
from typing import Any

__all__ = [
    "UNSAFE_FORMAT_CHARS_RE",
    "Redactor",
    "compile_candidates",
    "first_private",
    "mask",
    "privacy_matches",
    "redact_text",
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


def first_private(
    record: Mapping[str, Any], terms: Iterable[tuple[str, str]], patterns: Iterable[Any]
) -> tuple[str, str] | None:
    """``(field, masked match)`` of the first field whose serialized value the push would
    refuse, or ``None`` — a ledger line is scanned as the bytes it is written as."""
    terms, patterns = list(terms), list(patterns)
    for key, value in record.items():
        for found, _source, _reason in privacy_matches(
            json.dumps(value, ensure_ascii=False), terms, patterns
        ):
            return key, mask(found)
    return None


# ============================================================================
# redact_text — display scrubbing (SPEC v0.4.5 FR7).
# ============================================================================

# Redaction patterns (privacy rules): operator-local home paths + IPs never land in a
# committed record. The username segment of a home path is scrubbed; the IPv4 form is
# masked wholesale. (A version token like v0.1.46 has only three numeric groups and is
# never matched.)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_POSIX_HOME_RE = re.compile(r"(/home/|/Users/)[^/\s:]+")
_WIN_HOME_RE = re.compile(r"([A-Za-z]:\\Users\\)[^\\\s:]+")

#: The C0/C1/DEL control range MINUS TAB (0x09), LF (0x0A) and CR (0x0D), plus the
#: Unicode LINE/PARAGRAPH SEPARATORS (U+2028/U+2029). Stripped — never escaped — FIRST
#: inside :func:`redact_text`, before any masking pass (v0.4.5 FR7/A7.3/A7.6, narrowed
#: by bug ``bug-event-sanitation-strips-tab-lf-cr-from-free-text``; bundles bug
#: ``bug-event-field-with-unicode-line-separator-silently-drops-the-event``).
#: A caller serializing with ``json.dumps(..., ensure_ascii=False)`` already escapes
#: the WHOLE C0/C1/DEL range as a JSON string escape — a literal TAB/LF/CR inside a
#: field value can never fragment a JSONL line, as long as the reader splits on a
#: literal ``"\\n"`` character, never on ``str.splitlines()``'s wider terminator set
#: (v0.4.5 FR7 read-side fix). TAB/LF/CR carry neither hazard this class exists to
#: close and must round-trip intact — deleting them only destroyed the word boundaries
#: of every multi-line free-text field, silently, on the live write path (bug
#: ``bug-event-sanitation-strips-tab-lf-cr-from-free-text``). What DOES still need
#: stripping: (a) U+0085/U+2028/U+2029 — the only bytes ``json.dumps`` leaves raw AND a
#: naive ``str.splitlines()``-style reader would treat as a terminator, the actual
#: fragmentation hazard (A7.1); (b) ESC and the rest of C0/C1/DEL — a raw ESC forges an
#: ANSI escape sequence or a fake second output line in any consumer that ever decodes
#: a folded record back to a terminal (CWE-117, A7.2). Deleted rather than escaped,
#: unlike that precedent: a denylisted term an attacker interrupts with one of these
#: bytes must re-join into a contiguous substring for the masking pass immediately
#: below to still catch it (A7.6) — an escape sequence (``"\\x1b"``) would leave the
#: two halves apart.
UNSAFE_FORMAT_CHARS_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\u2028\u2029]")


def redact_text(text: str) -> str:
    """Return ``text`` with unsafe control/format characters stripped (FIRST, see
    :data:`UNSAFE_FORMAT_CHARS_RE`), then operator-local home-path usernames and IPv4
    addresses masked."""
    out = UNSAFE_FORMAT_CHARS_RE.sub("", text)
    out = _IPV4_RE.sub("[REDACTED-IP]", out)
    out = _POSIX_HOME_RE.sub(r"\1[REDACTED]", out)
    return _WIN_HOME_RE.sub(r"\1[REDACTED]", out)


# ============================================================================
# Redactor — word-boundary ordinal-placeholder masking (SPEC v0.11.0 FR6/ADR D1-a).
# ============================================================================

#: Characters that make an adjacent match "not a whole word". Hyphens are
#: deliberately treated as WORD characters (not boundaries): a candidate (a context
#: name, a repo slug, a path segment) commonly contains them, and a short candidate
#: that is merely a substring/prefix of a longer, unrelated hyphenated string must
#: never be partially matched.
_WORD_CHARS = "A-Za-z0-9_-"


def compile_candidates(terms: Iterable[str]) -> re.Pattern[str] | None:
    """Word-boundary alternation over *terms*, longest-first so a short candidate that
    happens to be a prefix of a longer one never shadows the longer match.

    Returns ``None`` when *terms* carries no non-empty candidate — nothing to mask.
    """
    ordered = sorted({t for t in terms if t}, key=len, reverse=True)
    if not ordered:
        return None
    body = "|".join(
        rf"(?<![{_WORD_CHARS}]){re.escape(term)}(?![{_WORD_CHARS}])" for term in ordered
    )
    return re.compile(body)


class Redactor:
    """Stateful per-invocation masker: stable first-appearance ordinal placeholders.

    Construct ONE instance per rendering pass with the full candidate set. Reuse the
    SAME instance across every piece of output that pass renders, in rendering order,
    so the ordinal map accumulates in the TRUE first-appearance order of the pass.
    """

    def __init__(self, candidates: Iterable[str], *, placeholder_fmt: str) -> None:
        self._pattern = compile_candidates(candidates)
        self._placeholder_fmt = placeholder_fmt
        self._map: dict[str, str] = {}

    @property
    def active(self) -> bool:
        """True when at least one candidate exists to mask."""
        return self._pattern is not None

    def mask(self, value: str) -> str:
        """Mask every candidate substring found inside *value*."""
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
