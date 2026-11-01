"""The pre-push gate fails closed: with no dadaia runner anywhere, ``pre-push-ci-gate.sh``
refuses the push (exit 1), never skips it. The shim is driven through Git Bash in a real repo.

The invalid-branch and denylist refusals are proven at the real CLI boundary by the e2e
journeys in ``tests/e2e/``; this module adds no duplicate coverage of them.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import os
from pathlib import Path

import dadaia_workspace
from tests.fixtures.harness_env import git_bash, suite_env
from tests.helpers.oslib import run, stub_cli, venv_tool

_PRE_PUSH_SCRIPT = (
    Path(dadaia_workspace.__file__).parent / "public" / "scripts" / "pre-push-ci-gate.sh"
)
_ZERO = "0" * 40

#: Synthetic git identity on an RFC-2606 reserved domain, which privacy_baseline.json excludes.
_SYNTHETIC_GIT_EMAIL = "test@example.invalid"


def test_unresolvable_runner_still_refuses_the_push(tmp_path: Path) -> None:
    """With no workspace venv and no repo-local venv, ``pre-push-ci-gate.sh`` refuses the
    push (exit 1), never skips it. Pre-push keeps fail-closed runner resolution."""
    repo = tmp_path / "isolated-repo"
    repo.mkdir(parents=True)
    run(["git", "init", "-q"], cwd=repo, check=True)
    run(["git", "config", "user.email", _SYNTHETIC_GIT_EMAIL], cwd=repo, check=True)
    run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    stdin_text = f"refs/heads/feature/0.0.1 {'a' * 40} refs/heads/feature/0.0.1 {_ZERO}\n"
    result = run(
        [git_bash(), str(_PRE_PUSH_SCRIPT)],
        cwd=repo,
        input=stdin_text,
        env=suite_env(os.environ, repo),
        timeout=30,
    )
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert "could not locate the dadaia runner" in out, out


def test_the_repos_own_venv_runner_is_never_run(tmp_path: Path) -> None:
    """A planted `<repo>/.venv` runner with no workspace venv above is not run: the push is refused."""
    repo = tmp_path / "isolated-repo"
    repo.mkdir(parents=True)
    run(["git", "init", "-q"], cwd=repo, check=True)
    marker = tmp_path / "planted-ran"
    directory = venv_tool(repo / ".venv", "dadaia").parent
    directory.mkdir(parents=True)
    stub_cli(directory, "dadaia", f"#!python\nopen({str(marker)!r}, 'w').close()\n")

    stdin_text = f"refs/heads/feature/0.0.1 {'a' * 40} refs/heads/feature/0.0.1 {_ZERO}\n"
    result = run(
        [git_bash(), str(_PRE_PUSH_SCRIPT)],
        cwd=repo,
        input=stdin_text,
        env=suite_env(os.environ, repo),
        timeout=30,
    )
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert "could not locate the dadaia runner" in out, out
    assert not marker.exists()
