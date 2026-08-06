"""A platform with no execute bit must not be told its files lost one.

On Windows every managed script read `[drift] (not executable)` and the prescribed
repair could never clear it — `chmod` there only toggles read-only. The doctor became a
permanent red that no command could fix, which is worse than not checking at all
(bug doctor-reports-unrepairable-exec-bit-drift-on-windows).

These tests drive the POSIX-only guard by patching the platform predicate, so they prove
the Windows behaviour from any host.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure import public_assets as pa


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    scripts = tmp_path / ".dadaia" / "scripts"
    scripts.mkdir(parents=True)
    gate = scripts / "pre-push-ci-gate.sh"
    gate.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    gate.chmod(0o644)  # no execute bit, exactly what Windows always looks like
    return tmp_path


def test_a_platform_without_the_bit_reports_no_drift(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pa, "PLATFORM_HAS_EXECUTE_BIT", False)

    reports = pa.FileSystemPublicAssetManager()._check_managed_script_modes(workspace)

    assert reports == [], f"nothing to inspect on this platform, but got: {reports}"


def test_posix_still_reports_the_cleared_bit(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard must not become a blanket exemption — the real check still fires."""
    monkeypatch.setattr(pa, "PLATFORM_HAS_EXECUTE_BIT", True)

    reports = pa.FileSystemPublicAssetManager()._check_managed_script_modes(workspace)

    assert len(reports) == 1, reports
    assert "not executable" in reports[0]
    assert "pre-push-ci-gate.sh" in reports[0]
