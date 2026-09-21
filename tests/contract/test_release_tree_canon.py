"""``validate_release_tree`` over the real governance tree (0.4.7 FR1 / T-047-01).

Intent: CONTRACT — T-047-01: every committed ``_RELEASE.json`` (live and archived)
validates ``release-state-v1``, parses, carries a monotonic ``log``, one of the four
canonical phases, the ARCHIVED phase iff it lives under ``_archive/``, and the live
release carries its SPEC/PLAN/TASKS trio. The bug this closes
(``archived-release-state-invalid-and-unparseable-doctor-silent``) existed because the
schema was only ever exercised against synthetic fixtures — no code path read the
archived documents at all.
Size: SMALL — reads the repo's own ``specs/`` tree plus tmp_path fixtures; no
subprocess, no network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.specs import ReleaseTreeIssue, validate_release_tree

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _codes(issues: list[ReleaseTreeIssue]) -> list[str]:
    return [i.code for i in issues]


def _valid_document(**overrides: Any) -> dict[str, Any]:
    """A minimal document that passes every rule, before the caller breaks one field."""
    base: dict[str, Any] = {
        "schema": "release-state-v1",
        "release": "9.9.9",
        "phase": "DEFINITION",
        "rc": None,
        "defined": {"sha": "a" * 40, "ts": "2026-09-01T00:00:00Z"},
        "implemented": None,
        "shipped": None,
        "log": [
            {
                "ts": "2026-09-01T00:00:00Z",
                "agent": "product-engineer",
                "kind": "note",
                "text": "x",
            },
            {
                "ts": "2026-09-02T00:00:00Z",
                "agent": "product-engineer",
                "kind": "note",
                "text": "y",
            },
        ],
    }
    base.update(overrides)
    return base


def _write_release(root: Path, rel_dir: str, doc: dict[str, Any], *, trio: bool = True) -> Path:
    d = root / "releases" / rel_dir
    d.mkdir(parents=True, exist_ok=True)
    (d / "_RELEASE.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    if trio:
        for artifact in ("SPEC.md", "PLAN.md", "TASKS.md"):
            (d / artifact).write_text("**Status:** Approved\n", encoding="utf-8")
    return d


def test_real_tree_validates() -> None:
    """The repo's own specs/ tree — live 0.4.7 plus five archived releases."""
    issues = validate_release_tree(_REPO_ROOT / "specs")
    assert issues == [], [f"{i.path}: {i.code} {i.message}" for i in issues]


def test_pre_wave0_046_document_is_refused(tmp_path: Path) -> None:
    """The 0.4.6 archived document as committed before Wave 0: ``shipped`` without
    ``pr`` (``git show 7db9553c^:specs/releases/_archive/0.4.6/_RELEASE.json``)."""
    doc = _valid_document(
        release="0.4.6",
        phase="ARCHIVED",
        rc=3,
        implemented={"sha": "b" * 40, "rc": 3, "ts": "2026-09-05T00:00:00Z"},
        shipped={"sha": "c" * 40, "ts": "2026-09-06T15:05:36Z"},
    )
    _write_release(tmp_path, "_archive/0.4.6", doc, trio=False)

    issues = validate_release_tree(tmp_path)

    schema_issues = [i for i in issues if i.code == "RELEASE-TREE-SCHEMA"]
    assert len(schema_issues) == 1, _codes(issues)
    assert schema_issues[0].path == "releases/_archive/0.4.6/_RELEASE.json"
    assert "pr" in schema_issues[0].message
    assert "RELEASE-TREE-PARSE" in _codes(issues)


def test_non_monotonic_log_is_refused(tmp_path: Path) -> None:
    doc = _valid_document()
    doc["log"][1]["ts"] = "2026-08-01T00:00:00Z"
    _write_release(tmp_path, "9.9.9", doc)

    assert _codes(validate_release_tree(tmp_path)) == ["RELEASE-TREE-TS-ORDER"]


def test_phase_outside_the_four_is_refused(tmp_path: Path) -> None:
    _write_release(tmp_path, "9.9.9", _valid_document(phase="DISCOVERY"))

    issues = validate_release_tree(tmp_path)
    assert _codes(issues) == ["RELEASE-TREE-SCHEMA", "RELEASE-TREE-PHASE"], (
        "0.4.7 FR4 closed the phase enum in the schema too: a non-canonical phase is "
        "now refused by BOTH the schema and the parsed-state rule"
    )
    assert "DISCOVERY" in issues[0].message


def test_archived_dir_not_in_archived_phase_is_refused(tmp_path: Path) -> None:
    _write_release(tmp_path, "_archive/0.5.9", _valid_document(phase="CLOSURE"), trio=False)

    issues = validate_release_tree(tmp_path)
    assert _codes(issues) == ["RELEASE-TREE-ARCHIVED"]
    assert issues[0].path == "releases/_archive/0.5.9/_RELEASE.json"


def test_live_dir_in_archived_phase_is_refused(tmp_path: Path) -> None:
    _write_release(tmp_path, "9.9.9", _valid_document(phase="ARCHIVED"))

    assert _codes(validate_release_tree(tmp_path)) == ["RELEASE-TREE-ARCHIVED"]


def test_live_release_missing_plan_is_refused(tmp_path: Path) -> None:
    """IMPLEMENTATION: the candidate is under way, so all three are required."""
    d = _write_release(tmp_path, "9.9.9", _valid_document(phase="IMPLEMENTATION"))
    (d / "PLAN.md").unlink()

    issues = validate_release_tree(tmp_path)
    assert _codes(issues) == ["RELEASE-TREE-TRIO"]
    assert "PLAN.md" in issues[0].message


def test_closure_release_missing_tasks_is_refused(tmp_path: Path) -> None:
    d = _write_release(tmp_path, "9.9.9", _valid_document(phase="CLOSURE"))
    (d / "TASKS.md").unlink()

    assert _codes(validate_release_tree(tmp_path)) == ["RELEASE-TREE-TRIO"]


def test_definition_release_with_spec_only_is_clean(tmp_path: Path) -> None:
    """The state `release new` leaves (SPEC + _RELEASE.json, no PLAN/TASKS yet) and the
    state `rc-archive` leaves (no trio at all, DEFINITION) are both legitimate: the next
    candidate's trio is authored during DEFINITION. The trio rule is phase-scoped in its
    ONE home rather than each verb growing an exemption — the same structural mistake
    bug ``rc-archive-discovery-state-rejected-by-doctor`` already cost once."""
    d = _write_release(tmp_path, "9.9.9", _valid_document(phase="DEFINITION"))
    (d / "PLAN.md").unlink()
    (d / "TASKS.md").unlink()

    assert validate_release_tree(tmp_path) == []


def test_definition_release_without_any_trio_artifact_is_clean(tmp_path: Path) -> None:
    _write_release(tmp_path, "9.9.9", _valid_document(phase="DEFINITION"), trio=False)

    assert validate_release_tree(tmp_path) == []


def test_release_dir_without_state_document_is_refused(tmp_path: Path) -> None:
    d = tmp_path / "releases" / "9.9.9"
    d.mkdir(parents=True)
    (d / "SPEC.md").write_text("x\n", encoding="utf-8")
    (d / "PLAN.md").write_text("x\n", encoding="utf-8")
    (d / "TASKS.md").write_text("x\n", encoding="utf-8")

    issues = validate_release_tree(tmp_path)
    assert _codes(issues) == ["RELEASE-TREE-STATE-MISSING"]
    assert issues[0].path == "releases/9.9.9"


def test_the_histo_file_is_not_a_release_dir(tmp_path: Path) -> None:
    archive = tmp_path / "releases" / "_archive"
    archive.mkdir(parents=True)
    (archive / "releases_histo.jsonl").write_text("", encoding="utf-8")

    assert validate_release_tree(tmp_path) == []


def _archived(release: str, **overrides: Any) -> dict[str, Any]:
    doc = _valid_document(
        release=release,
        phase="ARCHIVED",
        rc=1,
        implemented={"sha": "b" * 40, "rc": 1, "ts": "2026-09-01T12:00:00Z"},
        shipped={"sha": "c" * 40, "pr": 7, "ts": "2026-09-02T00:00:00Z"},
    )
    doc.update(overrides)
    return doc


def test_archived_release_at_or_above_the_live_one_is_refused(tmp_path: Path) -> None:
    """The archive holds published versions only (operator ruling 2026-09-14, ADR 0014):
    the live release is last-published + 1 patch, so nothing at or above it shipped."""
    _write_release(tmp_path, "0.4.7", _valid_document(release="0.4.7"), trio=False)
    _write_release(tmp_path, "_archive/0.5.0", _archived("0.5.0"))
    _write_release(tmp_path, "_archive/0.4.6", _archived("0.4.6"))
    issues = validate_release_tree(tmp_path)
    assert _codes(issues) == ["RELEASE-TREE-ARCHIVE-ID"], issues
    assert "scripts/release.py fold 0.5.0 --into" in issues[0].message


def test_archived_release_without_a_publication_is_refused(tmp_path: Path) -> None:
    _write_release(tmp_path, "0.4.7", _valid_document(release="0.4.7"), trio=False)
    _write_release(tmp_path, "_archive/0.4.5", _archived("0.4.5", shipped=None))
    issues = validate_release_tree(tmp_path)
    assert _codes(issues) == ["RELEASE-TREE-ARCHIVE-UNSHIPPED"], issues
    assert "scripts/release.py fold 0.4.5 --into" in issues[0].message


def test_a_published_archived_release_below_the_live_one_is_clean(tmp_path: Path) -> None:
    _write_release(tmp_path, "0.4.7", _valid_document(release="0.4.7"), trio=False)
    _write_release(tmp_path, "_archive/0.4.6", _archived("0.4.6"))
    assert validate_release_tree(tmp_path) == []
