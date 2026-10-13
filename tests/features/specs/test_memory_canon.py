"""Memory-canon facts have ONE home — ``features.specs.memory_canon`` — and every consumer
imports it: the required-memory-file list, the forbidden-heading vocabulary and the
wikilink regex."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs import (
    doctor_memory,
    doctor_structural,
    memory_canon,
    memory_lint,
)


def test_memory_canon_facts_are_one_object_everywhere() -> None:
    from dadaia_workspace.core import fixed_sections

    assert doctor_memory.TOPLEVEL_MEMORY_FILES is memory_canon.MEMORY_TOPLEVEL_FILES
    assert doctor_structural._TREE3_MEMORY_FILES is memory_canon.MEMORY_REQUIRED_FILES
    assert set(memory_canon.MEMORY_TOPLEVEL_FILES) < set(memory_canon.MEMORY_REQUIRED_FILES)
    assert memory_lint._WIKILINK_RE is memory_canon.WIKILINK_RE
    assert memory_canon.FIXED_SECTIONS is fixed_sections.FIXED_SECTIONS
    assert memory_canon.render_fixed_section is fixed_sections.render_fixed_section
    assert memory_canon.extract_fixed_section is fixed_sections.extract_fixed_section
    assert dict(fixed_sections.FIXED_SECTIONS) == memory_canon.FIXED_SECTION_BY_PATH


def test_forbidden_heading_vocabulary_is_one_matcher() -> None:
    for heading in ("Changelog", "History", "Histórico", "Historico", "Version", "Versions"):
        assert memory_canon.is_forbidden_memory_heading(heading), heading
    assert not memory_canon.is_forbidden_memory_heading("Design")


def test_lint_flags_the_headings_the_doctor_flags(tmp_path: Path) -> None:
    """The divergence bug: '## Version' (singular) and '## Historico' (unaccented)
    violated the doctor's vocabulary but passed memory_lint's exact frozenset."""
    memory_dir = tmp_path / "memory"
    (memory_dir / "product" / "area").mkdir(parents=True)
    atom = memory_dir / "product" / "area" / "sample.md"
    atom.write_text(
        "---\nslug: sample\ntitle: Sample\ncategory: support\ntldr: One line.\n"
        "summary: Summary line.\ntags: [x]\n---\n# Sample\n\n## Version\n\nbody\n\n## Historico\n\nbody\n",
        encoding="utf-8",
    )
    schema = memory_lint.load_frontmatter_schema()
    result = memory_lint.lint_atom(atom, memory_dir, schema)
    forbidden = [e for e in result.errors if "Forbidden heading" in e]
    assert len(forbidden) == 2, result.errors
