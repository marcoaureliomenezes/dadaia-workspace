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
    its venv at a path holding a blank: `inline` quotes (or names) that path where a raw join,
    and on win32 `command`, do not. Returns the expected text of ``cli_words(None, *words)``."""
    venv = Path("/a b/.dadaia/.venv")
    monkeypatch.setattr(
        "dadaia_workspace.core.platform.PLATFORM", Capabilities.detect(request.param)
    )
    monkeypatch.setattr("dadaia_workspace.core.platform.venv_dir", lambda _root: venv)
    monkeypatch.setattr("sys.prefix", str(venv))

    def expected(*words: str) -> str:
        return inline(*cli_words(None, *words), caps=detect(request.param))

    return expected
