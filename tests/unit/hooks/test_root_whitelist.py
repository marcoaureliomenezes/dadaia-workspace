"""Root whitelist hook policy regressions."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.hooks import root_whitelist


def test_nested_forbidden_root_entry_is_blocked(tmp_path: Path) -> None:
    message = root_whitelist._root_violation(  # noqa: SLF001 - pure policy regression
        tmp_path, str(tmp_path / ".opencode" / "agents" / "x.md")
    )

    assert message is not None
    assert ".opencode" in message


def test_nested_allowed_root_entry_is_allowed(tmp_path: Path) -> None:
    assert (
        root_whitelist._root_violation(  # noqa: SLF001 - pure policy regression
            tmp_path, str(tmp_path / ".dadaia" / "tmp" / "x.txt")
        )
        is None
    )
