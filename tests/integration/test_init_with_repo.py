"""`dadaia init <dir> --harness <name> --repo <url>` clones, creates and alives one context."""

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
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid"}
    env |= {"GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env)


def _seed(bare: Path, text: str) -> Path:
    bare.parent.mkdir(parents=True, exist_ok=True)
    _git("init", "--bare", "--initial-branch=main", str(bare), cwd=bare.parent)
    work = bare.parent / f"seed-{bare.name}"
    work.mkdir()
    _git("init", "--initial-branch=main", cwd=work)
    (work / "README.md").write_text(text, encoding="utf-8")
    _git("add", "README.md", cwd=work)
    _git("commit", "-m", "seed", cwd=work)
    _git("remote", "add", "origin", str(bare), cwd=work)
    _git("push", "origin", "main", cwd=work)
    return bare


@pytest.fixture()
def origin(tmp_path: Path) -> Path:
    return _seed(tmp_path / "origin" / "demo-project.git", "seed\n")


def _init(workspace: Path, url: Path) -> list[str]:
    return ["init", str(workspace), "--harness", "claude", "--skip-assets", "--repo", str(url)]


def _contexts(workspace: Path) -> list[dict[str, str]]:
    path = workspace / ".dadaia" / "states" / "spec_contexts.json"
    return list(json.loads(path.read_text(encoding="utf-8"))["contexts"])


def test_init_with_repo_clones_creates_alives_binds_and_installs_the_hook(
    tmp_path: Path, origin: Path
) -> None:
    """The repo lands in repos/<slug>/, its context is ALIVE and unbound, the pre-push hook runs."""
    workspace = tmp_path / "ws"

    result = _runner.invoke(app, _init(workspace, origin))

    assert result.exit_code == 0, result.stdout
    repo = workspace / "repos" / "demo-project"
    assert (repo / "README.md").read_text(encoding="utf-8") == "seed\n"
    [ctx] = _contexts(workspace)
    assert (ctx["name"], ctx["repo_slug"], ctx["state"]) == (
        "demo-project",
        "demo-project",
        "alive",
    )
    assert not list((workspace / ".dadaia" / "sessions").glob("*.json"))  # AC7.1
    hook = repo / ".git" / "hooks" / "pre-push"
    assert hook.is_file() and os.access(hook, os.X_OK)
    assert "export DADAIA_" not in result.stdout and "bound" not in result.stdout
    for verb in ("context alive", "context bind", "context dead", "context show"):
        assert verb not in result.stdout


def test_the_printed_fix_line_succeeds_once_the_url_is_reachable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreachable --repo exits 1 with one `context create` fix line that succeeds once reachable."""
    workspace = tmp_path / "ws"
    bare = tmp_path / "app.git"

    failed = _runner.invoke(app, _init(workspace, bare))

    assert failed.exit_code == 1
    fixes = [ln for ln in failed.output.splitlines() if ln.startswith("fix: ")]
    venv_cli = workspace / ".dadaia" / ".venv" / "bin" / "dadaia"
    assert fixes == [
        f"fix: Operator action: run `{venv_cli} context create --main-repo {bare}` with a "
        f"reachable clone URL in place of {bare}"
    ]
    assert not (workspace / "repos" / "app").exists()

    _seed(bare, "app\n")
    monkeypatch.chdir(workspace)
    retry = _runner.invoke(app, ["context", "create", "--main-repo", str(bare)])

    assert retry.exit_code == 0, retry.output
    assert (workspace / "repos" / "app" / "README.md").read_text(encoding="utf-8") == "app\n"
    assert [c["state"] for c in _contexts(workspace) if c["name"] == "app"] == ["alive"]


def test_init_without_repo_closes_with_the_law_and_the_next_step(tmp_path: Path) -> None:
    """The last three lines are the law, the next step, and its venv-CLI `context create` fix."""
    ws = tmp_path / "ws"
    result = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])

    assert result.exit_code == 0, result.stdout
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    closing = lines[-3:]
    assert closing[0] == _LAW
    assert closing[1].startswith("Next (")  # AC6.2
    assert closing[2].startswith(
        f"fix: Operator action: run {ws / '.dadaia' / '.venv' / 'bin' / 'dadaia'} context create"
    )
    assert _LAW not in "\n".join(lines[:-3])


def test_re_init_is_idempotent_and_another_url_under_the_slug_refuses(
    tmp_path: Path, origin: Path
) -> None:
    """Re-running the same init changes nothing; the same slug from another origin exits 1, record kept."""
    workspace = tmp_path / "ws"
    assert _runner.invoke(app, _init(workspace, origin)).exit_code == 0

    def _snapshot() -> dict[str, str]:
        return {
            str(path.relative_to(workspace)): path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(workspace.rglob("*"))
            if path.is_file() and ".dadaia/sessions" not in path.as_posix()
        }

    before = _snapshot()
    rerun = _runner.invoke(app, _init(workspace, origin))
    assert rerun.exit_code == 0, rerun.stdout
    assert _snapshot() == before

    imposter = tmp_path / "elsewhere" / "demo-project.git"
    imposter.parent.mkdir()
    _git("clone", "--bare", "-q", str(origin), str(imposter), cwd=tmp_path)
    refused = _runner.invoke(app, _init(workspace, imposter))

    assert refused.exit_code == 1, refused.output
    assert len([ln for ln in refused.output.splitlines() if ln.startswith("fix: ")]) == 1
    assert [ctx["repo_url"] for ctx in _contexts(workspace)] == [str(origin)]
