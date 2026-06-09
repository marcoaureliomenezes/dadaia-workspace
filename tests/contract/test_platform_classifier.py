"""Contract test: pyproject.toml declares the correct OS classifier (T-018-08).

Verifies that the ``Operating System`` classifier in ``pyproject.toml`` is set to
``Operating System :: POSIX :: Linux`` — the honest classifier after the cross-platform
work in release 0.1.8 (Phase 1).  This is an honest statement of the currently
supported platform while the Windows/macOS porting work is in progress.

The test reads ``pyproject.toml`` via ``tomllib`` (stdlib since Python 3.11) so it
does NOT require Poetry or any external tool to be installed.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract


def _pyproject_path() -> Path:
    """Return the absolute path to ``pyproject.toml`` in the repo root."""
    # This file is at tests/contract/test_platform_classifier.py
    # Repo root is three levels up.
    return Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_os_classifier_is_posix_linux() -> None:
    """pyproject.toml must declare ``Operating System :: POSIX :: Linux``.

    This is the authoritative classifier for Phase 1 of the cross-platform
    porting work (0.1.8 alpha-1).  The test fails if the classifier is absent
    or if an over-broad ``OS Independent`` classifier is still present.
    """
    pyproject_path = _pyproject_path()
    assert pyproject_path.exists(), (
        f"pyproject.toml not found at {pyproject_path}. Run this test from the repository root."
    )

    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)

    classifiers: list[str] = data.get("tool", {}).get("poetry", {}).get("classifiers", [])

    target = "Operating System :: POSIX :: Linux"
    assert target in classifiers, (
        f"Missing classifier '{target}' in pyproject.toml. "
        f"Found classifiers: {classifiers!r}. "
        "The pyproject.toml must honestly declare the supported OS after the "
        "cross-platform porting work in release 0.1.8."
    )

    # Also assert the over-broad classifier is absent.
    over_broad = "Operating System :: OS Independent"
    assert over_broad not in classifiers, (
        f"Found over-broad classifier '{over_broad}' in pyproject.toml. "
        "Remove it — the package requires POSIX (Phase 1 honest classification)."
    )
