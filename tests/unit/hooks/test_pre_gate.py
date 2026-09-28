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
  carve-out. The harness-real no-``.dadaia/logs`` test (AC10, T-046-29) flows through
  ``run_hook_subprocess`` (the sanctioned subprocess channel).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.hooks import pre_gate
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
            lambda ws: ws / ".dadaia" / "sessions" / "a.json",
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
        # First header in-repo (allowed), second header PROTECTED
        # (.dadaia/sessions/) → blocked.
        (".dadaia/sessions/a.json", "+forge", "SEC-01"),
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

    monkeypatch.setattr(pre_gate, "_POLICIES", (rw, sdd))
    assert pre_gate.evaluate_payload({"tool_name": "Write"}) == "ROOT BLOCK"
    assert calls == ["rw"]

    def explode(_p: dict[str, object]) -> str | None:
        raise RuntimeError("boom")

    def allow(_p: dict[str, object]) -> str | None:
        return None

    monkeypatch.setattr(pre_gate, "_POLICIES", (explode, allow))
    # A policy that raises is treated as ALLOW — the entrypoint never deadlocks.
    assert pre_gate.evaluate_payload({"tool_name": "Write"}) is None


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
    monkeypatch.chdir(_mk_workspace(tmp_path))  # the session cwd, as the harness spawns it
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
    monkeypatch.chdir(_mk_workspace(tmp_path))  # the session cwd, as the harness spawns it
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
