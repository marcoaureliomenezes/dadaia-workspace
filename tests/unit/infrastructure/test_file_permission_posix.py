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


@pytest.mark.parametrize(
    ("target_kind", "mode_kwargs", "expected_mode", "as_string_path"),
    [
        pytest.param("file", {}, 0o600, False, id="file-default-mode"),
        pytest.param("file", {"mode": 0o400}, 0o400, False, id="file-custom-mode"),
        pytest.param("file", {}, 0o600, True, id="file-string-path"),
        pytest.param("dir", {}, 0o700, False, id="dir-default-mode"),
        pytest.param("dir", {"mode": 0o500}, 0o500, False, id="dir-custom-mode"),
    ],
)
def test_restrict_to_owner(
    tmp_path: Path,
    target_kind: str,
    mode_kwargs: dict[str, int],
    expected_mode: int,
    as_string_path: bool,
) -> None:
    """restrict_to_owner()/restrict_dir_to_owner() apply the expected chmod mode,
    honoring a custom mode= override and accepting str or Path targets."""
    from dadaia_workspace.infrastructure.file_permission_posix import PosixFilePermissionSetter

    setter = PosixFilePermissionSetter()

    if target_kind == "file":
        target = tmp_path / "secret.token"
        target.write_text("tok", encoding="utf-8")
        os.chmod(target, 0o644)  # start wider
        arg = str(target) if as_string_path else target
        setter.restrict_to_owner(arg, **mode_kwargs)
    else:
        target = tmp_path / "state"
        target.mkdir()
        os.chmod(target, 0o755)  # start wider
        setter.restrict_dir_to_owner(target, **mode_kwargs)

    assert target.stat().st_mode & 0o777 == expected_mode, (
        f"Expected {oct(expected_mode)}, got {oct(target.stat().st_mode & 0o777)}"
    )
