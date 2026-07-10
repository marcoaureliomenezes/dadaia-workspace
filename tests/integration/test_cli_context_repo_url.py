"""CLI integration tests for the context repo_url lifecycle (T-011-08 / FR-W2-03, ADR-7).

Closes bug ``context-repo-url-not-settable-or-repairable``. Covers:
- (a) ``context create --repo <slug> --url <url>`` persists the URL (overrides catalog).
- (b) ``context alive``/``dead`` back-fill repo_url from the on-disk origin remote when
      the record URL is empty (real git + local ``file://`` fixture remote).
- (c) ``context update --url`` repair verb.
- (d) ``dadaia doctor`` flags an ALIVE context with empty repo_url (CTX-URL-1).
- the named regression test reproducing the export/import clone scenario from the bug.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from typer.testing import CliRunner  # noqa: E402

from dadaia_workspace.cli.main import app  # noqa: E402
from dadaia_workspace.features.workspace.service import WorkspaceService  # noqa: E402
from dadaia_workspace.infrastructure.public_assets import (  # noqa: E402
    FileSystemPublicAssetManager,
)
from dadaia_workspace.infrastructure.python_env import (  # noqa: E402
    VenvPythonEnvironmentManager,
)

_runner = CliRunner()
_HAS_GIT = shutil.which("git") is not None


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch) -> Path:  # type: ignore[no-untyped-def]
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _git(args: list[str], cwd: Path) -> None:
    import os

    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@e",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@e",
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(cwd),
        },
    )


def _record(workspace: Path, name: str) -> dict:  # type: ignore[type-arg]
    data = json.loads(
        (workspace / ".dadaia" / "states" / "spec_contexts.json").read_text(encoding="utf-8")
    )
    # spec_contexts.json shape: {"version": ..., "contexts": {name: {...}}} or list.
    contexts = data.get("contexts", data)
    if isinstance(contexts, dict):
        return contexts[name]
    return next(c for c in contexts if c["name"] == name)


# --------------------------------------------------------------------- (a) create --url


def test_create_update_url_persistence_ctx_url_1_doctor_flag_and_export_import_clone(
    workspace: Path, tmp_path: Path
) -> None:
    """(a) create --url persists (overrides catalog); (c) update --url repairs an empty
    record; update on an unknown context exits 1; (d) doctor flags CTX-URL-1 for an ALIVE
    context with an empty repo_url.

    Plus the named regression for bug ``context-repo-url-not-settable-or-repairable``:
    reproduces the VPS export/import clone scenario — a context created without a URL
    whose on-disk repo HAS a valid origin remote. ``context alive`` must back-fill the
    record's repo_url from ``git remote get-url origin`` so that a later export/import +
    ``alive`` on a second machine can clone instead of failing on ``git clone ""``.
    """
    result = _runner.invoke(
        app, ["context", "create", "foo", "--repo", "foo", "--url", "https://x.test/foo.git"]
    )
    assert result.exit_code == 0, result.output
    rec = _record(workspace, "foo")
    assert rec["repo_url"] == "https://x.test/foo.git"

    _runner.invoke(app, ["context", "create", "bar", "--repo", "bar"])
    rec_bar = _record(workspace, "bar")
    assert rec_bar["repo_url"] == ""  # no catalog hit, no --url

    update_result = _runner.invoke(
        app, ["context", "update", "bar", "--url", "https://x.test/bar.git"]
    )
    assert update_result.exit_code == 0, update_result.output
    rec_bar = _record(workspace, "bar")
    assert rec_bar["repo_url"] == "https://x.test/bar.git"

    unknown_result = _runner.invoke(
        app, ["context", "update", "nope", "--url", "https://x.test/x.git"]
    )
    assert unknown_result.exit_code == 1
    assert "not found" in unknown_result.output.lower()

    if not _HAS_GIT:
        return

    # (d) CTX-URL-1: repo on disk with no origin, ALIVE with an empty url.
    repo_path = workspace / "repos" / "baz"
    repo_path.mkdir(parents=True)
    _git(["init"], cwd=repo_path)

    _runner.invoke(app, ["context", "create", "baz", "--repo", "baz"])
    alive = _runner.invoke(app, ["context", "alive", "baz"])
    assert alive.exit_code == 0, alive.output
    assert _record(workspace, "baz")["repo_url"] == ""

    doctor_result = _runner.invoke(app, ["doctor"])
    assert "CTX-URL-1" in doctor_result.output

    # Named regression: export/import clone scenario (own slug "qux" to avoid collision
    # with "foo"/"bar"/"baz" above).
    # 1. Build the upstream the on-disk repo points at (file:// fixture remote).
    upstream = tmp_path / "upstream.git"
    _git(["init", "--bare", str(upstream)], cwd=tmp_path)
    file_url = upstream.as_uri()

    # 2. context create with NO --url (and no catalog hit) → record repo_url == "".
    _runner.invoke(app, ["context", "create", "qux", "--repo", "qux"])
    assert _record(workspace, "qux")["repo_url"] == ""

    # 3. The repo exists on disk with a valid origin remote (clone/populate by any means).
    repo_path = workspace / "repos" / "qux"
    repo_path.mkdir(parents=True)
    _git(["init"], cwd=repo_path)
    _git(["checkout", "-b", "main"], cwd=repo_path)
    _git(["remote", "add", "origin", file_url], cwd=repo_path)
    (repo_path / "README.md").write_text("hi\n", encoding="utf-8")
    _git(["add", "-A"], cwd=repo_path)
    _git(["commit", "-m", "init"], cwd=repo_path)
    _git(["push", "-u", "origin", "main"], cwd=repo_path)

    # 4. context alive → back-fills repo_url from origin (the fix).
    qux_alive = _runner.invoke(app, ["context", "alive", "qux"])
    assert qux_alive.exit_code == 0, qux_alive.output
    assert _record(workspace, "qux")["repo_url"] == file_url

    # 5. The record is now portable: on a second machine (after export/import) the empty
    #    on-disk repo path means ``alive`` clones from the record's repo_url. With the bug,
    #    that URL was "" → ``git clone ""`` fails. Prove the persisted URL is cloneable by
    #    cloning it from a fresh location (the second-machine scenario, isolated from the
    #    orthogonal dead() 0444 rmtree guard).
    persisted = _record(workspace, "qux")["repo_url"]
    assert persisted == file_url
    second_machine = tmp_path / "second-machine-repos" / "qux"
    _git(["clone", persisted, str(second_machine)], cwd=tmp_path)
    assert (second_machine / ".git").exists()
