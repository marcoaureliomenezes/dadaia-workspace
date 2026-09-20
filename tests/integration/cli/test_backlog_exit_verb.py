"""`dadaia backlog exit` — one verb, one histo record (0.4.7 FR3, T-047-27).

Intent: CONTRACT — 0.4.7 FR3 (an item leaves `active[]` only by the verb; each
disposition carries its own required evidence; every refusal hands back one `fix:`).
Size: MEDIUM — the real CLI against a tmp_path specs tree and a tmp_path HOME.

Structural frame: `active[]` used to be edited "with file tools directly", so a closure
sweep was a script nobody could audit and an exit left no trace. The verb is the one
path; the event is the trace.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("DADAIA_CONTEXT", "dadaia-workspace")
    monkeypatch.setenv("DADAIA_SESSION_ID", "session-under-test")
    return tmp_path / "home"


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    target = tmp_path / "specs"
    (target / "releases" / "0.4.7").mkdir(parents=True)
    (target / "releases" / "_archive" / "0.4.6").mkdir(parents=True)
    return target


def _run(*args: str) -> str:
    result = _runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def _refuse(*args: str) -> str:
    result = _runner.invoke(app, list(args))
    assert result.exit_code == 1, result.output
    return result.output


def _new(specs_dir: Path, slug: str) -> None:
    _run("backlog", "new", slug, "--specs-dir", str(specs_dir))


def _pick(specs_dir: Path, slug: str) -> None:
    """Flip an entry to `picked` the way the release-definition commit does — the
    status FR3 requires before a `delivered`/`superseded` exit."""
    path = specs_dir / "backlog" / "BACKLOG.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    for item in document["active"]:
        if item["id"] == slug:
            item["status"] = "picked"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _histo_lines(specs_dir: Path) -> list[str]:
    path = specs_dir / "backlog" / "_archive" / "backlog_histo.jsonl"
    return [line for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def test_exit_removes_one_entry_and_appends_one_histo_record(home: Path, specs: Path) -> None:
    """The delivered lane: the object leaves `active[]`, the histo line carries it as
    `entry`."""
    _new(specs, "a-thing")
    _new(specs, "another-thing")
    _pick(specs, "a-thing")

    _run(
        "backlog", "exit", "a-thing", "--disposition", "delivered",
        "--release", "0.4.7", "--specs-dir", str(specs),
    )  # fmt: skip

    document = json.loads((specs / "backlog" / "BACKLOG.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in document["active"]] == ["another-thing"]

    lines = _histo_lines(specs)
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["id"] == "a-thing"
    assert record["disposition"] == "delivered"
    assert record["release"] == "0.4.7"
    assert record["entry"]["id"] == "a-thing"


def test_an_archived_release_is_a_valid_delivered_target(home: Path, specs: Path) -> None:
    """`--release` accepts a live OR an archived release id — a closure sweep run after
    the ship must still name the release that delivered the item."""
    _new(specs, "old-thing")
    _pick(specs, "old-thing")
    _run(
        "backlog", "exit", "old-thing", "--disposition", "delivered",
        "--release", "0.4.6", "--specs-dir", str(specs),
    )  # fmt: skip
    assert json.loads(_histo_lines(specs)[0])["release"] == "0.4.6"


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("delivered-without-release", ["--disposition", "delivered"]),
        ("delivered-unknown-release", ["--disposition", "delivered", "--release", "9.9.9"]),
        ("superseded-without-release", ["--disposition", "superseded"]),
        ("superseded-unknown-release", ["--disposition", "superseded", "--release", "9.9.9"]),
        ("rejected-without-reason", ["--disposition", "rejected"]),
    ],
)
def test_each_disposition_refuses_without_its_evidence(
    home: Path, specs: Path, name: str, args: list[str]
) -> None:
    """Every refusal exits 1, writes nothing, and hands back exactly one `fix:` line."""
    from tests.contract.test_every_block_carries_a_fix import assert_block_carries_a_runnable_fix

    _new(specs, "a-thing")
    output = _refuse("backlog", "exit", "a-thing", *args, "--specs-dir", str(specs))
    assert_block_carries_a_runnable_fix(output)

    document = json.loads((specs / "backlog" / "BACKLOG.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in document["active"]] == ["a-thing"]
    assert not (specs / "backlog" / "_archive").exists()


def test_a_second_exit_of_the_same_slug_refuses_and_points_at_the_histo(
    home: Path, specs: Path
) -> None:
    """A slug that is not in `active[]` is either already exited or never existed — the
    refusal names the live slugs and hands back the histo grep."""
    from tests.contract.test_every_block_carries_a_fix import assert_block_carries_a_runnable_fix

    _new(specs, "a-thing")
    _new(specs, "another-thing")
    _run(
        "backlog", "exit", "a-thing", "--disposition", "rejected",
        "--reason", "not wanted", "--specs-dir", str(specs),
    )  # fmt: skip

    output = _refuse(
        "backlog", "exit", "a-thing", "--disposition", "rejected",
        "--reason", "again", "--specs-dir", str(specs),
    )  # fmt: skip
    assert "another-thing" in output
    assert_block_carries_a_runnable_fix(output)
    assert len(_histo_lines(specs)) == 1


@pytest.mark.parametrize("disposition", ["delivered", "superseded"])
def test_a_release_exit_refuses_an_entry_that_was_never_picked(
    home: Path, specs: Path, disposition: str
) -> None:
    """FR3: `delivered`/`superseded` exit a PICKED entry. An `idea` that never entered a
    release cannot have been delivered or superseded by one — exiting it that way
    launders an unworked item into the histo as shipped work."""
    from tests.contract.test_every_block_carries_a_fix import assert_block_carries_a_runnable_fix

    _new(specs, "an-idea")

    output = _refuse(
        "backlog", "exit", "an-idea", "--disposition", disposition,
        "--release", "0.4.7", "--specs-dir", str(specs),
    )  # fmt: skip
    assert "picked" in output
    assert_block_carries_a_runnable_fix(output)

    document = json.loads((specs / "backlog" / "BACKLOG.json").read_text(encoding="utf-8"))
    assert [item["id"] for item in document["active"]] == ["an-idea"]
    assert not (specs / "backlog" / "_archive").exists()


def test_rejected_exits_from_any_live_status_and_needs_only_a_reason(
    home: Path, specs: Path
) -> None:
    """FR3: `rejected` is the lane for an item that never got picked — it carries a
    reason, names no release, and needs no status."""
    _new(specs, "an-idea")

    _run(
        "backlog", "exit", "an-idea", "--disposition", "rejected",
        "--reason", "out of scope", "--specs-dir", str(specs),
    )  # fmt: skip

    record = json.loads(_histo_lines(specs)[0])
    assert record["disposition"] == "rejected"
    assert record["reason"] == "out of scope"


def test_superseded_records_the_release_that_superseded_it(home: Path, specs: Path) -> None:
    """FR3: `superseded` names the release, exactly like `delivered` — one evidence rule
    for both release lanes instead of two."""
    _new(specs, "a-thing")
    _pick(specs, "a-thing")

    _run(
        "backlog", "exit", "a-thing", "--disposition", "superseded",
        "--release", "0.4.7", "--specs-dir", str(specs),
    )  # fmt: skip

    assert json.loads(_histo_lines(specs)[0])["release"] == "0.4.7"
