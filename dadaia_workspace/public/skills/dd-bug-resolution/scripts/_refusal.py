#!/usr/bin/env python3
"""The one refusal every skill script raises and catches: a message and its one `fix:` line."""

from __future__ import annotations

import re
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


def check_refusal(out: str) -> Refusal | None:
    """The Refusal a `release.py check` run states, its `[error]` or finding line and its `fix:` line, else None."""
    m = re.search(r"^(?:\S+ error |\[error\] )(.*)$", out, re.M)
    return Refusal(m[1], fix_of(out)) if m else None


def without_fix(text: str) -> str:
    """*text* with its `fix:` lines removed."""
    return "".join(ln for ln in text.splitlines(True) if not ln.startswith(FIX))


def report(message: object, fix: str, file: TextIO | None = None) -> None:
    """Print the one `[error]` line and the one `fix:` line of a refusal (default stderr)."""
    print(f"[error] {message}", spell_fix(fix), sep="\n", file=file or sys.stderr)
