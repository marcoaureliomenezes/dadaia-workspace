"""Intent: CONTRACT — sa-consumer-law-carries-library-facts (AC4.4): law projected into a
consumer names no library layer, ratchet, test file or release tool.
Size: SMALL — text reads over the packaged public tree and the canon templates.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import canon
from dadaia_workspace.infrastructure.privacy_check import PORTUGUESE_CONTROL_TERMS

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"


def _hits(paths: list[Path], pattern: str) -> list[str]:
    rx = re.compile(pattern)
    return [
        f"{p.relative_to(_PUBLIC)}:{n}"
        for p in paths
        for n, line in enumerate(p.read_text("utf-8").splitlines(), start=1)
        if rx.search(line)
    ]


def test_no_skill_prescribes_the_library_release_tooling() -> None:
    """sa-consumer-law-carries-library-facts#FR8.2: the projected dd-gitflow-default (and
    every other skill) prescribes no release-please, no `gh pr create` and no
    library-publication version rule."""
    skills = sorted((_PUBLIC / "skills").rglob("*.md"))
    assert skills
    assert _hits(skills, r"(?i)release-please|gh pr create|last tag \+ 1") == []


def test_scaffold_law_cites_no_library_ratchet_test_or_path() -> None:
    """sa-consumer-law-carries-library-facts#FR8.3: the scaffolded law and its fixed
    blocks cite no library ratchet, test file (tests/contract/test_adr_canon.py) or
    package path."""
    law = sorted((_PUBLIC / "scaffold").rglob("*.md")) + sorted(
        (_PUBLIC / "data" / "fixed").glob("*.md")
    )
    assert law
    pattern = r"ratchet V\d|test_\w+\.py|dadaia_workspace/|release-please"
    assert _hits(law, pattern) == []


def test_the_constitution_template_is_english() -> None:
    """sa-consumer-law-carries-library-facts#FR8.4: the constitution template canon.py
    scaffolds carries none of the Portuguese control vocabulary."""
    text = canon._CONSTITUTION_STUB.lower()
    assert "# constitution" in text
    assert [term for term, _ in PORTUGUESE_CONTROL_TERMS if term.lower() in text] == []
