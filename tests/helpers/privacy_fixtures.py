"""Pattern-shaped fixture values, composed at runtime from parts.

Intent: CONTRACT — v0.4.7 FR7 (T-047-22)

This repository is PUBLIC: every pushed blob is published, so the push-range denylist
scan stays FULL on every tracked path — ``tests/**`` included. Until v0.4.7 that scope
was made liveable by a hand-kept list of 23 tolerated ``(path, baseline pattern)``
pairs (``_TESTS_SCOPE_BASELINE``): a SECOND scope decision that had to be edited every
time a fixture was added, moved or renamed — the structural cause of the measured
26-bug privacy-scan loop, in which every fix was one more literal/baseline/regex edit.

The structural fix is that no tracked fixture FILE carries a literal any pattern
matches. A test that merely needs *a* home path, address or mailbox uses a value the
baseline already excludes by design (``/home/user``, the RFC 5737 documentation
ranges, ``@example.invalid``) written inline. A test that must prove the SCANNER FIRES
on a realistic shape calls one of the builders below: the shape exists only in memory,
at run time, and the assertion it feeds is unchanged.

Every builder returns a synthetic, non-identifying value.
"""

from __future__ import annotations

__all__ = [
    "aws_key_shape",
    "internal_host",
    "macos_home_path",
    "private_ip",
    "windows_home_path",
]


def aws_key_shape() -> str:
    """An ``AKIA``-prefixed access-key-id shape matching the ``secret-token``
    pattern — the 4-char prefix plus the 16 uppercase characters it requires."""
    return "AKIA" + "X" * 16


def private_ip() -> str:
    """An RFC 1918 address matching the ``ipv4-literal`` pattern — deliberately NOT
    one of the documentation ranges the baseline excludes, because the whole point of
    a caller reaching for this builder is that the pattern must FIRE."""
    return ".".join(("10", "99", "99", "99"))


def internal_host(label: str) -> str:
    """*label* under the ``.internal`` TLD class the ``internal-hostname`` pattern
    matches (``bastion``, ``db``, ``db-primary`` …)."""
    return label + "." + "internal"


def macos_home_path() -> str:
    """A ``users-abs-path`` match — the synthetic, non-identifying macOS home of
    ``zz-fixture-user``, which the baseline's placeholder carve-out does NOT cover."""
    return "/Users/" + "zz-fixture-user"


def windows_home_path() -> str:
    """A ``windows-users-path`` match — the same synthetic name under the Windows
    profile root."""
    return "C:\\Users\\" + "zz-fixture-user"
