"""Contract test: pyproject.toml declares the correct OS classifiers (T-018-08 / T-018-30).

After the 0.1.8 rc-2 Windows graduation (the cross-platform unit + contract CI legs
are green and hard-gated on Linux, macOS, and Windows), pyproject.toml advertises all
three supported operating systems via explicit per-OS classifiers — NOT the over-broad
``OS Independent`` (which would dishonestly imply every OS works without evidence).

The test reads ``pyproject.toml`` via ``tomllib`` (stdlib since Python 3.11) so it
does NOT require Poetry or any external tool to be installed.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

# The three OSes whose unit + contract CI legs are hard-gated green (T-018-30).
_REQUIRED_OS_CLASSIFIERS = (
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",
)


def _pyproject_path() -> Path:
    """Return the absolute path to ``pyproject.toml`` in the repo root."""
    # This file is at tests/contract/test_platform_classifier.py
    # Repo root is three levels up.
    return Path(__file__).resolve().parents[2] / "pyproject.toml"


def _classifiers() -> list[str]:
    pyproject_path = _pyproject_path()
    assert pyproject_path.exists(), (
        f"pyproject.toml not found at {pyproject_path}. Run this test from the repository root."
    )
    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)
    result: list[str] = data.get("tool", {}).get("poetry", {}).get("classifiers", [])
    return result


def test_os_classifiers_cover_linux_macos_windows_and_exclude_os_independent() -> None:
    """pyproject.toml must declare the three supported OS classifiers (matching the
    hard-gated CI matrix after 0.1.8 rc-2 graduation) and must NOT carry the
    over-broad ``OS Independent`` classifier (which would dishonestly imply every OS
    works without evidence)."""
    classifiers = _classifiers()
    for target in _REQUIRED_OS_CLASSIFIERS:
        assert target in classifiers, (
            f"Missing classifier '{target}' in pyproject.toml. Found: {classifiers!r}. "
            "pyproject.toml must declare every OS whose CI legs are hard-gated green."
        )
    over_broad = "Operating System :: OS Independent"
    assert over_broad not in classifiers, (
        f"Found over-broad classifier '{over_broad}' in pyproject.toml. "
        "Declare the specific supported OSes (Linux/macOS/Windows) instead."
    )
