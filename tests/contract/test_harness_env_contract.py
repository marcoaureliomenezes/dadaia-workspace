"""Intent: CONTRACT — tests/fixtures/harness_env discipline (no DADAIA_* fiction, no in-process hook stdin)

Zero tolerance across tests/: no non-allowlisted DADAIA_* env write outside the fixture module, and no
module that imports a hook behavior module while patching ``sys.stdin`` (use ``run_hook_subprocess``).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.fixtures.harness_env import ALLOWLISTED_DADAIA_ENV, HOOK_MODULES
from tests.helpers.scan_population import assert_populated
from tests.helpers.suite_files import tracked_test_files

pytestmark = pytest.mark.contract

_TESTS_ROOT = Path(__file__).resolve().parent.parent


def _trees() -> dict[str, ast.Module]:
    files = [
        p
        for p in tracked_test_files(_TESTS_ROOT.parent)
        if p.relative_to(_TESTS_ROOT).as_posix() != "fixtures/harness_env.py"
    ]
    assert_populated(files, sentinel=Path(__file__))
    return {
        p.relative_to(_TESTS_ROOT).as_posix(): ast.parse(p.read_text(encoding="utf-8"))
        for p in files
    }


def _str(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _is_environ(node: ast.AST) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == "environ") or (
        isinstance(node, ast.Name) and node.id == "environ"
    )


def _env_writes(tree: ast.Module) -> list[str | None]:
    """Names written by environ[...] =, setenv, environ.setdefault, setitem(environ, ...), environ.update({...})."""
    out: list[str | None] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            out += [
                _str(t.slice)
                for t in node.targets
                if isinstance(t, ast.Subscript) and _is_environ(t.value)
            ]
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
            attr, recv, args = node.func.attr, node.func.value, node.args
            if attr == "setenv" or (attr == "setdefault" and _is_environ(recv)):
                out.append(_str(args[0]))
            elif attr == "setitem" and len(args) >= 2 and _is_environ(args[0]):
                out.append(_str(args[1]))
            elif attr == "update" and _is_environ(recv) and isinstance(args[0], ast.Dict):
                out += [_str(k) for k in args[0].keys if k is not None]
    return out


def _simulates_hook_stdin(tree: ast.Module) -> bool:
    hooks = {
        a.name
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module == "dadaia_workspace.hooks"
        for a in n.names
    }
    hooks |= {
        a.name.split(".")[2]
        for n in ast.walk(tree)
        if isinstance(n, ast.Import)
        for a in n.names
        if a.name.startswith("dadaia_workspace.hooks.")
    }
    if not hooks & set(HOOK_MODULES):
        return False
    for n in ast.walk(tree):
        if (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "setattr"
            and n.args
        ):
            a = n.args
            if _str(a[0]) == "sys.stdin" or (
                isinstance(a[0], ast.Name)
                and a[0].id == "sys"
                and len(a) >= 2
                and _str(a[1]) == "stdin"
            ):
                return True
    return False


def test_no_file_writes_non_allowlisted_dadaia_env() -> None:
    """No test writes a DADAIA_* var that production does not read by design (the allowlist)."""
    offenders = {
        rel: bad
        for rel, tree in _trees().items()
        if (
            bad := [
                v
                for v in _env_writes(tree)
                if v and v.startswith("DADAIA_") and v not in ALLOWLISTED_DADAIA_ENV
            ]
        )
    }
    assert offenders == {}, (
        f"harness-fiction DADAIA_* writes; use claude_hook_env()+run_hook_subprocess(): {offenders}"
    )
    assert "DADAIA_CONTEXT" in ALLOWLISTED_DADAIA_ENV


def test_no_file_simulates_hook_stdin_in_process() -> None:
    """No test imports a hook behavior module and drives it through a patched sys.stdin."""
    offenders = sorted(rel for rel, tree in _trees().items() if _simulates_hook_stdin(tree))
    assert offenders == [], (
        f"in-process hook stdin simulation; use run_hook_subprocess(): {offenders}"
    )
