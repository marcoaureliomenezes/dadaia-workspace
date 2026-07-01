"""Unit tests for SpecsDoctor SPEC-DOC-033 — event-sourced JSONL bug-telemetry invariant.

Release v0.1.46 / T-46-04 (AC-1). Covers per-line schema validity, the rotation ceiling,
and event coherence over the terminal set {resolved, superseded, deferred, rejected}.

Coherence tests require BOTH incoherence classes to ERROR — (a) terminal-without-prior-
``reported`` and (b) double-terminal — PLUS a valid ``reported``→``resolved`` negative
control that must NOT error, PLUS an ``archived``-after-``resolved`` case that must NOT
error (the non-terminal exemption).
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.specs import Severity, SpecsDoctor


def _bugs_dir(specs: Path) -> Path:
    d = specs / "bugs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _reported(bug_id: str, *, severity: str = "HIGH", ts: str = "2026-07-01T13:00:00Z") -> dict:
    return {
        "bug_id": bug_id,
        "event": "reported",
        "ts": ts,
        "reported_by": "software-engineer",
        "title": f"title {bug_id}",
        "severity": severity,
        "surface": "gate",
        "component": "spec_context",
        "context": "dadaia-workspace",
        "tags": ["gate"],
        "symptom": "sym",
        "repro": "repro",
        "expected": "exp",
        "notes": "n",
    }


def _resolved(bug_id: str, *, ts: str = "2026-07-01T14:00:00Z") -> dict:
    return {
        "bug_id": bug_id,
        "event": "resolved",
        "ts": ts,
        "reported_by": "software-engineer",
        "release": "v0.1.46",
    }


def _write_log(bugs: Path, name: str, events: list[dict]) -> Path:
    path = bugs / name
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def _doc033(specs: Path) -> list:
    return [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-033"]


# --- no-op / clean --------------------------------------------------------------------


def test_no_bugs_dir_is_noop(tmp_path: Path) -> None:
    (tmp_path / "specs").mkdir()
    assert _doc033(tmp_path / "specs") == []


def test_coherent_reported_then_resolved_is_clean_negative_control(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(bugs, "20260701T13Z-00.jsonl", [_reported("bug-a"), _resolved("bug-a")])
    assert _doc033(specs) == []


def test_archived_after_resolved_is_exempt_and_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    archived = {
        "bug_id": "bug-a",
        "event": "archived",
        "ts": "2026-07-01T15:00:00Z",
        "reported_by": "project-auditor",
    }
    _write_log(bugs, "20260701T13Z-00.jsonl", [_reported("bug-a"), _resolved("bug-a"), archived])
    assert _doc033(specs) == []


# --- coherence: the two incoherence classes -------------------------------------------


def test_terminal_without_prior_reported_errors(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(bugs, "20260701T13Z-00.jsonl", [_resolved("orphan")])
    errors = _doc033(specs)
    assert len(errors) == 1
    assert errors[0].severity is Severity.ERROR
    assert "no prior 'reported'" in errors[0].description


def test_double_terminal_errors(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(
        bugs,
        "20260701T13Z-00.jsonl",
        [_reported("bug-a"), _resolved("bug-a"), _resolved("bug-a", ts="2026-07-01T16:00:00Z")],
    )
    errors = _doc033(specs)
    assert len(errors) == 1
    assert errors[0].severity is Severity.ERROR
    assert "second terminal event" in errors[0].description


def test_coherence_spans_multiple_files_in_chronological_order(tmp_path: Path) -> None:
    """A reported in an earlier file makes a terminal in a later file coherent."""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(bugs, "20260701T13Z-00.jsonl", [_reported("bug-a")])
    _write_log(bugs, "20260701T14Z-00.jsonl", [_resolved("bug-a")])
    assert _doc033(specs) == []


# --- per-line schema validity ---------------------------------------------------------


def test_malformed_json_line_errors(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    (bugs / "20260701T13Z-00.jsonl").write_text("{not json\n", encoding="utf-8")
    errors = _doc033(specs)
    assert len(errors) == 1
    assert "not valid JSON" in errors[0].description


def test_reported_missing_required_payload_fails_schema(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    incomplete = {
        "bug_id": "b",
        "event": "reported",
        "ts": "2026-07-01T13:00:00Z",
        "reported_by": "se",
        "title": "only a title",
    }
    _write_log(bugs, "20260701T13Z-00.jsonl", [incomplete])
    errors = _doc033(specs)
    assert any("schema" in e.description for e in errors)
    assert all(e.severity is Severity.ERROR for e in errors)


def test_bad_event_enum_fails_schema(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    bad = {"bug_id": "b", "event": "exploded", "ts": "2026-07-01T13:00:00Z", "reported_by": "se"}
    _write_log(bugs, "20260701T13Z-00.jsonl", [bad])
    errors = _doc033(specs)
    assert any("schema" in e.description for e in errors)


# --- rotation ceiling -----------------------------------------------------------------


def test_over_ceiling_errors(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    # 1001 valid reported rows (distinct bug_ids so coherence stays clean) > 1000 ceiling.
    events = [_reported(f"b{i}") for i in range(1001)]
    _write_log(bugs, "20260701T13Z-00.jsonl", events)
    errors = _doc033(specs)
    ceiling = [e for e in errors if "rotation ceiling" in e.description]
    assert len(ceiling) == 1
    assert ceiling[0].severity is Severity.ERROR


def test_exactly_ceiling_is_clean(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    events = [_reported(f"b{i}") for i in range(1000)]
    _write_log(bugs, "20260701T13Z-00.jsonl", events)
    assert [e for e in _doc033(specs) if "rotation ceiling" in e.description] == []
