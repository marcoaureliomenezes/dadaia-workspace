#!/usr/bin/env python3
"""The one refusal every skill script raises and catches: a message and its one `fix:` line."""

from __future__ import annotations

import subprocess
import sys
from typing import TextIO


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


FIX = "fix: "


def spell_fix(fix: str) -> str:
    """The one spelling of a `fix:` line."""
    return f"{FIX}{fix}"


def fix_of(text: str, default: str = "") -> str:
    """The first `fix:` line of a child script's *text*, else *default*: the one parser."""
    return next((ln[len(FIX) :] for ln in text.splitlines() if ln.startswith(FIX)), default)


def relay(done: subprocess.CompletedProcess[str], message: str, fix: str) -> None:
    """Raises `Refusal` when child *done* exited non-zero: its own first `fix:` line, else *fix*."""
    if done.returncode:
        raise Refusal(message, fix_of(done.stdout + done.stderr, fix))


def without_fix(text: str) -> str:
    """*text* with its `fix:` lines removed."""
    return "".join(ln for ln in text.splitlines(True) if not ln.startswith(FIX))


def report(message: object, fix: str, file: TextIO | None = None) -> None:
    """Print the one `[error]` line and the one `fix:` line of a refusal (default stderr)."""
    print(f"[error] {message}", spell_fix(fix), sep="\n", file=file or sys.stderr)
