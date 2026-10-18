"""The pre-push shim finds the dadaia runner, in this order, and fails closed with none:

  walk UP from the repo root to ``<ws>/.dadaia/.venv/<scripts>/dadaia`` (either host's layout)

``--probe-only`` prints the resolved runner and exits 0; every other run hands git's ref lines
and the ``ci push-gate-check`` verb to it. Each test drives the real shim through Git Bash in a
real git repo; the runner is a stub.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

import dadaia_workspace
from tests.fixtures.harness_env import git_bash, suite_env
from tests.helpers.oslib import detect, make_executable, run, stub_cli, venv_tool, write_text

GATE_SCRIPT = Path(dadaia_workspace.__file__).parent / "public" / "scripts" / "pre-push-ci-gate.sh"
_ZERO = "0" * 40


def _repo(path: Path) -> Path:
    path.mkdir(parents=True)
    run(["git", "init", "-q"], cwd=path, check=True)
    return path


def _runner(venv: Path, source: str = "#!python\n") -> Path:
    """A stub `dadaia` in *venv*'s scripts directory, as pip places a console script."""
    directory = venv_tool(venv, "dadaia").parent
    directory.mkdir(parents=True)
    return stub_cli(directory, "dadaia", source)


def _shim(repo: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    env = suite_env(os.environ, repo)
    return run([git_bash(), str(GATE_SCRIPT), *args], cwd=repo, input=stdin, env=env, timeout=60)


@pytest.mark.parametrize("name", ["walk_up_to_workspace_venv", "repo_local_venv"])
def test_runner_resolution_branch_table(tmp_path: Path, name: str) -> None:
    if name == "walk_up_to_workspace_venv":
        ws = tmp_path / "ws"
        repo = _repo(ws / "repos" / "slug")
        runner = _runner(ws / ".dadaia" / ".venv")
        res = _shim(repo, "--probe-only")
        assert res.returncode == 0, res.stderr
        assert "workspace-venv" in res.stdout
        assert runner.as_posix() in res.stdout
        assert "poetry" not in res.stdout
        return

    repo = _repo(tmp_path / "repo-with-local-venv")
    _runner(repo / ".venv")
    res = _shim(repo, "--probe-only")
    assert res.returncode == 1, res.stdout
    assert "could not locate the dadaia runner" in res.stderr


def test_a_runner_planted_in_the_repo_is_never_run_ahead_of_the_workspace_venv(
    tmp_path: Path,
) -> None:
    """A `<repo>/.dadaia/.venv` runner committed in the repo loses to the workspace venv above it."""
    ws = tmp_path / "ws"
    repo = _repo(ws / "repos" / "slug")
    runner = _runner(ws / ".dadaia" / ".venv")
    marker = tmp_path / "planted-ran"
    _runner(repo / ".dadaia" / ".venv", f"#!python\nopen({str(marker)!r}, 'w').close()\n")
    probe = _shim(repo, "--probe-only")
    assert probe.returncode == 0, probe.stderr
    assert runner.as_posix() in probe.stdout
    res = _shim(
        repo, stdin=f"refs/heads/feature/0.0.1 {'a' * 40} refs/heads/feature/0.0.1 {_ZERO}\n"
    )
    assert res.returncode == 0, res.stderr
    assert not marker.exists()


def test_the_other_hosts_layout_is_probed_too(tmp_path: Path) -> None:
    """A venv built on the other OS (a workspace shared across hosts) still resolves."""
    other = detect("linux" if detect().windows else "win32")
    runner = venv_tool(tmp_path / "ws" / ".dadaia" / ".venv", "dadaia", other)
    runner.parent.mkdir(parents=True)
    write_text(runner, "#!/bin/sh\n")
    make_executable(runner)
    res = _shim(_repo(tmp_path / "ws" / "repos" / "slug"), "--probe-only")
    assert res.returncode == 0, res.stderr
    assert runner.as_posix() in res.stdout


def test_a_runner_on_path_is_not_a_runner(tmp_path: Path) -> None:
    """Only the venvs are probed: a `dadaia` anywhere on PATH leaves the gate closed."""
    (tmp_path / "bin").mkdir()
    stub_cli(tmp_path / "bin", "dadaia", "#!python\n")
    repo = _repo(tmp_path / "repo")
    env = suite_env(
        os.environ, repo, overrides={"PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"}
    )
    res = run([git_bash(), str(GATE_SCRIPT), "--probe-only"], cwd=repo, env=env, timeout=60)
    assert res.returncode == 1, res.stdout
    assert "could not locate the dadaia runner" in res.stderr


@pytest.mark.parametrize("code", [0, 1])
def test_the_shim_hands_the_ref_lines_to_the_push_gate_and_returns_its_exit(
    tmp_path: Path, code: int
) -> None:
    seen = tmp_path / "seen"
    source = (
        "#!python\nimport pathlib, sys\n"
        f"pathlib.Path({str(seen)!r}).write_bytes((' '.join(sys.argv[1:]) + '|' + sys.stdin.read()).encode())\n"
        f"sys.exit({code})\n"
    )
    repo = _repo(tmp_path / "ws" / "repos" / "slug")
    _runner(tmp_path / "ws" / ".dadaia" / ".venv", source)
    refs = f"refs/heads/feature/0.0.1 {'a' * 40} refs/heads/feature/0.0.1 {_ZERO}\n"
    res = _shim(repo, stdin=refs)
    assert res.returncode == code, res.stderr
    assert seen.read_bytes().decode() == f"ci push-gate-check|{refs}"
