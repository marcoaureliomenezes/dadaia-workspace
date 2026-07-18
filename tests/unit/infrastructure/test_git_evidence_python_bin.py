"""Bug implementation-review-uses-parent-venv-without-pytest (game cycle 8).

The executed-test gate and the review evidence provider ran pytest with
``sys.executable`` — the CLI's own interpreter, which in a consumer validation venv
has no pytest — instead of the workspace venv python the bootstrap provisions. Both
runners now accept the workspace venv interpreter and prefer it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import dadaia_workspace.infrastructure.git_evidence as ge


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_ok():\n    assert True\n")
    return tmp_path


def _capture_cmd(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    class _Proc:
        returncode = 0
        stdout = "1 passed"
        stderr = ""

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        calls.append(list(cmd))
        return _Proc()

    monkeypatch.setattr(ge.subprocess, "run", fake_run)
    return calls


def test_executed_test_gate_prefers_workspace_python(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _capture_cmd(monkeypatch)
    gate = ge.build_executed_test_gate(repo, paths=("tests/**",), python_bin="/ws/.venv/bin/python")
    ok, _evidence = gate()
    assert ok is True
    assert calls[0][0] == "/ws/.venv/bin/python"


def test_executed_test_gate_falls_back_to_sys_executable(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _capture_cmd(monkeypatch)
    gate = ge.build_executed_test_gate(repo, paths=("tests/**",))
    gate()
    assert calls[0][0] == sys.executable


def test_test_output_provider_prefers_workspace_python(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _capture_cmd(monkeypatch)
    provider = ge.build_test_output_provider(
        repo, paths=("tests/**",), python_bin="/ws/.venv/bin/python"
    )
    provider()
    assert calls[0][0] == "/ws/.venv/bin/python"
