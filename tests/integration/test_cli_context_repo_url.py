"""CLI integration tests for the context repo_url lifecycle (T-011-08 / FR-W2-03, ADR-7).

Closes bug ``context-repo-url-not-settable-or-repairable``. Covers:
- (a) ``context create --main-repo <slug> --url <url>`` persists the URL; a repo with
      neither a URL nor a ``repos/<slug>`` checkout is refused (bug
      ``context-create-admits-uncloneable-empty-url``).
- (b) ``context alive``/``dead`` back-fill repo_url from the on-disk origin remote when
      the record URL is empty (real git + local ``file://`` fixture remote).
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
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
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
    ).init(tmp_path, harnesses=L1_ENTRY_HARNESSES)
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


def _contexts(workspace: Path) -> list[dict]:  # type: ignore[type-arg]
    data = json.loads(
        (workspace / ".dadaia" / "states" / "spec_contexts.json").read_text(encoding="utf-8")
    )
    return list(data["contexts"])


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


def test_create_url_persistence_ctx_url_1_doctor_flag_and_export_import_clone(
    workspace: Path, tmp_path: Path
) -> None:
    """(a) create --url persists; (d) doctor flags CTX-URL-1 for an
    ALIVE context with an empty repo_url.

    Plus the named regression for bug ``context-repo-url-not-settable-or-repairable``:
    reproduces the VPS export/import clone scenario — a context created without a URL
    whose on-disk repo HAS a valid origin remote. ``context alive`` must back-fill the
    record's repo_url from ``git remote get-url origin`` so that a later export/import +
    ``alive`` on a second machine can clone instead of failing on ``git clone ""``.
    """
    result = _runner.invoke(
        app, ["context", "create", "foo", "--main-repo", "foo", "--url", "https://x.test/foo.git"]
    )
    assert result.exit_code == 0, result.output
    rec = _record(workspace, "foo")
    assert rec["repo_url"] == "https://x.test/foo.git"

    # No --url and no repos/bar checkout: nothing could ever clone it — refused, nothing
    # registered, one runnable fix line (bug context-create-admits-uncloneable-empty-url).
    refused = _runner.invoke(app, ["context", "create", "bar", "--main-repo", "bar"])
    assert refused.exit_code == 1, refused.output
    assert "fix: .dadaia/.venv/bin/dadaia context create bar --main-repo bar --url <clone-url>" in (
        refused.output
    )
    assert "bar" not in [c["name"] for c in _contexts(workspace)]

    if not _HAS_GIT:
        return

    # (d) CTX-URL-1: repo on disk with no origin, ALIVE with an empty url.
    repo_path = workspace / "repos" / "baz"
    repo_path.mkdir(parents=True)
    _git(["init"], cwd=repo_path)

    _runner.invoke(app, ["context", "create", "baz", "--main-repo", "baz"])
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

    # 2. The repo exists on disk with a valid origin remote (clone/populate by any means).
    repo_path = workspace / "repos" / "qux"
    repo_path.mkdir(parents=True)
    _git(["init"], cwd=repo_path)
    _git(["checkout", "-b", "main"], cwd=repo_path)
    _git(["remote", "add", "origin", file_url], cwd=repo_path)
    (repo_path / "README.md").write_text("hi\n", encoding="utf-8")
    _git(["add", "-A"], cwd=repo_path)
    _git(["commit", "-m", "init"], cwd=repo_path)
    _git(["push", "-u", "origin", "main"], cwd=repo_path)

    # 3. context create with NO --url adopts the checkout → record repo_url == "".
    _runner.invoke(app, ["context", "create", "qux", "--main-repo", "qux"])
    assert _record(workspace, "qux")["repo_url"] == ""

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


def test_a_bare_associated_slug_with_no_checkout_is_refused(workspace: Path) -> None:
    """Bug context-create-admits-uncloneable-empty-url, associated arm: ``--associated-repos
    a`` with no ``=URL`` and no ``repos/a`` is the same dead end ``alive`` hits cloning
    ``''`` — create and ``repo add`` refuse it with one runnable fix line."""
    create = _runner.invoke(
        app,
        [
            "context",
            "create",
            "m",
            "--main-repo",
            "m",
            "--url",
            "https://x.test/m.git",
            "--associated-repos",
            "a",
        ],
    )
    assert create.exit_code == 1, create.output
    assert (
        "fix: .dadaia/.venv/bin/dadaia context create m --main-repo m "
        "--url https://x.test/m.git --associated-repos a=<clone-url>"
    ) in create.output
    assert "m" not in [c["name"] for c in _contexts(workspace)]

    ok = _runner.invoke(
        app, ["context", "create", "m", "--main-repo", "m", "--url", "https://x.test/m.git"]
    )
    assert ok.exit_code == 0, ok.output
    add = _runner.invoke(app, ["context", "repo", "add", "m", "a"])
    assert add.exit_code == 1, add.output
    assert "fix: .dadaia/.venv/bin/dadaia context repo add m a --url <clone-url>" in add.output
