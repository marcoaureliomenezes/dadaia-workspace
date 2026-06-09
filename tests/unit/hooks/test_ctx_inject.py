"""Unit + parity tests for dadaia_workspace.hooks.ctx_inject.

Mandatory parity: a second invocation in the same session emits nothing (the once-per-
session sentinel guards the ENTIRE payload; sentinel path byte-identical to the shell one).
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from dadaia_workspace.hooks import ctx_inject


def _ws(tmp_path: Path, slug: str = "ctx", *, with_memory: bool = True) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": slug, "state": "alive"}]}),
        encoding="utf-8",
    )
    specs = tmp_path / "repos" / slug / "specs"
    specs.mkdir(parents=True)
    if with_memory:
        mem = specs / "memory"
        mem.mkdir()
        (mem / "tech-stack.md").write_text("# tech\nPython 3.12\n", encoding="utf-8")
        (mem / "product").mkdir()
        (mem / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    return tmp_path


def _run(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    *,
    capsys: pytest.CaptureFixture[str],
) -> str:
    # Clear harness env vars so the test controls the session id via the stdin field.
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "OPENCODE_SESSION_ID",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert ctx_inject.main() == 0
    return capsys.readouterr().out


def test_first_injection_emits_context_and_memory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _ws(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_HOOK_OUTPUT", raising=False)
    out = _run(monkeypatch, {"session_id": "s1"}, capsys=capsys)
    assert "[ctx]" in out
    assert "dispatcher preflight" in out
    assert "tech-stack" in out or "Python 3.12" in out
    assert "end memory bootstrap" in out


def test_second_invocation_emits_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PARITY: the once-per-session sentinel suppresses the ENTIRE payload on re-invocation.
    ws = _ws(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    first = _run(monkeypatch, {"session_id": "same"}, capsys=capsys)
    assert first.strip()  # non-empty
    second = _run(monkeypatch, {"session_id": "same"}, capsys=capsys)
    assert second == ""  # nothing on the second call


def test_sentinel_path_byte_identical_to_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _ws(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    _run(monkeypatch, {"session_id": "abc123"}, capsys=capsys)
    expected = ws / ".dadaia" / "tmp" / "ctx-inject-fired-abc123"
    assert expected.exists()


def test_codex_json_envelope(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _ws(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("DADAIA_HOOK_OUTPUT", "codex-json")
    monkeypatch.setenv("DADAIA_HOOK_EVENT", "SessionStart")
    out = _run(monkeypatch, {"session_id": "s2"}, capsys=capsys)
    env = json.loads(out)
    assert env["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "[ctx]" in env["hookSpecificOutput"]["additionalContext"]


def test_json_output_default_event(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _ws(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("DADAIA_HOOK_OUTPUT", "json")
    monkeypatch.delenv("DADAIA_HOOK_EVENT", raising=False)
    out = _run(monkeypatch, {"session_id": "s3"}, capsys=capsys)
    env = json.loads(out)
    assert env["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_no_alive_context_emits_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": "x", "state": "dead"}]}), encoding="utf-8"
    )
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    monkeypatch.delenv("DADAIA_HOOK_OUTPUT", raising=False)
    out = _run(monkeypatch, {"session_id": "s"}, capsys=capsys)
    assert out == ""


def test_runtime_ptr_written(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _ws(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    _run(monkeypatch, {"session_id": "ptrsess"}, capsys=capsys)
    ptr = ws / ".dadaia" / "sessions" / "runtime" / "ptrsess.ptr"
    assert ptr.exists()
    assert ptr.read_text(encoding="utf-8") == "ptrsess"
