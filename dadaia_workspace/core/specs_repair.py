"""Placeholder-atom repair for specs trees (``core/specs_repair.py``).

The retired placeholder feature atom (bug
scaffold-repair-cannot-remediate-invalid-placeholder-atom): old scaffolds shipped a raw
``memory/product/feature.md`` template whose ``*_PLACEHOLDER`` markers no verb could
remediate. This module owns the exact-token detection and removal so BOTH repair
surfaces — ``specs doctor --fix`` (features.specs) and ``specs upgrade``
(features.migrate) — share one home without a forbidden sibling edge (import-linter:
features never import features).

Layering: a pure ``core`` leaf — stdlib only, no upward import.
"""

from __future__ import annotations

import re
from pathlib import Path

#: Exact template tokens of the retired placeholder feature atom. An atom carrying ANY
#: of them was never filled by a human — it is a template artifact, never real content
#: (the tokens are shouty constants; a filled atom cannot contain them verbatim).
_PLACEHOLDER_TOKENS: tuple[str, ...] = (
    "SLUG_PLACEHOLDER",
    "TITLE_PLACEHOLDER",
    "RELEASE_PLACEHOLDER",
)

#: FR8 (idea ``tests-agents-md-placeholder-doctor-warning``): the installed
#: ``tests/AGENTS.md`` copy carries literal ``<TOKEN>`` markers (e.g. ``<UNIT_TIMEOUT_S>``)
#: for the operator to fill with this project's own numbers. Every genuine fill-me value
#: in ``dadaia_workspace/public/templates/tests-AGENTS.md`` is a TIGHT single-backtick
#: code span around nothing but the token itself — `` `<UNIT_TIMEOUT_S>` `` — which is
#: also what distinguishes it from the template's own "Intent: `<KIND>` — <AC id | ...>"
#: line: a documentation example illustrating a DIFFERENT file's docstring syntax, whose
#: backtick span wraps more than the bracketed token. Requiring the tight wrap means a
#: filled installed copy that (correctly) keeps that illustrative line verbatim is never
#: mistaken for an unfilled placeholder (A8.3); the shouty-plus-underscore body still
#: matches nothing but real fill-me shapes (never ``<project-name>``/``<ANGLE-BRACKET>``).
_ANGLE_PLACEHOLDER_RE = re.compile(r"`<[A-Z_]+>`")


def is_placeholder_atom(path: Path) -> bool:
    """True when *path* is an unfilled placeholder memory atom (template artifact).

    Detection is exact-token based and never fires on filled content: a real atom
    cannot carry ``SLUG_PLACEHOLDER``/``TITLE_PLACEHOLDER``/``RELEASE_PLACEHOLDER``
    verbatim. Read errors degrade to False (never delete on uncertainty).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(token in text for token in _PLACEHOLDER_TOKENS)


def has_unfilled_angle_placeholders(path: Path) -> bool:
    """True when *path* still carries an unfilled `` `<TOKEN>` `` placeholder (FR8).

    Detects the installed-consumer-file placeholder shape: a single-backtick code span
    wrapping nothing but an uppercase-letters/underscores token (e.g.
    `` `<UNIT_TIMEOUT_S>` ``). The tight wrap excludes a token merely illustrated inside a
    longer code span (e.g. the template's own `` `Intent: <KIND> — ...` `` docstring-
    syntax example) — that shape documents a DIFFERENT file's convention, not an unfilled
    value of this one. Read errors degrade to False — never flag on uncertainty.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(_ANGLE_PLACEHOLDER_RE.search(text))


def remove_placeholder_atoms(specs_dir: Path, *, dry_run: bool = False) -> list[Path]:
    """Remove every unfilled placeholder atom under ``specs_dir/memory/``; return removed paths.

    Shared repair for the retired placeholder feature atom, consumed by
    ``specs upgrade`` and by ``specs doctor --fix``'s issue-level fix. Exact-token
    detection (:func:`is_placeholder_atom`) — filled atoms are never touched.
    ``dry_run=True`` only reports what would be removed.
    """
    mem_dir = specs_dir / "memory"
    removed: list[Path] = []
    if not mem_dir.is_dir():
        return removed
    for path in sorted(mem_dir.rglob("*.md")):
        if is_placeholder_atom(path):
            removed.append(path)
            if not dry_run:
                path.unlink()
    return removed
