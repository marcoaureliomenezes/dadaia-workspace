"""The derived onboarding step list — one fixture per step, plus its invariant.

Size: SMALL (unit): the
two git reads (``published``, ``work_version``) are patched at the adapter; the real-git behaviour is the property test's.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.gitflow import SeveralWorkBranches
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION, state
from dadaia_workspace.features.specs.rules import RULES
from dadaia_workspace.features.workspace.onboarding import next_step

_CLIENT = "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient"  # by name: importing it would size the module medium
_SCAFFOLD = workspace_layout.public_scripts_dir().parent / "scaffold"


@pytest.fixture(autouse=True)
def _git(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    remote = {"published": False}
    monkeypatch.setattr(f"{_CLIENT}.published", lambda _s, _p: remote["published"])
    monkeypatch.setattr(f"{_CLIENT}.work_version", lambda _s, _p: "0.1.0")
    return remote


def _specs(tmp_path: Path, name: str = "app", *, audited: bool = False) -> Path:
    specs = tmp_path / "repos" / name / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    stamp = f"---\nspecs_pattern_version: {CANONICAL_SPECS_VERSION}\n---\n# c\n"
    (specs / "constitution.md").write_text(stamp, "utf-8")
    for stub in ("ARCHITECTURE.md", "QUALITY.md"):
        shutil.copyfile(_SCAFFOLD / "memory" / stub, specs / "memory" / stub)
    if audited:
        for stub in ("ARCHITECTURE.md", "QUALITY.md"):
            (specs / "memory" / stub).write_text(f"# {stub}\n\nreal content\n", "utf-8")
        (specs / "memory" / "product" / "catalog.json").write_text(
            json.dumps({"features": [{"slug": "x"}]}), "utf-8"
        )
    return specs


def _bare(tmp: Path) -> dict[str, Path]:
    return {"app": tmp / "repos" / "app" / "specs"}


def _foreign(tmp: Path) -> dict[str, Path]:
    (tmp / "repos" / "app" / "specs" / "features").mkdir(parents=True)
    return _bare(tmp)


def _typo(tmp: Path) -> dict[str, Path]:
    specs = _specs(tmp, audited=True)
    (specs / "constitution.md").write_text(
        "---\nspecs_pattern_version: 7\ngitflow: {principal: main\n---\n"
    )
    return {"app": specs}


def _v047(tmp: Path) -> dict[str, Path]:
    specs = _specs(tmp, audited=True)
    (specs / "constitution.md").write_text("---\nspecs_pattern_version: 7\n---\n# c\n", "utf-8")
    return {"app": specs}


_CMD = "command"


# fmt: off
@pytest.mark.parametrize(("trees", "kwargs", "published", "expected", "command", "in_command"), [
    pytest.param(lambda t: {}, {}, False, ("context", _CMD), None, ["Agent action: run {} with a context name and --main-repo set to the main repo's clone URL"], id="zero-contexts"),
    pytest.param(_bare, {}, False, ("specs", _CMD), ("specs", "init", "--context", "app"), [], id="S1-no-identity-no-bind-step"),
    pytest.param(_bare, {"bound": False}, False, ("bind", _CMD), ("context", "bind", "app"), [], id="S1-unbound-session-binds"),
    pytest.param(_bare, {"bound": True}, False, ("specs", _CMD), ("specs", "init", "--context", "app"), [], id="S1-bound-is-past-bind"),
    pytest.param(_foreign, {}, False, ("specs", _CMD), ("specs", "init", "--context", "app", "--replace-foreign"), [], id="B28-4-foreign-tree-replace-foreign"),
    pytest.param(_v047, {}, False, ("specs", _CMD), ("specs", "init", "--context", "app"), [], id="upgrade-leaves-project-specs-unmigrated-and-silent-0.4.7-tree"),
    pytest.param(_typo, {}, False, ("constitution", "agent"), None, ["repos/app/specs/constitution.md"], id="ADR0047-yaml-typo-is-an-agent-repair"),
    pytest.param(lambda t: {"app": _specs(t)}, {}, False, ("first-pass", "agent"), None,
                 ["then run the dd-audit-project first pass in it", "memory/QUALITY.md", "no atom"], id="shipped-stubs-first-pass"),
    pytest.param(lambda t: {"app": _specs(t, audited=True)}, {}, False, ("publish", _CMD), ("context", "baseline", "app"), [], id="publish-until-on-a-remote"),
    pytest.param(lambda t: {"app": _specs(t, audited=True)}, {}, True, None, None, [], id="published-is-done"),
    pytest.param(lambda t: {"app": _specs(t, audited=True), "other": t / "repos" / "other" / "specs"}, {"focus": "app", "bound": True}, True, None, None, [], id="onboarding-next-step-names-another-context"),
    pytest.param(lambda t: {"new": t / "repos" / "new" / "specs", "app": _specs(t)}, {}, False, None, None, [], id="two-contexts-no-focus-judges-none"),
    pytest.param(lambda t: {"new": t / "repos" / "new" / "specs", "app": _specs(t)}, {"bound": False}, False, None, None, [], id="two-contexts-unbound-names-no-bind-target"),
    pytest.param(lambda t: {"y": _specs(t, "y")}, {"focus": "x"}, False, None, None, [], id="missing-focus-never-falls-back"),
    pytest.param(lambda t: {"new": t / "repos" / "new" / "specs", "app": _specs(t)}, {"focus": "app"}, False, ("first-pass", "agent"), None, [], id="focus-context-answers-first"),
])
# fmt: on
def test_next_step_is_derived_from_the_workspace_state(
    tmp_path: Path, _git: dict[str, bool], trees: Callable[[Path], dict[str, Path]], kwargs: dict[str, object],
    published: bool, expected: tuple[str, str] | None, command: tuple[str, ...] | None, in_command: list[str],
) -> None:  # fmt: skip
    """The ``bind`` step judges the caller's Bind (no identity, no step). The specs fix is
    state()'s; a typo is never a move."""
    _git["published"] = published
    step = next_step(tmp_path, trees(tmp_path), **kwargs)  # type: ignore[arg-type]
    assert (step and (step.id, step.kind)) == expected
    if step is None:
        return
    if command:
        assert step.command == fix_line(tmp_path, *command)
    create = fix_line(tmp_path, "context", "create")  # the binary every OS prints, {} in a row
    assert all(part.format(create) in step.command for part in in_command)


def test_the_first_pass_fix_opens_the_backlog_first_pass_lane(tmp_path: Path) -> None:
    specs = _specs(tmp_path, "proj")  # the repo slug differs from the context name
    step = next_step(tmp_path, {"app": specs})
    memory = specs / "memory"
    pending = f"{memory / 'ARCHITECTURE.md'}, {memory / 'QUALITY.md'}, {memory / 'product'} (no atom)"
    lane = fix_line(tmp_path, "worktree", "new", "proj", "0.1.0/wt-backlog-first-pass")
    assert step is not None
    assert step.command == (
        f"Agent action: open the lane {lane}, then run the dd-audit-project first pass in it — {pending}"
    )


def test_the_specs_step_reports_state_and_the_doctor_has_no_specs_version_code(tmp_path: Path) -> None:
    """ONBOARDING reports the state; the doctor has no SPECS-VERSION code."""
    specs = _foreign(tmp_path)["app"]
    step = next_step(tmp_path, {"app": specs})
    assert step is not None and step.command == state(specs, root=tmp_path, context="app")[1]
    assert "specs tree is foreign" in step.reason
    assert not any("SPECS-VERSION" in rule.codes for rule in RULES)


def test_i1_an_audits_histo_stamp_changes_no_step(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    before = next_step(tmp_path, {"app": specs})
    histo = specs / "audits" / "_archive" / "audits_histo.jsonl"
    histo.parent.mkdir(parents=True)
    histo.write_text('{"id": "first"}\n', encoding="utf-8")
    assert next_step(tmp_path, {"app": specs}) == before


def test_the_text_names_the_kind_and_carries_one_fix_line(tmp_path: Path) -> None:
    step = next_step(tmp_path, {})
    assert step is not None
    head, fix = step.text().split("\n")
    assert head.startswith("Next (command step context): ") and fix == f"fix: {step.command}"


@pytest.mark.parametrize(
    ("fix", "first"),
    [
        (
            "Agent action: run `git -C /r switch feature/0.2.0`, then run `git -C /r branch -d feature/0.1.0`",
            "run `git -C /r switch feature/0.2.0`, then run `git -C /r branch -d feature/0.1.0`",
        ),
        (
            "Agent action: run `git -C /r switch feature/0.2.0`, then merge feature/0.1.0 into feature/0.2.0, then run `git -C /r branch -d feature/0.1.0`",
            "run `git -C /r switch feature/0.2.0`, then merge feature/0.1.0 into feature/0.2.0, then run `git -C /r branch -d feature/0.1.0`",
        ),
    ],
)
def test_several_work_branches_make_the_first_pass_an_agent_step_with_the_refusals_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fix: str, first: str
) -> None:
    several = load_owner("dd-gitflow-default", "_worktree_git").SeveralWork(
        "2 work branches", fix, "0.2.0"
    )

    def refuse(_s: object, _p: object) -> str:
        raise SeveralWorkBranches(several)

    monkeypatch.setattr(f"{_CLIENT}.work_version", refuse)
    specs = _specs(tmp_path, "proj")
    step = next_step(tmp_path, {"app": specs})
    memory = specs / "memory"
    pending = f"{memory / 'ARCHITECTURE.md'}, {memory / 'QUALITY.md'}, {memory / 'product'} (no atom)"
    lane = fix_line(tmp_path, "worktree", "new", "proj", "0.2.0/wt-backlog-first-pass")
    assert step is not None and (step.id, step.kind) == ("first-pass", "agent")
    assert step.command == (
        f"Agent action: {first}, then open the lane {lane}, then run the dd-audit-project first pass in it — {pending}"
    )
    assert step.text().count("fix:") == 1
