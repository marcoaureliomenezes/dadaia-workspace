"""Intent: CONTRACT — T-048-05 (SPEC 0.4.8 D7, D9, AC4.2): a specs tree is dadaia when its
constitution carries ``specs_pattern_version`` >= 6, foreign otherwise; the scaffolded
stubs speak English and carry the fixed memory sections. Size: SMALL."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import canon

pytestmark = pytest.mark.unit


def _constitution(specs: Path, text: str) -> None:
    specs.mkdir(parents=True)
    (specs / "constitution.md").write_text(text, encoding="utf-8")


def test_a_missing_tree_is_absent(tmp_path: Path) -> None:
    assert canon.classify(tmp_path / "specs") == "absent"


@pytest.mark.parametrize("version", [6, 7])
def test_a_stamp_of_six_or_more_is_dadaia(tmp_path: Path, version: int) -> None:
    _constitution(tmp_path / "specs", f"---\nspecs_pattern_version: {version}\n---\n# C\n")
    assert canon.classify(tmp_path / "specs") == "dadaia"


@pytest.mark.parametrize(
    "text", ["---\nspecs_pattern_version: 5\n---\n# C\n", "# A foreign constitution\n"]
)
def test_a_stamp_below_six_or_no_stamp_is_foreign(tmp_path: Path, text: str) -> None:
    _constitution(tmp_path / "specs", text)
    assert canon.classify(tmp_path / "specs") == "foreign"


def test_a_tree_without_a_constitution_is_foreign(tmp_path: Path) -> None:
    (tmp_path / "specs" / "features").mkdir(parents=True)
    assert canon.classify(tmp_path / "specs") == "foreign"


def test_the_scaffolded_stubs_are_english_with_the_fixed_memory_sections(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    canon.scaffold(specs, project_name="demo")

    constitution = (specs / "constitution.md").read_text(encoding="utf-8")
    assert "## Purpose" in constitution
    assert not re.search(r"Propósito|Invariantes|Exclusões|Definir", constitution)

    def headings(rel: str) -> list[str]:
        text = (specs / "memory" / rel).read_text(encoding="utf-8")
        return re.findall(r"^## (.+)$", text, re.MULTILINE)

    assert headings("ARCHITECTURE.md") == ["Principles", "Tech Stack", "Structure"]
    assert headings("QUALITY.md") == ["Principles", "Test architecture", "Gates"]
