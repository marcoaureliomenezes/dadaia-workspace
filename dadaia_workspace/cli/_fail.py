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


def fail(error: object) -> NoReturn:
    """Print the refusal (:func:`print_error`) and exit 1."""
    print_error(error)
    raise typer.Exit(1) from None
