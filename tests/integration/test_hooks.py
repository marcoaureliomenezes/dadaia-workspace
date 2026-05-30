"""Subprocess tests for shell hooks: ctx-inject.sh + sdd-spec-gate.sh."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_PKG_SCRIPTS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "scripts"
CTX_INJECT = _PKG_SCRIPTS / "ctx-inject.sh"
SDD_GATE = _PKG_SCRIPTS / "sdd-spec-gate.sh"


def _install_scripts(workspace: Path) -> Path:
    """Copy the hooks to <workspace>/.dadaia/scripts/ where they expect to live."""
    target = workspace / ".dadaia" / "scripts"
    target.mkdir(parents=True, exist_ok=True)
    for src in (CTX_INJECT, SDD_GATE):
        shutil.copy2(src, target / src.name)
        (target / src.name).chmod(0o755)
    return target


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "ws"


def test_ctx_inject_reports_none_when_no_primary(workspace: Path) -> None:
    scripts = _install_scripts(workspace)
    result = subprocess.run(
        ["bash", str(scripts / "ctx-inject.sh")],
        capture_output=True,
        text=True,
        cwd="/tmp",
        timeout=5,
    )
    assert result.returncode == 0
    assert "[context: none]" in result.stdout


def test_ctx_inject_reports_active_context(workspace: Path) -> None:
    scripts = _install_scripts(workspace)
    (workspace / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (workspace / ".dadaia" / "states" / "primary_context.json").write_text(
        json.dumps({"name": "active-ctx", "repo_slug": "active-ctx", "specs_dir": "/x"})
    )
    result = subprocess.run(
        ["bash", str(scripts / "ctx-inject.sh")],
        capture_output=True,
        text=True,
        cwd="/tmp",
        timeout=5,
    )
    assert result.returncode == 0
    assert "[active-ctx]" in result.stdout


def test_ctx_inject_honors_dadaia_context_env(workspace: Path) -> None:
    scripts = _install_scripts(workspace)
    (workspace / "repos" / "envctx" / "specs").mkdir(parents=True)
    env = {**os.environ, "DADAIA_CONTEXT": "envctx"}
    result = subprocess.run(
        ["bash", str(scripts / "ctx-inject.sh")],
        capture_output=True,
        text=True,
        cwd="/tmp",
        env=env,
        timeout=5,
    )
    assert result.returncode == 0
    assert "[envctx]" in result.stdout


def test_sdd_gate_passes_for_non_production_paths(workspace: Path) -> None:
    scripts = _install_scripts(workspace)
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": str(workspace / "scratch.txt")}}
    )
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "decision" not in result.stdout  # not blocked


def test_sdd_gate_passes_when_tool_not_write(workspace: Path) -> None:
    scripts = _install_scripts(workspace)
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/anywhere"}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout == ""


# --- v2 gate: primary_slug scope + [-] granularity ---


def _make_primary_context(workspace: Path, slug: str, specs_dir: Path) -> None:
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "primary_context.json").write_text(
        json.dumps({"name": slug, "repo_slug": slug, "specs_dir": str(specs_dir)})
    )


def test_sdd_gate_v2_blocks_primary_slug_path_when_no_active_task(workspace: Path) -> None:
    """Gate blocks writes inside repos/<primary_slug>/ when no [-] task in specs."""
    scripts = _install_scripts(workspace)
    specs = workspace / "repos" / "my-proj" / "specs"
    specs.mkdir(parents=True)
    (specs / "TASKS.md").write_text("- [ ] T-001 — do something\n")
    _make_primary_context(workspace, "my-proj", specs)

    target_file = workspace / "repos" / "my-proj" / "src" / "main.py"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "SDD GATE" in data["reason"]


def test_sdd_gate_v2_passes_primary_slug_path_with_active_task(workspace: Path) -> None:
    """Gate allows writes inside repos/<primary_slug>/ when a [-] task is in active release."""
    scripts = _install_scripts(workspace)
    specs = workspace / "repos" / "my-proj" / "specs"
    # Create release-directory structure (root TASKS.md is no longer supported per T-8a)
    rel_dir = specs / "releases" / "my-release-v1"
    rel_dir.mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text(
        "release: my-release-v1\nphase: IMPLEMENTATION\n"
    )
    (rel_dir / "TASKS.md").write_text("- [-] T-001 — doing this now\n")
    _make_primary_context(workspace, "my-proj", specs)

    target_file = workspace / "repos" / "my-proj" / "src" / "main.py"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout == ""  # not blocked


def test_sdd_gate_fail_open_on_empty_stdin(workspace: Path) -> None:
    """Gate exits 0 and emits nothing when stdin is empty (fail-open)."""
    scripts = _install_scripts(workspace)
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input="",
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_sdd_gate_v2_allows_meta_edit_on_tasks_md(workspace: Path) -> None:
    """Gate allows writes to TASKS.md even with no [-] task (deadlock-prevention bypass)."""
    scripts = _install_scripts(workspace)
    specs = workspace / "repos" / "my-proj" / "specs"
    specs.mkdir(parents=True)
    tasks_path = specs / "TASKS.md"
    tasks_path.write_text("- [ ] T-001 — todo\n")
    _make_primary_context(workspace, "my-proj", specs)

    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(tasks_path)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout == ""  # not blocked


# --- T-8a: per-release gate tests (AC-T8a-3 and AC-T8a-4) ---


def test_gate_resolves_active_release_tasks(workspace: Path) -> None:
    """AC-T8a-3: Gate reads releases/ACTIVE.md -> releases/<id>/TASKS.md and allows
    when a [-] marker is present in the active release's TASKS.md.

    This test verifies the gate works correctly with the canonical release-directory
    structure (no root-level TASKS.md required).
    """
    scripts = _install_scripts(workspace)
    specs = workspace / "repos" / "my-proj" / "specs"
    rel_dir = specs / "releases" / "active-release-v1"
    rel_dir.mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text(
        "release: active-release-v1\nphase: IMPLEMENTATION\n"
    )
    (rel_dir / "TASKS.md").write_text(
        "# Tasks\n\n- [-] T-001 — work in progress\n- [ ] T-002 — pending\n"
    )
    _make_primary_context(workspace, "my-proj", specs)

    target_file = workspace / "repos" / "my-proj" / "src" / "service.py"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "WORKSPACE_ROOT": str(workspace)},
        timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout == ""  # not blocked: active release TASKS.md has [-] marker


def test_gate_blocks_when_active_release_has_no_task(workspace: Path) -> None:
    """AC-T8a-4: Gate blocks when ACTIVE.md points to a release whose TASKS.md
    has no [-] (IN PROGRESS) marker, and no other releases have one either.

    Confirms the root-level TASKS.md fallback is gone: a root TASKS.md with [-]
    does NOT satisfy the gate.
    """
    scripts = _install_scripts(workspace)
    specs = workspace / "repos" / "my-proj" / "specs"
    rel_dir = specs / "releases" / "active-release-v1"
    rel_dir.mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text(
        "release: active-release-v1\nphase: IMPLEMENTATION\n"
    )
    # All tasks open — no [-] marker
    (rel_dir / "TASKS.md").write_text(
        "# Tasks\n\n- [ ] T-001 — not started\n- [ ] T-002 — not started\n"
    )
    # Root-level TASKS.md with [-] marker must be ignored (T-8a removes this fallback)
    (specs / "TASKS.md").write_text("- [-] T-ROOT — this should be ignored\n")
    _make_primary_context(workspace, "my-proj", specs)

    target_file = workspace / "repos" / "my-proj" / "src" / "service.py"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "WORKSPACE_ROOT": str(workspace)},
        timeout=5,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "SDD GATE" in data["reason"]
