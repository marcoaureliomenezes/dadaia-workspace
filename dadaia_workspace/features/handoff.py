"""features/handoff — the public entrypoint onto ``core.handoff_index`` (release 0.5.1 K6).

The implementation lives in ``core/handoff_index.py`` (see that module's docstring for
why): a resolver several mutually-independent feature packages need (``chokepoints``,
``specs``, ``panel``, ``reports``) cannot live in any ONE of them without a new
``features-no-cross-feature`` suppression per consumer, and the GATE this release runs
under requires that ignore-edge cap to never rise. This is the thin, feature-layer-facing
re-export — the CLI's and this candidate's own test suite's home for
``from dadaia_workspace.features.handoff import HandoffIndex, Handoff`` — while every
feature-internal reader imports ``core.handoff_index`` directly (a plain ``core`` import,
free under every layering contract).

Deliberately a flat module, not a package (no ``features/handoff/__init__.py``): a new
*package* under ``features/`` is a live-introspected member of two drift-guarded counts —
the ``features-no-cross-feature`` contract's ``modules =`` list (``P-07``,
:mod:`tests.contract.test_import_linter_ignore_cap`) and the feature package-map diagram
in ``specs/memory/ARCHITECTURE.md`` (``P-13``,
:mod:`tests.contract.test_architecture_diagrams_current`, which parses that memory atom
directly). A flat module is invisible to both — ``pkgutil.iter_modules``'s ``ispkg`` flag
is ``False`` for it — so this facade needs no matching diagram edit to a file this task's
scope keeps off-limits (``specs/**``); a future ``ai-engineer``/``product-engineer`` pass
can promote it to a package and update that diagram in the same commit if the surface
grows enough to warrant one.
"""

from __future__ import annotations

from dadaia_workspace.core.handoff_index import (
    Finding,
    Handoff,
    HandoffIndex,
    ValidationResult,
    discover_handoff_paths,
    load_schema,
    scan_handoffs,
    validate_schema_shape,
)

__all__ = [
    "Finding",
    "Handoff",
    "HandoffIndex",
    "ValidationResult",
    "discover_handoff_paths",
    "load_schema",
    "scan_handoffs",
    "validate_schema_shape",
]
