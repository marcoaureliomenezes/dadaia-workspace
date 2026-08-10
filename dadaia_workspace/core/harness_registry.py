"""Typed harness identity registry — ``core/harness_registry.py``.

The **code embodiment** of the agent-runtime roster that ``specs/memory/tech-stack.md``
("Agent runtimes") documents as the single source of truth (SPEC-DOC-037). This module
does not compete with that doc — it *types* the entry-harness roster so no bare string
literal is scattered across the codebase.

One roster lives here:

* :data:`L1_ENTRY_HARNESSES` — the Layer-1 *entry* harnesses an operator can drive the
  workspace from: ``claude``, ``codex``, ``kimi-code``. This is the identity set
  the panel runtime-validation and the ``dadaia init --harness`` / projection vocabulary
  key on.

Layering: a pure ``core`` leaf — **stdlib only, no upward import** (import-linter clean).
Consumed downward by ``infrastructure`` / ``features`` / ``cli``.
"""

from __future__ import annotations

#: The Layer-1 entry-harness roster — the harnesses an operator enters the workspace
#: from. Canonical order (also the ``init --harness all`` / projection order).
#: ``kimi-code`` (v0.2.8) is Layer-1 only.
L1_ENTRY_HARNESSES: tuple[str, ...] = ("claude", "codex", "kimi-code")

#: The projectable install targets in canonical order: the shared ``agents`` skills root
#: plus one projection per Layer-1 entry harness. Consumed by ``public_assets.install``'s
#: per-target loop (``target == "all"`` expands to this tuple).
PROJECTION_TARGETS: tuple[str, ...] = ("agents", *L1_ENTRY_HARNESSES)

#: The full ``--target`` vocabulary the public-asset installer accepts: every projectable
#: target plus the ``all`` meta-target. Single source for ``public_assets_common``'s
#: ``_VALID_TARGETS`` (re-exported there for back-compat).
INSTALL_TARGETS: frozenset[str] = frozenset({"all", *PROJECTION_TARGETS})

_L1_SET: frozenset[str] = frozenset(L1_ENTRY_HARNESSES)


def is_l1(harness: str) -> bool:
    """Return ``True`` iff *harness* is a Layer-1 entry harness (``claude``/``codex``/``pi``/``kimi-code``)."""
    return harness in _L1_SET


def parse_harness_set(value: str) -> tuple[str, ...]:
    """Parse a ``--harness`` selector into a validated, canonically-ordered L1 tuple.

    Accepts either the meta-value ``"all"`` (⇒ the full :data:`L1_ENTRY_HARNESSES`) or a
    comma-separated subset of Layer-1 harness names (case-insensitive, whitespace-tolerant,
    de-duplicated). The result is always ordered by :data:`L1_ENTRY_HARNESSES`, never by
    input order.

    Args:
        value: the raw selector, e.g. ``"claude"``, ``"codex,kimi-code"``, ``"all"``.

    Returns:
        The validated harness tuple in canonical L1 order.

    Raises:
        ValueError: if *value* is empty or names any harness outside
            :data:`L1_ENTRY_HARNESSES`. The message lists the valid harnesses.
    """
    raw = value.strip().lower()
    if raw == "all":
        return L1_ENTRY_HARNESSES
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    valid = ", ".join(L1_ENTRY_HARNESSES)
    if not parts:
        raise ValueError(
            f"empty harness set {value!r}; expected 'all' or a comma-separated subset of {valid}"
        )
    unknown = [p for p in parts if p not in _L1_SET]
    if unknown:
        plural = "es" if len(unknown) > 1 else ""
        named = ", ".join(repr(u) for u in unknown)
        raise ValueError(f"unknown harness{plural} {named}; valid harnesses: {valid} (or 'all')")
    return tuple(h for h in L1_ENTRY_HARNESSES if h in set(parts))
