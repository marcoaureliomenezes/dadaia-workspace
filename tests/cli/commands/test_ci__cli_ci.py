"""``dadaia ci install-hook``: where the pre-push gate lands and when it refuses to overwrite."""

from __future__ import annotations

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_install_hook_writes_and_refuses_overwrite_without_force(
    monkeypatch, tmp_path: Path
) -> None:
    """Under core.hooksPath the gate lands
    where git runs hooks; a hook already there is refused non-zero with a fix: line."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "core.hooksPath", ".husky"], check=True)
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    result = _runner.invoke(app, ["ci", "install-hook"])
    assert result.exit_code == 0

    assert not (tmp_path / ".git" / "hooks" / "pre-push").exists()
    pre_push = tmp_path / ".husky" / "pre-push"
    assert pre_push.exists()
    pre_push_text = pre_push.read_text()
    assert "ci push-gate-check" in pre_push_text

    # second call without --force is refused (pre-push already present).
    refused = _runner.invoke(app, ["ci", "install-hook"])
    assert refused.exit_code == 1
    assert f"ci install-hook --force --repo {tmp_path.as_posix()}" in refused.output
    assert "fix: " in refused.output
    # --force overwrites both.
    assert _runner.invoke(app, ["ci", "install-hook", "--force"]).exit_code == 0
