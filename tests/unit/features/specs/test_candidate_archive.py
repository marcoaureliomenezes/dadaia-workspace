"""Release 0.4.6 candidate 1, FR4 (ADR 0008) — ``archive_candidate``: the deterministic
mechanics behind ``dadaia release rc-archive``. One deep verb: validates candidate
closure, moves the root trio to ``rc-N/``, bumps the archived-candidate counter, sets
phase DISCOVERY, always writes the canonical ``_RELEASE.json`` name.

Intent: CONTRACT (the promote-or-continue gate's "continue" mechanics). Size: SMALL.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.candidate import CandidateArchiveError, archive_candidate


def _live_release(
    specs: Path,
    version: str = "1.0.0",
    *,
    phase: str = "CLOSURE",
    tasks: str = "- [x] T-1 done\n",
    legacy_name: bool = False,
    rc: int | None = None,
) -> Path:
    rdir = specs / "releases" / version
    rdir.mkdir(parents=True)
    (rdir / "SPEC.md").write_text("# SPEC\n\n**Status:** Aprovado\n", encoding="utf-8")
    (rdir / "PLAN.md").write_text("# PLAN\n\n**Status:** Aprovado\n", encoding="utf-8")
    (rdir / "TASKS.md").write_text("# TASKS\n\n**Status:** Aprovado\n\n" + tasks, encoding="utf-8")
    state = {
        "schema": "release-state-v1",
        "release": version,
        "phase": phase,
        "rc": rc,
        "defined": None,
        "implemented": None,
        "shipped": None,
        "audited": None,
        "log": [],
    }
    name = "RELEASE.json" if legacy_name else "_RELEASE.json"
    (rdir / name).write_text(json.dumps(state), encoding="utf-8")
    return rdir


def test_archive_moves_trio_to_rc1_and_bumps_counter(tmp_path: Path) -> None:
    rdir = _live_release(tmp_path)
    result = archive_candidate(tmp_path)
    assert result.rc == 1 and result.release == "1.0.0"
    assert (rdir / "rc-1" / "SPEC.md").is_file()
    assert (rdir / "rc-1" / "PLAN.md").is_file()
    assert (rdir / "rc-1" / "TASKS.md").is_file()
    assert not (rdir / "SPEC.md").exists()
    state = json.loads((rdir / "_RELEASE.json").read_text(encoding="utf-8"))
    assert state["rc"] == 1 and state["phase"] == "DISCOVERY"
    assert any("rc-1" in e.get("text", "") for e in state["log"])


def test_archive_numbers_next_candidate_after_existing(tmp_path: Path) -> None:
    rdir = _live_release(tmp_path)
    (rdir / "rc-1").mkdir()
    (rdir / "rc-1" / "SPEC.md").write_text("old", encoding="utf-8")
    result = archive_candidate(tmp_path)
    assert result.rc == 2
    assert (rdir / "rc-2" / "TASKS.md").is_file()


def test_archive_renames_legacy_state_file_on_write(tmp_path: Path) -> None:
    rdir = _live_release(tmp_path, legacy_name=True)
    archive_candidate(tmp_path)
    assert (rdir / "_RELEASE.json").is_file()
    assert not (rdir / "RELEASE.json").exists()


def test_archive_refuses_open_tasks(tmp_path: Path) -> None:
    _live_release(tmp_path, tasks="- [x] T-1 done\n- [ ] T-2 open\n")
    with pytest.raises(CandidateArchiveError, match=r"\[ \]|open"):
        archive_candidate(tmp_path)


def test_archive_refuses_in_progress_tasks(tmp_path: Path) -> None:
    _live_release(tmp_path, tasks="- [-] T-1 reserved\n")
    with pytest.raises(CandidateArchiveError):
        archive_candidate(tmp_path)


def test_archive_refuses_wrong_phase(tmp_path: Path) -> None:
    _live_release(tmp_path, phase="IMPLEMENTATION")
    with pytest.raises(CandidateArchiveError, match="CLOSURE"):
        archive_candidate(tmp_path)


def test_archive_refuses_without_live_release(tmp_path: Path) -> None:
    (tmp_path / "releases").mkdir()
    with pytest.raises(CandidateArchiveError, match="live release"):
        archive_candidate(tmp_path)


def test_doctor_accepts_the_between_candidates_discovery_state(tmp_path: Path) -> None:
    """Bug rc-archive-discovery-state-rejected-by-doctor: the state ``rc-archive``
    legally produces (trio in ``rc-N/``, root empty, phase DISCOVERY) must be
    doctor-clean — the verb and the doctor may never disagree about it."""
    from dadaia_workspace.features.specs.doctor import SpecsDoctor

    specs = tmp_path
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    _live_release(specs)
    archive_candidate(specs)

    issues = [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-004"]
    assert issues == [], [i.description for i in issues]
