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
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core import gitflow
from dadaia_workspace.core.release_state import CANDIDATE_RE
from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = pytest.mark.contract

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"
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
          {"id": "already-fixed", "status": "resolved", "resolved_release": "0.5.0"},
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
    status or schema; a finding names only the unresolved ids. A carried id whose record
    does not point back yet is listed, not a finding, before the dispositions entry."""
    specs = _specs(tmp_path, _GOOD)
    _seed_ledgers(specs)
    (specs / "releases/0.5.0/rc-1/SPEC.md").write_text(f"**Status:** Approved\n{origin}\n", "utf-8")

    messages = _check(script, specs)

    assert len(messages) == len(needles[:1]), messages
    assert all(n in messages[0] for n in needles)
    assert "a-real-entry" not in "".join(messages) and "still-broken" not in "".join(messages)


def test_a_missing_pointer_is_a_finding_once_the_candidate_logs_its_dispositions(
    script: Path, tmp_path: Path
) -> None:
    """AC3.2: a carried bug without `resolved_release` and a live entry with no exit are
    listed (with whether they point back) until the live candidate's `dispositions` entry
    exists; an older candidate's entry (before `defined.ts`) does not count. Once it does,
    each is an error on the real Origin line whose fix writes the pointer."""
    specs = _specs(tmp_path, _GOOD)
    entry = {"ts": "2026-01-02T00:00:00Z", "agent": "a", "kind": "dispositions", "text": "t"}
    state = specs / "releases/0.5.0/_RELEASE.json"
    defined = {"sha": "abc1234", "ts": "2026-01-01T00:00:00Z"}
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "phase": "CLOSURE",
                                 "defined": defined}))  # fmt: skip
    (specs / "releases/0.5.0/rc-1/SPEC.md").write_text(
        "# S\n\n**Status:** Approved\n**Origin:** backlog:a-real-entry; bugs:still-broken,already-fixed\n"
        "\n## Bug window review\n", "utf-8")  # fmt: skip
    _seed_ledgers(specs, log=[{**entry, "ts": "2025-12-31T00:00:00Z"}])
    assert _origin_rows(script, specs) == []  # --json, the doctor's contract: errors only
    listed = subprocess.run([sys.executable, str(script), "check", "--specs", str(specs)],
                            capture_output=True, text=True)  # fmt: skip
    assert [
        ln.split(" ", 3)[3] for ln in listed.stdout.splitlines() if " info " in ln
    ] == [  # fmt: skip
        "Origin backlog:a-real-entry untraced",
        "Origin bugs:still-broken untraced",
        "Origin bugs:already-fixed traced",
    ]

    _seed_ledgers(specs, log=[entry])

    errors = [f for f in _origin_rows(script, specs) if f["verdict"] == "error"]
    assert [(f["line"], f["message"]) for f in errors] == [
        (4, "Origin backlog:a-real-entry untraced"), (4, "Origin bugs:still-broken untraced")]  # fmt: skip
    assert " exit a-real-entry --disposition delivered --release 0.5.0 --specs " in errors[0]["fix"]
    assert errors[1]["fix"].startswith("Operator action: resolve bug still-broken in release 0.5.0")
    assert "<" not in errors[1]["fix"]  # ADR 0158: a bug's resolve needs evidence no row holds


def test_a_deferred_carried_bug_is_untraced_after_the_sweep(script: Path, tmp_path: Path) -> None:
    """Operator ruling 2026-10-01: a carried bug `deferred` at the closing sweep stays
    untraced, an error whose fix is the operator's act (resolve it here, or rule on scope)."""
    specs = _specs(tmp_path, _GOOD)
    state = specs / "releases/0.5.0/_RELEASE.json"
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "phase": "CLOSURE"}))
    _seed_ledgers(specs, log=[{"ts": "2026-01-02T00:00:00Z", "agent": "a", "kind": "dispositions",
                               "text": "t"}])  # fmt: skip
    with (specs / "bugs/BUGS.jsonl").open("a") as ledger:
        ledger.write(json.dumps({"id": "parked", "status": "deferred", "reason": "later"}) + "\n")
    (specs / "releases/0.5.0/rc-1/SPEC.md").write_text("**Origin:** bugs:parked\n", "utf-8")

    [row] = _origin_rows(script, specs)

    assert row["message"] == "Origin bugs:parked untraced"
    assert row["fix"].startswith("Operator action: resolve bug parked in release 0.5.0")


def test_a_carried_id_is_traced_through_its_owning_ledger_after_it_moves(
    script: Path, tmp_path: Path
) -> None:
    """AC3.2 (review F1, F5): `audit.py close` deletes the audit and leaves one histo record
    keyed by the audit id; `bugs.py archive` moves a record to the archive; `supersede`
    writes `superseded_by` — each carried id still traces, asked of the ledger owning it."""
    specs = _specs(tmp_path, _GOOD)
    state = specs / "releases/0.5.0/_RELEASE.json"
    log = [{"ts": "2026-01-02T00:00:00Z", "agent": "a", "kind": "dispositions", "text": "t"}]
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "phase": "CLOSURE",
                                 "defined": {"sha": "abc1234", "ts": "2026-01-01T00:00:00Z"}}))  # fmt: skip
    _seed_ledgers(specs, log=log)
    shutil.rmtree(specs / "audits/20260930-x")
    (specs / "audits/_archive").mkdir(parents=True)
    (specs / "audits/_archive/audits_histo.jsonl").write_text(
        json.dumps({"id": "20260930-x", "disposition": "resolved", "release": "0.5.0"}) + "\n"
    )
    (specs / "bugs/_archive").mkdir()
    (specs / "bugs/_archive/bugs_histo.jsonl").write_text(
        json.dumps({"id": "gone-fixed", "status": "resolved", "resolved_release": "0.5.0"}) + "\n"
    )
    with (specs / "bugs/BUGS.jsonl").open("a") as ledger:
        ledger.write(json.dumps({"id": "folded", "status": "superseded",
                                 "superseded_by": "already-fixed"}) + "\n")  # fmt: skip
    (specs / "releases/0.5.0/rc-1/SPEC.md").write_text(
        "**Status:** Approved\n**Origin:** bugs:gone-fixed,folded; findings:20260930-x-F001\n"
    )

    assert _check(script, specs) == []


def test_a_stacked_candidate_in_definition_lists_its_carried_ids(
    script: Path, tmp_path: Path
) -> None:
    """AC3.2 (review F2): `new` keeps the closed candidate's `defined` and its logged
    `dispositions`; the stacked candidate in DEFINITION has swept nothing yet."""
    specs = _specs(tmp_path, _GOOD)
    state = specs / "releases/0.5.0/_RELEASE.json"
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")),
                                 "defined": {"sha": "abc1234", "ts": "2026-01-01T00:00:00Z"},
                                 "implemented": {"sha": "abc1235", "ts": "2026-01-02T00:00:00Z"}}))  # fmt: skip
    _seed_ledgers(specs, log=[{"ts": "2026-01-03T00:00:00Z", "agent": "a", "kind": "dispositions",
                               "text": "rc-1 sweep"}])  # fmt: skip
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
    assert _check(script, Path(__file__).resolve().parents[2] / "specs") == []


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
        pytest.param(_JOB1.replace("`tests/helpers/worktree_ws.py`", "`scripts/ci.py`"),
                     "tasks/j2.md stage J1.S1 writes scripts/ci.py — stage 1 writes tests only",
                     id="rc9-job1-shape-stage-1-source"),
        pytest.param(_JOB_TABLE, None, id="stage-1-table-tests"),
        pytest.param(_JOB_TABLE.replace("`tests/unit/test_t.py`", "`scripts/ci.py`"),
                     "tasks/j2.md stage J1.S1 writes scripts/ci.py — stage 1 writes tests only",
                     id="stage-1-table-source"),
        pytest.param(_JOB.replace("`W:` `tests/unit/test_x.py`", "`W:` `src/y.py`"),
                     "tasks/j2.md stage J2.S1 writes src/y.py — stage 1 writes tests only",
                     id="stage-1-non-test"),
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
        pytest.param(_dag(*_CHAIN[:2]).replace("### Hot files", "### Notes"), "Hot files",
                     id="no-hot-files"),
    ],
)  # fmt: skip
def test_phase_implementation_refuses_a_plan_without_dag_or_hot_files(
    script: Path, tmp_path: Path, plan: str, needle: str
) -> None:
    """AC4.3: the PLAN carries `## DAG` and `### Hot files`; one fix line each."""
    result = _phase(script, _specs(tmp_path, plan))
    fixes = [
        ln for ln in result.stderr.splitlines() if ln.startswith(("fix: ", "Operator action: "))
    ]
    assert (result.returncode, needle in result.stderr, len(fixes)) == (1, True, 1)


# --- AC4.4: the bug balance block is a closure check ---------------------------------


def test_a_stale_balance_block_refuses_at_closure_and_passes_in_implementation(
    script: Path, tmp_path: Path
) -> None:
    """AC4.4: `QUALITY.md`'s `## Bugs` block that differs from its regeneration is one
    refusal in CLOSURE, its fix the regenerating command; IMPLEMENTATION lets it be."""
    stage_skill_scripts("dd-bug-resolution", tmp_path / "skills" / "dd-bug-resolution" / "scripts")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    specs = _specs(tmp_path, _GOOD)
    log = [{"ts": "2026-01-01T00:00:00Z", "agent": "a", "kind": "note", "text": "t"}]
    _seed_ledgers(specs, log=log)
    quality = specs / "memory" / "QUALITY.md"
    quality.parent.mkdir()
    quality.write_text("# Quality\n\n## Bugs\n\n```text\nstale\n```\n", "utf-8")
    state = specs / "releases/0.5.0/_RELEASE.json"

    def balance_rows(phase: str) -> list[dict[str, str]]:
        state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "phase": phase}))
        done = subprocess.run([sys.executable, str(script), "check", "--json", "--specs", str(specs)],
                              capture_output=True, text=True)  # fmt: skip
        assert done.stdout, done.stderr
        return [f for f in json.loads(done.stdout) if f["path"] == "memory/QUALITY.md"]

    assert balance_rows("IMPLEMENTATION") == []
    stale = balance_rows("CLOSURE")
    assert [r["verdict"] for r in stale] == ["error"]
    assert stale[0]["fix"].endswith(f" balance --write --specs {specs.as_posix()}")

    bugs = script.parents[2] / "dd-bug-resolution" / "scripts" / "bugs.py"
    written = subprocess.run([sys.executable, str(bugs), "balance", "--write", "--specs", str(specs)],
                             capture_output=True, text=True)  # fmt: skip
    assert written.returncode == 0, written.stderr
    assert "Bug balance from BUGS.jsonl: 4 records (4 live, 0 archived)." in quality.read_text(
        "utf-8"
    )
    assert balance_rows("CLOSURE") == []


def _balance_tree(
    tmp_path: Path, records: list[dict[str, object]], *, git: bool = True
) -> list[str]:
    """A one-release specs tree with *records* as its ledger and both skills staged beside it;
    returns the `bugs.py balance` argv."""
    for skill in ("dd-bug-resolution", "dd-release-implementation"):
        stage_skill_scripts(skill, tmp_path / "skills" / skill / "scripts")
    if git:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    specs = _specs(tmp_path, _GOOD)
    log = [{"ts": "2026-01-01T12:00:00Z", "agent": "a", "kind": "note", "text": "t"}]
    _seed_ledgers(specs, log=log)
    (specs / "bugs/BUGS.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    bugs = tmp_path / "skills" / "dd-bug-resolution" / "scripts" / "bugs.py"
    return [sys.executable, str(bugs), "balance", "--specs", str(specs)]


@pytest.mark.xfail(strict=True, reason="J4.S5 RED: the verb's edge catches nothing yet")
@pytest.mark.parametrize("git", [True, False], ids=["record-without-ts", "tree-without-git"])
def test_balance_refuses_an_unreadable_input_with_one_fix_line(tmp_path: Path, git: bool) -> None:
    """L6: a record with no `ts`, or a tree that is no git repo, is a refusal, not a traceback."""
    found = {"release": "0.5.0", "rc": "rc-1"}
    argv = _balance_tree(tmp_path, [{"id": "a", "surface": "core", "found_in": found}], git=git)

    done = subprocess.run(argv, capture_output=True, text=True)

    assert done.returncode == 1
    assert "Traceback" not in done.stderr
    assert sum(ln.startswith("fix: ") for ln in done.stderr.splitlines()) == 1
