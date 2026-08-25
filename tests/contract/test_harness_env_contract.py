"""Harness-env contract tests (WS-R5 / FR-R5-01 / AC-R5-01, release v0.1.10).

Two HARD-FAIL contracts protect the harness-env fixture discipline introduced in
``tests/fixtures/harness_env.py``. Both formerly carried per-file *baselines* of pre-existing
violations and failed only on growth; the rc-2 amendment burned those baselines to **zero**,
so each contract now fails on the *first* violation — there is no residual cap.

1. :class:`TestDadaiaEnvSetenvContract` — scans the whole ``tests/`` tree for any write of
   a ``DADAIA_*`` environment variable (``monkeypatch.setenv``, ``os.environ[...] = ...``,
   ``os.environ.setdefault``/``update``, ``setenv(...)``) outside the fixture module. The
   only permitted ``DADAIA_*`` writes are the allowlist in
   ``tests/fixtures/harness_env.ALLOWLISTED_DADAIA_ENV`` — each entry an operator-shell input
   or operator override that production code reads from the environment *by design* (so
   setting it in a unit test exercises a real production env-read path, not harness-fiction).
   Every other ``DADAIA_*`` setenv (``DADAIA_SESSION_ID`` planted as if the harness supplied
   it, persona/mode fiction, the harness-control output-contract vars) is a violation: it
   certifies a mechanism no harness delivers, exactly the audit defect
   (``specs/audits/2026-06-10T010550Z/qa-engineer.md`` §6.1) this contract closes. The
   burn-down (T-010-11 + the rc-2 amendment) rewrote the genuine-fiction sites to the
   subprocess fixture and allowlisted only the by-design env-reads, driving the count to 0.

2. :class:`TestHookBehaviorChannelContract` — flags the harness-**stdin-simulation** pattern:
   a test module that imports a hook *behavior* module (``sdd_gate``/``sdd_post_gate``/
   ``ctx_inject``/``root_whitelist``) **and** patches ``sys.stdin`` in-process to drive its
   ``main()``. Feeding a hook a hand-built stdin payload in-process re-opens the simulated-env
   evasion this fixture exists to kill; harness-real behavior must flow through
   ``run_hook_subprocess`` (which spawns ``python -m dadaia_workspace.hooks.<name>`` with a
   real stdin pipe and a pinned :func:`claude_hook_env`). White-box unit tests that import a
   hook module to call a *pure helper* (``sdd_gate._resolve_mode``) or to fault-inject a
   production internal (``monkeypatch.setattr`` on a module symbol) — and never simulate
   ``sys.stdin`` — are legitimately in-process and are NOT flagged. This replaces the former
   blanket file-level baseline (every importing file) with a precise behavior definition, so
   the contract carries NO file baseline.

Both ratchets are now zero-tolerance: the baseline data structures and over-count guards are
gone, and any new violation fails immediately.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.fixtures.harness_env import ALLOWLISTED_DADAIA_ENV, HOOK_MODULES
from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract

_TESTS_ROOT = Path(__file__).resolve().parent.parent
_FIXTURE_REL = "fixtures/harness_env.py"

# monkeypatch.<attr>(...) calls that *set* an env var (first arg = var name). Removals
# (``delenv``/``os.environ.pop``) are correct hygiene, not violations, so they are excluded.
_SETENV_CALLS: frozenset[str] = frozenset({"setenv"})
# os.environ.<attr>(...) mutators that *set* an env var (first string arg = var name).
_ENVIRON_METHOD_CALLS: frozenset[str] = frozenset({"setdefault"})


def _iter_test_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(_TESTS_ROOT.rglob("*.py")):
        rel = path.relative_to(_TESTS_ROOT).as_posix()
        if rel == _FIXTURE_REL:
            continue  # the fixture module is the one sanctioned home
        if "__pycache__" in path.parts or "node_modules" in path.parts:
            continue
        files.append(path)
    # v0.4.5 FR5 (scan-test-vacuity-guard): a mis-rooted _TESTS_ROOT would degrade this
    # walk to an empty list, under which both _scan_env_violations() and
    # _scan_hook_behavior_violations() below return {} and their `== {}` assertions pass
    # VACUOUSLY GREEN. This file is itself a tests/** module, so it is its own sentinel.
    assert_populated(files, sentinel=Path(__file__))
    return files


def _string_arg(node: ast.AST) -> str | None:
    """Return the literal-string value of an AST node, else ``None``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_environ_subscript(node: ast.expr) -> bool:
    """True for ``os.environ`` / ``environ`` subscript/attr targets."""
    if isinstance(node, ast.Attribute):
        return node.attr == "environ"
    if isinstance(node, ast.Name):
        return node.id == "environ"
    return False


class _EnvVarWriteVisitor(ast.NodeVisitor):
    """Collect the DADAIA_* env var names a test module *writes*."""

    def __init__(self) -> None:
        self.written: list[str] = []

    def _record(self, name: str | None) -> None:
        if name and name.startswith("DADAIA_"):
            self.written.append(name)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Subscript) and _is_environ_subscript(target.value):
                self._record(_string_arg(target.slice))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and node.args:
            arg0 = _string_arg(node.args[0])
            # monkeypatch.setenv("DADAIA_X", ...) / monkeypatch.setitem(os.environ, "DADAIA_X")
            sets_via_first_arg = func.attr in _SETENV_CALLS or (
                # os.environ.setdefault("DADAIA_X", ...)
                func.attr in _ENVIRON_METHOD_CALLS and _is_environ_subscript(func.value)
            )
            if sets_via_first_arg:
                self._record(arg0)
            elif (
                func.attr == "setitem"
                and len(node.args) >= 2
                and _is_environ_subscript(node.args[0])
            ):
                # monkeypatch.setitem(os.environ, "DADAIA_X", ...) — the os.environ escape
                # hatch that bypasses setenv; treated identically to a setenv.
                self._record(_string_arg(node.args[1]))
            # os.environ.update({"DADAIA_X": ...})
            elif func.attr == "update" and _is_environ_subscript(func.value):
                self._record_update(node)
        self.generic_visit(node)

    def _record_update(self, node: ast.Call) -> None:
        if node.args and isinstance(node.args[0], ast.Dict):
            for key in node.args[0].keys:
                if key is not None:
                    self._record(_string_arg(key))


def _scan_env_violations() -> dict[str, int]:
    """Map ``tests/``-relative path → count of non-allowlisted DADAIA_* env writes."""
    violations: dict[str, int] = {}
    for path in _iter_test_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):  # pragma: no cover - defensive
            continue
        visitor = _EnvVarWriteVisitor()
        visitor.visit(tree)
        offending = [v for v in visitor.written if v not in ALLOWLISTED_DADAIA_ENV]
        if offending:
            violations[path.relative_to(_TESTS_ROOT).as_posix()] = len(offending)
    return violations


def _imports_hook_module(tree: ast.Module) -> set[str]:
    """Return hook *behavior* modules imported in a parsed test module.

    Matches ``from dadaia_workspace.hooks import sdd_gate`` and
    ``import dadaia_workspace.hooks.sdd_gate``. ``_common`` is excluded (shared-primitives
    library, legitimate to unit-test directly).
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "dadaia_workspace.hooks":
                for alias in node.names:
                    if alias.name in HOOK_MODULES:
                        found.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                prefix = "dadaia_workspace.hooks."
                if alias.name.startswith(prefix):
                    mod = alias.name[len(prefix) :].split(".")[0]
                    if mod in HOOK_MODULES:
                        found.add(mod)
    return found


def _patches_sys_stdin(tree: ast.Module) -> bool:
    """True if the module patches ``sys.stdin`` in-process (the harness-stdin simulation).

    Detects ``monkeypatch.setattr("sys.stdin", ...)`` and
    ``monkeypatch.setattr(sys, "stdin", ...)`` — the only sanctioned way to feed a hook a
    hand-built stdin payload in-process. That pattern, combined with a hook-module import,
    *is* the in-process behavior-simulation the subprocess runner replaces.
    """
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "setattr" or not node.args:
            continue
        # Form 1: setattr("sys.stdin", ...)
        first = _string_arg(node.args[0])
        if first == "sys.stdin":
            return True
        # Form 2: setattr(sys, "stdin", ...)
        if (
            isinstance(node.args[0], ast.Name)
            and node.args[0].id == "sys"
            and len(node.args) >= 2
            and _string_arg(node.args[1]) == "stdin"
        ):
            return True
    return False


def _scan_hook_behavior_violations() -> dict[str, set[str]]:
    """Map test file → imported hook modules, for files that ALSO simulate ``sys.stdin``.

    Scope is the whole ``tests/`` tree (not just hooks/gate dirs): the simulated-stdin
    evasion is the same wherever it lives. A file is a violation iff it imports a hook
    behavior module AND patches ``sys.stdin`` in-process — i.e. it drives ``main()`` through
    a hand-built stdin rather than ``run_hook_subprocess``.
    """
    violations: dict[str, set[str]] = {}
    for path in _iter_test_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):  # pragma: no cover - defensive
            continue
        mods = _imports_hook_module(tree)
        if mods and _patches_sys_stdin(tree):
            violations[path.relative_to(_TESTS_ROOT).as_posix()] = mods
    return violations


class TestDadaiaEnvSetenvContract:
    """Zero out-of-fixture, non-allowlisted DADAIA_* env writes (hard-fail, no baseline)."""

    def test_no_file_writes_non_allowlisted_dadaia_env(self) -> None:
        current = _scan_env_violations()
        assert current == {}, (
            "Test file(s) write a non-allowlisted DADAIA_* env var outside "
            "tests/fixtures/harness_env.py. Either the var is read from the environment by "
            "production BY DESIGN (add it to ALLOWLISTED_DADAIA_ENV with a one-line "
            "justification naming the production reader), or it is harness-fiction "
            "(DADAIA_SESSION_ID planted as harness-supplied, persona/mode vars, the "
            "DADAIA_HOOK_OUTPUT/EVENT output contract): rewrite the test to "
            "claude_hook_env()/codex_hook_env() + run_hook_subprocess(), or to explicit "
            f"function params / a monkeypatched reader. Offending file -> count: {current}"
        )
        assert "DADAIA_CONTEXT" in ALLOWLISTED_DADAIA_ENV


class TestHookBehaviorChannelContract:
    """No in-process harness-stdin simulation of a hook (hard-fail, no baseline)."""

    def test_no_file_simulates_hook_stdin_in_process(self) -> None:
        current = _scan_hook_behavior_violations()
        assert current == {}, (
            "Test file(s) import a hook behavior module AND patch sys.stdin in-process to "
            "drive its main() — the simulated-env evasion run_hook_subprocess() exists to "
            "kill. Invoke the hook via run_hook_subprocess() with claude_hook_env()/"
            "codex_hook_env() instead. (Pure-helper unit tests like sdd_gate._resolve_mode, "
            "and fault-injection tests that monkeypatch a production internal without "
            "simulating sys.stdin, are legitimately in-process and are not flagged.) "
            f"Offending file -> imported hook modules: "
            f"{ {k: sorted(v) for k, v in current.items()} }"
        )
