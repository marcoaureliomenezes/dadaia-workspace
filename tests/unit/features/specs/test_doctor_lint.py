"""Unit tests for SpecsDoctor LINT-1 mapping without spawning subprocesses."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs import doctor as doctor_module


def _make_specs_with_memory(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    return specs


def test_lint1_clean_exit_returns_no_issues(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specs = _make_specs_with_memory(tmp_path)

    monkeypatch.setattr(
        doctor_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    assert SpecsDoctor(specs)._check_lint1_memory_atoms() == []  # noqa: SLF001


def test_lint1_error_exit_maps_to_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)

    monkeypatch.setattr(
        doctor_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="frontmatter invalid", stderr=""
        ),
    )

    issues = SpecsDoctor(specs)._check_lint1_memory_atoms()  # noqa: SLF001

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].severity == Severity.ERROR
    assert "frontmatter invalid" in issues[0].description


def test_lint1_warning_exit_maps_to_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specs = _make_specs_with_memory(tmp_path)

    monkeypatch.setattr(
        doctor_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stdout="", stderr="token drift"),
    )

    issues = SpecsDoctor(specs)._check_lint1_memory_atoms()  # noqa: SLF001

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].severity == Severity.WARNING
    assert "token drift" in issues[0].description


def test_lint1_timeout_maps_to_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)

    def raise_timeout(*args: object, **kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="lint-memory-atoms.py", timeout=30)

    monkeypatch.setattr(doctor_module.subprocess, "run", raise_timeout)

    issues = SpecsDoctor(specs)._check_lint1_memory_atoms()  # noqa: SLF001

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
