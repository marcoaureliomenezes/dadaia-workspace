"""Unit tests for the canonical-subject registry (T-25-02, SPEC §3.2, ADR-A; T-050-154).

Every test runs against a fixed ``tmp_path`` repo built from inline ``MINIMAL_*`` constants,
the tracked paths handed in — never the live repo, never cwd.

UNRESOLVED-halts rows are preserved per kind (fail-closed binding).
"""

from __future__ import annotations

import json
import subprocess
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
    (tmp_path / "pkg" / "widget.go").write_text(MINIMAL_GO, encoding="utf-8")
    (tmp_path / "pkg" / "api" / "handlers.go").write_text("package api\n", encoding="utf-8")
    product = tmp_path / "specs" / "memory" / "product"
    product.mkdir(parents=True)
    (product / "catalog.json").write_text(json.dumps(MINIMAL_CATALOG), encoding="utf-8")
    (tmp_path / "specs" / "memory" / "architecture.md").write_text(MINIMAL_ARCH_DOC, "utf-8")
    return tmp_path


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
    """SPEC §3.7.5: no stored registry — editing the file changes the verdict."""
    (repo / "pkg" / "widget.go").write_text("package widget\n", encoding="utf-8")
    assert _build(repo).bind("pkg/widget.go#MakeWidget", SubjectKind.CODE).status is (
        BindStatus.UNRESOLVED
    )


def test_a_gitignored_path_does_not_bind_an_untracked_one_does(repo: Path) -> None:
    """The adapter's set: tracked plus untracked-unignored; an ignored file never binds."""
    for args in (["init", "-q"], ["add", "pkg/api/handlers.go"]):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)  # noqa: S603, S607
    (repo / ".gitignore").write_text("build/\n", encoding="utf-8")
    (repo / "build").mkdir()
    (repo / "build" / "out.go").write_text("package out\n", encoding="utf-8")
    reg = _build(repo, GitSubprocessClient().tracked(repo))
    assert reg.bind("build/out.go", SubjectKind.CODE).status is BindStatus.UNRESOLVED
    assert reg.bind("pkg/widget.go", SubjectKind.CODE).status is BindStatus.RESOLVED


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
    """FR2 (v0.1.49): only specs/memory declares invariants; a source file never does."""
    (repo / "pkg" / "leak.go").write_text("// INV-source-leak\n", encoding="utf-8")
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
