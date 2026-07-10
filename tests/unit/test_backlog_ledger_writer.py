"""T-26-03 — the consumed_backlog ledger writer (SPEC §3.6 writer, ADR-C).

``write_consumed`` emits specs/_archive/<release-id>/consumed_backlog.json in the EXACT R1
reader shape, keyed on the verified shipped subject-anchor set (not the slug string). The
round-trip proof is: writer output -> R1 read_consumed -> expected {slug: shipped_anchors}.

The operator-local-anchor rejection is a privacy law — kept standalone.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.ledger import LEDGER_FILENAME, read_consumed
from dadaia_workspace.features.backlog.ledger_writer import (
    ConsumedEntry,
    write_consumed,
)


def test_writer_rejects_operator_local_anchor(tmp_path: Path) -> None:
    """PRIVACY (SPEC §3.8): an absolute / operator-local anchor must be rejected."""
    archive_root = tmp_path / "_archive"
    with pytest.raises(ValueError, match="module-relative"):
        write_consumed(
            archive_root=archive_root,
            release_id="v0.1.26",
            consumed=[ConsumedEntry(slug="s", shipped_anchors=frozenset({"/home/op/x.py#Y"}))],
        )


def test_writer_emits_reader_shape_and_round_trips(tmp_path: Path) -> None:
    archive_root = tmp_path / "_archive"
    consumed = [
        ConsumedEntry(slug="old-feature", shipped_anchors=frozenset({"pkg/mod.py#Sym", "INV-foo"})),
        ConsumedEntry(slug="other", shipped_anchors=frozenset({"a/b.py#X"})),
    ]

    path = write_consumed(archive_root=archive_root, release_id="v0.1.26", consumed=consumed)

    assert path == archive_root / "v0.1.26" / LEDGER_FILENAME
    assert path.is_file()

    # R1 reader round-trips the writer output (acceptance §3.7.8).
    back = read_consumed(archive_root)
    assert back == {
        "old-feature": {"pkg/mod.py#Sym", "INV-foo"},
        "other": {"a/b.py#X"},
    }


def test_writer_json_sorted_anchors_creates_dir_and_empty_consumed(tmp_path: Path) -> None:
    archive_root = tmp_path / "_archive"
    assert not archive_root.exists()

    write_consumed(
        archive_root=archive_root,
        release_id="v0.1.26",
        consumed=[ConsumedEntry(slug="s", shipped_anchors=frozenset({"z#b", "a#a"}))],
    )
    data = json.loads((archive_root / "v0.1.26" / LEDGER_FILENAME).read_text(encoding="utf-8"))
    assert data["release"] == "v0.1.26"
    assert data["consumed"][0]["slug"] == "s"
    # Anchors are serialized in a stable sorted order (deterministic output).
    assert data["consumed"][0]["shipped_anchors"] == ["a#a", "z#b"]
    assert (archive_root / "v0.1.26" / LEDGER_FILENAME).is_file()

    empty_root = tmp_path / "_archive_empty"
    write_consumed(archive_root=empty_root, release_id="v0.1.26", consumed=[])
    empty_data = json.loads((empty_root / "v0.1.26" / LEDGER_FILENAME).read_text(encoding="utf-8"))
    assert empty_data["consumed"] == []
    assert read_consumed(empty_root) == {}
