"""``BugService.normalize_records`` — the ONE fixer that puts a committed bug record
back into its canonical shape (0.4.7 FR1, T-047-25).

Intent: CONTRACT — 0.4.7 FR1 (`dadaia doctor --fix` strips the retired provenance keys
from the committed ledger and histo losslessly; a terminal record missing ``closed_at``
is stamped from its own ``ts``).
Size: SMALL — raw JSONL files under tmp_path, no git, no subprocess, no real ledger.

Structural frame: the seven retired keys were a git-derived CACHE stored in the record
(`resolved_commit` & co). Deriving them needed a full history walk every CI job fetched
depth-0 for, and every reader disagreed about the walk — the bug family that produced
`git history walk omits --full-history` and `Contract coverage CI job's default shallow
checkout makes BugService.resolved_commit derive HEAD`. Deleting the cache deletes the
family; this fixer is how the 541 committed records lose it.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.bugs.service import BugService

from ._bug_record_helpers import bug_archive_store, bug_record_store

_TS = "2026-08-26T10:00:00Z"

_RETIRED = {
    "lineage_source": "declared",
    "registration_commit": "a" * 40,
    "registration_granularity": "exact",
    "resolved_commit": "b" * 40,
    "resolution_granularity": "ledger-only",
    "root_cause": "the old duplicate of cause",
    "migration_note": "unmapped legacy surface",
}


def _legacy(bug_id: str, *, status: str, closed_at: str | None = None) -> dict[str, object]:
    return {
        "id": bug_id,
        "ts": _TS,
        "reported_by": "dd-software-engineer",
        "title": "t",
        "severity": "HIGH",
        "surface": "bugs",
        "component": "c",
        "context": "dadaia-workspace",
        "symptom": "s",
        "repro": "r",
        "expected": "e",
        "status": status,
        "closed_at": closed_at,
        "cause": "c" if status != "open" else None,
        "caused_by": None,
        "resolved_release": "0.4.6" if status != "open" else None,
        "audited": None,
        **_RETIRED,
    }


def _write(path: Path, records: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8"
    )
    return path


def _read(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()
    ]


def _service(tmp_path: Path) -> BugService:
    return BugService(bug_record_store(tmp_path), archive_store=bug_archive_store(tmp_path))


def test_normalize_strips_every_retired_key_from_the_ledger_and_the_histo(
    tmp_path: Path,
) -> None:
    """One pass, both files: the derived cache leaves 541 committed records and nothing
    else about them changes."""
    ledger = _write(
        tmp_path / "bugs" / "BUGS.jsonl",
        [_legacy("bug-live", status="resolved", closed_at="2026-09-01T00:00:00Z")],
    )
    histo = _write(
        tmp_path / "bugs" / "_archive" / "bugs_histo.jsonl",
        [_legacy("bug-old", status="rejected", closed_at="2026-09-01T00:00:00Z")],
    )

    assert _service(tmp_path).normalize_records() == 2

    for path, bug_id in ((ledger, "bug-live"), (histo, "bug-old")):
        record = _read(path)[0]
        assert set(record) & set(_RETIRED) == set()
        assert record["id"] == bug_id
        assert record["cause"] == "c"
        assert record["resolved_release"] == "0.4.6"
        assert record["closed_at"] == "2026-09-01T00:00:00Z"


def test_normalize_stamps_a_terminal_record_missing_closed_at_from_its_own_ts(
    tmp_path: Path,
) -> None:
    """Arm B's back-fill survives the cache's deletion with the ``ts`` fallback ALONE —
    the ledger's git history is never consulted (bug
    ``bugs-update-cannot-heal-terminal-record-missing-closed-at``)."""
    ledger = _write(tmp_path / "bugs" / "BUGS.jsonl", [_legacy("bug-beta", status="resolved")])

    assert _service(tmp_path).normalize_records() == 1
    assert _read(ledger)[0]["closed_at"] == _TS
    assert [r.id for r in _service(tmp_path).status(include_closed=True)] == ["bug-beta"]


def test_normalize_is_idempotent_and_preserves_a_line_it_cannot_read(tmp_path: Path) -> None:
    """A canonical ledger is never rewritten (the doctor calls a fixer once per reported
    issue), and a line this fixer cannot parse is preserved verbatim rather than dropped."""
    ledger = _write(tmp_path / "bugs" / "BUGS.jsonl", [_legacy("bug-x", status="open")])
    _service(tmp_path).normalize_records()
    ledger.write_text(ledger.read_text(encoding="utf-8") + "not json at all\n", encoding="utf-8")
    before = ledger.read_text(encoding="utf-8")

    assert _service(tmp_path).normalize_records() == 0
    assert ledger.read_text(encoding="utf-8") == before
