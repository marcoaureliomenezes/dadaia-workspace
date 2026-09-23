"""Backlog cli-help-architecture-and-session-injection (T-053-24): the CLI digest is
DERIVED from the live command tree — one source, never transcribed. Intent: contract;
size: unit."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.cli.help_digest import _MAX_CHARS, render_digest, write_digest


def test_digest_derives_from_the_live_tree_within_budget() -> None:
    text = render_digest()
    assert len(text) <= _MAX_CHARS, "digest must stay within the ~4k-token budget"
    # Derived and grounded in real groups; no version, which is not a fact of the tree —
    # a version bump must never drift the committed docs/cli.md.
    assert text.startswith("<!-- derived-from: dadaia help tree")
    assert text.splitlines()[2].startswith(
        "# dadaia CLI digest (derived from the live command tree"
    )
    assert "(v" not in text.splitlines()[2]
    for group in ("context", "specs", "doctor", "public", "help"):
        assert f"## dadaia {group}" in text or f"- {group} " in text, group
    # The one retired phantom the old hand-written skill documented.
    assert "specs hotfix" not in text


def test_write_digest_skips_an_identical_file(tmp_path: Path) -> None:
    first = write_digest(tmp_path)
    assert first is not None and first.is_file()
    mtime = first.stat().st_mtime_ns
    second = write_digest(tmp_path)
    assert second == first
    assert first.stat().st_mtime_ns == mtime, "an identical digest must skip the rewrite"


def test_write_digest_fails_soft(tmp_path: Path) -> None:
    blocker = tmp_path / ".dadaia"
    blocker.write_text("not a dir", encoding="utf-8")
    assert write_digest(tmp_path) is None
