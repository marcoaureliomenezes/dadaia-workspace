"""Unit tests for ``dadaia_workspace.core.platform``.

Tests monkeypatch ``sys.platform`` by passing the value directly to
``detect()`` so the module-level ``PLATFORM`` singleton is not disturbed.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import PLATFORM, Capabilities, detect


@pytest.mark.parametrize(
    (
        "plat",
        "has_fcntl",
        "has_proc_fs",
        "has_posix_chmod",
        "has_sigterm",
        "has_os_kill_liveness",
        "venv_scripts_dir",
        "venv_exe_suffix",
    ),
    [
        ("linux", True, True, True, True, True, "bin", ""),
        ("darwin", True, False, True, True, True, "bin", ""),  # /proc not available on macOS
        ("win32", False, False, False, False, False, "Scripts", ".exe"),
    ],
)
def test_capability_flags_golden(
    plat: str,
    has_fcntl: bool,
    has_proc_fs: bool,
    has_posix_chmod: bool,
    has_sigterm: bool,
    has_os_kill_liveness: bool,
    venv_scripts_dir: str,
    venv_exe_suffix: str,
) -> None:
    caps = detect(plat)
    assert caps.has_fcntl is has_fcntl
    assert caps.has_proc_fs is has_proc_fs
    assert caps.has_posix_chmod is has_posix_chmod
    assert caps.has_sigterm is has_sigterm
    assert caps.has_os_kill_liveness is has_os_kill_liveness
    assert caps.venv_scripts_dir == venv_scripts_dir
    assert caps.venv_exe_suffix == venv_exe_suffix
    assert isinstance(caps.tmp_dir, Path)
    if plat == "linux":
        # The canonical temp dir must match tempfile.gettempdir() on the host platform.
        assert str(caps.tmp_dir) == tempfile.gettempdir()


def test_platform_singleton_frozen_and_equivalent_construction() -> None:
    assert isinstance(PLATFORM, Capabilities)
    with pytest.raises((AttributeError, TypeError)):
        PLATFORM.has_fcntl = False  # type: ignore[misc]
    # Classmethod vs module-level function are equivalent for every known platform.
    for plat in ("linux", "darwin", "win32"):
        assert detect(plat) == Capabilities.detect(plat)
    # detect() with no argument reads sys.platform (smoke).
    result = detect()
    assert isinstance(result, Capabilities)
