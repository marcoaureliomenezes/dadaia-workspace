"""``features.chokepoints.verdict`` — the ONE verdict store (v0.5.1 K7).

Table-driven over :func:`covering_verdict`'s cases (head match, first-parent match,
stale, ambiguous "two files", non-qualifying agent/verdict) plus
:func:`discover_verdict_candidates`'s live+archived root discovery.

Intent: CONTRACT — v0.5.1 K7 (replaces
``tests/unit/features/chokepoints/test_iter_security_approvals.py`` and
``tests/unit/features/chokepoints/test_push_verdict_gc.py``, both deleted — the
``.dadaia/handoff/`` verdict store and its GC lane no longer exist).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.chokepoints.verdict import (
    Verdict,
    covering_verdict,
    discover_verdict_candidates,
)

_SHA_HEAD = "a" * 40
_SHA_PARENT = "b" * 40
_SHA_OTHER = "c" * 40
_SHA_STALE = "d" * 40


def _write_verdict(
    path: Path,
    sha: str,
    *,
    agent: str = "security-reviewer",
    verdict: str | None = "APPROVED",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {"agent": agent, "metrics": {"commit_sha": sha}}
    if verdict is not None:
        payload["verdict"] = verdict
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# covering_verdict — table-driven over the cases the design card names.
# ---------------------------------------------------------------------------


def test_head_match_wins(tmp_path: Path) -> None:
    path = _write_verdict(tmp_path / "v.handoff.json", _SHA_HEAD)
    result = covering_verdict([path], _SHA_HEAD, _SHA_PARENT)
    assert result == Verdict(commit_sha=_SHA_HEAD, path=path)


def test_first_parent_match_wins_when_no_head_match(tmp_path: Path) -> None:
    path = _write_verdict(tmp_path / "v.handoff.json", _SHA_PARENT)
    result = covering_verdict([path], _SHA_HEAD, _SHA_PARENT)
    assert result == Verdict(commit_sha=_SHA_PARENT, path=path)


def test_no_parent_supplied_only_head_can_match(tmp_path: Path) -> None:
    path = _write_verdict(tmp_path / "v.handoff.json", _SHA_OTHER)
    assert covering_verdict([path], _SHA_HEAD, None) is None


def test_stale_sha_matching_neither_is_none(tmp_path: Path) -> None:
    path = _write_verdict(tmp_path / "v.handoff.json", _SHA_STALE)
    assert covering_verdict([path], _SHA_HEAD, _SHA_PARENT) is None


def test_two_files_matching_the_same_head_sha_is_ambiguous_none(tmp_path: Path) -> None:
    first = _write_verdict(tmp_path / "one.handoff.json", _SHA_HEAD)
    second = _write_verdict(tmp_path / "two.handoff.json", _SHA_HEAD)
    assert covering_verdict([first, second], _SHA_HEAD, _SHA_PARENT) is None


def test_two_files_matching_the_same_parent_sha_is_ambiguous_none(tmp_path: Path) -> None:
    first = _write_verdict(tmp_path / "one.handoff.json", _SHA_PARENT)
    second = _write_verdict(tmp_path / "two.handoff.json", _SHA_PARENT)
    assert covering_verdict([first, second], _SHA_HEAD, _SHA_PARENT) is None


def test_head_match_wins_even_with_an_unrelated_parent_match(tmp_path: Path) -> None:
    head_verdict = _write_verdict(tmp_path / "head.handoff.json", _SHA_HEAD)
    _write_verdict(tmp_path / "parent.handoff.json", _SHA_PARENT)
    result = covering_verdict(
        [head_verdict, tmp_path / "parent.handoff.json"], _SHA_HEAD, _SHA_PARENT
    )
    assert result == Verdict(commit_sha=_SHA_HEAD, path=head_verdict)


@pytest.mark.parametrize(
    ("agent", "verdict"),
    [
        pytest.param("code-reviewer", "APPROVED", id="wrong-agent"),
        pytest.param("security-reviewer", "REJECTED", id="not-approved"),
        pytest.param("security-reviewer", None, id="missing-verdict-field"),
    ],
)
def test_non_qualifying_handoff_never_covers(
    tmp_path: Path, agent: str, verdict: str | None
) -> None:
    path = _write_verdict(tmp_path / "v.handoff.json", _SHA_HEAD, agent=agent, verdict=verdict)
    assert covering_verdict([path], _SHA_HEAD, _SHA_PARENT) is None


def test_malformed_json_sibling_is_skipped_never_raises(tmp_path: Path) -> None:
    broken = tmp_path / "broken.handoff.json"
    broken.write_text("{ not json", encoding="utf-8")
    good = _write_verdict(tmp_path / "good.handoff.json", _SHA_HEAD)
    result = covering_verdict([broken, good], _SHA_HEAD, _SHA_PARENT)
    assert result == Verdict(commit_sha=_SHA_HEAD, path=good)


def test_empty_candidates_is_none() -> None:
    assert covering_verdict([], _SHA_HEAD, _SHA_PARENT) is None


# ---------------------------------------------------------------------------
# discover_verdict_candidates — live + archived roots, glob narrowing.
# ---------------------------------------------------------------------------


def test_discovers_both_live_and_archived_roots(tmp_path: Path) -> None:
    live = tmp_path / "specs" / "releases" / "0.5.1" / "verdicts" / f"{_SHA_HEAD}.handoff.json"
    archived = (
        tmp_path
        / "specs"
        / "releases"
        / "_archive"
        / "0.4.5"
        / "verdicts"
        / f"{_SHA_PARENT}.handoff.json"
    )
    _write_verdict(live, _SHA_HEAD)
    _write_verdict(archived, _SHA_PARENT)

    found = discover_verdict_candidates(tmp_path)
    assert set(found) == {live, archived}


def test_release_glob_narrows_to_one_release(tmp_path: Path) -> None:
    matching = tmp_path / "specs" / "releases" / "0.5.1" / "verdicts" / f"{_SHA_HEAD}.handoff.json"
    other = tmp_path / "specs" / "releases" / "0.6.0" / "verdicts" / f"{_SHA_PARENT}.handoff.json"
    _write_verdict(matching, _SHA_HEAD)
    _write_verdict(other, _SHA_PARENT)

    found = discover_verdict_candidates(tmp_path, release_glob="0.5.1")
    assert found == [matching]


def test_ideas_directory_is_never_a_candidate_root(tmp_path: Path) -> None:
    """F-16 (the bash script's old hardening class): a `verdicts/` directory placed
    directly under `_ideas/` must never match — structurally impossible here since
    each template carries exactly ONE `{glob}` segment at the release-id position and
    `Path.glob` never crosses `/` for a single `*` (unlike bash `fnmatch`)."""
    decoy = tmp_path / "specs" / "releases" / "_ideas" / "verdicts" / f"{_SHA_HEAD}.handoff.json"
    _write_verdict(decoy, _SHA_HEAD)

    assert discover_verdict_candidates(tmp_path) == []


def test_no_specs_tree_yields_no_candidates(tmp_path: Path) -> None:
    assert discover_verdict_candidates(tmp_path) == []
