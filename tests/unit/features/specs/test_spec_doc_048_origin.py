"""SPEC-DOC-048: every live and candidate SPEC declares where its work came from.

The SPEC header is the flow's only machine-read input: `operator-demand` names an
operator's direct order, `backlog:<id>` an entry that must resolve in `BACKLOG.json` or
the archived histo, `bugs:<id>` a record of the ledger, whatever its status. Archived releases
under `_archive/` are frozen history and out of scope.

Intent: CONTRACT — AC4.1. Size: SMALL.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.container import build_bug_record_store
from dadaia_workspace.features.specs import SpecsDoctor
from dadaia_workspace.features.specs.rules import RULES

from .test_doctor_ledger_invariants import _by_code, _make_clean_specs_tree

_RELEASE = "0.9.9"
_REPO_ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(autouse=True)
def _no_memory_lint_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

    monkeypatch.setattr(MemoryValidator, "check_lint1_memory_atoms", lambda self: [])


def _write_spec(specs: Path, origin_line: str) -> Path:
    path = specs / "releases" / _RELEASE / "SPEC.md"
    path.write_text(
        f"# Spec\n\n**Status:** Approved\n**Opened:** 2026-09-21\n{origin_line}\n\nBody.\n",
        encoding="utf-8",
    )
    return path


def _issues(specs: Path) -> list[str]:
    doctor = SpecsDoctor(specs, bug_store_factory=build_bug_record_store)
    return [i.description for i in _by_code(doctor.check(), "SPEC-DOC-048")]


def _write_backlog(specs: Path, ids: list[str]) -> None:
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    (specs / "backlog" / "BACKLOG.json").write_text(
        json.dumps({"schema": "backlog-v1", "active": [{"id": i} for i in ids]}),
        encoding="utf-8",
    )


def _write_bugs(specs: Path, records: list[dict[str, object]]) -> None:
    (specs / "bugs").mkdir(parents=True, exist_ok=True)
    (specs / "bugs" / "BUGS.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )


def _bug(bug_id: str, status: str) -> dict[str, object]:
    record: dict[str, object] = {
        "schema": "bug-record-v1",
        "id": bug_id,
        "ts": "2026-09-01T00:00:00Z",
        "title": "A broken contract",
        "severity": "HIGH",
        "surface": "cli",
        "component": "x",
        "context": "dadaia-workspace",
        "reported_by": "dd-software-engineer",
        "symptom": "It breaks.",
        "repro": "dadaia doctor",
        "expected": "exit 0",
        "status": status,
    }
    if status != "open":
        record["closed_at"] = "2026-09-02T00:00:00Z"
        record["cause"] = "the cause"
        record["solution"] = "the fix"
    return record


def test_a_spec_without_an_origin_line_is_an_error(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _write_spec(specs, "")

    issues = _issues(specs)

    assert len(issues) == 1
    assert "Origin" in issues[0]


def test_the_rule_carries_one_fix_naming_the_line() -> None:
    rule = next(r for r in RULES if "SPEC-DOC-048" in r.codes)

    assert rule.fix_help is not None
    assert "**Origin:**" in rule.fix_help
    assert rule.fix_help.split()[0] == "sed"


def test_an_unknown_backlog_id_is_an_error(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _write_backlog(specs, ["a-real-entry"])
    _write_spec(specs, "**Origin:** backlog:a-real-entry,a-ghost")

    issues = _issues(specs)

    assert len(issues) == 1
    assert "a-ghost" in issues[0]
    assert "a-real-entry" not in issues[0]


def test_a_backlog_id_resolving_only_in_the_histo_passes(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _write_backlog(specs, [])
    (specs / "backlog" / "_archive").mkdir(parents=True, exist_ok=True)
    (specs / "backlog" / "_archive" / "backlog_histo.jsonl").write_text(
        json.dumps({"id": "a-shipped-entry", "disposition": "delivered"}) + "\n",
        encoding="utf-8",
    )
    _write_spec(specs, "**Origin:** backlog:a-shipped-entry")

    assert _issues(specs) == []


def test_a_bug_id_passes_whatever_its_status_and_an_unknown_one_errors(tmp_path: Path) -> None:
    """Resolving the cited bug is the flow's purpose — it must not turn the SPEC
    that fixed it into a permanent doctor ERROR. Membership in the ledger is the
    judgement, exactly as `backlog:` judges membership in BACKLOG.json or the histo.
    """
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _write_bugs(specs, [_bug("still-broken", "open"), _bug("already-fixed", "resolved")])

    _write_spec(specs, "**Origin:** bugs:still-broken,already-fixed")
    assert _issues(specs) == []

    _write_spec(specs, "**Origin:** bugs:still-broken,a-ghost")
    issues = _issues(specs)
    assert len(issues) == 1
    assert "a-ghost" in issues[0]
    assert "still-broken" not in issues[0]


def test_a_non_canonical_origin_value_is_an_error(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _write_spec(specs, "**Origin:** because I felt like it")

    issues = _issues(specs)

    assert len(issues) == 1
    assert "not canonical" in issues[0]


def test_an_archived_candidate_spec_under_the_live_release_is_in_scope(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _write_spec(specs, "**Origin:** operator-demand")
    rc = specs / "releases" / _RELEASE / "rc-1"
    rc.mkdir()
    (rc / "SPEC.md").write_text("# Spec\n\n**Status:** Approved\n", encoding="utf-8")

    issues = _issues(specs)

    assert len(issues) == 1
    assert "rc-1" in issues[0]


def test_this_repos_live_and_candidate_specs_all_pass() -> None:
    doctor = SpecsDoctor(_REPO_ROOT / "specs", bug_store_factory=build_bug_record_store)

    issues = doctor._release.check_spec_origin(doctor._governance.known_bug_ids)

    assert _by_code(issues, "SPEC-DOC-048") == []
