"""Unit tests for ``dadaia_workspace.core.platform``.

Tests monkeypatch ``sys.platform`` by passing the value directly to
``detect()`` so the module-level ``PLATFORM`` singleton is not disturbed.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.platform import PLATFORM, Capabilities, detect


@pytest.mark.parametrize(
    ("plat", "venv_scripts_dir", "venv_exe_suffix"),
    [("linux", "bin", ""), ("darwin", "bin", ""), ("win32", "Scripts", ".exe")],
)
def test_capability_flags_golden(plat: str, venv_scripts_dir: str, venv_exe_suffix: str) -> None:
    caps = detect(plat)
    assert caps.venv_scripts_dir == venv_scripts_dir
    assert caps.venv_exe_suffix == venv_exe_suffix


def test_platform_singleton_frozen_and_equivalent_construction() -> None:
    assert isinstance(PLATFORM, Capabilities)
    with pytest.raises((AttributeError, TypeError)):
        PLATFORM.venv_exe_suffix = ""  # type: ignore[misc]
    # Classmethod vs module-level function are equivalent for every known platform.
    for plat in ("linux", "darwin", "win32"):
        assert detect(plat) == Capabilities.detect(plat)
    # detect() with no argument reads sys.platform (smoke).
    result = detect()
    assert isinstance(result, Capabilities)
