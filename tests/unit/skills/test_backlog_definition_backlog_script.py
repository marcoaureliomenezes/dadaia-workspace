"""Intent: CONTRACT — dd-backlog-definition/scripts/backlog.py owns BACKLOG.json and its
histo (0.4.7 c7 T-047-65: the backlog ledger verbs move into a stdlib skill script).
Size: SMALL.

The script reads its two schemas from ``scripts/schemas/`` BESIDE itself — copies
`public stage` makes — so every test stages the trio exactly as stage does.
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
_SCRIPTS = _PUBLIC / "skills" / "dd-backlog-definition" / "scripts"
_SOURCE = _SCRIPTS / "backlog.py"
_SCHEMAS = (
    _PUBLIC / "schemas" / "backlog" / "backlog-v1.schema.json",
    _PUBLIC / "schemas" / "histo" / "histo-record-v1.schema.json",
)


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: backlog.py with both schema copies beside it."""
    staged = tmp_path / "staged" / "scripts"
    (staged / "schemas").mkdir(parents=True)
    for module in sorted(_SCRIPTS.glob("*.py")):
        shutil.copy2(module, staged / module.name)
    for schema in _SCHEMAS:
        shutil.copy2(schema, staged / "schemas" / schema.name)
    return staged / "backlog.py"


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
    path = specs / "backlog" / "_archive" / "backlog_histo.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _picked(specs: Path, slug: str) -> None:
    """Mature an entry to the one status a release-lane exit accepts."""
    document = json.loads((specs / "backlog" / "BACKLOG.json").read_text(encoding="utf-8"))
    for item in document["active"]:
        if item["id"] == slug:
            item["status"] = "picked"
    (specs / "backlog" / "BACKLOG.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )


def _release(specs: Path, release_id: str = "0.4.7") -> None:
    (specs / "releases" / release_id).mkdir(parents=True, exist_ok=True)


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


def test_missing_specs_above_cwd_is_refused_with_one_fix_line(script: Path, tmp_path: Path) -> None:
    lonely = tmp_path / "nowhere"
    lonely.mkdir()
    done = _run(script, "check", cwd=lonely)
    assert done.returncode == 1
    assert len(_fix_lines(done)) == 1
    assert "--specs" in _fix_lines(done)[0]


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
    specs = _specs(tmp_path)
    _release(specs)
    assert _run(script, "new", "an-idea", "--specs", str(specs)).returncode == 0
    _picked(specs, "an-idea")
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
    _release(specs)
    _run(script, "new", "an-idea", "--specs", str(specs))
    _picked(specs, "an-idea")
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
    assert "backlog.py" in fixes[0] or "backlog_histo.jsonl" in fixes[0]
    assert len(_histo(specs)) == 1


def test_delivered_on_a_non_picked_entry_is_refused(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _release(specs)
    _run(script, "new", "an-idea", "--specs", str(specs))
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "delivered", "--release", "0.4.7",
    )  # fmt: skip
    assert done.returncode == 1
    assert "picked" in done.stdout + done.stderr
    assert len(_active(specs)) == 1
    assert _histo(specs) == []


def test_delivered_without_a_known_release_is_refused(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    _picked(specs, "an-idea")
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "delivered", "--release", "9.9.9",
    )  # fmt: skip
    assert done.returncode == 1
    assert len(_active(specs)) == 1


def test_rejected_requires_a_reason(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    done = _run(script, "exit", "an-idea", "--specs", str(specs), "--disposition", "rejected")
    assert done.returncode == 1
    assert len(_active(specs)) == 1
    ok = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "rejected", "--reason", "no release ever took it",
    )  # fmt: skip
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert _histo(specs)[0]["reason"] == "no release ever took it"


def test_bl_conflict_fix_line_runs_as_printed(script: Path, tmp_path: Path) -> None:
    """Intent: CONTRACT — 0.4.7 c8 review MEDIUM-4.

    BL-CONFLICT's own ``fix:`` line, run verbatim against the two-twin shape it
    diagnoses, must clear the finding. It printed ``--disposition superseded --reason
    <the-twin-slug>`` while ``_backlog_exit.REQUIRED_EVIDENCE`` binds ``superseded`` to
    ``--release``: the one remedy the operator was handed refused itself.
    """
    from dadaia_workspace.features.backlog.doctor import RULES

    fix = next(rule.fix_help for rule in RULES if rule.codes == ("BL-CONFLICT",))
    assert fix is not None
    specs = _specs(tmp_path)
    for slug in ("a-twin", "its-divergent-twin"):
        assert _run(script, "new", slug, "--specs", str(specs)).returncode == 0

    argv = fix.split()[2:]  # drop the interpreter and the script path
    argv = [str(specs) if token == "specs" else token for token in argv]
    argv = ["a-twin" if token == "<slug>" else token for token in argv]
    argv = ["its-divergent-twin" if token == "<the-twin-slug>" else token for token in argv]
    done = _run(script, *argv, "--specs", str(specs))
    assert done.returncode == 0, f"BL-CONFLICT's own fix line refuses:\n{fix}\n{done.stderr}"
    assert [item["id"] for item in _active(specs)] == ["its-divergent-twin"]
    assert _histo(specs)[0]["reason"] == "its-divergent-twin"


def test_exit_refuses_a_disposition_outside_the_backlog_vocabulary(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    _run(script, "new", "an-idea", "--specs", str(specs))
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs), "--disposition", "resolved",
        "--reason", "r",
    )  # fmt: skip
    assert done.returncode == 1
    assert len(_active(specs)) == 1


def test_exit_redacts_an_operator_local_path_from_the_histo_record(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    home = "/".join(("", "home", "someone", "work"))
    _run(script, "new", "an-idea", "--specs", str(specs), "--description", f"seen at {home}")
    done = _run(
        script, "exit", "an-idea", "--specs", str(specs),
        "--disposition", "rejected", "--reason", f"found under {home}",
    )  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    line = (specs / "backlog" / "_archive" / "backlog_histo.jsonl").read_text(encoding="utf-8")
    assert "someone" not in line
    assert "[REDACTED]" in line


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


def test_check_reports_a_terminal_status_in_active(script: Path, tmp_path: Path) -> None:
    specs = _specs(
        tmp_path,
        {
            "id": "gone",
            "title": "t",
            "opened": "2026-09-20",
            "status": "delivered",
            "description": "d",
            "provenance": "operator request",
        },  # fmt: skip
    )
    done = _run(script, "check", "--specs", str(specs))
    assert done.returncode == 1
    assert "delivered" in done.stdout


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


# --- subjects ------------------------------------------------------------------------


def _aliases(root: Path, *lines: str) -> Path:
    path = root / ".dadaia" / "states" / "backlog_subject_aliases.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# a comment\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_subjects_lists_the_alias_map_anchors(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    aliases = _aliases(tmp_path, "panel:/api/thing -> panel:/api/thing")
    done = _run(script, "subjects", "--specs", str(specs), "--alias-map", str(aliases))
    assert done.returncode == 0, done.stdout + done.stderr
    assert "panel:/api/thing" in done.stdout


def test_subjects_resolves_a_bound_subject(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    aliases = _aliases(tmp_path, "the-thing -> panel:/api/thing")
    done = _run(
        script, "subjects", "--specs", str(specs), "--alias-map", str(aliases),
        "--resolve", "the-thing", "--kind", "panel",
    )  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    assert "RESOLVED" in done.stdout
    assert "panel:/api/thing" in done.stdout


def test_subjects_refuses_an_unresolved_subject(script: Path, tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    aliases = _aliases(tmp_path, "the-thing -> panel:/api/thing")
    done = _run(
        script, "subjects", "--specs", str(specs), "--alias-map", str(aliases),
        "--resolve", "nothing-like-it", "--kind", "panel",
    )  # fmt: skip
    assert done.returncode == 1
    assert "UNRESOLVED" in done.stdout + done.stderr


def test_subjects_lists_the_subjects_the_live_document_already_binds(
    script: Path, tmp_path: Path
) -> None:
    specs = _specs(tmp_path)
    _run(
        script, "new", "an-idea", "--specs", str(specs),
        "--intent", "code:dadaia_workspace/container.py#build=wire it",
    )  # fmt: skip
    done = _run(script, "subjects", "--specs", str(specs), "--alias-map", str(tmp_path / "none"))
    assert done.returncode == 0, done.stdout + done.stderr
    assert "dadaia_workspace/container.py#build" in done.stdout
