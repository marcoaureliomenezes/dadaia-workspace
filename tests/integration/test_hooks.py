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
    # v2: context is resolved via DADAIA_CONTEXT env var; create minimal specs dir
    # so the hook emits the context name rather than a "specs not found" warning.
    (workspace / "repos" / "active-ctx" / "specs").mkdir(parents=True)
    env = {**os.environ, "DADAIA_CONTEXT": "active-ctx", "WORKSPACE_ROOT": str(workspace)}
    result = subprocess.run(
        ["bash", str(scripts / "ctx-inject.sh")],
        capture_output=True,
        text=True,
        cwd="/tmp",
        timeout=5,
        env=env,
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
    """Write spec_contexts.json (v2) with the given slug as the sole ALIVE context.

    The legacy primary_context.json file is no longer read by the gate (T-HARD-01);
    the v2 resolution chain uses spec_contexts.json as step 2.
    """
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    ctx_data = {
        "schema_version": "2",
        "contexts": [
            {
                "name": slug,
                "state": "alive",
                "repo_slug": slug,
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00+00:00",
                "alive_since": "2026-01-01T00:00:00+00:00",
                "dead_since": None,
                "current_branch": "main",
            }
        ],
    }
    (states / "spec_contexts.json").write_text(json.dumps(ctx_data, indent=2))


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
    (specs / "releases" / "ACTIVE.md").write_text("release: my-release-v1\nphase: IMPLEMENTATION\n")
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


# ---------------------------------------------------------------------------
# T-HARD-01: spec_contexts.json fallback (DADAIA_CONTEXT unset, no
# primary_context.json) — gate must resolve PRIMARY_SPECS and enforce.
# ---------------------------------------------------------------------------


def test_sdd_gate_t_hard_01_spec_contexts_fallback_blocks_when_no_active_task(
    workspace: Path,
) -> None:
    """T-HARD-01: DADAIA_CONTEXT unset, primary_context.json absent, valid
    spec_contexts.json present → gate resolves PRIMARY_SLUG via step 2 and
    BLOCKS a write inside repos/<slug>/ when no [-] task exists.

    This is the critical scenario that was broken before T-HARD-01: the gate
    would silently exit 0 (fail-open / enforce nothing) because primary_context.json
    was absent. After the fix, step 2 of the resolution chain reads spec_contexts.json
    and finds the ALIVE context.
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    rel_dir = specs / "releases" / "v1"
    rel_dir.mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text("release: v1\nphase: IMPLEMENTATION\n")
    # Only an OPEN task — no [-] marker
    (rel_dir / "TASKS.md").write_text("- [ ] T-001 — not started\n")

    # Write spec_contexts.json (v2) with slug as the sole ALIVE entry.
    # DO NOT write primary_context.json — that file must NOT be present.
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    ctx_data = {
        "schema_version": "2",
        "contexts": [
            {
                "name": slug,
                "state": "alive",
                "repo_slug": slug,
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00+00:00",
                "alive_since": "2026-01-01T00:00:00+00:00",
                "dead_since": None,
                "current_branch": "main",
            }
        ],
    }
    (states / "spec_contexts.json").write_text(json.dumps(ctx_data, indent=2))
    assert not (states / "primary_context.json").exists(), "primary_context.json must be absent"

    target_file = workspace / "repos" / slug / "src" / "service.py"
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace)}
    # Explicitly unset DADAIA_CONTEXT to exercise step 2
    env.pop("DADAIA_CONTEXT", None)
    log_file = workspace / ".dadaia" / "sdd-gate.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env["SDD_GATE_LOG"] = str(log_file)

    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0, f"Gate crashed; stderr: {result.stderr!r}"
    # Gate must emit a block decision — NOT silently exit 0 (the old no-op bug)
    assert result.stdout.strip(), (
        "Gate emitted empty stdout (fail-open / no-op). "
        "Expected a BLOCK decision from step 2 of the resolution chain."
    )
    data = json.loads(result.stdout)
    assert data["decision"] == "block", (
        f"Expected block but got: {result.stdout!r}\nLog: {log_file.read_text()!r}"
    )
    assert "SDD GATE" in data["reason"], f"Block reason unexpected: {data['reason']!r}"

    # Verify the gate used step 2 (spec_contexts.json) in the log
    log_content = log_file.read_text() if log_file.exists() else ""
    assert "step2" in log_content or "spec_contexts" in log_content, (
        f"Expected step2/spec_contexts resolution in log.\nLog: {log_content!r}"
    )


def test_sdd_gate_t_hard_01_spec_contexts_fallback_allows_when_active_task(
    workspace: Path,
) -> None:
    """T-HARD-01 (positive): DADAIA_CONTEXT unset, primary_context.json absent,
    valid spec_contexts.json with ALIVE entry → gate allows write inside repos/<slug>/
    when a [-] task IS active.
    """
    scripts = _install_scripts(workspace)
    slug = "my-proj"
    specs = workspace / "repos" / slug / "specs"
    rel_dir = specs / "releases" / "v1"
    rel_dir.mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text("release: v1\nphase: IMPLEMENTATION\n")
    # Active [-] task
    (rel_dir / "TASKS.md").write_text("- [-] T-001 — in progress\n")

    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    ctx_data = {
        "schema_version": "2",
        "contexts": [
            {
                "name": slug,
                "state": "alive",
                "repo_slug": slug,
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00+00:00",
                "alive_since": "2026-01-01T00:00:00+00:00",
                "dead_since": None,
                "current_branch": "main",
            }
        ],
    }
    (states / "spec_contexts.json").write_text(json.dumps(ctx_data, indent=2))
    assert not (states / "primary_context.json").exists(), "primary_context.json must be absent"

    target_file = workspace / "repos" / slug / "src" / "service.py"
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace)}
    env.pop("DADAIA_CONTEXT", None)
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0, f"Gate crashed; stderr: {result.stderr!r}"
    assert result.stdout == "", f"Expected empty stdout (allow) but got: {result.stdout!r}"


# ---------------------------------------------------------------------------
# T-MMS-07: ctx-inject.sh reads .md files verbatim, no strip-memory-html.py
# ---------------------------------------------------------------------------


def _make_full_context(workspace: Path, slug: str) -> tuple[Path, Path, Path]:
    """Set up a minimal workspace with specs/memory/ tree under repos/<slug>/specs/.

    The v2 DADAIA_CONTEXT env-var branch resolves:
        SPECS_DIR = $WORKSPACE_ROOT/repos/$DADAIA_CONTEXT/specs

    so memory fixtures are placed under repos/<slug>/specs/memory/ — exactly
    where ctx-inject.sh will look when DADAIA_CONTEXT=<slug> is exported.

    Returns (scripts_dir, memory_dir, specs_dir) so callers can add fixtures.
    """
    scripts = _install_scripts(workspace)
    specs_dir = workspace / "repos" / slug / "specs"
    (specs_dir / "memory" / "product").mkdir(parents=True)
    return scripts, specs_dir / "memory", specs_dir


def _run_ctx_inject(
    workspace: Path, scripts: Path, *, fresh: bool = True, ctx: str = ""
) -> subprocess.CompletedProcess[str]:
    """Run ctx-inject.sh from the scripts dir, optionally purging the sentinel first.

    Pass *ctx* to inject DADAIA_CONTEXT=<ctx> into the subprocess environment so
    the v2 env-var branch fires (replacing the removed primary_context.json branch).
    """
    sentinel_dir = workspace / ".dadaia" / "tmp"
    if fresh:
        # Remove any sentinel so injection fires
        for f in sentinel_dir.glob("ctx-inject-fired-*"):
            f.unlink(missing_ok=True)
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace)}
    if ctx:
        env["DADAIA_CONTEXT"] = ctx
    return subprocess.run(
        ["bash", str(scripts / "ctx-inject.sh")],
        capture_output=True,
        text=True,
        cwd="/tmp",
        timeout=10,
        env=env,
    )


def test_ctx_inject_reads_tech_stack_md_verbatim(workspace: Path) -> None:
    """T-MMS-07: tech-stack.md is cat'd verbatim into the injection block (no strip pass)."""
    scripts, memory_dir, _ = _make_full_context(workspace, "myctx")
    tech_md = memory_dir / "tech-stack.md"
    tech_md.write_text("# tech-stack\n\nsome content here\n")

    result = _run_ctx_inject(workspace, scripts, ctx="myctx")

    assert result.returncode == 0, result.stderr
    assert "some content here" in result.stdout


def test_ctx_inject_does_not_call_strip_script(workspace: Path) -> None:
    """T-MMS-07: ctx-inject.sh must not reference or invoke strip-memory-html.py."""
    ctx_inject_src = CTX_INJECT.read_text()
    assert "strip-memory-html.py" not in ctx_inject_src, (
        "ctx-inject.sh still references strip-memory-html.py — must be removed"
    )
    assert "STRIP" not in ctx_inject_src, (
        "ctx-inject.sh still declares the STRIP variable — must be removed"
    )


def test_ctx_inject_no_tech_stack_html_reference(workspace: Path) -> None:
    """T-MMS-07: ctx-inject.sh must not reference tech-stack.html."""
    ctx_inject_src = CTX_INJECT.read_text()
    assert "tech-stack.html" not in ctx_inject_src, (
        "ctx-inject.sh still references tech-stack.html — must be repointed to tech-stack.md"
    )


def test_ctx_inject_catalog_json_preferred_over_index_md(workspace: Path) -> None:
    """T-MMS-07: when catalog.json exists it is used as-is; index.md is not read."""
    scripts, memory_dir, _ = _make_full_context(workspace, "myctx")
    (memory_dir / "tech-stack.md").write_text("# ts\n")
    catalog = {"features": [{"slug": "foo", "title": "Foo"}]}
    (memory_dir / "product" / "catalog.json").write_text(json.dumps(catalog))
    # index.md present but must NOT be emitted when catalog.json exists
    (memory_dir / "product" / "index.md").write_text("# index fallback — should NOT appear\n")

    result = _run_ctx_inject(workspace, scripts, ctx="myctx")

    assert result.returncode == 0, result.stderr
    assert "foo" in result.stdout
    assert "should NOT appear" not in result.stdout


def test_ctx_inject_falls_back_to_index_md_verbatim(workspace: Path) -> None:
    """T-MMS-07: when catalog.json is absent, product/index.md is cat'd verbatim."""
    scripts, memory_dir, _ = _make_full_context(workspace, "myctx")
    (memory_dir / "tech-stack.md").write_text("# ts\n")
    # No catalog.json; only index.md
    (memory_dir / "product" / "index.md").write_text("# Product Index\n\nfeature-alpha listed\n")

    result = _run_ctx_inject(workspace, scripts, ctx="myctx")

    assert result.returncode == 0, result.stderr
    assert "feature-alpha listed" in result.stdout


def test_ctx_inject_no_index_html_fallback(workspace: Path) -> None:
    """T-MMS-07: product/index.html fallback must no longer exist in the script."""
    ctx_inject_src = CTX_INJECT.read_text()
    assert "index.html" not in ctx_inject_src, (
        "ctx-inject.sh still references product/index.html — fallback must use index.md"
    )


def test_sdd_hooks_use_workspace_python() -> None:
    """SDD hooks must prefer .dadaia/.venv/bin/python over direct python3 calls."""
    for script in (SDD_GATE, _PKG_SCRIPTS / "sdd-post-gate.sh"):
        src = script.read_text(encoding="utf-8")
        assert 'PYTHON_BIN="${DADAIA_PYTHON:-$WS/.dadaia/.venv/bin/python}"' in src
        assert '"$PYTHON_BIN" -' in src
        assert "python3 -" not in src


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


# ---------------------------------------------------------------------------
# T-HARD-05: RULE F — .dadaia/tmp/ fast-allow
# ---------------------------------------------------------------------------


def test_sdd_gate_rule_f_tmp_path_exits_0(workspace: Path) -> None:
    """RULE F: a write whose target path is under .dadaia/tmp/ must exit 0
    immediately, regardless of any other gate state (no active task, no context).

    This makes the tmp-file-guardrail rule deterministic: even without a [-]
    task marker or a resolved primary context, tmp writes are never blocked.
    """
    scripts = _install_scripts(workspace)
    # No specs, no context, no tasks — conditions that would normally fail-open.
    # With RULE F the gate must exit 0 (allow) silently for tmp paths.
    tmp_target = (
        workspace / ".dadaia" / "tmp" / "software-engineer-python" / "20260603" / "output.json"
    )
    log_file = workspace / ".dadaia" / "sdd-gate.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace), "SDD_GATE_LOG": str(log_file)}

    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(tmp_target)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0, f"Gate crashed; stderr: {result.stderr!r}"
    assert result.stdout == "", f"Expected empty stdout (allow) but gate emitted: {result.stdout!r}"

    # Log must contain RULE F fast-allow message
    log_content = log_file.read_text() if log_file.exists() else ""
    assert "tmp path fast-allow" in log_content or "RULE F" in log_content, (
        f"Expected RULE F log message. Log:\n{log_content!r}"
    )


def test_sdd_gate_rule_f_tmp_nested_subdir_exits_0(workspace: Path) -> None:
    """RULE F: deeply nested paths under .dadaia/tmp/ are also fast-allowed."""
    scripts = _install_scripts(workspace)
    tmp_target = (
        workspace / ".dadaia" / "tmp" / "qa-engineer" / "2026" / "06" / "screenshot.png"
    )
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace)}

    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(tmp_target)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0
    assert result.stdout == "", f"Expected allow but got: {result.stdout!r}"


# ---------------------------------------------------------------------------
# T-HARD-05: one-[-]-per-owner WARN
# ---------------------------------------------------------------------------


def test_sdd_gate_one_minus_warn_two_markers_no_parallel_declaration(workspace: Path) -> None:
    """One-[-]-per-owner: when TASKS.md has 2+ [-] markers and no parallel_tasks:
    header, the gate must emit a WARN line to the gate log (but NOT block).
    """
    scripts = _install_scripts(workspace)
    specs = workspace / "repos" / "my-proj" / "specs"
    rel_dir = specs / "releases" / "my-release-v1"
    rel_dir.mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text("release: my-release-v1\nphase: IMPLEMENTATION\n")
    # Two simultaneous [-] markers, no parallel_tasks: declaration
    (rel_dir / "TASKS.md").write_text(
        "# Tasks\n\n"
        "- [-] T-001 — first in-progress task\n"
        "- [-] T-002 — second in-progress task\n"
        "- [ ] T-003 — open task\n"
    )
    _make_primary_context(workspace, "my-proj", specs)

    log_file = workspace / ".dadaia" / "sdd-gate.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace), "SDD_GATE_LOG": str(log_file)}

    # Write to a production path (repos/<slug>/) to reach RULE C
    target_file = workspace / "repos" / "my-proj" / "src" / "main.py"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    # Gate must ALLOW (two [-] markers do satisfy RULE C)
    assert result.returncode == 0, f"Gate crashed; stderr: {result.stderr!r}"
    assert result.stdout == "", f"Expected allow (warn-only) but got blocked: {result.stdout!r}"

    # WARN must be in the log
    log_content = log_file.read_text() if log_file.exists() else ""
    assert "WARN" in log_content and (
        "one-active-task" in log_content or "multiple [-]" in log_content
    ), (f"Expected WARN one-active-task in log. Log:\n{log_content!r}")
    # The count (2) must appear in the log message
    assert "2" in log_content, f"Expected count '2' in WARN log. Log:\n{log_content!r}"


def test_sdd_gate_one_minus_warn_suppressed_with_parallel_declaration(workspace: Path) -> None:
    """One-[-]-per-owner: when parallel_tasks: header is present, the WARN must
    be suppressed even if 2+ [-] markers exist.
    """
    scripts = _install_scripts(workspace)
    specs = workspace / "repos" / "my-proj" / "specs"
    rel_dir = specs / "releases" / "my-release-v1"
    rel_dir.mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text("release: my-release-v1\nphase: IMPLEMENTATION\n")
    # Two simultaneous [-] markers WITH parallel_tasks: declaration
    (rel_dir / "TASKS.md").write_text(
        "# Tasks\n\n"
        "parallel_tasks: T-001 || T-002 (disjoint write sets)\n\n"
        "- [-] T-001 — first in-progress task\n"
        "- [-] T-002 — second in-progress task\n"
    )
    _make_primary_context(workspace, "my-proj", specs)

    log_file = workspace / ".dadaia" / "sdd-gate.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace), "SDD_GATE_LOG": str(log_file)}

    target_file = workspace / "repos" / "my-proj" / "src" / "main.py"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0
    assert result.stdout == "", f"Expected allow but got: {result.stdout!r}"

    log_content = log_file.read_text() if log_file.exists() else ""
    # WARN must NOT appear when parallel_tasks: is declared
    assert "WARN one-active-task" not in log_content and "WARN: multiple [-]" not in log_content, (
        f"WARN should be suppressed with parallel_tasks declaration. Log:\n{log_content!r}"
    )
