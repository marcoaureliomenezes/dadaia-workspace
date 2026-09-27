"""The ``--redact`` render boundary for ``doctor`` and ``context list|show``.

Services keep returning true names; :func:`build_context_redactor` is the one builder,
:class:`ContextRedactor` masks each rendered string or JSON leaf as
``[REDACTED-CONTEXT-<n>]``, ordinal by first appearance in one invocation (SPEC A8.3),
on top of ``core/redaction.Redactor``.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from dadaia_workspace.cli._specs_resolution import resolve_context_for_cli
from dadaia_workspace.core.models.spec_context import SpecContextProject
from dadaia_workspace.core.redaction import Redactor, redact_text

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
        """Redact every foreign candidate substring and home-path user inside ``value``."""
        return self._redactor.mask(redact_text(value))

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


def build_context_redactor(contexts: Iterable[SpecContextProject]) -> ContextRedactor:
    """The one redactor builder for ``doctor --redact``, ``context list|show --redact``:
    candidates = every context name and every repo slug (main + associated); the
    caller's own resolved context and its whole repo set stay visible."""
    contexts = list(contexts)
    try:
        caller_name: str | None = resolve_context_for_cli(None)
    except ValueError:
        caller_name = None
    caller = next((ctx for ctx in contexts if ctx.name == caller_name), None)
    own = {r.slug for r in caller.all_repos()} if caller is not None else set()
    candidates = [
        term for ctx in contexts for term in (ctx.name, *(r.slug for r in ctx.all_repos()))
    ]
    return ContextRedactor(candidates, exclude=(caller_name, *own))
