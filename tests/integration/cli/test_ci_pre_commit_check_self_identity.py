"""`dadaia ci pre-commit-check` — the committing session recognises itself.

Intent: CONTRACT — bug pre-commit-presence-advisory-names-the-committing-session-itself

The git hook spawns this verb as a harness-FREE child: no hook payload, only the
environment the harness exported into the shell that ran ``git commit``. A harness
session exports its native id (``CLAUDE_CODE_SESSION_ID`` / ``CODEX_SESSION_ID`` /
``CODEX_THREAD_ID``) and never ``DADAIA_SESSION_ID``, so the verb must identify itself
through the ONE session-id rule (``core.invocation.resolve_session_id``) — a
single-variable read left its own presence record indistinguishable from a foreign one
and the advisory named the committing session as "another session".

MEDIUM tier by necessity: the seam is the CLI composition root (``cli/commands/ci.py``
wiring ``cli._specs_resolution.resolve_session_id_for_cli()`` — the sanctioned door onto
the ONE rule — into ``pre_commit_decision``), which the pure-function unit test in
``tests/unit/features/chokepoints/test_pre_commit_decision.py`` cannot reach. A real,
disposable git repo (a few kilobytes on ``tmp_path``, never a venv) keeps the verb's own
``git`` calls on their executed path.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app

_runner = CliRunner()
_SLUG = "demo-ctx"
_OWN = "harness-session-A"


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)


def _write_presence(workspace: Path, sid: str) -> None:
    path = workspace / ".dadaia" / "states" / "presence" / _SLUG / f"{sid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    path.write_text(
        json.dumps(
            {
                "session_id": sid,
                "runtime": "codex",
                "pid": 4321,
                "started_at": now,
                "last_seen_at": now,
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("holder", "expect_advisory"),
    [(_OWN, False), ("harness-session-B", True)],
    ids=["own-record-is-silent", "foreign-record-is-named"],
)
def test_pre_commit_check_identifies_itself_via_the_harness_native_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, holder: str, expect_advisory: bool
) -> None:
    workspace = tmp_path
    repo = workspace / "repos" / _SLUG
    _init_repo(repo)
    _write_presence(workspace, holder)
    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    monkeypatch.setenv("WORKSPACE_ROOT", str(workspace))
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", _OWN)

    result = _runner.invoke(app, ["ci", "pre-commit-check"])

    assert result.exit_code == 0, result.output + result.stderr
    combined = result.output + result.stderr
    if expect_advisory:
        assert "another session 'harness-session-B'" in combined
    else:
        assert "another session" not in combined, combined
