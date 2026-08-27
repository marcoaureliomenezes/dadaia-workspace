"""A3.10's two-sided import fence around the deletable ``migrate_v5`` module.

Intent: CONTRACT — 0.5.0 A3.10. Size: SMALL.

**The regression this guards against (SA-Q4, `specs/releases/0.5.0/reviews
/S1-AR1-ruling.md` §3).** The first Draft called the FR3 derivation "a pure core
function" and then placed it INSIDE ``features/bugs/migrate_v5.py`` — the module FR3
itself declares deletable at 0.6.0 — while FR8's resolver and FR14's pillar 1 both need
to import it permanently. A permanent consumer importing a disposable module is exactly
the fidelity defect the split (``core/bug_provenance.py``) closes; this test is the
ratchet that keeps it closed, scanned by AST rather than declared by a hand-kept list
(same convention as ``tests/unit/core/test_atomic_write_census.py``).

**Two assertions, by SHAPE:**

1. ``core/bug_provenance.py`` itself imports nothing from ``dadaia_workspace.features``
   — the derivation stays pure and stdlib-only, by construction, not by promise.
2. Outside ``tests/**`` and ``migrate_v5.py`` itself, ``migrate_v5`` is imported from
   exactly ONE already-known, already-documented site:
   ``features/bugs/service.py`` (T-050-08's ``read_ledger`` render-side consumer,
   named "deleted whole once T-050-10 rewrites the physical ledger ... and
   ``features/bugs/service.py`` drops this import" in ``migrate_v5.py``'s own module
   docstring — a pre-existing, D-F "switch" step **not** in this task's write set, so
   this test pins it as a NAMED, dated exception rather than silently allowing it).
   ANY additional importer — a hypothetical FR8 resolver or FR14 pillar-1 module reading
   the derivation through the wrong door — fails this test loudly.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.scan_population import assert_populated

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_ROOT = _REPO_ROOT / "dadaia_workspace"
_BUG_PROVENANCE = _PACKAGE_ROOT / "core" / "bug_provenance.py"
_MIGRATE_V5 = _PACKAGE_ROOT / "features" / "bugs" / "migrate_v5.py"
_MIGRATE_V5_DOTTED = "dadaia_workspace.features.bugs.migrate_v5"

#: The one pre-existing, dated, D-F "switch"-step exception (T-050-08) — retired by
#: T-050-10 per migrate_v5.py's own module docstring. Any OTHER hit is a regression.
_KNOWN_MIGRATE_V5_IMPORTERS: frozenset[str] = frozenset(
    {"dadaia_workspace/features/bugs/service.py"}
)


def _module_dotted_names(node: ast.Import | ast.ImportFrom) -> set[str]:
    """Every fully-qualified name *node* could bind — both ``import a.b.c`` and
    ``from a.b import c`` shapes, so a hit is caught regardless of import style.
    ``dadaia_workspace/`` uses only absolute imports (zero-hit grep for ``^from \\.``
    across the package, verified at authoring time) — a relative import is
    deliberately not resolved here, matching the codebase's own convention."""
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}
    module = node.module or ""
    return {f"{module}.{alias.name}" for alias in node.names} | {module}


def _imports_migrate_v5(path: Path) -> bool:
    """True iff *path* contains an ``import``/``from ... import`` statement that binds
    :data:`_MIGRATE_V5_DOTTED` — the module itself (``import a.b.migrate_v5`` /
    ``from a.b import migrate_v5``) or one of its names
    (``from a.b.migrate_v5 import X``); both shapes surface ``_MIGRATE_V5_DOTTED`` in
    :func:`_module_dotted_names`'s returned set."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return False
    return any(
        isinstance(node, (ast.Import, ast.ImportFrom))
        and _MIGRATE_V5_DOTTED in _module_dotted_names(node)
        for node in ast.walk(tree)
    )


def test_bug_provenance_imports_nothing_from_features() -> None:
    tree = ast.parse(_BUG_PROVENANCE.read_text(encoding="utf-8"), filename=str(_BUG_PROVENANCE))
    feature_imports = [
        name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for name in _module_dotted_names(node)
        if name.startswith("dadaia_workspace.features")
    ]
    assert feature_imports == [], (
        f"core/bug_provenance.py must stay stdlib-only, no features/** import "
        f"(A3.10): found {feature_imports}"
    )


def test_migrate_v5_has_no_permanent_consumer_outside_the_known_switch_step() -> None:
    files = sorted(p for p in _PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in p.parts)
    assert_populated(files, sentinel=_MIGRATE_V5)

    hits = {
        path.relative_to(_REPO_ROOT).as_posix()
        for path in files
        if path != _MIGRATE_V5 and _imports_migrate_v5(path)
    }

    assert hits == _KNOWN_MIGRATE_V5_IMPORTERS, (
        "a module outside the known, dated T-050-08 switch-step import now depends on "
        f"the deletable migrate_v5 module (A3.10) — expected exactly "
        f"{sorted(_KNOWN_MIGRATE_V5_IMPORTERS)}, found {sorted(hits)}"
    )
