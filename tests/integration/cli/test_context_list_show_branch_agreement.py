"""FR18/A18.1-A18.3 (v0.4.4 T-044-29) — `list` and `show` never disagree on
`current_branch` for an ALIVE repo whose checkout moved.

Intent: CONTRACT — bug `context-list-current-branch-stale-for-alive-repo`
(superseded_by: spec-context-associated-repos), acceptance carried by FR18.

This is the bug's own repro, as a regression test (A18.2): register an ALIVE
context with a stored `current_branch` snapshot, checkout a DIFFERENT branch on
disk, then assert `context list --json` and `context show --json` report the
SAME `current_branch` for that context — the live one, not the stale snapshot.
Before the fix, `list` read the store's cached snapshot directly while `show`
queried git live (two divergent branch-resolution implementations); the fix
collapses both onto `SpecContextService.repo_live_status` (A18.3).
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
_CTX = "list-show-agree-ctx"


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
    # 1. dadaia context alive <ctx> lands the repo on "main" (the stored snapshot
    # below). 2. The operator/agent then checks out a DIFFERENT branch on disk —
    # the exact bug repro step.
    subprocess.run(["git", "-C", str(repo), "checkout", "-qb", "feature/moved"], check=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": _CTX,
                        "state": "alive",
                        "repo_slug": _CTX,
                        "repo_url": "https://example.invalid/list-show-agree-ctx.git",
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


def test_list_and_show_report_the_same_current_branch_for_alive_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _make_workspace_with_repo(tmp_path)
    monkeypatch.chdir(ws)

    list_result = _runner.invoke(app, ["context", "list", "--json"])
    assert list_result.exit_code == 0, list_result.output
    show_result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert show_result.exit_code == 0, show_result.output

    list_payload = json.loads(list_result.stdout)
    show_payload = json.loads(show_result.stdout)
    list_row = next(row for row in list_payload if row["name"] == _CTX)

    # The bug: list_row["current_branch"] used to be the stale stored snapshot
    # ("main") while show_payload["current_branch"] was the live branch
    # ("feature/moved"). They must agree — on the LIVE branch, never the snapshot.
    assert list_row["current_branch"] == "feature/moved", list_row
    assert show_payload["current_branch"] == "feature/moved", show_payload
    assert list_row["current_branch"] == show_payload["current_branch"]

    # The stored snapshot remains meaningful but is exposed under a distinct name
    # in BOTH verbs (A18.1) — never silently reused as `current_branch`.
    assert list_row["stored_branch"] == "main"
    assert show_payload["stored_branch"] == "main"
