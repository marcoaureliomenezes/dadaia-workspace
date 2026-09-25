"""The derived onboarding step list — one fixture per step, plus I1.

Intent: CONTRACT — AC1.1, AC1.2, AC3.1, AC4.1, AC7.2 (T-050-17). Size: SMALL (unit): the
two git reads are patched at the adapter; the real-git behaviour is the property test's.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from dadaia_workspace.core import session_store, workspace_layout
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.features.workspace.onboarding import next_step
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

_SCAFFOLD = workspace_layout.public_scripts_dir().parent / "scaffold"


@pytest.fixture(autouse=True)
def _git(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    remote = {"published": False}
    monkeypatch.setattr(GitSubprocessClient, "default_branch", lambda _s, _p: "trunk")
    monkeypatch.setattr(GitSubprocessClient, "published", lambda _s, _p, _r: remote["published"])
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


def test_zero_contexts_is_the_context_step(tmp_path: Path) -> None:
    step = next_step(tmp_path, {})
    assert step is not None and (step.id, step.kind) == ("context", "command")
    assert step.command == fix_line(
        tmp_path, "context", "create", "<name>", "--main-repo", "<clone-url>"
    )


def test_bind_only_for_a_resolvable_unbound_session(tmp_path: Path) -> None:
    trees = {"app": tmp_path / "repos" / "app" / "specs"}
    assert next_step(tmp_path, trees).id == "specs"  # type: ignore[union-attr]
    step = next_step(tmp_path, trees, session="s1")
    assert step is not None and step.id == "bind"
    assert step.command == fix_line(tmp_path, "context", "bind", "app")
    session_store.write_session(
        tmp_path,
        "s1",
        session_store.new_binding_record(
            session_id="s1", context="app", runtime="t", pid=1, now="2999-01-01T00:00:00+00:00"
        ),
    )
    assert next_step(tmp_path, trees, session="s1").id == "specs"  # type: ignore[union-attr]


def test_specs_fix_carries_the_detected_gitflow_flags(tmp_path: Path) -> None:
    step = next_step(tmp_path, {"app": tmp_path / "repos" / "app" / "specs"})
    assert step is not None
    assert step.command == fix_line(
        tmp_path, "specs", "init", "--context", "app",
        "--principal", "trunk", "--integration", "develop", "--work-prefix", "feature/",
    )  # fmt: skip


def test_shipped_stubs_are_the_agent_first_pass_step(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    step = next_step(tmp_path, {"app": specs})
    assert step is not None and (step.id, step.kind) == ("first-pass", "agent")
    skill = tmp_path / ".agents" / "skills" / "dd-audit-project" / "SKILL.md"
    assert step.command.startswith(f"{skill} §first pass")
    assert str(specs / "memory" / "QUALITY.md") in step.command
    assert "no atom" in step.command


def test_i1_an_audits_histo_stamp_changes_no_step(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    before = next_step(tmp_path, {"app": specs})
    histo = specs / "audits" / "_archive" / "audits_histo.jsonl"
    histo.parent.mkdir(parents=True)
    histo.write_text('{"id": "first"}\n', encoding="utf-8")
    assert next_step(tmp_path, {"app": specs}) == before


def test_publish_until_the_constitution_is_on_a_remote(tmp_path: Path, _git) -> None:
    specs = _specs(tmp_path, audited=True)
    step = next_step(tmp_path, {"app": specs})
    assert step is not None and (step.id, step.kind) == ("publish", "command")
    assert step.command == fix_line(tmp_path, "context", "baseline", "app")
    _git["published"] = True
    assert next_step(tmp_path, {"app": specs}) is None


def test_the_focus_context_answers_first(tmp_path: Path) -> None:
    trees = {"new": tmp_path / "repos" / "new" / "specs", "app": _specs(tmp_path)}
    assert next_step(tmp_path, trees).id == "specs"  # type: ignore[union-attr]
    assert next_step(tmp_path, trees, focus="app").id == "first-pass"  # type: ignore[union-attr]


def test_the_text_names_the_kind_and_carries_one_fix_line(tmp_path: Path) -> None:
    step = next_step(tmp_path, {})
    assert step is not None
    head, fix = step.text().split("\n")
    assert head.startswith("Next (command step context): ") and fix == f"fix: {step.command}"
