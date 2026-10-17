"""Acceptance tests for the jobs-and-tasks release state. Size: SMALL."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.fixtures.harness_env import suite_env
from tests.helpers.oslib import read_text, replace, run, write_text
from tests.helpers.skill_scripts import stage_skill_scripts

_TS = "2026-10-08T12:00:00Z"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    return (
        stage_skill_scripts(
            "dd-release-implementation",
            tmp_path / "skills" / "dd-release-implementation" / "scripts",
        )
        / "release.py"
    )


def _run(script: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(script), *argv], check=False)


def _specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    archive = specs / "releases" / "_archive"
    archive.mkdir(parents=True)
    write_text(archive.joinpath("releases_histo.jsonl"), "")
    return specs


def _entry(kind: str, text: str, **extra: object) -> dict[str, object]:
    return {"ts": _TS, "agent": "test", "kind": kind, "text": text, **extra}


def _milestones(phase: str) -> list[dict[str, object]]:
    """The milestones a state in *phase* has logged."""
    stamps = [("defined", "1111111", "10")] + (
        [("implemented", "2222222", "11")] if phase == "CLOSURE" else []
    )
    return [
        {"ts": f"2026-10-08T{hour}:00:00Z", "agent": "release.py", "kind": "milestone",
         "candidate": "rc-1", "milestone": name, "sha": sha, "text": f"Candidate {name} at {sha}."}
        for name, sha, hour in stamps
    ]  # fmt: skip


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
    write_text(
        candidate.joinpath("SPEC.md"),
        "# SPEC\n\n**Status:** Approved\n**Origin:** operator-demand\n\n"
        "## Bug window review\n\n## 1. Problem\n",
    )
    second_path = "src/a.py" if overlap else "src/b.py"
    write_text(
        candidate.joinpath("PLAN.md"),
        "# PLAN\n\n**Status:** Approved\n\n## As-is review\n\n"
        "| unit | today | bugs | verdict | why |\n|---|---|---|---|---|\n"
        "| release | heavy | 0 | REBUILD | lean |\n\n"
        "## DAG\n\n| job | waits on | wave | `W:` |\n|---|---|---|---|\n"
        "| Job 1 | — | 1 | `src/a.py` |\n"
        f"| Job 2 | — | 1 | `{second_path}` |\n",
    )
    write_text(
        tasks.joinpath("job1.md"),
        "# Job 1\n\n| task | AC | `W:` | outcome |\n|---|---|---|---|\n"
        "| J1.T1 | AC3.3 | `src/a.py` | owner |\n",
    )
    write_text(
        tasks.joinpath("job2.md"),
        "# Job 2\n\n| task | AC | `W:` | outcome |\n|---|---|---|---|\n"
        f"| J2.T1 | AC3.4 | `{second_path}` | owner |\n",
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
        "log": log or _milestones(phase),
    }
    write_text(release.joinpath("_RELEASE.json"), json.dumps(state, indent=2) + "\n")
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
        for line in read_text(specs.joinpath("releases/0.6.0/rc-1/SPEC.md")).splitlines()
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
    state = json.loads(read_text(state_path))
    state["log"].append(_entry("reviews", "new legacy-shaped record"))
    write_text(state_path, json.dumps(state, indent=2) + "\n")
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
    write_text(
        bugs,
        json.dumps(
            {
                "id": "a-bug",
                "status": "open",
            }
        )
        + "\n",
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
    assert json.loads(read_text(bugs))["status"] == "open"
    archived = json.loads(read_text(specs.joinpath("releases/_archive/0.5.0/_RELEASE.json")))
    assert authorization in [entry["text"] for entry in archived["log"]]


@pytest.mark.parametrize(
    ("log", "fix"),
    [
        pytest.param(
            [_entry("summary", "carried: a-bug; backlog exits: none")],
            "Operator action: authorize carrying a-bug",
            id="no-authorization-is-the-operators",
        ),
        pytest.param(
            [_entry("note", 'Operator authorization verbatim: "carry a-bug open"')],
            "Agent action: add a-bug to the carried field of the kind: summary entry",
            id="no-carry-is-the-agents",
        ),
    ],
)
def test_ship_names_who_clears_a_missing_authorization_or_carry(
    script: Path, tmp_path: Path, log: list[dict[str, object]], fix: str
) -> None:
    specs = _specs(tmp_path)
    memory = _entry("memory", "m", since="1111111", until="2222222", reviewed=[], changed=[])
    _write_release(specs, phase="CLOSURE", log=[*log, memory])
    (specs / "bugs").mkdir()
    write_text(specs / "bugs" / "BUGS.jsonl", json.dumps({"id": "a-bug", "status": "open"}) + "\n")
    refused = _run(
        script, "ship", "--sha", "3333333", "--allow-open", "a-bug", "--specs", str(specs)
    )
    assert refused.returncode == 1
    assert refused.stderr.splitlines()[-1] == f"fix: {fix}"


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
    checked = run(
        [sys.executable, str(script), "check", "--specs", str(specs), "--json"],
        check=False,
        env=suite_env(os.environ, Path.home(), overrides={"PATH": ""}),
    )
    assert (checked.returncode, json.loads(checked.stdout)) == (0, [])


@pytest.mark.parametrize(
    "live_candidate",
    [pytest.param("rc-2", id="older-candidate"), pytest.param("rc-1", id="other-release")],
)
def test_ship_refuses_every_open_bug_then_carries_each_authorized_id(
    script: Path,
    tmp_path: Path,
    live_candidate: str,
) -> None:
    authorization = 'Operator authorization verbatim: "carry a-bug open"'
    specs = _specs(tmp_path)
    release = _write_release(
        specs,
        phase="CLOSURE",
        log=[
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
        ],
    )
    if live_candidate == "rc-2":
        replace(release / "rc-1", release / live_candidate)
    bugs = specs / "bugs" / "BUGS.jsonl"
    bugs.parent.mkdir()
    write_text(bugs, json.dumps({"id": "a-bug", "status": "open"}) + "\n")
    state = release / "_RELEASE.json"
    histo = specs / "releases/_archive/releases_histo.jsonl"
    before = (state.read_bytes(), histo.read_bytes())

    refused = _run(script, "ship", "--sha", "3333333", "--specs", str(specs))

    assert refused.returncode == 1
    assert "a-bug" in refused.stderr
    assert release.is_dir()
    assert not specs.joinpath("releases/_archive/0.5.0").exists()
    assert (state.read_bytes(), histo.read_bytes()) == before

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
    assert json.loads(read_text(bugs))["status"] == "open"
    archived = json.loads(read_text(specs.joinpath("releases/_archive/0.5.0/_RELEASE.json")))
    assert authorization in [entry["text"] for entry in archived["log"]]


# --- one state reader, a drafted next candidate adopted, `origin` ---


def _jsonl_owner():
    return load_owner("dd-bug-resolution", "_jsonl")


def test_parse_object_returns_a_state_document() -> None:
    assert _jsonl_owner().parse_object('{"phase": "CLOSURE"}', "fix it") == {"phase": "CLOSURE"}


@pytest.mark.parametrize("text", ["", "{not json", "[1, 2]"], ids=["empty", "malformed", "list"])
def test_parse_object_refuses_with_the_callers_act(text: str) -> None:
    refusal = load_owner("dd-bug-resolution", "_refusal")
    owner = _jsonl_owner()
    with pytest.raises(owner.Unreadable) as raised:
        owner.parse_object(text, "restore _RELEASE.json from git")
    assert isinstance(raised.value, refusal.Refusal)
    assert raised.value.fix == "restore _RELEASE.json from git"


def _closed_with_draft(tmp_path: Path) -> tuple[Path, Path, bytes]:
    specs = _specs(tmp_path)
    release = _write_release(specs, phase="CLOSURE")
    draft = release / "rc-2" / "SPEC.md"
    draft.parent.mkdir()
    draft.write_bytes(b"# SPEC\n\n**Status:** Draft\n**Origin:** operator-demand\n")
    return specs, release, draft.read_bytes()


def test_new_at_closure_adopts_the_drafted_next_candidate(script: Path, tmp_path: Path) -> None:
    specs, release, draft = _closed_with_draft(tmp_path)
    born = _run(script, "new", "0.5.0", "--specs", str(specs))
    assert born.returncode == 0, born.stderr
    assert release.joinpath("rc-2/SPEC.md").read_bytes() == draft
    assert not release.joinpath("rc-3").exists()
    assert json.loads(read_text(release.joinpath("_RELEASE.json")))["phase"] == "DEFINITION"


def test_a_refused_birth_leaves_the_draft_in_place(script: Path, tmp_path: Path) -> None:
    specs, release, draft = _closed_with_draft(tmp_path)
    refused = _run(script, "new", "0.6.0", "--specs", str(specs))
    assert refused.returncode == 1
    assert release.joinpath("rc-2/SPEC.md").read_bytes() == draft
    assert not release.joinpath("rc-3").exists()


@pytest.mark.parametrize(
    ("line", "printed"),
    [
        ("operator-demand", ""),
        ("backlog:a-1, b-2; bugs:x-bug", "backlog a-1\nbacklog b-2\nbugs x-bug\n"),
        ("findings:f-1; backlog:a-1", "backlog a-1\nfindings f-1\n"),
    ],
)
def test_origin_prints_the_ids_by_kind(
    script: Path, tmp_path: Path, line: str, printed: str
) -> None:
    spec = tmp_path / "SPEC.md"
    write_text(spec, f"# SPEC\n\n**Origin:** {line}\n")
    shown = _run(script, "origin", str(spec))
    assert (shown.returncode, shown.stdout) == (0, printed)


def test_origin_refuses_a_malformed_line_with_one_fix_line(script: Path, tmp_path: Path) -> None:
    spec = tmp_path / "SPEC.md"
    write_text(spec, "# SPEC\n\n**Origin:** backlog:\n")
    refused = _run(script, "origin", str(spec))
    assert refused.returncode == 1
    assert refused.stdout == ""
    assert refused.stderr.startswith("[error] ")
    assert len([row for row in refused.stderr.splitlines() if row.startswith("fix:")]) == 1


def test_new_on_a_milestone_less_closure_state_creates_the_next_candidate(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    release = _write_release(specs, phase="CLOSURE", log=[_entry("note", "Release 0.5.0 born")])
    spec = release / "rc-1" / "SPEC.md"
    closed = spec.read_bytes()
    born = _run(script, "new", "0.5.0", "--specs", str(specs))
    assert born.returncode == 0, born.stderr
    assert str(release / "rc-2" / "SPEC.md") in born.stdout
    assert release.joinpath("rc-2/SPEC.md").is_file()
    assert spec.read_bytes() == closed


# --- one reader of the live candidate's closure summary ---


def _at(hour: int, kind: str, text: str, **extra: object) -> dict[str, object]:
    return {**_entry(kind, text, **extra), "ts": f"2026-10-08T{hour:02d}:00:00Z"}


def _stacked(
    tmp_path: Path, origin: str, log: list[dict[str, object]], bug_ids: tuple[str, ...] = ()
) -> Path:
    """A live candidate defined at 10:00 whose log holds a previous candidate's history first."""
    specs = _specs(tmp_path)
    release = _write_release(specs, phase="CLOSURE", log=log)
    spec = release / "rc-1" / "SPEC.md"
    write_text(spec, read_text(spec).replace("operator-demand", origin))
    (specs / "backlog").mkdir()
    write_text(specs / "backlog" / "BACKLOG.json", json.dumps({"active": [{"id": "x-1"}]}))
    (specs / "bugs").mkdir()
    write_text(
        specs / "bugs" / "BUGS.jsonl",
        "".join(json.dumps({"id": i, "status": "open"}) + "\n" for i in bug_ids),
    )
    return specs


def _origin_messages(script: Path, specs: Path) -> list[str]:
    checked = _run(script, "check", "--specs", str(specs), "--json")
    return [row["message"] for row in json.loads(checked.stdout)]


_PRIOR = "delivered: before; carried: {}; backlog exits: {}"
_BORN = _at(10, "note", "Candidate born on 0.5.0")
_MEMORY = _at(12, "memory", "m", since="1111111", until="2222222", reviewed=[], changed=[])


def test_origin_ids_found_only_in_the_previous_candidates_summary_are_untraced(
    script: Path, tmp_path: Path
) -> None:
    log = [_at(9, "summary", _PRIOR.format("none", "x-1")), _BORN, _MEMORY]
    specs = _stacked(tmp_path, "backlog:x-1", log)
    lines = _run(script, "check", "--specs", str(specs)).stdout.splitlines()
    at = next(n for n, line in enumerate(lines) if "Origin backlog:x-1" in line)
    assert lines[at].split(" ", 2)[1] == "info"
    assert lines[at].endswith("Origin backlog:x-1 untraced")
    assert not any(line.startswith("fix:") for line in lines[at + 1 :])


def test_a_previous_candidates_carry_does_not_satisfy_allow_open(
    script: Path, tmp_path: Path
) -> None:
    log = [
        _at(9, "summary", _PRIOR.format("a-bug", "none")),
        _BORN,
        _at(11, "note", 'Operator authorization verbatim: "carry a-bug open"'),
        _MEMORY,
    ]
    specs = _stacked(tmp_path, "operator-demand", log, ("a-bug",))
    refused = _run(
        script, "ship", "--sha", "3333333", "--allow-open", "a-bug", "--specs", str(specs)
    )
    assert refused.returncode == 1
    assert refused.stderr.splitlines()[-1] == (
        "fix: Agent action: add a-bug to the carried field of the kind: summary entry"
    )


@pytest.mark.parametrize("word", ["delivered", "carried", "backlog", "exits", "none"])
def test_a_bug_id_equal_to_a_grammar_word_is_not_traced_by_the_summary_label(
    script: Path, tmp_path: Path, word: str
) -> None:
    log = [
        _BORN,
        _at(11, "summary", "delivered: lean; carried: none; backlog exits: none"),
        _MEMORY,
    ]
    specs = _stacked(tmp_path, f"bugs:{word}", log, (word,))
    assert f"Origin bugs:{word} untraced" in _origin_messages(script, specs)
