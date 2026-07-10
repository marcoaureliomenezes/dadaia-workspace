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


@pytest.mark.parametrize(
    "case",
    [
        "clone-error-with-stderr",
        "commit-noop-on-nothing-to-commit",
        "commit-raises-with-stdout-and-stderr",
        "checkout-raises-sync-error",
    ],
)
def test_error_and_noop_mapping(monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """Error-mapping matrix: a failing clone/commit/checkout maps to the
    domain-specific exception carrying stdout/stderr detail, while a commit whose
    only failure is 'nothing to commit' is treated as a no-op, not an error."""
    if case == "clone-error-with-stderr":
        monkeypatch.setattr(
            git_subprocess, "_run", lambda *_args, **_kwargs: _result(1, stderr="fatal")
        )
        with pytest.raises(GitCloneError, match="fatal"):
            GitSubprocessClient().clone("https://github.com/o/missing.git", Path("/dest"))

    elif case == "commit-noop-on-nothing-to-commit":
        calls: list[list[str]] = []

        def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            if args[:2] == ["git", "commit"]:
                return _result(1, stdout="nothing to commit, working tree clean")
            return _result()

        monkeypatch.setattr(git_subprocess, "_run", fake_run)
        GitSubprocessClient().commit_all(Path("/repo"), "message")
        assert ["git", "commit", "-m", "message"] in calls

    elif case == "commit-raises-with-stdout-and-stderr":

        def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            if args[:2] == ["git", "commit"]:
                return _result(1, stdout="stdout detail", stderr="stderr detail")
            return _result()

        monkeypatch.setattr(git_subprocess, "_run", fake_run)
        with pytest.raises(GitSyncError) as exc_info:
            GitSubprocessClient().commit_all(Path("/repo"), "message")
        assert "stdout detail" in str(exc_info.value)
        assert "stderr detail" in str(exc_info.value)

    else:  # checkout-raises-sync-error
        monkeypatch.setattr(
            git_subprocess, "_run", lambda *_args, **_kwargs: _result(1, stderr="no branch")
        )
        with pytest.raises(GitSyncError, match="no branch"):
            GitSubprocessClient().checkout(Path("/repo"), "missing")


def test_push_argv_contract_upstream_vs_explicit_refspec(monkeypatch: pytest.MonkeyPatch) -> None:
    """No tracking branch -> sets upstream (-u origin <branch>); tracking already
    set (v0.1.50 FR3) -> rev-list ahead-check then explicit push <remote> HEAD:<branch>,
    never re-running -u nor a bare `git push`."""
    upstream_calls: list[list[str]] = []

    def fake_run_no_upstream(
        args: list[str], cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        upstream_calls.append(args)
        if args == ["git", "rev-parse", "--abbrev-ref", "@{u}"]:
            return _result(1)
        if args == ["git", "branch", "--show-current"]:
            return _result(stdout="main\n")
        return _result()

    monkeypatch.setattr(git_subprocess, "_run", fake_run_no_upstream)
    GitSubprocessClient().push(Path("/repo"))
    assert ["git", "push", "-u", "origin", "main"] in upstream_calls

    refspec_calls: list[list[str]] = []

    def fake_run_with_upstream(
        args: list[str], cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        refspec_calls.append(args)
        if "--abbrev-ref" in args:
            return _result(stdout="origin/main\n")
        if "rev-list" in args:
            return _result(stdout="1\n")
        return _result(stdout="")

    monkeypatch.setattr(git_subprocess, "_run", fake_run_with_upstream)
    GitSubprocessClient().push(Path("/repo"))
    assert ["git", "push", "origin", "HEAD:main"] in refspec_calls
    assert not any(call[:3] == ["git", "push", "-u"] for call in refspec_calls)
    assert ["git", "push"] not in refspec_calls


@pytest.mark.parametrize(
    "bad_url",
    ["ext::sh -c id", "-oProxyCommand=evil", "--upload-pack=evil"],
)
def test_clone_rejects_disallowed_url_scheme(
    bad_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-05: clone() rejects non-https/ssh transports BEFORE invoking git. This is
    the ONLY coverage of the hostile-URL transport-injection reject matrix
    (ext::/ProxyCommand/upload-pack) — never reduce this param list."""
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
