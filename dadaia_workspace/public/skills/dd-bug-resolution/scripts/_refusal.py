#!/usr/bin/env python3
"""The one refusal every skill script raises and catches: a message and its one `fix:` line."""

from __future__ import annotations

import sys
from typing import TextIO


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


def report(message: object, fix: str, file: TextIO | None = None) -> None:
    """Print the one `[error]` line and the one `fix:` line of a refusal (default stderr)."""
    print(f"[error] {message}", f"fix: {fix}", sep="\n", file=file or sys.stderr)
