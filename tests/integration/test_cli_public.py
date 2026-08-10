"""dadaia public CLI — stage / install / doctor commands.

Merged per plan-integration.md (4 -> 2): (1) stage + install --target all + --force
smoke; (2) doctor exit-code routing (mocked service, both cases — the non-zero-on-drift
exit contract).
"""

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.doctor_report import (
    DoctorLine,
    DoctorReport,
    DoctorStatus,
)
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


def test_public_stage_install_force_smoke_and_doctor_exit_code_routing(
    tmp_path: Path, monkeypatch
) -> None:
    """Stage + install --target all + --force smoke, then T-PROP-02 integration: doctor
    CLI exits 0 on clean workspace, non-zero on drift.

    The doctor sub-cases are tested using patched service responses so the test is
    deterministic regardless of the real workspace state. The CLI layer
    (command/exit-code routing) is exercised in full; only the service return value
    is stubbed.
    """
    from unittest.mock import MagicMock, patch

    _init_ws(tmp_path)
    monkeypatch.chdir(tmp_path)

    stage_result = _runner.invoke(app, ["public", "stage"])
    assert stage_result.exit_code == 0, stage_result.output
    assert "staged" in stage_result.output.lower() or "No assets" in stage_result.output

    install_result = _runner.invoke(app, ["public", "install", "--target", "all"])
    assert install_result.exit_code == 0, install_result.output

    force_result = _runner.invoke(app, ["public", "install", "--force"])
    assert force_result.exit_code == 0, force_result.output

    ok_lines = DoctorReport(
        lines=(
            DoctorLine(DoctorStatus.OK, "stage:agents/qa-engineer.md"),
            DoctorLine(DoctorStatus.NOT_APPLICABLE, "codex:config.toml"),
        )
    )
    with patch("dadaia_workspace.cli.commands.public.container") as mock_container:
        mock_svc = MagicMock()
        mock_svc.doctor.return_value = ok_lines
        mock_container.build_public_service.return_value = mock_svc
        with patch(
            "dadaia_workspace.cli.commands.public.resolve_workspace_root",
            return_value=tmp_path,
        ):
            clean_result = _runner.invoke(app, ["public", "doctor"])

    assert clean_result.exit_code == 0, (
        f"Expected exit 0 for clean workspace, got {clean_result.exit_code}. "
        f"Output:\n{clean_result.output}"
    )
    assert "[ok]" in clean_result.output

    drift_lines = DoctorReport(
        lines=(
            DoctorLine(DoctorStatus.OK, "stage:agents/qa-engineer.md"),
            DoctorLine(DoctorStatus.DRIFT, "claude:rules/some-rule.md"),
        )
    )
    with patch("dadaia_workspace.cli.commands.public.container") as mock_container:
        mock_svc = MagicMock()
        mock_svc.doctor.return_value = drift_lines
        mock_container.build_public_service.return_value = mock_svc
        with patch(
            "dadaia_workspace.cli.commands.public.resolve_workspace_root",
            return_value=tmp_path,
        ):
            drift_result = _runner.invoke(app, ["public", "doctor"])

    assert drift_result.exit_code != 0, (
        f"Expected non-zero exit for drift, got {drift_result.exit_code}. "
        f"Output:\n{drift_result.output}"
    )
    assert "[drift]" in drift_result.output, (
        f"Expected '[drift]' in output, got:\n{drift_result.output}"
    )
