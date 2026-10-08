"""ADR 0209: the pure `judge` of the test freeze over diff rows, no git. Size: SMALL."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.ledger_scripts import _PACKAGE_SKILLS, load_owner
from tests.helpers.worktree_ws import git

sys.path.insert(0, str(_PACKAGE_SKILLS / "dd-gitflow-default" / "scripts"))
freeze = load_owner("dd-gitflow-default", "_worktree_freeze")
RED = re.compile(r"^@red$")
T = "tests/test_a.py"


def row(sha: str, subject: str, *, code: bool = False, edits: tuple = ()) -> object:
    tests = frozenset({T}) if edits else frozenset()
    paths = tests | ({"src/a.py"} if code else set())
    return freeze.Commit(sha, subject, paths, tests, edits)


S1 = row("c1", "test(J1.S1.T1): red", edits=((T, (), 2),))


def test_no_rows_judge_nothing() -> None:
    assert freeze.judge([], "base", None) is None


def test_a_rename_has_no_hunks_and_lands() -> None:
    rows = [S1, row("c2", "feat(J1.S2.T1): code", code=True), row("c3", "chore(J1.S2.T2): mv")]
    assert freeze.judge(rows, "base", None) is None


def test_a_deleted_file_past_the_anchor_refuses_with_the_anchor() -> None:
    rows = [S1, row("c2", "feat(J1.S2.T1): rm", edits=((T, ("def test_a():", "pass"), 0),))]
    assert freeze.judge(rows, "base", None) == (T, "c1")


def test_a_file_born_in_stage_two_then_edited_refuses() -> None:
    rows = [
        S1,
        row("c2", "feat(J1.S2.T1): code", code=True, edits=((T, (), 3),)),
        row("c3", "feat(J1.S2.T2): edit", edits=((T, ("x",), 1),)),
    ]
    assert freeze.judge(rows, "base", None) == (T, "c1")


def test_an_edit_with_no_stage_id_is_judged_from_the_base() -> None:
    rows = [row("c1", "tweak", edits=((T, ("x",), 1),))]
    assert freeze.judge(rows, "base", None) == (T, "base")


def test_a_marker_only_deletion_lands_and_a_mixed_one_refuses() -> None:
    marker = row("c2", "fix(J1.S2.T1): green", code=True, edits=((T, ("@red",), 0),))
    mixed = row("c2", "fix(J1.S2.T1): green", code=True, edits=((T, ("@red", "y"), 0),))
    assert freeze.judge([S1, marker], "base", RED) is None
    assert freeze.judge([S1, mixed], "base", RED) == (T, "c1")


@pytest.mark.parametrize("code", [False, True])
def test_added_test_lines_land_only_in_a_tests_only_stage(code: bool) -> None:
    rows = [S1, row("c2", "test(J1.S3.T1): more", edits=((T, (), 1),))]
    rows.append(row("c3", "feat(J1.S3.T2): code", code=True)) if code else None
    assert (freeze.judge(rows, "base", None) is None) is (not code)


def patched(sha: str, subject: str, patch: str) -> object:
    head = f"diff --git a/{T} b/{T}\nindex 1..2 100644\n"
    return row(sha, subject, code=True, edits=freeze._edits(head + patch))


GREEN = "fix(J1.S2.T1): green"


def test_a_hunk_of_several_lines_is_read_whole() -> None:
    patch = f"--- a/{T}\n+++ b/{T}\n@@ -3,2 +3 @@\n-@red\n-assert x == 1\n+assert x == 2\n"
    assert freeze.judge([S1, patched("c2", GREEN, patch)], "base", RED) == (T, "c1")


def test_the_second_of_two_adjacent_hunks_is_read() -> None:
    patch = f"--- a/{T}\n+++ b/{T}\n@@ -3 +2,0 @@\n-@red\n@@ -5 +4 @@\n-assert x == 1\n+assert x\n"
    assert freeze.judge([S1, patched("c2", GREEN, patch)], "base", RED) == (T, "c1")


def test_a_binary_test_file_edit_refuses() -> None:
    patch = f"Binary files a/{T} and b/{T} differ\n"
    assert freeze.judge([S1, patched("c2", GREEN, patch)], "base", RED) == (T, "c1")


def test_an_invalid_tests_red_pattern_refuses_with_one_fix_line(tmp_path: Path) -> None:
    with pytest.raises(freeze.Refusal) as refused:
        freeze.check(tmp_path, "w", "tests/**", "(")
    assert (
        refused.value.fix
        == "Operator action: fix the tests-red: line on w's AGENTS.md and commit it"
    )


def test_a_marker_first_hunk_with_a_real_line_in_a_tests_only_group_refuses() -> None:
    patch = f"--- a/{T}\n+++ b/{T}\n@@ -3,2 +3,0 @@\n-@red\n-assert x == 1\n"
    edits = freeze._edits(f"diff --git a/{T} b/{T}\n" + patch)
    assert freeze.judge([S1, row("c2", GREEN, edits=edits)], "base", RED) == (T, "c1")


def test_a_binary_test_edit_in_a_tests_only_group_refuses() -> None:
    edits = freeze._edits(f"Binary files a/{T} and b/{T} differ\n")
    assert freeze.judge([S1, row("c2", GREEN, edits=edits)], "base", RED) == (T, "c1")


def test_a_new_binary_test_file_beside_code_refuses() -> None:
    patch = f"Binary files /dev/null and b/{T} differ\n"
    assert freeze.judge([S1, patched("c2", GREEN, patch)], "base", RED) == (T, "c1")


def test_a_first_row_test_edit_is_judged_though_the_last_row_is_clean() -> None:
    rows = [row("c1", "tweak", edits=((T, ("x",), 1),)), row("c2", "chore: tidy")]
    assert freeze.judge(rows, "base", None) == (T, "base")


@pytest.mark.parametrize("job", ["JB", "JR", "J12"])
def test_a_bug_batch_red_commit_anchors_the_freeze(job: str) -> None:
    rows = [
        row("c1", f"test({job}.S1.T1): red", edits=((T, (), 2),)),
        row("c2", f"feat({job}.S2.T1): rm", edits=((T, ("x",), 0),)),
    ]
    assert freeze.judge(rows, "base", None) == (T, "c1")


def refusal(rows: list, monkeypatch: pytest.MonkeyPatch) -> str | None:
    """The refusal `check` raises over *rows*, else `None`; git is the only thing stood in."""
    monkeypatch.setattr(freeze, "git", lambda *args: "base\n")
    monkeypatch.setattr(freeze, "_rows", lambda *args: rows)
    try:
        freeze.check(Path("."), "w", "tests/**", "")
    except freeze.Refusal as refused:
        return str(refused)
    return None


def test_a_test_only_stage_is_red_wherever_it_sits(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        row("c1", "docs(JR.S2.T1): doc", code=True),
        row("c2", "test(JR.S4.T1): red", edits=((T, (), 2),)),
        row("c3", "fix(JR.S5.T1): green", code=True),
    ]
    assert refusal(rows, monkeypatch) is None


def test_stage_ids_with_no_test_edit_are_judged_not_refused_for_lacking_stage_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [row("c1", "feat(JR.S2.T1): a", code=True), row("c2", "fix(JR.S3.T1): b", code=True)]
    assert refusal(rows, monkeypatch) is None


@pytest.mark.parametrize("removed", [(), ("assert x == 1",)])
def test_a_source_stage_after_a_test_only_stage_refuses_an_added_or_changed_test_line(
    removed: tuple,
) -> None:
    rows = [
        row("c1", "test(JR.S4.T1): red", edits=((T, (), 2),)),
        row("c2", "fix(JR.S5.T1): green", code=True, edits=((T, removed, 1),)),
    ]
    assert freeze.judge(rows, "base", None) == (T, "base")


BUG = '{"id": "b1", "status": "open"}\n'


def amended(tmp_path: Path, subject: str, *, ledger: str = BUG) -> freeze.Refusal | None:
    """The refusal `check` raises over a real repo whose work branch holds *ledger* and whose
    only commit past the RED anchor, titled *subject*, changes a frozen test line."""
    git(tmp_path, "init", "-q", "-b", "main")
    for rel, text, msg in (
        ("specs/bugs/BUGS.jsonl", ledger, "init"),
        ("tests/test_a.py", "assert 0\n", "test(J1.S1.T1): red"),
        ("src/a.py", "x = 1\n", "feat(J1.S2.T1): code"),
    ):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
        git(tmp_path, "add", rel)
        git(tmp_path, "commit", "-qm", msg)
        if msg == "init":
            git(tmp_path, "branch", "work")  # the work branch holds the ledger only
    (tmp_path / "tests/test_a.py").write_text("assert 1\n")
    git(tmp_path, "commit", "-qam", subject)
    try:
        freeze.check(tmp_path, "work", "tests/**", "^@red")
    except freeze.Refusal as refused:
        return refused
    return None


REBUILD = "refactor(bugs): b1 — REBUILD the unit: a wrong assert"


@pytest.mark.medium
def test_a_rebuild_naming_a_ledger_bug_amends_a_frozen_test_line(tmp_path: Path) -> None:
    assert amended(tmp_path, REBUILD) is None


@pytest.mark.medium
def test_the_freeze_refusal_names_the_bug_proposal_act(tmp_path: Path) -> None:
    refused = amended(tmp_path, "fix(bugs): b1 — the cause")
    assert refused is not None
    assert "bugs.py append" in refused.fix


@pytest.mark.medium
def test_a_rebuild_naming_no_ledger_record_still_refuses(tmp_path: Path) -> None:
    assert amended(tmp_path, REBUILD, ledger='{"id": "other", "status": "open"}\n') is not None


@pytest.mark.medium
def test_a_non_rebuild_subject_naming_a_ledger_bug_still_refuses(tmp_path: Path) -> None:
    assert amended(tmp_path, "fix(bugs): b1 — the cause") is not None


@pytest.mark.medium
@pytest.mark.parametrize("status", ["resolved", "rejected"])
def test_a_rebuild_naming_a_terminal_record_still_refuses(tmp_path: Path, status: str) -> None:
    refused = amended(tmp_path, REBUILD, ledger=f'{{"id": "b1", "status": "{status}"}}\n')
    assert refused is not None
    assert "tests/test_a.py is frozen past the RED anchor" in refused.fix


@pytest.mark.medium
def test_a_rebuild_naming_a_deferred_record_amends(tmp_path: Path) -> None:
    assert amended(tmp_path, REBUILD, ledger='{"id": "b1", "status": "deferred"}\n') is None


@pytest.mark.medium
def test_a_rebuild_naming_an_id_only_the_job_trees_ledger_holds_still_refuses(
    tmp_path: Path,
) -> None:
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "specs/bugs").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    for rel, text, msg in (
        ("specs/bugs/BUGS.jsonl", '{"id": "other", "status": "open"}\n', "init"),
        ("tests/test_a.py", "assert 0\n", "test(J1.S1.T1): red"),
    ):
        (tmp_path / rel).write_text(text)
        git(tmp_path, "add", rel)
        git(tmp_path, "commit", "-qm", msg)
        if msg == "init":
            git(tmp_path, "branch", "work")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.py").write_text("x = 1\n")
    git(tmp_path, "add", "src/a.py")
    git(tmp_path, "commit", "-qm", "feat(J1.S2.T1): code")
    (tmp_path / "specs/bugs/BUGS.jsonl").write_text('{"id": "b1", "status": "open"}\n')
    (tmp_path / "tests/test_a.py").write_text("assert 1\n")
    git(tmp_path, "commit", "-qam", REBUILD)
    with pytest.raises(freeze.Refusal) as refused:
        freeze.check(tmp_path, "work", "tests/**", "^@red")
    assert "tests/test_a.py is frozen past the RED anchor" in refused.value.fix


def outcome(tmp_path: Path, ledger: str) -> str:
    """What the freeze did with a REBUILD over a frozen line given *ledger*: refused, admitted,
    or the name of the exception that escaped."""
    try:
        return "admitted" if amended(tmp_path, REBUILD, ledger=ledger) is None else "refused"
    except Exception as crash:  # noqa: BLE001 - the row names whatever escaped
        return type(crash).__name__


@pytest.mark.medium
@pytest.mark.parametrize("line", ['{"status": "open"}', "[1]", '"b1"'])
def test_a_ledger_line_naming_nothing_does_not_crash_or_admit(tmp_path: Path, line: str) -> None:
    assert outcome(tmp_path, f"{line}\n") == "refused"


@pytest.mark.medium
def test_a_non_object_ledger_line_leaves_the_records_after_it_readable(tmp_path: Path) -> None:
    assert outcome(tmp_path, f"[1]\n{BUG}") == "admitted"
