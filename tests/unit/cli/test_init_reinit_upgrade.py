"""Re-init is the upgrade: ``init <existing ws>`` compares the venv with the running version.

Intent: CONTRACT — 0.4.8 FR2 AC2.1-AC2.3 (T-048-06).

The venv is fake (the conftest backstop no-ops the builder): its reported version is the
``installed_version`` seam, and the running distribution is ``_running_version`` — the
one ``version_change`` decider reads both, for the install and for the report.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import init as init_module
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import cli_path
from dadaia_workspace.core.platform import detect
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    born = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])
    assert born.exit_code == 0, born.output
    return ws


def _bytes(tree: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in sorted(tree.rglob("*")) if p.is_file()}


def _versions(monkeypatch: pytest.MonkeyPatch, ws: Path, venv: str, running: str) -> None:
    cli_path(ws).parent.mkdir(parents=True, exist_ok=True)
    cli_path(ws).write_text("#!stub")
    monkeypatch.setattr(VenvPythonEnvironmentManager, "installed_version", lambda self, ws: venv)
    monkeypatch.setattr(
        VenvPythonEnvironmentManager, "_running_version", staticmethod(lambda: running)
    )


def test_equal_version_reports_already_at_without_harness(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _versions(monkeypatch, workspace, "0.4.8", "0.4.8")
    before = _bytes(workspace / ".dadaia")

    result = _runner.invoke(app, ["init", str(workspace)])

    assert result.exit_code == 0, result.output
    assert _bytes(workspace / ".dadaia") == before
    assert "already at 0.4.8" in result.output
    assert "upgraded" not in result.output


def test_newer_running_version_reconciles_and_reports_the_transition(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _versions(monkeypatch, workspace, "0.4.7", "0.4.8")
    reconciled: list[str] = []

    def _reconcile(root: Path, *, expected_version: str, **_: object) -> object:
        reconciled.append(expected_version)
        return type("R", (), {"ok": True, "error": None})()

    monkeypatch.setattr(init_module, "reconcile_workspace", _reconcile)

    result = _runner.invoke(app, ["init", str(workspace)])

    assert result.exit_code == 0, result.output
    assert "upgraded 0.4.7 -> 0.4.8" in result.output
    assert reconciled == ["0.4.8"]


def test_a_failed_reconcile_prints_the_windows_fix_line(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2.6 (T-050-08): the refusal's fix is built by ``fix_line`` — on Windows the CLI is
    ``Scripts\\dadaia.exe``, quoted by the MSVCRT rules."""
    _versions(monkeypatch, workspace, "0.4.7", "0.4.8")

    def _reconcile(root: Path, *, expected_version: str, **_: object) -> object:
        # Windows from here on: only the refusal is rendered after the reconcile.
        monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", detect("win32"))
        return type("R", (), {"ok": False, "error": "boom"})()

    monkeypatch.setattr(init_module, "reconcile_workspace", _reconcile)

    result = _runner.invoke(app, ["init", str(workspace)])

    exe = workspace.resolve() / ".dadaia" / ".venv" / "Scripts" / "dadaia.exe"
    assert result.exit_code == 1
    assert f"fix: {exe} reconcile --expect-version 0.4.8" in result.output


def test_older_running_version_exits_1_with_the_pinned_fix(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _versions(monkeypatch, workspace, "0.4.9", "0.4.8")

    before = sorted(p for p in workspace.rglob("*"))

    result = _runner.invoke(app, ["init", str(workspace)])

    assert result.exit_code == 1
    assert f"fix: uvx dadaia-workspace@0.4.9 init {workspace.resolve()}" in result.output
    assert sorted(p for p in workspace.rglob("*")) == before
