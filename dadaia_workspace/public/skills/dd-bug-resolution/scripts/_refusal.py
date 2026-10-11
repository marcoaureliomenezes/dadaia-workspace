#!/usr/bin/env python3
"""The one refusal every skill script raises and catches: a message and its one `fix:` line."""

from __future__ import annotations


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix
