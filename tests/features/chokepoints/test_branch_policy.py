"""The branch contract, read from the project gitflow (ADRs 0036, 0037, 0046; SPEC 0.5.0 AC6.5,
AC8.1): work branches ``<prefix><M.m.p>`` are pushable; the principal and integration
branches are PR-only; every refusal and its fix line name the CONFIGURED branches.
Every row runs under the default gitflow or a custom one (``trunk``/``next``/``work/``).
"""

from __future__ import annotations

import shlex
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from dadaia_workspace.core.gitflow import DEFAULT, Gitflow
from dadaia_workspace.features.chokepoints import Decision, push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import (
    check_branch_policy,
    parse_push_stdin,
)
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.features.specs.doctor_adr import cites_an_accepted_adr
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from tests.fakes import gate_fixes
from tests.fixtures.real_git import PushRepo

_A = "a" * 40
_B = "b" * 40
_ZERO = "0" * 40
_CUSTOM = Gitflow(principal="trunk", integration="next", work_prefix="work/")
Scenario = Callable[[PushRepo, Gitflow], str]


@pytest.fixture()
def repo(tmp_path: Path) -> PushRepo:
    return PushRepo(tmp_path)


def _decide(stdin: str, repo: PushRepo, flow: Gitflow) -> Decision:
    refs, malformed = parse_push_stdin(stdin)
    return push_gate_decision(
        refs, gitflow=flow, fixes=replace(gate_fixes(), work=f"{flow.work_prefix}0.6.0"), object_source=GitSubprocessObjectReader(),
        repo=repo.path, canon_violations_fn=canon_violations, cites_accepted_adr=cites_an_accepted_adr(None), malformed_lines=malformed,
    )  # fmt: skip


def _line(local: str, remote: str | None = None, remote_sha: str = _ZERO, sha: str = _A) -> str:
    return f"refs/heads/{local} {sha} refs/heads/{remote or local} {remote_sha}"


def _fix(decision: Decision) -> list[str]:
    return shlex.split(decision.message.rsplit("fix: ", 1)[1])


def _birth(role: str) -> Scenario:
    def run(repo: PushRepo, flow: Gitflow) -> str:
        repo.commit({"a.md": "a\n"})
        sha = repo.publish(flow.integration if role == "principal" else flow.principal)
        return _line(getattr(flow, role), sha=sha)

    return run


def _birth_with_commit(role: str, other: str) -> Scenario:
    def run(repo: PushRepo, flow: Gitflow) -> str:
        repo.commit({"a.md": "a\n"})
        repo.publish(getattr(flow, other))
        return _line(getattr(flow, role), sha=repo.commit({"b.md": "b\n"}))

    return run


def _existing_principal(repo: PushRepo, flow: Gitflow) -> str:
    repo.commit({"a.md": "a\n"})
    sha = repo.publish(flow.principal)
    return _line(flow.principal, remote_sha=sha, sha=sha)


def _birth_from_any_source(repo: PushRepo, flow: Gitflow) -> str:
    """Review H4: judged by the remote branch it creates and what it publishes, never the local name."""
    repo.commit({"a.md": "a\n"})
    sha = repo.publish()
    return f"{_line('main', 'develop', sha=sha)}\n{sha} {sha} refs/heads/develop {_ZERO}"


def _feature_to_published_integration(repo: PushRepo, flow: Gitflow) -> str:
    repo.commit({"a.md": "a\n"})
    repo.publish("trunk")
    return _line("work/0.0.1", "next")


def _commit_then(line: Callable[[str, Gitflow], str]) -> Scenario:
    return lambda repo, flow: line(repo.commit({"a.md": "a\n"}), flow)


_D, _C = DEFAULT, _CUSTOM


# fmt: off
@pytest.mark.parametrize(("flow", "scenario"), [
    pytest.param(_D, _commit_then(lambda s, f: _line(f"{f.work_prefix}0.0.0", sha=s)), id="default-work-branch"),
    pytest.param(_C, _commit_then(lambda s, f: _line(f"{f.work_prefix}0.0.0", sha=s)), id="custom-work-branch"),
    pytest.param(_D, _commit_then(lambda s, f: _line(f.principal, sha=s)), id="default-R13-empty-origin-admits-principal"),
    pytest.param(_C, _commit_then(lambda s, f: _line(f.principal, sha=s)), id="custom-R13-empty-origin-admits-principal"),
    pytest.param(_D, _birth("principal"), id="default-ADR0036-contentless-principal-birth"),
    pytest.param(_C, _birth("principal"), id="custom-ADR0036-contentless-principal-birth"),
    pytest.param(_D, _birth("integration"), id="default-ADR0036-contentless-integration-birth"),
    pytest.param(_C, _birth("integration"), id="custom-ADR0036-contentless-integration-birth"),
    pytest.param(_D, _birth_from_any_source, id="H4-contentless-birth-from-any-source"),
    pytest.param(_D, _commit_then(lambda s, f: f"refs/heads/wt/x {s} refs/tags/archive/wt/x {_ZERO}"), id="tag-carve-out-keys-on-the-remote-ref"),
    pytest.param(_D, lambda repo, flow: "", id="finding-1-empty-stdin-has-nothing-to-gate"),
])
# fmt: on
def test_the_gate_allows(repo: PushRepo, flow: Gitflow, scenario: Scenario) -> None:
    decision = _decide(scenario(repo, flow), repo, flow)
    assert decision.allowed, decision.message


_WORK = "{prefix}0.6.0"  # the live work branch, never the <M.m.p> pattern (fix-lines-are-not-one-runnable-command)
_PR_TO_INTEGRATION = ["Operator", "action:", "open", "a", "PR/MR", "from", _WORK, "into", "{integration}", "on", "your", "git", "host"]
_PR_TO_PRINCIPAL = ["Operator", "action:", "open", "a", "PR/MR", "from", "{integration}", "into", "{principal}", "on", "your", "git", "host"]


def _birth_fix(tip: str, role: str) -> list[str]:
    return ["git", "-C", "/repo", "push", "origin", f"refs/remotes/origin/{{{tip}}}:refs/heads/{{{role}}}"]


# fmt: off
@pytest.mark.parametrize(("flow", "scenario", "named", "fix"), [
    pytest.param(_D, lambda r, f: _line(f.integration, remote_sha=_B), "'{integration}'", _PR_TO_INTEGRATION, id="default-integration-is-PR-only"),
    pytest.param(_C, lambda r, f: _line(f.integration, remote_sha=_B), "'{integration}'", _PR_TO_INTEGRATION, id="custom-integration-is-PR-only"),
    pytest.param(_D, lambda r, f: _line(f.principal, remote_sha=_B), "'{principal}'", _PR_TO_PRINCIPAL, id="default-principal-is-PR-only"),
    pytest.param(_C, lambda r, f: _line(f.principal, remote_sha=_B), "'{principal}'", _PR_TO_PRINCIPAL, id="custom-principal-is-PR-only"),
    pytest.param(_D, lambda r, f: f"refs/tags/v1 {_A} refs/heads/{f.principal} {_B}", "'{principal}'", _PR_TO_PRINCIPAL, id="a-local-tag-onto-the-principal-is-PR-only"),
    pytest.param(_D, _birth_with_commit("principal", "integration"), "", _birth_fix("integration", "principal"), id="default-M2-principal-birth-carrying-a-commit"),
    pytest.param(_C, _birth_with_commit("principal", "integration"), "", _birth_fix("integration", "principal"), id="custom-M2-principal-birth-carrying-a-commit"),
    pytest.param(_D, _birth_with_commit("integration", "principal"), "", _birth_fix("principal", "integration"), id="default-M2-integration-birth-carrying-a-commit"),
    pytest.param(_C, _birth_with_commit("integration", "principal"), "", _birth_fix("principal", "integration"), id="custom-M2-integration-birth-carrying-a-commit"),
    pytest.param(_D, _existing_principal, "", None, id="an-existing-principal-is-never-a-birth"),
    pytest.param(_C, lambda r, f: _line("work/0.0.1", "work/0.0.2"), "refs/heads/work/0.0.2",
                 ["git", "-C", "/repo", "branch", "-m", "work/0.0.1", "work/0.0.2"], id="finding-2-work-branch-to-a-foreign-remote-ref"),
    pytest.param(_C, _feature_to_published_integration, "", None, id="finding-2-work-branch-to-the-integration-ref"),
    pytest.param(_C, lambda r, f: f"HEAD {_A} refs/heads/work/0.0.1 {_ZERO}", "",
                 ["git", "-C", "/repo", "switch", "-c", "work/0.6.0", _A], id="finding-6-detached-head-cuts-the-work-branch"),
    pytest.param(_D, lambda r, f: "this line has three fields", "", None, id="finding-1-malformed-stdin-fails-closed"),
])
# fmt: on
def test_the_gate_refuses_with_the_configured_fix(
    repo: PushRepo, flow: Gitflow, scenario: Scenario, named: str, fix: list[str] | None
) -> None:
    """Each refusal names the configured branches; its fix is one command, no `&&` (PowerShell 5.1 has none)."""
    names = {"principal": flow.principal, "integration": flow.integration, "prefix": flow.work_prefix}
    decision = _decide(scenario(repo, flow), repo, flow)
    assert not decision.allowed
    assert named.format(**names) in decision.message
    assert fix is None or _fix(decision) == [part.format(**names) for part in fix]


# fmt: off
@pytest.mark.parametrize(("flow", "branch"), [
    *[pytest.param(f, n, id=f"{i}-{n}") for f, i in ((_D, "default"), (_C, "custom"))
      for n in ("bugfix/x", "hotfix/0.6.1", f"{f.work_prefix}v0.0.0", f"{f.work_prefix}0.6")],
    *[pytest.param(_D, n, id=f"default-no-role-{n}") for n in ("feature/0.6.0-rc1", "Main", "developp", "release/0.6.0", "chore/cleanup")],
    pytest.param(_C, "feature/0.0.0", id="custom-default-work-name-is-ordinary"),
    pytest.param(_C, "main", id="custom-default-principal-name-is-ordinary"),
])
# fmt: on
def test_a_branch_outside_the_gitflow_is_refused_naming_the_work_branch(
    repo: PushRepo, flow: Gitflow, branch: str
) -> None:
    """AC6.1/AC6.5: a name that is not exactly the principal, the integration or prefix + M.m.p has no role.

    The fix is one command from any cwd carrying the refused commit (review H-C).
    """
    decision = _decide(_line(branch), repo, flow)
    assert not decision.allowed
    assert "outside the gitflow" in decision.message
    assert all(word in decision.message for word in (branch, flow.principal, flow.integration, flow.work_prefix))
    assert _fix(decision) == ["git", "-C", "/repo", "switch", "-c", f"{flow.work_prefix}0.6.0", _A]


def test_an_outside_ref_is_carried_onto_the_live_work_branch() -> None:
    """Review 5 M2: the live work branch may have diverged — switch to it and merge (append-only, never a rebase)."""
    refs = parse_push_stdin(_line("topic"))[0]
    decision = check_branch_policy(refs, _CUSTOM, replace(gate_fixes(), work="work/1.2.3", cut=True))
    assert decision is not None and "'work/1.2.3'" in decision.message
    assert f"merge {_A}" in decision.message
    assert _fix(decision) == ["git", "-C", "/repo", "switch", "work/1.2.3"]


@pytest.mark.parametrize(
    ("branch", "allowed"),
    [
        pytest.param("wt/0.5.0-rc9/job2", True),
        ("wt/0.5.0-rc9/define", False),
        ("wt/backlog/an-idea", True),
        ("wt/0.5.0-rc9/job2--T-1", False),
        ("wt/0.5.0a-impl", False),
    ],
)
def test_only_a_job_branch_of_wt_is_pushable(branch: str, allowed: bool) -> None:
    """AC1.2 (ADR 0190): pre-push accepts a job branch `wt/<M.m.p>-rc<N>/<job>` and a
    `wt/backlog/<slug>` branch, no other `wt/` branch."""
    refs, _ = parse_push_stdin(_line(branch))
    decision = check_branch_policy(refs, DEFAULT, replace(gate_fixes(), work="feature/0.5.0"))
    assert (decision is None) is allowed
