"""Intent: CONTRACT — dd-backlog-definition/scripts/backlog.py owns BACKLOG.json and its
histo (0.4.7 c7 T-047-65: the backlog ledger verbs move into a stdlib skill script).
Size: SMALL.

The script reads its two schemas from ``scripts/schemas/`` BESIDE itself — copies
`public stage` makes — so every test stages the trio exactly as stage does.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.ledger_scripts import load_owner
from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_SCRIPTS = _PUBLIC / "skills" / "dd-backlog-definition" / "scripts"
_SOURCE = _SCRIPTS / "backlog.py"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: backlog.py with both schema copies beside it, and the release
    and bug skills beside it, whose Origin parser and bug reader `exit` imports (ADR 0161)."""
    for owner in ("dd-release-implementation", "dd-bug-resolution"):
        stage_skill_scripts(owner, tmp_path / "skills" / owner / "scripts")
    skill = tmp_path / "skills" / "dd-backlog-definition" / "scripts"
    return stage_skill_scripts("dd-backlog-definition", skill) / "backlog.py"


def _specs(root: Path, *active: dict[str, object]) -> Path:
    specs = root / "specs"
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    (specs / "backlog" / "BACKLOG.json").write_text(
        json.dumps({"schema": "backlog-v1", "active": list(active)}, indent=2) + "\n",
        encoding="utf-8",
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


def _active(specs: Path) -> list[dict[str, object]]:
    document = json.loads((specs / "backlog" / "BACKLOG.json").read_text(encoding="utf-8"))
    items: list[dict[str, object]] = document["active"]
    return items


def _histo(specs: Path) -> list[dict[str, object]]:
    return load_owner("dd-bug-resolution", "_ledger").records(
        specs / "backlog" / "_archive" / "backlog_histo.jsonl"
    )


def _pick(specs: Path, origin: str = "backlog:an-idea") -> None:
    """The pick: `release.py new 0.4.7 --origin <origin>`, no hand edit of BACKLOG.json."""
    release = _PUBLIC / "skills" / "dd-release-implementation" / "scripts" / "release.py"
    done = _run(release, "new", "0.4.7", "--origin", origin, "--specs", str(specs))
    assert done.returncode == 0, done.stdout + done.stderr


def _fix_lines(done: subprocess.CompletedProcess[str]) -> list[str]:
    return [ln for ln in (done.stdout + done.stderr).splitlines() if ln.startswith("fix:")]


# --- the script contract ------------------------------------------------------------


def test_script_is_executable_and_has_a_shebang() -> None:
    assert os.access(_SOURCE, os.X_OK)
    assert _SOURCE.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")


def test_clean_document_checks_green(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 0, done.stdout + done.stderr


def test_absent_document_is_not_a_finding(script: Path, tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


# --- new ----------------------------------------------------------------------------


def test_new_appends_one_active_entry(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    done = _run(
        script, "new", "an-idea", "--specs", str(specs),
        "--title", "An idea", "--description", "what it needs", "--provenance", "operator request",
    )  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    (entry,) = _active(specs)
    assert entry["id"] == "an-idea"
    assert entry["title"] == "An idea"
    assert entry["status"] == "idea"
    assert entry["provenance"] == "operator request"


def test_new_refuses_a_duplicate_slug_with_one_fix_line(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    assert _run(script, "new", "an-idea", "--specs", str(specs)).returncode == 0
    done = _run(script, "new", "an-idea", "--specs", str(specs))
    assert done.returncode == 1
    assert len(_fix_lines(done)) == 1
    assert "backlog.py" in _fix_lines(done)[0]
    assert len(_active(specs)) == 1


def test_a_refused_positional_drops_only_itself_never_an_equal_flag_value(
    script: Path, tmp_path: Path
) -> None:
    """Intent: CONTRACT — AC4.4 (T-050-151 review LOW 1): the invalid slug leaves the quoted
    command; a flag value spelled the same stays with its flag."""
    done = _run(script, "new", "Bad", "--title", "Bad", "--specs", str(_specs(tmp_path)))
    (fix,) = _fix_lines(done)
    assert " new --title Bad --specs " in fix.split("`")[1], fix


def test_new_names_the_live_entries_it_relates_to(script: Path, tmp_path: Path) -> None:
    """ADR 0127 / AC1.12: past the first entry, `new` refuses without `--relates`, listing
    the live entries, and always refuses a slug that is not one; the named ones are recorded."""
    specs = _specs(tmp_path)
    assert _run(script, "new", "first", "--specs", str(specs), "--relates", "ghost").returncode == 1
    assert _run(script, "new", "first", "--specs", str(specs)).returncode == 0
    bare = _run(script, "new", "second", "--specs", str(specs))
    stray = _run(script, "new", "second", "--specs", str(specs), "--relates", "ghost")
    assert bare.returncode == stray.returncode == 1
    assert "relates to (ADR 0127): first\n" in bare.stderr
    assert (
        _run(script, "new", "second", "--specs", str(specs), "--relates", "first").returncode == 0
    )
    assert _active(specs)[-1]["relates"] == ["first"]


def test_new_refuses_a_malformed_slug(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    done = _run(script, "new", "Not A Slug", "--specs", str(specs))
    assert done.returncode == 1
    assert _active(specs) == []


def test_new_records_typed_intents(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    done = _run(
        script, "new", "an-idea", "--specs", str(specs),
        "--intent", "code:dadaia_workspace/container.py#build=wire the script",
    )  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    (entry,) = _active(specs)
    assert entry["intents"] == [
        {
            "subject": {"kind": "code", "ref": "dadaia_workspace/container.py#build"},
            "change": "wire the script",
        }
    ]


# --- exit: once-only and terminal ---------------------------------------------------


def test_exit_moves_the_entry_to_the_histo_exactly_once(script: Path, tmp_path: Path) -> None:
    """sa-ledger-verbs-append-histo-before-validating-the-pair#J5: "Given a valid pair, when
    `exit`/`archive` succeed, then the record leaves the document and appears exactly once
    in the histo, written atomically as a pair." (`exit` half)
    sa-backlog-status-has-no-single-authority#B4: `release.py new --origin backlog:<slug>`,
    then `exit --disposition delivered`, exits 0 with no hand edit. sa-backlog-status-has-no-single-authority#B6: until then the
    picked item stays live with its status unchanged."""
    specs = _specs(tmp_path)
    assert _run(script, "new", "an-idea", "--specs", str(specs)).returncode == 0
    _pick(specs)
    assert [e["status"] for e in _active(specs)] == ["idea"]
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "delivered", "--release", "0.4.7",
    )  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    assert _active(specs) == []
    (record,) = _histo(specs)
    assert record["id"] == "an-idea"
    assert record["disposition"] == "delivered"
    assert record["release"] == "0.4.7"
    assert isinstance(record["entry"], dict)
    assert record["entry"]["id"] == "an-idea"


def test_a_second_exit_exits_one_with_a_fix_naming_the_script(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    _pick(specs)
    _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "delivered", "--release", "0.4.7",
    )  # fmt: skip
    again = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "delivered", "--release", "0.4.7",
    )  # fmt: skip
    assert again.returncode == 1
    fixes = _fix_lines(again)
    assert len(fixes) == 1
    assert fixes == ["fix: grep an-idea specs/backlog/_archive/backlog_histo.jsonl"]
    assert len(_histo(specs)) == 1


@pytest.mark.parametrize("release", ["0.4.7", "9.9.9"])
def test_delivered_outside_the_release_origin_is_refused(
    script: Path, tmp_path: Path, release: str
) -> None:
    """sa-backlog-status-has-no-single-authority#B5: delivered on a slug outside Origin
    is refused, and the fix never suggests rejected."""
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    _pick(specs, "operator-demand")
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "delivered", "--release", release,
    )  # fmt: skip
    assert done.returncode == 1
    [fix] = _fix_lines(done)
    assert "rejected" not in fix and "<" not in fix  # ADR 0158: no placeholder
    assert len(_active(specs)) == 1
    assert _histo(specs) == []


def test_the_refusal_fix_names_the_latest_picking_release_by_version(
    script: Path, tmp_path: Path
) -> None:
    """Review F8: 0.10.0 is later than 0.9.0, though it sorts before it as text."""
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    for release in ("0.9.0", "0.10.0"):
        (specs / f"releases/{release}/rc-1").mkdir(parents=True)
        (specs / f"releases/{release}/rc-1/SPEC.md").write_text("**Origin:** backlog:an-idea\n")
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "delivered", "--release", "9.9.9",
    )  # fmt: skip
    [fix] = _fix_lines(done)
    assert fix.split(" --specs ")[0].endswith("--disposition delivered --release 0.10.0")


@pytest.mark.parametrize(
    ("origin", "code"),
    [
        ("**Origin:** operator-demand\n**Origin:** backlog:an-idea", 1),
        ("**Origin:** backlog:an-idea; bugs:a-bug", 0),
    ],
    ids=["a-second-origin-line-does-not-count", "a-multi-clause-line-parses"],
)
def test_exit_reads_origin_through_the_release_parser(
    script: Path, tmp_path: Path, origin: str, code: int
) -> None:
    """spec-origin-line-has-two-readers: only the first Origin line counts, and a
    clause line parses (ADR 0161) — `exit` asks `release.py`'s one parser."""
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    _pick(specs, "operator-demand")
    spec = specs / "releases/0.4.7/rc-1/SPEC.md"
    spec.write_text(spec.read_text("utf-8").replace("**Origin:** operator-demand", origin), "utf-8")
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "delivered", "--release", "0.4.7",
    )  # fmt: skip
    assert done.returncode == code, done.stdout + done.stderr


def test_rejected_requires_a_reason(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    done = _run(script, "exit", "an-idea", "--specs", str(specs), "--disposition", "rejected")
    assert done.returncode == 1
    [fix] = _fix_lines(done)
    assert fix.startswith("fix: Operator action:") and "--disposition rejected" in fix
    assert len(_active(specs)) == 1
    ok = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "rejected", "--reason", "no release ever took it",
    )  # fmt: skip
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert _histo(specs)[0]["reason"] == "no release ever took it"


@pytest.mark.parametrize(
    ("disposition", "evidence"),
    [("superseded", ["--release", "9.9.9"]), ("rejected", []), ("to-bug", [])],
)
def test_each_refusal_fix_keeps_the_chosen_disposition(
    script: Path, tmp_path: Path, disposition: str, evidence: list[str]
) -> None:
    """T-050-138 review F1: a picked entry refused for its evidence gets the fix of THAT
    evidence row — never a `delivered` exit the operator did not choose (#B5 class).
    A runnable fix runs as printed and exits under the chosen disposition (ADR 0158)."""
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    _pick(specs)
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs), "--disposition", disposition, *evidence
    )
    assert done.returncode == 1
    [fix] = _fix_lines(done)
    assert "delivered" not in fix and "<" not in fix
    if fix.startswith("fix: Operator action:"):
        assert f"--disposition {disposition}" in fix
        assert ("bugs.py append" in fix) == (disposition == "to-bug")
        assert _histo(specs) == []
        return
    ran = subprocess.run(shlex.split(fix.removeprefix("fix: ")), capture_output=True, check=False)
    assert ran.returncode == 0, ran.stderr
    assert [r["disposition"] for r in _histo(specs)] == [disposition]


def test_a_deferred_exit_is_refused_and_the_entry_stays_live(script: Path, tmp_path: Path) -> None:
    """Operator ruling 2026-10-01 (T-050-138 review F4): `deferred` is no backlog word —
    a postponed item stays in active[] and needs no exit; nothing is written."""
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    _pick(specs)
    done = _run(script, "exit", "an-idea", "--specs", str(specs), "--disposition", "deferred")
    assert done.returncode == 1
    assert _fix_lines(done) == [
        "fix: Operator action: a postponed item stays in active[] and needs no exit."
    ]
    assert len(_active(specs)) == 1
    assert _histo(specs) == []


@pytest.mark.parametrize(("bug", "code"), [("a-bug", 0), ("no-such-bug", 1)])
def test_to_bug_exits_only_into_a_registered_bug(
    script: Path, tmp_path: Path, bug: str, code: int
) -> None:
    """AC3.12 (ADR 0137): `to-bug` exits when --reason names a BUGS.jsonl record, an
    unknown id is refused with nothing written, and `check` accepts the record."""
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    (specs / "bugs").mkdir()
    (specs / "bugs" / "BUGS.jsonl").write_text(json.dumps({"id": "a-bug"}) + "\n", "utf-8")
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs), "--disposition", "to-bug",
        "--reason", bug,
    )  # fmt: skip
    assert done.returncode == code, done.stdout + done.stderr
    assert len(_active(specs)) == code
    assert [r["reason"] for r in _histo(specs)] == [bug] * (1 - code)
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_new_and_exit_refuse_a_value_the_push_refuses(script: Path, tmp_path: Path) -> None:
    """sa-ledger-write-seam-redacts-less-than-push-refuses#B2: backlog.py new/exit refuse
    a push-matched value, naming the field and the masked term; both files unchanged."""
    specs = _specs(tmp_path)
    home = "/".join(("", "home", "someone", "work"))
    refused_new = _run(script, "new", "leaky", "--specs", str(specs), "--description", home)
    assert _run(script, "new", "an-idea", "--specs", str(specs)).returncode == 0
    before = (specs / "backlog" / "BACKLOG.json").read_bytes()
    refused_exit = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "rejected", "--reason", f"found under {home}",
    )  # fmt: skip
    for done, field in ((refused_new, "description"), (refused_exit, "reason")):
        assert done.returncode == 1
        assert f"field {field!r} carries '/…e'" in done.stderr
    assert [e["id"] for e in _active(specs)] == ["an-idea"]
    assert (specs / "backlog" / "BACKLOG.json").read_bytes() == before
    assert _histo(specs) == []


# --- check: the invariants that need only the two files ------------------------------


def test_check_reports_a_duplicate_active_id(script: Path, tmp_path: Path) -> None:
    entry = {
        "id": "twice", "title": "t", "opened": "2026-09-20", "status": "idea",
        "description": "d", "provenance": "operator request",
    }  # fmt: skip
    specs = _specs(tmp_path, entry, dict(entry))
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    lines = [ln for ln in done.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert lines[0].startswith("LEDGER-BACKLOG-SCHEMA error ")
    assert "duplicate" in lines[0]


@pytest.mark.parametrize("status", ["delivered", "to-bug"])
def test_check_reports_a_terminal_status_in_active(
    script: Path, tmp_path: Path, status: str
) -> None:
    """T-050-138 review F2: every disposition is terminal, `to-bug` included."""
    specs = _specs(
        tmp_path,
        {
            "id": "gone",
            "title": "t",
            "opened": "2026-09-20",
            "status": status,
            "description": "d",
            "provenance": "operator request",
        },  # fmt: skip
    )
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    assert status in done.stdout


def test_check_reports_a_missing_required_field(script: Path, tmp_path: Path) -> None:
    specs = _specs(
        tmp_path,
        {"id": "thin", "title": "t", "opened": "2026-09-20", "status": "idea", "description": "d"},
    )
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    assert "provenance" in done.stdout


def test_check_reports_a_histo_record_off_the_backlog_vocabulary(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    histo = specs / "backlog" / "_archive" / "backlog_histo.jsonl"
    histo.parent.mkdir(parents=True, exist_ok=True)
    histo.write_text(
        json.dumps(
            {
                "id": "x",
                "ts": "2026-09-20",
                "disposition": "resolved",
                "release": None,
                "reason": "r",
                "summary": None,
                "entry": None,
            }  # fmt: skip
        )
        + "\n",
        encoding="utf-8",
    )
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    assert "resolved" in done.stdout


def test_check_json_carries_one_object_per_finding(script: Path, tmp_path: Path) -> None:
    specs = _specs(
        tmp_path,
        {"id": "thin", "title": "t", "opened": "2026-09-20", "status": "idea", "description": "d"},
    )
    done = _run(script, "check", "--specs", str(specs), "--json")
    assert done.returncode == 1
    payload = json.loads(done.stdout)
    assert len(payload) == 1
    assert payload[0]["code"] == "LEDGER-BACKLOG-SCHEMA"
    assert payload[0]["verdict"] == "error"


def test_a_refused_write_leaves_the_document_byte_identical(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    before = (specs / "backlog" / "BACKLOG.json").read_bytes()
    assert _run(script, "new", "an-idea", "--specs", str(specs)).returncode == 1
    assert (specs / "backlog" / "BACKLOG.json").read_bytes() == before


# --- kinds -----------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["panel", "api", "cli"])
def test_new_refuses_a_retired_kind_and_its_fix_lists_the_kinds(
    script: Path, tmp_path: Path, kind: str
) -> None:
    """sa-subjects-resolve-is-circular#B4: `new` refuses a kind outside the four, nothing
    written; T-050-154: its fix line `new --help` lists every kind, and `subjects` is gone."""
    specs = _specs(tmp_path)
    done = _run(script, "new", "x-item", "--specs", str(specs), "--intent", f"{kind}:x=y")
    fix = [line for line in (done.stdout + done.stderr).splitlines() if line.startswith("fix:")]
    assert done.returncode == 1 and _active(specs) == [] and fix, done.stdout + done.stderr
    assert " new --help" in fix[0]
    usage = " ".join(_run(script, "new", "--help").stdout.split())
    assert "code|doc|invariant|catalog" in usage
    assert _run(script, "subjects", "--specs", str(specs)).returncode == 2


def _pair(specs: Path) -> list[bytes]:
    histo = specs / "backlog" / "_archive" / "backlog_histo.jsonl"
    return [(specs / "backlog" / "BACKLOG.json").read_bytes(), histo.read_bytes()]


def _exited(script: Path, tmp_path: Path) -> Path:
    """A tree whose histo holds one exit of `gone` and whose active[] holds `an-idea`."""
    specs = _specs(tmp_path)
    for slug in ("gone", "an-idea"):
        assert _run(script, "new", slug, "--specs", str(specs), "--relates", "none").returncode == 0
    done = _run(
        script, "exit", "gone", "--specs", str(specs), "--disposition", "rejected",
        "--reason", "r",
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    return specs


def test_a_refused_exit_leaves_both_backlog_files_byte_intact(script: Path, tmp_path: Path) -> None:
    """sa-ledger-verbs-append-histo-before-validating-the-pair#J1: "Given BACKLOG.json
    holding an invalid entry (an Idea without intents), when `backlog.py exit <other-slug>`
    runs, then it exits 1 and BACKLOG.json and backlog_histo.jsonl are both
    byte-identical." Run twice: a retry appends nothing either."""
    specs = _exited(script, tmp_path)
    document = json.loads((specs / "backlog" / "BACKLOG.json").read_text(encoding="utf-8"))
    document["active"].append({"id": "broken", "status": "Idea"})
    (specs / "backlog" / "BACKLOG.json").write_text(json.dumps(document), encoding="utf-8")
    before = _pair(specs)

    for _ in range(2):
        done = _run(
            script, "exit", "an-idea", "--specs", str(specs), "--disposition", "rejected",
            "--reason", "r",
        )  # fmt: skip
        assert done.returncode == 1, done.stdout
        assert _pair(specs) == before


def test_new_refuses_a_slug_that_already_exited_and_writes_nothing(
    script: Path, tmp_path: Path
) -> None:
    """sa-ledger-verbs-append-histo-before-validating-the-pair#J3: "Given slug zz already
    exited (a histo record exists), when `backlog.py new zz` runs, then it exits 1 citing
    the earlier exit and writes nothing." The pair check refuses it."""
    specs = _exited(script, tmp_path)
    before = _pair(specs)

    done = _run(script, "new", "gone", "--specs", str(specs), "--relates", "none")

    assert done.returncode == 1, done.stdout
    assert "'gone' exited at this line" in done.stderr
    assert _pair(specs) == before
    assert _run(script, "check", "--specs", str(specs)).returncode == 0
