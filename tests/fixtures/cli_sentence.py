"""Fixtures shared by the features tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import cli_words
from dadaia_workspace.core.platform import Capabilities
from tests.helpers.oslib import detect, inline


@pytest.fixture(params=["linux", "win32"])
def sentence(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Callable[..., str]:
    """Words of the workspace CLI rendered for a sentence on a posix and on a faked win32 host,
    the venv at a path holding a blank: `inline` quotes (or names) that path where a raw join,
    and on win32 `command`, do not. ``expected(root, *words)`` is the text of the CLI of *root*'s
    workspace, or of the running venv (``sys.prefix``, a blank path of its own) when *root* is
    ``None``; a site that names the wrong one of the two differs."""
    running = Path("/p q/running venv")
    monkeypatch.setattr(
        "dadaia_workspace.core.platform.PLATFORM", Capabilities.detect(request.param)
    )
    monkeypatch.setattr("sys.prefix", str(running))

    def expected(root: Path | None, *words: str) -> str:
        return inline(*cli_words(root, *words), caps=detect(request.param))

    return expected
