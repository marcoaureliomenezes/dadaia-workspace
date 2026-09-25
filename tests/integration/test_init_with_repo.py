"""``dadaia init <dir> --harness <name> --repo <url>`` — the one-line bootstrap (0.4.7 FR1).

Intent: CONTRACT — 0.4.7 FR1 / AC1.1 (T-047-74). Size: MEDIUM (directory-tiered
``integration``).

``--repo`` makes ``init`` a CALLER of the context lifecycle: the repo is cloned into
``repos/<slug>/`` by the same ``SpecContextService.alive`` clone every other verb uses,
the context is created with that slug as its main repo, alive'd (never bound — ADR 0038),
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
from dadaia_workspace.core.cli_line import fix_line

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

    # 3. AC7.1: init binds nothing — no session record, `context bind` is the one binder.
    assert not list((workspace / ".dadaia" / "sessions").glob("*.json"))

    # 4. the pre-push chokepoint is installed in the cloned repo, executable.
    hook = repo / ".git" / "hooks" / "pre-push"
    assert hook.is_file()
    assert os.access(hook, os.X_OK)

    # 5. no export line, no "bound" claim.
    assert "export DADAIA_" not in result.stdout and "bound" not in result.stdout

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


def test_init_with_repo_is_idempotent_on_re_run(tmp_path: Path, origin: Path) -> None:
    """SPEC FR1 "idempotent on re-run" holds for `--repo` too: the second run of the
    identical command exits 0 and changes nothing."""
    workspace = tmp_path / "ws"
    argv = ["init", str(workspace), "--harness", "claude", "--skip-assets", "--repo", str(origin)]

    assert _runner.invoke(app, argv).exit_code == 0

    def _snapshot() -> dict[str, str]:
        return {
            str(path.relative_to(workspace)): path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(workspace.rglob("*"))
            if path.is_file() and ".dadaia/sessions" not in path.as_posix()
        }

    before = _snapshot()
    rerun = _runner.invoke(app, argv)

    assert rerun.exit_code == 0, rerun.stdout
    assert _snapshot() == before


def test_the_printed_fix_line_succeeds_once_the_url_is_reachable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `fix:` line a failed `--repo` prints (the venv's `context create`, the failing
    URL a placeholder — AC2.6) runs to success once the URL is reachable, never a stall
    that re-raises on the record the failed run left."""
    workspace = tmp_path / "ws"
    bare = tmp_path / "app.git"
    argv = ["init", str(workspace), "--harness", "claude", "--skip-assets", "--repo", str(bare)]

    failed = _runner.invoke(app, argv)
    assert failed.exit_code == 1
    fix = next(ln for ln in failed.output.splitlines() if ln.startswith("fix: "))
    assert fix == "fix: " + fix_line(workspace, "context", "create", "--main-repo", "<clone-url>")

    # The operator makes the URL reachable and re-runs the very same command.
    _git("init", "--bare", "--initial-branch=main", str(bare), cwd=tmp_path)
    work = tmp_path / "seed2"
    work.mkdir()
    _git("init", "--initial-branch=main", cwd=work)
    (work / "README.md").write_text("app\n", encoding="utf-8")
    _git("add", "README.md", cwd=work)
    _git("commit", "-m", "seed", cwd=work)
    _git("remote", "add", "origin", str(bare), cwd=work)
    _git("push", "origin", "main", cwd=work)

    monkeypatch.chdir(workspace)
    retry = _runner.invoke(app, ["context", "create", "--main-repo", str(bare)])

    assert retry.exit_code == 0, retry.output
    assert (workspace / "repos" / "app" / "README.md").read_text(encoding="utf-8") == "app\n"
    registry = json.loads(
        (workspace / ".dadaia" / "states" / "spec_contexts.json").read_text(encoding="utf-8")
    )
    assert [ctx["state"] for ctx in registry["contexts"] if ctx["name"] == "app"] == ["alive"]


def test_init_without_repo_closes_with_the_law_and_the_next_step(
    tmp_path: Path,
) -> None:
    """0.4.8 AC1.1 reshaped the 0.4.7 closing: the last line is the next step, run
    through the workspace's own venv CLI by absolute path (D2)."""
    ws = tmp_path / "ws"
    result = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])

    assert result.exit_code == 0, result.stdout
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    closing = lines[-3:]
    assert closing[0] == _LAW
    assert closing[1].startswith("Next (")  # the onboarding step, AC6.2
    assert closing[2].startswith(
        f"fix: {ws / '.dadaia' / '.venv' / 'bin' / 'dadaia'} context create"
    )
    assert _LAW not in "\n".join(lines[:-3])


def test_re_init_with_the_same_slug_but_another_url_refuses(tmp_path: Path, origin: Path) -> None:
    """Only a context holding THIS url is reused; the same slug from another origin is a
    different project and the re-run refuses with its fix line, the record untouched."""
    workspace = tmp_path / "ws"
    base = ["init", str(workspace), "--harness", "claude", "--skip-assets", "--repo"]
    assert _runner.invoke(app, [*base, str(origin)]).exit_code == 0
    imposter = tmp_path / "elsewhere" / "demo-project.git"
    imposter.parent.mkdir()
    _git("clone", "--bare", "-q", str(origin), str(imposter), cwd=tmp_path)

    rerun = _runner.invoke(app, [*base, str(imposter)])

    assert rerun.exit_code == 1, rerun.output
    assert len([line for line in rerun.output.splitlines() if line.startswith("fix: ")]) == 1
    registry = json.loads(
        (workspace / ".dadaia" / "states" / "spec_contexts.json").read_text(encoding="utf-8")
    )
    assert [ctx["repo_url"] for ctx in registry["contexts"]] == [str(origin)]
