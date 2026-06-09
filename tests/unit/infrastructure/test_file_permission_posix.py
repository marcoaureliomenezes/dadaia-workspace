"""Unit tests for infrastructure/file_permission_posix.py.

POSIX-only: all tests skip on Windows (no os.chmod effect there).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX chmod tests are meaningless on Windows",
)


def test_restrict_to_owner_sets_0o600(tmp_path: Path) -> None:
    """restrict_to_owner() applies mode 0o600 to a file."""
    from dadaia_workspace.infrastructure.file_permission_posix import PosixFilePermissionSetter

    f = tmp_path / "secret.token"
    f.write_text("tok", encoding="utf-8")
    os.chmod(f, 0o644)  # start wider

    setter = PosixFilePermissionSetter()
    setter.restrict_to_owner(f)

    assert f.stat().st_mode & 0o777 == 0o600, f"Expected 0o600, got {oct(f.stat().st_mode & 0o777)}"


def test_restrict_to_owner_custom_mode(tmp_path: Path) -> None:
    """restrict_to_owner() accepts a custom mode argument."""
    from dadaia_workspace.infrastructure.file_permission_posix import PosixFilePermissionSetter

    f = tmp_path / "data.bin"
    f.write_text("x", encoding="utf-8")
    setter = PosixFilePermissionSetter()
    setter.restrict_to_owner(f, mode=0o400)

    assert f.stat().st_mode & 0o777 == 0o400


def test_restrict_dir_to_owner_sets_0o700(tmp_path: Path) -> None:
    """restrict_dir_to_owner() applies mode 0o700 to a directory."""
    from dadaia_workspace.infrastructure.file_permission_posix import PosixFilePermissionSetter

    d = tmp_path / "state"
    d.mkdir()
    os.chmod(d, 0o755)  # start wider

    setter = PosixFilePermissionSetter()
    setter.restrict_dir_to_owner(d)

    assert d.stat().st_mode & 0o777 == 0o700, f"Expected 0o700, got {oct(d.stat().st_mode & 0o777)}"


def test_restrict_dir_to_owner_custom_mode(tmp_path: Path) -> None:
    """restrict_dir_to_owner() accepts a custom mode argument."""
    from dadaia_workspace.infrastructure.file_permission_posix import PosixFilePermissionSetter

    d = tmp_path / "locked"
    d.mkdir()
    setter = PosixFilePermissionSetter()
    setter.restrict_dir_to_owner(d, mode=0o500)

    assert d.stat().st_mode & 0o777 == 0o500


def test_restrict_to_owner_accepts_string_path(tmp_path: Path) -> None:
    """restrict_to_owner() works with a string path (not just Path)."""
    from dadaia_workspace.infrastructure.file_permission_posix import PosixFilePermissionSetter

    f = tmp_path / "s.token"
    f.write_text("t", encoding="utf-8")
    setter = PosixFilePermissionSetter()
    setter.restrict_to_owner(str(f))

    assert f.stat().st_mode & 0o777 == 0o600
