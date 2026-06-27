"""Unit tests for the read-only resolve/preview surface (T-25-03, SPEC §3.4a).

``resolve_one(ref, kind)`` shows how a proposed subject resolves to a canonical anchor
(or UNRESOLVED/AMBIGUOUS + an alias suggestion). ``list_anchors(kind?)`` lists the live
anchor set. The surface NEVER writes a backlog file or the alias map. Fixtures use a fixed
``tmp_path`` tree (SPEC §3.7.8); all roots injected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.features.backlog.preview import (
    PreviewResult,
    list_anchors,
    resolve_one,
)
from dadaia_workspace.features.backlog.subject_registry import BindStatus, build_registry

pytestmark = pytest.mark.unit

MINIMAL_SOURCE = "class Widget:\n    pass\n\n\ndef make() -> int:\n    return 1\n"
MINIMAL_CATALOG = {"features": [{"slug": "alpha-feature"}]}
MINIMAL_ALIAS = "the panel api -> panel:/api/widgets\n"


def _registry(tmp_path: Path) -> object:
    source_root = tmp_path / "src"
    (source_root / "pkg").mkdir(parents=True)
    (source_root / "pkg" / "m.py").write_text(MINIMAL_SOURCE, encoding="utf-8")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(MINIMAL_CATALOG), encoding="utf-8")
    alias = tmp_path / "aliases.txt"
    alias.write_text(MINIMAL_ALIAS, encoding="utf-8")
    return build_registry(
        source_root=source_root,
        catalog_path=catalog,
        alias_map_path=alias,
        specs_dir=tmp_path / "specs",
        cli_app=typer.Typer(),
    )


def test_resolve_one_resolved(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    result = resolve_one(reg, "pkg/m.py#Widget", SubjectKind.CODE)
    assert isinstance(result, PreviewResult)
    assert result.status is BindStatus.RESOLVED
    assert result.anchor_id == "pkg/m.py#Widget"


def test_resolve_one_unresolved_carries_alias_suggestion(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    result = resolve_one(reg, "pkg/m.py#Ghost", SubjectKind.CODE)
    assert result.status is BindStatus.UNRESOLVED
    assert "Ghost" in result.message
    # The preview surfaces an actionable alias-map suggestion for the gap.
    assert result.alias_suggestion is not None
    assert "->" in result.alias_suggestion


def test_resolve_one_panel_alias(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    result = resolve_one(reg, "the panel api", SubjectKind.PANEL)
    assert result.status is BindStatus.RESOLVED
    assert result.anchor_id == "panel:/api/widgets"


def test_list_anchors_filtered(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    code = list_anchors(reg, SubjectKind.CODE)
    ids = {a.id for a in code}
    assert "pkg/m.py#Widget" in ids
    assert all(a.kind is SubjectKind.CODE for a in code)


def test_list_anchors_all(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    everything = list_anchors(reg, None)
    assert any(a.kind is SubjectKind.CATALOG for a in everything)
