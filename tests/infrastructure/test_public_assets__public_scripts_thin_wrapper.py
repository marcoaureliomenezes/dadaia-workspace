"""0.4.7 FR1 (ADR 0018 measured_by): skill owner scripts; AC3.1 (ADR 0135):
one loader, one owner per grammar. Size: SMALL.

A ``public/skills/*/scripts/`` script OWNS its logic, so it must be self-contained:
stdlib imports only, exec bit set, and ``--help`` exits 0. Size is never capped: class and
method size and responsibility are review signals (ADR 0143).
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    _SKILL_SCRIPT_SHARED,  # allow-private-import: the staged siblings of a ledger script
)
from tests.helpers.scan_population import assert_populated

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SKILLS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "skills"

#: Owner scripts whose verb set includes `check` (the ledger scripts of FR2). A
#: script listed here must expose `check`; `registry.py` owns ports, not a ledger.
_LEDGER_OWNER_SCRIPTS: frozenset[str] = frozenset(
    {"bugs.py", "backlog.py", "release.py", "audit.py", "memory.py"}
)


# --- Owner scripts: public/skills/*/scripts/*.py (0.4.7 FR1) ------------------------


def _owner_scripts() -> list[Path]:
    return sorted(_SKILLS_DIR.glob("*/scripts/*.py"))


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


#: The cross-skill import edges, each a read-only use of the grammar's one owner (ADR
#: 0135): the release skill reads the navigator's drift decider and, at closure, the
#: worktrees' rows; the worktree script reads the release skill's trio status parser and
#: the backlog exit its Origin parser (ADR 0161) and the bug reader (ADR 0137); `_specs`
#: reads the worktree name grammar (``NAME_RE``). No module imports back along its own edge.
_CROSS_SKILL_EDGES = {
    "dd-release-implementation": {"_memory_drift", "_worktree_git", "_worktree_names"},
    "dd-gitflow-default": {"_release_schema", "_specs"},  # `_specs`: the fix-line quote
    "dd-backlog-definition": {"_release_schema", "_bugs_store"},
    "dd-bug-resolution": {"_release_schema", "_worktree_names"},
}


@pytest.mark.parametrize("script", _owner_scripts(), ids=lambda p: f"{p.parents[1].name}/{p.name}")
def test_skill_owner_script_meets_the_contract(script: Path) -> None:
    """FR1: every skill script is a self-contained stdlib owner — no import into
    the library, executable, and (for an entry point) `--help` exits 0.

    A script may split its verbs into `_`-prefixed sibling modules in the same folder, imported through the script's own directory on
    `sys.path`. A sibling is a module, not an entry point, so only the non-`_` scripts
    answer `--help`; everything else applies to every file under `scripts/`.
    """
    siblings = {module.stem for module in script.parent.glob("*.py")}
    skill = script.parent.parent.name
    siblings |= {Path(d).stem for _, d in _SKILL_SCRIPT_SHARED if d.startswith(f"skills/{skill}/")}
    siblings |= _CROSS_SKILL_EDGES.get(skill, set())
    foreign = _imported_roots(script) - set(sys.stdlib_module_names) - siblings
    assert foreign == set(), (
        f"{script.name} imports non-stdlib module(s) {sorted(foreign)} — a skill script "
        "runs from a projected skill folder with no library on sys.path (FR1)."
    )
    assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n"), (
        f"{script.name} is missing the `#!/usr/bin/env python3` shebang."
    )
    assert os.access(script, os.X_OK), f"{script.name} is not executable (exec bit unset)."
    if script.name.startswith("_"):
        return  # a sibling module, imported by its entry point — it has no argv surface

    done = subprocess.run(
        [sys.executable, str(script), "--help"], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, f"{script.name} --help exited {done.returncode}: {done.stderr}"


def test_ledger_owner_scripts_expose_check() -> None:
    """Every ledger script's read verb is `check` — the one name the doctor delegates to."""
    present = {p.name for p in _owner_scripts()}
    assert_populated(present, sentinel="registry.py")
    missing = _LEDGER_OWNER_SCRIPTS - present
    assert not missing, f"_LEDGER_OWNER_SCRIPTS names missing script(s): {sorted(missing)}"
    for script in _owner_scripts():
        if script.name not in _LEDGER_OWNER_SCRIPTS:
            continue
        done = subprocess.run(
            [sys.executable, str(script), "check", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, f"{script.name} has no `check` subcommand: {done.stderr}"


# --- The 0135 contract: one loader, one owner per grammar (AC3.1, PLAN §1.1) --------

_PACKAGE = _REPO_ROOT / "dadaia_workspace"
_LOADER = "infrastructure/ledger_scripts.py"
_RE_CALLS = {"compile", "search", "match", "fullmatch", "finditer", "findall", "sub", "split"}
#: A grammar's head, as a package regex would spell it; only its owner and pinned twin hold it.
_GRAMMAR_HEADS = {r"\*\*Origin:\*\*": set(), r"\*\*Status:\*\*": {"core/spec_status.py"}}
#: Each §1.1 owner's pinned file and top-level names (the Status pair: `test_spec_status.py`).
_SCHEMA = "public/skills/dd-release-implementation/scripts/_release_schema.py"
_OWNERS = {
    _SCHEMA: {"origin", "MARK_RE", "MARKS", "writes"},
    "public/skills/dd-bug-resolution/scripts/_ledger.py": {"records", "validate", "terms"},
    _LOADER: {"load_owner"},
    "core/context_registry.py": {"entries"},
    "features/migrate/state_v2.py": {"execute_migration"},  # the registry's upgrader
    "public/skills/dd-gitflow-default/scripts/_worktree_names.py": {"NAME_RE", "locate"},
    "core/cli_line.py": {"script_line"},
}


def _violations(source: str, rel: str) -> list[str]:
    """What `rel` does that only the loader or a grammar's owner may: exec, `runpy`, or a grammar regex."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
            if "runpy" in names or any("public.skills" in n for n in names):
                found.append(f"{rel}:{node.lineno} loads a script outside the loader")
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name in {"exec", "run_path", "exec_module"} and rel != _LOADER:
            found.append(f"{rel}:{node.lineno} {name}s outside the loader")
        arg = node.args[0] if node.args else None
        if name in _RE_CALLS and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            found += [
                f"{rel}:{node.lineno} parses {head} outside its owner"
                for head, twins in _GRAMMAR_HEADS.items()
                if head in arg.value and rel not in twins
            ]
    return found


def _package_modules() -> list[Path]:
    return [p for p in _PACKAGE.rglob("*.py") if "public" not in p.relative_to(_PACKAGE).parts[:1]]


def test_no_package_module_loads_a_script_or_parses_a_grammar_but_its_owner() -> None:
    """AC3.1: only the loader execs a `public/skills` script; no second grammar parser."""
    modules = _package_modules()
    assert_populated({p.name for p in modules}, sentinel="ledger_scripts.py")
    found = [
        v
        for p in modules
        for v in _violations(p.read_text("utf-8"), p.relative_to(_PACKAGE).as_posix())
    ]
    assert found == []


@pytest.mark.parametrize(
    "planted",
    [
        'import re\nORIGIN = re.compile(r"^\\*\\*Origin:\\*\\*(.*)$")\n',
        'exec(open("s.py").read())\n',
        'import runpy\nrunpy.run_path("s.py")\n',
    ],
    ids=["origin-parser", "exec", "runpy-run-path"],
)
def test_a_planted_second_loader_or_parser_bites(planted: str) -> None:
    assert _violations(planted, "features/x.py")


@pytest.mark.parametrize("rel", _OWNERS)
def test_each_owner_sits_at_its_pinned_location(rel: str) -> None:
    tree = ast.parse((_PACKAGE / rel).read_text("utf-8"))
    defined = {
        t.id if isinstance(t, ast.Name) else getattr(t, "name", None)
        for node in tree.body
        for t in (getattr(node, "targets", None) or [getattr(node, "target", node)])
    }
    assert _OWNERS[rel] <= defined, f"{rel} lost {sorted(_OWNERS[rel] - defined)}"
