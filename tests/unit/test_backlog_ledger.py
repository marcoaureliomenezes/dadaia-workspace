"""Unit tests for the ``consumed_backlog`` ledger reader (T-25-05, SPEC §3.6, ADR-C).

R1 READS the sidecar JSON at ``specs/_archive/<release>/consumed_backlog.json`` by exact slug
membership; the writer is R2. The read is a **no-op (empty) when absent** — never a false
ERROR (acceptance §3.7.6). All paths injected (SPEC §3.8 #6). Fixtures use ``tmp_path``.

Absent-is-noop (never false ERROR) row preserved; malformed-ledger-skipped-not-crash kept
standalone.
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


def test_absent_or_empty_archive_root_is_noop(tmp_path: Path) -> None:
    assert read_consumed(tmp_path / "does-not-exist") == {}
    (tmp_path / "_archive").mkdir()
    assert read_consumed(tmp_path / "_archive") == {}


def test_single_multi_release_and_union_reads(tmp_path: Path) -> None:
    single = tmp_path / "single"
    _write_ledger(single, "v0.1.20", [{"slug": "old-feature", "shipped_anchors": ["a#X", "b#Y"]}])
    assert read_consumed(single) == {"old-feature": {"a#X", "b#Y"}}

    multi = tmp_path / "multi"
    _write_ledger(multi, "v0.1.20", [{"slug": "feat-a", "shipped_anchors": ["a#X"]}])
    _write_ledger(multi, "v0.1.21", [{"slug": "feat-b", "shipped_anchors": ["b#Y"]}])
    assert set(read_consumed(multi)) == {"feat-a", "feat-b"}

    union = tmp_path / "union"
    _write_ledger(union, "v0.1.20", [{"slug": "feat-a", "shipped_anchors": ["a#X"]}])
    _write_ledger(union, "v0.1.21", [{"slug": "feat-a", "shipped_anchors": ["a#Z"]}])
    assert read_consumed(union)["feat-a"] == {"a#X", "a#Z"}


def test_malformed_ledger_skipped_not_crash(tmp_path: Path) -> None:
    archive = tmp_path / "_archive"
    bad = archive / "v0.1.99"
    bad.mkdir(parents=True)
    (bad / "consumed_backlog.json").write_text("{ not json", encoding="utf-8")
    # A good ledger alongside the malformed one still reads.
    _write_ledger(archive, "v0.1.20", [{"slug": "feat-a", "shipped_anchors": ["a#X"]}])
    consumed = read_consumed(archive)
    assert consumed == {"feat-a": {"a#X"}}


def test_entry_without_anchors_tolerated_and_without_slug_skipped(tmp_path: Path) -> None:
    tolerant = tmp_path / "tolerant"
    _write_ledger(tolerant, "v0.1.20", [{"slug": "feat-a"}])
    assert read_consumed(tolerant) == {"feat-a": set()}

    skipped = tmp_path / "skipped"
    _write_ledger(skipped, "v0.1.20", [{"shipped_anchors": ["a#X"]}])
    assert read_consumed(skipped) == {}
