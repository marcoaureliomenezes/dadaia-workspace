"""Unit tests for the conftest session-pollution guard's pre/post snapshot diff.

These exercise the guard's logic against a *fake* repo root (tmp_path), never the
real repo root, so the test itself can never pollute the working tree.

Behavior pinned (T-010-25, AC-R8-02):
  * a pollution dir that already existed at session start → guard does NOT fail
  * a pollution dir CREATED during the session → guard fails (exitstatus = 1)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


def _load_root_conftest() -> ModuleType:
    """Load the workspace root conftest.py by path (it is not an importable name)."""
    root_conftest_path = Path(__file__).resolve().parents[3] / "conftest.py"
    spec = importlib.util.spec_from_file_location("_root_conftest_under_test", root_conftest_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


root_conftest = _load_root_conftest()


class _FakeSession:
    """Minimal stand-in for pytest.Session: just carries exitstatus + config."""

    def __init__(self) -> None:
        self.exitstatus = 0
        self.config = SimpleNamespace(option=SimpleNamespace(verbose=0))


def _run_guard_cycle(
    monkeypatch: pytest.MonkeyPatch,
    fake_root: Path,
    *,
    preexisting: tuple[str, ...],
    created_during: tuple[str, ...],
    capsys: Any,
) -> int:
    """Point the guard at ``fake_root``, simulate a session, return exitstatus."""
    monkeypatch.setattr(root_conftest, "_REPO_ROOT", fake_root, raising=True)

    for name in preexisting:
        (fake_root / name).mkdir(parents=True, exist_ok=True)

    session = _FakeSession()
    root_conftest.pytest_sessionstart(session)  # type: ignore[arg-type]

    # The gate's own ruff/mypy checks "create" these mid-session.
    for name in created_during:
        (fake_root / name).mkdir(parents=True, exist_ok=True)

    root_conftest.pytest_sessionfinish(session, 0)  # type: ignore[arg-type]
    capsys.readouterr()  # drain any printed message
    return session.exitstatus


def test_preexisting_pollution_dir_does_not_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: Any
) -> None:
    status = _run_guard_cycle(
        monkeypatch,
        tmp_path,
        preexisting=(".ruff_cache", ".mypy_cache"),
        created_during=(),
        capsys=capsys,
    )
    assert status == 0


def test_session_created_pollution_dir_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: Any
) -> None:
    status = _run_guard_cycle(
        monkeypatch,
        tmp_path,
        preexisting=(),
        created_during=(".ruff_cache",),
        capsys=capsys,
    )
    assert status == 1


def test_preexisting_ignored_but_new_one_still_caught(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: Any
) -> None:
    """A pre-existing dir is ignored, yet a NEW dir created in-session still fails."""
    status = _run_guard_cycle(
        monkeypatch,
        tmp_path,
        preexisting=(".mypy_cache",),
        created_during=(".pytest_cache",),
        capsys=capsys,
    )
    assert status == 1


def test_message_quality_lists_only_new_offenders(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setattr(root_conftest, "_REPO_ROOT", tmp_path, raising=True)
    (tmp_path / ".mypy_cache").mkdir()  # pre-existing — must NOT be reported
    session = _FakeSession()
    root_conftest.pytest_sessionstart(session)  # type: ignore[arg-type]
    (tmp_path / ".ruff_cache").mkdir()  # session-created — must be reported
    root_conftest.pytest_sessionfinish(session, 0)  # type: ignore[arg-type]
    out = capsys.readouterr().out
    assert "[SESSION POLLUTION]" in out
    assert ".ruff_cache" in out
    assert ".mypy_cache" not in out
    assert session.exitstatus == 1
