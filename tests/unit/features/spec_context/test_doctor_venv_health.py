"""Unit tests for the DoctorService venv-health invariant (FR-W3-02, T-014-13).

The doctor reports a VENV-* finding when the workspace venv is missing or its ``dadaia``
entrypoint is absent / non-executable. A healthy synthetic tree reports nothing, and every
VENV-* finding is non-fixable (rebuilding a venv is an operator action).

All fixtures are SYNTHETIC trees (mkdir/touch/chmod) — NEVER a real venv build
(quality-assurance memory law: building real venvs in tests exhausts disk).
"""

from __future__ import annotations

import os
import stat

import pytest

pytest.importorskip("fcntl")

from pathlib import Path  # noqa: E402

from dadaia_workspace.core.platform import PLATFORM  # noqa: E402
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

_WINDOWS = os.name == "nt"


def _make_doctor(workspace_root: Path) -> DoctorService:
    return DoctorService(FakeContextStore(), FakeGitClient(), workspace_root)


def _init_workspace(root: Path) -> None:
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}'
    )
    (root / "repos").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# agents")


def _venv_bin(root: Path) -> Path:
    return root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir


def _make_healthy_venv(root: Path) -> Path:
    """Create a SYNTHETIC venv tree with an executable ``dadaia`` entrypoint."""
    bindir = _venv_bin(root)
    bindir.mkdir(parents=True)
    entry = bindir / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n")
    entry.chmod(entry.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return entry


def _setup_non_executable(tp: Path) -> None:
    entry = _make_healthy_venv(tp)
    entry.chmod(entry.stat().st_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)


@pytest.mark.parametrize(
    ("case", "setup", "expect_finding"),
    [
        pytest.param("healthy", lambda tp: _make_healthy_venv(tp), False, id="healthy-venv-no-finding"),
        pytest.param("missing-dir", lambda tp: None, True, id="missing-venv-dir-triggers-finding"),
        pytest.param(
            "missing-entrypoint",
            lambda tp: _venv_bin(tp).mkdir(parents=True),
            True,
            id="missing-dadaia-entrypoint-triggers-finding",
        ),
        pytest.param(
            "non-executable",
            _setup_non_executable,
            True,
            id="non-executable-entrypoint-triggers-finding",
        ),
    ],
)
def test_venv_health_matrix(tmp_path: Path, case: str, setup, expect_finding: bool) -> None:  # type: ignore[no-untyped-def]
    if case == "non-executable" and _WINDOWS:
        pytest.skip("POSIX exec bit not meaningful on Windows")
    _init_workspace(tmp_path)
    setup(tmp_path)
    codes = {i.code for i in _make_doctor(tmp_path).check()}
    assert any(c.startswith("VENV") for c in codes) is expect_finding


def test_venv_finding_is_not_fixable(tmp_path: Path) -> None:
    # Rebuilding a venv is an operator action, not an auto-repair.
    _init_workspace(tmp_path)
    venv_issues = [i for i in _make_doctor(tmp_path).check() if i.code.startswith("VENV")]
    assert venv_issues
    assert all(not i.fixable for i in venv_issues)
