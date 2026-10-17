"""The census of the chokepoints' refusals and the verbs' raises: one entry per site, keyed
by its enclosing function. Shared by the two tests that give every site a case."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.oslib import read_text

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"

_CHOKEPOINTS = {
    "branch_policy": _PKG / "features" / "chokepoints" / "branch_policy.py",
    "push_gate": _PKG / "features" / "chokepoints" / "push_gate.py",
}
#: Each module whose verbs raise, and the verbs — every ``raise`` reachable from them
#: (``self.<method>()`` and module-level calls, transitively) is a site.
_VERBS = {
    "ci": (_PKG / "cli" / "commands" / "ci.py", ("push_gate_check",)),
    "service": (_PKG / "features" / "spec_context" / "service.py", ("alive", "baseline", "dead")),
}


def _scopes(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    scopes: dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            scopes |= {
                f"{node.name}.{f.name}": f for f in node.body if isinstance(f, ast.FunctionDef)
            }
        elif isinstance(node, ast.FunctionDef):
            scopes[node.name] = node
    return scopes


def _reachable(scopes: dict[str, ast.FunctionDef], roots: tuple[str, ...]) -> list[str]:
    """Every scope the *roots* reach through ``self.<m>()`` or a module-level call."""
    by_name = {qual.rsplit(".", 1)[-1]: qual for qual in scopes}
    todo, seen = [by_name[r] for r in roots], set()
    while todo:
        qual = todo.pop()
        if qual in seen:
            continue
        seen.add(qual)
        for node in ast.walk(scopes[qual]):
            func = node.func if isinstance(node, ast.Call) else None
            callee = (
                func.attr
                if isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "self"
                else func.id
                if isinstance(func, ast.Name)
                else None
            )
            if callee in by_name:
                todo.append(by_name[callee])
    return sorted(seen)


def fix_sites() -> list[str]:
    """The chokepoints' refusals (a call to ``spell_fix`` or to
    branch_policy's ``_blocked``, whose own body is the renderer) and every ``raise``
    the verbs reach — one entry per refusal, keyed by its enclosing function."""
    sites: list[str] = []
    for stem, path in _CHOKEPOINTS.items():
        for name, fn in _scopes(ast.parse(read_text(path))).items():
            hits = [
                n
                for n in ast.walk(fn)
                if name != "_blocked"
                and (
                    isinstance(n, ast.Call)
                    and getattr(n.func, "id", "") in ("_blocked", "spell_fix")
                )
            ]
            sites += [f"{stem}.{name}"] * len(hits)
    for stem, (path, roots) in _VERBS.items():
        scopes = _scopes(ast.parse(read_text(path)))
        for name in _reachable(scopes, roots):
            raises = [
                n
                for n in ast.walk(scopes[name])
                if (isinstance(n, ast.Raise) and n.exc)
                or (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "fail")
            ]
            sites += [f"{stem}.{name}"] * len(raises)
    return sites
