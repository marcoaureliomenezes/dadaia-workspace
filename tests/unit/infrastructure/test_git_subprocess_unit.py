"""GitSubprocessClient decisions at the ``git_subprocess._run`` seam; real-git behavior
lives in ``tests/integration/infrastructure/test_git_subprocess.py``.

Intent: CONTRACT — F-05 (clone transport reject matrix); v0.4.3 A10.1, A10.3 and the
T-043-23 ``_stage_files_safe`` hardening.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError
from dadaia_workspace.infrastructure import git_subprocess
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

Reply = Callable[[list[str]], "subprocess.CompletedProcess[str] | None"]


def _result(rc: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], rc, stdout=stdout, stderr=stderr)


def _fake(monkeypatch: pytest.MonkeyPatch, reply: Reply) -> list[list[str]]:
    """Route ``_run`` to *reply* (None = success) and record every argv."""
    calls: list[list[str]] = []

    def run(
        args: list[str], cwd: Path | None = None, **_: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return reply(args) or _result()

    monkeypatch.setattr(git_subprocess, "_run", run)
    return calls


@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        pytest.param("ext::sh -c id", False, id="reject-ext-scheme"),
        pytest.param("-oProxyCommand=evil", False, id="reject-proxycommand-flag-injection"),
        pytest.param("--upload-pack=evil", False, id="reject-upload-pack-flag-injection"),
        pytest.param("https://github.com/o/r.git", True, id="allow-https"),
        pytest.param("ssh://git@example.invalid/o/r.git", True, id="allow-ssh-uri"),
        pytest.param("git@example.invalid:o/r.git", True, id="allow-ssh-scp-style"),
        pytest.param("/local/path/repo", True, id="allow-local-path"),
        pytest.param("file:///srv/repo", True, id="allow-file-scheme"),
    ],
)
def test_clone_url_scheme_accept_reject_matrix(
    url: str, allowed: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-05: a hostile transport is refused BEFORE git runs (never reduce this list)."""
    calls = _fake(monkeypatch, lambda args: None)
    if allowed:
        GitSubprocessClient().clone(url, tmp_path / "dest")
    else:
        with pytest.raises(GitCloneError):
            GitSubprocessClient().clone(url, tmp_path / "dest")
    assert bool(calls) is allowed


def _commit_paths(repo: Path) -> None:
    GitSubprocessClient().commit_paths(repo, "message", ["missing.txt"])


def _commit_all(repo: Path) -> None:
    GitSubprocessClient().commit_all(repo, "message")


@pytest.mark.parametrize(
    ("act", "failing", "untracked", "match", "never"),
    [
        pytest.param(
            _commit_paths,
            ["git", "add"],
            "",
            "pathspec did not match",
            "commit",
            id="A10.1-commit-paths-add",
        ),
        pytest.param(
            _commit_all,
            ["git", "add", "-u"],
            "",
            "pathspec did not match",
            "ls-files",
            id="stage-add-dash-u",
        ),
        pytest.param(
            _commit_all,
            ["git", "add", "--"],
            "new.txt\0",
            "pathspec did not match",
            "commit",
            id="stage-untracked-add",
        ),
        pytest.param(
            _commit_all,
            ["git", "commit"],
            "",
            "stdout detail.*stderr detail",
            None,
            id="commit-carries-stdout-and-stderr",
        ),
    ],
)
def test_a_failed_git_step_raises_and_nothing_after_it_runs(
    monkeypatch: pytest.MonkeyPatch,
    act: Callable[[Path], None],
    failing: list[str],
    untracked: str,
    match: str,
    never: str | None,
) -> None:
    """A stage that did not happen never silently becomes a commit."""

    def reply(args: list[str]) -> subprocess.CompletedProcess[str] | None:
        if args[: len(failing)] == failing:
            return _result(1, "stdout detail", "stderr detail fatal: pathspec did not match")
        if args[:3] == ["git", "ls-files", "--others"]:
            return _result(stdout=untracked)
        return None

    calls = _fake(monkeypatch, reply)
    with pytest.raises(GitSyncError, match=match):
        act(Path("/repo"))
    after = calls[[c[: len(failing)] for c in calls].index(failing) + 1 :]
    assert never is None or not any(never in call for call in after)


@pytest.mark.parametrize(
    ("act", "untracked", "paths"),
    [
        pytest.param(
            lambda repo: GitSubprocessClient().commit_paths(
                repo, "m", ["AGENTS.md", "tests/AGENTS.md"]
            ),
            "",
            ["AGENTS.md", "tests/AGENTS.md"],
            id="A10.3-commit-paths",
        ),
        pytest.param(
            _commit_all,
            "normal.txt\0:(exclude)specs\0",
            ["normal.txt", ":(exclude)specs"],
            id="stage-files-safe-untracked",
        ),
    ],
)
def test_every_path_is_staged_and_committed_as_a_literal_pathspec(
    monkeypatch: pytest.MonkeyPatch, act: Callable[[Path], None], untracked: str, paths: list[str]
) -> None:
    """A10.3: a name that looks like pathspec magic is never reinterpreted."""
    calls = _fake(
        monkeypatch,
        lambda args: (
            _result(stdout=untracked) if args[:3] == ["git", "ls-files", "--others"] else None
        ),
    )
    act(Path("/repo"))
    literal = [f":(literal){p}" for p in paths]
    assert ["git", "add", "--", *literal] in calls
    commit = next(c for c in calls if "commit" in c)
    assert act is _commit_all or commit[-len(literal) - 1 :] == ["--", *literal]


def test_commit_paths_is_a_noop_for_an_empty_path_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake(monkeypatch, lambda args: None)
    GitSubprocessClient().commit_paths(Path("/repo"), "message", [])
    assert calls == []
