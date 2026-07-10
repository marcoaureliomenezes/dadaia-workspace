"""Round-trip tests for the ``specs/bugs/*.md`` → JSONL migration (T-46-05, AC-2).

Mandatory round-trip over a fixture bugs-tree asserts, in one migration run:
  (1) the emitted JSONL is the EXACT expected event stream per source bug (status
      shapes: open/resolved/superseded/unknown-release);
  (2) a re-run is a no-op (idempotent — no duplicate events, no re-move), and a
      partial prior run (jsonl written, .md still present) does not re-emit;
  (3) ``--dry-run`` writes nothing AND moves nothing (reports the plan only);
  (4) CRITICAL — the migrated streams pass SPEC-DOC-033 doctor coherence, including
      the closed-before-reported terminal-ts clamp (data-loss/false-ERROR guard).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dadaia_workspace.features.migrate.bugs_jsonl import migrate_bugs_jsonl

_OPEN_MD = """\
---
name: open-gate-bug
status: Open
severity: High
reported: 2026-06-27
surface: pre-commit gate
---

**Symptom:** the gate blocks a legitimate commit.

**Repro:** commit a consumed item.

**Expected:** the commit flows.

**Notes:** seen under /home/marco/workspace at 10.0.0.1.
"""

_CLOSED_RESOLVED_MD = """\
---
name: closed-resolved-bug
status: Closed
severity: MEDIUM
reported: 2026-06-10
resolved_in: v0.1.30
surface: cli/commands/context.py
---

**Symptom:** bind keyed by the wrong id.

**Expected:** bind keyed by harness sid.
"""

_CLOSED_SUPERSEDED_MD = """\
---
name: closed-superseded-bug
status: Closed
severity: LOW
reported: 2026-06-12
superseded_by: panel-ux-overhaul
---

**Symptom:** duplicate defect.
"""

_CLOSED_UNKNOWN_MD = """\
---
name: closed-unknown-bug
status: Closed
severity: HIGH
reported: 2026-06-11
---

**Symptom:** closed but no closing release recorded.
"""

# A legacy Closed bug whose `closed` date PRECEDES its `reported` date (data-entry skew).
# The terminal ts must be clamped up to the reported ts, else the emitted stream splits
# across two hour-buckets out of order and trips a false coherence ERROR (FIX 3).
_CLOSED_BEFORE_REPORTED_MD = """\
---
name: closed-before-reported-bug
status: Closed
severity: LOW
reported: 2026-06-27
closed: 2026-06-10
resolved_in: v0.1.40
---

**Symptom:** closed date recorded before the reported date.
"""


def _seed_bugs_tree(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    bugs = specs / "bugs"
    bugs.mkdir(parents=True)
    (bugs / "_archive").mkdir()  # precondition T-46-11
    (bugs / "open-gate-bug.md").write_text(_OPEN_MD, encoding="utf-8")
    (bugs / "closed-resolved-bug.md").write_text(_CLOSED_RESOLVED_MD, encoding="utf-8")
    (bugs / "closed-superseded-bug.md").write_text(_CLOSED_SUPERSEDED_MD, encoding="utf-8")
    (bugs / "closed-unknown-bug.md").write_text(_CLOSED_UNKNOWN_MD, encoding="utf-8")
    return specs


def _all_events(bugs_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for jsonl in sorted(bugs_dir.glob("*.jsonl")):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def _by_bug(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for e in events:
        out.setdefault(e["bug_id"], []).append(e)
    return out


# ---------------------------------------------------------------------------
# Event-emission shapes (open / resolved / superseded / unknown-release)
# ---------------------------------------------------------------------------


def test_event_emission_shapes(tmp_path: Path) -> None:
    specs = _seed_bugs_tree(tmp_path)
    result = migrate_bugs_jsonl(specs)
    by_bug = _by_bug(_all_events(specs / "bugs"))

    open_stream = by_bug["open-gate-bug"]
    assert [e["event"] for e in open_stream] == ["reported"]
    ev = open_stream[0]
    assert ev["ts"] == "2026-06-27T00:00:00Z"
    assert ev["severity"] == "HIGH"
    assert ev["surface"] == "pre-commit gate"
    assert ev["symptom"] == "the gate blocks a legitimate commit."
    # notes were redacted of the operator-local path + IP.
    assert "marco" not in ev["notes"]
    assert "10.0.0.1" not in ev["notes"]

    resolved_stream = by_bug["closed-resolved-bug"]
    assert [e["event"] for e in resolved_stream] == ["reported", "resolved"]
    assert resolved_stream[1]["release"] == "v0.1.30"

    superseded_stream = by_bug["closed-superseded-bug"]
    assert [e["event"] for e in superseded_stream] == ["reported", "superseded"]
    assert superseded_stream[1]["superseded_by"] == "panel-ux-overhaul"

    unknown_stream = by_bug["closed-unknown-bug"]
    assert [e["event"] for e in unknown_stream] == ["reported", "resolved"]
    assert unknown_stream[1]["release"] == "unknown"
    assert any("unknown" in w and "closed-unknown-bug" in w for w in result.skipped)


# ---------------------------------------------------------------------------
# CRITICAL: doctor coherence, incl. closed-before-reported terminal-ts clamp
# ---------------------------------------------------------------------------


def test_migrated_streams_pass_doctor_coherence(tmp_path: Path) -> None:
    """The emitted streams must be coherent under SPEC-DOC-033."""
    from dadaia_workspace.features.specs import SpecsDoctor

    specs = _seed_bugs_tree(tmp_path)
    migrate_bugs_jsonl(specs)
    doc033 = [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-033"]
    assert doc033 == []


def test_closed_before_reported_clamps_terminal_ts_and_stays_coherent(tmp_path: Path) -> None:
    """A Closed bug whose `closed` predates `reported` must still emit a coherent stream.

    Without clamping, the terminal event lands in an earlier hour-bucket than its own
    `reported`, so the doctor reads a terminal-without-prior-reported ERROR (FIX 3).
    """
    from dadaia_workspace.features.specs import SpecsDoctor

    specs = tmp_path / "specs"
    bugs = specs / "bugs"
    bugs.mkdir(parents=True)
    (bugs / "_archive").mkdir()
    (bugs / "closed-before-reported-bug.md").write_text(
        _CLOSED_BEFORE_REPORTED_MD, encoding="utf-8"
    )

    migrate_bugs_jsonl(specs)

    stream = _by_bug(_all_events(bugs))["closed-before-reported-bug"]
    assert [e["event"] for e in stream] == ["reported", "resolved"]
    reported_ts, terminal_ts = stream[0]["ts"], stream[1]["ts"]
    # Terminal ts clamped up to the reported ts (never before it).
    assert terminal_ts >= reported_ts
    assert terminal_ts == "2026-06-27T00:00:00Z"
    # And the emitted stream is doctor-clean.
    doc033 = [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-033"]
    assert doc033 == []


# ---------------------------------------------------------------------------
# Idempotence: rerun-noop, partial-skip, dry-run
# ---------------------------------------------------------------------------


def test_rerun_noop_partial_skip_and_dry_run(tmp_path: Path) -> None:
    # (1) full rerun is a no-op.
    specs = _seed_bugs_tree(tmp_path)
    migrate_bugs_jsonl(specs)
    first = _all_events(specs / "bugs")
    second_result = migrate_bugs_jsonl(specs)
    second = _all_events(specs / "bugs")
    assert second == first
    assert second_result.moved == []

    # (2) a partial prior run (jsonl written, .md re-appears) is not re-emitted.
    events_before = _all_events(specs / "bugs")
    (specs / "bugs" / "open-gate-bug.md").write_text(_OPEN_MD, encoding="utf-8")
    result = migrate_bugs_jsonl(specs)
    assert _all_events(specs / "bugs") == events_before
    assert any("already in JSONL" in msg for msg in result.skipped)

    # (3) dry-run on a fresh tree writes and moves nothing but plans.
    fresh_specs = _seed_bugs_tree(tmp_path.parent / (tmp_path.name + "-fresh"))
    dry_result = migrate_bugs_jsonl(fresh_specs, dry_run=True)
    bugs = fresh_specs / "bugs"
    assert list(bugs.glob("*.jsonl")) == []
    assert sorted(p.name for p in bugs.glob("*.md")) == [
        "closed-resolved-bug.md",
        "closed-superseded-bug.md",
        "closed-unknown-bug.md",
        "open-gate-bug.md",
    ]
    assert list((bugs / "_archive").glob("*.md")) == []
    assert len(dry_result.moved) == 4
    assert dry_result.dry_run is True
