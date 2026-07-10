"""Public CLI contracts for `dadaia ci` (pre-push gate, T-GATE-01).

Pre-commit allow/block and push-gate block/pass are covered at the STRONGER
real-boundary e2e (``tests/e2e/test_pre_commit_lease_gate.py`` / real git hook,
``tests/e2e/test_push_gate_check.py`` / real subprocess stdin) — this CliRunner-level
duplicate was removed; the ``metrics.commit_sha`` keying coverage lives wholly there.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.mark.parametrize("all_pass", [True, False], ids=["pass", "fail"])
def test_preflight_pass_and_fail(monkeypatch, tmp_path: Path, all_pass: bool) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    if all_pass:
        monkeypatch.setattr(ci, "subprocess_runner", lambda root: lambda argv: (0, "ok"))
        result = _runner.invoke(app, ["ci", "preflight"])
        assert result.exit_code == 0
        assert "All preflight checks passed" in result.output
        return

    def factory(root: Path):
        def run(argv: Sequence[str]) -> tuple[int, str]:
            # argv may carry absolute tool paths (runner-derived resolution,
            # T-011-06) — match by substring, not exact element.
            if any("mypy" in part for part in argv):
                return (1, "type error on line 1")
            return (0, "ok")

        return run

    monkeypatch.setattr(ci, "subprocess_runner", factory)

    result = _runner.invoke(app, ["ci", "preflight", "--no-fail-fast"])

    assert result.exit_code == 1
    assert "Pre-push gate FAILED" in result.output
    assert "mypy --strict" in result.output


def test_install_hook_writes_and_refuses_overwrite_without_force(
    monkeypatch, tmp_path: Path
) -> None:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    result = _runner.invoke(app, ["ci", "install-hook"])
    assert result.exit_code == 0

    pre_push = tmp_path / ".git" / "hooks" / "pre-push"
    pre_commit = tmp_path / ".git" / "hooks" / "pre-commit"
    assert pre_push.exists()
    assert pre_commit.exists()
    assert "ci preflight" in pre_push.read_text()
    assert "ci push-gate-check" in pre_push.read_text()
    assert "ci pre-commit-check" in pre_commit.read_text()

    # second call without --force is refused (pre-commit already present).
    assert _runner.invoke(app, ["ci", "install-hook"]).exit_code == 1
    # --force overwrites both.
    assert _runner.invoke(app, ["ci", "install-hook", "--force"]).exit_code == 0
