"""F011 (20260830-design-bug-surface-audit): memory-canon facts have ONE home —
``features.specs.memory_canon`` — and every consumer imports it. Intent: contract;
size: unit.

Multiplied before the fold: the required-memory-file list (canon.CANON rows,
doctor_structural._TREE3_MEMORY_FILES, doctor_memory.TOPLEVEL_MEMORY_FILES), the
forbidden-heading vocabulary (doctor_memory prefix regex vs memory_lint exact
frozenset — already divergent: singular 'Version' and unaccented 'Historico'
passed lint), and the wikilink regex compiled three times.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs import (
    catalog,
    doctor_memory,
    doctor_structural,
    memory_canon,
    memory_lint,
)


def test_memory_file_lists_are_the_one_home() -> None:
    assert doctor_memory.TOPLEVEL_MEMORY_FILES is memory_canon.MEMORY_TOPLEVEL_FILES
    assert doctor_structural._TREE3_MEMORY_FILES is memory_canon.MEMORY_REQUIRED_FILES
    assert set(memory_canon.MEMORY_TOPLEVEL_FILES) < set(memory_canon.MEMORY_REQUIRED_FILES)


def test_wikilink_regex_is_compiled_once() -> None:
    assert doctor_memory._WIKILINK_RE is memory_canon.WIKILINK_RE
    assert memory_lint._WIKILINK_RE is memory_canon.WIKILINK_RE
    assert catalog._WIKILINK_RE is memory_canon.WIKILINK_RE


def test_forbidden_heading_vocabulary_is_one_matcher() -> None:
    assert doctor_memory.FORBIDDEN_MEMORY_H2_RE is memory_canon.FORBIDDEN_MEMORY_HEADING_RE
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
        "---\n"
        "slug: sample\n"
        "title: Sample\n"
        "category: support\n"
        "tldr: One line.\n"
        "summary: Summary line.\n"
        "tags: [x]\n"
        "---\n"
        "# Sample\n\n## Version\n\nbody\n\n## Historico\n\nbody\n",
        encoding="utf-8",
    )
    schema = memory_lint.load_frontmatter_schema()
    result = memory_lint.lint_atom(atom, memory_dir, schema)
    forbidden = [e for e in result.errors if "Forbidden heading" in e]
    assert len(forbidden) == 2, result.errors
