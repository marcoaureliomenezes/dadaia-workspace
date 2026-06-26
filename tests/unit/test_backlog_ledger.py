"""Unit tests for the ``consumed_backlog`` ledger reader (T-25-05, SPEC §3.6, ADR-C).

R1 READS the sidecar JSON at ``specs/_archive/<release>/consumed_backlog.json`` by exact slug
membership; the writer is R2. The read is a **no-op (empty) when absent** — never a false
ERROR (acceptance §3.7.6). All paths injected (SPEC §3.8 #6). Fixtures use ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.ledger import read_consumed

pytestmark = pytest.mark.unit


def _write_ledger(archive_root: Path, release: str, entries: list[dict[str, object]]) -> None:
    rel_dir = archive_root / release
    rel_dir.mkdir(parents=True, exist_ok=True)
    (rel_dir / "consumed_backlog.json").write_text(
        json.dumps({"release": release, "consumed": entries}), encoding="utf-8"
    )


def test_absent_archive_root_is_noop(tmp_path: Path) -> None:
    assert read_consumed(tmp_path / "does-not-exist") == {}


def test_empty_archive_root_is_noop(tmp_path: Path) -> None:
    (tmp_path / "_archive").mkdir()
    assert read_consumed(tmp_path / "_archive") == {}


def test_single_ledger_read(tmp_path: Path) -> None:
    archive = tmp_path / "_archive"
    _write_ledger(
        archive,
        "v0.1.20",
        [{"slug": "old-feature", "shipped_anchors": ["a#X", "b#Y"]}],
    )
    consumed = read_consumed(archive)
    assert consumed == {"old-feature": {"a#X", "b#Y"}}


def test_membership_across_multiple_releases(tmp_path: Path) -> None:
    archive = tmp_path / "_archive"
    _write_ledger(archive, "v0.1.20", [{"slug": "feat-a", "shipped_anchors": ["a#X"]}])
    _write_ledger(archive, "v0.1.21", [{"slug": "feat-b", "shipped_anchors": ["b#Y"]}])
    consumed = read_consumed(archive)
    assert set(consumed) == {"feat-a", "feat-b"}


def test_same_slug_union_across_releases(tmp_path: Path) -> None:
    archive = tmp_path / "_archive"
    _write_ledger(archive, "v0.1.20", [{"slug": "feat-a", "shipped_anchors": ["a#X"]}])
    _write_ledger(archive, "v0.1.21", [{"slug": "feat-a", "shipped_anchors": ["a#Z"]}])
    consumed = read_consumed(archive)
    assert consumed["feat-a"] == {"a#X", "a#Z"}


def test_malformed_ledger_skipped_not_crash(tmp_path: Path) -> None:
    archive = tmp_path / "_archive"
    bad = archive / "v0.1.99"
    bad.mkdir(parents=True)
    (bad / "consumed_backlog.json").write_text("{ not json", encoding="utf-8")
    # A good ledger alongside the malformed one still reads.
    _write_ledger(archive, "v0.1.20", [{"slug": "feat-a", "shipped_anchors": ["a#X"]}])
    consumed = read_consumed(archive)
    assert consumed == {"feat-a": {"a#X"}}


def test_entry_without_anchors_tolerated(tmp_path: Path) -> None:
    archive = tmp_path / "_archive"
    _write_ledger(archive, "v0.1.20", [{"slug": "feat-a"}])
    consumed = read_consumed(archive)
    assert consumed == {"feat-a": set()}


def test_entry_without_slug_skipped(tmp_path: Path) -> None:
    archive = tmp_path / "_archive"
    _write_ledger(archive, "v0.1.20", [{"shipped_anchors": ["a#X"]}])
    assert read_consumed(archive) == {}
