"""`release phase` — phase and milestones move only by verb (0.4.7 FR5, T-047-29).

Intent: CONTRACT — 0.4.7 FR5 (`IMPLEMENTATION` requires the trio `Aprovado` and stamps
`defined`; `CLOSURE` requires every task `[x]` and stamps `implemented {sha, rc+1, ts}`;
an out-of-order or repeated transition is refused with one `fix:`; `archive` can no
longer hang on a hand-set milestone).
Size: SMALL — a tmp_path specs tree, no CLI, no git.

Structural frame: `_RELEASE.json`'s `phase`/`defined`/`implemented` were Read-then-Edit,
and the candidate-1 reviewer found `release archive` refusing on a hand-edited
`implemented` that `archive` itself validated — a document with two writers, one of whom
could not be told apart from a typo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.candidate import (
    ArchiveError,
    archive_release,
    set_phase,
)
from tests.contract.test_every_block_carries_a_fix import assert_block_carries_a_runnable_fix

_SHA = "a" * 40


def _live_release(
    specs: Path,
    version: str = "1.0.0",
    *,
    phase: str = "DEFINITION",
    tasks: str = "- [x] T-1 done\n",
    status: str = "Aprovado",
    plan_status: str | None = None,
    defined: dict[str, object] | None = None,
    rc: int | None = None,
) -> Path:
    rdir = specs / "releases" / version
    rdir.mkdir(parents=True)
    (rdir / "SPEC.md").write_text(f"# SPEC\n\n**Status:** {status}\n", encoding="utf-8")
    (rdir / "PLAN.md").write_text(
        f"# PLAN\n\n**Status:** {plan_status or status}\n", encoding="utf-8"
    )
    (rdir / "TASKS.md").write_text(f"# TASKS\n\n**Status:** {status}\n\n" + tasks, encoding="utf-8")
    (rdir / "_RELEASE.json").write_text(
        json.dumps(
            {
                "schema": "release-state-v1",
                "release": version,
                "phase": phase,
                "rc": rc,
                "defined": defined,
                "implemented": None,
                "shipped": None,
                "log": [],
            }
        ),
        encoding="utf-8",
    )
    return rdir


def _state(rdir: Path) -> dict[str, object]:
    return json.loads((rdir / "_RELEASE.json").read_text(encoding="utf-8"))


def test_implementation_stamps_defined_and_one_note(tmp_path: Path) -> None:
    """The trio is `Aprovado`, so the candidate is defined: phase and milestone move
    together, in one act, with one `note` recording it."""
    rdir = _live_release(tmp_path)
    record = set_phase(tmp_path, "IMPLEMENTATION", sha=_SHA)

    state = _state(rdir)
    assert record.phase == "IMPLEMENTATION"
    assert state["phase"] == "IMPLEMENTATION"
    assert state["defined"] == {"sha": _SHA, "ts": record.ts}
    assert state["implemented"] is None
    assert len(state["log"]) == 1
    assert state["log"][0]["kind"] == "note"


def test_closure_stamps_implemented_with_the_next_rc(tmp_path: Path) -> None:
    """`rc` names the candidate being closed: the first closure is candidate 1, and a
    release that already archived one candidate closes its second."""
    rdir = _live_release(tmp_path, phase="IMPLEMENTATION", defined={"sha": _SHA, "ts": "t"}, rc=1)
    set_phase(tmp_path, "CLOSURE", sha=_SHA)

    state = _state(rdir)
    assert state["phase"] == "CLOSURE"
    assert state["implemented"] == {"sha": _SHA, "rc": 2, "ts": state["implemented"]["ts"]}


def test_closure_refuses_while_a_task_is_reserved(tmp_path: Path) -> None:
    """A `[-]` marker is work in flight — the refusal names the task line."""
    _live_release(
        tmp_path,
        phase="IMPLEMENTATION",
        defined={"sha": _SHA, "ts": "t"},
        tasks="- [x] T-1 done\n- [-] T-2 in progress\n",
    )
    with pytest.raises(ArchiveError) as exc:
        set_phase(tmp_path, "CLOSURE", sha=_SHA)
    assert "T-2" in str(exc.value)
    assert_block_carries_a_runnable_fix(str(exc.value))


def test_implementation_refuses_a_draft_plan_naming_the_file(tmp_path: Path) -> None:
    _live_release(tmp_path, plan_status="Draft")
    with pytest.raises(ArchiveError) as exc:
        set_phase(tmp_path, "IMPLEMENTATION", sha=_SHA)
    assert "PLAN.md" in str(exc.value)
    assert_block_carries_a_runnable_fix(str(exc.value))


@pytest.mark.parametrize(
    ("name", "phase", "target"),
    [
        ("closure-before-implementation", "DEFINITION", "CLOSURE"),
        ("implementation-rerun", "IMPLEMENTATION", "IMPLEMENTATION"),
        ("closure-rerun", "CLOSURE", "CLOSURE"),
        ("archived", "ARCHIVED", "IMPLEMENTATION"),
    ],
)
def test_an_out_of_order_or_repeated_transition_is_refused(
    tmp_path: Path, name: str, phase: str, target: str
) -> None:
    _live_release(tmp_path, phase=phase, defined={"sha": _SHA, "ts": "t"})
    with pytest.raises(ArchiveError) as exc:
        set_phase(tmp_path, target, sha=_SHA)
    assert_block_carries_a_runnable_fix(str(exc.value))


def test_a_bad_sha_is_refused(tmp_path: Path) -> None:
    _live_release(tmp_path)
    with pytest.raises(ArchiveError) as exc:
        set_phase(tmp_path, "IMPLEMENTATION", sha="nope")
    assert_block_carries_a_runnable_fix(str(exc.value))


def test_archive_succeeds_on_a_release_closed_by_the_verb(tmp_path: Path) -> None:
    """The milestone `archive` validates is now written by the verb that also set the
    phase — the two can no longer disagree, so `archive` cannot hang on it."""
    _live_release(tmp_path, phase="IMPLEMENTATION", defined={"sha": _SHA, "ts": "t"})
    set_phase(tmp_path, "CLOSURE", sha=_SHA)

    records: list[object] = []
    result = archive_release(
        tmp_path,
        "1.0.0",
        shipped_sha=_SHA,
        pr=1,
        next_release="1.0.1",
        histo_append=records.append,
    )
    assert result.release == "1.0.0"
    assert (tmp_path / "releases" / "_archive" / "1.0.0").is_dir()
    assert len(records) == 1
