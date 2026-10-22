"""Unit tests for ``dadaia_workspace.core.platform``.

Tests pass the platform to ``Capabilities.detect`` so ``PLATFORM`` is not disturbed.
"""

from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath

import pytest

from dadaia_workspace.core import platform
from dadaia_workspace.core.platform import PLATFORM, Capabilities
from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers import oslib


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


@pytest.mark.medium
def test_importing_the_door_loads_no_dataclasses() -> None:
    code = (
        "import sys\nsys.modules.pop('dataclasses', None)\n"
        "import dadaia_workspace.core.platform\nprint('dataclasses' in sys.modules)"
    )
    assert oslib.run([sys.executable, "-c", code], check=True).stdout.strip() == "False"


_NO_CAPS_NEEDED = [
    "Undecodable", "decode", "effective_uid", "file_owner", "is_link", "link",
    "make_writable", "norm_sep", "popen", "popen_bytes", "read_text", "replace", "run",
    "run_bytes", "use_utf8_stdio", "write_text", "can_write",
]  # fmt: skip


@pytest.mark.parametrize("name", _NO_CAPS_NEEDED)
def test_the_door_hands_out_the_kernels_own_function(name: str) -> None:
    owner = load_owner("dd-bug-resolution", "_platform")
    assert getattr(platform, name) is getattr(owner, name)


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("quote", ("a b",)),
        ("head", ("C:/a b/x",)),
        ("command", ("C:/a b/x", "c d")),
        ("is_fully_qualified", ("\\tools",)),
        ("canonical_cli", ("x .venv/Scripts/dadaia.exe",)),
        ("cli_words", (PurePosixPath("/w"), "doctor")),
        ("mkdir_line", (PurePosixPath("/a b/c"),)),
        ("home_env", (Path("/h"),)),
        ("python_in", (PurePosixPath("/v"),)),
    ],
)
def test_the_door_feeds_the_kernel_the_platform_it_holds(
    name: str, args: tuple[object, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = load_owner("dd-bug-resolution", "_platform")
    monkeypatch.setattr(platform, "PLATFORM", Capabilities.detect("win32"))
    assert getattr(platform, name)(*args) == getattr(owner, name)(*args, caps=owner.detect("win32"))
