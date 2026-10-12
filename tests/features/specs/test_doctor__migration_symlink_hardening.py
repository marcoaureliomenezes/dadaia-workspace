"""A corrupt or oversized shipped-hashes history degrades to "nothing is provably ours" rather than crashing the doctor."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.template_history import (
    SHIPPED_HASHES_FILENAME,
    load_shipped_hashes,
)


def test_corrupt_history_degrades_instead_of_killing_the_doctor(tmp_path: Path) -> None:
    """A deeply nested history blows the JSON parser's stack; it must degrade to "nothing
    is provably ours" like every other malformation."""
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / SHIPPED_HASHES_FILENAME).write_text("[" * 200_000, encoding="utf-8")

    assert load_shipped_hashes(templates) == {}
