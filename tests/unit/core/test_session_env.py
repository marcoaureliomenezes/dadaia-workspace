"""Unit tests for ``core/session_env`` — harness session-id resolution.

v0.3.0: ``entry_harness()`` and the ``DADAIA_ENTRY_HARNESS`` pin were deleted with the
workflow engine (their sole consumer, the ``--harness auto`` sentinel, is gone). What
survives is :func:`harness_session_id` — the harness-native session-id resolution the
gate and context binding key on.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.session_env import harness_session_id


def test_codex_thread_id_resolves_session(monkeypatch: pytest.MonkeyPatch) -> None:
    # T-69-01 (FR1/FR1.2, bug codex-thread-id-bind-resolution-breaks-cli): a modern
    # Codex tool subprocess exposes CODEX_THREAD_ID instead of CODEX_SESSION_ID.
    for var in ("DADAIA_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-abc123")
    assert harness_session_id() == "thread-abc123"

    # AC1.2: when both CODEX_SESSION_ID and CODEX_THREAD_ID are present,
    # harness_session_id() must prefer CODEX_SESSION_ID (CODEX_THREAD_ID is ordered
    # AFTER CODEX_SESSION_ID).
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-sess-1")
    assert harness_session_id() == "codex-sess-1"
