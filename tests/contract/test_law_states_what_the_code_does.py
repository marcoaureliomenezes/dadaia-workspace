"""sa-text-restates-rules-the-code-contradicts: a law or docstring
sentence that restates a rule states what the code does, or cites the code instead.
Size: SMALL — text reads, one AST walk, in-process gate calls; one pre-gate subprocess, as
stdin is the only way an unreadable payload reaches the hook.
"""

from __future__ import annotations

import ast
import configparser
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path, PurePath
from types import ModuleType

import pytest

from dadaia_workspace.core import context_registry
from dadaia_workspace.features.spec_context import gate_policy
from dadaia_workspace.hooks import pre_gate, sdd_gate
from dadaia_workspace.infrastructure.runtime_transforms import hook_wrappers

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_PKG = _REPO / "dadaia_workspace"
_MAP = _PKG / "public" / "data" / "AGENTS.md"


def _fail_open_rows(
    law: dict[str, str], tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, bool]:
    """One row per fail-open path, keyed by the evidence the law names, each read from code."""
    hooks = _REPO / "tests/integration/gate/test_hook_interpreter.py"
    (tmp / ".dadaia/states").mkdir(parents=True)
    (tmp / ".dadaia/states/spec_contexts.json").write_text("{trunc", "utf-8")
    gate = [sys.executable, "-m", "dadaia_workspace.hooks.pre_gate"]
    unreadable = subprocess.run(gate, input="not json", capture_output=True, text=True,
                                cwd=tmp, env={**os.environ, "PYTHONPATH": str(_REPO)})  # fmt: skip

    def raises(_: dict[str, object]) -> str:
        raise RuntimeError

    monkeypatch.setattr(pre_gate, "_POLICIES", (raises,))
    bash = {"tool_name": "Bash", "tool_input": {"command": "echo x > AGENTS.md"}}
    worktree = {"root": PurePath("/ws"), "zone": "worktree", "repo": "r", "owner": "r"}
    return {
        "ADR 0067": "def test_missing_venv_is_loud_and_fails_open_on_every_harness"
        in hooks.read_text("utf-8"),
        "ADR 0118": f"past {hook_wrappers.TOOL_TIMEOUT_S} s" in law["ADR 0118"],
        "ADRs 0096, 0103, 0133": sdd_gate.evaluate_payload(bash) is None,
        "ADR 0116": gate_policy.evaluate("worktrees/r/w/x.py", has_id=False, **worktree)[0]
        == gate_policy.Decision.ALLOW
        != gate_policy.evaluate("worktrees/r/w/x.py", **worktree)[0],
        "`pre_gate`": pre_gate.evaluate_payload({}) is None,
        "`read_stdin_json`": unreadable.returncode == 0 and "deny" not in unreadable.stdout,
        "ADR 0132": context_registry.registered_slugs(tmp) == ({"*"}, {"*"}),
    }


def test_the_map_lists_every_fail_open_path_the_code_has(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4.9 (FR seventh-fail-open-path-law-line, F080): the map's fail-open list is
    set-equal to the code's paths, each naming its evidence; no sentence pinned."""
    line = next(ln for ln in _MAP.read_text("utf-8").splitlines() if "fails open on:" in ln)
    items = line.split("fails open on:")[1].rstrip(".").split(";")
    named = {m[1]: i for i in items if (m := re.search(r"\(([^()]+)\)\s*$", i))}
    rows = _fail_open_rows(named, tmp_path, monkeypatch)
    assert len(named) == len(items) and sorted(named) == sorted(rows)
    assert [k for k, held in rows.items() if not held] == []


def test_the_bind_resolution_contract_covers_every_verb_module() -> None:
    """sa-text-restates-rules-the-code-contradicts#49.4: every cli/commands/* module is a
    source of the bind-resolution-seam contract, so a direct core.invocation import in any
    verb (harness, reconcile, capabilities, certify included) breaks lint-imports."""
    config = configparser.ConfigParser()
    config.read(_REPO / "setup.cfg", encoding="utf-8")
    sources = config["importlinter:contract:bind-resolution-seam-is-a-single-home"]
    modules = sources["source_modules"].split()
    verbs = sorted((_PKG / "cli" / "commands").glob("[!_]*.py"))
    uncovered = [
        v.stem for v in verbs
        if not any(f"dadaia_workspace.cli.commands.{v.stem}".startswith(m) for m in modules)
    ]  # fmt: skip
    assert verbs and uncovered == []


def test_os_name_is_read_only_through_the_platform_seam() -> None:
    """sa-text-restates-rules-the-code-contradicts#49.5: no `os.name` read in the package
    outside core/platform (python_env branches on PLATFORM). Stdlib skill scripts under
    public/ cannot import core and are out of this ratchet."""
    reads = [
        f"{path.relative_to(_REPO)}:{node.lineno}"
        for path in sorted(_PKG.rglob("*.py"))
        if "public" not in path.relative_to(_PKG).parts
        for node in ast.walk(ast.parse(path.read_text("utf-8")))
        if isinstance(node, ast.Attribute) and node.attr == "name"
        and isinstance(node.value, ast.Name) and node.value.id == "os"
    ]  # fmt: skip
    assert reads == []


def _script(rel: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(Path(rel).stem, _PKG / "public/skills" / rel)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_commit_shapes_stage_the_kinds_allowed_set() -> None:
    """AC3.13 (F053, F054, F057; gitflow-shape2-omits-backlog-histo): every path a §3a row
    stages is in each named kind's allowed set (`KINDS`)."""
    kinds = _script("dd-gitflow-default/scripts/_worktree_kinds.py")
    text = (_PKG / "public/skills/dd-gitflow-default/SKILL.md").read_text("utf-8")
    section = text.split("## 3a.")[1].split("\n## ")[0]
    rows = [ln.split(" | ") for ln in section.splitlines() if re.match(r"\| \d", ln)]
    staged = [(re.findall(r"`(\w+)`", r[1]), re.findall(r"`(<code>|specs/[^`]+)`", r[2]))
              for r in rows]  # fmt: skip
    assert {k for ks, _ in staged for k in ks} == set(kinds.KINDS)
    assert all(paths for _, paths in staged)
    outside = [(k, p) for ks, ps in staged for k in ks for p in ps
               if not kinds.allows(k, "src/x.py" if p == kinds.CODE else p)]  # fmt: skip
    assert outside == []


def test_the_releases_law_transitions_equal_marks() -> None:
    """AC4.6 (ADR 0141): the releases law's marker transitions equal `_release_schema.MARKS`
    in order."""
    marks = _script("dd-release-implementation/scripts/_release_schema.py").MARKS
    arrow = r"`?\[([ x-])\]`?\s*(?:-+>|→|=>)\s*`?\[([ x-])\]"
    law = (_PKG / "public/scaffold/releases/AGENTS.md").read_text("utf-8")
    assert re.findall(arrow, law) == list(zip(marks, marks[1:], strict=False))
