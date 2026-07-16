"""commit_all must work in environments with no git identity (validation-029 F-06).

A consumer container/CI runner often has no user.name/user.email configured; dead()'s
auto-commit then died with GitSyncError ('Please tell me who you are') and a raw
traceback. Tool-authored commits fall back to a deterministic tool identity; an
operator-configured identity, when present, is respected.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient


def _git(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)


def test_commit_all_falls_back_to_tool_identity(tmp_path: Path, monkeypatch) -> None:
    # Isolate from ANY global/system git identity.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global-config"))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    monkeypatch.delenv("GIT_AUTHOR_NAME", raising=False)
    monkeypatch.delenv("GIT_AUTHOR_EMAIL", raising=False)
    monkeypatch.delenv("GIT_COMMITTER_NAME", raising=False)
    monkeypatch.delenv("GIT_COMMITTER_EMAIL", raising=False)

    import os

    env = os.environ.copy()
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(["init", "-q"], repo, env).returncode == 0
    (repo / "x.txt").write_text("x")

    GitSubprocessClient().commit_all(repo, "chore: tool commit without identity")

    log = _git(["log", "-1", "--format=%an <%ae> %s"], repo, env)
    assert log.returncode == 0
    assert "tool commit without identity" in log.stdout


def test_commit_all_respects_configured_identity(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global-config"))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")

    import os

    env = os.environ.copy()
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(["init", "-q"], repo, env).returncode == 0
    _git(["config", "user.name", "Operator"], repo, env)
    _git(["config", "user.email", "op@example.com"], repo, env)
    (repo / "x.txt").write_text("x")

    GitSubprocessClient().commit_all(repo, "chore: operator identity")

    log = _git(["log", "-1", "--format=%an <%ae>"], repo, env)
    assert "Operator <op@example.com>" in log.stdout
