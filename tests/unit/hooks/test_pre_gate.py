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
# Parity: SDD-gate + root-whitelist verdicts reproduced through pre_gate.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("tool_name", "input_key", "path_fn", "expect_reason"),
    [
        # An in-repo non-spec file is UNGATED by the SDD gate and is a subdir write (not a
        # new root entry), so both pre_gate policies allow it.
        (
            "Write",
            "file_path",
            lambda ws: ws / "repos" / "a" / "src" / "thing.py",
            None,
        ),
        # NotebookEdit is excluded from the root-whitelist tool set but IS an SDD write
        # tool. A README-sibling junk.ipynb at root is UNGATED by SDD and exempt from
        # root-whitelist for NotebookEdit → allowed (parity with standalone).
        ("NotebookEdit", "notebook_path", lambda ws: ws / "junk.ipynb", None),
        ("Read", "file_path", lambda ws: "x", None),
        (
            "Write",
            "file_path",
            lambda ws: ws / ".dadaia" / "sessions" / "runtime" / "a.ptr",
            "SEC-01",
        ),
        (
            "Write",
            "file_path",
            lambda ws: ws / "junk.txt",
            "ROOT WHITELIST GATE",
        ),
    ],
    ids=[
        "allow-parity-in-repo-subdir-write",
        "allow-parity-notebook-edit-root-exempt",
        "non-write-tool-allows",
        "protected-sessions-blocks-fail-closed",
        "root-whitelist-forbidden-entry-blocks",
    ],
)
def test_non_write_and_protected_matrix(
    tmp_path: Path, tool_name: str, input_key: str, path_fn: Any, expect_reason: str | None
) -> None:
    ws = _mk_workspace(tmp_path, "a")
    target = path_fn(ws)
    block = _run(tmp_path, {"tool_name": tool_name, "tool_input": {input_key: str(target)}})
    if expect_reason is None:
        assert block is None
    else:
        assert block is not None
        assert expect_reason in block["reason"]


@pytest.mark.parametrize(
    ("second_header", "second_body", "reason_fragment"),
    [
        # In-repo headers so root-whitelist passes and the SDD gate's FROZEN class fires
        # on the second header (the multi-file most-restrictive rule, FR-W4-04).
        ("repos/a/specs/_archive/x.md", "+frozen", "_archive"),
        # First header in-repo (allowed), second header PROTECTED
        # (.dadaia/sessions/) → blocked.
        (".dadaia/sessions/runtime/a.ptr", "+forge", "SEC-01"),
    ],
)
def test_apply_patch_multi_file_most_restrictive_blocks_whole_patch(
    tmp_path: Path, second_header: str, second_body: str, reason_fragment: str
) -> None:
    _mk_workspace(tmp_path, "a")
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: repos/a/README.md\n"
        "+ok\n"
        f"*** Update File: {second_header}\n"
        f"{second_body}\n"
        "*** End Patch"
    )
    block = _run(tmp_path, {"tool_name": "apply_patch", "tool_input": {"command": cmd}})
    assert block is not None
    assert reason_fragment in block["reason"] or reason_fragment.upper() in block["reason"].upper()


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


def test_evaluate_payload_first_block_wins_and_faulty_policy_fails_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


@pytest.mark.parametrize(
    ("extra_env", "tool_name", "tool_input", "expected_event"),
    [
        # Harness-real path: no DADAIA_HOOK_EVENT override → the latency record falls back
        # to "PreToolUse".
        (None, "Read", {"file_path": "x"}, "PreToolUse"),
        # DADAIA_HOOK_EVENT is a harness-control var (HARNESS_CONTROL_DADAIA_ENV): passed
        # through the SUBPROCESS env via ``extra`` — the harness-real channel — never via
        # an in-process setenv (which the env contract forbids).
        ({"DADAIA_HOOK_EVENT": "Bash"}, "Bash", {"command": "ls"}, "Bash"),
    ],
)
def test_main_appends_one_latency_record(
    tmp_path: Path,
    extra_env: dict[str, str] | None,
    tool_name: str,
    tool_input: dict[str, str],
    expected_event: str,
) -> None:
    env = claude_hook_env(tmp_path, extra=extra_env)
    result = run_hook_subprocess(
        "pre_gate", {"tool_name": tool_name, "tool_input": tool_input}, env
    )
    assert result.returncode == 0, result.stderr
    log = tmp_path / ".dadaia" / "logs" / "hook-latency.jsonl"
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["hook"] == "pre_gate"
    assert rec["event"] == expected_event
    assert isinstance(rec["duration_ms"], (int, float)) and rec["duration_ms"] >= 0
    assert "ts" in rec


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


# --------------------------------------------------------------------------- #
# WS-PI-4: the PI Layer-1 SDD-gate extension maps its tool names to the gate's
# canonical vocabulary (write→Write, edit→Edit) before delegating to pre_gate.
# These tests prove (a) why the mapping is necessary and (b) that the mapped
# names are enforced by the same gate the other harnesses use.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("rel_path", "expect_blocked", "reason_fragment"),
    [
        # A PI write to a FROZEN archive path, sent with the mapped canonical name "Write"
        # (as the extension sends it), is BLOCKED by pre_gate — proving PI's Ring-1
        # extension hits the real SDD gate.
        ("specs/_archive/old.md", True, "_archive"),
        # An ADDITIVE in-repo path (specs/bugs) sent with the mapped name "Write" is
        # allowed — the mapping does not over-block; only the path class decides.
        ("specs/bugs/some-bug.md", False, None),
    ],
)
def test_pi_mapped_write_name_hits_real_gate(
    tmp_path: Path, rel_path: str, expect_blocked: bool, reason_fragment: str | None
) -> None:
    # PI's built-in tool is named "write" (lowercase) — NOT in the gate's WRITE_TOOLS
    # vocabulary, so an unmapped payload would slip through. This is exactly why the
    # `.pi/extensions/dadaia-sdd-gate.ts` shim maps write→Write before calling pre_gate.
    assert _common.is_write_tool("write") is False
    assert _common.is_write_tool("edit") is False
    assert _common.is_write_tool("Write") is True
    assert _common.is_write_tool("Edit") is True

    ws = _mk_workspace(tmp_path, "a")
    target = ws / "repos" / "a" / rel_path
    block = _run(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(target)}})
    if expect_blocked:
        assert block is not None
        assert reason_fragment is not None
        assert (
            reason_fragment in block["reason"] or reason_fragment.upper() in block["reason"].upper()
        )
    else:
        assert block is None


# --------------------------------------------------------------------------- #
# v0.1.76 T-4 (FR5): PI presence parity — the shim now sends a stable, non-anon
# session_id on every tool_call payload; anon-session creates NO presence record.
# --------------------------------------------------------------------------- #


def _pi_shim_env(workspace: Path) -> dict[str, str]:
    """A raw process env matching what PI's `spawnSync` actually gives the hook child:
    no harness-native session var (PI exports none), no DADAIA_SESSION_ID override
    (nothing sets it), just WORKSPACE_ROOT — the true PI-shim invocation shape."""
    env = claude_hook_env(workspace, session_id="unused")
    for var in ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID", "DADAIA_CONTEXT"):
        env.pop(var, None)
    return env


def test_pi_shim_payload_with_session_id_creates_real_presence_record(tmp_path: Path) -> None:
    """FR5 fix: the current shim payload shape (session_id present) resolves a real,
    non-anon presence record — the CRITICAL-bug root cause (PI anon-session
    dual-writer) is closed."""
    ws = _mk_workspace(tmp_path, "a")
    target = ws / "repos" / "a" / "specs" / "releases" / "rel-1" / "TASKS.md"
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
        "session_id": "pi-session-11111111-2222-3333-4444-555555555555",
    }
    result = run_hook_subprocess("pre_gate", payload, _pi_shim_env(tmp_path))
    assert result.returncode == 0, result.stderr
    assert result.block_envelope() is None  # never blocks (doctrine)

    presence_dir = ws / ".dadaia" / "states" / "presence" / "a"
    records = list(presence_dir.glob("*.json")) if presence_dir.exists() else []
    sids = {p.stem for p in records}
    assert "pi-session-11111111-2222-3333-4444-555555555555" in sids
    assert "anon-session" not in sids


def test_pre_fix_payload_shape_with_no_session_id_documents_the_closed_bug(
    tmp_path: Path,
) -> None:
    """Documents the pre-fix bug: a payload with NO session_id field at all (the shape
    the shim sent before FR5) resolves to anon-session, which creates NO presence
    record at all (FR5's anon-session guard) — the write is still allowed (never
    blocked), but the session is invisible to presence. This is exactly the gap FR5's
    production fix closes by never omitting session_id from now on."""
    ws = _mk_workspace(tmp_path, "a")
    target = ws / "repos" / "a" / "specs" / "releases" / "rel-1" / "TASKS.md"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
    result = run_hook_subprocess("pre_gate", payload, _pi_shim_env(tmp_path))
    assert result.returncode == 0, result.stderr
    assert result.block_envelope() is None  # never blocks, even in the pre-fix shape

    presence_dir = ws / ".dadaia" / "states" / "presence" / "a"
    assert not presence_dir.exists() or list(presence_dir.glob("*.json")) == []


def test_main_emits_explicit_allow_envelope(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Bug claude-pre-gate-envelope-contract: allow must be Claude-Code contract-valid.

    Bug projected-pre-gate-silent-allow established the observable-allow doctrine (an
    allowed probe EMITS its decision). This pins the contract-valid shape: the top-level
    ``"decision": "allow"`` marker stays (recipe F-08 / codex / kimi observability — every
    non-Claude consumer treats a non-block envelope as allow), and the operative Claude
    Code field is ``hookSpecificOutput.permissionDecision: "defer"`` — the documented
    "run the normal permission flow" verdict (PreToolUse decision control).
    """
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": "repos/valproj/specs/bugs/x.md", "content": "x"},
    }
    monkeypatch.setattr(pre_gate._common, "read_stdin_json", lambda: payload)

    assert pre_gate.main() == 0
    out = capsys.readouterr().out.strip()
    assert json.loads(out.splitlines()[-1]) == {
        "decision": "allow",
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "defer",
        },
    }


def test_main_block_envelope_carries_claude_permission_deny(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Bug claude-pre-gate-envelope-contract: block must be Claude-Code contract-valid.

    The legacy ``"decision": "block"`` field rides an undocumented fallback in current
    Claude Code — the documented PreToolUse verdict is
    ``hookSpecificOutput.permissionDecision: "deny"``. The merged envelope carries BOTH
    (legacy for codex hooks + the kimi shim, modern for Claude Code) with one identical
    reason string.
    """
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": ".dadaia/sessions/x.json", "content": "x"},
    }
    monkeypatch.setattr(pre_gate._common, "read_stdin_json", lambda: payload)

    assert pre_gate.main() == 0
    envelope = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert envelope["decision"] == "block"
    assert envelope["reason"]
    hso = envelope["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert hso["permissionDecisionReason"] == envelope["reason"]


def test_block_envelope_raw_string_keeps_kimi_shim_markers(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The kimi pre-gate shim string-matches the raw stdout — its two anchors are law.

    The shim's ``case`` pattern greps the literal ``"decision": "block"`` and its ``sed``
    reason extraction (``.*"reason": "\\(.*\\)".*``) captures cleanly only when the
    top-level ``reason`` is the LAST key in the envelope. Both anchors must survive the
    Claude-contract merge byte-exactly.
    """
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": ".dadaia/sessions/x.json", "content": "x"},
    }
    monkeypatch.setattr(pre_gate._common, "read_stdin_json", lambda: payload)

    assert pre_gate.main() == 0
    raw = capsys.readouterr().out.strip().splitlines()[-1]
    assert '"decision": "block"' in raw
    assert raw.index('"hookSpecificOutput"') < raw.index('"reason": "'), (
        "top-level reason must stay the LAST key so the kimi sed capture stays clean"
    )
