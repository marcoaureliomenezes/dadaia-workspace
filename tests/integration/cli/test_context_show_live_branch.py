"""v0.1.72 FR4 — ``context show`` reports the LIVE branch for an ALIVE repo (bug
``context-current-branch-stale-for-alive-repo``).

The registry stores ``current_branch`` only at alive()/dead() transitions; the reporter's
remote had the repo on ``feature/v0.1.1`` while the store (and ``show``) said ``main`` —
and alive() restores from the stored value, so a stale snapshot can revive a context on
the wrong branch. Fix: for an ALIVE context whose repo exists on disk, ``show`` reports
the actual checked-out branch and exposes the stored snapshot as ``stored_branch``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

pytestmark = [pytest.mark.integration]

_runner = CliRunner()
_CTX = "live-branch-ctx"


def _make_workspace_with_repo(root: Path) -> Path:
    ws = root / "ws"
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    repo = ws / "repos" / _CTX
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "init"], check=True)
    # The LIVE branch differs from the stored snapshot below.
    subprocess.run(["git", "-C", str(repo), "checkout", "-qb", "feature/v9.9.9"], check=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": _CTX,
                        "state": "alive",
                        "repo_slug": _CTX,
                        "repo_url": "https://example.invalid/live-branch-ctx.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                        "current_branch": "main",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return ws


def test_show_reports_live_branch_for_alive_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stored snapshot says ``main``; the repo is actually on ``feature/v9.9.9`` — show
    must report the live branch (and keep the snapshot as ``stored_branch``)."""
    ws = _make_workspace_with_repo(tmp_path)
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["current_branch"] == "feature/v9.9.9", payload
    assert payload["stored_branch"] == "main"


def test_show_falls_back_to_stored_branch_when_repo_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No repo on disk (e.g. DEAD or not yet cloned) ⇒ stored snapshot is reported."""
    ws = _make_workspace_with_repo(tmp_path)
    import shutil

    shutil.rmtree(ws / "repos" / _CTX)
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["current_branch"] == "main"
    assert payload["stored_branch"] == "main"
