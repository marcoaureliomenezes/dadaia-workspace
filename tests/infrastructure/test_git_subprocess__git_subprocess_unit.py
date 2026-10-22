"""GitSubprocessClient decisions at the kernel ``_git.git_bytes`` seam; real-git behavior
lives in ``tests/infrastructure/test_git_subprocess.py``.

Clone transport reject matrix and the ``_stage_files_safe`` hardening.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

Reply = Callable[[list[str]], "subprocess.CompletedProcess[bytes] | None"]


def _result(rc: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(["git"], rc, stdout=stdout.encode(), stderr=stderr.encode())


def _fake(monkeypatch: pytest.MonkeyPatch, reply: Reply) -> list[list[str]]:
    """Route ``_git.git_bytes`` to *reply* (None = success) and record every argv, `git` first."""
    calls: list[list[str]] = []

    def run(repo: Path, *args: str, **_: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(["git", *args])
        return reply(["git", *args]) or _result()

    monkeypatch.setattr(load_owner("dd-bug-resolution", "_git"), "git_bytes", run)
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
    """A hostile transport is refused BEFORE git runs (never reduce this list)."""
    calls = _fake(monkeypatch, lambda args: None)
    if allowed:
        GitSubprocessClient().clone(url, tmp_path / "dest")
    else:
        with pytest.raises(GitCloneError):
            GitSubprocessClient().clone(url, tmp_path / "dest")
    assert bool(calls) is allowed


def _commit_paths(repo: Path) -> None:
    GitSubprocessClient().commit_paths(repo, "message", ["missing.txt"])


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
            _commit_paths,
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

    def reply(args: list[str]) -> subprocess.CompletedProcess[bytes] | None:
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
    ],
)
def test_every_path_is_staged_and_committed_as_a_literal_pathspec(
    monkeypatch: pytest.MonkeyPatch, act: Callable[[Path], None], untracked: str, paths: list[str]
) -> None:
    """A name that looks like pathspec magic is never reinterpreted."""
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
    assert commit[-len(literal) - 1 :] == ["--", *literal]


def test_commit_paths_is_a_noop_for_an_empty_path_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake(monkeypatch, lambda args: None)
    GitSubprocessClient().commit_paths(Path("/repo"), "message", [])
    assert calls == []


@pytest.mark.parametrize("url", ["--upload-pack=evil", "-oProxyCommand=evil", "ext::sh -c id"])
def test_reachable_refuses_a_hostile_url_before_git_runs(
    url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _fake(monkeypatch, lambda args: None)

    assert GitSubprocessClient().reachable(url) is False
    assert calls == []


def test_reachable_probes_with_the_url_after_the_options_end_and_nothing_to_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, object]] = []

    def run(repo: Path, *args: str, **kw: object) -> subprocess.CompletedProcess[bytes]:
        seen.append({"args": list(args), **kw})
        return _result()

    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)
    monkeypatch.delenv("GIT_SSH", raising=False)
    monkeypatch.setattr(load_owner("dd-bug-resolution", "_git"), "git_bytes", run)

    assert GitSubprocessClient().reachable("https://example.invalid/o/r.git") is True

    [config, call] = seen
    assert config["args"] == ["config", "core.sshCommand"]
    assert call["args"] == ["ls-remote", "--heads", "--", "https://example.invalid/o/r.git"]
    assert call["input"] == b""
    assert isinstance(call["timeout"], int | float)
    env = call["env"]
    assert isinstance(env, dict)
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert "BatchMode=yes" in env["GIT_SSH_COMMAND"]


@pytest.mark.parametrize(
    "failure", [subprocess.TimeoutExpired("git", 1), OSError("no git")], ids=["timeout", "no-git"]
)
def test_reachable_counts_a_timeout_or_a_missing_git_as_unreachable(
    failure: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(repo: Path, *args: str, **_: object) -> subprocess.CompletedProcess[bytes]:
        raise failure

    monkeypatch.setattr(load_owner("dd-bug-resolution", "_git"), "git_bytes", run)

    assert GitSubprocessClient().reachable("https://example.invalid/o/r.git") is False


def test_reachable_is_false_when_git_cannot_list_the_remote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake(monkeypatch, lambda args: _result(rc=128, stderr="fatal: unable to access"))

    assert GitSubprocessClient().reachable("https://example.invalid/o/r.git") is False
