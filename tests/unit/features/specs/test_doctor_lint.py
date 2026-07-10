"""Unit tests for the memory validator's LINT-1 mapping without spawning subprocesses.

v0.1.55 FR1 re-homed LINT-1 from the SpecsDoctor god module to ``doctor_memory.MemoryValidator``
(the sole holder of the lazy ``infrastructure.subprocess_runner`` import). These tests exercise
the validator's public ``check_lint1_memory_atoms`` directly and monkeypatch
``doctor_memory._LINT_SCRIPT``.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.process_runner import ProcessResult
from dadaia_workspace.features.specs import Severity
from dadaia_workspace.features.specs import doctor_memory as doctor_module
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator


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


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "expected_severity", "expect_no_issue", "message_fragment"),
    [
        pytest.param(0, "", "", None, True, None, id="clean-exit-no-issues"),
        pytest.param(
            1,
            "frontmatter invalid",
            "",
            Severity.ERROR,
            False,
            "frontmatter invalid",
            id="error-exit-maps-to-error",
        ),
        pytest.param(
            2,
            "",
            "token drift",
            Severity.WARNING,
            False,
            "token drift",
            id="warning-exit-maps-to-warning",
        ),
    ],
)
def test_lint1_exit_code_severity_mapping(
    tmp_path: Path,
    returncode: int,
    stdout: str,
    stderr: str,
    expected_severity: Severity | None,
    expect_no_issue: bool,
    message_fragment: str | None,
) -> None:
    specs = _make_specs_with_memory(tmp_path)
    doctor = MemoryValidator(
        specs,
        process_runner=_FakeProcessRunner(returncode=returncode, stdout=stdout, stderr=stderr),
    )
    issues = doctor.check_lint1_memory_atoms()

    if expect_no_issue:
        assert issues == []
        return
    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].severity == expected_severity
    assert message_fragment is not None and message_fragment in issues[0].description


def test_lint1_timeout_and_missing_script_degrade_to_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specs = _make_specs_with_memory(tmp_path)

    # Timeout degrades to a WARNING, never a crash.
    timeout_issues = MemoryValidator(
        specs, process_runner=_TimeoutProcessRunner()
    ).check_lint1_memory_atoms()
    assert len(timeout_issues) == 1
    assert timeout_issues[0].code == "LINT-1"
    assert timeout_issues[0].severity == Severity.WARNING
    assert "timed out" in timeout_issues[0].description

    # A missing lint script also degrades to a WARNING.
    missing_script = tmp_path / "missing-lint.py"
    monkeypatch.setattr(doctor_module, "_LINT_SCRIPT", missing_script)
    missing_issues = MemoryValidator(specs).check_lint1_memory_atoms()
    assert len(missing_issues) == 1
    assert missing_issues[0].code == "LINT-1"
    assert missing_issues[0].severity == Severity.WARNING
    assert str(missing_script) in missing_issues[0].description
