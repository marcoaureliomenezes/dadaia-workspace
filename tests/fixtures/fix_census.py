"""The census of refusal sites: one entry per site, keyed by its enclosing function. Two scopes, no
more: every ``raise`` reachable from the pre-push gate and the ``context`` verbs (plus the
chokepoints' refusals), and every function of the ``dd-gitflow-default`` worktree scripts that ends
a statement in a ``fix:`` line. One consumer, ``tests/core/test_cli_line__refusal_fix_lines_clear_their_refusal.py``,
gives every site a case or a named ``Skip``."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.oslib import read_text

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"

_SCRIPTS = _PKG / "public" / "skills" / "dd-gitflow-default" / "scripts"
#: A call that spells a fix line: the act and refusal constructors, the printers, or any ``fix=``.
_SPELLERS = {"act", "Refusal", "fail", "spell_fix", "_blocked"}

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


def _refusals(fn: ast.AST) -> int:
    """How many statements of *fn* end in a fix line (a raise, a return or a bare call that spells
    one); a function that only assigns one counts once."""
    ends = sum(
        isinstance(s, (ast.Raise, ast.Return, ast.Expr)) and any(map(_is_site, ast.walk(s)))
        for s in ast.walk(fn)
    )
    return ends or 1


def fix_sites() -> list[str]:
    """The chokepoints' refusals (a call to ``spell_fix`` or to branch_policy's ``_blocked``, whose
    own body is the renderer), every ``raise`` the verbs reach, and each worktree-script function
    that spells a fix line once per statement that ends in one (a spelling function's own body is
    the renderer, not a site) — keyed by the enclosing function."""
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
    for path in sorted(_SCRIPTS.glob("*.py")):
        for qual, fn in _functions(ast.parse(read_text(path))).items():
            if qual.rsplit(".", 1)[-1] not in _SPELLERS and any(map(_is_site, ast.walk(fn))):
                sites += [f"{path.stem}.{qual}"] * _refusals(fn)
    return sites
