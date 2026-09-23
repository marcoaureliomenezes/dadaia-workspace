"""The intent binder the backlog doctor reads, and its YAML error formatter.

Read-only: it never writes a backlog file or the alias map. The author-facing listing
and single-subject preview retired with ``dadaia backlog subjects`` (0.4.7 c7,
T-047-65) — the skill script's ``subjects`` verb is the author's surface now.

It hosts :func:`bound_anchor_changes`, the intent binder the doctor (T-120-05/08)
consumes to bind ``active[]`` entry intents from the single-source
``specs/backlog/BACKLOG.json`` (:mod:`dadaia_workspace.features.backlog.document`;
operator ruling 2026-08-28) against the registry. Kept here rather than in
``document.py`` so neither module imports the other's concrete type —
:func:`bound_anchor_changes` is typed against the structural :class:`_IntentBearing`
Protocol instead.
"""

from __future__ import annotations

from typing import Protocol

import yaml

from dadaia_workspace.core.models.backlog import Intent
from dadaia_workspace.features.backlog.subject_registry import (
    BindStatus,
    Registry,
)

__all__ = [
    "bound_anchor_changes",
    "format_yaml_error",
]


def format_yaml_error(exc: yaml.YAMLError, *, line_offset: int = 0) -> str:
    """Render a YAMLError as ``<msg> (line <L>, column <C>)`` when a mark is available.

    Prefers the short ``problem`` message over ``str(exc)`` (which embeds the mark in a
    multi-line snippet). Line/column are 1-based; ``line_offset`` shifts the mark's
    block-relative line to the FILE line the human will open. Public API (SPEC v0.4.2
    FR3, GRILL P7 — no leaf imports a sibling leaf's underscore-private symbol), reused
    verbatim by :mod:`dadaia_workspace.features.backlog.document` to format a malformed
    ``**Intents:**`` fenced-YAML block diagnostic (SPEC v0.12.0 FR1) — kept here as the
    one YAMLError-formatting home rather than duplicated.
    """
    problem = getattr(exc, "problem", None)
    message = str(problem) if problem else str(exc)
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        return f"{message} (line {mark.line + 1 + line_offset}, column {mark.column + 1})"
    return message


class _IntentBearing(Protocol):
    """Structural shape :func:`bound_anchor_changes` needs — satisfied by the
    single-source ``document.ActiveItem`` (SPEC v0.12.0 FR1/FR2). A Protocol rather
    than importing :class:`~dadaia_workspace.features.backlog.document.ActiveItem`
    directly, so neither module imports the other's concrete type (``document.py``
    already imports :func:`format_yaml_error` from this module).

    Declared as a read-only ``@property`` (not a plain annotated attribute): the
    concrete type is a FROZEN dataclass, and mypy treats a frozen dataclass field as
    read-only — a plain Protocol attribute annotation demands read+write access.
    """

    @property
    def intents(self) -> tuple[Intent, ...]: ...


def bound_anchor_changes(
    item: _IntentBearing, registry: Registry
) -> tuple[dict[str, str], list[str]]:
    """Bind each of ``item``'s intents to a canonical anchor.

    Returns ``(anchor_changes, unresolved)``: a map of anchor-id → change for every intent
    that resolved, plus the list of HALT messages for intents that did not (BL-SCHEMA fodder).
    When two intents bind to the same anchor with differing changes, the first wins for the
    map (the intra-item duplicate is an authoring error the doctor surfaces separately).
    A ``surface: new`` subject binds by declared identity (``new:<kind>:<ref>``) instead of
    registry resolution, so items introducing disjoint new surfaces classify UNRELATED.
    """
    anchor_changes: dict[str, str] = {}
    unresolved: list[str] = []
    for intent in item.intents:
        if intent.subject.surface == "new":
            # Bugs backlog-independent-cli-items-false-conflict-044 +
            # backlog-cli-intent-hallucinated-anchor-045: a declared NEW surface binds
            # by its own identity — never forced onto an existing anchor (false
            # conflicts) and never unresolved (dead-end blocks). Guard the dual error:
            # a "new" surface the registry already resolves is an authoring mistake.
            result = registry.bind(intent.subject.ref, intent.subject.kind)
            if result.status is BindStatus.RESOLVED and result.anchor is not None:
                unresolved.append(
                    f"subject ref {intent.subject.ref!r} (kind="
                    f"{intent.subject.kind.value}) is declared 'surface: new' but "
                    f"already resolves to existing anchor {result.anchor.id!r}; bind "
                    "it as existing (drop 'surface: new') or choose a new name."
                )
                continue
            declared = f"new:{intent.subject.kind.value}:{intent.subject.ref}"
            anchor_changes.setdefault(declared, intent.change)
            continue
        result = registry.bind(intent.subject.ref, intent.subject.kind)
        if result.status is BindStatus.RESOLVED and result.anchor is not None:
            anchor_changes.setdefault(result.anchor.id, intent.change)
        else:
            unresolved.append(result.message or f"unresolved: {intent.subject.ref}")
    return anchor_changes, unresolved
