"""Single-owner behaviours: hooks never import the container, harness directories derive from
the registry, the cache env is exported or its gap declared."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.infrastructure.runtime_config import codex_config, merge_claude_settings
from tests.fixtures.harness_env import suite_env

_REGISTRY = (
    Path(__file__).resolve().parents[2]
    / "dadaia_workspace"
    / "public"
    / "entities"
    / "registry.json"
)


@pytest.mark.parametrize(
    "module",
    ["pre_gate", "sdd_gate", "sdd_post_gate", "ctx_inject", "root_whitelist"],
)
def test_importing_a_hook_never_imports_the_container(module: str) -> None:
    """A hook is a one-shot process per write; the container costs ~2s to import."""
    code = f"import dadaia_workspace.hooks.{module}, sys; assert 'dadaia_workspace.container' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr


def test_gate_resolution_path_never_imports_the_container(tmp_path: Path) -> None:
    """The executed path: the gate's real entry judges a repo write (its BLOCK path:
    the worktree fix, `_worktree_names.locate`, `script_line`) with the container still unimported;
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
    env = suite_env(os.environ, Path.home()) | {
        k: os.environ[k] for k in ("PYTHONPATH", "DADAIA_FENCED_ROOTS")
    }
    env["PATH"] = "/usr/bin:/bin"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120, cwd=ws, env=env
    )
    assert result.returncode == 0, result.stderr


def test_harness_dirs_derive_from_the_one_harness_registry() -> None:
    """HARNESS_DIRS is `.agents` plus HARNESS_PROJECTION_DIRS; kimi-code owns none."""
    from dadaia_workspace.core import harness_registry, workspace_layout

    assert harness_registry.HARNESS_PROJECTION_DIRS["kimi-code"] == ()
    derived = {".agents"} | {
        d for ds in harness_registry.HARNESS_PROJECTION_DIRS.values() for d in ds
    }
    assert derived == workspace_layout.HARNESS_DIRS
    assert ".kimi-code" not in workspace_layout.HARNESS_DIRS


def test_gate_additive_prefixes_are_the_registry_view() -> None:
    """The gate's `.dadaia/` ADDITIVE class is the registry's OUTPUT + EPHEMERAL rows."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import gate_policy

    assert workspace_layout.additive_prefixes() == gate_policy._ADDITIVE_DADAIA_PREFIXES
    assert not hasattr(gate_policy, "_SPECS_ADDITIVE_PREFIXES")


def _gaps(behavior_id: str) -> dict[str, str]:
    behaviors = json.loads(_REGISTRY.read_text(encoding="utf-8"))["behaviors"]
    return next(b.get("gaps", {}) for b in behaviors if b["id"] == behavior_id)  # type: ignore[no-any-return]


def test_each_harness_carries_the_cache_env_or_declares_the_gap(tmp_path: Path) -> None:
    """Claude and Codex export the same
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
    assert sorted(_gaps("tool-cache-env")) == ["copilot", "cursor", "devin", "kimi-code"]
    assert {"claude", "codex"} | set(_gaps("tool-cache-env")) == set(HARNESS_RECORDS)
