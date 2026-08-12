"""T-060-04 (v0.6.0 FR4): develop-only push policy + four-pattern branch validation.

The gitflow law (DADAIA.md §5/§6, operator ruling 2026-08-12): exactly four branch
patterns exist — ``main``, ``develop``, ``feature/vM.m.p``, ``hotfix/vM.m.p`` — and
``develop`` is the ONLY pushable branch. ``main`` advances via PR only; feature and
hotfix branches live local-only. Tag pushes keep their DP-5 carve-out (publishing
depends on it). The security verdict covers the ``origin/develop..develop`` delta,
anchored on the pushed ``develop`` tip sha.

All seven A4.1 cases live here. Written RED-first: against the pre-v0.6.0 gate, the
refusal cases pass the gate (it had no branch policy at all) and the validator does
not exist.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.service import PushRef, parse_push_refs

_SHA_A = "a" * 40
_ZERO = "0" * 40


def _handoff(root: Path, name: str, *, commit_sha: str = _SHA_A) -> None:
    ctx_dir = root / "demo-ctx"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": "security-reviewer",
        "context": "demo-ctx",
        "produced_at": "2026-08-12T12:00:00Z",
        "artifact": {"type": "other"},
        "metrics": {"commit_sha": commit_sha},
        "verdict": "APPROVED",
    }
    (ctx_dir / f"{name}.handoff.json").write_text(json.dumps(payload), encoding="utf-8")


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_refs("\n".join(lines))


# ---------------------------------------------------------------------------
# A4.1 cases 1-2: main and feature refs are refused EVEN WITH a covering verdict
# ---------------------------------------------------------------------------


def test_push_of_main_is_refused_even_with_approved_verdict(tmp_path: Path) -> None:
    _handoff(tmp_path, "approve-a")
    decision = push_gate_decision(
        tmp_path, _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}")
    )
    assert not decision.allowed
    # A4.2: the message names the rule, the permitted value, and the corrective action.
    assert "main" in decision.message
    assert "develop" in decision.message
    assert "PR" in decision.message


def test_push_of_feature_branch_is_refused_as_local_only(tmp_path: Path) -> None:
    _handoff(tmp_path, "approve-a")
    decision = push_gate_decision(
        tmp_path, _refs(f"refs/heads/feature/v0.6.0 {_SHA_A} refs/heads/feature/v0.6.0 {_ZERO}")
    )
    assert not decision.allowed
    assert "local-only" in decision.message
    assert "merge" in decision.message.lower()
    assert "develop" in decision.message


# ---------------------------------------------------------------------------
# A4.1 cases 3-4: develop pushes hinge on a covering APPROVED verdict
# ---------------------------------------------------------------------------


def test_develop_push_with_covering_verdict_is_allowed(tmp_path: Path) -> None:
    _handoff(tmp_path, "approve-a", commit_sha=_SHA_A)
    decision = push_gate_decision(
        tmp_path, _refs(f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}")
    )
    assert decision.allowed


def test_develop_push_without_covering_verdict_is_refused(tmp_path: Path) -> None:
    # An APPROVE exists but for a DIFFERENT sha — it does not cover this delta.
    _handoff(tmp_path, "approve-stale", commit_sha="b" * 40)
    decision = push_gate_decision(
        tmp_path, _refs(f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}")
    )
    assert not decision.allowed
    # The refusal teaches the diff-based contract.
    assert "origin/develop..develop" in decision.message
    assert "security-reviewer" in decision.message


# ---------------------------------------------------------------------------
# A4.1 case 5: the tag carve-out survives byte-for-byte (publishing depends on it)
# ---------------------------------------------------------------------------


def test_tag_push_still_passes_with_no_verdict(tmp_path: Path) -> None:
    decision = push_gate_decision(
        tmp_path, _refs(f"refs/tags/v9.9.9 {_SHA_A} refs/tags/v9.9.9 {_ZERO}")
    )
    assert decision.allowed


# ---------------------------------------------------------------------------
# A4.1 case 6: a branch outside the four patterns is refused as an invalid NAME
# ---------------------------------------------------------------------------


def test_push_of_unpatterned_branch_is_refused_naming_the_four_patterns(
    tmp_path: Path,
) -> None:
    _handoff(tmp_path, "approve-a")
    decision = push_gate_decision(
        tmp_path, _refs(f"refs/heads/bugfix/whatever {_SHA_A} refs/heads/bugfix/whatever {_ZERO}")
    )
    assert not decision.allowed
    for pattern_word in ("main", "develop", "feature/", "hotfix/"):
        assert pattern_word in decision.message


# ---------------------------------------------------------------------------
# A4.1 case 7: the name validator accepts exactly the four permitted patterns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "branch",
    ["main", "develop", "feature/v0.6.0", "hotfix/v0.6.1", "feature/v12.0.3", "hotfix/v1.22.333"],
)
def test_permitted_branch_names_are_accepted_by_the_validator(branch: str) -> None:
    from dadaia_workspace.features.chokepoints.service import branch_name_is_permitted

    assert branch_name_is_permitted(branch)


@pytest.mark.parametrize(
    "branch",
    [
        "bugfix/whatever",
        "release/v0.6.0",
        "feature/0.6.0",  # missing the v — the release-id canon carries it
        "feature/v0.6",  # not major.minor.patch
        "hotfix/v0.6.0-rc1",  # suffixes are release-id territory, not branch names
        "chore/cleanup",
        "developp",
        "Main",
    ],
)
def test_unpatterned_branch_names_are_rejected_by_the_validator(branch: str) -> None:
    from dadaia_workspace.features.chokepoints.service import branch_name_is_permitted

    assert not branch_name_is_permitted(branch)
