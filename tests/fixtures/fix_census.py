"""The census of every refusal site: one entry per function of the package and the skill
scripts that spells a ``fix:`` line, found by an AST sweep. Shared by the tests that give every
site a case or a named exemption."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.oslib import read_text

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"
#: A call that spells a fix line: the act and refusal constructors, the printers, or any ``fix=``.
_SPELLERS = {"act", "Refusal", "fail", "spell_fix", "_blocked"}


def _is_site(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and (
        getattr(node.func, "id", "") in _SPELLERS or any(k.arg == "fix" for k in node.keywords)
    )


def _functions(node: ast.AST, prefix: tuple[str, ...] = ()) -> dict[str, ast.AST]:
    found: dict[str, ast.AST] = {}
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            found |= _functions(child, (*prefix, child.name))
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found[".".join((*prefix, child.name))] = child
    return found


def fix_sites() -> list[str]:
    """``<path under the package, no suffix>.<qualified function>`` of every function that spells a
    fix line, sorted; a spelling function's own body is the renderer, not a site."""
    return sorted(
        f"{path.relative_to(_PKG).with_suffix('').as_posix()}.{qual}"
        for path in _PKG.rglob("*.py")
        for qual, fn in _functions(ast.parse(read_text(path))).items()
        if qual.rsplit(".", 1)[-1] not in _SPELLERS and any(map(_is_site, ast.walk(fn)))
    )
