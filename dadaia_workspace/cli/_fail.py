"""The ONE printer of a CLI refusal: plain ``print`` — never wrapped at the terminal
width, never parsed as markup — so a ``fix:`` line reaches a non-TTY caller (every agent
harness) as one runnable line."""

from __future__ import annotations

import sys
from typing import NoReturn

import typer


def print_error(error: object) -> None:
    """``Error: <error>`` on stderr — the one rendering of a refusal."""
    print(f"Error: {error}", file=sys.stderr)


def fail(error: object, fix: str = "") -> NoReturn:
    """Print the refusal and exit 1: ``fix:`` is the error's own fix, else the caller's, else none."""
    print_error(error)
    if not getattr(error, "fix", "") and fix:
        print(f"fix: {fix}", file=sys.stderr)
    raise typer.Exit(1) from None
