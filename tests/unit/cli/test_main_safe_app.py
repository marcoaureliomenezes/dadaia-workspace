"""Unit tests for _safe_app() fallback behavior — T-018-08.

Verifies that ``_safe_app()`` derives the bug-report fallback directory from
``PLATFORM.tmp_dir`` rather than a hardcoded ``/tmp`` path.  The test is
platform-neutral: it monkeypatches ``PLATFORM`` to a custom ``tmp_dir`` and
asserts that the fallback path uses that value — i.e. the literal string
``"/tmp"`` is NOT hardcoded.

This test intentionally does NOT import fcntl and does NOT use importorskip —
``_safe_app``'s fallback path selection must work on all platforms.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def test_safe_app_fallback_uses_platform_tmp_dir(tmp_path: Path) -> None:
    """_safe_app() must derive the bug-fallback dir from PLATFORM.tmp_dir.

    Monkeypatches PLATFORM to expose a custom tmp_dir so we can assert that
    the fallback path uses the platform abstraction — NOT the literal string
    ``/tmp``.

    Raises:
        AssertionError: if the fallback path is hardcoded to ``/tmp/...``.
    """
    from dadaia_workspace.core.platform import Capabilities

    custom_tmp = tmp_path / "custom_tmp"
    custom_tmp.mkdir()

    # Build a Capabilities snapshot whose tmp_dir points to our custom path.
    platform_caps = Capabilities(
        has_fcntl=True,
        has_proc_fs=True,
        has_posix_chmod=True,
        has_sigterm=True,
        venv_scripts_dir="bin",
        venv_exe_suffix="",
        tmp_dir=custom_tmp,
    )

    # Capture the path passed to report_exception.
    captured_paths: list[Path] = []

    def _fake_report_exc(workspace_root: Path, command: str, exc: Exception) -> None:
        captured_paths.append(workspace_root)

    with (
        patch("dadaia_workspace.cli.main.PLATFORM", platform_caps),
        patch(
            "dadaia_workspace.cli.main.resolve_workspace_root",
            side_effect=__import__(
                "dadaia_workspace.core.exceptions",
                fromlist=["WorkspaceNotInitializedError"],
            ).WorkspaceNotInitializedError("no workspace"),
        ),
        patch("dadaia_workspace.cli.main._report_exc", _fake_report_exc),
        patch("dadaia_workspace.cli.main.app", side_effect=RuntimeError("boom")),
    ):
        import pytest as _pytest

        with _pytest.raises(RuntimeError, match="boom"):
            from dadaia_workspace.cli.main import _safe_app

            _safe_app()

    assert captured_paths, "_report_exc was never called — fallback path was not exercised."
    fallback = captured_paths[0]

    # The fallback must derive from PLATFORM.tmp_dir (the monkeypatched custom_tmp),
    # proving cli/main.py uses the platform seam rather than a hardcoded path. We do
    # NOT assert the absence of the literal "/tmp" substring: pytest's tmp_path lives
    # under /tmp on Linux, so custom_tmp legitimately contains it — the meaningful,
    # portable assertion is that the path is rooted at PLATFORM.tmp_dir.
    assert str(fallback).startswith(str(custom_tmp)), (
        f"Fallback path '{fallback}' does not start with the monkeypatched "
        f"PLATFORM.tmp_dir '{custom_tmp}'. "
        "cli/main.py must route the fallback through PLATFORM.tmp_dir, not a hardcoded path."
    )
    # And it must be the dadaia-bugs leaf under that platform tmp dir.
    assert fallback == custom_tmp / "dadaia-bugs", (
        f"Fallback path '{fallback}' is not PLATFORM.tmp_dir / 'dadaia-bugs'."
    )
