"""v0.1.72 FR4 (bug context-current-branch-stale-for-alive-repo) and
v0.4.4 FR18 A18.1-A18.3 (bug context-list-current-branch-stale-for-alive-repo): for an
ALIVE context whose repo is on disk, `context list` and `context show` both report the
LIVE checked-out branch (one resolver, `repo_live_status`) and expose the stored snapshot
as `stored_branch`; with no repo on disk the snapshot is reported.
"""

from __future__ import annotations

import json
import shutil
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


@pytest.mark.parametrize(("on_disk", "branch"), [(True, "feature/v9.9.9"), (False, "main")])
def test_list_and_show_report_the_live_branch_else_the_stored_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, on_disk: bool, branch: str
) -> None:
    ws = _make_workspace_with_repo(tmp_path)
    if not on_disk:
        shutil.rmtree(ws / "repos" / _CTX)
    monkeypatch.chdir(ws)

    shown = json.loads(_runner.invoke(app, ["context", "show", _CTX, "--json"]).stdout)
    listed = json.loads(_runner.invoke(app, ["context", "list", "--json"]).stdout)
    row = next(r for r in listed if r["name"] == _CTX)

    for payload in (shown, row):
        assert (payload["current_branch"], payload["stored_branch"]) == (branch, "main"), payload
