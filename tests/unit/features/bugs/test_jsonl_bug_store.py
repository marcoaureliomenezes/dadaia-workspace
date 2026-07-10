"""Unit tests for the append-only JSONL bug store + BugEvent model + BugService fold.

Covers (T-46-02, v0.1.73 FR1): single-canonical-file append contract, iter_events
chronological ordering (legacy-then-canonical) + malformed-line tolerance, the
redaction matrix across every free-text field (incl. the v0.1.73 CWE-532 ``evidence``
regression), and fold coherence (status/stats/archived).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.bugs import BugEvent, redact_text
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_bug_store import ROWS_PER_FILE, JsonlBugStore

_HOUR_TS = "2026-07-01T13:00:00Z"
_HOUR_BUCKET = "20260701T13"


def _reported(bug_id: str, *, severity: str = "HIGH", ts: str = _HOUR_TS) -> BugEvent:
    return BugEvent(
        bug_id=bug_id,
        event="reported",
        ts=ts,
        reported_by="software-engineer",
        title=f"title for {bug_id}",
        severity=severity,
        surface="surface",
        component="spec_context",
        context="dadaia-workspace",
        tags=("gate",),
        symptom="symptom",
        repro="repro",
        expected="expected",
        notes="all good",
    )


def _resolved(bug_id: str, *, ts: str = "2026-07-01T14:00:00Z") -> BugEvent:
    return BugEvent(
        bug_id=bug_id,
        event="resolved",
        ts=ts,
        reported_by="software-engineer",
        release="v0.1.46",
    )


# ---------------------------------------------------------------------------
# Redaction matrix (CWE-532) — every free-text field, incl. the v0.1.73 evidence fix
# ---------------------------------------------------------------------------


def test_redact_text_masks_home_and_ip_leaves_version_tokens_untouched() -> None:
    raw = "failed at /home/marco/workspace/x connecting to 10.1.2.3 and /Users/jane/notes"
    out = redact_text(raw)
    assert "marco" not in out
    assert "jane" not in out
    assert "10.1.2.3" not in out
    assert "/home/[REDACTED]" in out
    assert "/Users/[REDACTED]" in out
    assert "[REDACTED-IP]" in out
    # False-positive guard: version tokens must never be mistaken for a path/IP.
    assert redact_text("shipped in v0.1.46 build 1.2.3") == "shipped in v0.1.46 build 1.2.3"


@pytest.mark.parametrize(
    "field",
    ["title", "symptom", "repro", "expected", "notes", "evidence"],
)
def test_redact_matrix_scrubs_every_free_text_field(field: str, tmp_path: Path) -> None:
    """v0.1.73 security REJECT (bug ``bug-evidence-field-bypasses-redaction``, CWE-532):
    every free-text field — including ``evidence`` (reporter-artifact repro text) —
    must be scrubbed of operator-local usernames and IPs, both via BugEvent.redact()
    and end-to-end through BugService.append_event persistence."""
    leaky = "observed at /home/marco/x and /Users/jane/y hitting 10.1.2.3"
    event = BugEvent(
        bug_id=f"leaky-{field}",
        event="reported" if field != "evidence" else "resolved",
        ts=_HOUR_TS,
        reported_by="se",
        release="v9.9.9" if field == "evidence" else None,
        title="t" if field != "title" else leaky,
        severity="LOW" if field != "evidence" else None,
        surface="s" if field != "evidence" else None,
        component="c" if field != "evidence" else None,
        context="ctx" if field != "evidence" else None,
        tags=() if field != "evidence" else (),
        symptom=leaky if field == "symptom" else ("sy" if field != "evidence" else None),
        repro=leaky if field == "repro" else ("r" if field != "evidence" else None),
        expected=leaky if field == "expected" else ("e" if field != "evidence" else None),
        notes=leaky if field == "notes" else ("all good" if field != "evidence" else None),
        evidence=leaky if field == "evidence" else None,
    )
    red = event.redact()
    value = getattr(red, field)
    assert value is not None
    assert "marco" not in value
    assert "jane" not in value
    assert "10.1.2.3" not in value

    # End-to-end: BugService.append_event persists the redacted value, not the raw one.
    store = JsonlBugStore(tmp_path / field)
    BugService(store).append_event(event)
    persisted = list(store.iter_events())[0]
    persisted_value = getattr(persisted, field)
    assert persisted_value is not None
    assert "marco" not in persisted_value
    assert "jane" not in persisted_value
    assert "10.1.2.3" not in persisted_value


# ---------------------------------------------------------------------------
# Single-canonical-file append contract (v0.1.73 FR1)
# ---------------------------------------------------------------------------


def test_append_writes_single_canonical_file_across_hours_and_past_legacy_ceiling(
    tmp_path: Path,
) -> None:
    """v0.1.73 FR1 (bug ``bugs-store-fragments-into-hourly-files``): every append lands
    in the ONE canonical ``bugs.jsonl`` — the operator contract; the v0.1.46 per-hour
    rotation fragmented the ledger into dozens of files. Holds across distinct event
    hours and past the legacy per-file row ceiling (no rotation ever)."""
    store = JsonlBugStore(tmp_path)
    canonical = tmp_path / "bugs.jsonl"

    path = store.append_event(_reported("first"))
    assert path == canonical
    line = path.read_text(encoding="utf-8").strip()
    assert json.loads(line)["bug_id"] == "first"

    p2 = store.append_event(_reported("a", ts="2025-01-02T09:30:00Z"))
    p3 = store.append_event(_reported("b", ts="2026-07-01T15:00:00Z"))
    assert p2 == p3 == canonical
    assert len(store.files()) == 1

    with canonical.open("a", encoding="utf-8") as handle:
        for i in range(ROWS_PER_FILE + 5):
            handle.write(json.dumps(_reported(f"seed-{i}").to_dict()) + "\n")
    same = store.append_event(_reported("last"))
    assert same == canonical


# ---------------------------------------------------------------------------
# iter_events: chronological ordering + malformed-line / non-bug-file tolerance
# ---------------------------------------------------------------------------


def test_iter_events_orders_legacy_then_canonical_and_tolerates_bad_input(
    tmp_path: Path,
) -> None:
    """Legacy hourly files stream chronologically FIRST, the canonical file LAST —
    correct in both the pre- and post-consolidation regimes. Malformed JSON lines,
    blank lines, and schema-incomplete records are skipped; non-bug-log files
    (unrelated .jsonl, .md) are ignored entirely."""
    store = JsonlBugStore(tmp_path)
    store.append_event(_reported("canonical-tail", ts="2026-07-01T15:00:00Z"))
    (tmp_path / f"{_HOUR_BUCKET}Z-00.jsonl").write_text(
        json.dumps(_reported("early0").to_dict())
        + "\n"
        + "{not json"
        + "\n"
        + "\n"
        + json.dumps({"event": "reported"})
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / f"{_HOUR_BUCKET}Z-01.jsonl").write_text(
        json.dumps(_reported("early1").to_dict()) + "\n", encoding="utf-8"
    )
    (tmp_path / "notes.jsonl").write_text('{"bug_id":"stray"}\n', encoding="utf-8")
    (tmp_path / "readme.md").write_text("hi\n", encoding="utf-8")

    ids = [e.bug_id for e in store.iter_events()]
    assert ids == ["early0", "early1", "canonical-tail"]


# ---------------------------------------------------------------------------
# Service: fold coherence (status/stats/archived)
# ---------------------------------------------------------------------------


def test_status_stats_and_archived_fold_coherently(tmp_path: Path) -> None:
    store = JsonlBugStore(tmp_path)
    svc = BugService(store)
    svc.append_event(_reported("open-1", severity="HIGH"))
    svc.append_event(_reported("closed-1", severity="LOW"))
    svc.append_event(_resolved("closed-1"))
    svc.append_event(_reported("archived-then-resolved", severity="HIGH"))
    svc.append_event(_resolved("archived-then-resolved"))
    svc.append_event(
        BugEvent("archived-then-resolved", "archived", "2026-07-01T16:00:00Z", "auditor")
    )

    open_bugs = svc.status()
    assert {s.bug_id for s in open_bugs} == {"open-1"}
    assert open_bugs[0].status == "open"

    all_bugs = {s.bug_id: s.status for s in svc.status(include_closed=True)}
    assert all_bugs == {
        "open-1": "open",
        "closed-1": "resolved",
        "archived-then-resolved": "resolved",
    }

    stats = svc.stats()
    assert stats.total == 3
    assert stats.by_status == {"open": 1, "resolved": 2}
    assert stats.by_severity == {"HIGH": 2, "LOW": 1}
