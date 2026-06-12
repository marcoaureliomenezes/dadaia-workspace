"""Unit tests for the DoctorService venv-health invariant (FR-W3-02, T-014-13).

The doctor reports a VENV-* finding when the workspace venv is missing or its ``dadaia``
entrypoint is absent / non-executable. A healthy synthetic tree reports nothing.

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


# ---------------------------------------------------------------------------
# Positive: a healthy synthetic venv reports no VENV finding.
# ---------------------------------------------------------------------------


class TestVenvHealthy:
    def test_healthy_venv_no_finding(self, tmp_path: Path) -> None:
        _init_workspace(tmp_path)
        _make_healthy_venv(tmp_path)
        codes = {i.code for i in _make_doctor(tmp_path).check()}
        assert not any(c.startswith("VENV") for c in codes)


# ---------------------------------------------------------------------------
# Negative: missing venv / missing entrypoint / non-executable entrypoint.
# ---------------------------------------------------------------------------


class TestVenvMissing:
    def test_missing_venv_dir_triggers_finding(self, tmp_path: Path) -> None:
        _init_workspace(tmp_path)
        # No .dadaia/.venv at all.
        codes = {i.code for i in _make_doctor(tmp_path).check()}
        assert any(c.startswith("VENV") for c in codes)

    def test_missing_dadaia_entrypoint_triggers_finding(self, tmp_path: Path) -> None:
        _init_workspace(tmp_path)
        _venv_bin(tmp_path).mkdir(parents=True)  # bin/ exists but no dadaia entry.
        codes = {i.code for i in _make_doctor(tmp_path).check()}
        assert any(c.startswith("VENV") for c in codes)

    @pytest.mark.skipif(_WINDOWS, reason="POSIX exec bit not meaningful on Windows")
    def test_non_executable_entrypoint_triggers_finding(self, tmp_path: Path) -> None:
        _init_workspace(tmp_path)
        entry = _make_healthy_venv(tmp_path)
        entry.chmod(entry.stat().st_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)
        codes = {i.code for i in _make_doctor(tmp_path).check()}
        assert any(c.startswith("VENV") for c in codes)

    def test_venv_finding_is_not_fixable(self, tmp_path: Path) -> None:
        # Rebuilding a venv is an operator action, not an auto-repair.
        _init_workspace(tmp_path)
        venv_issues = [i for i in _make_doctor(tmp_path).check() if i.code.startswith("VENV")]
        assert venv_issues
        assert all(not i.fixable for i in venv_issues)
