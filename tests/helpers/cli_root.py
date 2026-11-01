"""The live CLI root command, built once, for tests that walk the command tree."""

from __future__ import annotations

import functools

from typer.main import get_command

from dadaia_workspace.cli.main import app


@functools.cache
def live_root() -> object:
    return get_command(app)
