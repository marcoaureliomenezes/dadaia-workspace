"""Closure must notice when it leaves a consumed item behind.

Bug ``r18-closure-leaves-consumed-backlog-item`` (consumer-side validator, R18): on a
live chain the SPEC declared ``Consumes: csv-line-parser-utility`` and the ledger was
written correctly — and the item stayed in the live backlog. Closure said nothing, so the
operator learned of it later, from ``backlog doctor`` reporting BL-STALE on a release they
believed was finished.

Reporting a leftover is not the same as fixing whatever left it there, and this does not
pretend otherwise. But a SILENT leftover is what turns a closed release into a stale tree
nobody expects — the same failure mode as every other defect this session: the product
doing the wrong thing quietly instead of saying so.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.cli.commands.lifecycle import _consumed_slugs_still_present

pytestmark = pytest.mark.unit

_CTX = "auditctx"
_RELEASE = "v0.1.0"


def _workspace(tmp_path: Path, *, claimed: list[str], present: list[str]) -> Path:
    specs = tmp_path / "repos" / _CTX / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "_archive" / _RELEASE).mkdir(parents=True)
    (specs / "_archive" / _RELEASE / "consumed_backlog.json").write_text(
        json.dumps({"release": _RELEASE, "consumed": [{"slug": s} for s in claimed]}),
        encoding="utf-8",
    )
    for slug in present:
        (specs / "backlog" / f"{slug}.md").write_text(f"# {slug}\n", encoding="utf-8")
    return tmp_path


def test_a_consumed_item_left_in_the_backlog_is_named(tmp_path: Path) -> None:
    workspace = _workspace(
        tmp_path, claimed=["csv-line-parser-utility"], present=["csv-line-parser-utility"]
    )

    left = _consumed_slugs_still_present(workspace, context=_CTX, release_id=_RELEASE)

    assert left == ["csv-line-parser-utility"], (
        "closure claimed the item was consumed and left it in the live backlog without "
        "a word; `backlog doctor` then rejects the tree as BL-STALE"
    )


def test_a_clean_closure_reports_nothing(tmp_path: Path) -> None:
    """A check that fires on a healthy closure is noise the operator learns to skip."""
    workspace = _workspace(tmp_path, claimed=["csv-line-parser-utility"], present=[])
    assert _consumed_slugs_still_present(workspace, context=_CTX, release_id=_RELEASE) == []


def test_a_missing_ledger_is_not_an_accusation(tmp_path: Path) -> None:
    """No ledger means nothing was claimed — the audit must not invent a finding."""
    (tmp_path / "repos" / _CTX / "specs" / "backlog").mkdir(parents=True)
    assert _consumed_slugs_still_present(tmp_path, context=_CTX, release_id=_RELEASE) == []
