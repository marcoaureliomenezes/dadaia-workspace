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
            if args[:3] == ["git", "config", "user.email"]:
                return _result(0, stdout="op@example.com\n")  # identity configured
            if "commit" in args:
                return _result(1, stdout="nothing to commit, working tree clean")
            return _result()

        monkeypatch.setattr(git_subprocess, "_run", fake_run)
        GitSubprocessClient().commit_all(Path("/repo"), "message")
        # Identity configured -> NO -c fallback injected (operator identity wins).
        assert ["git", "commit", "-m", "message"] in calls

    elif case == "commit-raises-with-stdout-and-stderr":

        def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            if "commit" in args:
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
    ("url", "allowed"),
    [
        pytest.param("ext::sh -c id", False, id="reject-ext-scheme"),
        pytest.param("-oProxyCommand=evil", False, id="reject-proxycommand-flag-injection"),
        pytest.param("--upload-pack=evil", False, id="reject-upload-pack-flag-injection"),
        pytest.param("https://github.com/o/r.git", True, id="allow-https"),
        pytest.param("ssh://git@github.com/o/r.git", True, id="allow-ssh-uri"),
        pytest.param("git@github.com:o/r.git", True, id="allow-ssh-scp-style"),
        pytest.param("/local/path/repo", True, id="allow-local-path"),
        pytest.param("file:///srv/repo", True, id="allow-file-scheme"),
    ],
)
def test_clone_url_scheme_accept_reject_matrix(
    url: str, allowed: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-05: clone() rejects non-https/ssh transports BEFORE invoking git (the ONLY
    coverage of the hostile-URL transport-injection reject matrix —
    ext::/ProxyCommand/upload-pack — never reduce this param list), and allows every
    legitimate https/ssh/local/file URL through to git."""
    ran = {"called": False}

    def _spy(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        ran["called"] = True
        return _result(0)

    monkeypatch.setattr(git_subprocess, "_run", _spy)

    if allowed:
        GitSubprocessClient().clone(url, tmp_path / "dest")  # must not raise
        assert ran["called"] is True
    else:
        with pytest.raises(GitCloneError):
            GitSubprocessClient().clone(url, tmp_path / "dest")
        assert ran["called"] is False, "git must not run for a disallowed URL"


# ── v0.4.3 T-043-14/FR10 — commit_paths is honest by construction ────────────────────
#
# Size: SMALL — pure unit tests on the ``git_subprocess._run`` seam. Intent: CONTRACT —
# v0.4.3 A10.1/A10.3. A10.2 (the operator-pre-staged-content exclusion, which needs a
# real index) is proven separately by a real-git integration fixture.


def test_commit_paths_raises_on_a_failed_git_add(monkeypatch: pytest.MonkeyPatch) -> None:
    """A10.1: a non-zero ``git add`` exit raises ``GitSyncError`` — a stage that did not
    happen must never silently become a commit."""
    calls: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ["git", "add"]:
            return _result(1, stderr="fatal: pathspec did not match any files")
        return _result()

    monkeypatch.setattr(git_subprocess, "_run", fake_run)

    with pytest.raises(GitSyncError, match="pathspec did not match"):
        GitSubprocessClient().commit_paths(Path("/repo"), "message", ["missing.txt"])

    # No commit was ever attempted once staging itself failed.
    assert not any("commit" in call for call in calls)


def test_commit_paths_applies_literal_pathspec_magic_to_add_and_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A10.3: the pathspec-magic defence (``:(literal)``) is applied to every path on
    BOTH the ``git add`` and the path-scoped ``git commit -- <paths>`` — a path
    containing a pathspec-magic character (``:``, ``*``, ``!``, …) must never be
    reinterpreted as a glob/exclude pattern."""
    calls: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:3] == ["git", "config", "user.email"]:
            return _result(0, stdout="op@example.com\n")
        return _result()

    monkeypatch.setattr(git_subprocess, "_run", fake_run)

    GitSubprocessClient().commit_paths(Path("/repo"), "message", ["AGENTS.md", "tests/AGENTS.md"])

    add_call = next(c for c in calls if c[:2] == ["git", "add"])
    assert add_call == ["git", "add", "--", ":(literal)AGENTS.md", ":(literal)tests/AGENTS.md"]

    commit_call = next(c for c in calls if "commit" in c)
    # A10.2: the commit itself is path-scoped (never a bare `git commit -m <msg>`).
    assert commit_call[-3:] == ["--", ":(literal)AGENTS.md", ":(literal)tests/AGENTS.md"]


def test_commit_paths_is_a_noop_for_an_empty_path_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        git_subprocess, "_run", lambda args, cwd=None: (calls.append(args), _result())[1]
    )

    GitSubprocessClient().commit_paths(Path("/repo"), "message", [])

    assert calls == []


# ── v0.4.3 T-043-23 security-review rework — _stage_files_safe hardening ─────────────
#
# Size: SMALL — pure unit tests on the ``git_subprocess._run`` seam, mirroring the
# A10.1/A10.3 pattern already proven above for `commit_paths`. Intent: CONTRACT.
# `_stage_files_safe` (used by `commit_all`) carried NEITHER of those two defences —
# security-reviewer LOW finding FR10, handoff
# 2026-08-17T173112Z-security-reviewer-v0.4.3-alpha-2-delta.


def test_stage_files_safe_raises_on_a_failed_git_add_dash_u(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-zero ``git add -u`` exit raises ``GitSyncError`` — a stage that did not
    happen must never silently become (part of) a ``commit_all`` commit, the same
    class A10.1 already covers for ``commit_paths``."""
    calls: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["git", "add", "-u"]:
            return _result(1, stderr="fatal: not a git repository")
        return _result()

    monkeypatch.setattr(git_subprocess, "_run", fake_run)

    with pytest.raises(GitSyncError, match="not a git repository"):
        git_subprocess._stage_files_safe(Path("/repo"))

    # No untracked-file discovery/staging was ever attempted once -u itself failed.
    assert not any(c[:3] == ["git", "ls-files", "--others"] for c in calls)


def test_stage_files_safe_raises_on_a_failed_git_add_for_untracked_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-zero exit staging the discovered untracked paths raises ``GitSyncError``
    — the second ``git add`` call gets the same A10.1 treatment as the first."""

    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if args == ["git", "add", "-u"]:
            return _result(0)
        if args[:3] == ["git", "ls-files", "--others"]:
            return _result(0, stdout="new-file.txt\n")
        if args[:2] == ["git", "add"]:
            return _result(1, stderr="fatal: pathspec did not match any files")
        return _result()

    monkeypatch.setattr(git_subprocess, "_run", fake_run)

    with pytest.raises(GitSyncError, match="pathspec did not match"):
        git_subprocess._stage_files_safe(Path("/repo"))


def test_stage_files_safe_applies_literal_pathspec_magic_to_untracked_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every untracked path is wrapped in ``:(literal)`` before it reaches ``git add``
    — the SAME defence ``commit_paths`` already applies (A10.3) — so a filename that
    happens to look like pathspec magic (e.g. ``:(exclude)specs``) is staged as the
    literal file it names, never reinterpreted."""
    calls: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["git", "add", "-u"]:
            return _result(0)
        if args[:3] == ["git", "ls-files", "--others"]:
            return _result(0, stdout="normal.txt\n:(exclude)specs\n")
        return _result(0)

    monkeypatch.setattr(git_subprocess, "_run", fake_run)

    git_subprocess._stage_files_safe(Path("/repo"))

    add_call = next(c for c in calls if c[:2] == ["git", "add"] and c != ["git", "add", "-u"])
    assert add_call == [
        "git",
        "add",
        "--",
        ":(literal)normal.txt",
        ":(literal):(exclude)specs",
    ]
