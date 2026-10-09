"""dd-bug-resolution/scripts/bugs.py owns BUGS.jsonl validation
(0.4.7 c7 T-047-63: the ledger verbs move into stdlib skill scripts). Size: SMALL.

The script reads its schema from ``scripts/schemas/`` BESIDE itself — a copy `public
stage` makes. Every test here therefore stages the pair into a tmp dir exactly as
stage does, which is also what proves the copy is the only path the script has.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.infrastructure.ledger_scripts import load_owner
from tests.helpers.skill_scripts import stage_skill_scripts

_read = load_owner("dd-bug-resolution", "_ledger").records


_PUBLIC = Path(__file__).resolve().parents[5] / "dadaia_workspace" / "public"
_SCRIPTS = _PUBLIC / "skills" / "dd-bug-resolution" / "scripts"
_SOURCE = _SCRIPTS / "bugs.py"
#: Composed at run time: a tracked IPv4 literal is refused by the push-range scan.
_LOCAL_IP = ".".join(("10", "1", "2", "3"))
#: Same reason: an absolute home path is composed, never written as a tracked literal.
_HOME_PATH = "/".join(("", "home", "someone", "work"))

_OPEN_RECORD: dict[str, object] = {
    "id": "a-bug",
    "ts": "2026-09-20T10:00:00Z",
    "reported_by": "software-engineer",
    "title": "t",
    "severity": "LOW",
    "surface": "cli",
    "component": "c",
    "context": "ctx",
    "symptom": "s",
    "repro": "r",
    "expected": "e",
    "status": "open",
    "cause": None,
    "caused_by": None,
    "closed_at": None,
}


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: bugs.py with its schema copy beside it, `candidate_at`'s skill beside its own."""
    stage_skill_scripts(
        "dd-release-implementation", tmp_path / "dd-release-implementation" / "scripts"
    )
    return stage_skill_scripts("dd-bug-resolution", tmp_path / "staged" / "scripts") / "bugs.py"


def _ledger(root: Path, *records: dict[str, object]) -> Path:
    """A git repo tracking `cli/` and the dot-directory `.github/` (F011, AC2.17)."""
    specs = root / "specs"
    (specs / "bugs").mkdir(parents=True, exist_ok=True)
    for tracked in ("cli", ".github"):
        (root / tracked).mkdir(exist_ok=True)
        (root / tracked / "x.py").write_text("def y() -> None: ...\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "cli", ".github"], check=True)
    schema = json.loads(
        (_PUBLIC / "schemas" / "bugs" / "bug-record-v1.schema.json").read_text(encoding="utf-8")
    )
    properties, required = set(schema["properties"]), set(schema["required"])
    shaped = [
        {**{key: None for key in required - record.keys()},
         **{key: value for key, value in record.items() if key in properties}}
        for record in records
    ]
    (specs / "bugs" / "BUGS.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in shaped), encoding="utf-8"
    )
    return specs


def _run(script: Path, *argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )


def test_clean_ledger_exits_zero(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.strip() == "" or "error" not in done.stdout


def test_record_missing_an_immutable_core_field_is_one_error_line(
    script: Path, tmp_path: Path
) -> None:
    broken = {k: v for k, v in _OPEN_RECORD.items() if k != "symptom"}
    specs = _ledger(tmp_path, broken)
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    lines = [ln for ln in done.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1, lines
    assert lines[0].startswith("LEDGER-BUGS-SCHEMA error ")
    assert "symptom" in lines[0] and "bugs/BUGS.jsonl:1" in lines[0]


@pytest.mark.parametrize(
    ("mutation", "needle"),
    [
        ({"status": "resolved"}, "closed_at"),
        ({"closed_at": "2026-09-20"}, "closed_at"),
        ({"severity": "URGENT"}, "severity"),
        ({"ts": "yesterday"}, "ts"),
        ({"root_cause": "retired key"}, "root_cause"),
        ({"diff_direction": "net-negative"}, "diff_direction"),  # ADR 0160: derived, never stored
    ],
)
def test_invariant_violations_are_reported(
    script: Path, tmp_path: Path, mutation: dict[str, object], needle: str
) -> None:
    specs = _ledger(tmp_path, {**_OPEN_RECORD, **mutation})
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    assert needle in done.stdout


def test_closed_at_before_ts_is_refused(script: Path, tmp_path: Path) -> None:
    record = {
        **_OPEN_RECORD,
        "status": "resolved",
        "closed_at": "2020-01-01T00:00:00Z",
        "solution": "s",
    }
    done = _run(script, "check", "--specs", str(_ledger(tmp_path, record)))
    assert done.returncode == 1
    assert "precedes" in done.stdout


def test_duplicate_ids_are_refused(script: Path, tmp_path: Path) -> None:
    done = _run(script, "check", "--specs", str(_ledger(tmp_path, _OPEN_RECORD, _OPEN_RECORD)))
    assert done.returncode == 1
    assert "duplicate" in done.stdout


@pytest.mark.parametrize(
    ("links", "needle"),
    [
        ({"a-bug": "b-bug", "b-bug": "a-bug"}, "cycle"),
        ({"a-bug": "never-filed"}, "names no record"),
    ],
)
def test_check_refuses_a_caused_by_cycle_or_dangling_target(
    script: Path, tmp_path: Path, links: dict[str, str], needle: str
) -> None:
    """AC3.8 (F012): lineage is acyclic and every target is a record, the archive's included."""
    records = [{**_OPEN_RECORD, "id": i, "caused_by": links.get(i)} for i in ("a-bug", "b-bug")]
    specs = _ledger(tmp_path, *records)
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    assert needle in done.stdout, done.stdout
    _archive(specs, "never-filed")
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == (1 if needle == "cycle" else 0), done.stdout


@pytest.mark.parametrize(("caused_by", "code"), [
    ("J1.T3", 0),
    ("J1.S2.T3", 0),  # historical task ids stay readable
    ("J9.S9.T9", 1),  # in no tasks/<job>.md
])  # fmt: skip
def test_check_resolves_a_job_task_id_against_the_rc_tasks_folder(
    script: Path, tmp_path: Path, caused_by: str, code: int
) -> None:
    specs = _ledger(tmp_path, {**_OPEN_RECORD, "caused_by": caused_by})
    job = specs / "releases" / "0.5.0" / "rc-9" / "tasks" / "job1.md"
    job.parent.mkdir(parents=True)
    job.write_text("| J1.T3 | AC1.1 | `ci.py` |\n| J1.S2.T3 | AC1.1 | `old.py` |\n", encoding="utf-8")
    done = _run(script, "check", "--specs", str(specs), "--json")
    assert done.returncode == code, done.stdout
    fixes = [f["fix"] for f in json.loads(done.stdout)]
    assert fixes == ([f"{Path(sys.executable).as_posix()} {script.as_posix()} update a-bug"
                      f" --set caused_by=none --specs {specs.as_posix()}"]
                     if code else []), fixes  # fmt: skip


def _archive(specs: Path, bug_id: str) -> None:
    archived = {**_OPEN_RECORD, "id": bug_id, "status": "rejected", "cause": "c",
                "closed_at": "2026-09-21T00:00:00Z"}  # fmt: skip
    (specs / "bugs" / "_archive").mkdir()
    (specs / "bugs" / "_archive" / "bugs_histo.jsonl").write_text(json.dumps(archived) + "\n")


def test_json_output_carries_one_object_per_finding(script: Path, tmp_path: Path) -> None:
    broken = {k: v for k, v in _OPEN_RECORD.items() if k != "symptom"}
    done = _run(script, "check", "--specs", str(_ledger(tmp_path, broken)), "--json")
    assert done.returncode == 1
    payload = json.loads(done.stdout)
    assert len(payload) == 1
    assert payload[0]["code"] == "LEDGER-BUGS-SCHEMA"
    assert payload[0]["verdict"] == "error"
    assert payload[0]["line"] == 1


@pytest.mark.parametrize("bad", ["[1, 2]", "{not json"])
def test_a_write_over_an_unreadable_line_refuses_naming_it(
    script: Path, tmp_path: Path, bad: str
) -> None:
    """The store refuses to rewrite a ledger it cannot read in full, naming the line."""
    specs = _ledger(tmp_path, _OPEN_RECORD)
    ledger = specs / "bugs" / "BUGS.jsonl"
    ledger.write_text(ledger.read_text(encoding="utf-8") + bad + "\n", encoding="utf-8")
    done = _run(script, "update", "a-bug", "--set", "caused_by=none", "--specs", str(specs))
    assert done.returncode == 1
    assert "BUGS.jsonl:2" in done.stderr and "cannot read in full" in done.stderr
    assert f"sed -n '2p' {ledger}" in done.stderr


_APPEND = ["append", "--bug-id", "x", "--title", "t", "--severity", "LOW", "--surface", "cli",
           "--component", "c", "--context", "c", "--symptom", "s", "--repro", "r", "--expected", "e"]  # fmt: skip


@pytest.mark.skipif(sys.platform == "win32", reason="the fake workspace CLI is a shebang script")
@pytest.mark.parametrize(
    ("argv", "trees", "fix", "note"),
    [
        (["stats"], ("0.5.0-rc1/j5",), "{rerun} --specs {ws}/repos/demo/specs", ""),
        (_APPEND, ("0.5.0-rc1/j1",), "{rerun} --specs {ws}/worktrees/demo/0.5.0-rc1/j1/specs", ""),
        (_APPEND, ("0.5.0-rc1/j7", "0.5.0-rc1/j6"), "{rerun} --specs {ws}/worktrees/demo/0.5.0-rc1/j6/specs",
         "; the first by name of 2 open worktrees"),
        (_APPEND, ("0.5.0-rc1/define", "0.5.0-rc1/j6--J1.S1.T1", "0.5.0-rc1-define/.agents",
                   "backlog/b", "0.5.0-rc1/j7"),
         "{rerun} --specs {ws}/worktrees/demo/0.5.0-rc1/j7/specs", ""),
        (_APPEND, ("0.5.0-rc1/define", "0.5.0-rc1-define/.agents"),
         "{py} {ws}/dd-gitflow-default/scripts/worktree.py list", ""),
        (_APPEND, (), "{py} {ws}/dd-gitflow-default/scripts/worktree.py list", ""),
    ],
)  # fmt: skip
def test_a_missing_specs_tree_is_refused_never_created(
    script: Path, tmp_path: Path, argv: list[str], trees: tuple[str, ...], fix: str, note: str
) -> None:
    """bug-law-spelling-registers-into-a-reaped-root-specs-tree; AC4.4 `_bound_tree`: a read
    verb reruns on the bound repo tree (and runs as printed); a write verb's fix names the
    repo's first open job worktree (ADR 0191), else the command listing them — never
    `repos/<r>/specs`, which only `specs/audits/` may write."""
    (cli := tmp_path / ".dadaia/.venv/bin/dadaia").parent.mkdir(parents=True)
    cli.write_text(f'#!{sys.executable}\nprint(\'{{"main_repo": "demo"}}\')\n', "utf-8")
    cli.chmod(0o755)
    (tmp_path / ".dadaia/states").mkdir()  # a workspace root holds its sentinel
    (tmp_path / ".dadaia/states/spec_contexts.json").write_text("{}")
    (tmp_path / ".git").mkdir()
    stage_skill_scripts("dd-gitflow-default", tmp_path / "dd-gitflow-default" / "scripts")
    for name in trees:
        (tmp_path / "worktrees" / "demo" / name).mkdir(parents=True)
    done = _run(script, *argv, "--specs", "specs", cwd=tmp_path)
    assert done.returncode == 1 and not (tmp_path / "specs").exists()
    rerun = f"{sys.executable} {script} {' '.join(argv)}"
    want = fix.format(rerun=rerun, ws=tmp_path, py=sys.executable)
    assert [ln for ln in done.stderr.splitlines() if ln.startswith("fix:")] == [f"fix: {want}"]
    assert done.stderr.splitlines()[0].endswith(f"nothing was written{note}")
    if argv == ["stats"]:  # the read runs as printed
        _ledger(tmp_path / "repos" / "demo")
        assert subprocess.run(want, shell=True, check=False, cwd=tmp_path).returncode == 0  # noqa: S602


def test_a_fix_already_naming_its_tree_gains_no_second_specs() -> None:
    """T-050-140 review I1: `with_specs` is idempotent."""
    spec = importlib.util.spec_from_file_location("_specs", _SCRIPTS / "_specs.py")
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(specs := importlib.util.module_from_spec(spec))
    fix = f"{specs.script(_SOURCE)} check --specs /a/specs"
    assert specs.with_specs(fix, Path("/b/specs")) == fix


def test_specs_default_resolves_the_nearest_git_rooted_specs_tree(
    script: Path, tmp_path: Path
) -> None:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    _ledger(root, _OPEN_RECORD)
    deep = root / "a" / "b"
    deep.mkdir(parents=True)
    assert _run(script, "check", cwd=deep).returncode == 0


def test_a_bad_archive_line_is_a_finding(script: Path, tmp_path: Path) -> None:
    """sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts#48.5: a non-JSON or
    non-bug-record-v1 line in bugs_histo.jsonl is a finding and check exits non-zero; a
    pre-v6 `event` line is history."""
    specs = _ledger(tmp_path, _OPEN_RECORD)
    (specs / "bugs" / "_archive").mkdir()
    (specs / "bugs" / "_archive" / "bugs_histo.jsonl").write_text(
        '{"event": "archived", "data": {}}\nnot json\n{"id": "x"}\n', encoding="utf-8"
    )
    done = _run(script, "check", "--specs", str(specs), "--json")
    assert done.returncode == 1
    assert [(f["path"], f["line"]) for f in json.loads(done.stdout)][:2] == [
        ("bugs/_archive/bugs_histo.jsonl", 2),
        ("bugs/_archive/bugs_histo.jsonl", 3),
    ]


def test_absent_ledger_is_not_a_finding(script: Path, tmp_path: Path) -> None:
    """A young specs tree has no bugs file yet — same posture as the doctor's."""
    specs = tmp_path / "specs"
    specs.mkdir()
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


@pytest.mark.parametrize(
    "bad",
    [
        "{not a record",
        "[1, 2]",
        json.dumps({**_OPEN_RECORD, "severity": "BLOCKER"}),
        json.dumps({**_OPEN_RECORD, "context": ""}),
        json.dumps({**_OPEN_RECORD, "root_cause": "a retired key"}),
        json.dumps({k: v for k, v in _OPEN_RECORD.items() if k != "title"}),
    ],
)
def test_a_bad_bug_line_is_one_finding_and_the_doctor_says_what_the_script_says(
    script: Path, tmp_path: Path, bad: str
) -> None:
    """sa-spec-doc-033-duplicates-bugs-check#B1: bug-record validity is reported only as
    LEDGER-BUGS-SCHEMA, and doctor = `bugs.py check` on every row.
    sa-spec-doc-033-duplicates-bugs-check#B3: severity BLOCKER gives exactly one finding."""
    from dadaia_workspace.features.specs import SpecsDoctor
    from dadaia_workspace.infrastructure.ledger_scripts import script_findings

    specs = _ledger(tmp_path, _OPEN_RECORD)
    ledger = specs / "bugs" / "BUGS.jsonl"
    ledger.write_text(ledger.read_text(encoding="utf-8") + bad + "\n", encoding="utf-8")
    checked = json.loads(_run(script, "check", "--specs", str(specs), "--json").stdout)
    expected = [f"{f['path']}:{f['line']} {f['message']}" for f in checked]

    own = [i.code for i in SpecsDoctor(specs).check() if i.message.endswith(f"({ledger})")]
    bugs = [f for f in script_findings(specs) if f.code == "LEDGER-BUGS-SCHEMA"]

    assert len(expected) == 1 and own == []
    assert [f.message for f in bugs] == expected


def test_script_is_executable_and_has_a_shebang() -> None:
    assert os.access(_SOURCE, os.X_OK)
    assert _SOURCE.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")


@pytest.mark.parametrize("verb", ["fix", "window", "balance"])
def test_retired_derived_verbs_are_not_cli_choices(script: Path, verb: str) -> None:
    done = _run(script, verb, "--help")
    assert done.returncode == 2
    assert f"invalid choice: '{verb}'" in done.stderr


# --- the write verbs (T-047-64): one ledger, one writer ------------------------------


def _store(script: Path) -> Any:
    """The staged `_bugs_store` module, loaded beside its own siblings as bugs.py loads it."""
    spec = importlib.util.spec_from_file_location("_bugs_store", script.parent / "_bugs_store.py")
    assert spec is not None and spec.loader is not None
    store = importlib.util.module_from_spec(spec)
    loaded, siblings = set(sys.modules), str(script.parent)
    sys.path.insert(0, siblings)
    try:
        spec.loader.exec_module(store)
    finally:  # its siblings stay this test's: never a cached copy of another tmp tree
        sys.path.remove(siblings)
        for name in set(sys.modules) - loaded:
            del sys.modules[name]
    return store


def _records(specs: Path) -> list[dict[str, Any]]:
    return _read(specs / "bugs/BUGS.jsonl")


def _resolve_argv(
    bug_id: str = "a-bug", caused_by: str = "none"
) -> list[str]:
    return [
        "resolve", bug_id, "--cause", "c", "--caused-by", caused_by,
        "--solution", "s", "--fix-sha", "a" * 40,
    ]  # fmt: skip


def test_append_registers_one_open_record(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path)
    done = _run(
        script, "append", "--specs", str(specs), "--bug-id", "new-bug", "--title", "t",
        "--severity", "LOW", "--surface", "cli", "--component", "c", "--context", "ctx",
        "--symptom", "s", "--repro", "r", "--expected", "e", "--correlates", "none",
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert "\n[ok] registered new-bug" in done.stdout
    [record] = _records(specs)
    assert record["status"] == "open" and record["closed_at"] is None
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_append_names_its_correlations_from_the_ledger(script: Path, tmp_path: Path) -> None:
    """ADR 0127 / AC1.12: append lists the open and the recently resolved records on its
    surface, refusing without `--correlates` or with an id the ledger lacks."""
    recent = {
        **_OPEN_RECORD,
        "id": "recent",
        "status": "resolved",
        "closed_at": "2999-01-01T00:00:00Z",
    }
    old = {**recent, "id": "old", "ts": "1999-01-01T00:00:00Z", "closed_at": "2000-01-01T00:00:00Z"}
    other = {**_OPEN_RECORD, "id": "other", "surface": "hooks"}
    specs = _ledger(tmp_path, _OPEN_RECORD, recent, old, other)
    argv = ["append", "--specs", str(specs), "--bug-id", "new-bug", "--title", "t",
            "--severity", "LOW", "--surface", "cli", "--component", "c", "--context", "ctx",
            "--symptom", "s", "--repro", "r", "--expected", "e"]  # fmt: skip
    bare, stray = _run(script, *argv), _run(script, *argv, "--correlates", "a-bug,ghost")
    assert bare.returncode == stray.returncode == 1
    assert "candidates on 'cli': a-bug, recent\n" in bare.stdout
    named = _run(script, *argv, "--correlates", "a-bug,old")
    assert named.stdout.startswith("correlation candidates on 'cli': a-bug, recent\n")
    assert _records(specs)[-1]["correlates"] == ["a-bug", "old"]


@pytest.mark.parametrize(
    ("field", "value", "needle"),
    [("surface", "cli", None), ("surface", ".github", None), ("surface", "unknown", "(closest: .github, cli)"),
     ("context", "", "shorter than its minLength"), ("component", "", "shorter than its minLength")],
)  # fmt: skip
def test_append_takes_a_tracked_directory_surface_and_non_blank_fields(
    script: Path, tmp_path: Path, field: str, value: str, needle: str | None
) -> None:
    """F011 / AC2.17: the tracked-directory set is the one decider — `.github` admitted,
    an untracked `unknown` refused naming close matches; this re-proves
    sa-consumer-law-carries-library-facts#FR8.1 (the context's own tree names it) and
    supersedes sa-spec-doc-033-duplicates-bugs-check#B5 (free text). #B2: a blank context
    or component is refused. Every refusal leaves the ledger untouched."""
    specs = _ledger(tmp_path)
    values = {"surface": "cli", "context": "ctx", "component": "c", field: value}
    done = _run(script, "append", "--specs", str(specs), "--bug-id", "b", "--title", "t",
                "--severity", "LOW", *[f"--{k}={v}" for k, v in values.items()],
                "--symptom", "s", "--repro", "r", "--expected", "e", "--correlates", "none")  # fmt: skip
    assert (done.returncode, needle is None or needle in done.stderr) == (int(bool(needle)), True)
    assert len(_records(specs)) == int(needle is None), done.stderr


def test_an_operator_action_run_outside_the_tree_keeps_its_specs_and_known_argv(
    script: Path, tmp_path: Path
) -> None:
    """AC4.4, bug ledger-fix-lines-drop-specs (T-050-151 review H1, L8):
    an `Operator action: run` fix quotes the refused command with `--specs` and every known
    flag, so pasted from outside the tree it refuses only on the choice the words name."""
    specs, elsewhere = _ledger(tmp_path), tmp_path / "elsewhere"
    elsewhere.mkdir()
    done = _run(script, "append", "--specs", str(specs), "--bug-id", "b", "--title", "t",
                "--severity", "LOW", "--surface", "nowhere", "--component", "c", "--context",
                "ctx", "--symptom", "s", "--repro", "r", "--expected", "e", "--correlates",
                "none", cwd=elsewhere)  # fmt: skip
    (fix,) = [ln for ln in done.stderr.splitlines() if ln.startswith("fix: ")]
    command = fix.split("`")[1]
    assert (
        fix.startswith("fix: Operator action: run `") and f"--specs {specs.as_posix()}" in command
    ), fix
    assert "--bug-id b" in command and "--correlates none" in command, fix


def test_append_outside_a_git_tree_is_one_refusal_naming_the_cause(
    script: Path, tmp_path: Path
) -> None:
    """F011: with no tracked tree to read, append refuses once, never with a traceback."""
    specs = tmp_path / "specs"
    (specs / "bugs").mkdir(parents=True)
    done = _run(script, "append", "--specs", str(specs), "--bug-id", "b", "--title", "t",
                "--severity", "LOW", "--surface", "cli", "--component", "c", "--context", "ctx",
                "--symptom", "s", "--repro", "r", "--expected", "e", "--correlates", "none")  # fmt: skip
    assert done.returncode == 1 and "Traceback" not in done.stderr
    assert "cannot list the repo's tracked directories: fatal:" in done.stderr
    assert "fix: Operator action: point --specs at a specs tree inside a git repo" in done.stderr


def test_append_refuses_a_duplicate_id_and_writes_nothing(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    before = (specs / "bugs" / "BUGS.jsonl").read_bytes()
    done = _run(
        script, "append", "--specs", str(specs), "--bug-id", "a-bug", "--title", "t",
        "--severity", "LOW", "--surface", "cli", "--component", "c", "--context", "ctx",
        "--symptom", "s", "--repro", "r", "--expected", "e",
    )  # fmt: skip
    assert done.returncode == 1
    assert "already exists" in done.stderr
    assert (specs / "bugs" / "BUGS.jsonl").read_bytes() == before


_SHA = "0123456789abcdef" * 2 + "01234567"


@pytest.mark.parametrize(
    ("value", "pushed"),
    [(f"seen at {_HOME_PATH}", True), (f"seen at {_LOCAL_IP}", True), (_SHA, False)],
)
def test_the_seam_refuses_exactly_what_the_push_refuses(
    script: Path, tmp_path: Path, value: str, pushed: bool
) -> None:
    """sa-ledger-write-seam-redacts-less-than-push-refuses#B1: append refuses a
    push-matched value, naming the field and the masked term, ledger unchanged.
    sa-ledger-write-seam-redacts-less-than-push-refuses#B3: resolve refuses it too and the
    record stays open. sa-ledger-write-seam-redacts-less-than-push-refuses#B4: on the same
    matrix the seam refuses iff the push matcher does.
    sa-ledger-write-seam-redacts-less-than-push-refuses#B5: a bare sha is not refused."""
    from dadaia_workspace.core.models.git_scan import ScannedObject
    from dadaia_workspace.features.chokepoints.denylist_scan import scan_objects
    from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns

    blob = ScannedObject(path="BUGS.jsonl", sha="", text=value, decodable=True)
    assert bool(scan_objects([blob], [], load_baseline_patterns()).hits) is pushed
    specs = _ledger(tmp_path, _OPEN_RECORD)
    before = (specs / "bugs" / "BUGS.jsonl").read_bytes()
    argv = _resolve_argv()
    argv[argv.index("--solution") + 1] = value
    appended = _run(
        script, "append", "--specs", str(specs), "--bug-id", "leaky", "--title", "t",
        "--severity", "LOW", "--surface", "cli", "--component", "c", "--context", "ctx",
        "--symptom", value, "--repro", "r", "--expected", "e", "--correlates", "none",
    )  # fmt: skip
    resolved = _run(script, *argv, "--specs", str(specs))
    for done, field in ((appended, "symptom"), (resolved, "solution")):
        assert (done.returncode == 1) is pushed, done.stderr
        assert (f"field {field!r} carries" in done.stderr) is pushed
    if pushed:
        assert (specs / "bugs" / "BUGS.jsonl").read_bytes() == before


_SLUG = {**_OPEN_RECORD, "context": "acme-games"}


# fmt: off
@pytest.mark.parametrize(("published", "context", "pushed", "rev_list_fails"), [
    pytest.param((_SLUG,), "acme-games", False, False, id="published-context-accepted"),
    pytest.param((_OPEN_RECORD,), "acme-games", True, False, id="unpublished-term-refused"),
    pytest.param((_OPEN_RECORD,), "ctx", False, False, id="no-term-accepted"),
    pytest.param((_SLUG,), "acme-games", True, True, id="failed-rev-list-amnesties-nothing"),
])
# fmt: on
def test_the_seam_verdict_equals_the_push_verdict_over_the_published_ledger(
    script: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    published: tuple[dict[str, object], ...], context: str, pushed: bool, rev_list_fails: bool,
) -> None:
    from dadaia_workspace.core.models.git_scan import ScannedObject
    from dadaia_workspace.features.chokepoints.denylist_scan import scan_objects
    from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns

    denylist = tmp_path / "denylist.json"
    denylist.write_text(json.dumps({"acme": "client"}), encoding="utf-8")
    monkeypatch.setenv("DADAIA_PRIVACY_DENYLIST", str(denylist))
    root = tmp_path / "repo"
    ledger = _ledger(root, *published) / "bugs" / "BUGS.jsonl"
    prior = ledger.read_text(encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c",
                    "user.email=t@t.invalid", "commit", "-qm", "published"], check=True)  # fmt: skip
    origin = tmp_path / "origin.git"  # published = what origin holds, as the push reads it
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run(["git", "-C", str(root), "push", "-q", "origin", "HEAD"], check=True)
    if rev_list_fails:  # a remote-tracking ref at a missing object: `rev-list` dies on every OS
        ghost = root / ".git" / "refs" / "remotes" / "origin" / "ghost"
        ghost.write_text("1" * 40 + "\n", encoding="utf-8")

    done = _run(
        script, "append", "--specs", str(root / "specs"), "--bug-id", "new-bug", "--title",
        "t", "--severity", "LOW", "--surface", "cli", "--component", "c", "--context",
        context, "--symptom", "s", "--repro", "r", "--expected", "e", "--correlates", "none",
    )  # fmt: skip

    blob = ScannedObject(path="specs/bugs/BUGS.jsonl", sha="", decodable=True,
                         text=ledger.read_text(encoding="utf-8") if done.returncode == 0
                         else prior + json.dumps({"context": context}) + "\n",
                         prior_text=None if rev_list_fails else prior)  # fmt: skip
    push_refuses = bool(scan_objects([blob], [("acme", "client")], load_baseline_patterns()).hits)
    assert push_refuses is pushed
    assert (done.returncode == 1) is pushed, done.stderr


def test_every_ledger_skill_stages_a_byte_identical_privacy_pair(tmp_path: Path) -> None:
    """sa-ledger-write-seam-redacts-less-than-push-refuses#B6: every ledger skill carries a
    byte-identical _privacy.py (the push matcher's module) and baseline copy."""
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

    FileSystemPublicAssetManager().stage(tmp_path)
    package = _PUBLIC.parent
    for skill in ("dd-bug-resolution", "dd-backlog-definition"):
        scripts = tmp_path / ".dadaia" / "agentic" / "skills" / skill / "scripts"
        assert (scripts / "_privacy.py").read_bytes() == (
            package / "core" / "redaction.py"
        ).read_bytes()
        assert (scripts / "privacy_baseline.json").read_bytes() == (
            package / "infrastructure" / "data" / "privacy_baseline.json"
        ).read_bytes()


def test_resolve_closes_the_record_at_its_own_instant(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, *_resolve_argv(), "--specs", str(specs))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[ok] resolved a-bug"
    [record] = _records(specs)
    assert {key: record[key] for key in ("status", "cause", "caused_by", "solution", "fix_sha")} == {
        "status": "resolved", "cause": "c", "caused_by": "none", "solution": "s",
        "fix_sha": "a" * 40,
    }
    assert record["closed_at"] is not None
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


@pytest.mark.parametrize(
    "argv",
    [
        ["update", "a-bug", "--set", "caused_by=never-filed"],
        ["update", "a-bug", "--set", "caused_by="],
        ["update", "a-bug", "--set", "caused_by=b-bug"],  # b-bug -> a-bug: a cycle
        _resolve_argv(caused_by="never-filed"),
    ],
)
def test_a_write_refuses_the_lineage_check_refuses(
    script: Path, tmp_path: Path, argv: list[str]
) -> None:
    """AC3.8, one judge: every write runs the lineage rule `check` runs, before writing."""
    other = {**_OPEN_RECORD, "id": "b-bug", "caused_by": "a-bug"}
    specs = _ledger(tmp_path, _OPEN_RECORD, other)
    before = (specs / "bugs" / "BUGS.jsonl").read_bytes()
    done = _run(script, *argv, "--specs", str(specs))
    assert done.returncode == 1
    assert "caused_by" in done.stderr
    # ledger-fix-lines-drop-specs: the fix runs as printed, from any cwd
    fix = f"fix: {sys.executable} {script} check --specs {specs.resolve()}"
    assert fix.replace("\\", "/") in done.stderr.replace("\\", "/")
    assert (specs / "bugs" / "BUGS.jsonl").read_bytes() == before


@pytest.mark.parametrize("archive", [False, True])
def test_only_an_archived_drop_keeps_its_id_known(
    script: Path, tmp_path: Path, archive: bool
) -> None:
    """A commit dropping a referenced record without archiving it would leave a target
    `check` refuses: the write refuses it too. Archived, the id stays known."""
    store = _store(script)
    other = {**_OPEN_RECORD, "id": "b-bug", "caused_by": "a-bug"}
    specs = _ledger(tmp_path, _OPEN_RECORD, other)
    ledger = specs / "bugs" / "BUGS.jsonl"

    def drop(rs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [r for r in rs if r["id"] != "a-bug"]

    if archive:
        store.commit(ledger, drop, archive=True)
        assert _run(script, "check", "--specs", str(specs)).returncode == 0
    else:
        with pytest.raises(store.Refusal, match="names no record"):
            store.commit(ledger, drop)
        assert [r["id"] for r in _records(specs)] == ["a-bug", "b-bug"]


def test_an_archive_racing_an_archive_loses_no_record(script: Path, tmp_path: Path) -> None:
    """Review R4: B archives during A's first apply; A's retry re-reads both files, so
    every record survives in the ledger or the archive."""
    store = _store(script)
    closed = {
        **_OPEN_RECORD,
        "status": "rejected",
        "cause": "c",
        "closed_at": "2026-09-21T00:00:00Z",
    }
    specs = _ledger(tmp_path, {**closed, "id": "old-a"}, {**closed, "id": "old-b"}, _OPEN_RECORD)
    ledger = specs / "bugs" / "BUGS.jsonl"
    calls: list[int] = []

    def apply_a(records: list[dict[str, object]]) -> list[dict[str, object]]:
        calls.append(1)
        if len(calls) == 1:  # B runs to completion inside A's first attempt
            time.sleep(0.01)  # a distinct mtime: the stamp sees B's write
            store.commit(ledger, lambda rs: [r for r in rs if r["id"] != "old-b"], archive=True)
        return [r for r in records if r["id"] != "old-a"]

    store.commit(ledger, apply_a, archive=True)
    histo = specs / "bugs" / "_archive" / "bugs_histo.jsonl"
    archived = [r["id"] for r in _read(histo)]
    assert [r["id"] for r in _records(specs)] == ["a-bug"]
    assert sorted(archived) == ["old-a", "old-b"]


def test_resolve_names_every_missing_field_at_once(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, "resolve", "a-bug", "--cause", "c", "--specs", str(specs))
    assert done.returncode == 1
    for name in ("caused_by", "solution", "fix_sha"):
        assert name in done.stderr
    assert _records(specs)[0]["status"] == "open"


@pytest.mark.parametrize(
    ("verb", "option", "status", "field"),
    [
        ("supersede", "--by", "superseded", "superseded_by"),
        ("reject", "--reason", "rejected", "cause"),
    ],
)
def test_the_other_transitions_close_the_record(
    script: Path, tmp_path: Path, verb: str, option: str, status: str, field: str
) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, verb, "a-bug", option, "because", "--specs", str(specs))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == f"[ok] {status} a-bug"
    [record] = _records(specs)
    assert record["status"] == status and record[field] == "because"
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_the_defer_transition_is_absent(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, "defer", "a-bug", "--reason", "later", "--specs", str(specs))
    assert done.returncode == 2
    assert "invalid choice: 'defer'" in done.stderr
    assert _records(specs) == [_OPEN_RECORD]


def test_update_writes_a_governance_field(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, "update", "a-bug", "--set", "caused_by=none", "--specs", str(specs))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[ok] updated caused_by for a-bug"
    assert _records(specs)[0]["caused_by"] == "none"


@pytest.mark.parametrize(
    ("change", "owner"),
    [
        ("status=resolved", "resolve, supersede, reject"),
        ("closed_at=2026-09-21T00:00:00Z", "resolve, supersede, reject"),
        ("superseded_by=other", "supersede"),
        ("title=rewritten", "immutable-core"),
        ("reported_by=other", "immutable-core"),
        ("context=other", "immutable-core"),
    ],
)
def test_update_refuses_a_field_it_does_not_own(
    script: Path, tmp_path: Path, change: str, owner: str
) -> None:
    """sa-spec-doc-033-duplicates-bugs-check#B6: update refuses x-mutability
    immutable-core (reported_by and context included) and refuses superseded_by; the
    refusal names the owner and the ledger is untouched."""
    specs = _ledger(tmp_path, _OPEN_RECORD)
    before = (specs / "bugs" / "BUGS.jsonl").read_bytes()
    done = _run(script, "update", "a-bug", "--set", change, "--specs", str(specs))
    assert done.returncode == 1
    assert owner in done.stderr
    assert (specs / "bugs" / "BUGS.jsonl").read_bytes() == before


def test_a_write_once_field_refuses_a_differing_second_write(script: Path, tmp_path: Path) -> None:
    """`fix_sha` is write-once: a differing second value is refused."""
    specs = _ledger(tmp_path, _OPEN_RECORD)
    first = _run(script, "update", "a-bug", "--set", f"fix_sha={'a' * 40}", "--specs", str(specs))
    second = _run(script, "update", "a-bug", "--set", f"fix_sha={'b' * 40}", "--specs", str(specs))
    assert first.returncode == 0, first.stderr
    assert second.returncode == 1
    assert "write-once" in second.stderr
    assert _records(specs)[0]["fix_sha"] == "a" * 40


def test_status_and_stats_read_the_ledger(script: Path, tmp_path: Path) -> None:
    closed = {
        **_OPEN_RECORD, "id": "old-bug", "status": "resolved",
        "closed_at": "2026-09-20T11:00:00Z", "severity": "HIGH",
    }  # fmt: skip
    specs = _ledger(tmp_path, _OPEN_RECORD, closed)
    open_only = _run(script, "status", "--specs", str(specs))
    assert open_only.stdout.splitlines()[-1] == "[ok] 1 open bug(s)."
    every = _run(script, "status", "--all", "--specs", str(specs))
    assert every.stdout.splitlines()[-1] == "[ok] 2 all bug(s)."
    stats = _run(script, "stats", "--specs", str(specs))
    assert "total\t2" in stats.stdout
    assert "status:resolved\t1" in stats.stdout
    assert "severity:HIGH\t1" in stats.stdout
    assert not [ln for ln in stats.stdout.splitlines() if ln.startswith("direction:")]  # AC9.2


def _closed(bug_id: str) -> dict[str, object]:
    return {**_OPEN_RECORD, "id": bug_id, "status": "rejected", "cause": "c",
            "closed_at": "2026-09-21T00:00:00Z"}  # fmt: skip


@pytest.mark.parametrize(("argv", "code"), [
    (["old-a", "old-b"], 0),
    (["old-a", "a-bug"], 1),  # an open record never leaves
    (["--threshold-days", "90"], 2),  # the age path is gone
    ([], 2),  # no record named
])  # fmt: skip
def test_archive_moves_named_terminal_records_without_an_adr_gate(
    script: Path, tmp_path: Path, argv: list[str], code: int
) -> None:
    """AC4.5: archive moves exactly the named terminal records with no ADR lookup or field."""
    specs = _ledger(tmp_path, _OPEN_RECORD, _closed("old-a"), _closed("old-b"), _closed("old-c"))
    (specs / "ADRs").mkdir()
    (specs / "ADRs" / "decisions.jsonl").write_text(
        json.dumps({"id": "0999", "status": "proposed"}) + "\n"
    )
    histo = specs / "bugs" / "_archive" / "bugs_histo.jsonl"
    histo.parent.mkdir()
    histo.write_text(json.dumps({"event": "archived", "data": {}}) + "\n", encoding="utf-8")
    before = [(specs / "bugs" / "BUGS.jsonl").read_bytes(), histo.read_bytes()]
    done = _run(script, "archive", *argv, "--specs", str(specs))
    assert done.returncode == code, done.stderr
    if code:
        assert [(specs / "bugs" / "BUGS.jsonl").read_bytes(), histo.read_bytes()] == before
        return
    assert [r["id"] for r in _records(specs)] == ["a-bug", "old-c"]
    assert [r["id"] for r in _read(histo)[1:]] == ["old-a", "old-b"]
    assert not any("archived_by" in r for r in _read(histo)[1:])


def test_check_accepts_an_archived_record_without_adr_metadata(
    script: Path, tmp_path: Path
) -> None:
    """AC4.5: history contains the terminal product fact, not an ADR-derived marker."""
    specs = _ledger(tmp_path, _OPEN_RECORD)
    histo = specs / "bugs" / "_archive" / "bugs_histo.jsonl"
    histo.parent.mkdir()
    lines = [{"event": "archived", "data": {}}, _closed("old-a")]
    histo.write_text("".join(json.dumps(r) + "\n" for r in lines), encoding="utf-8")
    done = _run(script, "check", "--specs", str(specs))
    assert (done.returncode, done.stdout) == (0, "")


def test_a_concurrent_write_is_re_read_and_re_applied_once(script: Path, tmp_path: Path) -> None:
    """The ledger is ADDITIVE: a race surfaces and retries, it never blocks. A record
    appended by another writer WHILE this update computes survives the replace."""
    specs = _ledger(tmp_path, _OPEN_RECORD)
    ledger = specs / "bugs" / "BUGS.jsonl"
    rival = {**_OPEN_RECORD, "id": "rival-bug"}
    racer = tmp_path / "race.py"
    racer.write_text(
        "import json, pathlib, sys\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "p.write_text(p.read_text() + json.dumps(json.loads(sys.argv[2])) + chr(10))\n",
        encoding="utf-8",
    )
    # The rival write lands between this process reading and replacing: simulated by
    # writing it before the command runs but AFTER the (size, mtime) this test pins.
    subprocess.run([sys.executable, str(racer), str(ledger), json.dumps(rival)], check=True)
    done = _run(script, "update", "a-bug", "--set", "caused_by=none", "--specs", str(specs))
    assert done.returncode == 0, done.stderr
    ids = {str(r["id"]) for r in _records(specs)}
    assert ids == {"a-bug", "rival-bug"}, "the concurrent record must survive the replace"
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_the_projection_rule_carries_the_exec_bit_for_an_executable_source(
    tmp_path: Path,
) -> None:
    """A skill script an agent runs directly must project executable — the projection is
    a copy of its source, permissions included (0.4.7 FR1). Asserted over the real
    authored `public/skills/` tree through the public rule-table seam."""
    from dadaia_workspace.infrastructure.install_plan import InstallPlan
    from dadaia_workspace.infrastructure.projection_rules import projection_rules

    plan = InstallPlan(
        workspace_root=tmp_path,
        agentic_dir=_PUBLIC,
        harness=None,
        force=False,
        harness_targets=("agents",),
        active_harnesses=frozenset({"agents"}),
        overlay=None,
        resolved_models={},
    )
    modes = {
        rule.dst.name: rule.mode
        for rule in projection_rules(plan)
        if rule.dst.parent.name == "scripts" and rule.dst.parent.parent.name == "dd-bug-resolution"
    }
    assert modes, "the skills rule table produced no dd-bug-resolution script rules"
    assert modes["bugs.py"] == 0o755
    assert modes["_bugs_store.py"] == 0o755


def test_a_refused_archive_leaves_both_ledger_files_byte_intact(
    script: Path, tmp_path: Path
) -> None:
    """sa-ledger-verbs-append-histo-before-validating-the-pair#J2: "Given BUGS.jsonl
    holding an invalid record, when `bugs.py archive` runs, then it exits non-zero and
    BUGS.jsonl and bugs_histo.jsonl are byte-identical." Run twice: a retry included."""
    old = {
        **_OPEN_RECORD, "id": "old-bug", "ts": "2025-12-01T00:00:00Z",
        "status": "resolved", "closed_at": "2026-01-01T00:00:00Z",
    }  # fmt: skip
    specs = _ledger(tmp_path, {**_OPEN_RECORD, "severity": "SEVERE"}, old)
    histo = specs / "bugs" / "_archive" / "bugs_histo.jsonl"
    histo.parent.mkdir(parents=True)
    histo.write_text("", encoding="utf-8")
    before = [(specs / "bugs" / "BUGS.jsonl").read_bytes(), histo.read_bytes()]

    for _ in range(2):
        done = _run(script, "archive", "old-bug", "--specs", str(specs))
        assert done.returncode == 1, done.stdout
        assert [(specs / "bugs" / "BUGS.jsonl").read_bytes(), histo.read_bytes()] == before
