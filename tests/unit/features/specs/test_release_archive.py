"""``archive_release`` — the one transactional promote verb (0.4.7 FR3, T-047-09).

Intent: CONTRACT — T-047-09: `dadaia release archive <id> --shipped --pr --next`
validates (release tree, the named id is the live one, every task `[x]`, phase
CLOSURE, `implemented` set, a fresh SemVer `<next>`), then ships the state, moves the
whole directory under `_archive/`, births `<next>` and appends exactly one
`releases_histo.jsonl` record — all-or-nothing, nothing written on any refusal. It
replaces RC-FLOW steps 9–12's hand-driven `git mv` + hand histo append.
Size: SMALL — tmp_path trees only; no subprocess, no network, no git.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.histo import HistoRecord
from dadaia_workspace.features.specs.candidate import ArchiveError, archive_release
from dadaia_workspace.features.specs.canon import release_new

_SHA = "a" * 40


class _FakeHisto:
    """The histo sink the CLI backs with a ``JsonlRecordStore``. A list, because the
    verb's contract is "exactly one record, of this shape" — asserting a value beats
    observing a mutation."""

    def __init__(self) -> None:
        self.records: list[HistoRecord] = []

    def __call__(self, record: HistoRecord) -> None:
        self.records.append(record)


def _digest(root: Path) -> str:
    """A byte digest of the whole tree — the refusal contract is "NOTHING written"."""
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def _closed_release(specs: Path, release_id: str = "1.0.0", *, tasks: str = "- [x] T-1\n") -> Path:
    """A release born by ``release_new`` (the real birth act) driven to CLOSURE."""
    specs.mkdir(parents=True, exist_ok=True)
    release_new(specs, release_id)
    rdir = specs / "releases" / release_id
    (rdir / "PLAN.md").write_text("# PLAN\n\n**Status:** Aprovado\n", encoding="utf-8")
    (rdir / "TASKS.md").write_text("# TASKS\n\n**Status:** Aprovado\n\n" + tasks, encoding="utf-8")
    state = json.loads((rdir / "_RELEASE.json").read_text(encoding="utf-8"))
    state["phase"] = "CLOSURE"
    state["rc"] = 2
    state["implemented"] = {"sha": "b" * 40, "ts": "2999-01-01T00:00:00Z", "rc": 2}
    state["log"].append(
        {
            "ts": "2999-01-01T00:00:00Z",
            "agent": "product-engineer",
            "kind": "summary",
            "text": "records tell the truth",
        }
    )
    (rdir / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return rdir


def _archive(specs: Path, histo: _FakeHisto | None = None, **kwargs: object) -> object:
    params: dict[str, object] = {
        "shipped_sha": _SHA,
        "pr": 251,
        "next_release": "1.0.1",
        "histo_append": histo or _FakeHisto(),
    }
    params.update(kwargs)
    return archive_release(specs, "1.0.0", **params)  # type: ignore[arg-type]


# ── happy path ────────────────────────────────────────────────────────────────


def test_archive_moves_the_directory_ships_the_state_and_births_next(tmp_path: Path) -> None:
    _closed_release(tmp_path)
    histo = _FakeHisto()

    result = _archive(tmp_path, histo)

    archived = tmp_path / "releases" / "_archive" / "1.0.0"
    assert not (tmp_path / "releases" / "1.0.0").exists()
    assert (archived / "SPEC.md").is_file() and (archived / "TASKS.md").is_file()
    state = json.loads((archived / "_RELEASE.json").read_text(encoding="utf-8"))
    assert state["phase"] == "ARCHIVED"
    assert state["shipped"]["sha"] == _SHA and state["shipped"]["pr"] == 251
    assert any(e["kind"] == "note" and "1.0.1" in e["text"] for e in state["log"])
    assert result.archived_dir == archived  # type: ignore[attr-defined]


def test_archive_appends_exactly_one_valid_histo_record(tmp_path: Path) -> None:
    _closed_release(tmp_path)
    histo = _FakeHisto()

    _archive(tmp_path, histo)

    assert len(histo.records) == 1
    record = histo.records[0]
    assert record.id == "1.0.0"
    assert record.disposition == "delivered"
    assert record.release == "1.0.0"
    assert record.reason is None and record.entry is None
    assert record.summary is not None
    assert f"shipped {_SHA}" in record.summary
    assert "PR #251" in record.summary and "rc=2" in record.summary
    assert "records tell the truth" in record.summary
    # Round-trips through the ONE record shape every _histo.jsonl is validated against.
    assert HistoRecord.from_dict(record.to_dict()) == record


def test_next_release_is_born_in_definition_with_its_state(tmp_path: Path) -> None:
    _closed_release(tmp_path)

    _archive(tmp_path)

    nxt = tmp_path / "releases" / "1.0.1"
    assert (nxt / "SPEC.md").is_file()
    state = json.loads((nxt / "_RELEASE.json").read_text(encoding="utf-8"))
    assert state["phase"] == "DEFINITION" and state["release"] == "1.0.1"


# ── refusals: nothing written ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("kwargs", "tasks", "needle"),
    [
        pytest.param({}, "- [-] T-1 in progress\n", "[x]", id="reserved-task"),
        pytest.param({}, "- [ ] T-1 open\n", "[x]", id="open-task"),
        pytest.param({"next_release": "1.0.0"}, "- [x] T-1\n", "1.0.0", id="next-already-exists"),
        pytest.param({"next_release": "nope"}, "- [x] T-1\n", "SemVer", id="next-not-semver"),
        pytest.param({"shipped_sha": "zz"}, "- [x] T-1\n", "sha", id="bad-sha"),
        pytest.param({"pr": 0}, "- [x] T-1\n", "--pr", id="bad-pr"),
    ],
)
def test_refusal_carries_a_fix_line_and_writes_nothing(
    tmp_path: Path, kwargs: dict[str, object], tasks: str, needle: str
) -> None:
    _closed_release(tmp_path, tasks=tasks)
    before = _digest(tmp_path)
    histo = _FakeHisto()

    with pytest.raises(ArchiveError) as excinfo:
        _archive(tmp_path, histo, **kwargs)

    message = str(excinfo.value)
    assert needle in message
    assert "\nfix: " in "\n" + message
    assert _digest(tmp_path) == before
    assert histo.records == []


def test_refuses_a_release_not_in_closure(tmp_path: Path) -> None:
    rdir = _closed_release(tmp_path)
    state = json.loads((rdir / "_RELEASE.json").read_text(encoding="utf-8"))
    state["phase"] = "IMPLEMENTATION"
    (rdir / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    before = _digest(tmp_path)

    with pytest.raises(ArchiveError, match="CLOSURE"):
        _archive(tmp_path)

    assert _digest(tmp_path) == before


def test_refuses_a_release_without_implemented(tmp_path: Path) -> None:
    rdir = _closed_release(tmp_path)
    state = json.loads((rdir / "_RELEASE.json").read_text(encoding="utf-8"))
    state["implemented"] = None
    (rdir / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    before = _digest(tmp_path)

    with pytest.raises(ArchiveError, match="implemented"):
        _archive(tmp_path)

    assert _digest(tmp_path) == before


def test_refuses_an_id_that_is_not_the_live_release(tmp_path: Path) -> None:
    _closed_release(tmp_path)
    before = _digest(tmp_path)

    with pytest.raises(ArchiveError, match="2.0.0"):
        archive_release(
            tmp_path,
            "2.0.0",
            shipped_sha=_SHA,
            pr=1,
            next_release="1.0.1",
            histo_append=_FakeHisto(),
        )

    assert _digest(tmp_path) == before


# ── rollback ──────────────────────────────────────────────────────────────────


def test_a_raising_histo_sink_rolls_the_whole_tree_back(tmp_path: Path) -> None:
    """The histo append is the LAST act, so a failure there must undo the move, the
    shipped state write and the birth — the operator retries one verb, never repairs
    a half-archived tree by hand."""
    _closed_release(tmp_path)
    before = _digest(tmp_path)

    def _boom(record: HistoRecord) -> None:
        raise OSError("ledger unavailable")

    with pytest.raises(OSError, match="ledger unavailable"):
        _archive(tmp_path, histo_append=_boom)

    assert (tmp_path / "releases" / "1.0.0" / "SPEC.md").is_file()
    assert not (tmp_path / "releases" / "1.0.1").exists()
    assert not (tmp_path / "releases" / "_archive" / "1.0.0").exists()
    assert _digest(tmp_path) == before
