"""Unit tests for the append-only JSONL bug store + BugEvent model + BugService fold.

Covers (T-46-02): append + filename shape, rotation-boundary roll to ``-<n+1>``, fold
coherence (status/stats), malformed-line skip, redaction, and to_dict/from_dict round-trip.
No wall-clock: the store derives the hour bucket from each event's own ``ts``.
"""

from __future__ import annotations

import json
from pathlib import Path

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


# --- model: to_dict / from_dict round-trip ----------------------------------------


def test_reported_to_dict_round_trips() -> None:
    event = _reported("gate-bug")
    restored = BugEvent.from_dict(event.to_dict())
    assert restored == event


def test_to_dict_omits_unset_fields_but_reported_keeps_tags() -> None:
    reported = _reported("b").to_dict()
    assert "tags" in reported and reported["tags"] == ["gate"]
    resolved = _resolved("b").to_dict()
    # A resolved event carries no reported-only fields and no empty tags array.
    assert set(resolved) == {"bug_id", "event", "ts", "reported_by", "release"}


def test_from_dict_rejects_missing_required_field() -> None:
    import pytest

    raw = _resolved("b").to_dict()
    del raw["bug_id"]
    with pytest.raises(ValueError, match="bug_id"):
        BugEvent.from_dict(raw)


def test_is_terminal_excludes_archived() -> None:
    assert _resolved("b").is_terminal is True
    assert BugEvent("b", "archived", _HOUR_TS, "auditor").is_terminal is False
    assert _reported("b").is_terminal is False


# --- model: redaction -------------------------------------------------------------


def test_redact_text_masks_home_and_ip() -> None:
    raw = "failed at /home/marco/workspace/x connecting to 10.1.2.3 and /Users/jane/notes"
    out = redact_text(raw)
    assert "marco" not in out
    assert "jane" not in out
    assert "10.1.2.3" not in out
    assert "/home/[REDACTED]" in out
    assert "/Users/[REDACTED]" in out
    assert "[REDACTED-IP]" in out


def test_redact_leaves_version_tokens_untouched() -> None:
    assert redact_text("shipped in v0.1.46 build 1.2.3") == "shipped in v0.1.46 build 1.2.3"


def test_service_append_redacts_notes(tmp_path: Path) -> None:
    store = JsonlBugStore(tmp_path)
    BugService(store).append_event(
        BugEvent(
            bug_id="leaky",
            event="reported",
            ts=_HOUR_TS,
            reported_by="se",
            title="t",
            severity="LOW",
            surface="s",
            component="c",
            context="ctx",
            tags=(),
            symptom="sy",
            repro="r",
            expected="e",
            notes="crash under /home/marco/secret",
        )
    )
    persisted = list(store.iter_events())
    assert persisted[0].notes is not None
    assert "marco" not in persisted[0].notes
    assert "[REDACTED]" in persisted[0].notes


def test_redact_masks_all_free_text_fields() -> None:
    """symptom/repro/expected/title are free text too (CWE-532) — all must be scrubbed."""
    event = BugEvent(
        bug_id="leaky-fields",
        event="reported",
        ts=_HOUR_TS,
        reported_by="se",
        title="crash in /home/marco/proj",
        severity="LOW",
        symptom="observed at /Users/jane/log while hitting 10.1.2.3",
        repro="run /home/marco/tool then curl 192.168.0.9",
        expected="clean exit under /Users/bob/out",
        notes="see /home/marco/secret",
    )
    red = event.redact()
    # No operator-local username or IP survives on any free-text field.
    for value in (red.title, red.symptom, red.repro, red.expected, red.notes):
        assert value is not None
        assert "marco" not in value
        assert "jane" not in value
        assert "bob" not in value
        assert "10.1.2.3" not in value
        assert "192.168.0.9" not in value
    assert red.title is not None and "[REDACTED]" in red.title
    assert red.symptom is not None and "[REDACTED-IP]" in red.symptom
    assert red.repro is not None and "[REDACTED-IP]" in red.repro
    assert red.expected is not None and "/Users/[REDACTED]" in red.expected
    # Structured/enumerated fields are not free text — left untouched.
    assert red.severity == "LOW"
    assert red.bug_id == "leaky-fields"


def test_redact_service_scrubs_symptom_repro_expected(tmp_path: Path) -> None:
    """End-to-end: a planted path/IP in symptom/repro/expected is masked on append."""
    store = JsonlBugStore(tmp_path)
    BugService(store).append_event(
        BugEvent(
            bug_id="leaky2",
            event="reported",
            ts=_HOUR_TS,
            reported_by="se",
            title="t",
            severity="LOW",
            symptom="fault at /home/marco/x",
            repro="hit 10.0.0.5",
            expected="ok at /Users/jane/y",
        )
    )
    persisted = list(store.iter_events())[0]
    assert persisted.symptom is not None and "marco" not in persisted.symptom
    assert persisted.repro is not None and "10.0.0.5" not in persisted.repro
    assert persisted.expected is not None and "jane" not in persisted.expected


# --- store: append + filename shape -----------------------------------------------


def test_append_writes_single_canonical_file(tmp_path: Path) -> None:
    """v0.1.73 FR1 (bug ``bugs-store-fragments-into-hourly-files``): every append lands
    in the ONE canonical ``bugs.jsonl`` — the operator contract; the v0.1.46 per-hour
    rotation fragmented the ledger into dozens of files."""
    store = JsonlBugStore(tmp_path)
    path = store.append_event(_reported("first"))
    assert path.name == "bugs.jsonl"
    line = path.read_text(encoding="utf-8").strip()
    assert json.loads(line)["bug_id"] == "first"


def test_appends_across_hours_go_to_same_single_file(tmp_path: Path) -> None:
    store = JsonlBugStore(tmp_path)
    p1 = store.append_event(_reported("a", ts="2025-01-02T09:30:00Z"))
    p2 = store.append_event(_reported("b", ts="2026-07-01T15:00:00Z"))
    assert p1 == p2 == tmp_path / "bugs.jsonl"
    assert len(store.files()) == 1


def test_no_rotation_ever_on_canonical_file(tmp_path: Path) -> None:
    """The single-file contract has NO rotation: past the legacy ceiling the append
    still lands in ``bugs.jsonl``."""
    store = JsonlBugStore(tmp_path)
    canonical = tmp_path / "bugs.jsonl"
    with canonical.open("w", encoding="utf-8") as handle:
        for i in range(ROWS_PER_FILE + 5):
            handle.write(json.dumps(_reported(f"seed-{i}").to_dict()) + "\n")
    same = store.append_event(_reported("last"))
    assert same == canonical


def test_iter_events_orders_legacy_then_canonical(tmp_path: Path) -> None:
    """Legacy hourly files stream chronologically FIRST, the canonical file LAST —
    correct in both the pre- and post-consolidation regimes."""
    store = JsonlBugStore(tmp_path)
    store.append_event(_reported("canonical-tail", ts="2026-07-01T15:00:00Z"))
    (tmp_path / f"{_HOUR_BUCKET}Z-00.jsonl").write_text(
        json.dumps(_reported("early0").to_dict()) + "\n", encoding="utf-8"
    )
    (tmp_path / f"{_HOUR_BUCKET}Z-01.jsonl").write_text(
        json.dumps(_reported("early1").to_dict()) + "\n", encoding="utf-8"
    )
    ids = [e.bug_id for e in store.iter_events()]
    assert ids == ["early0", "early1", "canonical-tail"]


# --- store: malformed-line tolerance ----------------------------------------------


def test_iter_events_skips_malformed_lines(tmp_path: Path) -> None:
    store = JsonlBugStore(tmp_path)
    path = tmp_path / f"{_HOUR_BUCKET}Z-00.jsonl"
    good = json.dumps(_reported("good").to_dict())
    path.write_text(
        good + "\n" + "{not json" + "\n" + "\n" + json.dumps({"event": "reported"}) + "\n",
        encoding="utf-8",
    )
    events = list(store.iter_events())
    # Only the one well-formed, schema-complete record survives.
    assert [e.bug_id for e in events] == ["good"]


def test_iter_events_ignores_non_bug_log_files(tmp_path: Path) -> None:
    store = JsonlBugStore(tmp_path)
    store.append_event(_reported("real"))
    (tmp_path / "notes.jsonl").write_text('{"bug_id":"stray"}\n', encoding="utf-8")
    (tmp_path / "readme.md").write_text("hi\n", encoding="utf-8")
    assert [e.bug_id for e in store.iter_events()] == ["real"]


# --- service: fold coherence ------------------------------------------------------


def test_status_folds_open_and_terminal(tmp_path: Path) -> None:
    store = JsonlBugStore(tmp_path)
    svc = BugService(store)
    svc.append_event(_reported("open-1"))
    svc.append_event(_reported("closed-1"))
    svc.append_event(_resolved("closed-1"))

    open_bugs = svc.status()
    assert [s.bug_id for s in open_bugs] == ["open-1"]
    assert open_bugs[0].status == "open"

    all_bugs = {s.bug_id: s.status for s in svc.status(include_closed=True)}
    assert all_bugs == {"open-1": "open", "closed-1": "resolved"}


def test_archived_does_not_change_folded_state(tmp_path: Path) -> None:
    store = JsonlBugStore(tmp_path)
    svc = BugService(store)
    svc.append_event(_reported("b"))
    svc.append_event(_resolved("b"))
    svc.append_event(BugEvent("b", "archived", "2026-07-01T16:00:00Z", "auditor"))
    states = {s.bug_id: s.status for s in svc.status(include_closed=True)}
    assert states == {"b": "resolved"}


def test_stats_aggregates_by_status_and_severity(tmp_path: Path) -> None:
    store = JsonlBugStore(tmp_path)
    svc = BugService(store)
    svc.append_event(_reported("a", severity="HIGH"))
    svc.append_event(_reported("b", severity="LOW"))
    svc.append_event(_reported("c", severity="HIGH"))
    svc.append_event(_resolved("c"))

    stats = svc.stats()
    assert stats.total == 3
    assert stats.by_status == {"open": 2, "resolved": 1}
    assert stats.by_severity == {"HIGH": 2, "LOW": 1}


def test_redact_scrubs_evidence_field() -> None:
    """v0.1.73 security REJECT (bug ``bug-evidence-field-bypasses-redaction``, CWE-532):
    ``evidence`` is operator-authored free text ("reporter-artifact repro") — exactly the
    content class that carries local paths/IPs — and must be scrubbed like notes/repro."""
    event = BugEvent(
        bug_id="ev",
        event="resolved",
        ts=_HOUR_TS,
        reported_by="se",
        release="v9.9.9",
        evidence="replayed /home/ubuntu/workspace repro against 10.0.0.5",
    )
    red = event.redact()
    assert red.evidence is not None
    assert "ubuntu" not in red.evidence
    assert "10.0.0.5" not in red.evidence
