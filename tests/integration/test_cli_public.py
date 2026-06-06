"""dadaia public CLI — stage / install / doctor commands."""

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_ws(tmp_path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    return tmp_path


def test_public_stage_reports_result(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "stage"])
    assert result.exit_code == 0, result.output
    assert "staged" in result.output.lower() or "No assets" in result.output


def test_public_install_with_target_all(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "install", "--target", "all"])
    assert result.exit_code == 0, result.output


def test_public_install_force_flag(tmp_path: Path, monkeypatch) -> None:
    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["public", "install", "--force"])
    assert result.exit_code == 0, result.output


def test_public_doctor_outputs_status(tmp_path: Path, monkeypatch) -> None:
    """T-PROP-02 integration: doctor CLI exits 0 on clean workspace, non-zero on drift.

    The two sub-cases are tested using patched service responses so the test
    is deterministic regardless of the real workspace state.  The CLI layer
    (command/exit-code routing) is exercised in full; only the service return
    value is stubbed.
    """
    from unittest.mock import MagicMock, patch

    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)

    # --- Case 1: clean workspace → exit 0, only [ok]/[not-applicable] lines ---
    ok_lines = ["[ok] stage:agents/qa-engineer.md", "[not-applicable] codex:config.toml"]
    with patch("dadaia_workspace.cli.commands.public.container") as mock_container:
        mock_svc = MagicMock()
        mock_svc.doctor.return_value = ok_lines
        mock_container.build_public_service.return_value = mock_svc
        with patch(
            "dadaia_workspace.cli.commands.public.resolve_workspace_root",
            return_value=tmp_path,
        ):
            result = _runner.invoke(app, ["public", "doctor"])

    assert result.exit_code == 0, (
        f"Expected exit 0 for clean workspace, got {result.exit_code}. Output:\n{result.output}"
    )
    assert "[ok]" in result.output

    # --- Case 2: drift detected → non-zero exit, [drift] in output ---
    drift_lines = ["[ok] stage:agents/qa-engineer.md", "[drift] claude:rules/some-rule.md"]
    with patch("dadaia_workspace.cli.commands.public.container") as mock_container:
        mock_svc = MagicMock()
        mock_svc.doctor.return_value = drift_lines
        mock_container.build_public_service.return_value = mock_svc
        with patch(
            "dadaia_workspace.cli.commands.public.resolve_workspace_root",
            return_value=tmp_path,
        ):
            result = _runner.invoke(app, ["public", "doctor"])

    assert result.exit_code != 0, (
        f"Expected non-zero exit for drift, got {result.exit_code}. Output:\n{result.output}"
    )
    assert "[drift]" in result.output, f"Expected '[drift]' in output, got:\n{result.output}"
