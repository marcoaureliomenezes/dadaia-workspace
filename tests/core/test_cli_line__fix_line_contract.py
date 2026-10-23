"""The fix-line contract: every refusal carries exactly one ``fix:`` line that clears it.

``SITES`` maps a site name to a producer: given a fresh workspace root it returns the refusal
text that site prints.

size: MEDIUM — real git and real CLI child processes, no network.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import shutil
import site
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.help_digest import command_paths
from dadaia_workspace.cli.main import app
from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.cli_line import fix_line, git_line
from dadaia_workspace.core.doctor_rules import rule_fix
from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.install_ledger import InstallLedger, LedgerEntry
from dadaia_workspace.core.platform import command, workspace_cli_path
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
from dadaia_workspace.features.spec_context.service import install_git_hooks
from dadaia_workspace.features.specs import canon
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.features.specs.citations import dead_verb_citations
from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.hooks import pre_gate
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import VENV_MISSING
from tests.fakes import gate_fixes
from tests.features.backlog.test_doctor import _SOURCE, _active_entry
from tests.features.specs.test_doctor import _make_clean_specs_tree
from tests.fixtures.fix_world import (
    _TERM,
    _UNSET,
    World,
    _advance_origin_work,
    _associated_dead,
    _associated_on_integration,
    _baseline_denylisted,
    _baseline_done,
    _constitution,
    _dead_clean_detached,
    _dead_done,
    _denylisted,
    _dirty_on_integration,
    _hit,
    _on_work,
    _rmtree,
    _unborn_dirty,
    fix_defect,
    the_fix,
)
from tests.fixtures.harness_env import git_bash, run_bash, suite_env
from tests.fixtures.real_git import PushRepo
from tests.fixtures.stores import own_venv_python, own_venv_workspace
from tests.helpers import oslib, worktree_ws
from tests.helpers.cli_root import live_root
from tests.helpers.oslib import link, read_text, stub_cli, venv_tool, write_text
from tests.helpers.oslib import run as os_run

_SHA_B, _ZERO = "b" * 40, "0" * 40


def _workspace(root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    write_text(
        root / ".dadaia" / "states" / "spec_contexts.json",
        '{"contexts": [{"repo_slug": "a", "state": "alive"}]}',
    )
    (root / ".dadaia" / "sessions").mkdir(parents=True)
    write_text(root / ".dadaiaignore", "[protected]\nsecrets\n")
    workspace_cli_path(root).parent.mkdir(parents=True, exist_ok=True)
    stub_cli(workspace_cli_path(root).parent, "dadaia", "#!python\n")  # a runnable CLI, exit 0
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return _workspace(tmp_path, monkeypatch)


@pytest.fixture
def blank_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A workspace whose root holds a blank, so the fix's executable path must be quoted."""
    return _workspace(tmp_path / "my ws", monkeypatch)


def _gate(ws: Path, rel: str) -> str | None:
    return pre_gate.evaluate_payload({"tool_name": "Write", "tool_input": {"file_path": str(ws / rel)}})  # fmt: skip


def _scope_block(ws: Path, *, has_id: bool) -> str:
    """A write into a repo another context owns, outside the bind's repos."""
    from dadaia_workspace.features.spec_context.gate_policy import evaluate

    return evaluate("repos/b/x.py", root=ws, zone="repo", repo="b", owner="b",
                    context="a", repos=frozenset({"a"}), has_id=has_id)[1]  # fmt: skip


def _push(ws: Path, line: str = "", files: dict[str, str] | None = None, **kwargs: Any) -> str:
    """A consumer work clone (``main`` published, one unpublished commit, the installed
    pre-push hook), pushing *line*; the refusal text."""
    (ws / "clone").mkdir()
    repo = PushRepo(ws / "clone")
    repo.commit({"README.md": "r\n"})
    repo.publish("main")
    install_git_hooks(repo.path)
    sha = repo.commit(files or {"a.md": "a\n"})
    fields = {"sha": sha, "other": _SHA_B, "zero": _ZERO, "a": "a" * 40}
    decision = push_gate_decision(
        parse_push_stdin(line.format(**fields))[0] if line else [],
        gitflow=DEFAULT,
        fixes=replace(gate_fixes(), head="feature/0.0.1"),
        object_source=GitSubprocessObjectReader(),
        repo=repo.path,
        canon_violations_fn=canon_violations,
        **{"malformed_lines": 0, "denylist_terms": (), **kwargs},
    )
    assert not decision.allowed, "expected a refusal"
    return decision.message


def _merge_only(ws: Path) -> str:
    """A write into the bound context's own repo: merge-only, the fix lists the worktrees."""
    from dadaia_workspace.features.spec_context.gate_policy import evaluate

    return evaluate("repos/a/x.py", root=ws, zone="repo", repo="a", owner="a",
                    context="a", repos=frozenset({"a"}), has_id=True)[1]  # fmt: skip


def _kernel_no_specs_tree(ws: Path) -> str:
    """A ledger write verb run where no specs tree exists, in a workspace whose CLI names its repo."""
    cli = workspace_cli_path(ws)
    stub_cli(cli.parent, "dadaia", '#!python\nprint(\'{"main_repo": "a"}\')\n')
    kernel = _PKG / "public" / "skills" / "dd-bug-resolution" / "scripts"
    code = f"import sys; sys.path[:0] = [{str(kernel)!r}]; import _specs; _specs.find_specs(None, ledger='specs/bugs/BUGS.jsonl')"  # fmt: skip
    return os_run([sys.executable, "-c", code], cwd=ws, check=False).stderr  # fmt: skip


_FEATURE = "refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {zero}"
SITES: dict[str, Callable[[Path], str | None]] = {
    "gate-root-whitelist": lambda ws: _gate(ws, "junk.txt"),
    "gate-protected-sessions": lambda ws: _gate(ws, ".dadaia/sessions/some-session.json"),
    "gate-protected-state": lambda ws: _gate(ws, ".dadaia/states/spec_contexts.json"),
    "gate-protected-projected": lambda ws: _gate(ws, ".dadaia/states/install_ledger.json"),
    "gate-protected-glob": lambda ws: _gate(ws, "repos/a/secrets/k"),
    "gate-scope-names-the-bind": lambda ws: _scope_block(ws, has_id=True),
    "gate-id-less-session-relaunch": lambda ws: _scope_block(ws, has_id=False),
    "gate-merge-only-lists-the-worktrees": _merge_only,
    "kernel-no-specs-tree-lists-the-worktrees": _kernel_no_specs_tree,
    "hook-missing-venv": lambda ws: VENV_MISSING.replace("$ROOT", ws.as_posix()),
    "push-malformed-stdin": lambda ws: _push(ws, malformed_lines=1),
    "push-main": lambda ws: _push(ws, "refs/heads/main {sha} refs/heads/main {other}"),
    "push-develop": lambda ws: _push(ws, "refs/heads/develop {sha} refs/heads/develop {other}"),
    "push-birth-with-content": lambda ws: _push(
        ws, "refs/heads/develop {sha} refs/heads/develop {zero}"
    ),
    "push-invalid-name": lambda ws: _push(ws, "refs/heads/wip/x {sha} refs/heads/wip/x {zero}"),
    "push-not-a-branch-head": lambda ws: _push(ws, "refs/notes/x {sha} refs/notes/x {zero}"),
    "push-refspec": lambda ws: _push(
        ws, "refs/heads/feature/0.0.1 {sha} refs/heads/develop {zero}"
    ),
    "push-specs-canon": lambda ws: _push(ws, _FEATURE, {"specs/not-a-canon-entry.md": "x\n"}),
    "push-denylist": lambda ws: _push(
        ws, _FEATURE, {"b.md": "zz-secret-term\n"}, denylist_terms=[("zz-secret-term", "synthetic")]
    ),
    # a sha the repo does not hold: the real object read fails and the gate fails closed
    "push-git-read-failure": lambda ws: _push(ws, _FEATURE.replace("{sha}", "{a}")),
}


_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"

#: Every `Operator action:` text the sources print, whole, by file, with the root map section 3
#: category that admits it: `ruling` (a ruling the law names, root map section 4 for uncommitted
#: work), `protected` (a PROTECTED or `.dadaiaignore` path, or a secret), `reach` (an act outside
#: the agents' reach). An f-string spells each value as `{source}`. A new or changed text fails
#: until it is classed here; a text built from a variable stays covered by its exact-line pin.
_OPERATOR_ACTIONS = {
    ("cli/commands/init.py", "empty {quote(str(root))} or name another empty folder for the workspace, then run {inline(*plan.words(root))}"): "ruling",
    ("cli/commands/context.py", "export DADAIA_SESSION_ID set to a stable id of your choice before opening the session"): "reach",
    ("features/export/scan.py", "rule whether {bundle} is restored from a copy or discarded"): "ruling",
    ("core/context_registry.py", "rewrite {path} as one {shape} object"): "protected",
    ("features/chokepoints/push_gate.py", "make git runnable here"): "reach",
    ("features/spec_context/doctor.py", "split {skill}/SKILL.md at its library source; this workspace holds none and never edits the projection"): "reach",
    ("features/spec_context/doctor.py", "move {entry.name} out of the workspace"): "protected",
    ("features/spec_context/gate_policy.py", "relaunch this session with DADAIA_CONTEXT={owner}"): "reach",
    ("features/spec_context/sweep.py", "remove {target}"): "reach",
    ("infrastructure/git_subprocess.py", "pop or drop the {stashes} stash entry(ies) of {path}"): "ruling",
    ("infrastructure/json_context_store.py", "set it to {SCHEMA_VERSION} in {path}"): "protected",
    ("infrastructure/json_context_store.py", "add {', '.join(missing)} to that row of {path}"): "protected",
    ("public/skills/dd-backlog-definition/scripts/_backlog_exit.py", "confirm {slug} as a bug (dd-bug-registration §2)"): "ruling",
    ("public/skills/dd-bug-resolution/scripts/_ledger.py", "rewrite {path} as one JSON object mapping each term to its reason"): "protected",
    ("public/skills/dd-cli-library/scripts/registry.py", "delete {_platform.quote(str(path))} — the next registry.py run starts an empty registry"): "protected",
    ("public/skills/dd-gitflow-default/scripts/_worktree_new.py", "confirm {what} (dd-bug-registration §2)"): "ruling",
    ("public/skills/dd-release-implementation/scripts/_release_phase.py", "set '**Status:** {APPROVED}' in {document.resolve()}"): "ruling",
    ("public/skills/dd-release-implementation/scripts/release.py", "authorize carrying {', '.join(missing)}"): "ruling",
    ("public/skills/dd-release-implementation/scripts/release.py", "authorize carrying {bug_id}"): "ruling",
}  # fmt: skip


def _operator_action_texts(source: str) -> list[str]:
    """Every text in *source* passed to an `act("operator", ...)` call; a string or f-string
    argument reads whole, an f-string's values as `{source}`."""

    def spelled(node: ast.AST) -> str | None:
        if isinstance(node, ast.JoinedStr):
            return "".join(
                v.value if isinstance(v, ast.Constant) else "{" + ast.unparse(v.value) + "}"
                for v in node.values
            )
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    return [
        spelled(node.args[1]) or f"<not a literal: {ast.unparse(node.args[1])}>"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == "act"
        and len(node.args) == 2
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "operator"
    ]


def test_an_operator_action_text_reads_an_act_call() -> None:
    source = 'b = act("operator", f"remove {target}")\nc = act("agent", "edit the file")\n'
    assert _operator_action_texts(source) == ["remove {target}"]


def test_an_operator_action_whose_text_is_a_variable_is_a_hit() -> None:
    source = 'a = act("operator", text)\nb = act("operator", "x" + y)\n'
    assert _operator_action_texts(source) == ["<not a literal: text>", "<not a literal: 'x' + y>"]


def test_an_operator_action_is_one_act_the_law_reserves_to_the_human() -> None:
    """Each `Operator action:` text the sources print is exactly one classed act, whole: a
    trailing step, a second literal or a changed word fails."""
    found = sorted(
        (p.relative_to(_PKG).as_posix(), text)
        for p in _PKG.rglob("*.py")
        for text in _operator_action_texts(read_text(p))
    )
    assert found == sorted(_OPERATOR_ACTIONS)


@pytest.mark.parametrize(
    ("fix", "defect"),
    [
        pytest.param("Agent action: edit the Origin line of SPEC.md, then rerun it", False, id="agent-act"),
        pytest.param("Agent action: choose a or b and rerun", False, id="agent-menu-in-words"),
        pytest.param("Operator action: relaunch the session, then rebind", False, id="operator-act"),
        pytest.param("Agent action: edit <file>", True, id="agent-placeholder"),
        pytest.param("Agent action: edit a|b", True, id="agent-menu-bar"),
        pytest.param("Human action: edit the file", True, id="third-label"),
    ],
)  # fmt: skip
def test_fix_defect_judges_both_action_labels_by_one_act(fix: str, defect: bool) -> None:
    assert fix_defect(fix) is defect


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World.of(tmp_path)


# ── doctor-specs: the specs rules' fix lines ─────────────────────────────────────────
# A producer plants one finding in a clean specs tree and reads it from ``doctor --json``. Its
# progress rule: the printed fix runs and the finding is gone with no new error; an operator
# action names a file under the tree.

_RELEASE = "1.2.3"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text(path, text)


def _append(path: Path, text: str) -> None:
    write_text(path, read_text(path) + text)


def _plant_missing_memory_document(root: Path) -> None:
    (root / "specs" / "memory" / "QUALITY.md").unlink()


def _plant_headingless_memory_document(root: Path) -> None:
    _write(root / "specs" / "memory" / "QUALITY.md", "---\nslug: quality\n---\n\nno heading here\n")


def _plant_nothing(root: Path) -> None:
    """The fixture already carries it (no audits/, bugs/ dirs; no backlog/_archive/)."""


def _plant_placeholder_atom(root: Path) -> None:
    atom = root / "specs" / "memory" / "product" / "testarea" / "raw.md"
    write_text(atom, "---\nslug: SLUG_PLACEHOLDER\n---\n# TITLE_PLACEHOLDER\n")


def _plant_missing_root_agents(root: Path) -> None:
    (root / "specs" / "AGENTS.md").unlink(missing_ok=True)


def _plant_fixed_block_gone(root: Path) -> None:
    """A memory document whose fixed law block was deleted by hand."""
    quality = root / "specs" / "memory" / "QUALITY.md"
    head, _, rest = read_text(quality).partition("<!-- dadaia:fixed slop-tests -->")
    write_text(quality, head + rest.partition("<!-- /dadaia:fixed slop-tests -->\n")[2])


def _plant_fixed_block_drifted(root: Path) -> None:
    """A memory document whose fixed law block was edited by hand."""
    quality = root / "specs" / "memory" / "QUALITY.md"
    write_text(
        quality,
        read_text(quality).replace(
            "<!-- dadaia:fixed slop-tests -->\n", "<!-- dadaia:fixed slop-tests -->\n- edited\n"
        ),
    )


def _plant_gitflow_gone(root: Path) -> None:
    """A current dadaia tree whose constitution frontmatter has no gitflow block."""
    constitution = root / "specs" / "constitution.md"
    write_text(
        constitution,
        f"---\nspecs_pattern_version: {CANONICAL_SPECS_VERSION}\n---\n" + read_text(constitution),
    )


def _plant_status_line_gone(root: Path) -> None:
    """A SPEC.md with no status line and a 173-line TASKS.md with a lowercase token: both fire."""
    release = root / "specs" / "releases" / _RELEASE / "rc-1"
    write_text(release / "SPEC.md", "# Spec\n\nContent.\n")
    write_text(release / "TASKS.md", "# Tasks\n\n**Status:** approved\n" + "- t\n" * 170)


def _plant_changelog_heading(root: Path) -> None:
    _append(
        root / "specs" / "memory" / "product" / "testarea" / "feature-a.md",
        "\n## Changelog\n\n- 1.0.0 born\n",
    )


def _plant_legacy_state_name(root: Path) -> None:
    """The legacy state-file name, renamed by `doctor --fix`."""
    state = root / "specs" / "releases" / _RELEASE / "_RELEASE.json"
    state.rename(state.with_name("RELEASE.json"))


def _plant_stray_dotfile(root: Path) -> None:
    """Untracked and with no canon home: a ``git mv`` could not serve it."""
    (root / "specs" / ".DS_Store").write_bytes(b"\x00")


def _plant_orphan_wt(root: Path) -> None:
    """An unmerged orphan: a lane branch carries a commit and has no tree."""
    repo, tree = root / "repos/r", root / "worktrees/r/0.5.0/wt-hotfix-b"
    worktree_ws.git(repo, "checkout", "-q", "feature/0.5.0")
    worktree_ws.git(repo, "worktree", "add", "-q", "-b", "wt/0.5.0/wt-hotfix-b", str(tree))
    worktree_ws.commit(tree, "src/a.py")
    worktree_ws.git(repo, "worktree", "remove", str(tree))


def _plant_raw_law(root: Path) -> None:
    """The unrendered template an older ``specs init`` copied."""
    public = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"
    (root / "specs" / "AGENTS.md").write_bytes(
        (public / "templates" / "specs-AGENTS.md").read_bytes()
    )


#: code -> how to make it fire; ``WORKTREE`` plants a workspace, the rest a specs tree.
PLANTS: dict[str, Callable[[Path], None]] = {
    "TREE-4": _plant_nothing,
    "WORKTREE": _plant_orphan_wt,
    "TREE-5": _plant_missing_root_agents,
    "SPEC-DOC-034": _plant_nothing,
    "FIXED-1": _plant_fixed_block_gone,
    "FIXED-2": _plant_fixed_block_drifted,
    "TREE-3": _plant_missing_memory_document,
    "SPEC-DOC-046": _plant_legacy_state_name,
}


#: WARNING-only by construction, no fix line: their remedy is the operator's judgment.
REPORT_ONLY: dict[str, Callable[[Path], None]] = {
    "SPEC-DOC-030": lambda r: (r / "specs" / "audits" / "Bad_Name").mkdir(parents=True),
    "MEM-DRIFT-2": lambda r: _append(
        r / "specs" / "memory" / "QUALITY.md", "\nRun `dadaia no-such-verb`.\n"
    ),
}

#: Error findings no command can repair (the remedy is the agent's content).
AGENT_ACTION: dict[str, Callable[[Path], None]] = {
    "SPEC-DOC-002": _plant_headingless_memory_document,
    "MEM-PLACEHOLDER-1": _plant_placeholder_atom,
    "SPEC-DOC-004": _plant_status_line_gone,
    "TREE-8": _plant_stray_dotfile,
    "LINT-1": lambda r: _write(r / "specs" / "memory" / "product" / "testarea" / "x.md", "# X\n"),
    "SPEC-DOC-001": lambda r: (r / "specs" / "constitution.md").unlink(),
    "GITFLOW-1": _plant_gitflow_gone,
    "SPEC-DOC-026": lambda r: _write(r / f"specs/releases/_archive/{_RELEASE}/SPEC.md", "# S\n"),
    "ADR-SUPERSEDED-CITATION": lambda r: (
        _write(r / "specs/ADRs/decisions.jsonl", '{"id": "0001", "status": "superseded"}\n'),
        _append(r / "specs/memory/QUALITY.md", "\nADR: 0001\n"),
    ),
    "BL-SCHEMA": lambda r: _write(r / "specs/backlog/BACKLOG.json", json.dumps({"schema": "backlog-v1", "active": [
        _active_entry("xx", "x", "candidate", ref="pkg/m.py#Ghost", change="x")]})),
    "BL-CONFLICT": lambda r: (
        _write(r / "pkg/m.py", _SOURCE),
        _write(r / "specs/backlog/BACKLOG.json", json.dumps({"schema": "backlog-v1", "active": [
            _active_entry(t, t, "candidate", ref="pkg/m.py#Widget", change=t) for t in ("dd", "ee")]})),
    ),
}  # fmt: skip

_AREA_HEADER = "| Area | Members |"
_ROOT_ROW = "| root | `AGENTS.md constitution.md memory/ releases/ backlog/ bugs/ audits/ ADRs/` |"
_PLACEHOLDERS = ("<!-- zones -->", "<!-- canon -->", "<!-- root -->", "<!-- specs-canon -->")


def _tree_git(root: Path, *args: str) -> None:
    os_run(
        ["git", *args],
        cwd=root,
        check=True,
        env=suite_env(
            {}, root, overrides={"PATH": "/usr/bin:/bin", "GIT_CONFIG_GLOBAL": "/dev/null"}
        ),
    )


def _specs_tree(ws: Path, plant: Callable[[Path], None], *, commit: bool = False) -> Path:
    """A git-backed clean specs tree under *ws* with *plant* applied (committed when *commit*:
    a fix line may legitimately be a `git rm`/`git mv`)."""
    # beside *ws*, not under it: a tree under a workspace names that workspace's CLI
    root = Path(tempfile.mkdtemp(dir=ws.parent, prefix="specs-"))
    _make_clean_specs_tree(root, _RELEASE)
    for args in (
        ("init", "-q"),
        ("config", "user.email", "f@example.invalid"),
        ("config", "user.name", "f"),
    ):
        _tree_git(root, *args)  # fmt: skip
    plant(root)
    if commit:
        _tree_git(root, "add", "-A")
        _tree_git(root, "commit", "-qm", "fixture")
    return root


def _findings(root: Path, *sections: str) -> list[dict[str, str]]:
    """The findings of ``doctor --json`` over *root*'s specs tree, from its ``specs`` section or
    the *sections* named."""
    with contextlib.chdir(root):  # the tree is no workspace: a fix names the running venv's CLI
        ran = CliRunner().invoke(
            app, ["doctor", "--json", "--specs-dir", str(root / "specs")], env=dict.fromkeys(_UNSET)
        )
    report = json.loads(ran.output)["sections"]
    return [f for name in sections or ("specs",) for f in report[name]["findings"]]


def _keys(found: list[dict[str, str]]) -> set[tuple[str, str, bool]]:
    return {(f["code"], f["message"], f["verdict"] == "error") for f in found}


def _clears(
    ws: Path,
    plant: Callable[[Path], None],
    code: str,
    only: Callable[[str], bool] = bool,
    then: Callable[[Path], None] = lambda *_: None,
) -> str:
    """Plants the finding, runs its printed fix, and requires the finding gone with no new error;
    returns the fix line."""
    root = _specs_tree(ws, plant, commit=True)
    before = _findings(root)
    first = next((f for f in before if f["code"] == code and only(f["message"])), None)
    assert first, f"{code}: the fixture did not make the rule fire"
    if code == "TREE-3":  # one finding for one fact
        assert [f["code"] for f in before if "memory/QUALITY.md" in f["message"]] == ["TREE-3"]
    dead = dead_verb_citations(
        f"`{first['message']}`", rel=code, command_paths=command_paths(live_root())
    )
    assert not dead, f"{code}: the finding cites a verb that does not exist: {dead}"
    done = run_bash(first["fix"], cwd=root, check=False)
    after = _keys(_findings(root))
    assert (first["code"], first["message"], first["verdict"] == "error") not in after, (
        f"{code}: survives\n{first['fix']}\n{done.stderr}"
    )
    assert not {f for f in after - _keys(before) if f[2]}, f"{code}: the fix created an error"
    then(root)
    return f"fix: {first['fix']}"


def _agent_action(ws: Path, code: str) -> str:
    """Every finding of *code* is one `Agent action:` naming a file under the tree."""
    root = _specs_tree(ws, AGENT_ACTION[code])
    found = [f for f in _findings(root, "specs", "ledgers") if f["code"] == code]
    assert found, f"{code}: the fixture did not make the rule fire"
    for finding in found:
        assert finding["fix"].startswith("Agent action: ") and str(root) in finding["fix"]
    return f"fix: {found[0]['fix']}"


def _gitflow_1(ws: Path) -> str:
    """The fix is one Agent action naming `specs init` and the commit; performing both clears
    the finding with no new error."""
    root = _specs_tree(ws, _plant_gitflow_gone, commit=True)
    before = _findings(root)
    first = next((f for f in before if f["code"] == "GITFLOW-1"), None)
    assert first, "GITFLOW-1: the fixture did not make the rule fire"
    fix = first["fix"]
    assert fix.startswith("Agent action: ") and fix.count("Agent action:") == 1, fix
    assert "specs init" in fix and str(root / "specs") in fix, fix
    assert "commit" in fix and "constitution.md" in fix, fix
    with contextlib.chdir(root):
        CliRunner().invoke(app, ["specs", "init", "--specs-dir", str(root / "specs")])
    _tree_git(root, "add", "specs/constitution.md")
    _tree_git(root, "commit", "-qm", "gitflow")
    after = _keys(_findings(root))
    assert ("GITFLOW-1", first["message"], False) not in after, f"GITFLOW-1 survives\n{fix}"
    assert not {f for f in after - _keys(before) if f[2]}, "GITFLOW-1: the fix created an error"
    return f"fix: {fix}"


def _law_is_rendered(root: Path) -> None:
    law = read_text(root / "specs" / "AGENTS.md")
    assert _AREA_HEADER in law and _ROOT_ROW in law
    assert not [p for p in _PLACEHOLDERS if p in law]


def _worktree(ws: Path) -> str:
    """An unmerged orphan wt/* carries the owner's `worktree.py merge`; its chain (merge refuses
    with the re-attach, the re-attached tree is still ours and `ready`, the reviewed merge lands)
    ends with no finding."""
    (ws / "wt").mkdir()
    root = worktree_ws.make_workspace(ws / "wt")
    PLANTS["WORKTREE"](root)
    doctor = worktree_ws.registered_doctor(root)
    first = ""
    for _ in range(3):
        if not (found := doctor.check_worktrees("c")):
            break
        first = first or found[0].fix
        worktree_ws.approve(
            root, worktree_ws.git(root / "repos/r", "rev-parse", "wt/0.5.0/wt-hotfix-b").strip()
        )
        done = run_bash(found[0].fix, cwd=root)
        if done.returncode:
            (refix,) = worktree_ws.fixes(done)
            run_bash(refix.removeprefix("fix: "), check=True)
    assert first and doctor.check_worktrees("c") == []
    return f"fix: {first}"


SITES |= {
    **{
        f"doctor-specs-{code}": lambda ws, code=code: _clears(ws, PLANTS[code], code)
        for code in PLANTS
        if code != "WORKTREE"
    },
    **{
        f"doctor-specs-{code}": lambda ws, code=code: _agent_action(ws, code)
        for code in AGENT_ACTION
    },
    "doctor-specs-WORKTREE": _worktree,
    "doctor-specs-GITFLOW-1": _gitflow_1,
    # a raw ``specs/AGENTS.md`` (the template an older ``specs init`` copied) is flagged
    # refreshable; its fix renders the law.
    "doctor-specs-TREE-5-raw-law": lambda ws: _clears(
        ws, _plant_raw_law, "TREE-5", lambda m: m.startswith("specs/AGENTS.md "), _law_is_rendered
    ),
}

# ── doctor-workspace: the workspace and ledger findings' fix lines ──────────────────
# A producer plants a finding and reads it from ``doctor --json``. A command fix runs from
# ``worktrees/`` and the real doctor drops the finding; an agent action names file and law.

_WS_UNSET = (*_UNSET, "CLAUDE_CODE_SESSION_ID")
_ENTRY = {"id": "a-entry", "title": "a", "opened": "2026-10-02", "status": "idea",
          "description": "d", "provenance": "operator request"}  # fmt: skip
_PRETTY = json.dumps(
    {"schema": "backlog-v1", "active": [_ENTRY, {**_ENTRY, "id": "b-entry", "status": "resolved"}]},
    indent=2,
)
#: (code, file, committed, bad, where): a JSONL ledger names its line; a JSON document
#: names the entry or key, since none of its lines is one commit's.
_LEDGER_ROWS = [
    ("LEDGER-BUGS-SCHEMA", "specs/bugs/BUGS.jsonl", "", '{"id": "broken"}\n', 1),
    ("LEDGER-BUGS-SCHEMA", "specs/bugs/BUGS.jsonl", "{not json\n", "{not json\n", 1),
    ("LEDGER-BACKLOG-SCHEMA", "specs/backlog/BACKLOG.json", '{"schema": "backlog-v1", "active": []}', "{not json\n", "its JSON syntax (line 1)"),
    ("LEDGER-BACKLOG-SCHEMA", "specs/backlog/BACKLOG.json", "", _PRETTY, "entry 'b-entry'"),
    ("LEDGER-FINDINGS-SCHEMA", "specs/audits/20260101-x/FINDINGS.jsonl", "", "{not json\n", 1),
    ("LEDGER-RELEASE-SCHEMA", "specs/releases/1.0.0/_RELEASE.json", "{}\n", "{not json\n", "its JSON syntax (line 1)"),
]  # fmt: skip


def _ws_env() -> dict[str, str]:
    return suite_env(os.environ, Path.home(), unset=_WS_UNSET)


def _doctor(root: Path, *scope: str, real: bool = False) -> list[dict[str, str]]:
    """The findings of ``doctor --json`` run in *root*: in process, or as a child with *real*."""
    if real:
        argv = [sys.executable, "-m", "dadaia_workspace", "doctor", *scope, "--json"]
        out = os_run(argv, cwd=root, env=_ws_env(), check=False).stdout  # noqa: S603
    else:
        with contextlib.chdir(root):
            out = (
                CliRunner()
                .invoke(app, ["doctor", *scope, "--json"], env=dict.fromkeys(_WS_UNSET))
                .stdout
            )
    sections = json.loads(out)["sections"]
    if scope:  # a bare specs tree: the fenced child judges no workspace at all
        assert sections.get("workspace", {}).get("findings", []) == [], "unfenced"
    return [f for s in sections.values() for f in s["findings"]]


def _from_elsewhere(root: Path, fix: str) -> None:
    """Runs *fix* from ``worktrees/`` in *root*: inside the workspace, yet never the slop the fix
    moves, which Windows refuses while a process holds it as its cwd."""
    elsewhere = root / "worktrees"
    elsewhere.mkdir(exist_ok=True)
    ran = run_bash(fix, cwd=elsewhere, env=_ws_env())
    assert ran.returncode == 0, ran.stdout + ran.stderr


def _ledger_tree(ws: Path, rel: str, committed: str, bad: str) -> Path:
    """A git tree beside *ws* whose ledger *rel* holds *committed* at HEAD and *bad* on disk."""
    root = Path(tempfile.mkdtemp(dir=ws.parent, prefix="ledger-"))
    ledger = root / rel
    ledger.parent.mkdir(parents=True)
    if "audits" in rel:
        write_text(ledger.parent / "AUDIT.md", "# Audit\n")
    write_text(ledger, committed)
    for args in (
        ["init", "-q"],
        ["add", rel],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "l"],
    ):
        os_run(["git", "-C", str(root), *args], check=True)  # noqa: S603, S607
    write_text(ledger, bad)
    return root


def _ledger(ws: Path, code: str) -> str:
    """Every invalid-ledger row of *code* is ONE `Agent action:` naming the file, where in
    it and the ledger's law: uncommitted content is discarded, else the introducing commit is
    reverted, never a hand edit."""
    first = ""
    for row_code, rel, committed, bad, where in _LEDGER_ROWS:
        if row_code != code:
            continue
        tree = _ledger_tree(ws, rel, committed, bad)
        (fix,) = [f["fix"] for f in _doctor(tree, "--specs-dir", "specs") if f["code"] == code]
        path = (tree / rel).resolve()
        assert fix.startswith("Agent action: ") and "AGENTS.md" in fix, fix
        assert "<" not in fix and "by hand" not in fix, fix
        if "audits" in rel:  # a bound session writes findings directly: the governed act
            assert f"line 1 of {path} " in fix, fix
        else:
            finder = (
                git_line(path.parent, "log", "-L", f"1,1:{path.name}")
                if where == 1
                else git_line(path.parent, "log", "-p", "--", path.name)
            )
            assert "checkout" not in fix, fix
            assert finder in fix, fix
            assert (f"line 1 of {path} " if where == 1 else f"{path} fails at {where} ") in fix, fix
        first = first or fix
    return f"fix: {first}"


_RECORD = {"id": "a-bug", "ts": "2026-09-20T10:00:00Z", "reported_by": "e", "title": "t",
           "severity": "LOW", "surface": "cli", "component": "c", "context": "x", "symptom": "s",
           "repro": "r", "expected": "e", "status": "open", "cause": None, "caused_by": None,
           "closed_at": None}  # fmt: skip


def _bugs_fix(ws: Path, *records: dict[str, object]) -> tuple[Path, str]:
    """The tree and the one LEDGER-BUGS-SCHEMA fix over a ledger of *records*."""
    ledger = "".join(json.dumps(r) + "\n" for r in records)
    tree = _ledger_tree(ws, "specs/bugs/BUGS.jsonl", ledger, ledger)
    return tree, next(
        f["fix"] for f in _doctor(tree, "--specs-dir", "specs") if f["code"] == "LEDGER-BUGS-SCHEMA"
    )


def test_a_dangling_caused_by_is_cleared_by_bugs_update(workspace: Path) -> None:
    """A line a governance verb clears takes that verb with real values; run from elsewhere,
    `bugs.py update <id> --set caused_by=none` clears it."""
    tree, fix = _bugs_fix(workspace, {**_RECORD, "caused_by": "a-ghost"})
    assert " update a-bug --set caused_by=none --specs " in fix, fix
    _from_elsewhere(tree, fix)
    assert "LEDGER-BUGS-SCHEMA" not in {
        f["code"] for f in _doctor(tree, "--specs-dir", "specs", real=True)
    }


def test_a_caused_by_cycle_is_an_agent_decision(workspace: Path) -> None:
    """Which link of a cycle is wrong is a judgement: the fix names the cycle's records and the
    law, and sets no value."""
    _, fix = _bugs_fix(
        workspace,
        {**_RECORD, "caused_by": "b-bug"},
        {**_RECORD, "id": "b-bug", "caused_by": "a-bug"},
    )
    assert fix.startswith("Agent action: decide which of a-bug, b-bug ") and "update" in fix
    assert "caused_by=none" not in fix and "<" not in fix and "AGENTS.md" in fix, fix


def _initialized(ws: Path) -> Path:
    """A real ``init`` under *ws*, its venv stubbed onto this interpreter (never a real venv)."""
    root = ws / "ws"
    root.mkdir()
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(), python_env=VenvPythonEnvironmentManager()
    ).init(root, harnesses=L1_ENTRY_HARNESSES[:1])
    stub_dir = venv_tool(root / ".dadaia" / ".venv", "dadaia").parent
    stub_dir.mkdir(parents=True, exist_ok=True)
    main = "#!python\nimport runpy\nrunpy.run_module('dadaia_workspace', run_name='__main__')\n"
    stub_cli(stub_dir, "dadaia", main, python=Path(sys.executable))
    return root


def _plant_root_slop(root: Path) -> str:
    write_text(root / "junk.txt", "x\n")
    return "WS-root-slop"


def _plant_drifted_hook(root: Path) -> str:
    repo = root / "repos" / "beta"
    os_run(["git", "init", "-q", str(repo)], check=True)  # noqa: S603, S607
    for target, _ in workspace_layout.INSTALLED_GIT_HOOKS:
        write_text(repo / ".git" / "hooks" / target, "#!/bin/sh\nexit 0\n")
    ctx = {"name": "beta", "state": "alive", "repo_slug": "beta", "repo_url": "file:///x.git",
           "created_at": "2026-01-01T00:00:00Z", "alive_since": "2026-01-01T00:00:00Z",
           "dead_since": None, "current_branch": None}  # fmt: skip
    write_text(
        root / ".dadaia/states/spec_contexts.json",
        json.dumps({"schema_version": "2", "contexts": [ctx]}),
    )
    return "HOOKS-DRIFT-1"


def _plant_disarmed_gate(root: Path) -> str:
    (root / ".claude" / "settings.json").unlink()
    return "PROJECTION"


#: Every workspace-doctor code the home proves: cleared by its printed fix (a plant), or an
#: agent action (``None``: a ledger row, or the long SKILL.md).
WORKSPACE_PLANTS = {
    **dict.fromkeys(code for code, *_ in _LEDGER_ROWS),
    "WS-ENTRY": _plant_root_slop,
    "HOOKS-DRIFT-1": _plant_drifted_hook,
    "PROJECTION": _plant_disarmed_gate,
    "SKILL-MD-LENGTH": None,
}


def _workspace_clears(ws: Path, plant: Callable[[Path], str]) -> str:
    """Plants a workspace finding, runs its printed fix from elsewhere, and requires it gone."""
    root = _initialized(ws)
    code = plant(root)
    fix = next(f["fix"] for f in _doctor(root) if f["code"] == code)
    _from_elsewhere(root, fix)
    assert code not in {f["code"] for f in _doctor(root, real=True)}
    return f"fix: {fix}"


def _long_skill(ws: Path) -> str:
    """A long SKILL.md is one non-error finding whose fix names who splits it: an agent action
    when its library source sits in a repo of the workspace, else the operator's. Once the skill
    is short, the finding is gone."""
    root = _initialized(ws)
    skill = root / ".agents" / "skills" / "long" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    soft = json.loads((_PKG / "features/spec_context/behavior-map.json").read_bytes())
    write_text(skill, "l\n" * (soft["skill_md_line_soft"] + 1))
    source = root / "repos" / "lib" / "dadaia_workspace" / "public" / "skills" / "long" / "SKILL.md"
    source.parent.mkdir(parents=True)
    write_text(source, "l\n")
    [found] = [f for f in _doctor(root) if f["code"] == "SKILL-MD-LENGTH"]
    assert found["verdict"] == "warning"
    assert found["fix"] == (
        "Agent action: add the split of long/SKILL.md to a task of the open rc, then run public install"
    )
    source.unlink()
    [found] = [f for f in _doctor(root) if f["code"] == "SKILL-MD-LENGTH"]
    assert found["fix"] == (
        "Operator action: split long/SKILL.md at its library source; this workspace holds none and never edits the projection"
    )
    write_text(skill, "l\n")
    assert "SKILL-MD-LENGTH" not in {f["code"] for f in _doctor(root, real=True)}
    return f"fix: {found['fix']}"


def _denylist_refusal(ws: Path) -> str:
    """The skill kernel's refusal of a privacy denylist that is not one JSON object."""
    write_text(ws / ".dadaia" / "states" / "privacy_denylist.json", "[]")
    err = io.StringIO()
    with contextlib.redirect_stderr(err), pytest.raises(SystemExit):
        load_owner("dd-bug-resolution", "_ledger").terms(ws)
    return err.getvalue()


def _registry_refusal(ws: Path) -> str:
    """The server registry's refusal of a file that is not UTF-8."""
    path = ws / ".dadaia" / "states" / "server_registry.json"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(load_owner("dd-bug-resolution", "_refusal").Refusal) as refused:
        load_owner("dd-cli-library", "registry").load(path)
    return f"[error] {refused.value}\nfix: {refused.value.fix}"


SITES |= {
    "skill-denylist-not-an-object": _denylist_refusal,
    "skill-registry-not-utf8": _registry_refusal,
}


@pytest.mark.parametrize(
    "rel",
    [
        ".agents/skills/dd-x/SKILL.md",
        "AGENTS.md",
        ".claude/settings.json",
        ".dadaia/AGENTS.md",
        "repos/a/secrets/k",
    ],
)
def test_an_agent_action_naming_a_path_the_gate_protects_is_refused(
    workspace: Path, rel: str
) -> None:
    """Planted, each protected class goes red; a path in a tree stays green."""
    states = workspace / ".dadaia" / "states"
    entries = [LedgerEntry(relpath=r, sha256="a" * 64, family="law") for r in (
        ".agents/skills/dd-x/SKILL.md", ".claude/settings.json", ".dadaia/AGENTS.md")]  # fmt: skip
    JsonInstallLedgerStore().write(states, InstallLedger.of(entries))
    with pytest.raises(AssertionError):
        the_fix(f"[error] x\nfix: Agent action: edit {workspace / rel}", workspace)
    tree = workspace / "worktrees" / "a" / "t" / "x.py"
    the_fix(f"[error] x\nfix: Agent action: edit {tree}", workspace)


SITES |= {
    **{
        f"doctor-workspace-{code}": lambda ws, code=code: _ledger(ws, code)
        for code in dict.fromkeys(c for c, *_ in _LEDGER_ROWS)
    },
    **{
        f"doctor-workspace-{code}": lambda ws, plant=plant: _workspace_clears(ws, plant)
        for code, plant in WORKSPACE_PLANTS.items()
        if plant
    },
    "doctor-workspace-SKILL-MD-LENGTH": _long_skill,
}


def test_a_deleted_hook_is_reported_absent_and_its_fix_restores_it(workspace: Path) -> None:
    """A deleted projected hook is reported absent, and its printed fix, run, restores the hook
    byte for byte."""
    root = _initialized(workspace)
    _plant_drifted_hook(root)
    hooks = root / "repos" / "beta" / ".git" / "hooks"
    for target, _ in workspace_layout.INSTALLED_GIT_HOOKS:
        (hooks / target).unlink()
    found = next(f for f in _doctor(root) if f["code"] == "HOOKS-DRIFT-1")
    assert "absent" in found["message"], found["message"]
    _from_elsewhere(root, found["fix"])
    for target, source in workspace_layout.INSTALLED_GIT_HOOKS:
        assert (hooks / target).read_bytes() == (
            workspace_layout.public_scripts_dir() / source
        ).read_bytes()
    assert "HOOKS-DRIFT-1" not in {f["code"] for f in _doctor(root, real=True)}


@pytest.mark.parametrize("rule", SPECS_RULES, ids=lambda rule: "/".join(rule.codes))
def test_no_fix_line_deletes_a_record_without_recording_it(rule: Any) -> None:
    """A bare recursive ``rm`` (at the head of the line or of any chain segment) is never a fix:
    what the finding protects goes with it. ``git rm -r`` stages a removal git still holds."""
    assert not re.search(r"(?:^|&&|;|\|)\s*rm\s+-[a-zA-Z]*r", rule_fix(rule, Path()) or "")


def test_a_judgment_only_rule_never_makes_the_run_exit_1(workspace: Path) -> None:
    """Every judgment-only rule fires at once and contributes NO error-class finding and NO fix
    line; a history heading planted beside them is reported once, by LINT-1."""

    def plant(root: Path) -> None:
        _plant_changelog_heading(root)
        for plant_one in REPORT_ONLY.values():
            plant_one(root)

    found = _findings(_specs_tree(workspace, plant))
    fired = {f["code"] for f in found}
    assert set(REPORT_ONLY) <= fired, fired
    assert not {"CAT-1", "SPEC-DOC-008", "SPEC-DOC-010"} & fired, fired
    history = [f for f in found if "Changelog" in f["message"]]
    assert [(f["code"], f["verdict"]) for f in history] == [("LINT-1", "error")], history
    assert [
        f for f in found if f["code"] in REPORT_ONLY and (f["verdict"] == "error" or f["fix"])
    ] == []


_SLOW = pytest.mark.slow(reason="real git remotes and CLI child processes")


@pytest.mark.parametrize(
    "site",
    [
        pytest.param(s, marks=_SLOW) if s.startswith(("doctor-specs-", "doctor-workspace-")) else s
        for s in SITES
    ],
)
def test_every_site_carries_one_runnable_fix(workspace: Path, site: str) -> None:
    the_fix(SITES[site](workspace), workspace)


_BLOCKS = {
    "gate-protected-glob-dec-11" if s == "gate-protected-glob" else s: SITES[s]
    for s in (
        "gate-root-whitelist", "gate-protected-sessions", "gate-protected-projected",
        "gate-protected-glob", "gate-scope-names-the-bind", "gate-id-less-session-relaunch",
        "hook-missing-venv", "push-malformed-stdin", "push-main", "push-develop",
        "push-birth-with-content", "push-invalid-name", "push-not-a-branch-head", "push-refspec",
        "push-specs-canon", "push-denylist", "push-git-read-failure",
    )
}  # fmt: skip


@pytest.mark.parametrize("block", list(_BLOCKS))
def test_every_block_carries_a_runnable_fix(workspace: Path, block: str) -> None:
    the_fix(_BLOCKS[block](workspace), workspace)


def _shell_argv(shell: str) -> list[str]:
    """The argv that runs one line in *shell*; skips when the host lacks it."""
    if shell == "bash":
        try:
            return [git_bash(), "-c"]
        except FileNotFoundError:
            pytest.skip("Git Bash is not installed")
    argv = {
        "sh": ["sh", "-c"],
        "cmd": ["cmd", "/d", "/s", "/c"],
        "powershell": ["powershell", "-NoProfile", "-Command"],
        "pwsh": ["pwsh", "-NoProfile", "-Command"],
    }[shell]
    if not shutil.which(argv[0]):
        pytest.skip(f"{shell} is not installed")
    return argv


def _in_shell(shell: str, line: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    argv = _shell_argv(shell)
    if (
        shell == "cmd"
    ):  # cmd /s strips the outer quotes of its raw tail; list2cmdline's \" is not cmd syntax.
        return oslib.run_cmdline(f'{subprocess.list2cmdline(argv)} "{line}"', cwd=cwd, timeout=120, check=False)  # fmt: skip
    return os_run([*argv, line], cwd=cwd, timeout=120, check=False)


@pytest.mark.parametrize("shell", oslib.shells_for(oslib.detect()))
def test_a_fix_runs_verbatim_in_every_host_shell(blank_workspace: Path, shell: str) -> None:
    """In a root that holds a blank, the root refusal's fix runs verbatim from ``repos/demo``,
    twice, never writing the exceptions file, in each shell the host offers (POSIX ``sh``; on
    Windows cmd, PowerShell and Git Bash). The CLI fix runs too, except on Windows: its head
    holds a blank, which no spelling gets through all three shells, so it is an Agent action."""
    workspace = blank_workspace
    (workspace / ".dadaiaignore").unlink()
    root_fix = the_fix(_gate(workspace, "junk.txt"), workspace)
    (workspace / "repos" / "demo").mkdir(parents=True)
    runs = [_in_shell(shell, root_fix, workspace / "repos" / "demo") for _ in range(2)]
    assert [r.returncode for r in runs] == [0, 0], [r.stderr for r in runs]
    cli_fix = fix_line(workspace)
    if oslib.detect().windows:
        assert cli_fix.startswith("Agent action: run ")
    else:
        assert _in_shell(shell, cli_fix, workspace / "repos" / "demo").returncode == 0
    assert (workspace / ".dadaia" / "tmp").is_dir()
    assert not (workspace / ".dadaiaignore").exists()  # the fix never writes the operator's file


@pytest.mark.parametrize("shell", oslib.shells_for(oslib.detect()))
def test_a_cli_fix_without_a_blank_runs_the_cli_in_every_host_shell(
    workspace: Path, shell: str
) -> None:
    """The CLI ran, not a shell echo of its quoted path (PowerShell exits 0 on an expression)."""
    run = _in_shell(shell, fix_line(workspace), workspace)
    direct = os_run([workspace_cli_path(workspace)], check=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == direct.stdout.strip()


@_SLOW
def test_dead_leaves_a_clean_published_detached_head(world: World) -> None:
    done = _hit(world, _dead_clean_detached(world))
    assert done.returncode == 0, done.stdout + done.stderr
    _dead_done(world)


@_SLOW
def test_dead_pushes_an_associated_repo_while_its_main_repo_is_absent(world: World) -> None:
    """Dead's preflight reads the gitflow
    through the same reader — an absent main repo is the default, never a traceback."""
    _associated_on_integration(world)
    world.git(world.ws / "repos" / "lib", "checkout", "-q", "-b", "feature/1.0.0")
    _rmtree(world.repo)
    done = world.cli("context", "dead", "proj")
    assert done.returncode == 0, done.stdout + done.stderr
    _associated_dead(world)


@_SLOW
def test_a_repaired_custom_gitflow_publishes_end_to_end(world: World) -> None:
    """On an empty origin the draft constitution names non-default branches —
    baseline publishes under those names, the shipped gate admitting every push."""
    world.clone()
    world.onboard(_constitution("trunk", "stage", "rel/"))
    done = world.cli("context", "baseline", "proj")
    assert done.returncode == 0, done.stdout + done.stderr
    _baseline_done(world, "rel/0.1.0", ("trunk", "stage"))


@_SLOW
def test_a_clone_on_the_integration_branch_is_never_auto_committed(world: World) -> None:
    """H (dead on develop): the refusal comes before any commit — the local integration
    branch is exactly the remote's."""
    _dirty_on_integration(world)
    before = world.git(world.repo, "rev-parse", "develop")
    assert world.cli("context", "dead", "proj").returncode != 0
    assert world.git(world.repo, "rev-parse", "develop") == before


@_SLOW
def test_every_fix_line_prints_on_one_line_without_a_tty(tmp_path: Path) -> None:
    """H (dead wrapping): a fix naming a path longer than 80 columns stays one line. The
    no-TTY sentinel of every family: gate, baseline, alive and dead refusals all print
    through the one ``cli/_fail.fail`` a real child process exercises here."""
    world = World(tmp_path / ("d" * 90))
    _unborn_dirty(world)
    fix = the_fix(world.cli("context", "dead", "proj"), world.ws)
    assert fix.startswith("Agent action: move ") and fix.endswith("notes.txt into a worktree"), fix
    assert re.search(re.escape(str(world.ws)), fix)


@_SLOW
def test_the_gate_is_read_only_and_its_fix_is_one_agent_action_naming_the_listed_path(
    world: World,
) -> None:
    """The denylist refusal's one fix is an Agent action naming the listed path; the gate
    offers no history rewrite and no publish verb that rewrites."""
    command = _denylisted(world)
    fix = the_fix(_hit(world, command), world.ws)
    assert fix.startswith("Agent action: ") and "notes.md" in fix, fix
    assert "--rewrite-from" not in fix
    assert "--republish" not in world.cli("context", "baseline", "--help").stdout


@_SLOW
def test_a_denylisted_tag_from_a_detached_head_on_an_empty_origin_prints_no_command(
    world: World,
) -> None:
    """The range reaches a root commit and the ref is a tag — the refusal
    names the agent action, prints no command, and the repo stays a repo."""
    world.clone()
    world.deny()
    world.commit("README.md", "r\n")
    world.commit("notes.md", f"a {_TERM}\n")
    world.git(world.repo, "tag", "tagged")
    world.git(world.repo, "checkout", "-q", "--detach", "tagged")
    done = _hit(world, "git push -q origin tagged")
    output = done.stdout + done.stderr
    assert done.returncode != 0 and "\nfix: Agent action: " in output
    assert world.git(world.repo, "rev-parse", "HEAD") == world.git(
        world.repo, "rev-parse", "tagged"
    )
    assert world.remote_heads() == {}


@_SLOW
def test_dead_on_a_non_fast_forward_carries_gits_own_text_and_removes_nothing(
    world: World,
) -> None:
    """No pull fix row leads dead into a conflicted merge it would commit and
    push — git's own text stands alone; the checkout stays."""
    _on_work(world)
    _advance_origin_work(world)
    write_text(world.repo / "README.md", "edited\n")
    world.git(world.repo, "commit", "-qam", "edited")
    done = world.cli("context", "dead", "proj")
    output = done.stdout + done.stderr
    assert done.returncode != 0 and "rejected" in output
    assert "\nfix: " not in output
    assert world.repo.is_dir() and not (world.repo / ".git" / "MERGE_HEAD").exists()


@_SLOW
def test_a_refused_baseline_push_names_the_anchor_and_the_publish_as_the_next_step(
    world: World,
) -> None:
    """The gate refuses baseline's push — the refusal keeps the gate's
    one fix (an Agent action naming the listed path) and names the anchor and the publish
    as the step after that fix (a hand push would drop origin's merge parent)."""
    done = _hit(world, _baseline_denylisted(world))
    output = done.stdout + done.stderr
    assert done.returncode != 0 and the_fix(done, world.ws).startswith("Agent action: ")
    assert f"onboarding commit {world.git(world.repo, 'rev-parse', 'HEAD')}" in output
    assert fix_line(world.ws, "context", "baseline", "proj") in output.replace("\n", "")


@_SLOW
def test_dead_after_the_operator_pulls_into_a_conflict_publishes_no_markers(
    world: World,
) -> None:
    """The operator follows git's own `git pull` hint into a conflict;
    the unmerged file is a dirty checkout dead refuses — nothing published, the checkout kept."""
    _on_work(world)
    _advance_origin_work(world)
    other = world.tmp / "other"
    write_text(other / "README.md", "theirs\n")
    world.git(other, "commit", "-qam", "t")
    world.git(other, "push", "-q", "origin", "feature/1.0.0")
    write_text(world.repo / "README.md", "mine\n")
    world.git(world.repo, "commit", "-qam", "mine")
    world.run("git pull -q --no-rebase --no-edit origin feature/1.0.0", world.repo)
    published = world.remote_heads()["feature/1.0.0"]
    done = world.cli("context", "dead", "proj")
    output = done.stdout + done.stderr
    fix = the_fix(done, world.ws)
    assert done.returncode != 0 and "README.md" in fix and "x.md" in fix, output
    assert fix.startswith("Agent action: move ") and fix.endswith("into a worktree"), output
    assert world.repo.is_dir() and world.remote_heads()["feature/1.0.0"] == published


@pytest.mark.slow(reason="a real doctor child process")
def test_the_real_doctor_prints_every_fix_as_one_whole_runnable_line(tmp_path: Path) -> None:
    """A workspace finding (an expired tmp entry), an error-class specs finding (FIXED-1 on a
    symlinked QUALITY.md) and a ledger finding (a malformed BACKLOG.json), through a
    `dadaia doctor` subprocess at a 61-char root with COLUMNS unset: exit 1, and every `fix:`
    line is one whole line in one of the two fix forms."""
    ws = own_venv_workspace(tmp_path / ("w" * max(1, 61 - len(str(tmp_path)))))
    expired = ws / ".dadaia" / "tmp" / "agent" / "20200101"
    expired.mkdir(parents=True)
    os.utime(expired, (0, 0))
    specs = ws / "repos" / "demo" / "specs"
    canon.scaffold(specs, project_name="demo")
    outside = tmp_path / "outside.md"
    write_text(outside, "# Quality\n")
    (specs / "memory" / "QUALITY.md").unlink()
    assert link(str(outside), specs / "memory" / "QUALITY.md", is_dir=False)
    write_text(specs / "backlog" / "BACKLOG.json", "{}\n")
    env = {k: v for k, v in os.environ.items() if k != "COLUMNS"}
    env["PYTHONPATH"] = os.pathsep.join([str(_PKG.parent), *site.getsitepackages()])
    argv = [str(own_venv_python(ws)), "-m", "dadaia_workspace", "doctor", "--specs-dir", str(specs)]
    run = os_run(argv, cwd=ws, env=env, timeout=120)  # noqa: S603
    assert run.returncode == 1, run.stdout + run.stderr
    lines = run.stdout.splitlines()
    assert {"WS-tmp-expired", "FIXED-1", "LEDGER-BACKLOG-SCHEMA"} <= {
        ln.split(" ", 1)[0] for ln in lines
    }
    fixes = [line for line in lines if line.startswith("fix: ")]
    assert fixes, run.stdout
    for fix in fixes:
        if the_fix(fix, ws).startswith("Agent action: "):  # it names the file
            assert re.search(r"\s(/|\w:[\\/])\S", fix), fix
    # a wrapped fix would leave a continuation line that is neither a finding nor a `fix:` line
    assert [ln for ln in lines if ln and not re.match(r"(fix: |[A-Z][A-Za-z0-9-]+ )", ln)] == []


@pytest.mark.parametrize(
    "site", ["gate-merge-only-lists-the-worktrees", "kernel-no-specs-tree-lists-the-worktrees"]
)
def test_a_worktree_listing_fix_runs_the_public_runner(workspace: Path, site: str) -> None:
    """The gate and the kernel send the agent to `dadaia worktree list`, never to the skill script."""
    fix = the_fix(SITES[site](workspace), workspace)

    assert fix == command(str(workspace_cli_path(workspace)), "worktree", "list")


def test_no_fix_line_literal_in_the_library_names_the_skill_script() -> None:
    """A `fix:` text, or an argument of `fix_line`/`spell_fix`, runs `dadaia worktree`, never `worktree.py`."""

    def literal(node: ast.AST) -> str:
        return "".join(
            n.value
            for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        )

    hits: list[str] = []
    for path in sorted(_PKG.rglob("*.py")):
        for node in ast.walk(ast.parse(read_text(path))):
            carried = []
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) in {"fix_line", "spell_fix"}:  # fmt: skip
                carried = [*node.args, *(k.value for k in node.keywords)]
            elif isinstance(node, ast.Constant | ast.JoinedStr) and literal(node).startswith("fix:"):  # fmt: skip
                carried = [node]
            if any("worktree.py" in literal(c) for c in carried):
                hits.append(f"{path.relative_to(_PKG.parent)}:{node.lineno}")
    assert sorted(set(hits)) == []


#: The POSIX shim's one label line, whole: its exception is keyed by this text, never its number.
_SHIM = "dadaia_workspace/public/scripts/pre-push-ci-gate.sh"
_SHIM_LABEL = r'    echo "[pre-push]   fix: Agent action: install the workspace venv (re-run \`uvx dadaia-workspace init\` at the workspace root)." >&2'


def _action_label_hits(pkg: Path) -> list[str]:
    """Each `Agent action:` / `Operator action:` line of *pkg*'s `.py` and `.sh` files, but the
    kernel producer and the shim's one exact line; a second copy of that line is a hit."""
    label = re.compile(r"(Agent|Operator) action:")
    producer = "dadaia_workspace/public/skills/dd-bug-resolution/scripts/_platform.py"
    hits: list[str] = []
    for p in sorted([*pkg.rglob("*.py"), *pkg.rglob("*.sh")]):
        rel = p.relative_to(pkg.parent).as_posix()
        if rel == producer:
            continue
        exempt = rel == _SHIM
        for n, line in enumerate(read_text(p).splitlines(), 1):
            if not label.search(line):
                continue
            if exempt and line == _SHIM_LABEL:
                exempt = False
                continue
            hits.append(f"{rel}:{n}")
    return hits


def test_only_the_producer_spells_an_action_label() -> None:
    """The one-grep contract: `Agent action:` / `Operator action:` appear in no `.py` or `.sh`
    under the library but the kernel producer and the POSIX shim's one line."""
    assert _action_label_hits(_PKG) == []


def test_a_second_action_label_line_in_the_shim_is_a_hit(tmp_path: Path) -> None:
    pkg = tmp_path / "dadaia_workspace"
    _write(pkg / "public" / "scripts" / "pre-push-ci-gate.sh", f"{_SHIM_LABEL}\n{_SHIM_LABEL}\n")
    assert _action_label_hits(pkg) == [f"{_SHIM}:2"]


def _attribute_act_calls(pkg: Path) -> list[str]:
    """Every `<x>.act(...)` call under *pkg*."""
    return [
        f"{p.relative_to(pkg.parent).as_posix()}:{node.lineno}"
        for p in sorted(pkg.rglob("*.py"))
        for node in ast.walk(ast.parse(read_text(p)))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "act"
    ]


def test_no_module_calls_act_through_an_attribute() -> None:
    """An action label is spelled by a bare `act(...)`; `platform.act(...)` is not a producer call."""
    assert _attribute_act_calls(_PKG) == []


def test_a_planted_attribute_act_call_is_a_hit(tmp_path: Path) -> None:
    pkg = tmp_path / "dadaia_workspace"
    _write(pkg / "core" / "platform.py", "act = _owner.act\n")
    _write(pkg / "features" / "gate.py", 'text = platform.act("agent", "edit the file")\n')
    assert _attribute_act_calls(pkg) == ["dadaia_workspace/features/gate.py:1"]
