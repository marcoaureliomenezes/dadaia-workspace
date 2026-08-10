"""RED tests — the doctor exit verdict comes from the typed report, fail-closed.

Bug ``public-doctor-exits-zero-despite-error``: the CLI re-derived severity by
``startswith`` against a closed prefix list; ``[error]`` lines (public-privacy,
codex checks) fell into a decorative ``else`` and the command exited 0. These tests
pin the new contract: the exit code is :attr:`DoctorReport.blocking` — ANY blocking
status fails the run, including statuses the old chain never knew.
"""

from __future__ import annotations

from pathlib import Path

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


def test_error_line_exits_nonzero(monkeypatch, tmp_path: Path) -> None:
    """An ``[error]`` finding (e.g. public-privacy) MUST fail the run."""
    result = _run_doctor_with(
        monkeypatch,
        tmp_path,
        (
            DoctorLine(DoctorStatus.OK, "stage:data/DADAIA.md"),
            DoctorLine(DoctorStatus.ERROR, "public-privacy:x.md: contains 'secret-name'"),
        ),
    )
    assert result.exit_code == 1, result.output
    assert "[error] public-privacy:x.md" in result.output


def test_all_nonblocking_exits_zero(monkeypatch, tmp_path: Path) -> None:
    """warn/info/foreign/not-applicable stay non-blocking (Ruling 16 for foreign)."""
    result = _run_doctor_with(
        monkeypatch,
        tmp_path,
        (
            DoctorLine(DoctorStatus.OK, "law:DADAIA.md"),
            DoctorLine(DoctorStatus.WARN, "claude: out-of-profile runtime present"),
            DoctorLine(DoctorStatus.INFO, "codex:trust-boundary — informational"),
            DoctorLine(DoctorStatus.FOREIGN, "repos/consumer:AGENTS.md"),
            DoctorLine(DoctorStatus.NOT_APPLICABLE, "git-dirty check (not a git repo)"),
        ),
    )
    assert result.exit_code == 0, result.output


def test_drift_and_missing_still_exit_nonzero(monkeypatch, tmp_path: Path) -> None:
    for status in (DoctorStatus.DRIFT, DoctorStatus.MISSING, DoctorStatus.LEAK):
        result = _run_doctor_with(
            monkeypatch, tmp_path, (DoctorLine(status, "claude:agents/x.md"),)
        )
        assert result.exit_code == 1, (status, result.output)
