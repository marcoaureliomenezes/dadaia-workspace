"""Regression seam for the ``jsonschema``-in-mutation-scope bug (resolves bug
``mutation-baseline-core-models-scope-now-imports-jsonschema-isolated-venv-cannot-collect``).

``tests/scripts/run_mutation_baseline.sh`` stages ONLY ``dadaia_workspace/core/models/``
and ``tests/unit/core/models/`` into an isolated venv that installs nothing beyond
``mutmut``/``pytest`` (its own header comment: "import nothing beyond stdlib + pytest ...
verified: no third-party top-level import across either tree"). That invariant was never
an executable check — a new test file importing a third-party package (as
``tests/unit/core/models/test_bug_record.py`` did at T-050-07, importing ``jsonschema``)
silently broke the isolated venv's ability to collect, discovered only by actually running
the ~20-minute mutation baseline. This AST ratchet makes the same invariant a SMALL, fast,
always-on check: no top-level import in either scoped directory names a module outside
{stdlib, ``pytest``, first-party ``dadaia_workspace``}.

Deliberately silent about intra-``dadaia_workspace`` package boundaries (e.g. a
``core/models/`` file importing a sibling outside ``core/models/``, such as
``core.redaction``) — that is a SEPARATE, already-registered gap (bug
``mutation-baseline-core-models-scope-omits-public-schemas-fixture-directory``'s sibling
concern), not this bug's fix; encoding it here would make this seam fail for a change
this task does not own.

Intent: CONTRACT — pins the fix for
``mutation-baseline-core-models-scope-now-imports-jsonschema-isolated-venv-cannot-collect``.

Size: SMALL — pure AST scan, no subprocess, no venv.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCOPED_DIRS = (
    _REPO_ROOT / "dadaia_workspace" / "core" / "models",
    _REPO_ROOT / "tests" / "unit" / "core" / "models",
)

_ALLOWED_ROOTS = frozenset(sys.stdlib_module_names) | {"pytest", "dadaia_workspace"}


def _scoped_files() -> list[Path]:
    files: list[Path] = []
    for scoped_dir in _SCOPED_DIRS:
        files.extend(sorted(p for p in scoped_dir.glob("*.py") if p.name != "__init__.py"))
    return files


def _top_level_import_roots(source: str, filename: str) -> set[str]:
    """Every top-level (module-scope) import's root package name — ``import a.b.c`` and
    ``from a.b import c`` both yield ``"a"``; a relative import (``from . import x``,
    ``level > 0``) yields nothing (it can only ever reach a first-party sibling)."""
    tree = ast.parse(source, filename=filename)
    roots: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0 or node.module is None:
                continue
            roots.add(node.module.split(".")[0])
    return roots


def test_scoped_files_exist() -> None:
    """Guards the scan itself against a silently-empty glob."""
    assert len(_scoped_files()) >= 5


def test_no_third_party_top_level_import_in_the_mutation_baseline_scope() -> None:
    offenses: dict[str, set[str]] = {}
    for candidate in _scoped_files():
        roots = _top_level_import_roots(
            candidate.read_text(encoding="utf-8"), str(candidate.relative_to(_REPO_ROOT))
        )
        disallowed = roots - _ALLOWED_ROOTS
        if disallowed:
            offenses[str(candidate.relative_to(_REPO_ROOT))] = disallowed

    assert not offenses, (
        "run_mutation_baseline.sh's isolated venv installs nothing beyond mutmut/pytest — "
        "a third-party top-level import here breaks pytest-collection in that sandbox "
        f"(see the script's own header comment): {offenses}"
    )
