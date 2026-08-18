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

from dadaia_workspace.hooks import _common, pre_gate, root_whitelist, sdd_gate
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


def test_latency_log_rotates_at_the_shared_cap(tmp_path: Path) -> None:
    """FR27/A27.1 — ``_append_latency`` funnels through the shared rotation helper, so
    ``hook-latency.jsonl`` rotates exactly like every other ``.dadaia/logs/*.jsonl``
    writer once it crosses the cap. Driven in-process (no subprocess) against the
    production function directly — the shared helper's own cap-crossing/retention
    behavior is proven once in ``tests/unit/infrastructure/test_jsonl_log_rotation.py``;
    this test only proves THIS writer is actually wired through it.
    """
    log = tmp_path / ".dadaia" / "logs" / "hook-latency.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text('{"seed": true}\n', encoding="utf-8")

    import dadaia_workspace.infrastructure.jsonl_log_rotation as rotation

    original_cap = rotation.LOG_ROTATION_MAX_BYTES
    rotation.LOG_ROTATION_MAX_BYTES = 8
    try:
        pre_gate._append_latency(tmp_path, "PreToolUse", 1.5)  # noqa: SLF001
    finally:
        rotation.LOG_ROTATION_MAX_BYTES = original_cap

    rotated = log.with_name(log.name + ".1")
    assert rotated.exists()
    assert json.loads(rotated.read_text(encoding="utf-8").strip()) == {"seed": True}
    new_rec = json.loads(log.read_text(encoding="utf-8").strip())
    assert new_rec["hook"] == "pre_gate"
    assert new_rec["event"] == "PreToolUse"


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


# --------------------------------------------------------------------------- #


def test_main_emits_explicit_allow_envelope(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Bug pre-gate-allow-envelope-fails-claude-schema: allow must validate silently.

    Claude Code's PreToolUse output schema restricts the top-level ``decision`` enum to
    ``["approve", "block"]`` — ``"allow"`` is invalid and makes the harness reject the
    WHOLE envelope ("Hook JSON output validation failed") on every allowed call. And
    ``permissionDecision: "defer"`` is print-mode only: interactive sessions log a warn
    and ignore it. The contract-valid allow envelope therefore carries NO permission
    verdict at all — the gate steps aside into the normal permission flow. It stays
    non-empty (observable-allow doctrine, bug projected-pre-gate-silent-allow); codex
    and the kimi shim treat any non-block envelope as allow.
    """
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": "repos/valproj/specs/bugs/x.md", "content": "x"},
    }
    monkeypatch.setattr(pre_gate._common, "read_stdin_json", lambda: payload)

    assert pre_gate.main() == 0
    out = capsys.readouterr().out.strip()
    envelope = json.loads(out.splitlines()[-1])
    assert envelope == {
        "continue": True,
        "hookSpecificOutput": {"hookEventName": "PreToolUse"},
    }
    assert "decision" not in envelope
    assert "permissionDecision" not in envelope["hookSpecificOutput"]
    assert "defer" not in out


def test_allow_envelope_has_no_kimi_block_marker(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The kimi shim greps the literal ``"decision": "block"`` — allow must not carry it."""
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": "repos/valproj/specs/bugs/x.md", "content": "x"},
    }
    monkeypatch.setattr(pre_gate._common, "read_stdin_json", lambda: payload)

    assert pre_gate.main() == 0
    raw = capsys.readouterr().out.strip().splitlines()[-1]
    assert '"decision": "block"' not in raw


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


# --------------------------------------------------------------------------- #
# Wiring ratchets — every PreToolUse policy must be reachable through the SHIPPED
# entrypoint, and the block must carry the verdict Claude Code actually reads.
# --------------------------------------------------------------------------- #


def test_bash_venv_guard_blocks_through_the_shipped_entrypoint(tmp_path: Path) -> None:
    """``Bash`` is in the PreToolUse matcher and ``venv_guard`` is its ONLY policy.

    Every venv-guard case called ``venv_guard.evaluate_payload`` directly, so the policy
    could be unwired from ``pre_gate._POLICIES`` — or deleted outright — while the whole
    hook suite stayed green (proven by mutation: neutering the policy left 141/141
    passing). This drives the real ``python -m dadaia_workspace.hooks.pre_gate`` with a
    ``Bash`` payload that MUST block, so the Bash arm of the matcher is pinned end to end.
    """
    env = claude_hook_env(tmp_path)
    result = run_hook_subprocess(
        "pre_gate",
        {"tool_name": "Bash", "tool_input": {"command": "pip install requests"}},
        env,
    )
    assert result.returncode == 0, result.stderr
    envelope = result.block_envelope()
    assert envelope is not None, f"Bash venv-guard did not block: {result.stdout!r}"
    reason = str(envelope.get("reason", ""))
    assert "VENV GUARD" in reason.upper(), reason
    # The corrected command must ride the block — a gate that names no remedy is a toll.
    assert ".dadaia/.venv/bin" in reason, reason


def test_pre_gate_stdout_is_exactly_one_json_object(tmp_path: Path) -> None:
    """Whole stdout must parse as ONE object — for allow AND for block.

    The envelope assertions parsed ``stdout.splitlines()[-1]``, which tolerates anything
    printed before the JSON. Claude Code parses the stream, so a stray ``print`` upstream
    of the envelope corrupts the verdict. Assert on the WHOLE stdout instead.
    """
    env = claude_hook_env(tmp_path)
    for payload in (
        {"tool_name": "Read", "tool_input": {"file_path": "x"}},
        {"tool_name": "Bash", "tool_input": {"command": "pip install requests"}},
    ):
        result = run_hook_subprocess("pre_gate", payload, env)
        raw = result.stdout.strip()
        assert raw, f"the gate must always emit an observable envelope: {payload}"
        parsed = json.loads(raw)  # raises on any pollution before/after the object
        assert isinstance(parsed, dict), parsed


def test_policies_tuple_is_the_wired_composition() -> None:
    """The real ``_POLICIES`` membership and ORDER — first-block-wins is documented law.

    The existing short-circuit test installs its own fake tuple and asserts its own string
    back, so it proves the ``for`` loop stops early and nothing about which policies are
    actually wired. This pins the shipped composition.
    """
    assert (  # noqa: SLF001
        root_whitelist.evaluate_payload,
        pre_gate._venv_guard_reason,  # noqa: SLF001
        sdd_gate.evaluate_payload_with_advisory,
    ) == pre_gate._POLICIES
