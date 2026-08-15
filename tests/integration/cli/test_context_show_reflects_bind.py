"""Caller-scoped bind state is visible to context show without global pointers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.fixtures.harness_env import scrub_context_resolution_env

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
    """Bug ``specs-resolver-context-tests-flaky-under-xdist-full-suite``: also scrubs
    ``WORKSPACE_ROOT``, honoured unconditionally by the resolution authority ahead of
    every ``monkeypatch.chdir()`` this module performs."""
    scrub_context_resolution_env(monkeypatch)


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


def test_context_show_reflects_bind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bind/show resolves through this harness's own record only."""
    monkeypatch.setenv("CODEX_THREAD_ID", "test-harness-session")
    # AC4.1 — named show reflects a just-completed bind.
    named_ws = _make_workspace(tmp_path)
    monkeypatch.chdir(named_ws)

    bind_result = _runner.invoke(
        app,
        ["context", "bind", _CTX, "--mode", "implementation", "--release", "v0.1.69"],
    )
    assert bind_result.exit_code == 0, bind_result.output

    named_show_result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert named_show_result.exit_code == 0, named_show_result.output
    named_payload = json.loads(named_show_result.output)
    assert named_payload["session"] is not None, (
        "context show --json must reflect the caller-owned harness session; "
        f"got session=None. Full payload: {named_payload}"
    )
    named_session = named_payload["session"]
    assert named_session["context"] == _CTX
    assert named_session["mode"].upper() == "BOUND_IMPLEMENTATION"
    assert named_session["release"] == "v0.1.69"

    # AC4.2 — no bind at all -> named show still reports session: null.
    no_bind_ws = _make_workspace(tmp_path / "no-bind-root")
    monkeypatch.chdir(no_bind_ws)
    no_bind_show_result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert no_bind_show_result.exit_code == 0, no_bind_show_result.output
    no_bind_payload = json.loads(no_bind_show_result.output)
    assert no_bind_payload["session"] is None

    # FR3 — no-arg show resolves to the bound context, not first-ALIVE.
    two_ctx_ws = _make_two_context_workspace(tmp_path)
    monkeypatch.chdir(two_ctx_ws)

    bind_second_result = _runner.invoke(
        app,
        ["context", "bind", "bound-second", "--mode", "implementation", "--release", "v0.2.0"],
    )
    assert bind_second_result.exit_code == 0, bind_second_result.output

    noarg_show_result = _runner.invoke(app, ["context", "show", "--json"])
    assert noarg_show_result.exit_code == 0, noarg_show_result.output
    noarg_payload = json.loads(noarg_show_result.output)
    assert noarg_payload["name"] == "bound-second", noarg_payload
    assert noarg_payload["session"] is not None, noarg_payload
    assert noarg_payload["session"]["context"] == "bound-second"
    assert noarg_payload["session"]["release"] == "v0.2.0"

    # Caller-owned selection — without a bind, no-arg show ANSWERS null (exit 0).
    # Contract changed by bug context-show-json-traceback-unbound (consumer validation
    # 2026-07-15): `show` is a query verb, so "nothing selected" is a valid answer —
    # the old fail-loud behavior surfaced as a raw ValueError traceback in the field
    # and broke agent-side context discovery.
    fallback_ws = _make_two_context_workspace(tmp_path / "fallback-root")
    monkeypatch.chdir(fallback_ws)
    fallback_show_result = _runner.invoke(app, ["context", "show", "--json"])
    assert fallback_show_result.exit_code == 0, fallback_show_result.output
    assert fallback_show_result.exception is None
    assert json.loads(fallback_show_result.output) == {"context": None}
