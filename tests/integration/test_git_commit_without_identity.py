"""commit_all commits under the operator's own git identity (SA-H3-2: git's rule is the
only one — the tool fallback identity is deleted; a missing identity is refused up front
by ``GitSubprocessClient.identity_fix``, see ``test_context_baseline``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient


def _git(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)


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
