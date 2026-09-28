"""The derived onboarding step list — one fixture per step, plus I1.

Intent: CONTRACT — AC1.1, AC1.2, AC3.1, AC4.1, AC7.2 (T-050-17). Size: SMALL (unit): the
one git read is patched at the adapter; the real-git behaviour is the property test's.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.specs_version import state
from dadaia_workspace.features.specs.rules import RULES
from dadaia_workspace.features.workspace.onboarding import next_step
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

_SCAFFOLD = workspace_layout.public_scripts_dir().parent / "scaffold"


@pytest.fixture(autouse=True)
def _git(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    remote = {"published": False}
    monkeypatch.setattr(GitSubprocessClient, "published", lambda _s, _p: remote["published"])
    return remote


def _specs(tmp_path: Path, name: str = "app", *, audited: bool = False) -> Path:
    specs = tmp_path / "repos" / name / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "constitution.md").write_text("---\nspecs_pattern_version: 7\n---\n# c\n", "utf-8")
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


_CMD = "command"


# fmt: off
@pytest.mark.parametrize(("trees", "kwargs", "published", "expected", "command", "in_command"), [
    pytest.param(lambda t: {}, {}, False, ("context", _CMD), ("context", "create", "<name>", "--main-repo", "<clone-url>"), [], id="zero-contexts"),
    pytest.param(_bare, {}, False, ("specs", _CMD), ("specs", "init", "--context", "app"), [], id="S1-no-identity-no-bind-step"),
    pytest.param(_bare, {"bound": False}, False, ("bind", _CMD), ("context", "bind", "app"), [], id="S1-unbound-session-binds"),
    pytest.param(_bare, {"bound": True}, False, ("specs", _CMD), ("specs", "init", "--context", "app"), [], id="S1-bound-is-past-bind"),
    pytest.param(_foreign, {}, False, ("specs", _CMD), ("specs", "init", "--context", "app", "--replace-foreign"), [], id="B28-4-foreign-tree-replace-foreign"),
    pytest.param(_typo, {}, False, ("constitution", "agent"), None, ["repos/app/specs/constitution.md"], id="ADR0047-yaml-typo-is-an-agent-repair"),
    pytest.param(lambda t: {"app": _specs(t)}, {}, False, ("first-pass", "agent"), None,
                 [".agents/skills/dd-audit-project/SKILL.md §first pass", "memory/QUALITY.md", "no atom"], id="shipped-stubs-first-pass"),
    pytest.param(lambda t: {"app": _specs(t, audited=True)}, {}, False, ("publish", _CMD), ("context", "baseline", "app"), [], id="publish-until-on-a-remote"),
    pytest.param(lambda t: {"app": _specs(t, audited=True)}, {}, True, None, None, [], id="published-is-done"),
    pytest.param(lambda t: {"new": t / "repos" / "new" / "specs", "app": _specs(t)}, {}, False, ("specs", _CMD), ("specs", "init", "--context", "new"), [], id="first-context-answers-first"),
    pytest.param(lambda t: {"new": t / "repos" / "new" / "specs", "app": _specs(t)}, {"focus": "app"}, False, ("first-pass", "agent"), None, [], id="focus-context-answers-first"),
])
# fmt: on
def test_next_step_is_derived_from_the_workspace_state(
    tmp_path: Path, _git: dict[str, bool], trees: Callable[[Path], dict[str, Path]], kwargs: dict[str, object],
    published: bool, expected: tuple[str, str] | None, command: tuple[str, ...] | None, in_command: list[str],
) -> None:  # fmt: skip
    """sa-bind-has-two-stores#S1: the ``bind`` step judges the caller's Bind (no identity, no step).
    sa-specs-tree-state-read-five-ways#B28-4: the specs fix is state()'s; ADR 0047: a typo is never a move."""
    _git["published"] = published
    step = next_step(tmp_path, trees(tmp_path), **kwargs)  # type: ignore[arg-type]
    assert (step and (step.id, step.kind)) == expected
    if step is None:
        return
    if command:
        assert step.command == fix_line(tmp_path, *command)
    assert all(part in step.command.replace("\\", "/") for part in in_command)


def test_the_specs_step_reports_state_and_the_doctor_has_no_specs_version_code(tmp_path: Path) -> None:
    """sa-specs-tree-state-read-five-ways#B28-6: ONBOARDING reports the state; the doctor has no SPECS-VERSION code."""
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
