"""Unit tests for SpecsDoctor LINT-1 mapping without spawning subprocesses."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.process_runner import ProcessResult
from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs import doctor as doctor_module


def _make_specs_with_memory(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    return specs


class _FakeProcessRunner:
    """Fake ProcessRunner that returns a preconfigured ProcessResult."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self._result = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> ProcessResult:
        return self._result


class _TimeoutProcessRunner:
    """Fake ProcessRunner that raises TimeoutError."""

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> ProcessResult:
        raise TimeoutError("command timed out after 30s")


def test_lint1_clean_exit_returns_no_issues(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)

    doctor = SpecsDoctor(specs, process_runner=_FakeProcessRunner(returncode=0))
    assert doctor._check_lint1_memory_atoms() == []  # noqa: SLF001


def test_lint1_error_exit_maps_to_error(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)

    doctor = SpecsDoctor(
        specs,
        process_runner=_FakeProcessRunner(returncode=1, stdout="frontmatter invalid"),
    )
    issues = doctor._check_lint1_memory_atoms()  # noqa: SLF001

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].severity == Severity.ERROR
    assert "frontmatter invalid" in issues[0].description


def test_lint1_warning_exit_maps_to_warning(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)

    doctor = SpecsDoctor(
        specs,
        process_runner=_FakeProcessRunner(returncode=2, stderr="token drift"),
    )
    issues = doctor._check_lint1_memory_atoms()  # noqa: SLF001

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].severity == Severity.WARNING
    assert "token drift" in issues[0].description


def test_lint1_timeout_maps_to_warning(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)

    doctor = SpecsDoctor(specs, process_runner=_TimeoutProcessRunner())
    issues = doctor._check_lint1_memory_atoms()  # noqa: SLF001

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].severity == Severity.WARNING
    assert "timed out" in issues[0].description


def test_lint1_missing_script_maps_to_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specs = _make_specs_with_memory(tmp_path)
    missing_script = tmp_path / "missing-lint.py"
    monkeypatch.setattr(doctor_module, "_LINT_SCRIPT", missing_script)

    issues = SpecsDoctor(specs)._check_lint1_memory_atoms()  # noqa: SLF001

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].severity == Severity.WARNING
    assert str(missing_script) in issues[0].description
