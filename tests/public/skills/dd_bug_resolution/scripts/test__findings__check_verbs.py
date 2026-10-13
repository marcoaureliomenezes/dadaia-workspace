"""The five check verbs share one finding renderer and one decode-aware reader.
Size: MEDIUM.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import git_line
from tests.helpers.skill_scripts import stage_skill_scripts

# verb: (skill, script, code, a tree the verb flags, a file whose bytes are not UTF-8)
_VERBS = {
    "audit": ("dd-audit-project", "audit.py", "LEDGER-FINDINGS-SCHEMA",
              ("audits/_archive/audits_histo.jsonl", b"not json\n"), "audits/20260101-w/FINDINGS.jsonl"),
    "bugs": ("dd-bug-resolution", "bugs.py", "LEDGER-BUGS-SCHEMA",
             ("bugs/BUGS.jsonl", b"not json\n"), "bugs/BUGS.jsonl"),
    "backlog": ("dd-backlog-definition", "backlog.py", "LEDGER-BACKLOG-SCHEMA",
                ("backlog/_archive/backlog_histo.jsonl", b"not json\n"), "backlog/BACKLOG.json"),
    "memory": ("dd-spec-navigator", "memory.py", "LEDGER-MEMORY-SCHEMA",
               ("memory/.keep", b""), "memory/product/area/x.md"),
    "release": ("dd-release-implementation", "release.py", "LEDGER-RELEASE-SCHEMA",
                ("releases/0.5.0/.keep", b""), "releases/0.5.0/_RELEASE.json"),
}  # fmt: skip


def _restore(path: Path) -> str:
    return f"Operator action: restore {path} with `{git_line(path.parent, 'checkout', '--', path.name)}`"


def _check(tmp_path: Path, verb: str, planted: tuple[str, bytes]):
    """A runner of ``check`` over a specs tree holding only *planted*."""
    skill, name, *_ = _VERBS[verb]
    script = stage_skill_scripts(skill, tmp_path / "staged" / "scripts") / name
    specs = tmp_path / "repo" / "specs"
    target = specs / planted[0]
    target.parent.mkdir(parents=True)
    target.write_bytes(planted[1])
    return lambda *flags: subprocess.run(
        [sys.executable, str(script), "check", "--specs", str(specs), *flags],
        capture_output=True, check=False, text=True,
    )  # fmt: skip


@pytest.mark.parametrize("verb", _VERBS)
def test_text_mode_prints_each_findings_fix_after_it(tmp_path: Path, verb: str) -> None:
    run = _check(tmp_path, verb, _VERBS[verb][3])
    as_json, as_text = run("--json"), run()

    findings = json.loads(as_json.stdout)
    assert as_text.returncode == 1 and findings
    lines = as_text.stdout.splitlines()
    for finding in findings:
        at = next(i for i, line in enumerate(lines) if finding["message"] in line)
        assert lines[at + 1] == f"fix: {finding['fix']}"


@pytest.mark.parametrize("verb", _VERBS)
def test_a_file_that_is_not_utf8_is_a_finding_of_the_verbs_own_code(
    tmp_path: Path, verb: str
) -> None:
    code, relative = _VERBS[verb][2], _VERBS[verb][4]
    done = _check(tmp_path, verb, (relative, b"\xff\xfe\n"))("--json")

    assert done.returncode == 1 and "Traceback" not in done.stderr
    (finding,) = json.loads(done.stdout)
    assert (finding["code"], finding["verdict"], finding["path"]) == (code, "error", relative)
    target = (tmp_path / "repo" / "specs" / relative).resolve()
    assert finding["fix"] == _restore(target)


# verb: (skill, script, argv after the script, the file whose bytes are not UTF-8)
_WRITERS = {
    "bugs": ("dd-bug-resolution", "bugs.py", ["status"], "bugs/BUGS.jsonl"),
    "backlog": ("dd-backlog-definition", "backlog.py",
                ["exit", "x", "--disposition", "delivered"], "backlog/BACKLOG.json"),
    "audit": ("dd-audit-project", "audit.py",
              ["disposition", "20260101-w", "20260101-w-F001", "--disposition", "resolved", "--release", "0.5.0"],
              "audits/20260101-w/FINDINGS.jsonl"),
    "memory": ("dd-spec-navigator", "memory.py", ["catalog", "generate"],
               "memory/product/area/x.md"),
}  # fmt: skip


@pytest.mark.parametrize("verb", _WRITERS)
def test_a_verb_that_reads_a_file_that_is_not_utf8_refuses_with_one_fix(
    tmp_path: Path, verb: str
) -> None:
    skill, name, argv, relative = _WRITERS[verb]
    script = stage_skill_scripts(skill, tmp_path / "staged" / "scripts") / name
    specs = tmp_path / "repo" / "specs"
    (specs / relative).parent.mkdir(parents=True)
    (specs / relative).write_bytes(b"\xff\xfe\n")
    done = subprocess.run(
        [sys.executable, str(script), *argv, "--specs", str(specs)],
        capture_output=True, check=False, text=True,
    )  # fmt: skip

    assert done.returncode == 1 and "Traceback" not in done.stderr
    assert relative in done.stderr
    assert [ln for ln in done.stderr.splitlines() if ln.startswith("fix: ")] == [
        f"fix: {_restore((specs / relative).resolve())}"
    ]


@pytest.mark.parametrize(
    "relative",
    ["bugs/BUGS.jsonl", "releases/0.5.0/rc-1/PLAN.md", "releases/0.5.0/rc-1/tasks/job1.md"],
)
def test_a_release_check_names_the_undecodable_file_and_not_the_spec_it_was_reached_from(
    tmp_path: Path, relative: str
) -> None:
    specs = tmp_path / "repo" / "specs"
    rc = specs / "releases" / "0.5.0" / "rc-1"
    (rc / "tasks").mkdir(parents=True)
    (rc / "SPEC.md").write_text("# S\n\n**Status:** Approved\n**Origin:** bugs:x\n\n", "utf-8")
    (rc / "PLAN.md").write_text("# P\n\n**Status:** Approved\n\n", "utf-8")
    state = {"schema": "release-state-v1", "release": "0.5.0", "phase": "DEFINITION",
             "defined": None, "implemented": None, "shipped": None, "log": []}  # fmt: skip
    (specs / "releases" / "0.5.0" / "_RELEASE.json").write_text(json.dumps(state), "utf-8")
    (specs / "bugs").mkdir()
    (specs / "bugs" / "BUGS.jsonl").write_text("", "utf-8")
    (specs / relative).write_bytes(b"\xff\xfe\n")
    script = stage_skill_scripts("dd-release-implementation", tmp_path / "staged" / "scripts")
    done = subprocess.run(
        [sys.executable, str(script / "release.py"), "check", "--specs", str(specs), "--json"],
        capture_output=True, check=False, text=True,
    )  # fmt: skip

    assert done.returncode == 1 and "Traceback" not in done.stderr
    assert [f["path"] for f in json.loads(done.stdout)] == [relative]


def test_the_origin_verb_names_a_spec_that_is_not_utf8_once(tmp_path: Path) -> None:
    script = stage_skill_scripts("dd-release-implementation", tmp_path / "staged" / "scripts")
    spec = tmp_path / "SPEC.md"
    spec.write_bytes(b"\xff\xfe\n")
    done = subprocess.run(
        [sys.executable, str(script / "release.py"), "origin", str(spec)],
        capture_output=True, check=False, text=True,
    )  # fmt: skip

    assert done.returncode == 1
    assert done.stderr == f"[error] {spec} is not valid UTF-8\nfix: {_restore(spec.resolve())}\n"
