"""Source-scan contract — no bare os.chmod in telemetry/service.py (v0.1.53 FR4, AC-4).

The Windows-silent-no-op chmod defect (CWE-732, accepted Tier-2) is prevented structurally,
not just by a runtime test: EVERY ``os.chmod(`` call in ``features/telemetry/service.py``
must be lexically enclosed by an ``if PLATFORM.has_posix_chmod:`` guard. A bare, unguarded
``os.chmod`` — the exact regression this release removes — makes this contract fail.

AC-7(b) mutation-sanity: restoring an unguarded ``os.chmod(...)`` anywhere in the module
makes this test fail (proven on the task line, then reverted).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SERVICE = _REPO_ROOT / "dadaia_workspace" / "features" / "telemetry" / "service.py"


def _is_posix_chmod_guard(test: ast.expr) -> bool:
    """True when *test* is exactly ``PLATFORM.has_posix_chmod``."""
    return (
        isinstance(test, ast.Attribute)
        and test.attr == "has_posix_chmod"
        and isinstance(test.value, ast.Name)
        and test.value.id == "PLATFORM"
    )


def _is_os_chmod_call(node: ast.AST) -> bool:
    """True when *node* is a call to ``os.chmod(...)``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "chmod"
        and isinstance(func.value, ast.Name)
        and func.value.id == "os"
    )


class _ChmodGuardVisitor(ast.NodeVisitor):
    """Collect line numbers of ``os.chmod`` calls NOT under a has_posix_chmod guard."""

    def __init__(self) -> None:
        self.unguarded: list[int] = []
        self.total: int = 0
        self._guard_depth = 0

    def visit_If(self, node: ast.If) -> None:
        if _is_posix_chmod_guard(node.test):
            # The THEN body is guarded; the ELSE body is not.
            self._guard_depth += 1
            for child in node.body:
                self.visit(child)
            self._guard_depth -= 1
            for child in node.orelse:
                self.visit(child)
            # Do not forget the test expression itself (no chmod expected there, but be safe).
            self.visit(node.test)
        else:
            self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if _is_os_chmod_call(node):
            self.total += 1
            if self._guard_depth == 0:
                self.unguarded.append(node.lineno)
        self.generic_visit(node)


def _scan() -> _ChmodGuardVisitor:
    tree = ast.parse(_SERVICE.read_text(encoding="utf-8"), filename=str(_SERVICE))
    visitor = _ChmodGuardVisitor()
    visitor.visit(tree)
    return visitor


def test_every_os_chmod_is_posix_guarded_and_at_least_one_exists() -> None:
    """Every os.chmod() call is enclosed by an `if PLATFORM.has_posix_chmod:` guard,
    and the module still performs at least one guarded chmod (guards against a
    vacuous pass where the guard contract is trivially satisfied by absence)."""
    visitor = _scan()
    assert visitor.unguarded == [], (
        "bare os.chmod() outside an `if PLATFORM.has_posix_chmod:` guard in "
        f"telemetry/service.py at line(s) {visitor.unguarded} — on Windows os.chmod is a "
        "silent no-op (CWE-732); route through the injected FilePermissionSetter or guard "
        "the direct call."
    )
    assert visitor.total >= 1, (
        "no os.chmod call found in telemetry/service.py — the permission-hardening fallback "
        "must still exist (guarded), otherwise the guard contract is vacuously satisfied"
    )
