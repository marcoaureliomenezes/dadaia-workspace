"""The branch contract, read from the project gitflow (ADRs 0037, 0046; SPEC 0.5.0 AC6.5,
AC8.1): work branches ``<prefix><M.m.p>`` are pushable; the principal and integration
branches are PR-only; every refusal and its fix line name the CONFIGURED branches.
Tag pushes keep their carve-out. Every case runs under the default gitflow and a custom
one (``trunk``/``next``/``work/``) — no branch name is hard-coded in the gate.

Name validation itself is ``Gitflow.role_of`` (``tests/unit/core/test_gitflow.py``).

Intent: CONTRACT — AC6.5, AC8.1 (T-050-12); v0.4.4 A3.1, A3.5
"""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.gitflow import DEFAULT, Gitflow
from dadaia_workspace.core.models.git_scan import ScannedObject
from dadaia_workspace.features.chokepoints import Decision, push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import PushRef, parse_push_stdin
from dadaia_workspace.features.specs.canon import canon_violations

_SHA_A = "a" * 40
_ZERO = "0" * 40
_SHA_B = "b" * 40
_CUSTOM = Gitflow(principal="trunk", integration="next", work_prefix="work/")
_FLOWS = pytest.mark.parametrize("flow", [DEFAULT, _CUSTOM], ids=["default", "custom"])


class _EmptyObjectSource:
    """No object is new: the denylist and canon scans are pure pass-throughs here.
    ``contentless`` names the shas whose push publishes nothing (a birth candidate)."""

    def __init__(
        self, contentless: frozenset[str] = frozenset(), remote: frozenset[str] = frozenset()
    ) -> None:
        self.contentless = contentless
        self.remote = remote
        self.asked: list[str] = []

    def remote_branch(self, repo: Path, branch: str) -> bool:
        return branch in self.remote

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        return ()

    def publishes_nothing(self, repo: Path, sha: str) -> bool:
        self.asked.append(sha)
        return sha in self.contentless


def _decide(refs: list[PushRef], root: Path, flow: Gitflow = DEFAULT, **kwargs: Any) -> Decision:
    kwargs.setdefault("object_source", _EmptyObjectSource())
    kwargs.setdefault("repo", root)
    kwargs.setdefault("canon_violations_fn", canon_violations)
    return push_gate_decision(refs, gitflow=flow, **kwargs)


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_stdin("\n".join(lines))[0]


def _push(local: str, remote: str | None = None, remote_sha: str = _ZERO) -> list[PushRef]:
    return _refs(f"refs/heads/{local} {_SHA_A} refs/heads/{remote or local} {remote_sha}")


def _fix(decision: Decision) -> list[str]:
    return shlex.split(decision.message.rsplit("fix: ", 1)[1])


@_FLOWS
def test_work_branch_push_is_allowed(tmp_path: Path, flow: Gitflow) -> None:
    decision = _decide(_push(f"{flow.work_prefix}0.0.0"), tmp_path, flow)
    assert decision.allowed, decision.message


@_FLOWS
def test_integration_push_is_refused_naming_the_pr_from_a_work_branch(
    tmp_path: Path, flow: Gitflow
) -> None:
    decision = _decide(_push(flow.integration, remote_sha=_SHA_B), tmp_path, flow)
    assert not decision.allowed
    assert f"'{flow.integration}'" in decision.message
    assert _fix(decision) == [
        "gh",
        "pr",
        "create",
        "--base",
        flow.integration,
        "--head",
        f"{flow.work_prefix}<M.m.p>",
    ]


@_FLOWS
def test_principal_push_is_refused_naming_the_pr_from_integration(
    tmp_path: Path, flow: Gitflow
) -> None:
    decision = _decide(_push(flow.principal, remote_sha=_SHA_B), tmp_path, flow)
    assert not decision.allowed
    assert f"'{flow.principal}'" in decision.message
    assert _fix(decision) == [
        "gh",
        "pr",
        "create",
        "--base",
        flow.principal,
        "--head",
        flow.integration,
    ]


@_FLOWS
@pytest.mark.parametrize("name", ["bugfix/x", "hotfix/0.6.1", "{prefix}v0.0.0", "{prefix}0.6"])
def test_a_branch_outside_the_gitflow_is_refused_naming_the_work_branch(
    tmp_path: Path, flow: Gitflow, name: str
) -> None:
    branch = name.format(prefix=flow.work_prefix)
    decision = _decide(_push(branch), tmp_path, flow)
    assert not decision.allowed
    assert branch in decision.message
    for word in (flow.principal, flow.integration, flow.work_prefix):
        assert word in decision.message
    work = f"{flow.work_prefix}<M.m.p>"
    assert _fix(decision) == [
        "git",
        "checkout",
        "-b",
        work,
        flow.principal,
    ]  # one command: no `&&` (Windows PowerShell 5.1)


def test_the_default_names_are_ordinary_branches_under_a_custom_gitflow(tmp_path: Path) -> None:
    assert not _decide(_push("feature/0.0.0"), tmp_path, _CUSTOM).allowed
    assert "trunk" in _decide(_push("main"), tmp_path, _CUSTOM).message


@_FLOWS
@pytest.mark.parametrize("role", ["principal", "integration"])
def test_a_contentless_birth_of_principal_or_integration_passes(
    tmp_path: Path, flow: Gitflow, role: str
) -> None:
    """ADR 0036: an orphan empty root pushed as the principal, or `git branch <integration>
    <principal>` pushed, creates the remote branch and publishes nothing."""
    source = _EmptyObjectSource(frozenset({_SHA_A}))
    decision = _decide(_push(getattr(flow, role)), tmp_path, flow, object_source=source)
    assert decision.allowed, decision.message
    assert source.asked == [_SHA_A]


@_FLOWS
@pytest.mark.parametrize(
    ("role", "other"), [("principal", "integration"), ("integration", "principal")]
)
def test_a_birth_carrying_a_commit_is_refused_naming_a_birth_at_the_other_published_tip(
    tmp_path: Path, flow: Gitflow, role: str, other: str
) -> None:
    """Review M2: birth at the other role's published tip (publishes nothing) — one
    command, no `&&` (Windows PowerShell 5.1 has none)."""
    branch, tip = getattr(flow, role), getattr(flow, other)
    source = _EmptyObjectSource(remote=frozenset({tip}))
    decision = _decide(_push(branch), tmp_path, flow, object_source=source)
    assert not decision.allowed
    assert _fix(decision) == [
        "git", "push", "origin", f"refs/remotes/origin/{tip}:refs/heads/{branch}",
    ]  # fmt: skip


@_FLOWS
def test_a_birth_fix_never_names_an_absent_remote_ref(tmp_path: Path, flow: Gitflow) -> None:
    """ADR 0048: with no published other role the fix is the work-branch route."""
    decision = _decide(_push(flow.principal), tmp_path, flow)
    assert not decision.allowed
    assert _fix(decision) == ["git", "push", "origin", flow.work_pattern]


def test_an_existing_principal_is_never_a_birth(tmp_path: Path) -> None:
    source = _EmptyObjectSource(frozenset({_SHA_A}))
    refs = _push("main", remote_sha=_SHA_B)
    decision = _decide(refs, tmp_path, object_source=source)
    assert not decision.allowed
    assert source.asked == []


def test_a_contentless_birth_passes_from_any_source(tmp_path: Path) -> None:
    """Review H4: baseline pushes `<sha>:refs/heads/<b>` — the birth is judged by the
    remote branch it creates and what it publishes, never by the local ref's name."""
    source = _EmptyObjectSource(frozenset({_SHA_A}))
    assert _decide(_push("main", "develop"), tmp_path, object_source=source).allowed
    sha_birth = _refs(f"{_SHA_A} {_SHA_A} refs/heads/develop {_ZERO}")
    assert _decide(sha_birth, tmp_path, object_source=source).allowed


def test_tag_push_still_passes(tmp_path: Path) -> None:
    decision = _decide(_refs(f"refs/tags/v9.9.9 {_SHA_A} refs/tags/v9.9.9 {_ZERO}"), tmp_path)
    assert decision.allowed


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
    decision = _decide(_push("work/0.0.1", "work/0.0.2"), tmp_path, _CUSTOM)
    assert not decision.allowed
    assert "refs/heads/work/0.0.2" in decision.message
    assert _fix(decision) == ["git", "push", "origin", "work/0.0.2:work/0.0.2"]
    assert not _decide(_push("work/0.0.1", "next"), tmp_path, _CUSTOM).allowed


def test_detached_head_ref_gets_a_pushable_branch_diagnosis(tmp_path: Path) -> None:
    """Finding 6, carried forward: `git push origin HEAD:feature/0.0.1` — right
    outcome needs the right words."""
    decision = _decide(_refs(f"HEAD {_SHA_A} refs/heads/work/0.0.1 {_ZERO}"), tmp_path, _CUSTOM)
    assert not decision.allowed
    assert _fix(decision)[:4] == ["git", "checkout", "-b", "work/<M.m.p>"]


@pytest.mark.parametrize("remote_sha", [_ZERO, _SHA_B], ids=["new-branch", "existing"])
def test_a_rewrite_refusal_fix_is_non_interactive(tmp_path: Path, remote_sha: str) -> None:
    """Review L1: the range-rewrite fix squashes the refused range onto what the remote
    already has — no `git rebase -i`, which an agent cannot drive."""
    from dadaia_workspace.features.chokepoints.push_gate import _rewrite_fix

    ref = PushRef("refs/heads/work/0.0.1", _SHA_A, "refs/heads/work/0.0.1", remote_sha)
    base = remote_sha if remote_sha != _ZERO else "refs/remotes/origin/next"
    argv = shlex.split(_rewrite_fix(ref, _CUSTOM))
    assert argv[:4] == ["git", "reset", "--soft", base] and "-i" not in argv
    assert argv[4:7] == ["&&", "git", "commit"]
