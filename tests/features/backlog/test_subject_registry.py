"""Unit tests for the canonical-subject registry.

Every test runs against a fixed ``tmp_path`` repo built from inline ``MINIMAL_*`` constants,
the tracked paths handed in — never the live repo, never cwd.

UNRESOLVED-halts rows are preserved per kind (fail-closed binding).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.features.backlog.subject_registry import (
    Anchor,
    BindStatus,
    Registry,
    build_registry,
)
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.helpers.oslib import run, write_text
from tests.helpers.oslib import write_text as os_write_text

MINIMAL_GO = """package widget

const WidgetConst = 1

func MakeWidget() int { return WidgetConst }

// call foo() with $env
"""

MINIMAL_CATALOG = {"features": [{"slug": "alpha-feature"}, {"slug": "beta-feature"}]}

MINIMAL_ARCH_DOC = """# Architecture

## INV-no-fixture-drift

Mentions SPEC-DOC-099 in prose.
"""

TRACKED = frozenset({"pkg/widget.go", "pkg/api/handlers.go"})


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A repo root holding a Go source and a specs tree; nothing parses Go."""
    (tmp_path / "pkg" / "api").mkdir(parents=True)
    write_text(tmp_path / "pkg" / "widget.go", MINIMAL_GO)
    write_text(tmp_path / "pkg" / "api" / "handlers.go", "package api\n")
    product = tmp_path / "specs" / "memory" / "product"
    product.mkdir(parents=True)
    write_text(product / "catalog.json", json.dumps(MINIMAL_CATALOG))
    for slug in ("alpha-feature", "beta-feature"):
        write_text(product / f"{slug}.md", _atom(slug))
    os_write_text(tmp_path / "specs" / "memory" / "architecture.md", MINIMAL_ARCH_DOC)
    return tmp_path


def _atom(slug: str) -> str:
    return f"---\nslug: {slug}\ntitle: {slug}\ntldr: {slug}\nsummary: {slug}\n---\n\n# {slug}\n"


def _build(repo: Path, tracked: frozenset[str] = TRACKED) -> Registry:
    return build_registry(specs_dir=repo / "specs", tracked=tracked)


@pytest.mark.parametrize(
    ("ref", "status", "anchor"),
    [
        ("pkg/widget.go", BindStatus.RESOLVED, "pkg/widget.go"),
        ("pkg/widget.go#MakeWidget", BindStatus.RESOLVED, "pkg/widget.go#MakeWidget"),
        ("widget.go#WidgetConst", BindStatus.RESOLVED, "pkg/widget.go#WidgetConst"),
        ("pkg/widget.go#Make", BindStatus.UNRESOLVED, None),  # a word, never a substring
        ("pkg/widget.go#foo()", BindStatus.RESOLVED, "pkg/widget.go#foo()"),
        ("pkg/widget.go#$env", BindStatus.RESOLVED, "pkg/widget.go#$env"),
        ("pkg/ghost.go", BindStatus.UNRESOLVED, None),
        ("pkg/api", BindStatus.UNRESOLVED, None),  # a directory is not a tracked path
    ],
)
def test_a_code_ref_is_any_tracked_path_its_word_optional(
    repo: Path, ref: str, status: BindStatus, anchor: str | None
) -> None:
    result = _build(repo).bind(ref, SubjectKind.CODE)
    assert result.status is status
    assert result.anchor == (Anchor(SubjectKind.CODE, anchor) if anchor else None)
    if status is BindStatus.UNRESOLVED:
        assert ref in result.message


def test_a_code_word_is_read_from_the_live_file(repo: Path) -> None:
    """No stored registry — editing the file changes the verdict."""
    write_text(repo / "pkg" / "widget.go", "package widget\n")
    assert _build(repo).bind("pkg/widget.go#MakeWidget", SubjectKind.CODE).status is (
        BindStatus.UNRESOLVED
    )


def test_a_gitignored_path_does_not_bind_an_untracked_one_does(repo: Path) -> None:
    """The adapter's set: tracked plus untracked-unignored; an ignored file never binds."""
    for args in (["init", "-q"], ["add", "pkg/api/handlers.go"]):
        run(["git", *args], cwd=repo, check=True)
    write_text(repo / ".gitignore", "build/\n")
    (repo / "build").mkdir()
    write_text(repo / "build" / "out.go", "package out\n")
    reg = _build(repo, GitSubprocessClient().tracked(repo))
    assert reg.bind("build/out.go", SubjectKind.CODE).status is BindStatus.UNRESOLVED
    assert reg.bind("pkg/widget.go", SubjectKind.CODE).status is BindStatus.RESOLVED


def test_a_catalog_slug_without_an_atom_file_does_not_resolve(repo: Path) -> None:
    """The catalog names a ghost, the atom file is the real feature: the files answer."""
    product = repo / "specs" / "memory" / "product"
    write_text(product / "catalog.json", json.dumps({"features": [{"slug": "ghost-feature"}]}))
    write_text(product / "real-feature.md", _atom("real-feature"))

    reg = _build(repo)

    assert reg.bind("ghost-feature", SubjectKind.CATALOG).status is BindStatus.UNRESOLVED
    assert reg.bind("real-feature", SubjectKind.CATALOG).status is BindStatus.RESOLVED


def test_an_unreadable_atom_is_named_by_a_catalog_refusal(repo: Path) -> None:
    """An atom whose frontmatter does not parse is never an empty anchor set: the catalog
    refusal names the file that broke."""
    write_text(repo / "specs" / "memory" / "product" / "broken.md", "---\nslug: [unclosed\n---\n")

    result = _build(repo).bind("alpha-feature", SubjectKind.CATALOG)

    assert result.status is BindStatus.UNRESOLVED
    assert "broken.md" in result.message


def test_catalog_doc_and_invariant_resolve_and_unknown_halts(repo: Path) -> None:
    reg = _build(repo)
    assert reg.bind("alpha-feature", SubjectKind.CATALOG).status is BindStatus.RESOLVED
    assert reg.bind("gamma-feature", SubjectKind.CATALOG).status is BindStatus.UNRESOLVED
    assert reg.bind("SPEC-DOC-099", SubjectKind.DOC).status is BindStatus.RESOLVED
    assert reg.bind("memory/architecture.md#INV-no-fixture-drift", SubjectKind.DOC).status is (
        BindStatus.RESOLVED
    )
    assert reg.bind("SPEC-DOC-12345", SubjectKind.DOC).status is BindStatus.UNRESOLVED
    assert reg.bind("INV-no-fixture-drift", SubjectKind.INVARIANT).status is BindStatus.RESOLVED
    assert reg.bind("INV-made-up", SubjectKind.INVARIANT).status is BindStatus.UNRESOLVED


def test_an_invariant_is_never_minted_from_source(repo: Path) -> None:
    """Only specs/memory declares invariants; a source file never does."""
    write_text(repo / "pkg" / "leak.go", "// INV-source-leak\n")
    reg = _build(repo, TRACKED | {"pkg/leak.go"})
    assert reg.bind("INV-source-leak", SubjectKind.INVARIANT).status is BindStatus.UNRESOLVED


def test_unique_suffix_ref_binds_and_ambiguous_suffix_halts(tmp_path: Path) -> None:
    """A ref missing its leading directories binds when it suffix-matches EXACTLY ONE
    anchor; two matches are AMBIGUOUS with both candidates named."""
    reg = Registry({SubjectKind.CODE: {"src/game/loop.py", "a/util.rs", "b/util.rs"}}, tmp_path)
    unique = reg.bind("loop.py", SubjectKind.CODE)
    assert (unique.status, unique.anchor) == (
        BindStatus.RESOLVED,
        Anchor(SubjectKind.CODE, "src/game/loop.py"),
    )
    halted = reg.bind("util.rs", SubjectKind.CODE)
    assert halted.status is BindStatus.AMBIGUOUS and "'util.rs'" in halted.message
    assert reg.bind("util.rs", SubjectKind.DOC).status is BindStatus.UNRESOLVED  # no doc kind
    assert set(halted.candidates) == {"a/util.rs", "b/util.rs"}
