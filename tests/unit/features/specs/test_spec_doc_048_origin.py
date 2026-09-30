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

from dadaia_workspace.features.specs import SpecsDoctor

from .test_doctor import _by_code, _make_clean_specs_tree

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
    doctor = SpecsDoctor(specs)
    return [i.message for i in _by_code(doctor.check(), "SPEC-DOC-048")]


def _seed(specs: Path) -> None:
    (specs / "backlog" / "_archive").mkdir(parents=True, exist_ok=True)
    active = {"schema": "backlog-v1", "active": [{"id": "a-real-entry"}]}
    (specs / "backlog" / "BACKLOG.json").write_text(json.dumps(active), encoding="utf-8")
    shipped = {"id": "a-shipped-entry", "disposition": "delivered"}
    (specs / "backlog" / "_archive" / "backlog_histo.jsonl").write_text(json.dumps(shipped) + "\n")
    malformed = {**_bug("half-written", "open"), "context": "", "severity": "BLOCKER"}
    records = [_bug("still-broken", "open"), _bug("already-fixed", "resolved"), malformed]
    (specs / "bugs").mkdir(parents=True, exist_ok=True)
    (specs / "bugs" / "BUGS.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))


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
        record |= {"closed_at": "2026-09-02T00:00:00Z", "cause": "c", "solution": "s"}
    return record


@pytest.mark.parametrize(
    ("origin", "needle", "absent"),
    [
        pytest.param("", "Origin", None, id="no-origin-line"),
        pytest.param(
            "**Origin:** backlog:a-real-entry,a-ghost",
            "a-ghost",
            "a-real-entry",
            id="unknown-backlog-id",
        ),
        pytest.param(
            "**Origin:** backlog:a-shipped-entry", None, None, id="backlog-id-in-histo-only"
        ),
        pytest.param(
            "**Origin:** bugs:still-broken,already-fixed,half-written",
            None,
            None,
            id="B4-bug-id-any-status-or-schema",
        ),
        pytest.param(
            "**Origin:** bugs:still-broken,a-ghost", "a-ghost", "still-broken", id="unknown-bug-id"
        ),
        pytest.param(
            "**Origin:** because I felt like it", "not canonical", None, id="non-canonical-value"
        ),
    ],
)
def test_spec_origin(tmp_path: Path, origin: str, needle: str | None, absent: str | None) -> None:
    """sa-spec-doc-033-duplicates-bugs-check#B4: SPEC-DOC-048 reads raw ids — a bug id
    resolves whatever its status, and an id whose record fails the schema still exists.
    An error names only the unresolved ids."""
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _seed(specs)
    _write_spec(specs, origin)

    issues = _issues(specs)

    if needle is None:
        assert issues == []
    else:
        [issue] = issues
        assert needle in issue and (absent is None or absent not in issue)


def test_a_candidate_folder_is_not_ranked_and_is_off_canon(tmp_path: Path) -> None:
    """sa-release-json-validated-three-times#B6: rc-1/SPEC.md is history, never ranked —
    SPEC-DOC-048 stays silent and TREE-8 names the path (no rc-N canon member)."""
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _write_spec(specs, "**Origin:** operator-demand")
    rc = specs / "releases" / _RELEASE / "rc-1"
    rc.mkdir()
    (rc / "SPEC.md").write_text("# Spec\n\n**Status:** Approved\n", encoding="utf-8")

    assert _issues(specs) == []
    tree8 = [i for i in SpecsDoctor(specs).check() if i.code == "TREE-8"]
    assert any("rc-1/SPEC.md" in i.message for i in tree8), tree8


def test_this_repos_live_and_candidate_specs_all_pass() -> None:
    doctor = SpecsDoctor(_REPO_ROOT / "specs")

    issues = doctor._release.check_spec_origin(doctor._governance.known_bug_ids)

    assert _by_code(issues, "SPEC-DOC-048") == []
