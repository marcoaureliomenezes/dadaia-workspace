"""RED tests — the doctor exit verdict comes from the typed report, fail-closed.

Bug ``public-doctor-exits-zero-despite-error``: the CLI re-derived severity by
``startswith`` against a closed prefix list; ``[error]`` lines (public-privacy,
codex checks) fell into a decorative ``else`` and the command exited 0. These tests
pin the new contract: the exit code is :attr:`DoctorReport.blocking` — ANY blocking
status fails the run, including statuses the old chain never knew.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorReport, DoctorStatus

_runner = CliRunner()


def _run_doctor_with(monkeypatch, tmp_path: Path, lines: tuple[DoctorLine, ...]) -> object:
    """Run ``dadaia public doctor`` with the service returning a fixed report."""
    import dadaia_workspace.cli.commands.public as public_cmd

    class _FakeService:
        def doctor(self, workspace_root: Path) -> DoctorReport:
            return DoctorReport(lines=lines)

    class _FakeContainer:
        def build_public_service(self) -> _FakeService:
            return _FakeService()

    monkeypatch.setattr(public_cmd, "container", _FakeContainer())
    monkeypatch.setattr(public_cmd, "resolve_workspace_root", lambda: tmp_path)
    return _runner.invoke(app, ["public", "doctor"])


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (DoctorStatus.ERROR, 1),  # public-privacy / codex [error] lines fail the run
        (DoctorStatus.DRIFT, 1),
        (DoctorStatus.MISSING, 1),
        (DoctorStatus.LEAK, 1),
        (DoctorStatus.WARN, 0),
        (DoctorStatus.INFO, 0),
        (DoctorStatus.FOREIGN, 0),  # Ruling 16
        (DoctorStatus.NOT_APPLICABLE, 0),
    ],
    ids=lambda v: getattr(v, "name", str(v)),
)
def test_the_exit_code_is_the_reports_blocking_verdict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: DoctorStatus, code: int
) -> None:
    line = DoctorLine(status, "public-privacy:x.md: contains 'secret-name'")
    result = _run_doctor_with(
        monkeypatch, tmp_path, (DoctorLine(DoctorStatus.OK, "root:AGENTS.md"), line)
    )
    assert result.exit_code == code, result.output  # type: ignore[attr-defined]
    assert f"[{status.value}] public-privacy:x.md" in result.output  # type: ignore[attr-defined]
