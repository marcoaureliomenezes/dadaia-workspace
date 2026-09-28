"""Intent: CONTRACT — sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges#47.4.

Shipped text (``dadaia_workspace/public/**``) never names memory sections "Part 1" /
"Part 2": the memory vocabulary is Principles / Tech Stack / Structure and Principles /
Test architecture / Gates. Negative fixtures under ``tests/`` are out of scope.
Size: SMALL.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"


def test_47_4_shipped_text_carries_no_part_1_part_2_vocabulary() -> None:
    hits = [
        f"{path.relative_to(_PUBLIC)}:{n}"
        for path in sorted(_PUBLIC.rglob("*"))
        if path.is_file() and path.suffix in {".md", ".json", ".py", ".toml", ".txt", ".sh"}
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "Part 1" in line or "Part 2" in line
    ]
    assert hits == []
