"""MEM-DRIFT-2 — memory atoms citing a dead `dadaia <verb>` or a dead repo path.

The doctor's citation rule: the same finders that keep `public/**` honest
(`features.specs.citations`) measure `specs/memory/**`, as a WARNING with no fix —
memory drift is a closure finding (QUALITY.md), never a red build or a push gate.
The command tree arrives as plain data, exactly as `live_shas` does; `features` never
imports `cli`.

A fixture atom citing `dadaia fixture-verb` yields one MEM-DRIFT-2 line and exit 0.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.citations import (
    dead_path_citations,
    dead_verb_citations,
    memory_citation_violations,
)
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator
from tests.helpers.cli_root import live_root
from tests.helpers.oslib import link, write_text

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
    write_text(tmp_path / "dadaia_workspace" / "container.py", "")
    atom = tmp_path / "specs" / "memory" / rel
    atom.parent.mkdir(parents=True)
    write_text(atom, body)

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
    """An unresolved CLI tree keeps the rule silent: never a false drift report."""
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    write_text(specs / "memory" / "thing.md", "Run `dadaia fixture-verb`.\n")
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
    """CWE-22: a token is alive only when it resolves
    INSIDE the repo; a symlink inside the repo is no containment proof."""
    repo_root = tmp_path / "repo"
    (tmp_path / "outside").mkdir()
    write_text(tmp_path / "outside" / "x.md", "secret")
    (repo_root / "specs").mkdir(parents=True)
    assert link(str(tmp_path / "outside" / "x.md"), repo_root / "specs" / "link.md", is_dir=False)

    violations = dead_path_citations(f"`{token}`\n", rel="a.md", repo_root=repo_root)

    assert violations == [f"a.md:1: dead path `{token}`"]


def test_the_markdown_walk_skips_symlinks(tmp_path: Path) -> None:
    """The walk never reads a symlinked atom."""
    repo_root = tmp_path / "repo"
    (tmp_path / "outside").mkdir()
    write_text(tmp_path / "outside" / "planted.md", "Run `dadaia fixture-verb`.\n")
    memory = repo_root / "specs" / "memory"
    memory.mkdir(parents=True)
    assert link(str(tmp_path / "outside" / "planted.md"), memory / "planted.md", is_dir=False)

    assert memory_citation_violations(memory, repo_root=repo_root, command_paths=_TREE) == []


def test_a_dead_token_inside_a_fixed_section_is_not_judged(tmp_path: Path) -> None:
    """Generated block text is the fragment's, judged by FIXED-2; the same token in prose still counts."""
    memory = tmp_path / "specs" / "memory"
    memory.mkdir(parents=True)
    write_text(
        memory / "thing.md",
        "# A\n\n<!-- dadaia:fixed adr-list -->\n"
        "- `dadaia_workspace/features/gone.py` `dadaia fixture-verb`\n"
        "<!-- /dadaia:fixed adr-list -->\n\n"
        "Run `dadaia fixture-verb`.\n",
    )

    violations = memory_citation_violations(memory, repo_root=tmp_path, command_paths=_TREE)

    assert [v.split(" `")[0] for _, v in violations] == ["specs/memory/thing.md:7: dead verb"]


@pytest.mark.parametrize(
    ("citation", "dead"),
    [
        pytest.param("dadaia doctor extra", False, id="leaf-plus-argument"),
        pytest.param("dadaia doctor", False, id="leaf"),
        pytest.param("dadaia nosuchverb", True, id="unknown-top-level"),
        pytest.param("dadaia nosuchverb extra", True, id="unknown-top-level-plus-word"),
        pytest.param("dadaia context bogus", True, id="group-unknown-sub"),
        pytest.param("dadaia context bind", False, id="two-level-live"),
    ],
)
def test_a_word_after_a_leaf_command_is_its_argument(citation: str, dead: bool) -> None:
    found = dead_verb_citations(f"`{citation}`", rel="x.md", command_paths=set(_TREE))

    assert bool(found) is dead


@pytest.mark.parametrize(
    ("citation", "dead"),
    [
        ("dadaia worktree merge", False),
        ("dadaia worktree bogus", False),
        ("dadaia nosuchverb", True),
    ],
)
def test_the_live_tree_as_a_plain_set(citation: str, dead: bool) -> None:
    from dadaia_workspace.cli.help_digest import command_paths

    found = dead_verb_citations(
        f"`{citation}`", rel="x.md", command_paths=set(command_paths(live_root()))
    )

    assert bool(found) is dead
