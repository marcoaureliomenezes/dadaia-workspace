"""v0.2.8 T3 — kimi-code projection: workspace tree, user-level hook wiring, doctor.

Covers the ``kimi-code`` install target end to end in a tmp workspace with
``KIMI_CODE_HOME`` redirected: the verbatim ``.kimi-code/`` copy, the managed
``[[hooks]]`` block upsert (foreign config preserved, idempotent), the four executable
shims, the ``kimi:``-style doctor lines (ok / drift / missing), and profile scoping
with the out-of-profile warning.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from dadaia_workspace.core.execute_bit import PLATFORM_HAS_EXECUTE_BIT
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.runtime_config import (
    KIMI_BLOCK_BEGIN,
    KIMI_BLOCK_END,
    kimi_hook_shims,
    kimi_hooks_block,
)

pytestmark = pytest.mark.unit


@pytest.fixture()
def kimi_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "kimi-home"
    monkeypatch.setenv("KIMI_CODE_HOME", str(home))
    return home


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "ws"


def _install(workspace: Path, manager: FileSystemPublicAssetManager | None = None) -> list[str]:
    mgr = manager or FileSystemPublicAssetManager()
    mgr.stage(workspace)
    return mgr.install(workspace, target="kimi-code")


def _kimi_lines(reports: list[str]) -> list[str]:
    # Projection/wiring labels only — the unconditional `stage:kimi-code/*` staged-tree
    # compare lines are out of scope for these assertions.
    return [line for line in reports if "kimi-code" in line and "stage:kimi-code" not in line]


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------


def test_install_projects_workspace_tree_and_user_wiring(workspace: Path, kimi_home: Path) -> None:
    _install(workspace)

    projected = workspace / ".kimi-code" / "AGENTS.md"
    assert projected.is_file()
    assert "Kimi Code" in projected.read_text(encoding="utf-8")

    config = (kimi_home / "config.toml").read_text(encoding="utf-8")
    assert KIMI_BLOCK_BEGIN in config
    assert KIMI_BLOCK_END in config
    assert config.count("[[hooks]]") == 4

    for name, content in kimi_hook_shims().items():
        shim = kimi_home / "hooks" / name
        assert shim.is_file()
        assert shim.read_text(encoding="utf-8") == content
        assert os.access(shim, os.X_OK)
        if os.name != "nt":
            # POSIX-only: Windows cannot materialise Unix exec bits (os.chmod there
            # toggles only the read-only flag), so the mode assertion is POSIX-scoped.
            assert stat.S_IXUSR & shim.stat().st_mode


def test_install_preserves_foreign_config_and_is_idempotent(
    workspace: Path, kimi_home: Path
) -> None:
    kimi_home.mkdir(parents=True)
    foreign = 'default_model = "kimi-code/k3"\n\n[thinking]\nenabled = true\n'
    (kimi_home / "config.toml").write_text(foreign, encoding="utf-8")

    _install(workspace)
    once = (kimi_home / "config.toml").read_text(encoding="utf-8")
    assert once.startswith(foreign)
    assert once.count(KIMI_BLOCK_BEGIN) == 1

    # Second install: no content change, no duplicated block.
    _install(workspace)
    twice = (kimi_home / "config.toml").read_text(encoding="utf-8")
    assert twice == once


def test_install_refreshes_stale_block_and_shims(workspace: Path, kimi_home: Path) -> None:
    kimi_home.mkdir(parents=True)
    (kimi_home / "config.toml").write_text(
        f"{KIMI_BLOCK_BEGIN}\nstale = true\n{KIMI_BLOCK_END}\n", encoding="utf-8"
    )
    hooks_dir = kimi_home / "hooks"
    hooks_dir.mkdir()
    stale_shim = hooks_dir / "dadaia-kimi-pre-gate.sh"
    stale_shim.write_text("#!/usr/bin/env sh\n# stale\n", encoding="utf-8")

    _install(workspace)
    config = (kimi_home / "config.toml").read_text(encoding="utf-8")
    assert "stale = true" not in config
    assert config == kimi_hooks_block(kimi_home)
    assert stale_shim.read_text(encoding="utf-8") == kimi_hook_shims()[stale_shim.name]


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


def test_doctor_ok_after_install(workspace: Path, kimi_home: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    _install(workspace, mgr)
    reports = mgr.doctor(workspace)
    kimi = _kimi_lines(reports)
    assert any(line.startswith("[ok] kimi-code:AGENTS.md") for line in kimi)
    assert any(line.startswith("[ok] kimi-code:hooks/") for line in kimi)
    assert any(line.startswith("[ok] kimi-code:config.toml") for line in kimi)
    assert not [line for line in kimi if line.startswith(("[missing]", "[drift]"))]


def test_doctor_flags_shim_drift(workspace: Path, kimi_home: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    _install(workspace, mgr)
    shim = kimi_home / "hooks" / "dadaia-kimi-pre-gate.sh"
    shim.write_text("#!/usr/bin/env sh\n# tampered\n", encoding="utf-8")
    reports = mgr.doctor(workspace)
    assert any(
        line == "[drift] kimi-code:hooks/dadaia-kimi-pre-gate.sh" for line in _kimi_lines(reports)
    )


@pytest.mark.skipif(os.name == "nt", reason="Windows cannot clear Unix exec bits via chmod")
@pytest.mark.skipif(not PLATFORM_HAS_EXECUTE_BIT, reason="no POSIX execute bit on this platform")
def test_doctor_flags_shim_not_executable(workspace: Path, kimi_home: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    _install(workspace, mgr)
    shim = kimi_home / "hooks" / "dadaia-kimi-pre-gate.sh"
    # Restored content but lost executable bit ⇒ drift (not executable).
    shim.chmod(0o644)
    reports = mgr.doctor(workspace)
    assert any(
        line == "[drift] kimi-code:hooks/dadaia-kimi-pre-gate.sh (not executable)"
        for line in _kimi_lines(reports)
    )


def test_doctor_flags_missing_and_drifted_config_block(workspace: Path, kimi_home: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    _install(workspace, mgr)

    (kimi_home / "config.toml").unlink()
    reports = mgr.doctor(workspace)
    assert any(
        line == "[missing] kimi-code:config.toml managed hooks block"
        for line in _kimi_lines(reports)
    )

    (kimi_home / "config.toml").write_text('default_model = "k3"\n', encoding="utf-8")
    reports = mgr.doctor(workspace)
    assert any(
        line == "[drift] kimi-code:config.toml managed hooks block" for line in _kimi_lines(reports)
    )


def test_doctor_scopes_kimi_out_of_profile(workspace: Path, kimi_home: Path) -> None:
    mgr = FileSystemPublicAssetManager()
    _install(workspace, mgr)
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "harness_profile.json").write_text(
        json.dumps({"schema_version": "1", "harnesses": ["claude"]}), encoding="utf-8"
    )
    reports = mgr.doctor(workspace)
    kimi = _kimi_lines(reports)
    assert kimi == ["[warn] kimi-code: out-of-profile runtime present (drift unchecked)"]


def test_doctor_without_kimi_projection_is_silent_when_out_of_profile(
    workspace: Path, kimi_home: Path
) -> None:
    mgr = FileSystemPublicAssetManager()
    mgr.stage(workspace)
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "harness_profile.json").write_text(
        json.dumps({"schema_version": "1", "harnesses": ["claude"]}), encoding="utf-8"
    )
    reports = mgr.doctor(workspace)
    assert _kimi_lines(reports) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX mount semantics")
@pytest.mark.skipif(not PLATFORM_HAS_EXECUTE_BIT, reason="no POSIX execute bit on this platform")
def test_doctor_reports_noexec_home_as_unsupported_not_repairable_drift(
    workspace: Path, kimi_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A noexec ``KIMI_CODE_HOME`` is an environment limit, never repairable drift.

    Bug ``kimi-hooks-noexec-home-reported-as-repairable-drift``: on a host whose
    ``KIMI_CODE_HOME`` sits on a ``noexec`` mount (a tmpfs ``/tmp`` is the common case),
    the installer's ``chmod(0o755)`` succeeds and the mode bits ARE executable, but
    ``os.access(X_OK)`` honours the mount flag and returns False. The doctor called that
    ``[drift]`` — the status whose remedy is "re-run install" — so every reinstall
    reproduced it, ``reconcile`` failed with ``rollback_required`` and the certification
    gate REJECTED the candidate, unfixably.

    The mount flag cannot be simulated in-process, so the probe is the discriminator
    itself: mode bits stay 0o755 (what the installer guarantees) while ``os.access``
    denies X_OK (what the mount imposes). The reparable case — cleared exec bits — must
    stay ``[drift]``; that boundary is asserted by
    ``test_doctor_flags_shim_not_executable``.
    """
    mgr = FileSystemPublicAssetManager()
    _install(workspace, mgr)
    shim = kimi_home / "hooks" / "dadaia-kimi-pre-gate.sh"
    assert shim.stat().st_mode & stat.S_IXUSR, "installer must leave the exec bits set"

    real_access = os.access

    def noexec_access(path: object, mode: int, **kwargs: object) -> bool:
        if mode == os.X_OK and str(path).startswith(str(kimi_home)):
            return False
        return real_access(path, mode, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("dadaia_workspace.infrastructure.public_assets.os.access", noexec_access)
    lines = _kimi_lines(mgr.doctor(workspace))
    shim_lines = [line for line in lines if "hooks/dadaia-kimi-pre-gate.sh" in line]
    assert shim_lines, lines
    line = shim_lines[0]
    assert not line.startswith("[drift]"), f"a noexec mount is not repairable drift: {line!r}"
    assert line.startswith("[unsupported]"), line
    assert "noexec" in line
    assert "KIMI_CODE_HOME" in line
