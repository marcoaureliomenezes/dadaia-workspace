"""sa-backlog-status-has-no-single-authority#B7: no law or skill names
the `picked` status or `**Consumes:**` — the pick is the SPEC's `**Origin:** backlog:`
line. Size: SMALL.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import dadaia_workspace

pytestmark = pytest.mark.contract

_PUBLIC = Path(dadaia_workspace.__file__).resolve().parent / "public"


def test_no_law_or_skill_names_the_picked_status_or_consumes() -> None:
    pattern = re.compile(r"status: picked|`picked`|\*\*Consumes:\*\*")
    hits = [
        f"{p.relative_to(_PUBLIC)}:{n}"
        for p in _PUBLIC.rglob("*.md")
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if pattern.search(line)
    ]
    assert hits == []
