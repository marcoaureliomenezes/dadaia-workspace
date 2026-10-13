"""Every leaf verb of the real Typer app, walked dynamically, resolves ``--context``/``--specs-dir``
through the seam: no literal default, and the value reaches a seam call (module-local AST reachability).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import typer

from dadaia_workspace.cli.main import app
from tests.helpers.scan_population import assert_populated

_CLI_COMMANDS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "cli" / "commands"
_SEAM_FUNCTIONS = frozenset(
    {"resolve_specs_dir_for_cli", "resolve_context_for_cli", "resolve_context_specs_dir_for_cli"}
)
# Its ``context`` kwarg equality-filters an already-resolved list; it is not a resolution input.
_FILTER_ONLY_FACTORIES = frozenset({"container.build_workflow_handoff_doctor"})


def _leaf_params() -> list[tuple[tuple[str, ...], Any, str]]:
    """(verb path, command, param name) for every context/specs_dir param of every leaf verb."""
    out: list[tuple[tuple[str, ...], Any, str]] = []

    # Recurse on ``.commands``: Typer's vendored click shim fails isinstance(click.Group).
    def walk(cmd: Any, prefix: tuple[str, ...]) -> None:
        if getattr(cmd, "commands", None) is not None:
            for name, sub in cmd.commands.items():
                walk(sub, (*prefix, name))
        else:
            out.extend(
                (prefix, cmd, p.name) for p in cmd.params if p.name in {"context", "specs_dir"}
            )

    walk(typer.main.get_command(app), ())
    return out


def _label(path: tuple[str, ...], param: str) -> str:
    return f"dadaia {' '.join(path)} --{param.replace('_', '-')}"


def _closure(fn: ast.FunctionDef, seed: str) -> set[str]:
    """Local names transitively assigned from *seed* inside *fn* (``ctx = context or ...``)."""
    tainted, grown = {seed}, True
    while grown:
        before = len(tainted)
        for node in ast.walk(fn):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            if {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)} & tainted:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                tainted |= {t.id for t in targets if isinstance(t, ast.Name)}
        grown = len(tainted) > before
    return tainted


def _callee(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    container = (
        isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "container"
    )
    if container and f.attr.startswith(("build_", "resolve_")):  # type: ignore[union-attr]
        return f"container.{f.attr}"  # type: ignore[union-attr]
    return None


def _reaches_seam(module: Path, func_name: str, param: str) -> bool:
    """*param* of *func_name* flows by name into a seam call, directly or via module-local helpers."""
    tree = ast.parse(module.read_text(encoding="utf-8"))
    defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    seen: set[tuple[str, str]] = set()

    def explore(fn_name: str, seed: str) -> bool:
        if (fn_name, seed) in seen or fn_name not in defs:
            return False
        seen.add((fn_name, seed))
        fn = defs[fn_name]
        tainted = _closure(fn, seed)
        for call in (n for n in ast.walk(fn) if isinstance(n, ast.Call)):
            name = _callee(call)
            if name is None or name in _FILTER_ONLY_FACTORIES:
                continue
            passed = [a for a in call.args] + [kw.value for kw in call.keywords]
            if (name in _SEAM_FUNCTIONS or name.startswith("container.")) and any(
                isinstance(a, ast.Name) and a.id in tainted for a in passed
            ):
                return True
            helper = defs.get(name)
            if helper is None or name == fn_name:
                continue
            params = [a.arg for a in helper.args.args + helper.args.kwonlyargs]
            hops = [
                params[i]
                for i, a in enumerate(call.args)
                if i < len(params) and isinstance(a, ast.Name) and a.id in tainted
            ]
            hops += [
                kw.arg
                for kw in call.keywords
                if kw.arg in params and isinstance(kw.value, ast.Name) and kw.value.id in tainted
            ]
            if any(explore(name, h) for h in hops if h is not None):
                return True
        return False

    return explore(func_name, param)


def test_no_resolver_driven_verb_hardcodes_the_dadaia_workspace_default() -> None:
    """No context/specs_dir option of any verb defaults to the literal ``"dadaia-workspace"``."""
    params = _leaf_params()
    assert_populated([path for path, _c, _p in params], sentinel=("specs", "upgrade"))
    offenders = [
        _label(path, name)
        for path, cmd, name in params
        if next(p for p in cmd.params if p.name == name).default == "dadaia-workspace"
    ]
    assert not offenders, (
        f"hardcoded context default; resolve through the seam instead: {sorted(offenders)}"
    )


def test_every_resolver_driven_verb_reaches_the_seam_family() -> None:
    """Every context/specs_dir param of every verb reaches a seam call (no known non-resolver param)."""
    params = _leaf_params()
    assert params, "dynamic walk found zero context/specs_dir params"
    unreached = [
        _label(path, name)
        for path, cmd, name in params
        if not (
            (_CLI_COMMANDS / f"{path[0]}.py").is_file()
            and _reaches_seam(
                _CLI_COMMANDS / f"{path[0]}.py", getattr(cmd.callback, "__name__", ""), name
            )
        )
    ]
    assert not unreached, f"param(s) never reach the resolution seam: {sorted(unreached)}"
