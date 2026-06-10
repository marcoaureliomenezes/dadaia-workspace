"""Harness-env contract tests (WS-R5 / FR-R5-01 / AC-R5-01, release v0.1.10).

Two ratcheting contracts protect the harness-env fixture discipline introduced in
``tests/fixtures/harness_env.py``:

1. :class:`TestDadaiaEnvSetenvContract` — scans the whole ``tests/`` tree for any write of
   a ``DADAIA_*`` environment variable (``monkeypatch.setenv``, ``os.environ[...] = ...``,
   ``os.environ.setdefault``/``update``, ``setenv(...)``) outside the fixture module, with
   an explicit allowlist (``DADAIA_CONTEXT`` — the operator-shell context var). The audit
   (``specs/audits/2026-06-10T010550Z/qa-engineer.md`` §6.1, defect 2) showed tests planting
   ``DADAIA_SESSION_ID`` / persona vars that no harness delivers, certifying dead
   mechanisms. The ideal end state is **zero** out-of-fixture session/mode/persona setenvs;
   T-010-11 burns the existing ones down. To keep the suite green *now* while ratcheting,
   this contract records a per-file baseline of pre-existing violations and fails only on
   **growth** (a new violating file, or more violations in a baselined file).

2. :class:`TestHookImportContract` — flags direct import+call of a hook *behavior* module
   (``sdd_gate``/``sdd_post_gate``/``ctx_inject``/``root_whitelist``) inside
   ``tests/**/hooks|gate/**``. Behavior tests must drive hooks through
   ``run_hook_subprocess`` (the harness-real path), not by importing ``main()`` in-process
   — the in-process path re-opens the ``os.environ.update`` evasion. Same growth-only
   ratchet: a per-file baseline is recorded and only new offending files fail.

Both ratchets are intentionally *recorded baselines* of CURRENT reality, not aspirational
zeros, so this task ships green and the named follow-up tasks (T-010-11 for the setenvs,
the hook-subprocess migrations for the imports) drive the counts to zero.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.fixtures.harness_env import ALLOWLISTED_DADAIA_ENV, HOOK_MODULES

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
            # monkeypatch.setenv("DADAIA_X", ...)
            sets_via_first_arg = func.attr in _SETENV_CALLS or (
                # os.environ.setdefault("DADAIA_X", ...)
                func.attr in _ENVIRON_METHOD_CALLS and _is_environ_subscript(func.value)
            )
            if sets_via_first_arg:
                self._record(arg0)
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


# Recorded baseline of pre-existing out-of-fixture DADAIA_* env writes (2026-06-10, HEAD
# of feature/v0.1.10). Burned down by T-010-11; this contract fails only on GROWTH.
_ENV_BASELINE: dict[str, int] = {
    "unit/features/agents/test_reader.py": 15,
    "unit/features/panel/test_api_agent_prompt.py": 6,
    "unit/features/workflows/test_service.py": 1,
    "unit/hooks/test_common.py": 1,
    "unit/hooks/test_ctx_inject.py": 3,
    "unit/hooks/test_sdd_post_gate.py": 5,
    "unit/test_container.py": 1,
}


def _import_offending_hook_modules(tree: ast.Module) -> set[str]:
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


def _scan_hook_import_violations() -> dict[str, set[str]]:
    """Map ``tests/**/hooks|gate/**`` file → set of directly-imported hook modules."""
    violations: dict[str, set[str]] = {}
    for path in _iter_test_files():
        parts = set(path.relative_to(_TESTS_ROOT).parts)
        if not ({"hooks", "gate"} & parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):  # pragma: no cover - defensive
            continue
        mods = _import_offending_hook_modules(tree)
        if mods:
            violations[path.relative_to(_TESTS_ROOT).as_posix()] = mods
    return violations


# Recorded baseline of test files in tests/**/hooks|gate/** that import a hook behavior
# module directly (instead of going through run_hook_subprocess). Migrated by the
# hook-subprocess tasks; this contract fails only on GROWTH (a new offending file).
_HOOK_IMPORT_BASELINE: frozenset[str] = frozenset(
    {
        "unit/hooks/test_ctx_inject.py",
        "unit/hooks/test_root_whitelist.py",
        "unit/hooks/test_sdd_gate.py",
        "unit/hooks/test_sdd_post_gate.py",
    }
)


class TestDadaiaEnvSetenvContract:
    """No new out-of-fixture DADAIA_* env writes (growth-only ratchet)."""

    def test_no_new_files_write_dadaia_env(self) -> None:
        current = _scan_env_violations()
        new_files = sorted(set(current) - set(_ENV_BASELINE))
        assert not new_files, (
            "New test file(s) write a non-allowlisted DADAIA_* env var outside "
            "tests/fixtures/harness_env.py. Hook/gate/lease tests must build env via "
            "claude_hook_env()/codex_hook_env(); other DADAIA_* config must be set in "
            f"the fixture or allowlisted. Offending: {new_files}"
        )

    def test_no_baselined_file_grows(self) -> None:
        current = _scan_env_violations()
        grown = {
            f: (current[f], _ENV_BASELINE[f])
            for f in _ENV_BASELINE
            if current.get(f, 0) > _ENV_BASELINE[f]
        }
        assert not grown, (
            "A baselined file added MORE non-allowlisted DADAIA_* env writes. The ratchet "
            f"only goes down (T-010-11 burns these to zero). file -> (now, baseline): {grown}"
        )

    def test_baseline_does_not_overcount(self) -> None:
        """Baseline must not exceed reality — keeps the recorded numbers honest."""
        current = _scan_env_violations()
        stale = {
            f: (current.get(f, 0), _ENV_BASELINE[f])
            for f in _ENV_BASELINE
            if _ENV_BASELINE[f] > current.get(f, 0)
        }
        assert not stale, (
            "Baseline over-counts (a file dropped below its recorded count). Lower the "
            f"baseline so the ratchet keeps biting. file -> (now, baseline): {stale}"
        )

    def test_context_var_is_allowlisted(self) -> None:
        assert "DADAIA_CONTEXT" in ALLOWLISTED_DADAIA_ENV


class TestHookImportContract:
    """No new direct hook-behavior imports in tests/**/hooks|gate/** (growth-only)."""

    def test_no_new_direct_hook_imports(self) -> None:
        current = set(_scan_hook_import_violations())
        new_files = sorted(current - _HOOK_IMPORT_BASELINE)
        assert not new_files, (
            "New behavior test in tests/**/hooks|gate/** imports a hook module directly. "
            "Invoke the hook via run_hook_subprocess() with claude_hook_env()/"
            f"codex_hook_env() instead. Offending: {new_files}"
        )

    def test_baseline_files_still_exist(self) -> None:
        """Baseline stays honest — a migrated/removed file must leave the baseline."""
        current = set(_scan_hook_import_violations())
        stale = sorted(_HOOK_IMPORT_BASELINE - current)
        assert not stale, (
            "Baselined file no longer imports a hook module directly (migrated/removed). "
            f"Drop it from _HOOK_IMPORT_BASELINE so the ratchet keeps biting: {stale}"
        )
