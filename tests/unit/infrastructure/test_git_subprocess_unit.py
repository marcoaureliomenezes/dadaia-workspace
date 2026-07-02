"""Pure unit tests for GitSubprocessClient command decisions."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError
from dadaia_workspace.infrastructure import git_subprocess
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient


def _result(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["git"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_clone_raises_git_clone_error_with_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        git_subprocess, "_run", lambda *_args, **_kwargs: _result(1, stderr="fatal")
    )

    with pytest.raises(GitCloneError, match="fatal"):
        GitSubprocessClient().clone("https://github.com/o/missing.git", Path("/dest"))


def test_commit_all_treats_nothing_to_commit_as_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ["git", "commit"]:
            return _result(1, stdout="nothing to commit, working tree clean")
        return _result()

    monkeypatch.setattr(git_subprocess, "_run", fake_run)

    GitSubprocessClient().commit_all(Path("/repo"), "message")

    assert ["git", "commit", "-m", "message"] in calls


def test_commit_all_raises_with_stdout_and_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["git", "commit"]:
            return _result(1, stdout="stdout detail", stderr="stderr detail")
        return _result()

    monkeypatch.setattr(git_subprocess, "_run", fake_run)

    with pytest.raises(GitSyncError) as exc_info:
        GitSubprocessClient().commit_all(Path("/repo"), "message")

    assert "stdout detail" in str(exc_info.value)
    assert "stderr detail" in str(exc_info.value)


def test_push_sets_upstream_when_tracking_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["git", "rev-parse", "--abbrev-ref", "@{u}"]:
            return _result(1)
        if args == ["git", "branch", "--show-current"]:
            return _result(stdout="main\n")
        return _result()

    monkeypatch.setattr(git_subprocess, "_run", fake_run)

    GitSubprocessClient().push(Path("/repo"))

    assert ["git", "push", "-u", "origin", "main"] in calls


def test_push_uses_explicit_refspec_when_tracking_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """v0.1.50 FR3: tracking set ⇒ rev-list ahead-check, then push <remote> HEAD:<branch>."""
    calls: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if "--abbrev-ref" in args:
            return _result(stdout="origin/main\n")
        if "rev-list" in args:
            return _result(stdout="1\n")
        return _result(stdout="")

    monkeypatch.setattr(git_subprocess, "_run", fake_run)

    GitSubprocessClient().push(Path("/repo"))

    assert ["git", "push", "origin", "HEAD:main"] in calls
    assert not any(call[:3] == ["git", "push", "-u"] for call in calls)
    assert ["git", "push"] not in calls


def test_checkout_raises_sync_error_on_git_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        git_subprocess, "_run", lambda *_args, **_kwargs: _result(1, stderr="no branch")
    )

    with pytest.raises(GitSyncError, match="no branch"):
        GitSubprocessClient().checkout(Path("/repo"), "missing")


@pytest.mark.parametrize(
    "bad_url",
    ["ext::sh -c id", "-oProxyCommand=evil", "--upload-pack=evil"],
)
def test_clone_rejects_disallowed_url_scheme(
    bad_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-05: clone() rejects non-https/ssh transports BEFORE invoking git."""
    ran = {"called": False}

    def _spy(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        ran["called"] = True
        return _result(0)

    monkeypatch.setattr(git_subprocess, "_run", _spy)

    with pytest.raises(GitCloneError):
        GitSubprocessClient().clone(bad_url, tmp_path / "dest")

    assert ran["called"] is False, "git must not run for a disallowed URL"


@pytest.mark.parametrize(
    "ok_url",
    [
        "https://github.com/o/r.git",
        "ssh://git@github.com/o/r.git",
        "git@github.com:o/r.git",
        "/local/path/repo",
        "file:///srv/repo",
    ],
)
def test_clone_allows_network_url_schemes(
    ok_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Allowed https/ssh URLs pass validation and reach git."""
    monkeypatch.setattr(git_subprocess, "_run", lambda *_a, **_k: _result(0))
    GitSubprocessClient().clone(ok_url, tmp_path / "dest")  # must not raise
