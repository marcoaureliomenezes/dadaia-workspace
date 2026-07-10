"""Contract test: write_generated is idempotent across newline conventions (FR-RC2-2).

The public-asset installer's hash-compare "skip when content matches" optimisation
must hold on every OS. It hashes ``content.encode("utf-8")`` (LF) against a *binary*
read of the destination, so the bytes written to disk must equal that LF content.
Before 0.1.8 rc-2 the atomic writer wrote in text mode, so Windows newline
translation (``\n`` -> ``\r\n``) made the hashes never match and every ``install``
rewrote every generated file.

These contract tests pin the invariant directly (no OS-specific skips): the bytes on
disk are exactly the LF content, and a second write of identical content is skipped.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.install_helpers import write_generated

pytestmark = pytest.mark.contract

_CONTENT = "line-one\nline-two\nline-three\n"


def test_generated_bytes_are_lf_exact_and_second_write_skips(tmp_path: Path) -> None:
    """write_generated leaves on-disk bytes == content.encode('utf-8') (no CRLF
    translation), and a second write of identical content is a no-op (skip)."""
    dst = tmp_path / "settings.json"
    write_generated(dst, _CONTENT, force=False, installed=[])

    # Binary read: no universal-newline translation. Must equal the LF content exactly,
    # even on Windows. A "\r\n" anywhere here is the regression FR-RC2-2 guards against.
    assert dst.read_bytes() == _CONTENT.encode("utf-8")
    assert b"\r\n" not in dst.read_bytes()

    mtime_before = dst.stat().st_mtime_ns
    second: list[str] = []
    write_generated(dst, _CONTENT, force=False, installed=second)

    assert any("[skip]" in entry for entry in second), (
        "identical content must skip — the hash-compare must match on every OS"
    )
    assert not any("[ok]" in entry for entry in second), "no rewrite expected on a skip"
    assert dst.stat().st_mtime_ns == mtime_before, "skipped file must not be rewritten"
