"""T-69-08/T-69-09 (FR4, bug ``context-bind-success-not-reflected-in-context-show``, MEDIUM).

``bind`` mints a session id, persists the record, and refreshes the incumbent pointer
(``session_identity.set_incumbent``) — but only *prints* the sid. ``show`` resolves the
session SOLELY from ``os.environ.get("DADAIA_SESSION_ID")``; when unset (the normal case
after a bare ``dadaia context bind``, no ``eval $(...)``), ``session`` is ``None`` — a
successful bind is invisible to ``show``.

Pre-fix (T-69-08 RED, superseded here to its GREEN form matching the T-69-04/T-69-06
pattern): with ``DADAIA_SESSION_ID`` unset, a real ``context bind`` followed by
``context show --json`` reported ``session: null`` despite the bind having just
succeeded and written the incumbent pointer.

Post-fix (T-69-09 GREEN): ``show`` falls back to
``session_identity.read_incumbent_ptr(workspace, ctx)``, loads + stale-checks that
record, and populates ``session`` with sid/mode/release/context (AC4.1). Resolution
order stays env first, then the incumbent pointer; a stale/absent pointer still yields
``session: null`` (AC4.2, unchanged).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

pytestmark = [pytest.mark.integration]

_runner = CliRunner()
_CTX = "show-ctx"


def _make_workspace(root: Path) -> Path:
    ws = root / "ws"
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": _CTX,
                        "state": "alive",
                        "repo_slug": _CTX,
                        "repo_url": "https://example.invalid/show-ctx.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return ws


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        monkeypatch.delenv(var, raising=False)


def test_bind_success_reflected_in_show_json_ac41(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _make_workspace(tmp_path)
    monkeypatch.chdir(ws)

    bind_result = _runner.invoke(
        app,
        [
            "context",
            "bind",
            _CTX,
            "--mode",
            "implementation",
            "--release",
            "v0.1.69",
        ],
    )
    assert bind_result.exit_code == 0, bind_result.output

    show_result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert show_result.exit_code == 0, show_result.output
    payload = json.loads(show_result.output)

    # AC4.1: session.session_id == the bound sid, with populated mode/release/context —
    # not null, despite DADAIA_SESSION_ID never being set in this shell.
    assert payload["session"] is not None, (
        "context show --json must reflect the just-completed bind via the incumbent "
        f"pointer fallback (FR4); got session=None. Full payload: {payload}"
    )
    session = payload["session"]
    assert session["context"] == _CTX
    assert session["mode"].upper() == "BOUND_IMPLEMENTATION"
    assert session["release"] == "v0.1.69"


def test_show_without_any_bind_still_reports_null_session_ac42(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4.2 regression guard: no bind at all ⇒ session stays null (unchanged)."""
    ws = _make_workspace(tmp_path)
    monkeypatch.chdir(ws)

    show_result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert show_result.exit_code == 0, show_result.output
    payload = json.loads(show_result.output)
    assert payload["session"] is None


# --- v0.1.71 FR3: no-arg `context show` reflects the bound session -------------------


def _make_two_context_workspace(root: Path) -> Path:
    """First-ALIVE ``default-first`` (never bound) + ``bound-second`` (bound below)."""
    ws = root / "ws2"
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": "default-first",
                        "state": "alive",
                        "repo_slug": "default-first",
                        "repo_url": "https://example.invalid/default-first.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    },
                    {
                        "name": "bound-second",
                        "state": "alive",
                        "repo_slug": "bound-second",
                        "repo_url": "https://example.invalid/bound-second.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return ws


def test_noarg_show_resolves_to_bound_context_not_first_alive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR3: after a bare ``context bind bound-second``, ``context show --json`` (NO arg)
    surfaces ``bound-second`` with its live session — not first-ALIVE ``default-first``
    with ``session: null`` (the exact remote symptom against 574a84bd)."""
    ws = _make_two_context_workspace(tmp_path)
    monkeypatch.chdir(ws)

    bind_result = _runner.invoke(
        app,
        ["context", "bind", "bound-second", "--mode", "implementation", "--release", "v0.2.0"],
    )
    assert bind_result.exit_code == 0, bind_result.output

    show_result = _runner.invoke(app, ["context", "show", "--json"])
    assert show_result.exit_code == 0, show_result.output
    payload = json.loads(show_result.output)
    assert payload["name"] == "bound-second", payload
    assert payload["session"] is not None, payload
    assert payload["session"]["context"] == "bound-second"
    assert payload["session"]["release"] == "v0.2.0"


def test_noarg_show_falls_back_to_first_alive_when_no_bound_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR3 fallback: with no live bound session anywhere, no-arg show returns first-ALIVE
    (unchanged prior behaviour)."""
    ws = _make_two_context_workspace(tmp_path)
    monkeypatch.chdir(ws)

    show_result = _runner.invoke(app, ["context", "show", "--json"])
    assert show_result.exit_code == 0, show_result.output
    payload = json.loads(show_result.output)
    assert payload["name"] == "default-first", payload
    assert payload["session"] is None
