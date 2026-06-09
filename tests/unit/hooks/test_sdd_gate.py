"""Unit + parity tests for dadaia_workspace.hooks.sdd_gate.

Mandatory rc-4 parity invariants tested here:
  (a) PATH-first context slug: a write under repos/B never acquires repos/A's lease.
  (b) Fail-open: any non-PROTECTED, non-live-foreign error -> ALLOW.
  (c) PROTECTED (.dadaia/sessions/) is the sole fail-CLOSED path.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import gate_policy
from dadaia_workspace.hooks import sdd_gate


def _mk_workspace(tmp_path: Path, *slugs: str) -> Path:
    """Build a minimal workspace with repos/<slug>/specs/releases/ACTIVE.md for each slug."""
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


def _run(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    *,
    capsys: pytest.CaptureFixture[str],
) -> str:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    rc = sdd_gate.main()
    assert rc == 0  # the gate signals block via stdout, always returns 0
    return capsys.readouterr().out


def test_non_write_tool_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(_mk_workspace(tmp_path, "a")))
    out = _run(monkeypatch, {"tool_name": "Read", "tool_input": {"file_path": "x"}}, capsys=capsys)
    assert out == ""


def test_unparseable_target_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(_mk_workspace(tmp_path, "a")))
    out = _run(monkeypatch, {"tool_name": "Write", "tool_input": {}}, capsys=capsys)
    assert out == ""


def test_ungated_path_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "README.md")}},
        capsys=capsys,
    )
    assert out == ""


def test_protected_sessions_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PARITY (c): .dadaia/sessions/ is the sole fail-CLOSED path — blocked unconditionally.
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    target = ws / ".dadaia" / "sessions" / "runtime" / "a.ptr"
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        capsys=capsys,
    )
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "SEC-01" in decision["reason"]


def test_path_first_context_slug_parity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PARITY (a): first-ALIVE is repos/A, but a write under repos/B MUST acquire repos/B's
    # lease, never repos/A's (fixes gate-cross-context-lock-contamination).
    ws = _mk_workspace(tmp_path, "A", "B")  # A is first-ALIVE
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    out = _run(
        monkeypatch,
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
            "session_id": "sess-1",
        },
        capsys=capsys,
    )
    assert out == ""  # acquired cleanly (no foreign conflict)
    # The lease record must be for context B, never A.
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    assert (lock_dir / "B.lock.json").exists()
    assert not (lock_dir / "A.lock.json").exists()


def test_mutating_no_context_fails_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A specs/releases/ path with no repo slug + no DADAIA_CONTEXT -> fail open (no lease).
    ws = _mk_workspace(tmp_path, "a")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    target = ws / "specs" / "releases" / "x" / "TASKS.md"
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        capsys=capsys,
    )
    assert out == ""


def test_fail_open_on_lease_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # PARITY (b): any non-LockHeldError from the lease subsystem -> ALLOW (fail-open).
    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("lease subsystem exploded")

    monkeypatch.setattr(gate_policy.lease, "acquire", boom)
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "s"},
        capsys=capsys,
    )
    assert out == ""  # fail open despite the lease error


def test_live_foreign_lease_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A genuine live-foreign LockHeldError -> BLOCK with the informative yield message.
    from dadaia_workspace.core.exceptions import LockHeldError

    ws = _mk_workspace(tmp_path, "B")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)

    def held(*_a: object, **_k: object) -> None:
        raise LockHeldError("context 'B' is held by another live session")

    monkeypatch.setattr(gate_policy.lease, "acquire", held)
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": "s"},
        capsys=capsys,
    )
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "another live session" in decision["reason"]
