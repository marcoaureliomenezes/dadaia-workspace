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

v0.11.0 FR6/ADR D1-a: the masking primitive itself (word-boundary alternation,
longest-first ordering, stable first-appearance ordinal placeholders) now lives in
``core/redaction.py`` — a stdlib-pure module the push-range denylist gate's own render
boundary (``features/chokepoints/service.py``) can ALSO import, since
``features/chokepoints/**`` may import ``core`` but never ``cli``. This module is a
THIN CONSUMER of that primitive: its public behaviour is byte-identical to before the
extraction (the regression proof is ``tests/unit/cli/test_redact_output.py`` passing
with no change to its assertions).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from dadaia_workspace.core.redaction import Redactor

#: SPEC FR8 placeholder shape.
_PLACEHOLDER_FMT = "[REDACTED-CONTEXT-{n}]"


class ContextRedactor:
    """Stateful per-invocation redactor.

    Construct ONE instance per command invocation with the full candidate set (every
    known Spec Context name and repo slug), minus whatever must stay visible (the
    caller's own resolved context name and repo slug — SPEC FR8: "other than the
    caller's resolved context"). Reuse the same instance across every piece of output
    the command renders, in rendering order, so the underlying :class:`Redactor`
    accumulates ordinals in the true first-appearance order of the invocation (A8.3).
    """

    def __init__(self, candidates: Iterable[str], *, exclude: Iterable[str | None] = ()) -> None:
        excluded = {name for name in exclude if name}
        terms = [c for c in candidates if c and c not in excluded]
        self._redactor = Redactor(terms, placeholder_fmt=_PLACEHOLDER_FMT)

    @property
    def active(self) -> bool:
        """True when at least one foreign candidate exists to redact."""
        return self._redactor.active

    def text(self, value: str) -> str:
        """Redact every foreign candidate substring found inside ``value``."""
        return self._redactor.mask(value)

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
