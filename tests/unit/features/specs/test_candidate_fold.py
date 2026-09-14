"""Intent: UNIT — `dadaia release fold` (ADR 0014, operator ruling 2026-09-14): a wrongly
archived release becomes rc-N (or the final root trio) of the published version that
shipped it — trio moved, logs merged in ts order, folded directory deleted, histo
record rewritten in place — or nothing moves at all.
Size: SMALL — tmp_path trees, an in-memory histo.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.models.histo import HistoRecord
from dadaia_workspace.features.specs.candidate import ArchiveError, fold_release

pytestmark = pytest.mark.unit

_TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")


def _state(release: str, **overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "release-state-v1",
        "release": release,
        "phase": "ARCHIVED",
        "rc": None,
        "defined": {"sha": "a" * 40, "ts": "2026-08-27T10:00:00Z"},
        "implemented": {"sha": "b" * 40, "rc": 1, "ts": "2026-08-28T10:00:00Z"},
        "shipped": None,
        "log": [
            {"ts": "2026-08-27T10:00:00Z", "agent": "x", "kind": "note", "text": f"{release} born"},
            {
                "ts": "2026-08-28T10:00:00Z",
                "agent": "x",
                "kind": "summary",
                "text": f"{release} closed",
            },
        ],
    }
    doc.update(overrides)
    return doc


def _write(root: Path, rel: str, doc: dict[str, Any] | None, *, trio: bool = True) -> Path:
    d = root / "releases" / rel
    d.mkdir(parents=True, exist_ok=True)
    if doc is not None:
        (d / "_RELEASE.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    if trio:
        for name in _TRIO:
            (d / name).write_text(f"# {rel} {name}\n", encoding="utf-8")
    return d


class _Histo:
    def __init__(self, *ids: str) -> None:
        self.records = {
            i: HistoRecord(i, "2026-08-31T00:00:00Z", "delivered", i, None, f"{i} summary", None)
            for i in ids
        }

    def update(
        self, record_id: str, mutate: Callable[[HistoRecord], HistoRecord]
    ) -> HistoRecord | None:
        if record_id not in self.records:
            return None
        self.records[record_id] = mutate(self.records[record_id])
        return self.records[record_id]


@pytest.fixture
def specs(tmp_path: Path) -> Path:
    _write(tmp_path, "0.4.7", _state("0.4.7", phase="CLOSURE", shipped=None))
    _write(tmp_path, "_archive/0.5.0", _state("0.5.0"))
    return tmp_path


def test_first_fold_births_the_published_release_and_places_rc_1(specs: Path) -> None:
    histo = _Histo("v0.5.0")
    result = fold_release(
        specs,
        "0.5.0",
        into="0.4.5",
        shipped_sha="fe04319a",
        pr=240,
        final=False,
        histo_update=histo.update,
    )
    target = specs / "releases" / "_archive" / "0.4.5"
    assert result.placed_at == target / "rc-1" and result.rc == 1
    assert sorted(p.name for p in (target / "rc-1").iterdir()) == sorted(_TRIO)
    assert not (specs / "releases" / "_archive" / "0.5.0").exists()
    state = json.loads((target / "_RELEASE.json").read_text())
    assert state["release"] == "0.4.5" and state["phase"] == "ARCHIVED"
    assert state["shipped"]["sha"] == "fe04319a" and state["shipped"]["pr"] == 240
    assert state["defined"]["sha"] == "a" * 40 and state["implemented"]["sha"] == "b" * 40
    assert [e["text"] for e in state["log"]][:2] == ["0.5.0 born", "0.5.0 closed"]
    assert state["log"][-1]["kind"] == "note" and "Folded" in state["log"][-1]["text"]
    assert result.histo_ids == ("v0.5.0",)
    assert histo.records["v0.5.0"].release == "0.4.5"
    assert "folded into 0.4.5/rc-1" in histo.records["v0.5.0"].summary


def test_later_folds_continue_rc_numbering_and_final_takes_the_root(specs: Path) -> None:
    _write(
        specs,
        "_archive/0.5.1",
        _state(
            "0.5.1",
            log=[
                {"ts": "2026-08-29T10:00:00Z", "agent": "x", "kind": "note", "text": "0.5.1 born"},
            ],
        ),
    )
    histo = _Histo("0.5.1")
    fold_release(
        specs,
        "0.5.0",
        into="0.4.5",
        shipped_sha="fe04319a",
        pr=240,
        final=False,
        histo_update=_Histo("v0.5.0").update,
    )
    result = fold_release(
        specs,
        "0.5.1",
        into="0.4.5",
        shipped_sha=None,
        pr=None,
        final=True,
        histo_update=histo.update,
    )
    target = specs / "releases" / "_archive" / "0.4.5"
    assert result.placed_at == target and all((target / n).is_file() for n in _TRIO)
    assert (target / "rc-1").is_dir() and not (target / "rc-2").exists()
    state = json.loads((target / "_RELEASE.json").read_text())
    texts = [e["text"] for e in state["log"] if e["kind"] != "note" or "Folded" not in e["text"]]
    assert texts == ["0.5.0 born", "0.5.0 closed", "0.5.1 born"]  # ts order across both
    assert state["rc"] == 1
    assert "folded into 0.4.5/root (final candidate)" in histo.records["0.5.1"].summary


def test_a_second_final_is_refused_and_nothing_moves(specs: Path) -> None:
    _write(specs, "_archive/0.5.1", _state("0.5.1"))
    fold_release(
        specs,
        "0.5.0",
        into="0.4.5",
        shipped_sha="fe04319a",
        pr=240,
        final=True,
        histo_update=_Histo().update,
    )
    before = sorted(p.as_posix() for p in specs.rglob("*"))
    with pytest.raises(ArchiveError, match="already carries a root trio"):
        fold_release(
            specs,
            "0.5.1",
            into="0.4.5",
            shipped_sha=None,
            pr=None,
            final=True,
            histo_update=_Histo().update,
        )
    assert sorted(p.as_posix() for p in specs.rglob("*")) == before


@pytest.mark.parametrize(
    ("into", "shipped", "pr", "match"),
    [
        ("0.4.7", "fe04319a", 240, "not below the live release"),
        ("0.4.5", None, None, "publication must be named"),
        ("x.y", "fe04319a", 240, "not bare SemVer"),
        ("0.5.0", "fe04319a", 240, "folded into itself"),
    ],
)
def test_refusals_carry_a_fix_line(
    specs: Path, into: str, shipped: str | None, pr: int | None, match: str
) -> None:
    with pytest.raises(ArchiveError, match=match) as exc:
        fold_release(
            specs,
            "0.5.0",
            into=into,
            shipped_sha=shipped,
            pr=pr,
            final=False,
            histo_update=_Histo().update,
        )
    assert "fix: " in str(exc.value)
    assert (specs / "releases" / "_archive" / "0.5.0" / "SPEC.md").is_file()


def test_a_folded_release_with_its_own_rc_folders_contributes_them_first(specs: Path) -> None:
    folded = specs / "releases" / "_archive" / "0.5.0"
    (folded / "rc-1").mkdir()
    for n in _TRIO:
        (folded / "rc-1" / n).write_text("old rc\n", encoding="utf-8")
    result = fold_release(
        specs,
        "0.5.0",
        into="0.4.5",
        shipped_sha="fe04319a",
        pr=240,
        final=False,
        histo_update=_Histo().update,
    )
    target = specs / "releases" / "_archive" / "0.4.5"
    assert (target / "rc-1" / "SPEC.md").read_text() == "old rc\n"
    assert result.placed_at == target / "rc-2" and result.rc == 2
