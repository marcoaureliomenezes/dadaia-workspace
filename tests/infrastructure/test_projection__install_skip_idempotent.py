"""Contract test: a rule's projected bytes are LF-exact and idempotent.

The retired ``write_generated`` free function is superseded by the ONE
``ProjectionRule``/``install_rules`` seam (``infrastructure/projection.py``) — every
generated projection (settings.json, config.toml, ...) now flows through it. The
invariant this pins is now structurally guaranteed rather than merely tested:
``install_rules`` always calls ``atomic_write(rule.dst, desired)`` with *desired* typed
``bytes`` (never ``str``), so binary mode applies unconditionally and no newline
translation can occur on any OS. A text-mode writer once made Windows newline translation (``\n`` -> ``\r\n``) defeat the
hash-compare "skip when content matches" optimisation; this test pins that it cannot.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.projection import ProjectionRule, install_rules

_CONTENT = "line-one\nline-two\nline-three\n"


def test_rule_bytes_are_lf_exact_and_second_write_skips(tmp_path: Path) -> None:
    """A rule's rendered bytes on disk equal content.encode('utf-8') exactly (no CRLF
    translation), and a second install of identical content is a no-op (skip)."""
    dst = tmp_path / "settings.json"

    def _render(_current: bytes | None) -> bytes:
        return _CONTENT.encode("utf-8")

    rule = ProjectionRule(label="test:settings.json", harness="claude", dst=dst, render=_render)
    install_rules((rule,), force=False)

    # Binary read: no universal-newline translation. Must equal the LF content exactly,
    # even on Windows. A "\r\n" anywhere here is the regression this guards against.
    assert dst.read_bytes() == _CONTENT.encode("utf-8")
    assert b"\r\n" not in dst.read_bytes()

    mtime_before = dst.stat().st_mtime_ns
    transcript = install_rules((rule,), force=False)

    assert transcript.lines[0].status == "skip", (
        "identical content must skip — the hash-compare must match on every OS"
    )
    assert dst.stat().st_mtime_ns == mtime_before, "skipped file must not be rewritten"
