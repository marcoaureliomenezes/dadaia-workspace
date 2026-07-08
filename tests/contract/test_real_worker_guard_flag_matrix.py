"""T-67-09 (SPEC v0.1.67 FR3, AC3.3 per-flag matrix) — real-binary guard non-interference.

The autouse ``_real_worker_guard`` fixture (``tests/conftest.py``) fails loud with
``RuntimeError`` unless one of FOUR established live-opt-in flags is set:
``DADAIA_E2E_REAL_WORKER``, ``DADAIA_PI_LIVE``, ``DADAIA_CODEX_LIVE``,
``DADAIA_CLAUDE_LIVE``. T-67-08 structurally proves the guard fires when NONE of the
four are set. This module proves the inverse — each flag set INDIVIDUALLY must make
the guard stay quiet — with a distinct, explicit, NAMED assertion per flag (architect
finding F1's specific requirement: the ``DADAIA_CODEX_LIVE`` case must never be
inferred from a ``DADAIA_E2E_REAL_WORKER``/``DADAIA_PI_LIVE`` run — a single-flag
guard design would silently false-block a legitimate ``DADAIA_CODEX_LIVE=1`` run of
``tests/integration/codex_live/``).

**Fixture-ordering note.** ``_real_worker_guard`` is ``autouse=True``, so it ALWAYS
evaluates before any explicitly-requested fixture or the test body itself (pytest
autouse-before-explicit ordering, same scope) — setting the flag via
``monkeypatch.setenv`` inside the test BODY would run too late to influence the
guard's own setup-time ``_real_worker_opt_in()`` check. Each flag is therefore set via
a small parametrized FIXTURE (``_live_flag``) requested by the test, which pytest
resolves as part of fixture setup — same phase as the autouse guard, in file
declaration order, so the flag lands in ``os.environ`` before the guard reads it.

**Hermeticity (never spawns a real binary to completion):** each case constructs the
adapter with NO ``runner=`` and ``timeout_seconds=1`` and calls ``.run()``. If the
guard incorrectly fired, it would raise ``RuntimeError`` — the assertion this module
checks does NOT happen. If the guard correctly stays quiet, the call falls through to
the real, module-qualified ``subprocess.run`` — which, absent the ``pi``/``codex``
binary's expected environment, either errors quickly or is bounded by the 1-second
timeout (mapped internally to a FAILED ``AgentRunResult``, never a raised exception) —
so no case in this module can hang or spend operator credits, regardless of local
binary/auth availability.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter, CodexExecConfig
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig

_GUARD_MESSAGE = "real pi/codex binary invocation attempted"


def _pi_request() -> object:
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunRequest,
        AgentRuntimeKind,
        GateEvidenceKind,
    )

    return AgentRunRequest(
        role="software-engineer",
        prompt="probe",
        runtime=AgentRuntimeKind.PI_HEADLESS,
        context="dadaia-workspace",
        release_id="v0.1.67",
        task_id="T-67-09",
        allowed_paths=("src/**",),
        forbidden_paths=("secrets/**",),
        expected_schema="agent-run-result-v1",
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def _codex_request() -> object:
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunRequest,
        AgentRuntimeKind,
        GateEvidenceKind,
    )

    return AgentRunRequest(
        role="software-engineer",
        prompt="probe",
        runtime=AgentRuntimeKind.CODEX_EXEC,
        context="dadaia-workspace",
        release_id="v0.1.67",
        task_id="T-67-09",
        allowed_paths=("src/**",),
        forbidden_paths=("secrets/**",),
        expected_schema="agent-run-result-v1",
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def _assert_guard_quiet(run: object) -> None:
    """Invoke a zero-arg callable; fail only if the GUARD's own RuntimeError fires."""
    assert callable(run)
    try:
        run()
    except RuntimeError as exc:
        if _GUARD_MESSAGE in str(exc):
            pytest.fail(f"guard fired despite the live-opt-in flag being set: {exc}")
        raise


@pytest.fixture
def e2e_real_worker_flag(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Sets `DADAIA_E2E_REAL_WORKER=1` during fixture SETUP (before the autouse guard
    reads os.environ), not inside the test body."""
    monkeypatch.setenv("DADAIA_E2E_REAL_WORKER", "1")
    yield


@pytest.fixture
def pi_live_flag(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Sets `DADAIA_PI_LIVE=1` during fixture setup."""
    monkeypatch.setenv("DADAIA_PI_LIVE", "1")
    yield


@pytest.fixture
def codex_live_flag(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Sets `DADAIA_CODEX_LIVE=1` during fixture setup."""
    monkeypatch.setenv("DADAIA_CODEX_LIVE", "1")
    yield


@pytest.fixture
def claude_live_flag(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Sets `DADAIA_CLAUDE_LIVE=1` during fixture setup."""
    monkeypatch.setenv("DADAIA_CLAUDE_LIVE", "1")
    yield


def test_dadaia_e2e_real_worker_flag_keeps_pi_guard_quiet(
    tmp_path: Path, e2e_real_worker_flag: None
) -> None:
    """AC3.3: `DADAIA_E2E_REAL_WORKER=1` — the guard never fires for PiHeadlessAdapter."""
    adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path, timeout_seconds=1))
    _assert_guard_quiet(lambda: adapter.run(_pi_request()))  # type: ignore[arg-type]


def test_dadaia_pi_live_flag_keeps_pi_guard_quiet(tmp_path: Path, pi_live_flag: None) -> None:
    """AC3.3: `DADAIA_PI_LIVE=1` — the guard never fires for PiHeadlessAdapter."""
    adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path, timeout_seconds=1))
    _assert_guard_quiet(lambda: adapter.run(_pi_request()))  # type: ignore[arg-type]


def test_dadaia_codex_live_flag_keeps_codex_guard_quiet(
    tmp_path: Path, codex_live_flag: None
) -> None:
    """AC3.3 (F1's specific named requirement): `DADAIA_CODEX_LIVE=1` — the guard never
    fires for CodexExecAdapter. This is the exact regression the architect review's F1
    finding identified in the original single-flag guard design; it MUST be its own
    explicit assertion, never inferred from a `DADAIA_E2E_REAL_WORKER`/`DADAIA_PI_LIVE`
    run (a pi-flag pass proves nothing about the codex adapter's own guard branch)."""
    adapter = CodexExecAdapter(CodexExecConfig(cwd=tmp_path, timeout_seconds=1), environ={})
    _assert_guard_quiet(lambda: adapter.run(_codex_request()))  # type: ignore[arg-type]


def test_dadaia_claude_live_flag_keeps_pi_and_codex_guard_quiet(
    tmp_path: Path, claude_live_flag: None
) -> None:
    """AC3.3: `DADAIA_CLAUDE_LIVE=1` — the union predicate is flag-name-agnostic, so
    setting the claude_live flag ALSO keeps the pi/codex guard quiet (the predicate
    does not scope by which adapter is being constructed, only whether ANY of the 4
    flags is set) — proven directly against both adapters."""
    pi_adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path, timeout_seconds=1))
    _assert_guard_quiet(lambda: pi_adapter.run(_pi_request()))  # type: ignore[arg-type]

    codex_adapter = CodexExecAdapter(CodexExecConfig(cwd=tmp_path, timeout_seconds=1), environ={})
    _assert_guard_quiet(lambda: codex_adapter.run(_codex_request()))  # type: ignore[arg-type]
