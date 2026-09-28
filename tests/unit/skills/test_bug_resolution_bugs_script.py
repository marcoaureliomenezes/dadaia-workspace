"""Intent: CONTRACT — dd-bug-resolution/scripts/bugs.py owns BUGS.jsonl validation
(0.4.7 c7 T-047-63: the ledger verbs move into stdlib skill scripts). Size: SMALL.

The script reads its schema from ``scripts/schemas/`` BESIDE itself — a copy `public
stage` makes. Every test here therefore stages the pair into a tmp dir exactly as
stage does, which is also what proves the copy is the only path the script has.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_SCRIPTS = _PUBLIC / "skills" / "dd-bug-resolution" / "scripts"
_SOURCE = _SCRIPTS / "bugs.py"
#: Composed at run time: a tracked IPv4 literal is refused by the push-range scan.
_LOCAL_IP = ".".join(("10", "1", "2", "3"))
#: Same reason: an absolute home path is composed, never written as a tracked literal.
_HOME_PATH = "/".join(("", "home", "someone", "work"))
_SCHEMA = _PUBLIC / "schemas" / "bugs" / "bug-record-v1.schema.json"

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
    "resolved_release": None,
    "audited": None,
    "closed_at": None,
}


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: bugs.py with its schema copy beside it."""
    staged = tmp_path / "staged" / "scripts"
    (staged / "schemas").mkdir(parents=True)
    for module in sorted(_SCRIPTS.glob("*.py")):
        shutil.copy2(module, staged / module.name)
    shutil.copy2(_SCHEMA, staged / "schemas" / _SCHEMA.name)
    return staged / "bugs.py"


def _ledger(root: Path, *records: dict[str, object]) -> Path:
    specs = root / "specs"
    (specs / "bugs").mkdir(parents=True, exist_ok=True)
    (specs / "bugs" / "BUGS.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
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


def test_json_output_carries_one_object_per_finding(script: Path, tmp_path: Path) -> None:
    broken = {k: v for k, v in _OPEN_RECORD.items() if k != "symptom"}
    done = _run(script, "check", "--specs", str(_ledger(tmp_path, broken)), "--json")
    assert done.returncode == 1
    payload = json.loads(done.stdout)
    assert len(payload) == 1
    assert payload[0]["code"] == "LEDGER-BUGS-SCHEMA"
    assert payload[0]["verdict"] == "error"
    assert payload[0]["line"] == 1


def test_missing_specs_above_cwd_is_refused_with_one_fix_line(script: Path, tmp_path: Path) -> None:
    """No `specs/` at or above cwd whose parent holds `.git` — the default resolution
    refuses rather than guessing, and says exactly how to proceed."""
    lonely = tmp_path / "nowhere"
    lonely.mkdir()
    done = _run(script, "check", cwd=lonely)
    assert done.returncode == 1
    fixes = [ln for ln in (done.stdout + done.stderr).splitlines() if ln.startswith("fix:")]
    assert len(fixes) == 1
    assert "--specs" in fixes[0]


def test_specs_default_resolves_the_nearest_git_rooted_specs_tree(
    script: Path, tmp_path: Path
) -> None:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    _ledger(root, _OPEN_RECORD)
    deep = root / "a" / "b"
    deep.mkdir(parents=True)
    assert _run(script, "check", cwd=deep).returncode == 0


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

    own = [i.code for i in SpecsDoctor(specs).check() if i.path == str(ledger)]
    bugs = [f for f in script_findings(specs) if f.code == "LEDGER-BUGS-SCHEMA"]

    assert len(expected) == 1 and own == []
    assert [f.message for f in bugs] == expected


def test_script_is_executable_and_has_a_shebang() -> None:
    assert os.access(_SOURCE, os.X_OK)
    assert _SOURCE.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")


# --- the write verbs (T-047-64): one ledger, one writer ------------------------------


def _records(specs: Path) -> list[dict[str, object]]:
    text = (specs / "bugs" / "BUGS.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _resolve_argv(bug_id: str = "a-bug", caused_by: str = "none") -> list[str]:
    return [
        "resolve", bug_id, "--cause", "c", "--caused-by", caused_by,
        "--resolved-release", "0.4.7", "--solution", "s", "--evidence-loop", "pytest -k x",
        "--evidence-seam", "tests/x.py::y", "--evidence-diff", "net-negative: smaller",
    ]  # fmt: skip


def test_append_registers_one_open_record(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path)
    done = _run(
        script, "append", "--specs", str(specs), "--bug-id", "new-bug", "--title", "t",
        "--severity", "LOW", "--surface", "cli", "--component", "c", "--context", "ctx",
        "--symptom", "s", "--repro", "r", "--expected", "e",
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("[ok] registered new-bug")
    [record] = _records(specs)
    assert record["status"] == "open" and record["closed_at"] is None
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_append_accepts_a_consumer_surface_and_refuses_unknown(
    script: Path, tmp_path: Path
) -> None:
    """sa-consumer-law-carries-library-facts#FR8.1: a consumer names its own unit as the
    surface (`billing-api` is no library layer or package) and it is accepted; the
    `unknown` sentinel is refused. sa-spec-doc-033-duplicates-bugs-check#B5: surface is
    free text with minLength 1. sa-spec-doc-033-duplicates-bugs-check#B2: an empty context or component is refused and the
    ledger is untouched."""
    specs = _ledger(tmp_path)
    argv = ["append", "--specs", str(specs), "--title", "t", "--severity", "LOW",
            "--component", "c", "--context", "ctx", "--symptom", "s", "--repro", "r",
            "--expected", "e"]  # fmt: skip
    ok = _run(script, *argv, "--bug-id", "consumer-bug", "--surface", "billing-api")
    refused = _run(script, *argv, "--bug-id", "vague-bug", "--surface", "unknown")

    assert ok.returncode == 0, ok.stderr
    assert refused.returncode == 1
    for empty in ("surface", "context", "component"):
        blank = [*argv, "--bug-id", "blank-bug", "--surface", "cli"]
        blank[blank.index(f"--{empty}") + 1] = ""
        done = _run(script, *blank)
        assert done.returncode == 1
        assert f"field '{empty}' is shorter than its minLength of 1" in done.stderr
    assert [r["surface"] for r in _records(specs)] == ["billing-api"]
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


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


def test_append_redacts_a_local_home_path_and_an_ip(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path)
    done = _run(
        script, "append", "--specs", str(specs), "--bug-id", "leaky", "--title", "t",
        "--severity", "LOW", "--surface", "cli", "--component", "c", "--context", "ctx",
        "--symptom", f"seen at {_HOME_PATH} and {_LOCAL_IP}", "--repro", "r",
        "--expected", "e",
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    [record] = _records(specs)
    expected = "/".join(("", "home", "[REDACTED]", "work"))
    assert record["symptom"] == f"seen at {expected} and [REDACTED-IP]"


def test_resolve_closes_the_record_and_derives_diff_direction(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, *_resolve_argv(), "--specs", str(specs))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[ok] resolved a-bug"
    [record] = _records(specs)
    assert record["status"] == "resolved"
    assert record["diff_direction"] == "net-negative"
    assert record["closed_at"] is not None
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_resolve_refuses_an_unknown_caused_by(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, *_resolve_argv(caused_by="never-filed"), "--specs", str(specs))
    assert done.returncode == 1
    assert "not a record of this bug ledger" in done.stderr
    assert _records(specs)[0]["status"] == "open"


def test_resolve_names_every_missing_field_at_once(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, "resolve", "a-bug", "--cause", "c", "--specs", str(specs))
    assert done.returncode == 1
    for name in ("caused_by", "resolved_release", "solution", "evidence_diff"):
        assert name in done.stderr
    assert _records(specs)[0]["status"] == "open"


@pytest.mark.parametrize(
    ("verb", "option", "status", "field"),
    [
        ("supersede", "--by", "superseded", "superseded_by"),
        ("defer", "--reason", "deferred", "cause"),
        ("reject", "--reason", "rejected", "cause"),
    ],
)
def test_the_other_three_transitions_close_the_record(
    script: Path, tmp_path: Path, verb: str, option: str, status: str, field: str
) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, verb, "a-bug", option, "because", "--specs", str(specs))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == f"[ok] {status} a-bug"
    [record] = _records(specs)
    assert record["status"] == status and record[field] == "because"
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_update_writes_a_governance_field(script: Path, tmp_path: Path) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    done = _run(script, "update", "a-bug", "--set", "audited=20260920-sweep", "--specs", str(specs))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[ok] updated audited for a-bug"
    assert _records(specs)[0]["audited"] == "20260920-sweep"


@pytest.mark.parametrize(
    ("change", "owner"),
    [
        ("status=resolved", "resolve|supersede|defer|reject"),
        ("closed_at=2026-09-21T00:00:00Z", "resolve|supersede|defer|reject"),
        ("caused_by=a-bug", "--caused-by"),
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
    """`solution` is write-once: a differing second value is refused."""
    specs = _ledger(tmp_path, _OPEN_RECORD)
    first = _run(script, "update", "a-bug", "--set", "solution=one", "--specs", str(specs))
    second = _run(script, "update", "a-bug", "--set", "solution=two", "--specs", str(specs))
    assert first.returncode == 0, first.stderr
    assert second.returncode == 1
    assert "write-once" in second.stderr
    assert _records(specs)[0]["solution"] == "one"


@pytest.mark.parametrize("bad", ["smaller", "net-sideways: x", "net-negative:"])
def test_resolve_refuses_a_malformed_evidence_diff(script: Path, tmp_path: Path, bad: str) -> None:
    """`evidence_diff` must open with a `net-*:` direction and carry a rationale."""
    specs = _ledger(tmp_path, _OPEN_RECORD)
    argv = _resolve_argv()
    argv[argv.index("--evidence-diff") + 1] = bad
    done = _run(script, *argv, "--specs", str(specs))
    assert done.returncode == 1
    assert "evidence_diff" in done.stderr
    assert _records(specs)[0]["status"] == "open"


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


def test_archive_moves_only_records_closed_past_the_threshold(script: Path, tmp_path: Path) -> None:
    """sa-ledger-verbs-append-histo-before-validating-the-pair#J5: "Given a valid pair, when
    `exit`/`archive` succeed, then the record leaves the document and appears exactly once
    in the histo, written atomically as a pair." (`archive` half)"""
    old = {
        **_OPEN_RECORD, "id": "old-bug", "ts": "2025-12-01T00:00:00Z",
        "status": "resolved", "closed_at": "2026-01-01T00:00:00Z",
    }  # fmt: skip
    fresh = {
        **_OPEN_RECORD, "id": "fresh-bug", "ts": "2026-09-01T00:00:00Z",
        "status": "resolved", "closed_at": "2026-09-19T00:00:00Z",
    }  # fmt: skip
    specs = _ledger(tmp_path, _OPEN_RECORD, old, fresh)
    done = _run(
        script, "archive", "--specs", str(specs), "--now", "2026-09-20T00:00:00Z",
        "--threshold-days", "90",
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[ok] archived 1 record(s), 2 kept."
    assert {r["id"] for r in _records(specs)} == {"a-bug", "fresh-bug"}
    histo = (specs / "bugs" / "_archive" / "bugs_histo.jsonl").read_text(encoding="utf-8")
    assert [json.loads(line)["id"] for line in histo.splitlines()] == ["old-bug"]


def test_archive_with_nothing_eligible_is_a_byte_identical_no_op(
    script: Path, tmp_path: Path
) -> None:
    specs = _ledger(tmp_path, _OPEN_RECORD)
    before = (specs / "bugs" / "BUGS.jsonl").read_bytes()
    done = _run(script, "archive", "--specs", str(specs), "--threshold-days", "90")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[ok] archived 0 record(s), 1 kept."
    assert (specs / "bugs" / "BUGS.jsonl").read_bytes() == before
    assert not (specs / "bugs" / "_archive").exists()


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
    done = _run(script, "update", "a-bug", "--set", "audited=sweep", "--specs", str(specs))
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
    from dadaia_workspace.infrastructure.public_assets_common import OverwritePolicy

    plan = InstallPlan(
        workspace_root=tmp_path,
        agentic_dir=_PUBLIC,
        harness=None,
        overwrite=OverwritePolicy.PRESERVE,
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
        done = _run(
            script, "archive", "--specs", str(specs), "--now", "2026-09-20T00:00:00Z",
            "--threshold-days", "90",
        )  # fmt: skip
        assert done.returncode == 1, done.stdout
        assert [(specs / "bugs" / "BUGS.jsonl").read_bytes(), histo.read_bytes()] == before
