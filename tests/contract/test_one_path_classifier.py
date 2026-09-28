"""Intent: CONTRACT — sa-gate-path-classes-diverge-from-the-law#B39-6: one classifier.
The class tables (``SPECS_ADDITIVE_GLOBS``, ``additive_prefixes()``) are read by
``gate_policy`` alone and ``classify_path`` is the one producer of a ``PathClass``;
any other module only compares the verdict it returned. Size: SMALL — one AST walk."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_TABLES = {"SPECS_ADDITIVE_GLOBS", "additive_prefixes"}
_OWNERS = {"features/spec_context/gate_policy.py", "core/workspace_layout.py"}


def _uses(path: Path) -> set[str]:
    tree = ast.parse(path.read_text("utf-8"))
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    return names


def test_the_class_tables_have_one_reader() -> None:
    readers = sorted(
        path.relative_to(_PKG).as_posix()
        for path in _PKG.rglob("*.py")
        if path.relative_to(_PKG).as_posix() not in _OWNERS and _uses(path) & _TABLES
    )
    assert readers == []


def test_no_other_module_calls_a_path_class_into_being() -> None:
    """``PathClass(...)`` or ``PathClass.X`` as a return value outside gate_policy."""
    producers = []
    for path in sorted(_PKG.rglob("*.py")):
        if path.relative_to(_PKG).as_posix() in _OWNERS:
            continue
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            value = node.value if isinstance(node, ast.Return) else None
            if isinstance(value, ast.Attribute) and "PathClass" in ast.unparse(value):
                producers.append(f"{path.relative_to(_PKG)}:{node.lineno}")
    assert producers == []
