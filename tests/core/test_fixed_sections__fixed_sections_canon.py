"""Size: SMALL. Reads the library's fragments and scaffold templates, scaffolds a fresh
tree into tmp and runs the doctor over it — the expected bytes are the fragments.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.fixed_sections import extract_fixed_section
from dadaia_workspace.features.specs.canon import scaffold
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.memory_canon import FIXED_SECTIONS, read_fixed_fragment

_PUBLIC_DIR = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"


def test_fresh_scaffold_renders_every_block_byte_equal_and_doctor_reports_no_fixed_issue(
    tmp_path: Path,
) -> None:
    specs = tmp_path / "specs"
    scaffold(specs, project_name="Proj", public_dir=_PUBLIC_DIR)
    for rel, section_id in FIXED_SECTIONS:
        text = (specs / rel).read_text(encoding="utf-8")
        assert extract_fixed_section(text, section_id) == read_fixed_fragment(
            _PUBLIC_DIR, section_id
        )
    issues = SpecsDoctor(specs, public_dir=_PUBLIC_DIR).check()
    assert [i.code for i in issues if i.code.startswith("FIXED-")] == []
