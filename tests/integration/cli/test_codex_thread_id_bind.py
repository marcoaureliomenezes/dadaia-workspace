"""T-69-03 (FR1.3, bug ``codex-thread-id-bind-resolution-breaks-cli``, CRITICAL).

Integration proof for the AC1.3 chain: with ONLY ``CODEX_THREAD_ID`` set in the
environment (the shape a modern Codex tool subprocess actually exposes —
``CODEX_SESSION_ID`` absent), a real ``dadaia context bind`` CLI invocation must:

1. persist a session record keyed by the sanitized thread id
   (``.dadaia/sessions/<thread-id>.json``) — the v0.1.55 FR4 harness-native channel
   (``bind`` calls ``harness_session_id()``, which now recognizes ``CODEX_THREAD_ID``
   per T-69-02); and
2. make the bound context resolvable by a resolver-driven CLI call with NO
   ``--specs-dir`` flag — exercised here via the real
   ``dadaia_workspace.cli._specs_resolution.resolve_specs_dir_for_cli`` seam (the same
   function every resolver-driven ``dadaia`` command calls), proving the
   ``core.specs_resolver._session_context`` harness-native channel actually resolves the
   live thread-keyed record end to end.

Hand-assembles a minimal ``tmp_path`` workspace (registry + specs tree) — no git clone,
matching the existing ``test_cli_bound_session_resolution.py`` /
``test_specs_resolver_harness_bind.py`` pattern — and drives the REAL ``context bind``
Typer command via ``CliRunner`` (executed path, not a hand-fed session record).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.cli.main import app
from tests.fixtures.harness_env import scrub_context_resolution_env

pytestmark = [pytest.mark.integration]

_runner = CliRunner()
_CTX = "thread-ctx"
_THREAD_ID = "thread-abc123def456"


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
                        "repo_url": "https://example.invalid/thread-ctx.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (ws / "repos" / _CTX / "specs").mkdir(parents=True)
    return ws


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bug ``specs-resolver-context-tests-flaky-under-xdist-full-suite``: also scrubs
    ``WORKSPACE_ROOT``, honoured unconditionally by the resolution authority ahead of
    every ``monkeypatch.chdir()`` this module performs."""
    scrub_context_resolution_env(monkeypatch)


def test_codex_thread_id_bind_persists_resolver_attributes_and_negative_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CRITICAL-adjacent (minimal merge only, v0.1.76 rewrites): a real bind persists a
    thread-keyed session record and makes the bound context resolver-attributable with
    no --specs-dir; negative control confirms no bind means no record and no
    attribution."""
    ws = _make_workspace(tmp_path)
    monkeypatch.chdir(ws)
    monkeypatch.setenv("CODEX_THREAD_ID", _THREAD_ID)

    result = _runner.invoke(
        app,
        ["context", "bind", _CTX, "--mode", "read"],
    )
    assert result.exit_code == 0, result.output

    # (1) a session record keyed to the sanitized thread id exists and carries the
    # bound context — the v0.1.55 FR4 harness-native channel, now reachable via
    # CODEX_THREAD_ID (T-69-02).
    thread_record_path = ws / ".dadaia" / "sessions" / f"{_THREAD_ID}.json"
    assert thread_record_path.is_file(), (
        f"bind must persist a session record keyed by CODEX_THREAD_ID; "
        f"found: {sorted(p.name for p in (ws / '.dadaia' / 'sessions').glob('*.json'))}"
    )
    record = json.loads(thread_record_path.read_text(encoding="utf-8"))
    assert record["context"] == _CTX
    assert record["session_id"] == _THREAD_ID

    # (2) a resolver-driven CLI call (no --specs-dir) attributes the bound context via
    # the harness-native channel — the exact seam every resolver-driven `dadaia`
    # command (bugs append, specs doctor, ...) calls.
    resolved = resolve_specs_dir_for_cli(None)
    assert resolved == (ws / "repos" / _CTX / "specs").resolve()

    # (3) negative control: no bind -> no thread-keyed record -> resolver cannot
    # attribute, in a fresh unbound workspace.
    unbound_ws = _make_workspace(tmp_path / "unbound-root")
    monkeypatch.chdir(unbound_ws)

    unbound_thread_record_path = unbound_ws / ".dadaia" / "sessions" / f"{_THREAD_ID}.json"
    assert not unbound_thread_record_path.exists()

    with pytest.raises(typer.BadParameter):  # no bind, no cwd/specs fallback
        resolve_specs_dir_for_cli(None)
