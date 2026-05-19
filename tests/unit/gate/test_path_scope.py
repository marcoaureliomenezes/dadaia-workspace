"""Unit tests for the path-scope check (RULE D) in sdd-spec-gate.sh.

Covers T1–T9 from the architect ADR (2026-05-19T021310Z-path-scope-gate-pattern.html).
Tests invoke sdd-spec-gate.sh as a black-box subprocess with controlled stdin/env
and assert on stdout, returncode, and /tmp/sdd-gate.log (redirected via SDD_GATE_LOG).

Test seam requirements (from ADR §9):
- Subprocess invocation with WORKSPACE_ROOT pointing at a tmp tree.
- SDD_GATE_LOG env override to write log to a tmp file per test.
- Each test creates a minimal tmp workspace tree:
    dadaia_workspace/public/agents/<name>.md
    specs/releases/<rel>/TASKS.md (with [-] marker where needed)
    specs/releases/ACTIVE.md
    .dadaia/states/primary_context.json
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

import pytest

# Absolute path to the gate script (source of truth — not the installed projection)
_GATE = (
    Path(__file__).parent.parent.parent.parent
    / "dadaia_workspace"
    / "public"
    / "scripts"
    / "sdd-spec-gate.sh"
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_WRITE_ALLOWLIST_ENTRIES = {
    "code-reviewer": [".dadaia/reports/<ctx>/code-reviewer/**"],
    "software-engineer": [
        "dadaia_workspace/**",
        "tests/**",
        ".dadaia/reports/<ctx>/software-engineer/**",
    ],
    "product-engineer": [
        "specs/**",
        ".dadaia/reports/<ctx>/product-engineer/**",
    ],
}


def _make_agent_md(name: str, write_allowlist: list[str] | None = None) -> str:
    """Return agent frontmatter markdown with optional paths block."""
    wl_yaml = ""
    if write_allowlist is not None:
        entries = "\n".join(f"    - {g}" for g in write_allowlist)
        wl_yaml = f"paths:\n  write_allowlist:\n{entries}\n"
    return (
        f"---\nname: {name}\ndescription: Test agent {name}.\n"
        f"{wl_yaml}---\n\n# {name.title()}\n"
    )


def _build_workspace(
    tmp_path: Path,
    agents: dict[str, list[str] | None] | None = None,
    active_phase: str = "TASKS",
    active_release: str = "test-release-v1",
    with_tasks_marker: bool = True,
    context_name: str = "dadaia-workspace",
) -> Path:
    """Create a minimal workspace tree under tmp_path and return the root."""
    # Agent files
    agents_dir = tmp_path / "dadaia_workspace" / "public" / "agents"
    agents_dir.mkdir(parents=True)
    for agent_name, wl in (agents or {}).items():
        (agents_dir / f"{agent_name}.md").write_text(
            _make_agent_md(agent_name, wl), encoding="utf-8"
        )

    # Specs / releases
    rel_dir = tmp_path / "specs" / "releases" / active_release
    rel_dir.mkdir(parents=True)

    # ACTIVE.md
    (tmp_path / "specs" / "releases" / "ACTIVE.md").write_text(
        f"release: {active_release}\nphase: {active_phase}\n", encoding="utf-8"
    )

    # TASKS.md with optional [-] marker
    tasks_content = (
        "# Tasks\n\n"
        "- [-] T001 — in-progress task (software-engineer)\n"
        if with_tasks_marker
        else "# Tasks\n\n- [ ] T001 — open task\n"
    )
    (rel_dir / "TASKS.md").write_text(tasks_content, encoding="utf-8")

    # primary_context.json
    state_dir = tmp_path / ".dadaia" / "states"
    state_dir.mkdir(parents=True)
    (state_dir / "primary_context.json").write_text(
        json.dumps(
            {
                "name": context_name,
                "repo_slug": context_name,
                "specs_dir": str(tmp_path / "specs"),
            }
        ),
        encoding="utf-8",
    )

    return tmp_path


def _run_gate(
    ws: Path,
    tool: str,
    file_path: str,
    env_overrides: dict[str, str] | None = None,
    payload_meta: dict[str, str] | None = None,
    log_path: Path | None = None,
) -> tuple[str, int, str]:
    """Run the gate and return (stdout, returncode, log_contents)."""
    if log_path is None:
        log_path = ws / "gate.log"

    payload: dict = {
        "tool_name": tool,
        "tool_input": {"file_path": file_path},
    }
    if payload_meta:
        payload["tool_input"]["_meta"] = payload_meta

    env = os.environ.copy()
    # Unset all persona vars by default for isolation
    for key in ["DADAIA_AGENT_PERSONA", "CLAUDE_AGENT_PERSONA",
                "CODEX_AGENT_PERSONA", "OPENCODE_AGENT_PERSONA",
                "DADAIA_CONTEXT", "SDD_LEGACY_FEATURES"]:
        env.pop(key, None)
    env["WORKSPACE_ROOT"] = str(ws)
    env["SDD_GATE_LOG"] = str(log_path)
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        ["bash", str(_GATE)],
        input=json.dumps(payload),
        env=env,
        capture_output=True,
        text=True,
    )
    log_contents = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    return result.stdout, result.returncode, log_contents


def _last_log_line(log_contents: str) -> str:
    """Return the last non-empty line of the log (after timestamp prefix)."""
    lines = [ln for ln in log_contents.splitlines() if ln.strip()]
    if not lines:
        return ""
    last = lines[-1]
    # Strip timestamp prefix: [<ISO>] sdd-gate: <rest>
    m = re.match(r"^\[.*?\]\s+sdd-gate:\s+(.*)", last)
    return m.group(1) if m else last


# ---------------------------------------------------------------------------
# T1 — Accept inside allowlist (priority-1 env var: DADAIA_AGENT_PERSONA)
# ---------------------------------------------------------------------------


def test_t1_accept_inside_allowlist_priority1_env(tmp_path: Path) -> None:
    """T1: DADAIA_AGENT_PERSONA=code-reviewer; write to code-reviewer's report dir.

    Expected: exit 0, no block JSON emitted, log line says 'allowed — path-scope ok'.
    """
    ws = _build_workspace(
        tmp_path,
        agents={"code-reviewer": [".dadaia/reports/dadaia-workspace/code-reviewer/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    target = str(ws / ".dadaia" / "reports" / "dadaia-workspace" / "code-reviewer" / "report.html")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
        log_path=log_path,
    )
    assert rc == 0
    assert "block" not in stdout
    # path-scope ok log line must appear
    assert "path-scope ok" in log, f"Expected 'path-scope ok' in log. Log:\n{log}"
    assert "persona=code-reviewer" in log


# ---------------------------------------------------------------------------
# T2 — Reject outside allowlist (priority-1 env) — exact error format
# ---------------------------------------------------------------------------


def test_t2_reject_outside_allowlist_exact_format(tmp_path: Path) -> None:
    """T2: code-reviewer tries to write to an agent file (outside its allowlist).

    Expected: exit 0 with block JSON containing exact PATH SCOPE ERROR string.
    """
    ws = _build_workspace(
        tmp_path,
        agents={"code-reviewer": [".dadaia/reports/<ctx>/code-reviewer/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    target = str(ws / "dadaia_workspace" / "public" / "agents" / "foo.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' in stdout
    assert "[PATH SCOPE ERROR]" in stdout
    assert "agent code-reviewer cannot write to" in stdout
    assert "write_allowlist:" in stdout
    # Verify it contains the agent and the path
    assert "code-reviewer" in stdout
    assert "foo.md" in stdout


# ---------------------------------------------------------------------------
# T3 — Fail-open when persona unset — log warning + allow
# ---------------------------------------------------------------------------


def test_t3_fail_open_no_persona_log_warning(tmp_path: Path) -> None:
    """T3: All persona env vars unset, no payload field — gate must fail open.

    Expected: exit 0, stdout is allow (or silent), log has FAIL-OPEN line with
    'no agent persona detected (env=unset payload=unset)'.
    """
    ws = _build_workspace(tmp_path)
    log_path = tmp_path / "gate.log"
    target = str(ws / "dadaia_workspace" / "public" / "agents" / "foo.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
    # Log must contain the FAIL-OPEN line
    assert "FAIL-OPEN path-scope: no agent persona detected" in log
    assert "env=unset" in log
    assert "payload=unset" in log
    assert f"tool=Write" in log


# ---------------------------------------------------------------------------
# T4 — Fail-open priority via harness-specific env (CLAUDE_AGENT_PERSONA)
# ---------------------------------------------------------------------------


def test_t4_harness_specific_env_claude(tmp_path: Path) -> None:
    """T4: DADAIA_AGENT_PERSONA unset; CLAUDE_AGENT_PERSONA=software-engineer.

    software-engineer's allowlist includes dadaia_workspace/**.
    Expected: exit 0, no block, log says allowed via path-scope ok.
    """
    ws = _build_workspace(
        tmp_path,
        agents={"software-engineer": ["dadaia_workspace/**", "tests/**",
                                       ".dadaia/reports/<ctx>/software-engineer/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    target = str(ws / "dadaia_workspace" / "public" / "agents" / "foo.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"CLAUDE_AGENT_PERSONA": "software-engineer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
    assert "allowed" in log or "path-scope ok" in log


def test_t4_harness_specific_env_codex(tmp_path: Path) -> None:
    """T4 variant: CODEX_AGENT_PERSONA used when DADAIA_ and CLAUDE_ are unset."""
    ws = _build_workspace(
        tmp_path,
        agents={"software-engineer": ["dadaia_workspace/**", "tests/**",
                                       ".dadaia/reports/<ctx>/software-engineer/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    target = str(ws / "dadaia_workspace" / "public" / "agents" / "foo.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"CODEX_AGENT_PERSONA": "software-engineer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout


def test_t4_harness_specific_env_opencode(tmp_path: Path) -> None:
    """T4 variant: OPENCODE_AGENT_PERSONA used when higher-priority vars are unset."""
    ws = _build_workspace(
        tmp_path,
        agents={"software-engineer": ["dadaia_workspace/**", "tests/**",
                                       ".dadaia/reports/<ctx>/software-engineer/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    target = str(ws / "dadaia_workspace" / "public" / "agents" / "foo.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"OPENCODE_AGENT_PERSONA": "software-engineer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout


def test_t4_dadaia_takes_priority_over_harness_specific(tmp_path: Path) -> None:
    """T4 invariant: DADAIA_AGENT_PERSONA takes priority over CLAUDE_AGENT_PERSONA."""
    ws = _build_workspace(
        tmp_path,
        agents={
            "code-reviewer": [".dadaia/reports/<ctx>/code-reviewer/**"],
            "software-engineer": ["dadaia_workspace/**", "tests/**",
                                   ".dadaia/reports/<ctx>/software-engineer/**"],
        },
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    # code-reviewer cannot write to dadaia_workspace/**
    target = str(ws / "dadaia_workspace" / "public" / "agents" / "foo.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={
            "DADAIA_AGENT_PERSONA": "code-reviewer",   # priority 1 wins
            "CLAUDE_AGENT_PERSONA": "software-engineer",  # would allow, but not picked
        },
        log_path=log_path,
    )
    assert rc == 0
    # code-reviewer blocks (DADAIA_ wins, not CLAUDE_)
    assert '"decision":"block"' in stdout
    assert "code-reviewer" in stdout


# ---------------------------------------------------------------------------
# T5 — Fail-open priority via JSON payload field
# ---------------------------------------------------------------------------


def test_t5_payload_field_used_when_env_unset(tmp_path: Path) -> None:
    """T5: All env vars unset; tool_input._meta.agent_persona = software-engineer.

    software-engineer can write to dadaia_workspace/**.
    Expected: exit 0, no block.
    """
    ws = _build_workspace(
        tmp_path,
        agents={"software-engineer": ["dadaia_workspace/**", "tests/**",
                                       ".dadaia/reports/<ctx>/software-engineer/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    target = str(ws / "dadaia_workspace" / "public" / "agents" / "foo.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        payload_meta={"agent_persona": "software-engineer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
    assert "FAIL-OPEN" not in log or "persona detected" not in log


# ---------------------------------------------------------------------------
# T6 — Agent file with no paths: block → fail-open
# ---------------------------------------------------------------------------


def test_t6_agent_file_missing_paths_block_fail_open(tmp_path: Path) -> None:
    """T6: Fixture agent has no 'paths:' in frontmatter → fail-open with warning.

    Expected: exit 0, allow, log warns 'has no paths block'.
    """
    ws = _build_workspace(
        tmp_path,
        agents={"fixture-broken": None},  # None → no write_allowlist in frontmatter
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    target = str(ws / "dadaia_workspace" / "public" / "agents" / "any_file.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "fixture-broken"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
    assert "FAIL-OPEN" in log
    assert "no paths block" in log or "has no paths block" in log


# ---------------------------------------------------------------------------
# T7 — Unknown persona (no agent file) → fail-open
# ---------------------------------------------------------------------------


def test_t7_unknown_persona_no_agent_file_fail_open(tmp_path: Path) -> None:
    """T7: DADAIA_AGENT_PERSONA=ghost-agent; no such agent file.

    Expected: exit 0, allow, log warns 'not in store'.
    """
    ws = _build_workspace(tmp_path)
    log_path = tmp_path / "gate.log"
    target = str(ws / "dadaia_workspace" / "public" / "agents" / "foo.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "ghost-agent"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
    assert "FAIL-OPEN" in log
    assert "ghost-agent" in log
    assert "not in store" in log


# ---------------------------------------------------------------------------
# T8 — Meta-edit passthrough still wins over path-scope
# ---------------------------------------------------------------------------


def test_t8_meta_edit_passthrough_before_path_scope(tmp_path: Path) -> None:
    """T8: code-reviewer writes to TASKS.md (not in allowlist) — step 5 allows first.

    Expected: exit 0, allowed via meta-edit (step 5 fires before step 6).
    The path-scope step must NOT fire on meta-edit paths.
    """
    ws = _build_workspace(
        tmp_path,
        agents={"code-reviewer": [".dadaia/reports/<ctx>/code-reviewer/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    # TASKS.md is a meta-edit path — must be allowed regardless of agent
    target = str(ws / "specs" / "releases" / "test-release-v1" / "TASKS.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
    # Log must show meta-edit allowed, NOT path-scope block
    assert "meta-edit on spec file" in log
    assert "PATH SCOPE ERROR" not in stdout
    assert "FAIL-OPEN" not in log.split("meta-edit")[1] if "meta-edit" in log else True


def test_t8_spec_md_meta_edit_passthrough(tmp_path: Path) -> None:
    """T8 variant: SPEC.md is also a meta-edit path."""
    ws = _build_workspace(
        tmp_path,
        agents={"code-reviewer": [".dadaia/reports/<ctx>/code-reviewer/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    target = str(ws / "specs" / "releases" / "test-release-v1" / "SPEC.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
    assert "meta-edit on spec file" in log


# ---------------------------------------------------------------------------
# T9 — Memory atomicity still wins over path-scope
# ---------------------------------------------------------------------------


def test_t9_memory_atomicity_wins_over_path_scope(tmp_path: Path) -> None:
    """T9: product-engineer (in allowlist) writes to specs/memory/architecture.html
    during TASKS phase — memory gate fires first (step 3 before step 6).

    Expected: exit 0 with block; reason starts with [SDD GATE] memory/.
    Path-scope does NOT bypass memory atomicity.
    """
    ws = _build_workspace(
        tmp_path,
        agents={"product-engineer": ["specs/**", ".dadaia/reports/<ctx>/product-engineer/**"]},
        active_phase="TASKS",  # Not CLOSURE — memory gate should fire
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    # Create the memory dir so path resolve works
    (ws / "specs" / "memory").mkdir(parents=True, exist_ok=True)
    target = str(ws / "specs" / "memory" / "architecture.html")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "product-engineer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' in stdout
    # The block reason must start with [SDD GATE] memory/ (step 3 fired)
    assert "[SDD GATE]" in stdout
    assert "memory" in stdout.lower()
    # PATH SCOPE ERROR must NOT appear (path-scope never reached)
    assert "[PATH SCOPE ERROR]" not in stdout


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


def test_non_write_tool_passes_through(tmp_path: Path) -> None:
    """Non-write tools (e.g. Read) are passed through without any gate checks."""
    ws = _build_workspace(tmp_path)
    log_path = tmp_path / "gate.log"

    stdout, rc, _ = _run_gate(
        ws,
        tool="Read",
        file_path=str(ws / "specs" / "releases" / "test-release-v1" / "TASKS.md"),
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout


def test_archive_path_blocked_before_path_scope(tmp_path: Path) -> None:
    """Archive paths are blocked by RULE B (step 4) before path-scope (step 6)."""
    ws = _build_workspace(
        tmp_path,
        agents={"software-engineer": ["specs/_archive/**", "dadaia_workspace/**",
                                       "tests/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    target = str(ws / "specs" / "_archive" / "old-feature" / "something.md")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "software-engineer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' in stdout
    assert "[SDD GATE]" in stdout
    # Archive error, not path-scope error
    assert "[PATH SCOPE ERROR]" not in stdout


def test_glob_double_star_matches_nested_paths(tmp_path: Path) -> None:
    """** in write_allowlist matches nested subdirectories."""
    ws = _build_workspace(
        tmp_path,
        agents={"software-engineer": ["dadaia_workspace/**", "tests/**",
                                       ".dadaia/reports/<ctx>/software-engineer/**"]},
        context_name="dadaia-workspace",
    )
    log_path = tmp_path / "gate.log"
    # Deeply nested path — should match dadaia_workspace/**
    target = str(ws / "dadaia_workspace" / "features" / "agents" / "deep" / "file.py")

    stdout, rc, log = _run_gate(
        ws,
        tool="Edit",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "software-engineer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
    assert "path-scope ok" in log


def test_glob_ctx_substitution_with_context_name(tmp_path: Path) -> None:
    """<ctx> in write_allowlist is substituted with PRIMARY_SLUG from context.json."""
    ws = _build_workspace(
        tmp_path,
        agents={"code-reviewer": [".dadaia/reports/<ctx>/code-reviewer/**"]},
        context_name="my-context",
    )
    log_path = tmp_path / "gate.log"
    # Path with the actual context name substituted
    target = str(ws / ".dadaia" / "reports" / "my-context" / "code-reviewer" / "r.html")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' not in stdout
    assert "path-scope ok" in log


def test_glob_ctx_substitution_wrong_context_blocked(tmp_path: Path) -> None:
    """<ctx> substitution: wrong context name in path → blocked."""
    ws = _build_workspace(
        tmp_path,
        agents={"code-reviewer": [".dadaia/reports/<ctx>/code-reviewer/**"]},
        context_name="my-context",
    )
    log_path = tmp_path / "gate.log"
    # Wrong context name in the path
    target = str(ws / ".dadaia" / "reports" / "other-context" / "code-reviewer" / "r.html")

    stdout, rc, log = _run_gate(
        ws,
        tool="Write",
        file_path=target,
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
        log_path=log_path,
    )
    assert rc == 0
    assert '"decision":"block"' in stdout
    assert "[PATH SCOPE ERROR]" in stdout


def test_empty_stdin_passes_through(tmp_path: Path) -> None:
    """Empty stdin causes gate to exit 0 silently (fail-open on empty payload)."""
    ws = _build_workspace(tmp_path)
    log_path = tmp_path / "gate.log"
    env = os.environ.copy()
    env["WORKSPACE_ROOT"] = str(ws)
    env["SDD_GATE_LOG"] = str(log_path)

    result = subprocess.run(
        ["bash", str(_GATE)],
        input="",
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert '"decision":"block"' not in result.stdout
