"""The real `ci install-hook` + a real `git push` to a local bare remote. The planted-term
refuse -> amend -> push journey is the refusal harness Case `denylisted`; the refusal message
shape (masking) is pinned by the denylist scan's own tests.
The hook's runner is a `dadaia` console-script stub (`stub_cli`) in the workspace venv, forwarding to this interpreter's CLI.
Size: LARGE — real git hooks.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import suite_env
from tests.helpers.oslib import run, stub_cli, venv_dir, venv_tool, write_text

pytestmark = pytest.mark.e2e

_SLUG = "denylist-journey"
_BRANCH = "feature/0.0.1"
_EXIT_DEADLINE = 30.0
_PLANTED_TERM = "zz-fake-context-name"  # synthetic — never a real term


def _git(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    run(["git", *args], cwd=cwd, check=True, env=env)


def _init_repo_and_remote(workspace: Path, slug: str) -> tuple[Path, Path]:
    """A throwaway working repo on a pushable branch plus a local bare remote (no
    network)."""
    bare = workspace / "remote.git"
    bare.mkdir(parents=True)
    _git(["init", "--bare", "-q"], bare)

    repo = workspace / "repos" / slug
    repo.mkdir(parents=True)
    _git(["init", "-q", "-b", _BRANCH], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    _git(["remote", "add", "origin", str(bare)], repo)
    return repo, bare


def _write_dadaia_stub(workspace: Path, python_exe: str) -> None:
    """The workspace venv CLI the installed hook finds by its walk up from the repo:
    forwards to the REAL CLI through this interpreter, stdin included."""
    directory = venv_tool(venv_dir(workspace), "dadaia").parent
    directory.mkdir(parents=True)
    source = (
        "#!python\nimport os, sys\n"
        f"argv = [{python_exe!r}, '-m', 'dadaia_workspace.cli.main', *sys.argv[1:]]\n"
        "sys.exit(os.spawnv(os.P_WAIT, argv[0], argv))\n"
    )
    stub_cli(directory, "dadaia", source, Path(python_exe))


def _write_denylist_file(workspace: Path) -> Path:
    path = workspace / "privacy_denylist.json"
    write_text(path, json.dumps({_PLANTED_TERM: "planted e2e term (synthetic)"}))
    return path


def _push(repo: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return run(
        ["git", "push", "origin", f"{_BRANCH}:{_BRANCH}"], cwd=repo, env=env, timeout=_EXIT_DEADLINE
    )


def _remote_branch_sha(bare: Path) -> str | None:
    result = run(["git", "rev-parse", "--verify", f"refs/heads/{_BRANCH}"], cwd=bare)
    return result.stdout.strip() if result.returncode == 0 else None


def test_the_gate_runs_where_core_hookspath_points(tmp_path: Path) -> None:
    """With ``core.hooksPath`` set, ``ci install-hook`` puts the gate where git runs hooks, and a
    push carrying an AKIA-shaped key is refused. Composed at runtime — never a tracked secret
    literal."""
    repo, bare = _init_repo_and_remote(tmp_path, _SLUG)
    _git(["config", "core.hooksPath", ".husky"], repo)
    write_text(repo / "creds.txt", "key " + "AKIA" + "Q" * 16 + "\n")
    _git(["add", "creds.txt"], repo)
    _git(["commit", "-q", "-m", "seed"], repo)
    result = run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", "ci", "install-hook"],
        cwd=repo,
        timeout=_EXIT_DEADLINE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".husky" / "pre-push").is_file()

    _write_dadaia_stub(tmp_path, sys.executable)
    env = suite_env(os.environ, Path.home()) | {
        "DADAIA_PRIVACY_DENYLIST": str(_write_denylist_file(tmp_path))
    }
    refused = _push(repo, env)

    assert refused.returncode != 0, refused.stdout + refused.stderr
    assert _remote_branch_sha(bare) is None


def test_a_record_whose_context_carries_a_published_term_registers_and_pushes(
    tmp_path: Path,
) -> None:
    """A context value origin already holds is accepted by the ledger seam AND by the installed
    pre-push."""
    from tests.helpers.skill_scripts import stage_skill_scripts

    bugs = stage_skill_scripts("dd-bug-resolution", tmp_path / "staged" / "scripts") / "bugs.py"
    repo, bare = _init_repo_and_remote(tmp_path, _SLUG)
    (repo / "cli").mkdir()
    write_text(repo / "cli" / "x.py", "x = 1\n")
    (repo / "specs" / "bugs").mkdir(parents=True)
    write_text(repo / "specs" / "bugs" / "BUGS.jsonl", "")
    _git(["add", "cli"], repo)
    env = suite_env(os.environ, Path.home())

    def register(bug_id: str, run_env: dict[str, str]) -> None:
        done = run([sys.executable, str(bugs), "append", "--specs", str(repo / "specs"),
             "--bug-id", bug_id, "--reported-by", "t", "--title", "t", "--severity", "LOW",
             "--surface", "cli", "--component", "c", "--context", f"{_PLANTED_TERM}-games",
             "--symptom", "s", "--repro", "r", "--expected", "e", "--correlates", "none"], cwd=repo, env=run_env, timeout=_EXIT_DEADLINE)  # fmt: skip
        assert done.returncode == 0, done.stderr
        _git(["add", "-A"], repo)
        _git(["commit", "-q", "-m", bug_id], repo)

    register("published", env)
    _git(["push", "-q", "origin", f"{_BRANCH}:{_BRANCH}"], repo)  # published before any gate
    env |= {"DADAIA_PRIVACY_DENYLIST": str(_write_denylist_file(tmp_path))}
    register("second", env)  # unpublished, committed before any hook is installed
    installed = run([sys.executable, "-m", "dadaia_workspace.cli.main", "ci", "install-hook"], cwd=repo, timeout=_EXIT_DEADLINE)  # fmt: skip
    assert installed.returncode == 0, installed.stdout + installed.stderr
    _write_dadaia_stub(tmp_path, sys.executable)
    pushed = _push(repo, env)

    assert pushed.returncode == 0, pushed.stdout + pushed.stderr
    head = run(["git", "rev-parse", "HEAD"], cwd=repo)
    assert _remote_branch_sha(bare) == head.stdout.strip()
