"""Unit tests for ``dadaia_workspace.core.platform``.

Tests monkeypatch ``sys.platform`` by passing the value directly to
``detect()`` so the module-level ``PLATFORM`` singleton is not disturbed.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import PLATFORM, Capabilities, detect

# ---------------------------------------------------------------------------
# Sanity check for the module-level singleton (Linux runner)
# ---------------------------------------------------------------------------


def test_platform_singleton_is_capabilities_instance() -> None:
    assert isinstance(PLATFORM, Capabilities)


def test_platform_singleton_is_frozen() -> None:
    with pytest.raises((AttributeError, TypeError)):
        PLATFORM.has_fcntl = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Linux detection
# ---------------------------------------------------------------------------


def test_linux_flags() -> None:
    caps = detect("linux")
    assert caps.has_fcntl is True
    assert caps.has_proc_fs is True
    assert caps.has_posix_chmod is True
    assert caps.has_sigterm is True
    assert caps.venv_scripts_dir == "bin"
    assert caps.venv_exe_suffix == ""


def test_linux_tmp_dir_is_path() -> None:
    caps = detect("linux")
    assert isinstance(caps.tmp_dir, Path)
    # The canonical temp dir must match tempfile.gettempdir().
    assert str(caps.tmp_dir) == tempfile.gettempdir()


# ---------------------------------------------------------------------------
# macOS / darwin detection
# ---------------------------------------------------------------------------


def test_darwin_flags() -> None:
    caps = detect("darwin")
    assert caps.has_fcntl is True
    assert caps.has_proc_fs is False  # /proc not available on macOS
    assert caps.has_posix_chmod is True
    assert caps.has_sigterm is True
    assert caps.venv_scripts_dir == "bin"
    assert caps.venv_exe_suffix == ""


# ---------------------------------------------------------------------------
# Windows detection
# ---------------------------------------------------------------------------


def test_win32_flags() -> None:
    caps = detect("win32")
    assert caps.has_fcntl is False
    assert caps.has_proc_fs is False
    assert caps.has_posix_chmod is False
    assert caps.has_sigterm is False
    assert caps.venv_scripts_dir == "Scripts"
    assert caps.venv_exe_suffix == ".exe"


def test_win32_tmp_dir_is_path() -> None:
    caps = detect("win32")
    assert isinstance(caps.tmp_dir, Path)


# ---------------------------------------------------------------------------
# Classmethod vs module-level function are equivalent
# ---------------------------------------------------------------------------


def test_detect_function_and_classmethod_agree() -> None:
    for plat in ("linux", "darwin", "win32"):
        assert detect(plat) == Capabilities.detect(plat)


# ---------------------------------------------------------------------------
# detect() with no argument reads sys.platform (smoke)
# ---------------------------------------------------------------------------


def test_detect_no_arg_returns_capabilities() -> None:
    result = detect()
    assert isinstance(result, Capabilities)
