"""One owner per question: each rule scans the package and names every module that answers a
question its owner alone answers.

Intent: CONTRACT — P-11 core file-I/O purity, P-12 hooks never import the container, P-18 module
ceiling, F001 no orphaned factory, and the single-owner bug fixes cited on each row. Size: SMALL —
AST/text over the package source, plus one subprocess per hook import.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS, L1_ENTRY_HARNESSES
from dadaia_workspace.infrastructure.runtime_config import codex_config, merge_claude_settings
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import HOOK_DIALECTS
from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PKG = _REPO_ROOT / "dadaia_workspace"
_REGISTRY = _PKG / "public" / "entities" / "registry.json"


def _rel(path: Path) -> str:
    return path.relative_to(_PKG).as_posix()


def _trees(glob: str = "**/*.py") -> Iterator[tuple[Path, ast.Module]]:
    paths = sorted(p for p in _PKG.glob(glob) if "__pycache__" not in p.parts)
    assert_populated(paths, sentinel=paths[0] if paths else _PKG / "missing")
    for path in paths:
        yield path, ast.parse(path.read_text(encoding="utf-8"))


def _called(node: ast.Call) -> str:
    return getattr(node.func, "attr", getattr(node.func, "id", ""))


def _functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    yield from (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef))


#: core/ modules whose file I/O is architecture-authorized (ARCHITECTURE.md P-11); new I/O
#: enters core/ only by joining this set on purpose.
_CORE_IO_STEMS = frozenset(
    {"workspace_resolver", "atomic_write", "context_registry", "session_store", "handoff_index",
     "template_history", "gitflow", "workspace_layout"}
)  # fmt: skip
_PATH_IO_ATTRS = frozenset(
    {"read_text", "write_text", "mkdir", "exists", "glob", "iterdir", "rglob"}
)


def _core_file_io() -> list[str]:
    """Any open()/Path I/O/shutil copy-or-move call in a core module outside the authorized
    set, plus any authorized stem that no longer names a module."""
    hits, stems = [], set()
    for path, tree in _trees("core/**/*.py"):
        stems.add(path.stem)
        if path.stem in _CORE_IO_STEMS:
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            if (
                (isinstance(f, ast.Name) and f.id == "open")
                or (isinstance(f, ast.Attribute) and f.attr in _PATH_IO_ATTRS)
                or (
                    isinstance(f, ast.Attribute)
                    and isinstance(f.value, ast.Name)
                    and f.value.id == "shutil"
                    and (f.attr.startswith("copy") or f.attr == "move")
                )
            ):
                hits.append(f"{_rel(path)}:{n.lineno}")
    return hits + [f"stale authorized stem {s}" for s in sorted(_CORE_IO_STEMS - stems)]


def _session_paths() -> list[str]:
    """Only core/session_store.py builds a session-record path; nobody builds the retired
    ``sessions/runtime/*.ptr`` pointer namespace."""
    pointer = ('"sessions" / "runtime"', '"runtime" / f"{')
    record = ('"sessions" / f"{', '".dadaia" / "sessions"')
    hits = []
    for path in sorted(_PKG.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        idioms = pointer + (() if _rel(path) == "core/session_store.py" else record)
        hits += [f"{_rel(path)}: {i}" for i in idioms if i in text]
    return hits


def _orphan_factories() -> list[str]:
    """Every container.py def/class is used by production code outside it, or by another
    container definition — a test-only consumer does not count."""
    source = (_PKG / "container.py").read_text(encoding="utf-8")
    defs = re.findall(r"^(?:def|class) ([A-Za-z_][A-Za-z0-9_]*)", source, re.M)
    assert defs, "container.py defines nothing? the scan is broken"
    others = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted(_PKG.rglob("*.py"))
        if p.name != "container.py"
    )

    def used(text: str, name: str) -> bool:
        return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text) is not None

    return [
        n
        for n in defs
        if not used(others, n)
        and not used(re.sub(rf"^(?:def|class) {n}\b", "", source, flags=re.M), n)
    ]


def _doctor_modules_over_ceiling() -> list[str]:
    """P-18: no features/specs/doctor*.py above 699 lines (lower it after a split)."""
    modules = sorted((_PKG / "features" / "specs").glob("doctor*.py"))
    assert modules
    return [p.name for p in modules if len(p.read_text(encoding="utf-8").splitlines()) > 699]


def _rmtree_sites() -> list[str]:
    """Only create's rollback of its own clones and the TTL primitive may rmtree in the one
    owner of repos/."""
    allowed = {"service.py:create", "sweep.py:remove"}
    sites = {
        f"{path.name}:{fn.name}"
        for path, tree in _trees("features/spec_context/*.py")
        for fn in _functions(tree)
        if fn.name != "rmtree"
        and any(isinstance(c, ast.Call) and _called(c) == "rmtree" for c in ast.walk(fn))
    }
    return sorted(sites ^ allowed)


def _ttl_clocks() -> list[str]:
    """No `*_TTL*` constant outside the zone registry (the session record's own clock excepted)."""
    allowed = {"SESSION_GC_TTL_SECONDS"}
    return [
        f"{_rel(path)}:{t.id}"
        for path, tree in _trees()
        if "public" not in path.relative_to(_PKG).parts and path.name != "workspace_layout.py"
        for n in ast.walk(tree)
        for t in (
            n.targets
            if isinstance(n, ast.Assign)
            else [n.target]
            if isinstance(n, ast.AnnAssign)
            else []
        )
        if isinstance(t, ast.Name) and "_TTL" in t.id and t.id not in allowed
    ]


_PATH_CLASS_OWNERS = {"features/spec_context/gate_policy.py", "core/workspace_layout.py"}


def _path_class_tables_read_elsewhere() -> list[str]:
    tables = {"additive_prefixes"}
    return [
        _rel(path)
        for path, tree in _trees()
        if _rel(path) not in _PATH_CLASS_OWNERS
        and tables
        & (
            {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            | {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            | {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
        )
    ]


def _path_class_produced_elsewhere() -> list[str]:
    return [
        f"{_rel(path)}:{n.lineno}"
        for path, tree in _trees()
        if _rel(path) not in _PATH_CLASS_OWNERS
        for n in ast.walk(tree)
        if isinstance(n, ast.Return)
        and isinstance(n.value, ast.Attribute)
        and "PathClass" in ast.unparse(n.value)
    ]


def _release_state_writes() -> list[str]:
    """core/release_state.py parses and serializes a supplied document; it never reads or
    writes disk (the CAS write stays in features/infrastructure)."""
    source = (_PKG / "core" / "release_state.py").read_text(encoding="utf-8")
    writers = {"write_text", "write_bytes", "mkdir", "unlink", "rmdir", "atomic_write", "open"}
    hits = [
        f"release_state.py:{n.lineno}:{_called(n)}"
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Call) and _called(n) in writers
    ]
    return hits + (["release_state.py: read_text("] if "read_text(" in source else [])


def _repos_path_from_a_context_name() -> list[str]:
    return [
        f"{_rel(path)}:{n.lineno}"
        for path, tree in _trees()
        for n in ast.walk(tree)
        if isinstance(n, ast.BinOp)
        and isinstance(n.op, ast.Div)
        and isinstance(n.left, ast.BinOp)
        and isinstance(n.left.right, ast.Constant)
        and n.left.right.value == "repos"
        and "context" in (text := ast.unparse(n.right))
        and "slug" not in text
    ]


def _raw_specs_writes() -> list[str]:
    """features/migrate and features/specs write only through core.atomic_write."""
    hits = []
    for glob in ("features/migrate/*.py", "features/specs/*.py"):
        for path, tree in _trees(glob):
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Attribute):
                    continue
                name, owner = n.func.attr, n.func.value
                is_os = isinstance(owner, ast.Name) and owner.id == "os"
                opens_for_write = name == "open" and any(
                    isinstance(a, ast.Constant) and str(a.value)[:1] in {"w", "a", "x"}
                    for a in n.args
                )
                if (
                    name in {"write_text", "write_bytes"}
                    or (is_os and name in {"replace", "open"})
                    or opens_for_write
                ):
                    hits.append(f"{path.name}:{n.lineno}:{name}")
    return hits


def _reaped_zone_deleters() -> list[str]:
    """Holds die only in the doctor's EXPIRED lane, which never names ``reaped``."""
    return [
        f"{_rel(path)}:{fn.name}"
        for path, tree in _trees()
        for fn in _functions(tree)
        if any(
            (isinstance(n, ast.Constant) and n.value == "reaped")
            or (isinstance(n, ast.Name) and n.id == "REAPED_ZONE")
            for n in ast.walk(fn)
        )
        and any(
            isinstance(n, ast.Call) and _called(n) in {"remove", "rmtree", "unlink", "rmdir"}
            for n in ast.walk(fn)
        )
    ]


def _layout_sets_read_by(module: str) -> list[str]:
    tree = ast.parse((_PKG / module).read_text(encoding="utf-8"))
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    sets = {
        "ROOT_ALLOWED_DIRS",
        "ROOT_ALLOWED_FILES",
        "DADAIA_ROOT_FILES",
        "STATES_CANON",
        "zone_names",
    }
    return sorted((attrs | names) & sets) + (
        [] if "verdict" in attrs else ["no workspace_layout.verdict call"]
    )


_RULES: dict[str, Callable[[], list[str]]] = {
    "core-file-io-purity": _core_file_io,
    "session-store-owns-session-paths": _session_paths,
    "every-container-def-has-a-production-consumer": _orphan_factories,
    "doctor-modules-under-the-ceiling": _doctor_modules_over_ceiling,
    # sa-context-dead-removes-repos-outside-the-reaper#C8
    "no-rmtree-outside-the-create-rollback": _rmtree_sites,
    # sa-expiry-has-two-clocks#45.3
    "one-expiry-clock": _ttl_clocks,
    # sa-gate-path-classes-diverge-from-the-law#B39-6 (tables and producer)
    "path-class-tables-have-one-reader": _path_class_tables_read_elsewhere,
    "path-class-has-one-producer": _path_class_produced_elsewhere,
    "release-state-module-never-writes": _release_state_writes,
    # sa-context-repo-mapping-falls-back-to-the-name#B5
    "repos-path-comes-from-the-registry": _repos_path_from_a_context_name,
    # sa-specs-upgrade-writes-through-symlinks#B4
    "specs-writes-go-through-atomic-write": _raw_specs_writes,
    # sa-reaper-destroys-its-own-hold-before-ttl#B8
    "no-function-naming-the-reaped-zone-deletes": _reaped_zone_deleters,
    # sa-gate-allows-root-entries-the-reaper-moves#E9 (gate and doctor ask the one verdict)
    "root-whitelist-asks-the-one-verdict": lambda: _layout_sets_read_by("hooks/root_whitelist.py"),
    "doctor-asks-the-one-verdict": lambda: _layout_sets_read_by("features/spec_context/doctor.py"),
}


@pytest.mark.parametrize("rule", list(_RULES))
def test_each_question_has_one_owner(rule: str) -> None:
    offenders = _RULES[rule]()
    assert offenders == [], f"{rule}: {offenders}"


@pytest.mark.parametrize(
    "module",
    ["pre_gate", "sdd_gate", "sdd_post_gate", "ctx_inject", "root_whitelist", "venv_guard"],
)
def test_importing_a_hook_never_imports_the_container(module: str) -> None:
    """P-12: a hook is a one-shot process per write; the container costs ~2s to import."""
    code = f"import dadaia_workspace.hooks.{module}, sys; assert 'dadaia_workspace.container' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr


def test_gate_resolution_path_never_imports_the_container(tmp_path: Path) -> None:
    """P-12, the executed path: the gate's real entry judges a repo write (its BLOCK path:
    the worktree fix, `kind_holding`, `script_line`) with the container still unimported;
    the child carries the conftest pin, so it judges THIS checkout."""
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    (ws / "repos" / "demo").mkdir(parents=True)
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(ws / "repos" / "demo" / "f.py")},
    }
    code = (
        "import json, sys\nfrom dadaia_workspace.hooks import sdd_gate\n"
        f"sdd_gate.evaluate_payload(json.loads({json.dumps(payload)!r}))\n"
        "assert 'dadaia_workspace.container' not in sys.modules\n"
    )
    env = {k: os.environ[k] for k in ("PYTHONPATH", "DADAIA_FENCED_ROOTS")} | {
        "PATH": "/usr/bin:/bin"
    }
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120, cwd=ws, env=env
    )
    assert result.returncode == 0, result.stderr


def test_harness_dirs_derive_from_the_one_harness_registry() -> None:
    """0.4.7 FR3: HARNESS_DIRS is `.agents` plus HARNESS_PROJECTION_DIRS; kimi-code owns none."""
    from dadaia_workspace.core import harness_registry, workspace_layout

    assert harness_registry.HARNESS_PROJECTION_DIRS["kimi-code"] == ()
    derived = {".agents"} | {
        d for ds in harness_registry.HARNESS_PROJECTION_DIRS.values() for d in ds
    }
    assert derived == workspace_layout.HARNESS_DIRS
    assert ".kimi-code" not in workspace_layout.HARNESS_DIRS


def test_gate_additive_prefixes_are_the_registry_view() -> None:
    """0.4.6 FR1: the gate's `.dadaia/` ADDITIVE class is the registry's OUTPUT + EPHEMERAL rows."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import gate_policy

    assert workspace_layout.additive_prefixes() == gate_policy._ADDITIVE_DADAIA_PREFIXES
    assert not hasattr(gate_policy, "_SPECS_ADDITIVE_PREFIXES")


def _behavior(behavior_id: str) -> dict[str, str]:
    behaviors = json.loads(_REGISTRY.read_text(encoding="utf-8"))["behaviors"]
    return next(b["implementations"] for b in behaviors if b["id"] == behavior_id)  # type: ignore[no-any-return]


def test_each_harness_carries_the_cache_env_or_declares_the_gap(tmp_path: Path) -> None:
    """sa-tool-caches-land-outside-the-cache-zone#B40-2: Claude and Codex export the same
    absolute env; kimi-code, cursor, devin and copilot declare a gap — never silence."""
    tmp = Path("/ws/.dadaia/tmp")  # native separators (a backslash path on Windows)
    ruff, mypy = str(tmp / "ruff-cache"), str(tmp / "mypy-cache")
    env = merge_claude_settings(None, Path("/ws"))["env"]
    assert (env["MYPY_CACHE_DIR"], env["RUFF_CACHE_DIR"]) == (mypy, ruff)
    codex = codex_config(tmp_path / "agentic", Path("/ws"))
    assert (
        f"[shell_environment_policy.set]\nMYPY_CACHE_DIR = '{mypy}'\nRUFF_CACHE_DIR = '{ruff}'\n"
        in codex
    )
    answer = _behavior("tool-cache-env")
    assert sorted(answer) == sorted(L1_ENTRY_HARNESSES)
    assert sorted(h for h, t in answer.items() if t.startswith("gap:")) == [
        "copilot",
        "cursor",
        "devin",
        "kimi-code",
    ]


def test_b7_the_registry_states_what_each_rendered_gate_is() -> None:
    """sa-gate-blind-on-cursor-copilot-devin#B7: each harness's sdd-gate claim names every
    pre-gate event its rendered hook file registers, and says "gate not enforced" exactly
    when its dialect declares an ungated action."""
    claims = _behavior("sdd-gate")
    for name, record in HARNESS_RECORDS.items():
        dialect = HOOK_DIALECTS[record.hooks]
        for event in {e for f in dialect.files for e, lane, _ in f.events if lane == "pre-gate"}:
            assert event in claims[name], (name, event)
        assert ("gate not enforced" in claims[name]) is bool(dialect.ungated), name
