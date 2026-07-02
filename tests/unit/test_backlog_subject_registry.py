"""Unit tests for the canonical-subject registry (T-25-02, SPEC §3.2, ADR-A).

The linchpin. Every test here runs against a **fixed ``tmp_path`` fixture tree** built from
inline ``MINIMAL_*`` constants — NOT the live repo (SPEC §3.7.8). Live derivation gets
exactly one scoped create/delete test (``test_live_derivation_*``) that builds and tears down
its own anchor source file.

All roots (source_root, catalog_path, alias_map_path, specs_dir) are injected — never cwd
(SPEC §3.8 #6).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

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
        cli_app=_fixture_app(),
    )


# ── code kind (AST) ─────────────────────────────────────────────────────────────


def test_code_anchor_resolves_class(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    result = reg.bind("pkg/sample.py#WidgetFactory", SubjectKind.CODE)
    assert result.status is BindStatus.RESOLVED
    assert result.anchor is not None
    assert result.anchor.id == "pkg/sample.py#WidgetFactory"


def test_code_anchor_resolves_function_and_const(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("pkg/sample.py#make_widget", SubjectKind.CODE).status is BindStatus.RESOLVED
    assert reg.bind("pkg/sample.py#WIDGET_CONST", SubjectKind.CODE).status is BindStatus.RESOLVED


def test_code_anchor_unresolved_symbol_halts(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    result = reg.bind("pkg/sample.py#NoSuchSymbol", SubjectKind.CODE)
    assert result.status is BindStatus.UNRESOLVED
    assert "NoSuchSymbol" in result.message  # actionable: names the ref


def test_code_anchor_unknown_file_halts(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    result = reg.bind("pkg/ghost.py#Widget", SubjectKind.CODE)
    assert result.status is BindStatus.UNRESOLVED


# ── cli kind (Typer app tree) ───────────────────────────────────────────────────


def test_cli_anchor_resolves_command_id(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    result = reg.bind("backlog doctor", SubjectKind.CLI)
    assert result.status is BindStatus.RESOLVED
    assert result.anchor is not None and result.anchor.id == "backlog doctor"


def test_cli_anchor_unknown_command_halts(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("backlog frobnicate", SubjectKind.CLI).status is BindStatus.UNRESOLVED


# ── catalog kind ────────────────────────────────────────────────────────────────


def test_catalog_slug_resolves(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("alpha-feature", SubjectKind.CATALOG).status is BindStatus.RESOLVED


def test_catalog_unknown_slug_halts(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("gamma-feature", SubjectKind.CATALOG).status is BindStatus.UNRESOLVED


# ── doc kind (spec-doc ids + memory heading anchors) ────────────────────────────


def test_doc_specdoc_id_resolves(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("SPEC-DOC-099", SubjectKind.DOC).status is BindStatus.RESOLVED


def test_doc_heading_anchor_resolves(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert (
        reg.bind("memory/architecture.md#INV-no-fixture-drift", SubjectKind.DOC).status
        is BindStatus.RESOLVED
    )


def test_doc_unknown_halts(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("SPEC-DOC-12345", SubjectKind.DOC).status is BindStatus.UNRESOLVED


# ── invariant kind ──────────────────────────────────────────────────────────────


def test_invariant_resolves(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("INV-no-fixture-drift", SubjectKind.INVARIANT).status is BindStatus.RESOLVED


def test_invariant_unknown_halts(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    assert reg.bind("INV-made-up", SubjectKind.INVARIANT).status is BindStatus.UNRESOLVED


def test_invariant_in_py_docstring_does_not_resolve(fixture_tree: dict[str, Path]) -> None:
    """FR2 (v0.1.49): ``.py`` content is not an invariant declaration surface."""
    leaky = fixture_tree["source_root"] / "pkg" / "leaky.py"
    leaky.write_text('"""Docstring example: INV-py-docstring-leak."""\n', encoding="utf-8")
    reg = _build(fixture_tree)
    assert reg.bind("INV-py-docstring-leak", SubjectKind.INVARIANT).status is BindStatus.UNRESOLVED


def test_invariant_under_tests_dir_does_not_resolve(fixture_tree: dict[str, Path]) -> None:
    """FR2 (v0.1.49): test fixtures under the source root never mint anchors."""
    tests_dir = fixture_tree["source_root"] / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_leak.py").write_text("EXPECT = 'INV-test-fixture-leak'\n", encoding="utf-8")
    reg = _build(fixture_tree)
    assert reg.bind("INV-test-fixture-leak", SubjectKind.INVARIANT).status is BindStatus.UNRESOLVED


# ── panel/api — alias-map ONLY in R1 ─────────────────────────────────────────────


def test_panel_resolves_only_via_alias(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    # The alias map maps "the panel API" -> panel:/api/widgets.
    result = reg.bind("the panel API", SubjectKind.PANEL)
    assert result.status is BindStatus.RESOLVED
    assert result.anchor is not None and result.anchor.id == "panel:/api/widgets"


def test_panel_without_alias_halts(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    # No auto-derivation for panel in R1; an unaliased panel ref must HALT.
    assert reg.bind("panel:/api/never-aliased", SubjectKind.PANEL).status is BindStatus.UNRESOLVED


# ── alias collapses synonym to one anchor (acceptance §3.7.5) ────────────────────


def test_alias_collapses_synonym_to_canonical_anchor(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    # "widget factory" is a synonym aliased to the real code anchor.
    result = reg.bind("widget factory", SubjectKind.CODE)
    assert result.status is BindStatus.RESOLVED
    assert result.anchor is not None and result.anchor.id == "pkg/sample.py#WidgetFactory"


# ── list_anchors (preview surface feed) ─────────────────────────────────────────


def test_list_anchors_filters_by_kind(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    code_anchors = reg.list_anchors(SubjectKind.CODE)
    ids = {a.id for a in code_anchors}
    assert "pkg/sample.py#WidgetFactory" in ids
    assert "pkg/sample.py#make_widget" in ids
    # No catalog anchors leak into a code listing.
    assert all(a.kind is SubjectKind.CODE for a in code_anchors)


def test_list_anchors_all_kinds(fixture_tree: dict[str, Path]) -> None:
    reg = _build(fixture_tree)
    all_anchors = reg.list_anchors()
    kinds = {a.kind for a in all_anchors}
    assert SubjectKind.CODE in kinds
    assert SubjectKind.CLI in kinds
    assert SubjectKind.CATALOG in kinds


# ── absent injected roots tolerated (no crash) ──────────────────────────────────


def test_absent_alias_map_tolerated(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    (source_root / "pkg").mkdir(parents=True)
    (source_root / "pkg" / "sample.py").write_text(MINIMAL_SOURCE, encoding="utf-8")
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(MINIMAL_CATALOG), encoding="utf-8")
    reg = build_registry(
        source_root=source_root,
        catalog_path=catalog_path,
        alias_map_path=tmp_path / "missing-aliases.txt",
        specs_dir=tmp_path / "missing-specs",
        cli_app=_fixture_app(),
    )
    # Code still resolves; an aliased synonym now HALTs (no alias map present).
    assert reg.bind("pkg/sample.py#make_widget", SubjectKind.CODE).status is BindStatus.RESOLVED
    assert reg.bind("widget factory", SubjectKind.CODE).status is BindStatus.UNRESOLVED


# ── scoped LIVE-derivation test (creates/deletes its own source file) ────────────


def test_live_derivation_reflects_source_changes(tmp_path: Path) -> None:
    """SPEC §3.7.5: the registry recomputes from live truth each run.

    A symbol added then removed in source changes resolution without editing any stored
    registry file. This is the ONLY test that mutates a source file at runtime.
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
            cli_app=_fixture_app(),
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
