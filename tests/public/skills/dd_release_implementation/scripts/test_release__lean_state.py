"""Acceptance tests for the jobs-and-tasks release state. Size: SMALL."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.skill_scripts import stage_skill_scripts

_TS = "2026-10-08T12:00:00Z"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    for skill in ("dd-spec-navigator", "dd-gitflow-default", "dd-bug-resolution"):
        stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")
    return (
        stage_skill_scripts(
            "dd-release-implementation",
            tmp_path / "skills" / "dd-release-implementation" / "scripts",
        )
        / "release.py"
    )


def _run(script: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *argv], capture_output=True, text=True, check=False
    )


def _specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    archive = specs / "releases" / "_archive"
    archive.mkdir(parents=True)
    archive.joinpath("releases_histo.jsonl").write_text("", encoding="utf-8")
    return specs


def _entry(kind: str, text: str, **extra: object) -> dict[str, object]:
    return {"ts": _TS, "agent": "test", "kind": kind, "text": text, **extra}


def _write_release(
    specs: Path,
    *,
    phase: str = "IMPLEMENTATION",
    log: list[dict[str, object]] | None = None,
    overlap: bool = False,
) -> Path:
    release = specs / "releases" / "0.5.0"
    candidate = release / "rc-1"
    tasks = candidate / "tasks"
    tasks.mkdir(parents=True)
    candidate.joinpath("SPEC.md").write_text(
        "# SPEC\n\n**Status:** Approved\n**Origin:** operator-demand\n\n"
        "## Bug window review\n\n## 1. Problem\n",
        encoding="utf-8",
    )
    second_path = "src/a.py" if overlap else "src/b.py"
    candidate.joinpath("PLAN.md").write_text(
        "# PLAN\n\n**Status:** Approved\n\n## As-is review\n\n"
        "| unit | today | bugs | verdict | why |\n|---|---|---|---|---|\n"
        "| release | heavy | 0 | REBUILD | lean |\n\n"
        "## DAG\n\n| job | waits on | wave | `W:` |\n|---|---|---|---|\n"
        "| Job 1 | — | 1 | `src/a.py` |\n"
        f"| Job 2 | — | 1 | `{second_path}` |\n",
        encoding="utf-8",
    )
    tasks.joinpath("job1.md").write_text(
        "# Job 1\n\n| task | AC | `W:` | outcome |\n|---|---|---|---|\n"
        "| J1.T1 | AC3.3 | `src/a.py` | owner |\n",
        encoding="utf-8",
    )
    tasks.joinpath("job2.md").write_text(
        "# Job 2\n\n| task | AC | `W:` | outcome |\n|---|---|---|---|\n"
        f"| J2.T1 | AC3.4 | `{second_path}` | owner |\n",
        encoding="utf-8",
    )
    state = {
        "schema": "release-state-v1",
        "release": "0.5.0",
        "phase": phase,
        "defined": {"sha": "1111111", "ts": "2026-10-08T10:00:00Z"},
        "implemented": (
            {"sha": "2222222", "ts": "2026-10-08T11:00:00Z"} if phase == "CLOSURE" else None
        ),
        "shipped": None,
        "log": log or [],
    }
    release.joinpath("_RELEASE.json").write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )
    return release


def test_check_accepts_lean_jobs_and_refuses_same_wave_write_overlap(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    _write_release(specs)
    clean = _run(script, "check", "--specs", str(specs), "--json")
    assert (clean.returncode, json.loads(clean.stdout)) == (0, [])

    overlapping = _specs(tmp_path / "overlap")
    _write_release(overlapping, overlap=True)
    refused = _run(script, "check", "--specs", str(overlapping), "--json")
    messages = [row["message"] for row in json.loads(refused.stdout)]
    assert refused.returncode == 1
    assert messages == ["PLAN.md DAG wave 1: two jobs write src/a.py — `W:` sets overlap"]


def test_new_spec_uses_the_seven_approved_default_sections(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    created = _run(script, "new", "0.6.0", "--specs", str(specs))
    assert created.returncode == 0, created.stderr
    headings = [
        line
        for line in specs.joinpath("releases/0.6.0/rc-1/SPEC.md").read_text("utf-8").splitlines()
        if line.startswith("## ")
    ]
    assert headings == [
        "## Bug window review",
        "## 1. Problem",
        "## 2. Measurable Goals",
        "## 3. Non-goals",
        "## 4. Requirements",
        "## 5. Constraints and risks",
        "## 6. Open questions",
    ]


def test_check_reads_legacy_log_history_but_rejects_a_new_legacy_kind(
    script: Path, tmp_path: Path
) -> None:
    allowed = [
        _entry("size", "legacy size record"),
        _entry("note", "Candidate born on 0.5.0"),
        _entry(
            "milestone",
            "Candidate implemented",
            candidate="rc-1",
            milestone="implemented",
            sha="2222222",
        ),
        _entry("summary", "delivered: lean release; carried: none; backlog exits: none"),
        _entry(
            "memory",
            "memory reconciled",
            since="1111111",
            until="2222222",
            reviewed=[],
            changed=[],
        ),
    ]
    specs = _specs(tmp_path)
    release = _write_release(specs, phase="CLOSURE", log=allowed)
    assert _run(script, "check", "--specs", str(specs)).returncode == 0

    state_path = release / "_RELEASE.json"
    state = json.loads(state_path.read_text("utf-8"))
    state["log"].append(_entry("reviews", "new legacy-shaped record"))
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    refused = _run(script, "check", "--specs", str(specs), "--json")
    assert refused.returncode == 1
    assert "reviews" in json.loads(refused.stdout)[0]["message"]


def test_memory_is_a_closure_only_log_entry(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _write_release(
        specs,
        log=[
            _entry("note", "Candidate born on 0.5.0"),
            _entry(
                "memory",
                "memory reconciled",
                since="1111111",
                until="2222222",
                reviewed=[],
                changed=[],
            ),
        ],
    )
    refused = _run(script, "check", "--specs", str(specs), "--json")
    assert refused.returncode == 1
    assert "memory" in json.loads(refused.stdout)[0]["message"]


def test_ship_requires_each_open_bug_flag_and_its_verbatim_authorization_note(
    script: Path, tmp_path: Path
) -> None:
    authorization = 'Operator authorization verbatim: "carry a-bug open"'
    log = [
        _entry("note", "Candidate born on 0.5.0"),
        _entry("note", authorization),
        _entry("summary", "delivered: lean state; carried: a-bug; backlog exits: none"),
        _entry(
            "memory",
            "memory reconciled",
            since="1111111",
            until="2222222",
            reviewed=[],
            changed=[],
        ),
    ]
    specs = _specs(tmp_path)
    _write_release(specs, phase="CLOSURE", log=log)
    bugs = specs / "bugs" / "BUGS.jsonl"
    bugs.parent.mkdir()
    bugs.write_text(
        json.dumps(
            {
                "id": "a-bug",
                "status": "open",
                "found_in": {"release": "0.5.0", "rc": "rc-1"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    refused = _run(script, "ship", "--sha", "3333333", "--specs", str(specs))
    assert refused.returncode == 1
    assert "a-bug" in refused.stderr

    shipped = _run(
        script,
        "ship",
        "--sha",
        "3333333",
        "--allow-open",
        "a-bug",
        "--specs",
        str(specs),
    )
    assert shipped.returncode == 0, shipped.stderr
    assert json.loads(bugs.read_text("utf-8"))["status"] == "open"
    archived = json.loads(
        specs.joinpath("releases/_archive/0.5.0/_RELEASE.json").read_text("utf-8")
    )
    assert authorization in [entry["text"] for entry in archived["log"]]


def test_closure_check_needs_the_memory_entry_but_not_git(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _write_release(
        specs,
        phase="CLOSURE",
        log=[
            _entry("note", "Candidate born on 0.5.0"),
            _entry(
                "memory",
                "memory reconciled",
                since="1111111",
                until="2222222",
                reviewed=[],
                changed=[],
            ),
        ],
    )
    checked = subprocess.run(
        [sys.executable, str(script), "check", "--specs", str(specs), "--json"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PATH": ""},
    )
    assert (checked.returncode, json.loads(checked.stdout)) == (0, [])
