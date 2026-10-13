"""CLI integration tests for the context repo_url lifecycle.

- A record with neither a URL nor a ``repos/<slug>`` checkout is refused.
- ``context alive`` back-fills repo_url from the on-disk origin remote when the record
  URL is empty (real git + local ``file://`` fixture remote), so the record stays cloneable.
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
from dadaia_workspace.core.exceptions import RepoUrlMissingError
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.features.workspace.service import WorkspaceService  # noqa: E402
from dadaia_workspace.infrastructure.public_assets import (  # noqa: E402
    FileSystemPublicAssetManager,
)
from dadaia_workspace.infrastructure.python_env import (  # noqa: E402
    VenvPythonEnvironmentManager,
)
from tests.fakes import seed_dead_context

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
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
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


# --------------------------------------------------------------------- (a) empty url


def test_empty_url_refusal_ctx_url_1_doctor_flag_and_export_import_clone(
    workspace: Path, tmp_path: Path
) -> None:
    """An unobtainable record is refused; an ALIVE context over a checkout with no origin keeps
    an empty repo_url; one whose checkout has an origin remote gets it back-filled by
    ``context alive``, so a later export/import + ``alive`` on a second machine can clone
    instead of failing on ``git clone ""``.
    """
    # No URL and no repos/bar checkout: nothing could ever clone it — refused, nothing
    # registered.
    with pytest.raises(RepoUrlMissingError):
        seed_dead_context(workspace, "bar", "bar", "")
    assert "bar" not in [c["name"] for c in _contexts(workspace)]

    if not _HAS_GIT:
        return

    # Repo on disk with no origin: ALIVE keeps the empty url.
    repo_path = workspace / "repos" / "baz"
    repo_path.mkdir(parents=True)
    _git(["init"], cwd=repo_path)

    seed_dead_context(workspace, "baz", "baz", "")
    alive = _runner.invoke(app, ["context", "alive", "baz"])
    assert alive.exit_code == 0, alive.output
    assert _record(workspace, "baz")["repo_url"] == ""

    # Export/import clone scenario (own slug "qux" to avoid collision with "bar"/"baz" above).
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

    # 3. A record with NO url adopts the checkout → record repo_url == "".
    seed_dead_context(workspace, "qux", "qux", "")
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
    """A bare associated slug with no URL and no ``repos/a`` is the dead end ``alive`` hits
    cloning ``''`` — ``repo add`` refuses it with one operator action naming the URL to supply."""
    seed_dead_context(workspace, "m", "m", "https://x.test/m.git")
    add = _runner.invoke(app, ["context", "repo", "add", "m", "a"])
    assert add.exit_code == 1, add.output
    assert ".dadaia/.venv/bin/dadaia context repo add m a --url` with the repo's clone URL" in (
        add.output
    )
