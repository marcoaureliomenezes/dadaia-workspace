"""``dadaia init <dir> --harness <name> --repo <url>`` — the one-line bootstrap (0.4.7 FR1).

Intent: CONTRACT — 0.4.7 FR1 / AC1.1 (T-047-74). Size: MEDIUM (directory-tiered
``integration``).

``--repo`` makes ``init`` a CALLER of the context lifecycle: the repo is cloned into
``repos/<slug>/`` by the same ``SpecContextService.alive`` clone every other verb uses,
the context is created with that slug as its main repo, alive'd, bound to this session,
and the cloned repo gets the pre-push chokepoint. Network-free: the origin is a local
bare repo, so the assertions below exercise the real git path with no remote.

``dadaia doctor`` exit 0 on this tree is AC1.1's own assertion and lives in
``tests/e2e/test_one_line_bootstrap.py`` (T-047-75): the suite stubs the venv builder
(``tests/conftest.py::_no_real_venv_in_tests``), so doctor's VENV-1 check can never pass
in-process for reasons that have nothing to do with FR1.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()

_LAW = "Sessions launch at the workspace root."


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    )


@pytest.fixture()
def origin(tmp_path: Path) -> Path:
    """A local bare repo named ``demo-project.git`` carrying one commit."""
    bare = tmp_path / "origin" / "demo-project.git"
    bare.parent.mkdir(parents=True)
    _git("init", "--bare", "--initial-branch=main", str(bare), cwd=tmp_path)

    work = tmp_path / "seed"
    work.mkdir()
    _git("init", "--initial-branch=main", cwd=work)
    (work / "README.md").write_text("seed\n", encoding="utf-8")
    _git("add", "README.md", cwd=work)
    _git("commit", "-m", "seed", cwd=work)
    _git("remote", "add", "origin", str(bare), cwd=work)
    _git("push", "origin", "main", cwd=work)
    return bare


def test_init_with_repo_clones_creates_alives_binds_and_installs_the_hook(
    tmp_path: Path, origin: Path
) -> None:
    workspace = tmp_path / "ws"

    result = _runner.invoke(
        app,
        ["init", str(workspace), "--harness", "claude", "--skip-assets", "--repo", str(origin)],
    )

    assert result.exit_code == 0, result.stdout

    # 1. cloned into repos/<slug>/ — slug is the URL's last segment minus `.git`.
    repo = workspace / "repos" / "demo-project"
    assert (repo / ".git").is_dir()
    assert (repo / "README.md").read_text(encoding="utf-8") == "seed\n"

    # 2. the context exists with that slug as its main repo, and is ALIVE.
    registry = json.loads(
        (workspace / ".dadaia" / "states" / "spec_contexts.json").read_text(encoding="utf-8")
    )
    contexts = {ctx["name"]: ctx for ctx in registry["contexts"]}
    assert contexts["demo-project"]["repo_slug"] == "demo-project"
    assert contexts["demo-project"]["state"] == "alive"

    # 3. this session is bound to it.
    sessions = list((workspace / ".dadaia" / "sessions").glob("*.json"))
    bindings = [json.loads(path.read_text(encoding="utf-8")) for path in sessions]
    assert [record["context"] for record in bindings] == ["demo-project"]

    # 4. the pre-push chokepoint is installed in the cloned repo, executable.
    hook = repo / ".git" / "hooks" / "pre-push"
    assert hook.is_file()
    assert os.access(hook, os.X_OK)

    # 5. the eval-ready binding is printed — the SAME two lines `context bind
    #    --print-env` emits, so the operator's shell reaches the context it just made.
    assert "export DADAIA_CONTEXT=demo-project" in result.stdout
    assert "export DADAIA_SESSION_ID=" in result.stdout

    # 6. `create` is the only context verb init ever names (FR1: a single-repo
    #    workspace is the degenerate multi-repo case).
    for verb in ("context alive", "context bind", "context dead", "context show"):
        assert verb not in result.stdout


def test_init_with_an_unreachable_repo_exits_1_with_one_fix_line(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"

    result = _runner.invoke(
        app,
        [
            "init",
            str(workspace),
            "--harness",
            "claude",
            "--skip-assets",
            "--repo",
            str(tmp_path / "nowhere.git"),
        ],
    )

    assert result.exit_code == 1
    assert len([line for line in result.output.splitlines() if line.startswith("fix: ")]) == 1
    assert not (workspace / "repos" / "nowhere").exists()


def test_init_without_repo_closes_with_exactly_three_lines(tmp_path: Path) -> None:
    result = _runner.invoke(app, ["init", str(tmp_path / "ws"), "--harness", "claude"])

    assert result.exit_code == 0, result.stdout
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    closing = lines[-3:]
    assert closing[0] == _LAW
    assert closing[1].startswith("Claude Code: set `instructionFiles:")
    # The third line: where projects live, and the ONE command that makes the first.
    assert "repos/" in closing[2]
    assert "dadaia context create" in closing[2]
    # Exactly three — nothing above them is a closing note.
    assert _LAW not in "\n".join(lines[:-3])
