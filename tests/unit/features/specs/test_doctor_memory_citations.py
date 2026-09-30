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

import pytest

from dadaia_workspace.features.specs.citations import (
    dead_path_citations,
    memory_citation_violations,
)
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

_TREE: frozenset[tuple[str, ...]] = frozenset({(), ("doctor",), ("context",), ("context", "bind")})


@pytest.mark.parametrize(
    ("rel", "body", "needles"),
    [
        pytest.param(
            "product/thing.md",
            "# Thing\n\nRun `dadaia fixture-verb` to start.\n",
            ("specs/memory/product/thing.md:3", "dadaia fixture-verb"),
            id="dead-verb-names-file-and-line",
        ),
        pytest.param(
            "ARCHITECTURE.md",
            "# A\n\nSee `dadaia_workspace/features/gone.py`.\n",
            ("dadaia_workspace/features/gone.py",),
            id="dead-repo-path",
        ),
        pytest.param(
            "product/thing.md",
            "Run `dadaia context bind` and read `dadaia_workspace/container.py`.\n",
            (),
            id="live-verb-and-real-path-silent",
        ),
    ],
)
def test_mem_drift2_citation(tmp_path: Path, rel: str, body: str, needles: tuple[str, ...]) -> None:
    (tmp_path / "dadaia_workspace").mkdir()
    (tmp_path / "dadaia_workspace" / "container.py").write_text("", encoding="utf-8")
    atom = tmp_path / "specs" / "memory" / rel
    atom.parent.mkdir(parents=True)
    atom.write_text(body, encoding="utf-8")

    issues = MemoryValidator(tmp_path / "specs").check_mem_drift2_citations(
        repo_root=tmp_path, command_paths=_TREE
    )

    if not needles:
        assert issues == []
        return
    [issue] = issues
    assert (issue.code, issue.verdict, issue.fixable) == ("MEM-DRIFT-2", "warning", False)
    assert all(needle in issue.message for needle in needles)


def test_no_command_tree_no_repo_root_or_no_specs_is_silent(tmp_path: Path) -> None:
    """An unresolved CLI tree keeps the rule silent, as ``live_shas=None`` keeps
    SPEC-DOC-044 silent — never a false drift report."""
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    (specs / "memory" / "thing.md").write_text("Run `dadaia fixture-verb`.\n", encoding="utf-8")
    check = MemoryValidator.check_mem_drift2_citations
    assert check(MemoryValidator(specs), repo_root=tmp_path, command_paths=None) == []
    assert check(MemoryValidator(specs), repo_root=None, command_paths=_TREE) == []
    assert (
        check(MemoryValidator(tmp_path / "absent"), repo_root=tmp_path, command_paths=_TREE) == []
    )


@pytest.mark.parametrize(
    "token", ["specs/../../outside/x.md", "specs/link.md"], ids=["traversal", "symlink"]
)
def test_a_citation_resolving_outside_the_repo_is_dead(tmp_path: Path, token: str) -> None:
    """CWE-22 (0.4.7 T-047-35 security finding): a token is alive only when it resolves
    INSIDE the repo; a symlink inside the repo is no containment proof."""
    repo_root = tmp_path / "repo"
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "x.md").write_text("secret", encoding="utf-8")
    (repo_root / "specs").mkdir(parents=True)
    (repo_root / "specs" / "link.md").symlink_to(tmp_path / "outside" / "x.md")

    violations = dead_path_citations(f"`{token}`\n", rel="a.md", repo_root=repo_root)

    assert violations == [f"a.md:1: dead path `{token}`"]


def test_the_markdown_walk_skips_symlinks(tmp_path: Path) -> None:
    """0.4.7 T-047-35 security finding: the walk never reads a symlinked atom."""
    repo_root = tmp_path / "repo"
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "planted.md").write_text(
        "Run `dadaia fixture-verb`.\n", encoding="utf-8"
    )
    memory = repo_root / "specs" / "memory"
    memory.mkdir(parents=True)
    (memory / "planted.md").symlink_to(tmp_path / "outside" / "planted.md")

    assert memory_citation_violations(memory, repo_root=repo_root, command_paths=_TREE) == []
