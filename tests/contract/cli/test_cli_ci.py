"""Public CLI contracts for `dadaia ci` (pre-push gate, T-GATE-01)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_preflight_passes_when_all_checks_pass(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(ci, "subprocess_runner", lambda root: lambda argv: (0, "ok"))

    result = _runner.invoke(app, ["ci", "preflight"])

    assert result.exit_code == 0
    assert "All preflight checks passed" in result.output


def test_preflight_blocks_when_a_check_fails(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    def factory(root: Path):
        def run(argv: Sequence[str]) -> tuple[int, str]:
            return (1, "type error on line 1") if "mypy" in argv else (0, "ok")

        return run

    monkeypatch.setattr(ci, "subprocess_runner", factory)

    result = _runner.invoke(app, ["ci", "preflight", "--no-fail-fast"])

    assert result.exit_code == 1
    assert "Pre-push gate FAILED" in result.output
    assert "mypy --strict" in result.output


def test_install_hook_writes_executable_pre_push(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    result = _runner.invoke(app, ["ci", "install-hook"])
    assert result.exit_code == 0

    hook = tmp_path / ".git" / "hooks" / "pre-push"
    assert hook.exists()
    assert "dadaia ci preflight" in hook.read_text()


def test_install_hook_refuses_overwrite_without_force(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    assert _runner.invoke(app, ["ci", "install-hook"]).exit_code == 0
    # second call without --force is refused
    assert _runner.invoke(app, ["ci", "install-hook"]).exit_code == 1
    # --force overwrites
    assert _runner.invoke(app, ["ci", "install-hook", "--force"]).exit_code == 0
