"""Direct unit pin of ``resolve_context_for_cli``'s fallback ORDERING (v0.1.77 FR1).

QA finding (v0.1.77 release review, LOW): the seam's rung order — explicit → env →
own session → first-ALIVE → self-hosting-slug terminal fallback — was exercised only
indirectly. These tests pin the two rungs that protect CONSUMER workspaces: a real
ALIVE context always outranks the terminal ``"dadaia-workspace"`` literal, and the
literal fires only in the degenerate zero-ALIVE-context workspace.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.cli._specs_resolution import resolve_context_for_cli

pytestmark = pytest.mark.unit


def _mk_workspace(root: Path, contexts: list[str]) -> None:
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": name,
                        "state": "alive",
                        "repo_slug": name,
                        "repo_url": f"https://example.invalid/{name}.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    }
                    for name in contexts
                ],
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def _clean_session_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.usefixtures("_clean_session_env")
@pytest.mark.parametrize(
    ("contexts", "expected"),
    [
        pytest.param(
            ["consumer-only-context"],
            "consumer-only-context",
            id="first-alive-outranks-the-terminal-literal-in-a-consumer-workspace",
        ),
        pytest.param(
            [],
            "dadaia-workspace",
            id="terminal-literal-fires-only-with-zero-alive-contexts",
        ),
    ],
)
def test_fallback_ordering_first_alive_before_terminal_literal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    contexts: list[str],
    expected: str,
) -> None:
    ws = tmp_path / "ws"
    _mk_workspace(ws, contexts)
    monkeypatch.chdir(ws)
    assert resolve_context_for_cli(None) == expected


@pytest.mark.usefixtures("_clean_session_env")
def test_explicit_and_env_outrank_first_alive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "ws"
    _mk_workspace(ws, ["alive-ctx"])
    monkeypatch.chdir(ws)
    assert resolve_context_for_cli("explicit-ctx") == "explicit-ctx"
    monkeypatch.setenv("DADAIA_CONTEXT", "env-ctx")
    assert resolve_context_for_cli(None) == "env-ctx"
