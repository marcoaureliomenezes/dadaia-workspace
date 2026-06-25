"""Tests for the merged PreToolUse entrypoint dadaia_workspace.hooks.pre_gate (T-014-03).

Two layers:

* **Parity (subprocess)** — the consolidated entrypoint, spawned as a real harness hook,
  reproduces the standalone SDD-gate and root-whitelist verdicts (ALLOW/BLOCK envelope)
  including the multi-file apply_patch most-restrictive rule, NotebookEdit handling, and
  the fail-CLOSED PROTECTED path.
* **Subprocess-free single-spawn contract (in-process)** — driving ``pre_gate.main()`` /
  ``evaluate_payload`` spawns NO child process and never execs: the entrypoint reads stdin
  once and dispatches to pure policy functions (the perf invariant, seed 5).
  ``subprocess.Popen``/``run`` and ``os.exec*`` are monkeypatched to raise. These in-process
  tests fault-inject ``_common.read_stdin_json`` (a production internal) to supply the
  payload — they never simulate ``sys.stdin``, so they stay on the contract's white-box
  carve-out. The harness-real latency-log behavior tests flow through
  ``run_hook_subprocess`` (the sanctioned subprocess channel).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.hooks import _common, pre_gate
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


def _mk_workspace(tmp_path: Path, *slugs: str) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": s, "state": "alive"} for s in slugs]}),
        encoding="utf-8",
    )
    for s in slugs:
        rel = tmp_path / "repos" / s / "specs" / "releases"
        rel.mkdir(parents=True)
        (rel / "ACTIVE.md").write_text("release: rel-1\nphase: IMPLEMENTATION\n", encoding="utf-8")
    return tmp_path


def _run(tmp_path: Path, payload: dict[str, Any], *, session_id: str = "claude-sess") -> Any:
    env = claude_hook_env(tmp_path, session_id=session_id)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    full_payload = {**payload, "session_id": session_id}
    result = run_hook_subprocess("pre_gate", full_payload, env)
    assert result.returncode == 0, result.stderr
    return result.block_envelope()


# --------------------------------------------------------------------------- #
# Parity: SDD-gate verdicts reproduced through pre_gate.
# --------------------------------------------------------------------------- #


def test_non_write_tool_allows(tmp_path: Path) -> None:
    _mk_workspace(tmp_path, "a")
    assert _run(tmp_path, {"tool_name": "Read", "tool_input": {"file_path": "x"}}) is None


def test_ungated_path_allows(tmp_path: Path) -> None:
    # An in-repo non-spec file is UNGATED by the SDD gate and is a subdir write (not a new
    # root entry), so both pre_gate policies allow it.
    ws = _mk_workspace(tmp_path, "a")
    target = ws / "repos" / "a" / "src" / "thing.py"
    block = _run(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(target)}})
    assert block is None


def test_protected_sessions_blocks_fail_closed(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path, "a")
    target = ws / ".dadaia" / "sessions" / "runtime" / "a.ptr"
    block = _run(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(target)}})
    assert block is not None
    assert "SEC-01" in block["reason"]


def test_apply_patch_multi_file_frozen_blocks_whole_patch(tmp_path: Path) -> None:
    # In-repo headers so root-whitelist passes and the SDD gate's FROZEN class fires on the
    # second header (the multi-file most-restrictive rule, FR-W4-04).
    _mk_workspace(tmp_path, "a")
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: repos/a/README.md\n"
        "+ok\n"
        "*** Update File: repos/a/specs/_archive/x.md\n"
        "+frozen\n"
        "*** End Patch"
    )
    block = _run(tmp_path, {"tool_name": "apply_patch", "tool_input": {"command": cmd}})
    assert block is not None
    assert "_archive" in block["reason"] or "FROZEN" in block["reason"].upper()


# --------------------------------------------------------------------------- #
# Parity: root-whitelist verdicts reproduced through pre_gate.
# --------------------------------------------------------------------------- #


def test_root_whitelist_forbidden_entry_blocks(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path, "a")
    block = _run(
        tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(ws / "junk.txt")}}
    )
    assert block is not None
    assert "ROOT WHITELIST GATE" in block["reason"]


def test_apply_patch_multi_file_protected_blocks_whole_patch(tmp_path: Path) -> None:
    # First header in-repo (allowed), second header PROTECTED (.dadaia/sessions/) → blocked.
    _mk_workspace(tmp_path, "a")
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: repos/a/README.md\n"
        "+ok\n"
        "*** Update File: .dadaia/sessions/runtime/a.ptr\n"
        "+forge\n"
        "*** End Patch"
    )
    block = _run(tmp_path, {"tool_name": "apply_patch", "tool_input": {"command": cmd}})
    assert block is not None
    assert "SEC-01" in block["reason"]


def test_notebook_edit_not_root_gated_but_sdd_gated(tmp_path: Path) -> None:
    # NotebookEdit is excluded from the root-whitelist tool set but IS an SDD write tool.
    # A NotebookEdit at root must NOT be blocked by root-whitelist (parity with standalone).
    ws = _mk_workspace(tmp_path, "a")
    block = _run(
        tmp_path,
        {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": str(ws / "junk.ipynb")}},
    )
    # README-sibling junk.ipynb at root is UNGATED by SDD and exempt from root-whitelist for
    # NotebookEdit → allowed.
    assert block is None


# --------------------------------------------------------------------------- #
# Subprocess-free single-spawn contract (seed 5).
# --------------------------------------------------------------------------- #


def _no_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("pre_gate must not spawn a subprocess / exec a child")

    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(subprocess, "run", boom)
    import os

    for name in ("execv", "execve", "execvp", "execvpe"):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, boom)


@pytest.mark.parametrize(
    "payload",
    [
        {"tool_name": "Edit", "tool_input": {"file_path": "/tmp/x.py"}},
        {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.py"}},
        {"tool_name": "MultiEdit", "tool_input": {"file_path": "/tmp/x.py"}},
        {"tool_name": "apply_patch", "tool_input": {"command": "*** Add File: a.py\n+x\n"}},
    ],
)
def test_main_is_subprocess_free(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, payload: dict[str, Any]
) -> None:
    _no_subprocess(monkeypatch)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    # Fault-inject the production stdin reader (NOT sys.stdin) so the entrypoint runs fully
    # in-process per the harness-env contract carve-out: reads the payload once, dispatches
    # to pure policy functions, returns 0 — no child spawned.
    monkeypatch.setattr(_common, "read_stdin_json", lambda: dict(payload))
    assert pre_gate.main() == 0


def test_evaluate_payload_first_block_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    # root-whitelist policy fires before the SDD gate: a forbidden-root block short-circuits
    # and the SDD policy is never consulted.
    calls: list[str] = []

    def rw(_p: dict[str, object]) -> str | None:
        calls.append("rw")
        return "ROOT BLOCK"

    def sdd(_p: dict[str, object]) -> str | None:
        calls.append("sdd")
        return "SDD BLOCK"

    monkeypatch.setattr(pre_gate, "_POLICIES", (rw, pre_gate._venv_guard_reason, sdd))
    assert pre_gate.evaluate_payload({"tool_name": "Write"}) == "ROOT BLOCK"
    assert calls == ["rw"]


def test_faulty_policy_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(_p: dict[str, object]) -> str | None:
        raise RuntimeError("boom")

    def allow(_p: dict[str, object]) -> str | None:
        return None

    monkeypatch.setattr(pre_gate, "_POLICIES", (explode, allow))
    # A policy that raises is treated as ALLOW — the entrypoint never deadlocks.
    assert pre_gate.evaluate_payload({"tool_name": "Write"}) is None


# --------------------------------------------------------------------------- #
# Hook-latency telemetry (FR-W4-06, T-014-04).
# --------------------------------------------------------------------------- #


def test_main_appends_one_latency_record(tmp_path: Path) -> None:
    # Harness-real path: spawn the hook as a real subprocess (no DADAIA_HOOK_EVENT override
    # → the latency record falls back to "PreToolUse").
    env = claude_hook_env(tmp_path)
    result = run_hook_subprocess(
        "pre_gate", {"tool_name": "Read", "tool_input": {"file_path": "x"}}, env
    )
    assert result.returncode == 0, result.stderr
    log = tmp_path / ".dadaia" / "logs" / "hook-latency.jsonl"
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["hook"] == "pre_gate"
    assert rec["event"] == "PreToolUse"
    assert isinstance(rec["duration_ms"], (int, float)) and rec["duration_ms"] >= 0
    assert "ts" in rec


def test_latency_event_from_env(tmp_path: Path) -> None:
    # DADAIA_HOOK_EVENT is a harness-control var (HARNESS_CONTROL_DADAIA_ENV): pass it through
    # the SUBPROCESS env via ``extra`` — the harness-real channel — never via an in-process
    # setenv (which the env contract forbids).
    env = claude_hook_env(tmp_path, extra={"DADAIA_HOOK_EVENT": "Bash"})
    result = run_hook_subprocess(
        "pre_gate", {"tool_name": "Bash", "tool_input": {"command": "ls"}}, env
    )
    assert result.returncode == 0, result.stderr
    log = tmp_path / ".dadaia" / "logs" / "hook-latency.jsonl"
    rec = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[0])
    assert rec["event"] == "Bash"


def test_telemetry_failure_does_not_change_verdict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # An unwritable logs path must not alter the gate verdict or the exit code (fail-open).
    # Fault-inject the production stdin reader (NOT sys.stdin) to stay in-process per the
    # contract carve-out.
    def boom(*_a: object, **_k: object) -> None:
        raise OSError("logs dir unwritable")

    monkeypatch.setattr(Path, "mkdir", boom)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"tool_name": "Read"})
    assert pre_gate.main() == 0  # no crash, verdict unaffected


def test_append_latency_no_workspace_is_noop(tmp_path: Path) -> None:
    # workspace=None (unresolvable) → no file written, no error.
    pre_gate._append_latency(None, "PreToolUse", 1.0)
    assert not (tmp_path / ".dadaia").exists()


# --------------------------------------------------------------------------- #
# WS-PI-4: the PI Layer-1 SDD-gate extension maps its tool names to the gate's
# canonical vocabulary (write→Write, edit→Edit) before delegating to pre_gate.
# These tests prove (a) why the mapping is necessary and (b) that the mapped
# names are enforced by the same gate the other harnesses use.
# --------------------------------------------------------------------------- #


def test_pi_raw_lowercase_write_name_is_not_a_write_tool(tmp_path: Path) -> None:
    # PI's built-in tool is named "write" (lowercase) — NOT in the gate's WRITE_TOOLS
    # vocabulary, so an unmapped payload would slip through. This is exactly why the
    # `.pi/extensions/dadaia-sdd-gate.ts` shim maps write→Write before calling pre_gate.
    assert _common.is_write_tool("write") is False
    assert _common.is_write_tool("edit") is False
    assert _common.is_write_tool("Write") is True
    assert _common.is_write_tool("Edit") is True


def test_pi_mapped_write_name_blocks_frozen_path(tmp_path: Path) -> None:
    # A PI write to a FROZEN archive path, sent with the mapped canonical name "Write"
    # (as the extension sends it), is BLOCKED by pre_gate — proving PI's Ring-1 extension
    # hits the real SDD gate.
    ws = _mk_workspace(tmp_path, "a")
    target = ws / "repos" / "a" / "specs" / "_archive" / "old.md"
    block = _run(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(target)}})
    assert block is not None
    assert "_archive" in block["reason"] or "FROZEN" in block["reason"].upper()


def test_pi_mapped_write_name_allows_additive_path(tmp_path: Path) -> None:
    # An ADDITIVE in-repo path (specs/bugs) sent with the mapped name "Write" is allowed —
    # the mapping does not over-block; only the path class decides.
    ws = _mk_workspace(tmp_path, "a")
    target = ws / "repos" / "a" / "specs" / "bugs" / "some-bug.md"
    block = _run(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(target)}})
    assert block is None
