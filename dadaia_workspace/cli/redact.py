"""Shared ``--redact`` rendering helper (SPEC v0.9.0 FR8a, T-090-07).

Applied ONLY at the CLI render boundary — ``dadaia doctor``, ``dadaia context list``
and ``dadaia context show`` build a :class:`ContextRedactor` from the true names their
underlying services already returned, then use it to mask text right before printing
or JSON-serializing. Services (``DoctorService``, ``SpecContextService``,
``features.spec_context.presence``) are never modified by this module and always keep
returning true names — redaction is a pure display-time concern, never a business-logic
one.

Placeholder shape: ``[REDACTED-CONTEXT-<n>]``, ordinal assigned by FIRST APPEARANCE
within one invocation (SPEC A8.3). Callers get this "first appearance" property for
free by constructing ONE :class:`ContextRedactor` per invocation and feeding it every
string/JSON value in the exact order they render it — the ordinal map grows lazily as
new foreign terms are encountered, so it always matches the actual order of the
rendered output.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

#: SPEC FR8 placeholder shape.
_PLACEHOLDER_FMT = "[REDACTED-CONTEXT-{n}]"

#: Characters that make an adjacent match "not a whole word" — the same charset a
#: context name / repo slug is restricted to (letters, digits, ``_``, ``-``). Hyphens
#: are deliberately treated as WORD characters (not boundaries): repo slugs commonly
#: contain them (``dadaia-workspace``), and a short candidate that is merely a
#: substring/prefix of a longer, unrelated hyphenated string must never be partially
#: redacted.
_WORD_CHARS = "A-Za-z0-9_-"


def _compile_candidates(terms: Iterable[str]) -> re.Pattern[str] | None:
    """Word-boundary alternation over ``terms``, longest-first so a short candidate
    that happens to be a prefix of a longer one never shadows the longer match."""
    ordered = sorted({t for t in terms if t}, key=len, reverse=True)
    if not ordered:
        return None
    body = "|".join(
        rf"(?<![{_WORD_CHARS}]){re.escape(term)}(?![{_WORD_CHARS}])" for term in ordered
    )
    return re.compile(body)


class ContextRedactor:
    """Stateful per-invocation redactor.

    Construct ONE instance per command invocation with the full candidate set (every
    known Spec Context name and repo slug), minus whatever must stay visible (the
    caller's own resolved context name and repo slug — SPEC FR8: "other than the
    caller's resolved context"). Reuse the same instance across every piece of output
    the command renders, in rendering order, so :attr:`_map` accumulates ordinals in
    the true first-appearance order of the invocation (A8.3).
    """

    def __init__(self, candidates: Iterable[str], *, exclude: Iterable[str | None] = ()) -> None:
        excluded = {name for name in exclude if name}
        terms = [c for c in candidates if c and c not in excluded]
        self._pattern = _compile_candidates(terms)
        self._map: dict[str, str] = {}

    @property
    def active(self) -> bool:
        """True when at least one foreign candidate exists to redact."""
        return self._pattern is not None

    def text(self, value: str) -> str:
        """Redact every foreign candidate substring found inside ``value``."""
        if not value or self._pattern is None:
            return value

        def _sub(match: re.Match[str]) -> str:
            term = match.group(0)
            placeholder = self._map.get(term)
            if placeholder is None:
                placeholder = _PLACEHOLDER_FMT.format(n=len(self._map) + 1)
                self._map[term] = placeholder
            return placeholder

        return self._pattern.sub(_sub, value)

    def json_value(self, value: Any) -> Any:
        """Recursively redact string leaves of a JSON-shaped value.

        Keys and every non-string leaf (bool/int/float/None) pass through unchanged —
        the redacted JSON always carries the SAME key set as the source (A8.4).
        """
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, dict):
            return {key: self.json_value(val) for key, val in value.items()}
        if isinstance(value, list):
            return [self.json_value(item) for item in value]
        return value
