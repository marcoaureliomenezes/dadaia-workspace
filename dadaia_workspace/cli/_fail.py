"""The ONE printer of a CLI refusal: plain ``print`` — never wrapped at the terminal
width, never parsed as markup — so a ``fix:`` line reaches a non-TTY caller (every agent
harness) as one runnable line."""

from __future__ import annotations

import sys
from typing import NoReturn

import typer


def fail(error: object) -> NoReturn:
    """Print ``Error: <error>`` to stderr and exit 1."""
    print(f"Error: {error}", file=sys.stderr)
    raise typer.Exit(1) from None
