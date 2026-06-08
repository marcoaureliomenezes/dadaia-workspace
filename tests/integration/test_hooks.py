"""Subprocess tests for shell hooks: ctx-inject.sh + sdd-spec-gate.sh."""

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
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


def test_ctx_inject_silent_and_never_nags_when_no_context(workspace: Path) -> None:
    """No ALIVE context → ctx-inject stays silent. It must NEVER nag the operator to
    bind/rebind a context (that instruction was a flow-breaking bug and is deleted)."""
    scripts = _install_scripts(workspace)
    result = subprocess.run(
        ["bash", str(scripts / "ctx-inject.sh")],
        capture_output=True,
        text=True,
        cwd="/tmp",
        env={k: v for k, v in os.environ.items() if k != "DADAIA_CONTEXT"},
        timeout=5,
    )
    assert result.returncode == 0
    assert "context: none" not in result.stdout
    assert "context bind" not in result.stdout
    assert "--mode" not in result.stdout


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


def _bind_impl_session(
    workspace: Path, slug: str, release: str, session_id: str = "sess_impl"
) -> dict[str, str]:
    now = datetime.now(tz=UTC).isoformat()
    sessions = workspace / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / f"{session_id}.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "mode": "BOUND_IMPLEMENTATION",
                "context": slug,
                "release": release,
                "runtime": "codex",
                "pid": 123,
                "started_at": now,
                "last_seen_at": now,
                "ttl_seconds": 300,
            }
        )
    )
    locks = workspace / ".dadaia" / "locks" / "implementation"
    locks.mkdir(parents=True, exist_ok=True)
    (locks / f"{slug}__{release}.json").write_text(
        json.dumps(
            {
                "context": slug,
                "release": release,
                "session_id": session_id,
                "last_seen_at": now,
                "ttl_seconds": 300,
            }
        )
    )
    return {"DADAIA_SESSION_ID": session_id}


def test_sdd_gate_v2_passes_primary_slug_path_with_active_task(workspace: Path) -> None:
    """Gate allows production writes only with a bound implementation session."""
    scripts = _install_scripts(workspace)
    specs = workspace / "repos" / "my-proj" / "specs"
    # Create release-directory structure (root TASKS.md is no longer supported per T-8a)
    rel_dir = specs / "releases" / "my-release-v1"
    rel_dir.mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text("release: my-release-v1\nphase: IMPLEMENTATION\n")
    (rel_dir / "TASKS.md").write_text("- [-] T-001 — doing this now\n")
    _make_primary_context(workspace, "my-proj", specs)
    session_env = _bind_impl_session(workspace, "my-proj", "my-release-v1")

    target_file = workspace / "repos" / "my-proj" / "src" / "main.py"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "WORKSPACE_ROOT": str(workspace), **session_env},
        timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout == ""  # not blocked


def test_sdd_gate_parses_codex_apply_patch_command_path(workspace: Path) -> None:
    """Codex apply_patch provides patch text in tool_input.command; gate must parse it."""
    scripts = _install_scripts(workspace)
    specs = workspace / "repos" / "my-proj" / "specs"
    rel_dir = specs / "releases" / "my-release-v1"
    rel_dir.mkdir(parents=True)
    (specs / "releases" / "ACTIVE.md").write_text("release: my-release-v1\nphase: IMPLEMENTATION\n")
    (rel_dir / "TASKS.md").write_text("- [ ] T-001 — not started\n")
    _make_primary_context(workspace, "my-proj", specs)
    session_env = _bind_impl_session(workspace, "my-proj", "my-release-v1")

    # Target a FROZEN path: a successful apply_patch parse reaches RULE B and blocks,
    # which proves the gate parsed the patch's "Update File:" header.
    target = workspace / "repos" / "my-proj" / "specs" / "_archive" / "old.md"
    command = f"""*** Begin Patch
*** Update File: {target}
@@
+x = 1
*** End Patch
"""
    payload = json.dumps({"tool_name": "apply_patch", "tool_input": {"command": command}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "WORKSPACE_ROOT": str(workspace), **session_env},
        timeout=5,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "block"
    assert "_archive/ is read-only" in data["reason"]


def test_sdd_gate_allows_write_like_tool_without_parseable_path(workspace: Path) -> None:
    """v0.1.6 fail-safe: an unparseable target is ALLOWED (never deadlock on a parse miss)."""
    scripts = _install_scripts(workspace)
    payload = json.dumps({"tool_name": "apply_patch", "tool_input": {"command": "not a patch"}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "WORKSPACE_ROOT": str(workspace)},
        timeout=5,
    )

    assert result.returncode == 0
    assert result.stdout == ""


# ---------------------------------------------------------------------------
# T-HARD-01: spec_contexts.json fallback (DADAIA_CONTEXT unset, no
# primary_context.json) — gate must resolve PRIMARY_SPECS and enforce.
# ---------------------------------------------------------------------------


def test_sdd_gate_t_hard_01_spec_contexts_fallback_allows_when_active_task(
    workspace: Path,
) -> None:
    """T-HARD-01 (positive): DADAIA_CONTEXT unset, primary_context.json absent,
    valid spec_contexts.json with ALIVE entry → gate allows write inside repos/<slug>/
    when a [-] task IS active and the session owns the implementation lock.
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
    session_env = _bind_impl_session(workspace, slug, "v1")

    target_file = workspace / "repos" / slug / "src" / "service.py"
    env = {**os.environ, "WORKSPACE_ROOT": str(workspace), **session_env}
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
    workspace: Path,
    scripts: Path,
    *,
    fresh: bool = True,
    ctx: str = "",
    hook_output: str = "",
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
    if hook_output:
        env["DADAIA_HOOK_OUTPUT"] = hook_output
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


def test_ctx_inject_codex_json_output_is_parseable(workspace: Path) -> None:
    """Codex UserPromptSubmit output must be valid hook JSON, not JSON-like text."""
    scripts, memory_dir, _ = _make_full_context(workspace, "myctx")
    (memory_dir / "tech-stack.md").write_text("# tech-stack\n\njson mode content\n")
    (memory_dir / "product" / "catalog.json").write_text(
        json.dumps({"features": [{"slug": "json-mode"}]})
    )

    result = _run_ctx_inject(workspace, scripts, ctx="myctx", hook_output="codex-json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    hook_output = payload["hookSpecificOutput"]
    assert hook_output["hookEventName"] == "UserPromptSubmit"
    assert "json mode content" in hook_output["additionalContext"]
    assert "json-mode" in hook_output["additionalContext"]


def test_ctx_inject_codex_stdin_session_id_idempotent(workspace: Path) -> None:
    """T-016-C01: ctx-inject keys idempotence on the session_id Codex passes on stdin.

    Two consecutive invocations in the same logical session inject exactly once; the
    second produces NO output (not even a breadcrumb). The sentinel is keyed on the
    stable session_id, never the volatile shell PID ($$)."""
    scripts, memory_dir, _ = _make_full_context(workspace, "myctx")
    (memory_dir / "tech-stack.md").write_text("# tech\n\nbootstrap marker\n")
    env = {
        **os.environ,
        "WORKSPACE_ROOT": str(workspace),
        "DADAIA_CONTEXT": "myctx",
        "DADAIA_HOOK_OUTPUT": "codex-json",
    }
    # Strip harness session env vars so the stdin-session_id path is exercised
    # (env vars correctly take precedence over stdin when present).
    for _var in (
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "OPENCODE_SESSION_ID",
        "DADAIA_SESSION_ID",
    ):
        env.pop(_var, None)
    stdin_json = json.dumps({"session_id": "codex-sess-abc", "event": "startup"})
    sentinel_dir = workspace / ".dadaia" / "tmp"
    for f in sentinel_dir.glob("ctx-inject-fired-*"):
        f.unlink(missing_ok=True)

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(scripts / "ctx-inject.sh")],
            input=stdin_json,
            capture_output=True,
            text=True,
            cwd="/tmp",
            timeout=10,
            env=env,
        )

    first = _run()
    assert first.returncode == 0, first.stderr
    assert "bootstrap marker" in first.stdout, "first invocation must inject full context"
    # Sentinel keyed on the stdin session_id (not the PID).
    assert (sentinel_dir / "ctx-inject-fired-codex-sess-abc").exists()
    assert not list(sentinel_dir.glob("ctx-inject-fired-[0-9]*")), "no PID-keyed sentinel"

    second = _run()
    assert second.returncode == 0, second.stderr
    assert second.stdout.strip() == "", "second prompt must produce no output (no breadcrumb)"


def test_ctx_inject_opencode_session_guard(workspace: Path) -> None:
    """T-016-C02: OpenCode first message injects bootstrap; second appends nothing.
    Idempotence is keyed on OPENCODE_SESSION_ID."""
    scripts, memory_dir, _ = _make_full_context(workspace, "myctx")
    (memory_dir / "tech-stack.md").write_text("# tech\n\noc bootstrap\n")
    env = {
        **os.environ,
        "WORKSPACE_ROOT": str(workspace),
        "DADAIA_CONTEXT": "myctx",
        "OPENCODE_SESSION_ID": "oc-sess-1",
    }
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("CODEX_SESSION_ID", None)
    for f in (workspace / ".dadaia" / "tmp").glob("ctx-inject-fired-*"):
        f.unlink(missing_ok=True)

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(scripts / "ctx-inject.sh")],
            capture_output=True,
            text=True,
            cwd="/tmp",
            timeout=10,
            env=env,
        )

    first = _run()
    assert first.returncode == 0, first.stderr
    assert "oc bootstrap" in first.stdout
    assert (workspace / ".dadaia" / "tmp" / "ctx-inject-fired-oc-sess-1").exists()
    second = _run()
    assert second.returncode == 0, second.stderr
    assert second.stdout.strip() == ""


def test_ctx_inject_no_pid_fallback(workspace: Path) -> None:
    """T-016-C01: the $$ shell-PID fallback is removed from ctx-inject.sh."""
    src = CTX_INJECT.read_text()
    assert 'SESSION_ID="$$"' not in src
    assert "CODEX_SESSION_ID" in src, "session id must be resolvable from the Codex env var"


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
    when a [-] marker is present and the session owns the implementation lock.

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
    session_env = _bind_impl_session(workspace, "my-proj", "active-release-v1")

    target_file = workspace / "repos" / "my-proj" / "src" / "service.py"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(target_file)}})
    result = subprocess.run(
        ["bash", str(scripts / "sdd-spec-gate.sh")],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "WORKSPACE_ROOT": str(workspace), **session_env},
        timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout == ""  # not blocked: active release TASKS.md has [-] marker


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
    assert "class=ADDITIVE" in log_content, (
        f"Expected ADDITIVE classification. Log:\n{log_content!r}"
    )


def test_sdd_gate_rule_f_tmp_nested_subdir_exits_0(workspace: Path) -> None:
    """RULE F: deeply nested paths under .dadaia/tmp/ are also fast-allowed."""
    scripts = _install_scripts(workspace)
    tmp_target = workspace / ".dadaia" / "tmp" / "qa-engineer" / "2026" / "06" / "screenshot.png"
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
    session_env = _bind_impl_session(workspace, "my-proj", "my-release-v1")

    log_file = workspace / ".dadaia" / "sdd-gate.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "WORKSPACE_ROOT": str(workspace),
        "SDD_GATE_LOG": str(log_file),
        **session_env,
    }

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
