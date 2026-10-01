"""Intent: CONTRACT — AC2.1–AC2.6, AC1.9 (release 0.5.0 candidate 2, ADR 0041 `measured_by`);
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
from tests.helpers.release_state import SCHEDULE
from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = pytest.mark.contract

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"
_SKILL = _PUBLIC / "skills" / "dd-release-definition" / "SKILL.md"
_SCRIPTS = _PUBLIC / "skills" / "dd-release-implementation" / "scripts"
_HEADER = "| unit | today | bugs | verdict | why |\n|---|---|---|---|---|\n"
_ROW = "| `core/x.py` `run` | does x | 0 | {verdict} | reason |\n"
_AUTH_HEADER = "| question | authority | consults | deleted |\n|---|---|---|---|\n"
_AUTHORITIES = (
    "\n### 1.1 Authorities\n\n" + _AUTH_HEADER + "| who writes x | `core/x.run` | cli | `y` |\n"
)
_SKELETONS = (r"## 1\. As-is review", r"## 5\. Parallel schedule")
_GOOD = (
    "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="UPDATE") + _AUTHORITIES
    + "\n## 2. Strategy\n"
)  # fmt: skip


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
        ("SPEC.md", "**Origin:** operator-demand\n"),
        ("PLAN.md", plan),
        ("TASKS.md", "- [ ] T-1\n"),
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


def _admits(
    script: Path, tmp_path: Path, plan: str, *, authorities: bool = True, schedule: str = SCHEDULE
) -> None:
    """*authorities*: append a valid §1.1 table to a PLAN whose case is the As-is table."""
    specs = _specs(tmp_path, plan + (_AUTHORITIES if authorities else "") + schedule)
    result = _phase(script, specs)
    assert result.returncode == 0, result.stderr
    state = json.loads((specs / "releases/0.5.0/_RELEASE.json").read_text("utf-8"))
    assert (state["phase"], state["defined"]["sha"]) == ("IMPLEMENTATION", "abc1234")
    assert len(state["log"]) == 1


def _refuses(script: Path, tmp_path: Path, plan: str, *needles: str) -> str:
    specs = _specs(tmp_path, plan)
    before = (specs / "releases/0.5.0/_RELEASE.json").read_bytes()
    result = _phase(script, specs)
    assert result.returncode != 0
    assert (specs / "releases/0.5.0/_RELEASE.json").read_bytes() == before
    assert "PLAN.md" in result.stderr
    fixes = [line for line in result.stderr.splitlines() if line.lstrip().startswith("fix:")]
    assert len(fixes) == 1 and "dd-release-definition" in fixes[0] and "As-is review" in fixes[0]
    for needle in needles:
        assert needle in result.stderr
    return result.stderr


def test_a_plan_with_the_table_enters_implementation(script: Path, tmp_path: Path) -> None:
    _admits(script, tmp_path, _GOOD)


def test_an_unnumbered_heading_and_a_lowercase_verdict_pass(script: Path, tmp_path: Path) -> None:
    plan = "## as-is REVIEW\n\n" + _HEADER + _ROW.format(verdict="**`rebuild`**")
    _admits(script, tmp_path, plan)


def test_an_all_add_table_with_empty_cells_passes(script: Path, tmp_path: Path) -> None:
    _admits(script, tmp_path, "## 1. As-is review\n\n" + _HEADER + "| new.py | — |  | ADD |  |\n")


@pytest.mark.parametrize(
    "plan",
    [
        pytest.param("## 1. Strategy\n\nno table\n", id="heading-missing"),
        pytest.param("## 1. As-is review\n\nprose only\n\n## 2. Next\n\n" + _HEADER, id="no-table"),
        pytest.param(
            "## 1. As-is review\n\n| unit | verdict |\n|---|---|\n| a | KEEP |\n", id="wrong-header"
        ),
        pytest.param("## 1. As-is review\n\n" + _HEADER, id="zero-rows"),
    ],
)
def test_a_plan_without_the_table_structure_is_refused(
    script: Path, tmp_path: Path, plan: str
) -> None:
    _refuses(script, tmp_path, plan, "As-is review")


def test_a_verdict_outside_the_vocabulary_names_its_row(script: Path, tmp_path: Path) -> None:
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="SHRINK")
    _refuses(script, tmp_path, plan, "core/x.py", "SHRINK")


def test_an_unapproved_trio_refuses_before_the_table(script: Path, tmp_path: Path) -> None:
    result = _phase(script, _specs(tmp_path, "no table\n", plan_status="Draft"))
    assert result.returncode != 0
    assert "carries status 'Draft'" in result.stderr and "As-is review" not in result.stderr


def test_the_taught_skeleton_passes_the_check(script: Path, tmp_path: Path) -> None:
    """Both skeletons `dd-release-definition` shows (§1 As-is, §5 schedule) are the PLAN
    shape the gate admits."""
    skill = _SKILL.read_text("utf-8")
    fences = [re.search(rf"```markdown\n({h}\n.*?)```", skill, re.DOTALL) for h in _SKELETONS]
    assert all(fences), "dd-release-definition lost a PLAN skeleton"
    as_is, schedule = (f.group(1) for f in fences if f)
    _admits(script, tmp_path, as_is, authorities=False, schedule="\n" + schedule)


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


@pytest.mark.parametrize(
    "heading",
    ["## 1 As-is review", "## 1) As is review:", "## As-is review (PLAN §1)", "## 2. AS-IS REVIEW"],
)
def test_any_level_2_heading_naming_the_review_passes(
    script: Path, tmp_path: Path, heading: str
) -> None:
    _admits(script, tmp_path, f"{heading}\n\n" + _HEADER + _ROW.format(verdict="KEEP"))


def test_rows_without_outer_pipes_and_escaped_pipes_pass(script: Path, tmp_path: Path) -> None:
    table = (
        "unit | today | bugs | verdict | why\n---|---|---|---|---\n\ta \\| b\t| x | 0 |\tKEEP | y\n"
    )
    _admits(script, tmp_path, "## As-is review\n\n" + table)


def test_the_table_ends_at_its_first_blank_line(script: Path, tmp_path: Path) -> None:
    later = "\n| other | table | 0 | SHRINK | ignored |\n"
    _admits(script, tmp_path, _GOOD.split("\n## 2.")[0] + later)


def test_the_refusal_says_heading_missing_or_table_malformed(script: Path, tmp_path: Path) -> None:
    missing = _refuses(script, tmp_path / "a", "## Strategy\n", "heading")
    malformed = _refuses(script, tmp_path / "b", "## 1. As-is review\n\n" + _HEADER, "header")
    assert "not followed by a table" not in missing and "not followed by a table" in malformed


def test_every_fix_names_an_existing_absolute_path(script: Path, tmp_path: Path) -> None:
    """F1 — fix lines point at files, never at a cwd-relative or section-numbered command."""
    plan_fix = _refuses(script, tmp_path / "plan", "").split("fix: ")[1]
    skill = Path(re.search(r"of (\S+SKILL\.md)", plan_fix)[1]).relative_to(tmp_path)
    assert (_PUBLIC / skill).is_file(), "the staged sibling skill the fix names ships"
    fix = [ln for ln in _phase(script, _specs(tmp_path, "", plan_status="Draft")).stderr.splitlines()
           if ln.lstrip().startswith("fix:")][0]  # fmt: skip
    assert Path(fix.split(" in ", 1)[1].strip()).is_file()


def test_a_sentence_naming_the_columns_above_the_table_passes(script: Path, tmp_path: Path) -> None:
    prose = "## 1. As-is review\n\nColumns are `unit | today` and more.\n\n"
    _admits(script, tmp_path, prose + _HEADER + _ROW.format(verdict="KEEP"))


def test_a_plan_giving_each_question_one_authority_enters_implementation(
    script: Path, tmp_path: Path
) -> None:
    """AC5.2 fixture pair, good twin: one authority per question, a question repeated
    with the SAME authority is still one authority."""
    rows = "| who writes x | `a` | b |  |\n| who reads y | `c` |  | `d` |\n| who writes x | `a` | e |  |\n"
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="KEEP")
    _admits(
        script,
        tmp_path,
        plan + "\n### 1.1 Authorities\n\n" + _AUTH_HEADER + rows,
        authorities=False,
    )


def test_a_question_with_two_authorities_is_refused(script: Path, tmp_path: Path) -> None:
    """AC5.2 fixture pair, refused twin: the same question names two authorities."""
    rows = "| who writes x | `a` | b |  |\n| Who writes x | `z` |  |  |\n"
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="KEEP")
    stderr = _refuses(
        script, tmp_path, plan + "\n### 1.1 Authorities\n\n" + _AUTH_HEADER + rows,
        "'who writes x'", "two authorities",
    )  # fmt: skip
    assert "`a`" in stderr and "`z`" in stderr


@pytest.mark.parametrize(
    ("authorities", "needle"),
    [
        pytest.param("", "Authorities", id="no-table"),
        pytest.param("\n### 1.1 Authorities\n\nprose\n", "question | authority", id="no-header"),
        pytest.param("\n### 1.1 Authorities\n\n" + _AUTH_HEADER, "question | authority", id="zero-rows"),
        pytest.param(
            "\n### 1.1 Authorities\n\n" + _AUTH_HEADER + "| who writes x |  | b |  |\n",
            "empty authority", id="empty-authority",
        ),
    ],
)  # fmt: skip
def test_a_plan_without_a_well_formed_authorities_table_is_refused(
    script: Path, tmp_path: Path, authorities: str, needle: str
) -> None:
    """AC5.2: missing table, header or rows, or an empty authority — one fix line each."""
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="KEEP") + authorities
    _refuses(script, tmp_path, plan, needle)


def test_an_authorities_table_outside_section_1_does_not_count(
    script: Path, tmp_path: Path
) -> None:
    """AC5.2: the table belongs to §1; one under a later section is not the table."""
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="KEEP") + "\n## 2. Strategy\n"
    _refuses(script, tmp_path, plan + _AUTHORITIES, "Authorities")


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


_TASKS = (
    "- [ ] **T-1 — a.** `W:` `a.py`, `TASKS.md`, `specs/bugs/BUGS.jsonl`, `dir/map.json` (`x.py`)\n"
    "- [x] **T-3 — merged.** `W:` `a.py`\n"
    "- [ ] **T-2 — b.** `W:` `b.py`, `TASKS.md`, `specs/bugs/BUGS.jsonl`, `dir/map.json`, `x.py` · x\n"
)
_WIDE = SCHEDULE.replace("| T-1 | 1 |", "| T-1, T-2, T-3 | 3 |")


@pytest.mark.parametrize(
    ("schedule", "tasks", "needle"),
    [
        pytest.param(_WIDE, _TASKS, None, id="disjoint-outside-markers-ledgers-and-derived"),
        pytest.param("", _TASKS, "no '## … Parallel schedule' table", id="no-section"),
        pytest.param(_WIDE.replace("Critical path", "Path"), _TASKS, "critical path", id="no-path"),
        pytest.param(_WIDE.replace("| 3 |", "| 2 |"), _TASKS, "width 2 for 3", id="width"),
        pytest.param(_WIDE, _TASKS.replace("`b.py`", "`a.py`"), "T-1 and T-2 both write a.py", id="overlap"),
        pytest.param(_WIDE.replace("derived `dir", "derived `ir").replace("but", "`dir/map.json` but"),
                     _TASKS, "both write dir/map.json", id="derived-is-a-declared-path-suffix-only"),
    ],
)  # fmt: skip
def test_the_transition_and_check_judge_the_parallel_schedule_alike(
    script: Path, tmp_path: Path, schedule: str, tasks: str, needle: str | None
) -> None:
    """ADR 0141 `measured_by`: the PLAN carries the schedule and its critical path; each
    step's width counts its tasks, whose unfinished `W:` sets are disjoint outside TASKS.md,
    the JSONL ledgers and each path the schedule declares "derived `<path>`". `phase IMPLEMENTATION` refuses a row on
    DEFINITION, and `check` refuses the same row written onto an admitted tree."""
    specs = _specs(tmp_path, "")
    release = specs / "releases/0.5.0/rc-1"

    def write(schedule: str, tasks: str) -> None:
        (release / "PLAN.md").write_text(f"**Status:** Approved\n\n{_GOOD}{schedule}", "utf-8")
        (release / "TASKS.md").write_text(f"**Status:** Approved\n\n{tasks}", "utf-8")

    write(schedule, tasks)
    phase = _phase(script, specs)
    if needle:
        write(_WIDE, _TASKS)
        assert _phase(script, specs).returncode == 0
        write(schedule, tasks)
    check = subprocess.run([sys.executable, str(script), "check", "--specs", str(specs)],
                           capture_output=True, text=True)  # fmt: skip
    assert (phase.returncode != 0, check.returncode != 0) == (bool(needle),) * 2, check.stdout
    assert needle is None or needle in phase.stderr and needle in check.stdout


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
    specs = _specs(tmp_path, _GOOD + SCHEDULE)
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
    specs = _specs(tmp_path, _GOOD + SCHEDULE)
    entry = {"ts": "2026-01-02T00:00:00Z", "agent": "a", "kind": "dispositions", "text": "t"}
    state = specs / "releases/0.5.0/_RELEASE.json"
    defined = {"sha": "abc1234", "ts": "2026-01-01T00:00:00Z"}
    state.write_text(json.dumps({**json.loads(state.read_text("utf-8")), "phase": "CLOSURE",
                                 "defined": defined}))  # fmt: skip
    (specs / "releases/0.5.0/rc-1/SPEC.md").write_text(
        "# S\n\n**Status:** Approved\n**Origin:** backlog:a-real-entry; bugs:still-broken,already-fixed\n", "utf-8")  # fmt: skip
    _seed_ledgers(specs, log=[{**entry, "ts": "2025-12-31T00:00:00Z"}])
    assert [(f["verdict"], f["message"]) for f in _origin_rows(script, specs)] == [
        ("info", "Origin backlog:a-real-entry untraced"),
        ("info", "Origin bugs:still-broken untraced"),
        ("info", "Origin bugs:already-fixed traced"),
    ]

    _seed_ledgers(specs, log=[entry])

    errors = [f for f in _origin_rows(script, specs) if f["verdict"] == "error"]
    assert [(f["line"], f["message"]) for f in errors] == [
        (4, "Origin backlog:a-real-entry untraced"), (4, "Origin bugs:still-broken untraced")]  # fmt: skip
    assert " exit a-real-entry --disposition delivered --release 0.5.0 --specs " in errors[0]["fix"]
    assert " resolve still-broken --resolved-release 0.5.0 --specs " in errors[1]["fix"]


def test_a_carried_id_is_traced_through_its_owning_ledger_after_it_moves(
    script: Path, tmp_path: Path
) -> None:
    """AC3.2 (review F1, F5): `audit.py close` deletes the audit and leaves one histo record
    keyed by the audit id; `bugs.py archive` moves a record to the archive; `supersede`
    writes `superseded_by` — each carried id still traces, asked of the ledger owning it."""
    specs = _specs(tmp_path, _GOOD + SCHEDULE)
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
    specs = _specs(tmp_path, _GOOD + SCHEDULE)
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
    specs = _specs(tmp_path, _GOOD + SCHEDULE)
    (specs / "releases/0.5.0/rc-2").mkdir()
    (specs / "releases/0.5.0/rc-2/SPEC.md").write_text("**Status:** Draft\n", "utf-8")

    [row] = _origin_rows(script, specs)

    assert row["path"].endswith("rc-2/SPEC.md") and "has no `**Origin:**`" in row["message"]


def test_this_repos_live_spec_origin_passes(script: Path) -> None:
    assert _check(script, Path(__file__).resolve().parents[2] / "specs") == []
