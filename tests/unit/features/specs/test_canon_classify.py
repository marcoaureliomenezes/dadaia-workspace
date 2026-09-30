"""Intent: CONTRACT — sa-specs-tree-state-read-five-ways, T-048-05 (ADR 0047): the tree state
and its fix; the scaffolded stubs speak English with the fixed memory sections. SMALL."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.core import specs_version
from dadaia_workspace.features.specs import canon

pytestmark = pytest.mark.unit


_MALFORMED = "---\nspecs_pattern_version: 7\ngitflow: {principal: main\n---\n# C\n"


@pytest.mark.parametrize(
    ("text", "kind", "fix_tail"),
    [
        (None, "absent", "specs init --context demo"),
        ("---\nspecs_pattern_version: 8\n---\n# C\n", "canonical", None),
        ("---\nspecs_pattern_version: 7\n---\n# C\n", "upgradable", "specs init --context demo"),
        ("---\nspecs_pattern_version: 6\n---\n# C\n", "upgradable", "specs init --context demo"),
        (
            "---\nspecs_pattern_version: 5\n---\n# C\n",
            "foreign",
            "--context demo --replace-foreign",
        ),
        ("# A foreign constitution\n", "foreign", "--context demo --replace-foreign"),
        ("", "foreign", "--context demo --replace-foreign"),
        (_MALFORMED, "malformed", "{principal: main"),
        (
            "---\nspecs_pattern_version: 7\ngitflow: {principal: a, integration: a, work: w/}\n---\n",
            "malformed",
            "differ",
        ),
    ],
)
def test_state_is_the_one_reader_with_one_fix(
    tmp_path: Path, text: str | None, kind: str, fix_tail: str | None
) -> None:
    """sa-specs-tree-state-read-five-ways#B28-1: exactly one state plus one fix; a malformed
    constitution is malformed, never pattern 0. ``""`` = no constitution file in the tree.
    sa-specs-tree-state-read-five-ways#B28-7: state() is the module's only tree reader."""
    specs = tmp_path / "specs"
    if text is not None:
        specs.mkdir()
        if text:
            (specs / "constitution.md").write_text(text, encoding="utf-8")
    found, fix = specs_version.state(specs, context="demo")
    assert found == kind
    assert fix == fix_tail if fix_tail is None else fix is not None and fix_tail in fix
    assert not {"read_pattern_version", "classify"} & set(vars(specs_version))


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
