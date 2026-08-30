"""ADR-0001 ("Ring rule stays; a Protocol exists only where two production adapters
exist") is measured HERE — the accepted decision's own text names this file as its
``P-08`` check: "every class under core/protocols has >= 2 implementers under
infrastructure/" — landing in the same commit that retires the single-adapter
protocols.

Intent: CONTRACT — ADR-0001 (P-08). Size: SMALL (directory-tiered ``contract``).

**Structural check chosen (documented per the ADR text's own "choose the simplest
deterministic one" instruction).** A class "implements" a Protocol when its own
method-name set is a SUPERSET of the Protocol's method-name set — the same duck-typing
``typing.Protocol`` itself uses at runtime (``isinstance`` against a
``@runtime_checkable`` Protocol checks attribute *presence*, not signatures either).
This is AST-based (never an import + ``isinstance`` probe): importing every
``infrastructure/`` module just to count classes would pull in real subprocess/OS-level
side-effect modules at collection time, which a SMALL contract test must never do.
A method-name-set match can in principle over- or under-count relative to a stricter
per-signature check; the two-adapter counts asserted below are cross-checked by hand
against the actual adapter files (see each protocol's own docstring) and are stable
unless a protocol or an adapter class is renamed/added.

**Two exception categories (both explicitly enumerated, never silently skipped).**

1. ``_CROSS_FEATURE_COMPOSITION_EXCEPTIONS`` — a handful of ``core/protocols`` classes
   exist not as I/O-boundary ports (ADR-0001's target) but so the ``panel`` feature can
   depend on a sibling feature (``agents``/``spec_context``/``server_registry``)
   WITHOUT importing it directly — the ``features-no-cross-feature`` import-linter
   contract's independence guarantee. Their sole implementer lives under
   ``features/``, never ``infrastructure/`` — ADR-0001 (P-08) only retires the
   ``features-no-infrastructure``/``cli-no-infrastructure`` port set, and this
   cross-feature-independence seam is untouched by that decision.
2. ``_PENDING_RETIREMENT_EXCEPTIONS`` — a genuinely single-adapter protocol not yet
   retired in THIS pass (operator/coordinator directive stopped further retirement
   mid-release); tracked here so the gap is visible and testable, never silently
   invisible. Shrinks to empty as a follow-up ADR-0001 pass lands; this test's own
   ``test_no_stale_pending_retirement_exceptions`` catches a stale entry (one whose
   protocol already has >= 2 adapters, or whose protocol file no longer exists).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROTOCOLS_DIR = _REPO_ROOT / "dadaia_workspace" / "core" / "protocols"
_INFRA_DIR = _REPO_ROOT / "dadaia_workspace" / "infrastructure"

# Cross-feature composition protocols (v0.1.54 FR3 "features -> features" avoidance,
# unchanged by ADR-0001): the panel feature reaches a sibling feature ONLY through one
# of these, never by importing it directly.
_CROSS_FEATURE_COMPOSITION_EXCEPTIONS: dict[str, str] = {
    "AgentsProvider": "implementer is features.agents.reader.FileSystemAgentsProvider",
    "ContextProjectProvider": "implementer is features.spec_context.service.SpecContextService",
    "ServerRegistryProvider": "implementer is features.server_registry.service.ServerRegistryService",
}

# Single-adapter protocols NOT yet retired this pass — visible debt, not silent debt.
# Empty since the RecordStore follow-up pass (ADR-0001): its single adapter
# (infrastructure.jsonl_record_store.JsonlRecordStore) is now the type every consumer
# names directly — core/protocols/record_store.py is deleted.
_PENDING_RETIREMENT_EXCEPTIONS: dict[str, str] = {}

_ALL_EXCEPTIONS = {**_CROSS_FEATURE_COMPOSITION_EXCEPTIONS, **_PENDING_RETIREMENT_EXCEPTIONS}


def _method_names(class_node: ast.ClassDef) -> frozenset[str]:
    """Every method DIRECTLY defined on *class_node* (never inherited, never a nested
    helper function defined inside a method body — only ``ast.FunctionDef``/
    ``AsyncFunctionDef`` nodes that are direct children of the class body), excluding
    dunders (``__init__`` carries no behavioral contract a Protocol method-set check
    should compare against)."""
    return frozenset(
        node.name
        for node in class_node.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not (node.name.startswith("__") and node.name.endswith("__"))
    )


def _is_protocol_base(base: ast.expr) -> bool:
    if isinstance(base, ast.Name):
        return base.id == "Protocol"
    if isinstance(base, ast.Attribute):
        return base.attr == "Protocol"
    return False


def _protocol_classes(path: Path) -> dict[str, frozenset[str]]:
    """Every ``class X(Protocol):`` (or ``class X[T](Protocol):``) defined at MODULE
    scope in *path*, mapped to its own method-name set. A generic Protocol's type
    parameters (PEP 695, e.g. ``RecordStore[T]``) do not affect base-class detection —
    ``ast`` parses ``type_params`` as a separate field from ``bases``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name: _method_names(node)
        for node in tree.body
        if isinstance(node, ast.ClassDef) and any(_is_protocol_base(b) for b in node.bases)
    }


def _infra_classes() -> dict[str, frozenset[str]]:
    """Every class defined at module scope across ``infrastructure/**/*.py``, mapped to
    its own method-name set. Never imports the modules (AST-only) — an import would run
    real subprocess/OS-level top-level code, which a SMALL contract test must never
    pay for at collection time."""
    classes: dict[str, frozenset[str]] = {}
    for path in sorted(_INFRA_DIR.rglob("*.py")):
        if path.name == "__pycache__":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes[node.name] = _method_names(node)
    return classes


def _implementer_count(
    protocol_methods: frozenset[str], infra_classes: dict[str, frozenset[str]]
) -> list[str]:
    """Every infra class name whose OWN method set is a superset of *protocol_methods*
    (structural/duck-typing conformance — the same test ``typing.Protocol`` itself
    uses). A Protocol with zero declared methods matches everything, so an empty
    *protocol_methods* is never asserted against — no protocol under core/protocols/
    today declares zero methods; a future one that does needs its own added exception
    with a reason, not a silent pass here."""
    return [name for name, methods in infra_classes.items() if protocol_methods.issubset(methods)]


def _all_protocol_files() -> list[Path]:
    return sorted(p for p in _PROTOCOLS_DIR.glob("*.py") if p.name != "__init__.py")


def test_every_non_exempt_protocol_has_at_least_two_infrastructure_implementers() -> None:
    infra_classes = _infra_classes()
    failures: list[str] = []
    checked_any = False
    for path in _all_protocol_files():
        for protocol_name, methods in _protocol_classes(path).items():
            if protocol_name in _ALL_EXCEPTIONS:
                continue
            checked_any = True
            implementers = _implementer_count(methods, infra_classes)
            if len(implementers) < 2:
                failures.append(
                    f"{protocol_name} ({path.name}): only {len(implementers)} "
                    f"infrastructure implementer(s) {implementers} for methods "
                    f"{sorted(methods)} — ADR-0001 (P-08) requires >= 2, or an "
                    "explicit exception in this test with a reason."
                )
    assert checked_any, "no non-exempt Protocol classes found under core/protocols/ — suspicious"
    assert not failures, "single-adapter Protocol(s) not covered by an exception:\n" + "\n".join(
        failures
    )


def test_no_stale_pending_retirement_exceptions() -> None:
    """Every ``_PENDING_RETIREMENT_EXCEPTIONS`` entry must name a Protocol that (a)
    still exists under ``core/protocols/`` and (b) still has FEWER than 2
    infrastructure implementers — a stale entry (already retired, or already grown a
    second adapter) must be deleted from the exception list in the SAME commit that
    changes the underlying reality, never left behind as dead debt-tracking."""
    infra_classes = _infra_classes()
    protocol_methods: dict[str, frozenset[str]] = {}
    for path in _all_protocol_files():
        protocol_methods.update(_protocol_classes(path))

    stale: list[str] = []
    for name in _PENDING_RETIREMENT_EXCEPTIONS:
        if name not in protocol_methods:
            stale.append(f"{name}: no longer exists under core/protocols/ — delete this exception")
            continue
        implementers = _implementer_count(protocol_methods[name], infra_classes)
        if len(implementers) >= 2:
            stale.append(
                f"{name}: now has {len(implementers)} implementers {implementers} — "
                "delete this exception, it is retired"
            )
    assert not stale, "stale _PENDING_RETIREMENT_EXCEPTIONS entries:\n" + "\n".join(stale)
