"""Intent: CONTRACT — 0.4.6 AC11 (fixed law sections: one fragment home, scaffold and doctor agree).

Size: SMALL. Reads the library's fragments and scaffold templates, scaffolds a fresh
tree into tmp and runs the doctor over it — the expected bytes are the fragments.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.fixed_sections import extract_fixed_section
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.memory_canon import FIXED_SECTIONS, read_fixed_fragment
from dadaia_workspace.features.specs.scaffolder import scaffold

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"
_MAX_BULLET_CHARS = 150


@pytest.mark.parametrize("rel, section_id", FIXED_SECTIONS, ids=[s for _, s in FIXED_SECTIONS])
def test_fragment_is_a_heading_plus_short_bullets(rel: str, section_id: str) -> None:
    fragment = read_fixed_fragment(_PUBLIC_DIR, section_id)
    assert fragment.endswith("\n") and not fragment.endswith("\n\n")
    heading, *bullets = fragment.splitlines()
    level = "## " if rel == "constitution.md" else "### "
    assert heading.startswith(level + "Slop — ") and heading.endswith("(fixed)")
    assert bullets, section_id
    for bullet in bullets:
        assert bullet.startswith("- "), bullet
        assert len(bullet) <= _MAX_BULLET_CHARS, f"{len(bullet)} chars: {bullet}"


@pytest.mark.parametrize("rel, section_id", FIXED_SECTIONS, ids=[s for _, s in FIXED_SECTIONS])
def test_scaffold_template_ends_with_its_empty_marker_pair(rel: str, section_id: str) -> None:
    template = (_PUBLIC_DIR / "scaffold" / rel).read_text(encoding="utf-8")
    assert extract_fixed_section(template, section_id) == ""
    assert template.endswith(f"<!-- /dadaia:fixed {section_id} -->\n")


def test_fresh_scaffold_renders_every_block_byte_equal_and_doctor_reports_no_fixed_issue(
    tmp_path: Path,
) -> None:
    specs = tmp_path / "specs"
    result = scaffold(specs, "Proj", False, _PUBLIC_DIR / "templates")
    assert not result.errors, result.errors
    for rel, section_id in FIXED_SECTIONS:
        text = (specs / rel).read_text(encoding="utf-8")
        assert extract_fixed_section(text, section_id) == read_fixed_fragment(
            _PUBLIC_DIR, section_id
        )
    issues = SpecsDoctor(specs, public_dir=_PUBLIC_DIR).check()
    assert [i.code for i in issues if i.code.startswith("FIXED-")] == []


def test_no_scaffold_or_law_file_restates_a_fragment_bullet() -> None:
    bullets = {
        line
        for _, section_id in FIXED_SECTIONS
        for line in read_fixed_fragment(_PUBLIC_DIR, section_id).splitlines()[1:]
    }
    copies = [
        (path.relative_to(_REPO_ROOT).as_posix(), line)
        for folder in ("scaffold", "data", "templates")
        for path in sorted((_PUBLIC_DIR / folder).rglob("*.md"))
        if "fixed" not in path.parts
        for line in path.read_text(encoding="utf-8").splitlines()
        if line in bullets
    ]
    assert copies == []
