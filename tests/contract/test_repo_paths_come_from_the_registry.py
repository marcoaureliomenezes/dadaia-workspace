"""Intent: CONTRACT — sa-context-repo-mapping-falls-back-to-the-name#B5: no module builds
``repos/<context name>``; a repo directory comes from ``repo_slug_for_context`` (or an
already-resolved slug). Size: SMALL — one AST walk."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"


def _names_a_context(node: ast.AST) -> bool:
    text = ast.unparse(node)
    return "context" in text and "slug" not in text


def test_no_repos_path_is_built_from_a_context_name() -> None:
    hits = []
    for path in sorted(_PKG.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            if (
                isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Div)
                and isinstance(node.left, ast.BinOp)
                and isinstance(node.left.right, ast.Constant)
                and node.left.right.value == "repos"
                and _names_a_context(node.right)
            ):
                hits.append(f"{path.relative_to(_PKG)}:{node.lineno}: {ast.unparse(node)}")
    assert hits == []
