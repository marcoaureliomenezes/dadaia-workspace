"""v0.4.4 T-044-06 (FR3): the v2 branch contract — feature/{M.m.p} is pushable, develop
and main are PR-only.

The gitflow law (DADAIA.md §4, operator ruling 2026-08-23, SPEC v0.4.4 FR3): exactly
three branch patterns exist — ``main``, ``develop``, ``feature/M.m.p`` (no ``v``, no
suffix, no ``hotfix`` row — G2 retires it outright) — and ``feature/M.m.p`` is the ONLY
pushable one. ``develop`` and ``main`` never take a direct push; both advance by PR only
(``feature/{M.m.p}`` → ``develop``, ``develop`` → ``main``). Tag pushes keep their
carve-out (publishing depends on it). The security verdict no longer lives on this path
at all (A3.4) — it is relocated to a PR gate (FR4), so a ``feature/{M.m.p}`` push is
allowed outright once branch policy and the denylist scan (``test_push_denylist_scan.py``)
clear.

This file supersedes T-060-04's v1 branch-policy tests (four patterns, ``develop``-only
pushable, verdict-gated): every "allowed" case below refused under the pre-T-044-06 gate
(it only knew ``develop``/``feature/v…``/``hotfix/v…``), and ``develop`` used to flow
with a covering verdict — under v2 it never flows at all, verdict or not.

Intent: CONTRACT — v0.4.4 A3.1, A3.2, A3.5
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.protocols.git_object_reader import ScannedObject
from dadaia_workspace.features.chokepoints import Decision, push_gate_decision
from dadaia_workspace.features.chokepoints.service import PushRef, parse_push_refs

_SHA_A = "a" * 40
_ZERO = "0" * 40


class _EmptyObjectSource:
    """No denylist configured for these tests — the scan step is a pure pass-through."""

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        return ()


def _decide(refs: list[PushRef], root: Path, **kwargs: Any) -> Decision:
    """``push_gate_decision`` with a no-op object source unless a test overrides it —
    these tests exercise branch-policy behavior only. The v0.9.0 denylist scan is
    covered separately in ``test_push_denylist_scan.py``; the security verdict no
    longer lives on this path at all (A3.4)."""
    kwargs.setdefault("object_source", _EmptyObjectSource())
    kwargs.setdefault("repo", root)
    return push_gate_decision(refs, **kwargs)


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_refs("\n".join(lines))


# ---------------------------------------------------------------------------
# A3.1 case 1 — a feature/{M.m.p} push is allowed outright: no verdict, no handoff
# on disk needed anywhere (A3.4 — the check simply does not exist on this path).
# ---------------------------------------------------------------------------


def test_push_of_feature_branch_is_allowed(tmp_path: Path) -> None:
    decision = _decide(
        _refs(f"refs/heads/feature/0.0.0 {_SHA_A} refs/heads/feature/0.0.0 {_ZERO}"), tmp_path
    )
    assert decision.allowed, decision.message


# ---------------------------------------------------------------------------
# A3.1 case 2 — a develop push is refused outright, naming the PR path
# (feature/{M.m.p} → develop) — never conditional on any verdict.
# ---------------------------------------------------------------------------


def test_push_of_develop_is_refused_naming_the_pr_path(tmp_path: Path) -> None:
    decision = _decide(_refs(f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}"), tmp_path)
    assert not decision.allowed
    assert "develop" in decision.message
    assert "PR" in decision.message
    assert "feature/" in decision.message


# ---------------------------------------------------------------------------
# A3.1 case 3 — a main push is refused, naming the PR path (develop → main).
# ---------------------------------------------------------------------------


def test_push_of_main_is_refused_naming_the_pr_path(tmp_path: Path) -> None:
    decision = _decide(_refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"), tmp_path)
    assert not decision.allowed
    assert "main" in decision.message
    assert "develop" in decision.message
    assert "PR" in decision.message


# ---------------------------------------------------------------------------
# A3.1 case 4 / A3.2 — the retired `feature/v…` shape is refused as an invalid name;
# no second pattern anywhere resurrects the leading `v`.
# ---------------------------------------------------------------------------


def test_push_of_v_prefixed_feature_branch_is_refused(tmp_path: Path) -> None:
    decision = _decide(
        _refs(f"refs/heads/feature/v0.0.0 {_SHA_A} refs/heads/feature/v0.0.0 {_ZERO}"), tmp_path
    )
    assert not decision.allowed
    assert "feature/v0.0.0" in decision.message
    for pattern_word in ("main", "develop", "feature/"):
        assert pattern_word in decision.message


# ---------------------------------------------------------------------------
# G2 — the retired `hotfix/*` row is refused outright, exactly like any other name
# outside the three permitted patterns (never a distinct "local-only" kind anymore).
# ---------------------------------------------------------------------------


def test_push_of_hotfix_branch_is_refused_pattern_retired(tmp_path: Path) -> None:
    decision = _decide(
        _refs(f"refs/heads/hotfix/0.6.1 {_SHA_A} refs/heads/hotfix/0.6.1 {_ZERO}"), tmp_path
    )
    assert not decision.allowed
    for pattern_word in ("main", "develop", "feature/"):
        assert pattern_word in decision.message


# ---------------------------------------------------------------------------
# A2.2-equivalent — the tag carve-out survives byte-for-byte (publishing depends on it).
# ---------------------------------------------------------------------------


def test_tag_push_still_passes_with_no_verdict(tmp_path: Path) -> None:
    decision = _decide(_refs(f"refs/tags/v9.9.9 {_SHA_A} refs/tags/v9.9.9 {_ZERO}"), tmp_path)
    assert decision.allowed


# ---------------------------------------------------------------------------
# A branch outside the three patterns entirely is refused as an invalid NAME.
# ---------------------------------------------------------------------------


def test_push_of_unpatterned_branch_is_refused_naming_the_three_patterns(
    tmp_path: Path,
) -> None:
    decision = _decide(
        _refs(f"refs/heads/bugfix/whatever {_SHA_A} refs/heads/bugfix/whatever {_ZERO}"), tmp_path
    )
    assert not decision.allowed
    for pattern_word in ("main", "develop", "feature/"):
        assert pattern_word in decision.message


# ---------------------------------------------------------------------------
# The name validator accepts exactly the three permitted patterns.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "branch",
    ["main", "develop", "feature/0.6.0", "feature/12.0.3", "feature/1.22.333", "feature/0.0.0"],
)
def test_permitted_branch_names_are_accepted_by_the_validator(branch: str) -> None:
    from dadaia_workspace.features.chokepoints.service import branch_name_is_permitted

    assert branch_name_is_permitted(branch)


@pytest.mark.parametrize(
    "branch",
    [
        "bugfix/whatever",
        "release/0.6.0",
        "feature/v0.6.0",  # the retired `v` prefix
        "feature/0.6",  # not major.minor.patch
        "feature/0.6.0-rc1",  # suffixes are release-id territory, not branch names
        "hotfix/0.6.1",  # the retired hotfix pattern (G2)
        "hotfix/v0.6.1",
        "chore/cleanup",
        "developp",
        "Main",
    ],
)
def test_unpatterned_branch_names_are_rejected_by_the_validator(branch: str) -> None:
    from dadaia_workspace.features.chokepoints.service import branch_name_is_permitted

    assert not branch_name_is_permitted(branch)


# ---------------------------------------------------------------------------
# T-060-07 review findings, carried forward unchanged in spirit — the gate fails
# CLOSED and polices the REMOTE ref, now against the v2 pushable branch.
# ---------------------------------------------------------------------------


def test_malformed_stdin_fails_closed_naming_the_sanctioned_bypass(tmp_path: Path) -> None:
    """Finding 1: present-but-unparseable stdin must refuse, never silently allow.

    Empty stdin (nothing to gate) still allows; stdin whose lines cannot be parsed
    is a different case — the gate must fail CLOSED and name git's sanctioned,
    traceable bypass (--no-verify) instead of silently disabling the whole law.
    """
    from dadaia_workspace.features.chokepoints.service import parse_push_stdin

    refs, malformed = parse_push_stdin("this line has three fields\n")
    assert refs == []
    assert malformed == 1
    decision = _decide(refs, tmp_path, malformed_lines=malformed)
    assert not decision.allowed
    assert "--no-verify" in decision.message

    empty_refs, empty_malformed = parse_push_stdin("")
    assert empty_malformed == 0
    assert _decide(empty_refs, tmp_path, malformed_lines=0).allowed


def test_pushing_feature_branch_to_a_foreign_remote_ref_is_refused(tmp_path: Path) -> None:
    """Finding 2, carried forward: `git push origin feature/0.0.1:develop` — local
    feature branch, remote develop. The policy must key on BOTH sides: a valid local
    feature/{M.m.p} tip aimed at any remote ref other than its own name is a refusal."""
    decision = _decide(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/develop {_ZERO}"), tmp_path
    )
    assert not decision.allowed
    assert "refs/heads/develop" in decision.message
    assert "feature/0.0.1" in decision.message


def test_detached_head_ref_gets_a_pushable_branch_diagnosis(tmp_path: Path) -> None:
    """Finding 6, carried forward: `git push origin HEAD:feature/0.0.1` — right
    outcome needs the right words."""
    decision = _decide(_refs(f"HEAD {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"), tmp_path)
    assert not decision.allowed
    assert "feature/" in decision.message
