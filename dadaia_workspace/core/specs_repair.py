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

from pathlib import Path

#: Exact template tokens of the retired placeholder feature atom. An atom carrying ANY
#: of them was never filled by a human — it is a template artifact, never real content
#: (the tokens are shouty constants; a filled atom cannot contain them verbatim).
_PLACEHOLDER_TOKENS: tuple[str, ...] = (
    "SLUG_PLACEHOLDER",
    "TITLE_PLACEHOLDER",
    "RELEASE_PLACEHOLDER",
)


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
