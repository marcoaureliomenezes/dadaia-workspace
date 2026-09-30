"""Intent: CONTRACT — 0.4.7 FR1 (ADR 0018 measured_by): skill owner scripts. Size: SMALL.

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

pytestmark = pytest.mark.contract

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
#: worktrees' rows; the worktree script reads the release skill's trio status parser.
#: No module imports back along its own edge.
_CROSS_SKILL_EDGES = {
    "dd-release-implementation": {"_memory_drift", "_worktree_git", "_worktree_kinds"},
    "dd-gitflow-default": {"_release_schema"},
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
