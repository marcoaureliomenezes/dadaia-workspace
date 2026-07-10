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
    root_conftest.pytest_sessionstart(session)

    # The gate's own ruff/mypy checks "create" these mid-session.
    for name in created_during:
        (fake_root / name).mkdir(parents=True, exist_ok=True)

    root_conftest.pytest_sessionfinish(session, 0)
    capsys.readouterr()  # drain any printed message
    return session.exitstatus


@pytest.mark.parametrize(
    ("preexisting", "created_during", "expect_status"),
    [
        pytest.param((), (".ruff_cache",), 1, id="session-created-pollution-dir-fails"),
        pytest.param((".ruff_cache", ".mypy_cache"), (), 0, id="preexisting-only-does-not-fail"),
        pytest.param(
            (".mypy_cache",),
            (".pytest_cache",),
            1,
            id="preexisting-ignored-but-new-one-still-caught",
        ),
    ],
)
def test_preexisting_pollution_handling(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: Any,
    preexisting: tuple[str, ...],
    created_during: tuple[str, ...],
    expect_status: int,
) -> None:
    status = _run_guard_cycle(
        monkeypatch,
        tmp_path,
        preexisting=preexisting,
        created_during=created_during,
        capsys=capsys,
    )
    assert status == expect_status
