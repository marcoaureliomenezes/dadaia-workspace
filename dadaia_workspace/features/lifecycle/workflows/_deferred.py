"""Deferred workflow entry points (WS-6) — scaffolded, not yet runnable.

The backlog / audit / research / bug-report workflow bodies are **deferred to a
follow-up release** (SPEC §3.12). They are scaffolded here so the workflow surface is
importable and discoverable, but every entry point **fails loud** — it raises
``NotImplementedError`` when invoked rather than silently no-op'ing. A silent no-op
would let a caller believe a deferred workflow ran; raising keeps the deferral honest
(WS-6 acceptance: "a test asserts the scaffolded-but-deferred workflows fail loudly").

Each entry point is a thin callable. When a deferred workflow is implemented in a later
release it replaces its entry point here with a real workflow body (mirroring
:mod:`dadaia_workspace.features.lifecycle.workflows.release_definition`).
"""

from __future__ import annotations

from typing import NoReturn

#: The deferred workflow names, in catalog order. Each maps to an entry point below.
#: ``backlog_definition`` LEFT this set in v0.1.26 R2 — it now ships a real workflow body
#: (:mod:`dadaia_workspace.features.lifecycle.workflows.backlog_definition`).
DEFERRED_WORKFLOWS: tuple[str, ...] = (
    "audit",
    "research",
    "bug_report",
)


def _deferred(name: str) -> NoReturn:
    raise NotImplementedError(f"{name} workflow deferred to a follow-up release")


def audit(*_args: object, **_kwargs: object) -> NoReturn:
    """Audit workflow — deferred to a follow-up release (fails loud)."""
    _deferred("audit")


def research(*_args: object, **_kwargs: object) -> NoReturn:
    """Research workflow — deferred to a follow-up release (fails loud)."""
    _deferred("research")


def bug_report(*_args: object, **_kwargs: object) -> NoReturn:
    """Bug-report workflow — deferred to a follow-up release (fails loud)."""
    _deferred("bug_report")


__all__ = [
    "DEFERRED_WORKFLOWS",
    "audit",
    "bug_report",
    "research",
]
