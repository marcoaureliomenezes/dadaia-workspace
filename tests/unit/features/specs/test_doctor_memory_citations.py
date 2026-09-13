"""MEM-DRIFT-2 — memory atoms citing a dead `dadaia <verb>` or a dead repo path.

The doctor's citation rule (0.4.7 FR2): the same finders that keep `public/**` honest
(`features.specs.citations`) measure `specs/memory/**`, as a WARNING with no fix —
memory drift is a closure finding (QUALITY.md), never a red build or a push gate.
The command tree arrives as plain data, exactly as `live_shas` does; `features` never
imports `cli`.

Intent: CONTRACT — 0.4.7 T-047-35 (FR2, AC: a fixture atom citing `dadaia fixture-verb`
yields one MEM-DRIFT-2 line and exit 0).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs.doctor_memory import MemoryValidator
from dadaia_workspace.features.specs.doctor_types import Severity

_TREE: frozenset[tuple[str, ...]] = frozenset({(), ("doctor",), ("context",), ("context", "bind")})


def _atom(specs: Path, rel: str, body: str) -> Path:
    path = specs / "memory" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _check(specs: Path, repo_root: Path) -> list:  # type: ignore[type-arg]
    return MemoryValidator(specs).check_mem_drift2_citations(
        repo_root=repo_root, command_paths=_TREE
    )


def test_dead_verb_in_an_atom_is_one_warning_naming_file_and_line(tmp_path: Path) -> None:
    repo_root = tmp_path
    specs = repo_root / "specs"
    _atom(specs, "product/thing.md", "# Thing\n\nRun `dadaia fixture-verb` to start.\n")

    issues = _check(specs, repo_root)

    assert [i.code for i in issues] == ["MEM-DRIFT-2"]
    assert issues[0].severity == Severity.WARNING
    assert issues[0].fixable is False
    assert "specs/memory/product/thing.md:3" in issues[0].description
    assert "dadaia fixture-verb" in issues[0].description


def test_dead_repo_path_in_an_atom_is_a_warning(tmp_path: Path) -> None:
    repo_root = tmp_path
    specs = repo_root / "specs"
    _atom(specs, "ARCHITECTURE.md", "# A\n\nSee `dadaia_workspace/features/gone.py`.\n")

    issues = _check(specs, repo_root)

    assert [i.code for i in issues] == ["MEM-DRIFT-2"]
    assert "dadaia_workspace/features/gone.py" in issues[0].description


def test_live_verbs_and_real_paths_produce_nothing(tmp_path: Path) -> None:
    repo_root = tmp_path
    specs = repo_root / "specs"
    (repo_root / "dadaia_workspace").mkdir()
    (repo_root / "dadaia_workspace" / "container.py").write_text("", encoding="utf-8")
    _atom(
        specs,
        "product/thing.md",
        "# Thing\n\nRun `dadaia context bind` and read `dadaia_workspace/container.py`.\n",
    )

    assert _check(specs, repo_root) == []


def test_no_command_tree_or_no_memory_dir_is_silent(tmp_path: Path) -> None:
    """A consumer whose CLI tree could not be resolved keeps the rule silent, exactly as
    `live_shas=None` keeps SPEC-DOC-044 silent — never a false drift report."""
    repo_root = tmp_path
    specs = repo_root / "specs"
    _atom(specs, "product/thing.md", "Run `dadaia fixture-verb`.\n")

    assert (
        MemoryValidator(specs).check_mem_drift2_citations(repo_root=repo_root, command_paths=None)
        == []
    )
    assert (
        MemoryValidator(specs).check_mem_drift2_citations(repo_root=None, command_paths=_TREE) == []
    )
    assert (
        MemoryValidator(repo_root / "absent-specs").check_mem_drift2_citations(
            repo_root=repo_root, command_paths=_TREE
        )
        == []
    )
