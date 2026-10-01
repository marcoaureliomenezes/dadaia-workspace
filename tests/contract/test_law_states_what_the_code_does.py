"""Intent: CONTRACT — sa-text-restates-rules-the-code-contradicts: a law or docstring
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
from dadaia_workspace.hooks import _common, pre_gate, sdd_gate
from dadaia_workspace.infrastructure.runtime_transforms import hook_wrappers

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_PKG = _REPO / "dadaia_workspace"
_MAP = _PKG / "public" / "data" / "AGENTS.md"


def test_the_map_states_what_the_gate_judges() -> None:
    """sa-text-restates-rules-the-code-contradicts#49.1 (first-token rows: unit test_venv_guard);
    gate-law-claims-out-of-scope-writes-blocked-but-bash-is-never-judged (map, README);
    AC2.8 the fail-open paths in one place; AC2.9 no pip; AC2.13 the onboarding writers."""
    tools = ("Write", "Edit", "MultiEdit", "apply_patch")
    assert {*tools, "NotebookEdit", "write_file", "edit_file"} == _common.WRITE_TOOLS
    line = next(ln for ln in _MAP.read_text("utf-8").splitlines() if "One PreToolUse gate" in ln)
    assert "first token is `dadaia` or `python -m dadaia_workspace`" in line and "pip" not in line
    assert "file-tool write (`" + "`, `".join(tools) + "`) creating a new" in line
    assert "a file-tool write (those or `NotebookEdit`) that is PROTECTED" in line
    assert [h.split(":")[0] for h in _lines(r"fails? open")] == ["public/data/AGENTS.md"]
    assert "only `context create` and a repo's first `specs init` write `specs/`" in _MAP.read_text(
        "utf-8"
    )
    readme = (_REPO / "README.md").read_text("utf-8")
    gate = next(p for p in readme.split("\n\n") if "The gate is one PreToolUse" in p)
    assert "root `AGENTS.md` §3" in gate and "pip" not in gate


_SESSION_NAMES = ("DADAIA_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID",
                  "CODEX_THREAD_ID", "session_id")  # fmt: skip


def _fail_open_rows(tmp: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
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
        "ADR 0118": hook_wrappers.TOOL_TIMEOUT_S == 10,
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
    named = [m[1] for i in items if (m := re.search(r"\(([^()]+)\)\s*$", i))]
    rows = _fail_open_rows(tmp_path, monkeypatch)
    assert len(named) == len(items) and sorted(named) == sorted(rows)
    assert [k for k, held in rows.items() if not held] == []


def test_no_docstring_restates_the_session_id_order() -> None:
    """sa-text-restates-rules-the-code-contradicts#49.2: the precedence is
    resolve_session_id's alone; no other module spells a session-id chain."""
    chains = []
    for path in sorted(_PKG.rglob("*.py")):
        if path.name == "invocation.py" and path.parent.name == "core":
            continue
        for number, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
            if re.search(r"→|->", line) and sum(name in line for name in _SESSION_NAMES) >= 2:
                chains.append(f"{path.relative_to(_REPO)}:{number}")
    assert chains == []


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


def test_the_work_order_has_one_home_the_map() -> None:
    """sa-implementation-adds-before-it-deletes: the map §1 states the order once; no skill."""
    rule = "Every change minimizes code and tests: DELETE → REBUILD → UPDATE → KEEP → ADD last;"
    skills = [p.read_text("utf-8") for p in (_PKG / "public" / "skills").rglob("*.md")]
    assert _MAP.read_text("utf-8").count(rule) == 1 and not [
        t for t in skills if "REBUILD → UPDATE" in t
    ]


_LAW = sorted((_PKG / "public").rglob("*.md"))


def _lines(pattern: str) -> list[str]:
    return [
        f"{path.relative_to(_PKG).as_posix()}:{n}"
        for path in _LAW
        for n, line in enumerate(path.read_text("utf-8").splitlines(), start=1)
        if re.search(pattern, line)
    ]


def test_reports_live_in_the_dadaia_reports_zone() -> None:
    """AC1.13, ADR 0147 (1): the map names `.dadaia/reports/<context>/`; no law names a
    report home inside a repo tree."""
    assert "HTML reports: `.dadaia/reports/<context>/`" in _MAP.read_text("utf-8")
    assert _lines(r"repos/[^`\s]*/reports|reports/<agent>|reports/dd-|repo's reports") == []


def test_no_specs_law_calls_a_path_additive() -> None:
    """AC1.13, ADR 0124: no specs-tree law or recipe grants ADDITIVE, and the map's
    ADDITIVE class names no specs area."""
    specs_laws = [
        _PKG / "public/templates/specs-AGENTS.md",
        _PKG / "public/data/CONSUMER_VALIDATION_RECIPE.md",
    ]
    specs_laws += sorted((_PKG / "public/scaffold").rglob("AGENTS.md"))
    assert [p.name for p in specs_laws if "ADDITIVE" in p.read_text("utf-8")] == []
    assert [
        ln for ln in _MAP.read_text("utf-8").splitlines() if "ADDITIVE" in ln and "specs" in ln
    ] == []


def test_the_bind_law_names_no_print_env() -> None:
    """ADR 0148 (4): the session id comes from the environment only; no law teaches
    `context bind --print-env`."""
    assert _lines(r"--print-env") == []


_POINTERS = ("dd-backlog-definition", "dd-bug-registration", "dd-bug-resolution",
             "dd-code-review", "dd-manager-orchestration", "dd-release-definition",
             "dd-release-implementation")  # fmt: skip


def test_the_worktree_rules_have_one_home() -> None:
    """AC1.13, ADR 0146 (4): only `worktrees/AGENTS.md` and `dd-gitflow-default` name
    `scripts/worktree.py`; seven skills point to the home."""
    namers = {hit.split(":")[0] for hit in _lines(r"scripts/worktree\.py")}
    assert namers == {
        "public/data/worktrees-AGENTS.md",
        "public/skills/dd-gitflow-default/SKILL.md",
    }
    skills = _PKG / "public" / "skills"
    missing = [
        s
        for s in _POINTERS
        if "`worktrees/AGENTS.md`" not in (skills / s / "SKILL.md").read_text("utf-8")
    ]
    assert missing == []


def test_the_acceptance_law_has_one_home() -> None:
    """ADR 0151 M4: the map and the three role personas point to `specs/ADRs/AGENTS.md` §2."""
    assert {h.split(":")[0] for h in _lines(r"`specs/ADRs/AGENTS\.md` §2")} == {
        "public/data/AGENTS.md",
        *(
            f"public/agents/dd-{r}.md"
            for r in ("product-engineer", "software-engineer", "code-reviewer")
        ),
    }


def _script(rel: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(Path(rel).stem, _PKG / "public/skills" / rel)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_commit_shapes_stage_the_kinds_allowed_set() -> None:
    """AC3.13 (F053, F054, F057; gitflow-shape2-omits-backlog-histo): every path a §3a row
    stages is in each named kind's allowed set (`KINDS`); no "alone", no "picked bugs"."""
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
    assert outside == [] and "alone" not in section and _lines(r"picked bugs") == []


def test_the_marker_lifecycle_is_stated_once_in_marks_order() -> None:
    """AC4.6 (DEL implementer-persona-states-a-second-task-marker-lifecycle; ADR 0141): the
    releases law's transitions equal `_release_schema.MARKS` in order; no other law states one."""
    marks = _script("dd-release-implementation/scripts/_release_schema.py").MARKS
    arrow = r"`?\[([ x-])\]`?\s*-+>\s*`?\[([ x-])\]"
    home = _PKG / "public/scaffold/releases/AGENTS.md"
    law = home.read_text("utf-8")
    assert re.findall(arrow, law) == list(zip(marks, marks[1:], strict=False))
    assert [p for p in _LAW if p != home and re.search(arrow, p.read_text("utf-8"))] == []
