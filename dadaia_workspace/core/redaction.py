"""Stdlib-pure masking primitive (SPEC v0.11.0 FR6/ADR D1-a).

Extracted mechanically from ``cli/redact.py#ContextRedactor`` (v0.9.0 FR8a) so the SAME
masking primitive can be consumed both by the CLI's ``--redact`` rendering
(``cli/redact.py``) AND by the push-range denylist gate's own render boundary
(``features/chokepoints/service.py``'s ``_compose_denylist_refusal`` /
``_annotate_skip``), which may import ``core`` but never ``cli``
(``architecture.md`` ring purity) — the extension entry #23's resolution A requires
would otherwise be unimplementable in either direction (grill P4).

Word-boundary alternation, longest-first ordering, and stable first-appearance ordinal
placeholders are the whole of the primitive; everything caller-specific (which
candidates to mask, what to exclude, JSON-tree recursion) stays in the consumer.

Zero I/O — ``core/`` stays stdlib-pure; the file-I/O authorized set
(``specs_backup``/``specs_repair``/``specs_version``/``specs_resolver``/
``workspace_resolver``) is unaffected.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

__all__ = ["Redactor", "compile_candidates"]

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
