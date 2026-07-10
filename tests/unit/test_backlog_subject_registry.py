"""Unit tests for the canonical-subject registry (T-25-02, SPEC §3.2, ADR-A).

The linchpin. Every test here runs against a **fixed ``tmp_path`` fixture tree** built from
inline ``MINIMAL_*`` constants — NOT the live repo (SPEC §3.7.8). Live derivation gets
exactly one scoped create/delete test (``test_live_derivation_*``) that builds and tears down
its own anchor source file.

All roots (source_root, catalog_path, alias_map_path, specs_dir) are injected — never cwd
(SPEC §3.8 #6).

UNRESOLVED-halts rows are preserved per kind (fail-closed binding).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from dadaia_workspace.cli.anchors import derive_cli_anchors
from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.features.backlog.subject_registry import (
    BindStatus,
    build_registry,
)

pytestmark = pytest.mark.unit


# ── inline MINIMAL_* fixture constants ──────────────────────────────────────────

MINIMAL_SOURCE = '''"""A minimal module for registry fixtures."""


WIDGET_CONST = 1


def make_widget() -> int:
    return WIDGET_CONST


class WidgetFactory:
    def build(self) -> int:
        return 2
'''

MINIMAL_CATALOG = {
    "generated_at": "2026-06-26T00:00:00Z",
    "context": "fixture",
    "features": [
        {"slug": "alpha-feature", "title": "Alpha"},
        {"slug": "beta-feature", "title": "Beta"},
    ],
}

MINIMAL_ALIAS_MAP = """
# fixture alias map
the panel API -> panel:/api/widgets
widget factory -> pkg/sample.py#WidgetFactory
"""

MINIMAL_ARCH_DOC = """---
title: architecture
---

# Architecture

## INV-no-fixture-drift

A fixture invariant.

Mentions SPEC-DOC-099 in prose.
"""


def _fixture_app() -> typer.Typer:
    """A tiny Typer app tree mirroring ``dadaia <group> <verb>`` shape."""
    app = typer.Typer()
    backlog = typer.Typer()

    @backlog.command("doctor")
    def _doctor() -> None:  # pragma: no cover - registration only
        pass

    @backlog.command("subjects")
    def _subjects() -> None:  # pragma: no cover - registration only
        pass

    app.add_typer(backlog, name="backlog")

    @app.command("version")
    def _version() -> None:  # pragma: no cover - registration only
        pass

    return app


@pytest.fixture()
def fixture_tree(tmp_path: Path) -> dict[str, Path]:
    """Build the fixed fixture tree once; every registry test consumes it."""
    source_root = tmp_path / "src"
    (source_root / "pkg").mkdir(parents=True)
    (source_root / "pkg" / "sample.py").write_text(MINIMAL_SOURCE, encoding="utf-8")

    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(MINIMAL_CATALOG), encoding="utf-8")

    alias_map_path = tmp_path / "aliases.txt"
    alias_map_path.write_text(MINIMAL_ALIAS_MAP, encoding="utf-8")

    specs_dir = tmp_path / "specs"
    (specs_dir / "memory").mkdir(parents=True)
    (specs_dir / "memory" / "architecture.md").write_text(MINIMAL_ARCH_DOC, encoding="utf-8")

    return {
        "source_root": source_root,
        "catalog_path": catalog_path,
        "alias_map_path": alias_map_path,
        "specs_dir": specs_dir,
    }


def _build(tree: dict[str, Path]) -> object:
    return build_registry(
        source_root=tree["source_root"],
        catalog_path=tree["catalog_path"],
        alias_map_path=tree["alias_map_path"],
        specs_dir=tree["specs_dir"],
        cli_anchors=derive_cli_anchors(_fixture_app()),
    )


# ── code kind (AST) ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("ref", "expected_status"),
    [
        ("pkg/sample.py#WidgetFactory", BindStatus.RESOLVED),
        ("pkg/sample.py#make_widget", BindStatus.RESOLVED),
        ("pkg/sample.py#WIDGET_CONST", BindStatus.RESOLVED),
        ("pkg/sample.py#NoSuchSymbol", BindStatus.UNRESOLVED),
        ("pkg/ghost.py#Widget", BindStatus.UNRESOLVED),
    ],
)
def test_code_anchor_table(
    fixture_tree: dict[str, Path], ref: str, expected_status: BindStatus
) -> None:
    reg = _build(fixture_tree)
    result = reg.bind(ref, SubjectKind.CODE)
    assert result.status is expected_status
    if expected_status is BindStatus.RESOLVED:
        assert result.anchor is not None
        assert result.anchor.id == ref
    elif "NoSuchSymbol" in ref:
        assert "NoSuchSymbol" in result.message  # actionable: names the ref


# ── cli kind (Typer app tree) + catalog kind ────────────────────────────────────


def test_cli_and_catalog_anchor_resolve_and_unknown_halts(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    result = reg.bind("backlog doctor", SubjectKind.CLI)
    assert result.status is BindStatus.RESOLVED
    assert result.anchor is not None and result.anchor.id == "backlog doctor"
    assert reg.bind("backlog frobnicate", SubjectKind.CLI).status is BindStatus.UNRESOLVED

    assert reg.bind("alpha-feature", SubjectKind.CATALOG).status is BindStatus.RESOLVED
    assert reg.bind("gamma-feature", SubjectKind.CATALOG).status is BindStatus.UNRESOLVED


# ── doc kind (spec-doc ids + memory heading anchors) ────────────────────────────


def test_doc_kind_table(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("SPEC-DOC-099", SubjectKind.DOC).status is BindStatus.RESOLVED
    assert (
        reg.bind("memory/architecture.md#INV-no-fixture-drift", SubjectKind.DOC).status
        is BindStatus.RESOLVED
    )
    assert reg.bind("SPEC-DOC-12345", SubjectKind.DOC).status is BindStatus.UNRESOLVED

    # panel/api — alias-map ONLY in R1.
    # The alias map maps "the panel API" -> panel:/api/widgets.
    result = reg.bind("the panel API", SubjectKind.PANEL)
    assert result.status is BindStatus.RESOLVED
    assert result.anchor is not None and result.anchor.id == "panel:/api/widgets"
    # No auto-derivation for panel in R1; an unaliased panel ref must HALT.
    assert reg.bind("panel:/api/never-aliased", SubjectKind.PANEL).status is BindStatus.UNRESOLVED


# ── invariant kind ──────────────────────────────────────────────────────────────


def test_invariant_resolves_unknown_halts_and_never_mints_from_py_or_tests(
    fixture_tree: dict[str, Path],
) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("INV-no-fixture-drift", SubjectKind.INVARIANT).status is BindStatus.RESOLVED
    assert reg.bind("INV-made-up", SubjectKind.INVARIANT).status is BindStatus.UNRESOLVED

    # FR2 (v0.1.49): `.py` content is not an invariant declaration surface (the
    # runtime-mutating live-derivation invariant, kept as the source of truth for
    # anchor-surface privacy — .py-docstring/tests-dir never mint anchors).
    leaky = fixture_tree["source_root"] / "pkg" / "leaky.py"
    leaky.write_text('"""Docstring example: INV-py-docstring-leak."""\n', encoding="utf-8")
    leaky_reg = _build(fixture_tree)
    assert (
        leaky_reg.bind("INV-py-docstring-leak", SubjectKind.INVARIANT).status
        is BindStatus.UNRESOLVED
    )

    # FR2 (v0.1.49): test fixtures under the source root never mint anchors.
    tests_dir = fixture_tree["source_root"] / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_leak.py").write_text("EXPECT = 'INV-test-fixture-leak'\n", encoding="utf-8")
    tests_reg = _build(fixture_tree)
    assert (
        tests_reg.bind("INV-test-fixture-leak", SubjectKind.INVARIANT).status
        is BindStatus.UNRESOLVED
    )


# ── alias collapses synonym to one anchor (acceptance §3.7.5), and absence tolerated ──


def test_alias_collapses_synonym_and_absent_alias_map_tolerated(
    fixture_tree: dict[str, Path], tmp_path: Path
) -> None:
    reg = _build(fixture_tree)
    # "widget factory" is a synonym aliased to the real code anchor.
    result = reg.bind("widget factory", SubjectKind.CODE)
    assert result.status is BindStatus.RESOLVED
    assert result.anchor is not None and result.anchor.id == "pkg/sample.py#WidgetFactory"

    # Absent injected roots tolerated (no crash) — code still resolves; an aliased
    # synonym now HALTs (no alias map present).
    absent_root = tmp_path / "absent-case"
    source_root = absent_root / "src"
    (source_root / "pkg").mkdir(parents=True)
    (source_root / "pkg" / "sample.py").write_text(MINIMAL_SOURCE, encoding="utf-8")
    catalog_path = absent_root / "catalog.json"
    catalog_path.write_text(json.dumps(MINIMAL_CATALOG), encoding="utf-8")
    absent_reg = build_registry(
        source_root=source_root,
        catalog_path=catalog_path,
        alias_map_path=absent_root / "missing-aliases.txt",
        specs_dir=absent_root / "missing-specs",
        cli_anchors=derive_cli_anchors(_fixture_app()),
    )
    assert (
        absent_reg.bind("pkg/sample.py#make_widget", SubjectKind.CODE).status is BindStatus.RESOLVED
    )
    assert absent_reg.bind("widget factory", SubjectKind.CODE).status is BindStatus.UNRESOLVED


# ── list_anchors (preview surface feed) ─────────────────────────────────────────


def test_list_anchors_filters_by_kind_and_all_kinds(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    code_anchors = reg.list_anchors(SubjectKind.CODE)
    ids = {a.id for a in code_anchors}
    assert "pkg/sample.py#WidgetFactory" in ids
    assert "pkg/sample.py#make_widget" in ids
    # No catalog anchors leak into a code listing.
    assert all(a.kind is SubjectKind.CODE for a in code_anchors)

    all_anchors = reg.list_anchors()
    kinds = {a.kind for a in all_anchors}
    assert SubjectKind.CODE in kinds
    assert SubjectKind.CLI in kinds
    assert SubjectKind.CATALOG in kinds


# ── scoped LIVE-derivation test (creates/deletes its own source file) ────────────


def test_live_derivation_reflects_source_changes(tmp_path: Path) -> None:
    """SPEC §3.7.5: the registry recomputes from live truth each run.

    A symbol added then removed in source changes resolution without editing any stored
    registry file. This is the ONLY test that mutates a source file at runtime — the one
    runtime-mutating test proving live derivation, not stored state.
    """
    source_root = tmp_path / "src"
    (source_root / "pkg").mkdir(parents=True)
    target = source_root / "pkg" / "live.py"
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({"features": []}), encoding="utf-8")
    alias_map_path = tmp_path / "aliases.txt"
    specs_dir = tmp_path / "specs"

    def build() -> object:
        return build_registry(
            source_root=source_root,
            catalog_path=catalog_path,
            alias_map_path=alias_map_path,
            specs_dir=specs_dir,
            cli_anchors=derive_cli_anchors(_fixture_app()),
        )

    # Step 1 — symbol present.
    target.write_text("class LiveThing:\n    pass\n", encoding="utf-8")
    assert build().bind("pkg/live.py#LiveThing", SubjectKind.CODE).status is BindStatus.RESOLVED

    # Step 2 — remove the symbol; a fresh build no longer resolves it.
    target.write_text("class OtherThing:\n    pass\n", encoding="utf-8")
    assert build().bind("pkg/live.py#LiveThing", SubjectKind.CODE).status is BindStatus.UNRESOLVED

    # Cleanup (scoped test owns its file).
    target.unlink()
    assert build().bind("pkg/live.py#OtherThing", SubjectKind.CODE).status is BindStatus.UNRESOLVED
