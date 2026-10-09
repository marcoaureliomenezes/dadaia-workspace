"""AC2.1–AC2.6, AC1.9 (release 0.5.0 candidate 2, ADR 0041 `measured_by`);
AC5.2, AC5.3 (release 0.5.0 candidate 4, the Authorities table); AC1.17(3) (ADR 0150, the
pinned pair resolving the live candidate); AC3.2 (candidate 7, ADR 0161: the one Origin
parser and the trace, re-homed from SPEC-DOC-048).

`release.py phase IMPLEMENTATION` admits a candidate only when PLAN.md carries the As-is
review table — structure only — and the skeleton `dd-release-definition` teaches passes
it, so the teaching and the gate cannot drift. Size: SMALL.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core import gitflow
from dadaia_workspace.core.release_state import CANDIDATE_RE
from tests.helpers.skill_scripts import stage_skill_scripts

_REPO_ROOT = Path(__file__).resolve().parents[5]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"
_SKILL = _PUBLIC / "skills" / "dd-release-definition" / "SKILL.md"
_SCRIPTS = _PUBLIC / "skills" / "dd-release-implementation" / "scripts"
_GOOD = "## 1. As-is review\n\n## 2. Strategy\n"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    stage_skill_scripts("dd-spec-navigator", tmp_path / "skills" / "dd-spec-navigator" / "scripts")
    return (
        stage_skill_scripts(
            "dd-release-implementation",
            tmp_path / "skills" / "dd-release-implementation" / "scripts",
        )
        / "release.py"
    )


def _specs(tmp_path: Path, plan: str, *, plan_status: str = "Approved") -> Path:
    specs = tmp_path / "specs"
    release = specs / "releases" / "0.5.0"
    (release / "rc-1").mkdir(parents=True)
    for name, body in (
        ("SPEC.md", "**Origin:** operator-demand\n\n## Bug window review\n"),
        ("PLAN.md", plan),
    ):
        status = plan_status if name == "PLAN.md" else "Approved"
        (release / "rc-1" / name).write_text(f"# {name}\n\n**Status:** {status}\n\n{body}", "utf-8")
    state: dict[str, object] = {"schema": "release-state-v1", "release": "0.5.0", "phase": "DEFINITION",
             "defined": None, "implemented": None, "shipped": None, "log": []}  # fmt: skip
    (release / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", "utf-8")
    return specs


def _phase(script: Path, specs: Path) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, str(script), "phase", "IMPLEMENTATION", "--sha", "abc1234"]
    return subprocess.run([*argv, "--specs", str(specs)], capture_output=True, text=True)


def _admits(script: Path, tmp_path: Path, plan: str) -> None:
    specs = _specs(tmp_path, plan)
    result = _phase(script, specs)
    assert result.returncode == 0, result.stderr
    state = json.loads((specs / "releases/0.5.0/_RELEASE.json").read_text("utf-8"))
    assert (state["phase"], state["defined"]["sha"]) == ("IMPLEMENTATION", "abc1234")
    assert len(state["log"]) == 1


def test_an_approved_spec_and_plan_enter_implementation_with_no_tasks_file(
    script: Path, tmp_path: Path
) -> None:
    """AC1.9 (ADR 0194): the job files carry the tasks; no `TASKS.md`, no PLAN table judge."""
    _admits(script, tmp_path, _dag(*_CHAIN[:2]))


def test_an_unapproved_plan_refuses(script: Path, tmp_path: Path) -> None:
    result = _phase(script, _specs(tmp_path, "no table\n", plan_status="Draft"))
    assert result.returncode != 0 and "'Draft'" in result.stderr


def test_new_writes_a_spec_stub_carrying_replaces(script: Path, tmp_path: Path) -> None:
    """AC1.9 — the stub asks for Replaces between Scope and Out of scope; no PLAN born."""
    specs = tmp_path / "specs"
    (specs / "releases").mkdir(parents=True)
    argv = [sys.executable, str(script), "new", "0.9.0", "--specs", str(specs)]
    assert subprocess.run(argv, capture_output=True, text=True).returncode == 0
    stub = (specs / "releases/0.9.0/rc-1/SPEC.md").read_text("utf-8")
    headings = re.findall(r"^## \d+\. (.+)$", stub, re.MULTILINE)
    assert headings.index("Scope") + 1 == headings.index("Replaces")
    assert headings.index("Replaces") + 1 == headings.index("Out of scope")
    assert not (specs / "releases/0.9.0/rc-1/PLAN.md").exists()


def test_the_pinned_pair_resolves_the_same_live_candidate(tmp_path: Path) -> None:
    """AC1.17(3): one grammar (`rc-<N>`, N from 1, no leading zero); the package and the
    scripts pick the same highest `rc-<N>/` directory, and birth the next one past a stray
    `rc-<N>` file; none without a candidate."""
    sys.path.insert(0, str(_SCRIPTS))
    import _release_schema as twin
    import _release_store

    assert twin.CANDIDATE_RE.pattern == CANDIDATE_RE.pattern
    release = tmp_path / "releases" / "1.0.0"
    release.mkdir(parents=True)
    (release / "_RELEASE.json").write_text('{"phase": "DEFINITION"}', encoding="utf-8")
    pair = (gitflow.resolve_live_candidate, lambda s: _release_store.live_release(s).candidate)
    assert [resolve(tmp_path) for resolve in pair] == [None, None]
    for name in ("rc-2", "rc-10", "rc-9", "rc-01", "rc-0", "notes"):
        (release / name).mkdir()
    (release / "rc-11").write_text("", encoding="utf-8")
    assert [resolve(tmp_path) for resolve in pair] == [release / "rc-10"] * 2
    assert gitflow.next_candidate(release) == twin.next_candidate(release) == release / "rc-12"


# --- the Origin line (ADR 0161; SPEC-DOC-048's cases re-homed by name) ---------------


def _origin_rows(script: Path, specs: Path) -> list[dict[str, str]]:
    done = subprocess.run([sys.executable, str(script), "check", "--json", "--specs", str(specs)],
                          capture_output=True, text=True)  # fmt: skip
    return [f for f in json.loads(done.stdout) if "Origin" in f["message"]]


def _check(script: Path, specs: Path) -> list[str]:
    return [f["message"] for f in _origin_rows(script, specs) if f["verdict"] == "error"]


def _seed_ledgers(specs: Path, *, log: list[dict[str, object]] | None = None) -> None:
    def jsonl(rel: str, *records: dict[str, object]) -> None:
        (specs / rel).parent.mkdir(parents=True, exist_ok=True)
        (specs / rel).write_text("".join(json.dumps(r) + "\n" for r in records), "utf-8")

    active = {"schema": "backlog-v1", "active": [{"id": "a-real-entry"}]}
    jsonl("backlog/BACKLOG.json", active)
    jsonl("backlog/_archive/backlog_histo.jsonl",
          {"id": "a-shipped-entry", "disposition": "delivered", "release": "0.5.0"},
          {"id": "sent-to-a-bug", "disposition": "to-bug", "reason": "turned-down"})  # fmt: skip
    jsonl("bugs/BUGS.jsonl", {"id": "still-broken", "status": "open"},
          {"id": "already-fixed", "status": "resolved"},
          {"id": "half-written", "severity": "BLOCKER"}, {"id": "turned-down", "status": "rejected"})  # fmt: skip
    jsonl("audits/20260930-x/FINDINGS.jsonl", {"id": "20260930-x-F001", "release": "0.5.0"})
    if log is not None:
        state = specs / "releases/0.5.0/_RELEASE.json"
        state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "log": log}), "utf-8")


@pytest.mark.parametrize(
    ("origin", "needles"),
    [
        pytest.param("", ["no `**Origin:**` line"], id="no-origin-line"),
        pytest.param("**Origin:** backlog:a-real-entry,a-ghost", ["backlog:a-ghost"],
                     id="unknown-backlog-id"),
        pytest.param("**Origin:** backlog:a-shipped-entry", [], id="backlog-id-in-histo-only"),
        pytest.param("**Origin:** bugs:still-broken,already-fixed,half-written", [],
                     id="B4-bug-id-any-status-or-schema"),
        pytest.param("**Origin:** bugs:still-broken,a-ghost", ["bugs:a-ghost"], id="unknown-bug-id"),
        pytest.param("**Origin:** because I felt like it", ["not canonical"],
                     id="non-canonical-value"),
        pytest.param("**Origin:** backlog:a-shipped-entry; bugs:already-fixed; "
                     "findings:20260930-x-F001", [], id="three-clauses-traced"),
        pytest.param("**Origin:** bugs:a; bugs:b", ["not canonical"], id="a-kind-twice"),
        pytest.param("**Origin:** findings:20260930-x-F009", ["findings:20260930-x-F009"],
                     id="unknown-finding-id"),
        pytest.param("**Origin:** backlog:sent-to-a-bug", ["backlog:sent-to-a-bug", "rejected"],
                     id="a-to-bug-target-later-rejected"),
    ],
)  # fmt: skip
def test_spec_origin(script: Path, tmp_path: Path, origin: str, needles: list[str]) -> None:
    """sa-spec-doc-033-duplicates-bugs-check#B4: an Origin id resolves whatever its record's
    status or schema; a finding names only the unresolved ids."""
    specs = _specs(tmp_path, _GOOD)
    _seed_ledgers(specs)
    (specs / "releases/0.5.0/rc-1/SPEC.md").write_text(f"**Status:** Approved\n{origin}\n", "utf-8")

    messages = _check(script, specs)

    assert len(messages) == len(needles[:1]), messages
    assert all(n in messages[0] for n in needles)
    assert "a-real-entry" not in "".join(messages) and "still-broken" not in "".join(messages)


def test_origin_trace_reads_the_closure_summary_instead_of_derived_ledger_fields(
    script: Path, tmp_path: Path
) -> None:
    """AC5.1: the summary is the closure fact for delivered, carried and backlog exits;
    Origin tracing does not reconstruct those facts from bug/backlog record fields."""
    specs = _specs(tmp_path, _GOOD)
    state = specs / "releases/0.5.0/_RELEASE.json"
    (specs / "releases/0.5.0/rc-1/SPEC.md").write_text(
        "# S\n\n**Status:** Approved\n**Origin:** backlog:a-real-entry; bugs:still-broken,already-fixed\n"
        "\n## Bug window review\n", "utf-8")  # fmt: skip
    summary = {
        "ts": "2026-01-02T00:00:00Z",
        "agent": "closer",
        "kind": "summary",
        "text": "delivered: bugs:already-fixed; carried: bugs:still-broken; backlog exits: a-real-entry",
    }
    _seed_ledgers(specs, log=[summary])
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "phase": "CLOSURE"}))

    rows = _origin_rows(script, specs)
    assert [(row["message"], row["verdict"]) for row in rows] == [
        ("Origin backlog:a-real-entry traced", "info"),
        ("Origin bugs:still-broken traced", "info"),
        ("Origin bugs:already-fixed traced", "info"),
    ]


def test_a_backlog_exit_rejected_by_disposition_traces(script: Path, tmp_path: Path) -> None:
    """release-check-reads-status-of-backlog-exits: `backlog.py exit --disposition rejected`
    writes `disposition` and no `status`; the carried id traces."""
    specs = _specs(tmp_path, _GOOD)
    _seed_ledgers(specs)
    with (specs / "backlog/_archive/backlog_histo.jsonl").open("a") as histo:
        histo.write(json.dumps({"id": "declined", "disposition": "rejected"}) + "\n")
    (specs / "releases/0.5.0/rc-1/SPEC.md").write_text("**Origin:** backlog:declined\n", "utf-8")

    listed = subprocess.run([sys.executable, str(script), "check", "--specs", str(specs)],
                            capture_output=True, text=True)  # fmt: skip

    assert [ln.split(" ", 3)[3] for ln in listed.stdout.splitlines() if " info " in ln] == [
        "Origin backlog:declined traced"
    ]


def test_a_stacked_candidate_in_definition_lists_its_carried_ids(
    script: Path, tmp_path: Path
) -> None:
    """AC5.1: `new` keeps the closed candidate's summary; a stacked candidate in
    DEFINITION has no closure summary of its own yet."""
    specs = _specs(tmp_path, _GOOD)
    state = specs / "releases/0.5.0/_RELEASE.json"
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")),
                                 "defined": {"sha": "abc1234", "ts": "2026-01-01T00:00:00Z"},
                                 "implemented": {"sha": "abc1235", "ts": "2026-01-02T00:00:00Z"}}))  # fmt: skip
    _seed_ledgers(specs, log=[{"ts": "2026-01-03T00:00:00Z", "agent": "a", "kind": "summary",
                               "text": "delivered: none; carried: none; backlog exits: a-real-entry"}])  # fmt: skip
    (specs / "releases/0.5.0/rc-2").mkdir()
    (specs / "releases/0.5.0/rc-2/SPEC.md").write_text(
        "**Status:** Draft\n**Origin:** backlog:a-real-entry\n", "utf-8"
    )

    assert _check(script, specs) == []


def test_only_the_live_candidate_is_ranked(script: Path, tmp_path: Path) -> None:
    """ADR 0150 (3): the highest rc-<N>/ is ranked; a closed rc-1 is history."""
    specs = _specs(tmp_path, _GOOD)
    (specs / "releases/0.5.0/rc-2").mkdir()
    (specs / "releases/0.5.0/rc-2/SPEC.md").write_text("**Status:** Draft\n", "utf-8")

    [row] = _origin_rows(script, specs)

    assert row["path"].endswith("rc-2/SPEC.md") and "has no `**Origin:**`" in row["message"]


def test_this_repos_live_spec_origin_passes(script: Path) -> None:
    assert _check(script, _REPO_ROOT / "specs") == []


_JOB = (
    "# Job 2 — the bug window\n\n## Stage J2.S1 — RED\n\n"
    "- Contract: exit tests `tests/unit/test_x.py` strict xfail; envelope `tests/**`; ACs AC2.1\n"
    "- J2.S1.T1 — AC2.1 · `W:` `tests/unit/test_x.py` · owner `tests/unit/test_x.py`\n\n"
    "## Stage J2.S2 — fix\n\n"
    "- Contract: exit tests unit + integration; envelope `src/**`; ACs AC2.1\n"
    "- J2.S2.T1 — AC2.1 · `W:` `src/x.py` · owner `tests/unit/test_x.py`\n"
)

_JOB1 = (  # the rc-9 job1 file's shape: titled stages, prose contracts, AC ranges
    "# TASKS — 0.5.0 rc-9, Job 1 — the demolition\n\n## Stage J1.S1 — RED (tests only)\n\n"
    "- Contract: exit tests are each AC's acceptance test as a strict xfail; envelope `tests/**`.\n\n"
    "- J1.S1.T1 — AC1.1 · `W:` `tests/integration/test_ci_script.py` · owner same\n"
    "- J1.S1.T2 — AC1.2–AC1.5 · `W:` `tests/integration/test_worktree_new.py`, "
    "`tests/helpers/worktree_ws.py` · owner same\n\n"
    "## Stage J1.S2 — code and law\n\n"
    "- Contract: exit tests are J1.S1's, passing, plus unit + integration; ACs AC1.1–AC1.10.\n\n"
    "- J1.S2.T1 — AC1.1 · `W:` `scripts/ci.py` · owner `test_ci_script.py`\n"
)

_JOB_TABLE = (  # the rc-9 job files' task tables: the `W:` column holds each row's writes
    "## Stage J1.S1 — RED\n\n- Contract: x\n\n| id | AC | `W:` | owner |\n|---|---|---|---|\n"
    "| T1 | AC1 | `tests/unit/test_t.py` | same |\n"
)


@pytest.mark.parametrize(
    ("job", "needle"),
    [
        pytest.param(_JOB, None, id="valid"),
        pytest.param(_JOB1, None, id="rc9-job1-shape"),
        pytest.param(_JOB_TABLE, None, id="stage-1-table-tests"),
    ],
)  # fmt: skip
def test_check_judges_each_job_file(
    script: Path, tmp_path: Path, job: str, needle: str | None
) -> None:
    """AC1.10 (ADR 0194, 0196): a job file parses into stages; stage 1 writes tests only."""
    specs = _specs(tmp_path, _dag(*_CHAIN[:2]))
    (tasks := specs / "releases/0.5.0/rc-1/tasks").mkdir()
    (tasks / "j2.md").write_text(job, "utf-8")
    done = subprocess.run([sys.executable, str(script), "check", "--json", "--specs", str(specs)],
                          capture_output=True, text=True)  # fmt: skip
    messages = [f["message"] for f in json.loads(done.stdout) if "tasks/" in f["path"]]
    assert messages == ([needle] if needle else [])
    phase = _phase(script, specs)  # the transition judges the same job file alike
    assert (phase.returncode, needle is None or needle in phase.stderr) == (int(bool(needle)), True)


@pytest.mark.parametrize(
    ("text", "bad"),
    [
        ("job: job1; start: 2026-10-05T12:00Z; end: 2026-10-05T18:00Z; wall: 360; "
         "ritual_wait: 20; dispatches: 4; job_gate_runs: 2", False),
        ("job: job1; start: 2026-10-05T12:00Z; end: 2026-10-05T18:00Z; wall: 360; "
         "ritual_wait: 20; dispatches: 4", True),
        ("job: job1; wall: 360; ritual_wait: 20; dispatches: 4", True),
        ("Merged PR #9 into develop.", False),  # a closure merge note, not a job's
    ],
    ids=["job-merge", "job-merge-without-job-gate-runs", "job-merge-without-start-end",
         "closure-merge"],
)  # fmt: skip
def test_check_validates_a_jobs_merge_entry(
    script: Path, tmp_path: Path, text: str, bad: bool
) -> None:
    """AC1.7: a job's `kind: merge` entry carries its six measurements (start..job_gate_runs)."""
    specs = _specs(tmp_path, _GOOD)
    state = specs / "releases/0.5.0/_RELEASE.json"
    entry = {"ts": "2026-10-05T18:00:00Z", "agent": "j", "kind": "merge", "text": text}
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "log": [entry]}))
    done = subprocess.run([sys.executable, str(script), "check", "--json", "--specs", str(specs)],
                          capture_output=True, text=True)  # fmt: skip
    hits = [f for f in json.loads(done.stdout) if "kind merge" in f["message"]]
    assert len(hits) == int(bad)


def _dag(*rows: tuple[str, str]) -> str:
    """A PLAN in the rc-9 shape: `## DAG` table (job | waits on | why), then `### Hot files`."""
    table = "".join(f"| {job} | {waits} | x |\n" for job, waits in rows)
    return (f"{_GOOD}\n## DAG\n\n| job | waits on | why |\n|---|---|---|\n{table}"
            "\n### Hot files\n\n- `scripts/ci.py`: Job 1, then Job 2.\n")  # fmt: skip


_CHAIN = [("Job 1", "—"), *((f"Job {n}", f"Job {n - 1}") for n in range(2, 9))]
_RECON = ("Reconciliation", "Jobs 1–8")


@pytest.mark.parametrize(
    ("plan", "job", "needle"),
    [
        pytest.param(_dag(*_CHAIN, _RECON), _JOB, None, id="valid-8-jobs-plus-reconciliation"),
        pytest.param(_dag(("Job 1", "Job 2"), ("Job 2", "Job 1")), _JOB, "cyclic",
                     id="cyclic-dag"),
        pytest.param(_dag(("Job 2", "—"), ("Job 3", "Job 2")), _JOB, "Job 1",
                     id="no-job-1"),
        pytest.param(_dag(*_CHAIN, ("Job 9", "Job 8"), _RECON), _JOB, "8 jobs",
                     id="nine-jobs"),
        pytest.param(_dag(*_CHAIN[:2]),
                     _JOB + "- J2.S2.T2 — AC2.1 · `W:` `src/x.py` · owner `tests/unit/test_x.py`\n",
                     "src/x.py", id="overlapping-w-in-a-stage"),
        pytest.param(_dag(*_CHAIN[:2]),
                     _JOB + "- J2.S2.T2 — AC2.1 · `W:` `pyproject.toml` · owner same\n"
                     "- J2.S2.T3 — AC2.1 · `W:` `pyproject.toml` · owner same\n",
                     "pyproject.toml", id="overlapping-root-file-in-a-stage"),
        pytest.param(_dag(), _JOB, "Job 1", id="empty-dag"),
    ],
)  # fmt: skip
def test_check_refuses_each_trio_row(
    script: Path, tmp_path: Path, plan: str, job: str, needle: str | None
) -> None:
    """AC4.2: one trio per refusal, one fix line each; the valid trio exits 0."""
    specs = _specs(tmp_path, plan)
    (tasks := specs / "releases/0.5.0/rc-1/tasks").mkdir()
    (tasks / "j2.md").write_text(job, "utf-8")
    done = subprocess.run([sys.executable, str(script), "check", "--json", "--specs", str(specs)],
                          capture_output=True, text=True)  # fmt: skip
    errors = [f for f in json.loads(done.stdout) if f["verdict"] == "error"]
    assert (done.returncode, len(errors)) == ((1, 1) if needle else (0, 0))
    for error in errors:
        assert needle in error["message"]
        assert error["fix"].startswith(("fix: ", "Operator action: ")) and "\n" not in error["fix"]


@pytest.mark.parametrize(
    ("plan", "needle"),
    [
        pytest.param(_dag(*_CHAIN[:2]).replace("## DAG", "## Jobs"), "DAG", id="no-dag"),
    ],
)  # fmt: skip
def test_phase_implementation_refuses_a_plan_without_a_dag(
    script: Path, tmp_path: Path, plan: str, needle: str
) -> None:
    """The PLAN carries one dependency DAG; its refusal has one fix line."""
    result = _phase(script, _specs(tmp_path, plan))
    fixes = [
        ln for ln in result.stderr.splitlines() if ln.startswith(("fix: ", "Operator action: "))
    ]
    assert (result.returncode, needle in result.stderr, len(fixes)) == (1, True, 1)


def test_phase_implementation_accepts_the_jobs_and_tasks_dialect(
    script: Path, tmp_path: Path
) -> None:
    plan = (
        f"{_GOOD}\n## DAG\n\n"
        "| job | waits on | wave | `W:` |\n"
        "|---|---|---|---|\n"
        "| Job 1 | — | 1 | `src/a.py`, `tests/test_a.py` |\n"
        "| Reconciliation | Job 1 | 2 | `specs/memory/product/a.md` |\n"
    )
    specs = _specs(tmp_path, plan)
    tasks = specs / "releases/0.5.0/rc-1/tasks"
    tasks.mkdir()
    tasks.joinpath("job1.md").write_text(
        "# Job 1\n\n"
        "| task | AC | `W:` | outcome |\n"
        "|---|---|---|---|\n"
        "| J1.T1 | AC2.1 | `tests/test_a.py` | RED |\n"
        "| J1.T2 | AC2.1 | `src/a.py` | GREEN |\n",
        encoding="utf-8",
    )

    result = _phase(script, specs)

    assert result.returncode == 0, result.stderr


def _current_plan(*rows: str) -> str:
    return f"{_GOOD}\n## DAG\n\n| job | waits on | wave | `W:` |\n|---|---|---|---|\n" + "".join(
        rows
    )


def _current_job(job: int, *writes: str) -> str:
    rows = "".join(
        f"| J{job}.T{number} | AC3.4 | `{path}` | owner |\n"
        for number, path in enumerate(writes, 1)
    )
    return f"# Job {job}\n\n| task | AC | `W:` | outcome |\n|---|---|---|---|\n{rows}"


def _phase_with_current_jobs(
    script: Path, tmp_path: Path, plan: str, jobs: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    specs = _specs(tmp_path, plan)
    tasks = specs / "releases/0.5.0/rc-1/tasks"
    tasks.mkdir()
    for name, body in jobs.items():
        tasks.joinpath(name).write_text(body, encoding="utf-8")
    return _phase(script, specs)


@pytest.mark.parametrize(
    ("plan", "jobs"),
    [
        pytest.param(
            _current_plan("| Job 1 | — | 1 | `src/second.py` |\n"),
            {
                "job1.md": _current_job(1, "src/first.py", "src/second.py").replace(
                    "|---|---|---|---|\n", "", 1
                )
            },
            id="job-table",
        ),
        pytest.param(
            _current_plan(
                "| Job 1 | — | 1 | `src/first.py` |\n",
                "| Job 2 | Job 1 | 2 | `src/second.py` |\n",
            ).replace("|---|---|---|---|\n", "", 1),
            {"job2.md": _current_job(2, "src/second.py")},
            id="plan-table",
        ),
    ],
)
def test_phase_implementation_refuses_a_current_authority_without_a_separator(
    script: Path, tmp_path: Path, plan: str, jobs: dict[str, str]
) -> None:
    result = _phase_with_current_jobs(script, tmp_path, plan, jobs)

    assert result.returncode == 1


@pytest.mark.parametrize(
    ("plan", "jobs"),
    [
        pytest.param(_current_plan(), {}, id="empty-dag"),
        pytest.param(
            _current_plan(
                "| Job 1 | — | 1 | `src/a.py` |\n",
                "| Job 2 | Job 1 | 2 | `src/b.py` |\n",
            ),
            {"job1.md": _current_job(1, "src/a.py")},
            id="missing-job-file",
        ),
        pytest.param(
            _current_plan("| Job 1 | — | 1 | `src/a.py` |\n"),
            {
                "job1.md": _current_job(1, "src/a.py"),
                "job2.md": _current_job(2, "src/b.py"),
            },
            id="extra-job-file",
        ),
        pytest.param(
            _current_plan(
                "| Job 1 | — | 1 | `src/a.py` |\n",
                "| Job 1 | — | 2 | `src/a.py` |\n",
            ),
            {"job1.md": _current_job(1, "src/a.py")},
            id="duplicate-job",
        ),
        pytest.param(
            _current_plan("| Job 1 | — | first | `src/a.py` |\n"),
            {"job1.md": _current_job(1, "src/a.py")},
            id="non-numeric-wave",
        ),
        pytest.param(
            _current_plan("| Job 1 | — | 1 | `src/a.py` |\n"),
            {"job1.md": _current_job(1, "src/a.py", "tests/test_a.py")},
            id="incomplete-write-set",
        ),
    ],
)
def test_phase_implementation_refuses_an_incomplete_current_job_union(
    script: Path, tmp_path: Path, plan: str, jobs: dict[str, str]
) -> None:
    result = _phase_with_current_jobs(script, tmp_path, plan, jobs)

    assert result.returncode == 1


def test_phase_implementation_accepts_each_current_jobs_exact_task_union(
    script: Path, tmp_path: Path
) -> None:
    result = _phase_with_current_jobs(
        script,
        tmp_path,
        _current_plan(
            "| Job 1 | — | 1 | `src/a.py`, `tests/test_a.py` |\n",
            "| Job 2 | Job 1 | 2 | `src/b.py` |\n",
        ),
        {
            "job1.md": _current_job(1, "src/a.py", "tests/test_a.py"),
            "job2.md": _current_job(2, "src/b.py"),
        },
    )

    assert result.returncode == 0, result.stderr


def test_phase_implementation_checks_same_wave_overlap_after_exact_task_unions(
    script: Path, tmp_path: Path
) -> None:
    result = _phase_with_current_jobs(
        script,
        tmp_path,
        _current_plan(
            "| Job 1 | — | 1 | `src/shared.py` |\n",
            "| Job 2 | — | 1 | `src/shared.py` |\n",
        ),
        {
            "job1.md": _current_job(1, "src/shared.py"),
            "job2.md": _current_job(2, "src/shared.py"),
        },
    )

    assert result.returncode == 1


def test_a_first_stage_may_write_tests_by_any_language_convention(
    script: Path, tmp_path: Path
) -> None:
    """No language is assumed: the repo's own gates judge a test file, so a first stage naming
    `pkg/x_test.go` passes `check` and `phase IMPLEMENTATION`."""
    specs = _specs(tmp_path, _dag(*_CHAIN[:2]))
    (tasks := specs / "releases/0.5.0/rc-1/tasks").mkdir()
    (tasks / "j2.md").write_text(
        _JOB_TABLE.replace("tests/unit/test_t.py", "pkg/x_test.go"), "utf-8"
    )
    done = subprocess.run([sys.executable, str(script), "check", "--json", "--specs", str(specs)],
                          capture_output=True, text=True)  # fmt: skip
    assert [f["message"] for f in json.loads(done.stdout) if "tasks/" in f["path"]] == []
    assert _phase(script, specs).returncode == 0
