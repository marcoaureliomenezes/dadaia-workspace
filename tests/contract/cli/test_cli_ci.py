"""Intent: CONTRACT — DADAIA §3.4 git chokepoints (dadaia ci install-hook)

Public CLI contracts for `dadaia ci` (pre-push gate, T-GATE-01).

Pre-commit allow/block and push-gate block/pass are covered at the STRONGER
real-boundary e2e (``tests/e2e/test_pre_commit_lease_gate.py`` / real git hook,
``tests/e2e/test_push_gate_check.py`` / real subprocess stdin) — this CliRunner-level
duplicate was removed; the ``metrics.commit_sha`` keying coverage lives wholly there.
"""

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
    """pre-push-gate-never-runs-under-core-hookspath#B1: under core.hooksPath the gate lands
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
