"""Unit tests for ``dadaia_workspace.core.platform``.

Tests pass the platform to ``Capabilities.detect`` so ``PLATFORM`` is not disturbed.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.platform import PLATFORM, Capabilities


@pytest.mark.parametrize(
    ("plat", "venv_scripts_dir", "venv_exe_suffix"),
    [("linux", "bin", ""), ("darwin", "bin", ""), ("win32", "Scripts", ".exe")],
)
def test_capability_flags_golden(plat: str, venv_scripts_dir: str, venv_exe_suffix: str) -> None:
    caps = Capabilities.detect(plat)
    assert caps.venv_scripts_dir == venv_scripts_dir
    assert caps.venv_exe_suffix == venv_exe_suffix


def test_platform_singleton_frozen_and_equivalent_construction() -> None:
    assert isinstance(PLATFORM, Capabilities)
    with pytest.raises((AttributeError, TypeError)):
        PLATFORM.venv_exe_suffix = ""  # type: ignore[misc]
    assert Capabilities.detect() == PLATFORM  # no argument reads sys.platform
