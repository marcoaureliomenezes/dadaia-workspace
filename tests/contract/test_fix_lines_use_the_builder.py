"""Intent: CONTRACT — AC2.5 (T-050-08): a fix line naming the workspace CLI is built only
by ``core/cli_line.fix_line``.

Scope is fix positions only (PLAN §5/§6 issue 2): the text after a ``fix:`` literal, a
``fix=``/``fix_help=`` argument, a ``Step``/``Refusal`` fix, a ``*fix*`` name's assigned
value and a ``*fix*`` function's returned value. In those positions a hand-built CLI
spelling — the venv path literal, a bare ``dadaia `` command, the deleted ``DADAIA_BIN``
constant or a ``cli_path(…)`` string — is a second spelling of the CLI.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_BUILDER = _PKG / "core" / "cli_line.py"
_SPELLING = re.compile(r"\.dadaia[/\\]\.venv|(?<![\w./-])dadaia\s")
_FIX_KWARGS = frozenset({"fix", "fix_help"})
_FIX_CTORS = {"Step": 1, "Refusal": 1}  # the positional index of the fix argument


def _pieces(node: ast.expr) -> list[str | ast.expr]:
    """A string-valued expression flattened into literal text and interpolated nodes."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        out: list[str | ast.expr] = []
        for value in node.values:
            out.extend(_pieces(value) if isinstance(value, ast.Constant) else [value])
        return out
    if isinstance(node, ast.FormattedValue):
        return [node.value]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return [*_pieces(node.left), *_pieces(node.right)]
    return [node]


def _hand_built(pieces: list[str | ast.expr]) -> bool:
    for piece in pieces:
        if isinstance(piece, str):
            if _SPELLING.search(piece):
                return True
            continue
        for sub in ast.walk(piece):
            if isinstance(sub, ast.Name) and sub.id in {"DADAIA_BIN", "cli_path"}:
                return True
            if isinstance(sub, ast.Attribute) and sub.attr in {"DADAIA_BIN", "cli_path"}:
                return True
            if (
                isinstance(sub, ast.Constant)
                and isinstance(sub.value, str)
                and _SPELLING.search(sub.value)
            ):
                return True
    return False


def _after_fix_colon(pieces: list[str | ast.expr]) -> list[str | ast.expr] | None:
    for index, piece in enumerate(pieces):
        if isinstance(piece, str) and "fix:" in piece:
            return [piece.split("fix:", 1)[1], *pieces[index + 1 :]]
    return None


def _name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _fix_positions(tree: ast.AST) -> Iterator[tuple[int, list[str | ast.expr]]]:
    docstrings = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    for node in ast.walk(tree):
        if id(node) in docstrings:
            continue
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in _FIX_KWARGS:
                    yield node.lineno, _pieces(kw.value)
            index = _FIX_CTORS.get(_name(node.func))
            if index is not None and len(node.args) > index:
                yield node.lineno, _pieces(node.args[index])
        elif isinstance(node, ast.Assign | ast.AnnAssign) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any("fix" in _name(t).lower() for t in targets):
                yield node.lineno, _pieces(node.value)
        elif isinstance(node, ast.FunctionDef) and "fix" in node.name.lower():
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and sub.value is not None:
                    yield sub.lineno, _pieces(sub.value)
        if isinstance(node, ast.JoinedStr | ast.Constant | ast.BinOp):
            tail = _after_fix_colon(_pieces(node))
            if tail is not None:
                yield node.lineno, tail


def _violations() -> list[str]:
    found: set[str] = set()
    for path in sorted(_PKG.rglob("*.py")):
        if path == _BUILDER or "public" in path.relative_to(_PKG).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for line, pieces in _fix_positions(tree):
            if _hand_built(pieces):
                found.add(f"{path.relative_to(_PKG).as_posix()}:{line}")
    return sorted(found)


def test_every_cli_fix_line_goes_through_fix_line() -> None:
    assert _violations() == []


def test_the_scan_catches_a_hand_built_fix() -> None:
    source = 'X = f"fix: {DADAIA_BIN} doctor"\nY = Step("r", ".dadaia/.venv/bin/dadaia doctor")\n'
    hits = [line for line, pieces in _fix_positions(ast.parse(source)) if _hand_built(pieces)]
    assert sorted(set(hits)) == [1, 2]
