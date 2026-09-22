"""A16.2 structural guarantee — mirrored public/scripts/ stay thin wrappers (v0.4.3
T-043-20/FR16).

Intent: CONTRACT — durable, small, structural. Size: SMALL (pure file-content checks,
no subprocess, no fixture tree). FR16 inverted the pre-v0.4.3 architecture: a script's
lint/catalog LOGIC used to live in the PROJECTED copy under
``dadaia_workspace/public/scripts/``, with the package shelling out to it
(``doctor_memory.py`` -> ``subprocess`` -> ``lint-memory-atoms.py``). The logic now
lives in the package (``features/specs/memory_lint.py``), imported directly; the
projected script becomes a thin wrapper. Nothing else stops that duplication from
silently re-accreting over time — a future edit could paste business logic back into
the projected copy and nothing would notice. This test is that backstop.

The rule is DATA-DRIVEN (``_THIN_WRAPPER_SCRIPTS``): a script joins the assertion by
adding one line to that dict, not by writing a new test — "so future one-sourcing
extends it" (T-043-20 instruction).

Scope is deliberately narrow — do NOT read "every script under public/scripts/" as
"every script must be thin":

* ``lint-memory-atoms.py`` — fully one-sourced (A16.1/A16.2): its lint logic lives
  entirely in ``features/specs/memory_lint.py``; the projected copy only imports and
  calls that module's ``main()``. Asserted thin here.
* ``generate-memory-catalog.py`` — DELETED (v0.5.1 T-051-16, K10/A10.1/A10.4): the
  duplicate it was "only partially one-sourced" with is gone; ``features/specs/
  catalog.py`` is now the only catalog generator, and the contract test that used to
  police the pair's byte-identity (``test_memory_catalog_render_contract.py``) is
  deleted with its subject.
* ``lint-dadaia-cli-reachability.py`` — standalone by design (its own ``--self-test``);
  it has no package canonical to mirror at all, so it is outside this contract's scope
  entirely, not merely excluded. ``lint-skill-collisions.py`` was the same shape and is
  RETIRED (FR9/T-044-15, v0.4.4): its logic is ported into
  ``tests/contract/test_behavior_map.py``, the one deterministic enforcer that
  replaces it — no projected script mirrors it any more.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts"
_SKILLS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "skills"

#: 0.4.7 FR1 (ADR 0018 measured_by) — the OTHER half of this contract. A
#: `public/scripts/` mirror is thin because its logic lives in the package; a
#: `public/skills/*/scripts/` script is the OWNER of its logic and must therefore be
#: self-contained: stdlib imports only (no import path into `dadaia_workspace`), exec
#: bit set, `--help` exits 0, and small enough that owning the logic stays honest.
_OWNER_SCRIPT_MAX_LINES = 150

#: Ratchet: a script measured ABOVE the ceiling when the contract landed keeps its
#: measured count until it is split — `registry.py` (0.4.7 c5) predates FR1's 150-line
#: rule. Lowering an entry is welcome; raising one defeats the contract.
_OWNER_SCRIPT_CEILINGS: dict[str, int] = {"registry.py": 339}

#: Owner scripts whose verb set includes `check` (the ledger scripts of FR2). A
#: script listed here must expose `check`; `registry.py` owns ports, not a ledger.
_LEDGER_OWNER_SCRIPTS: frozenset[str] = frozenset(
    {"bugs.py", "backlog.py", "release.py", "audit.py", "memory.py"}
)

#: Data-driven registry (A16.2): script name -> max total line count for a genuine
#: thin wrapper. Lowering a ceiling is welcome; raising one (or adding a script whose
#: logic has NOT actually moved into the package) defeats the contract's purpose.
_THIN_WRAPPER_SCRIPTS: dict[str, int] = {
    "lint-memory-atoms.py": 45,
}

#: Scripts intentionally excluded from the registry, with the reason each stays out —
#: read by the exclusion test below so the exclusion itself is data-driven and
#: verified against the real directory listing, not just asserted in prose.
_STANDALONE_BY_DESIGN: frozenset[str] = frozenset(
    {
        "lint-dadaia-cli-reachability.py",
        # A repository build step, not a mirror: it renders the standalone skills
        # repository from `public/skills/` and has no package canonical to thin out.
        "build-skills-repo.py",
    }
)
#: v0.5.1 T-051-16: generate-memory-catalog.py (the only member of this set) is
#: DELETED — the set stays declared, empty, so the exclusion test below still proves
#: (by construction) that nothing is silently re-added to it without review.
_PARTIALLY_ONE_SOURCED: frozenset[str] = frozenset()


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _local_function_and_class_defs(path: Path) -> list[str]:
    """Top-level ``def``/``class`` names DEFINED in this script (AST-based — immune to
    string/comment false positives). A name imported FROM the package and called
    (e.g. ``main()`` imported from ``memory_lint``) is never a local def."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.name
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


@pytest.mark.parametrize("script_name", sorted(_THIN_WRAPPER_SCRIPTS))
def test_mirrored_script_is_a_thin_wrapper(script_name: str) -> None:
    """A16.2: every script named in ``_THIN_WRAPPER_SCRIPTS`` stays a near-zero-LOC
    shim with NO locally-defined business-logic function, and actually references the
    ``dadaia_workspace`` package — it must import (or exec) its canonical package
    module rather than reimplementing the logic locally."""
    path = _SCRIPTS_DIR / script_name
    assert path.is_file(), f"{script_name} not found under {_SCRIPTS_DIR}"

    loc = _line_count(path)
    ceiling = _THIN_WRAPPER_SCRIPTS[script_name]
    assert loc <= ceiling, (
        f"{script_name} has grown to {loc} lines, exceeding the thin-wrapper ceiling "
        f"of {ceiling} — logic may have re-accreted locally instead of living in the "
        "package (A16.2 regression). Either move the new logic into the package and "
        "import it here, or (if it is genuinely wrapper-only growth) raise the "
        "ceiling with a same-commit justification."
    )

    local_defs = _local_function_and_class_defs(path)
    assert local_defs == [], (
        f"{script_name} defines local function/class(es) {local_defs} — a thin "
        "wrapper must import its logic from the package, never define its own "
        "business-logic functions (A16.2 regression)."
    )

    source = path.read_text(encoding="utf-8")
    assert "dadaia_workspace" in source, (
        f"{script_name} does not reference the `dadaia_workspace` package anywhere — "
        "a thin wrapper must import or exec the canonical package module."
    )


def test_thin_wrapper_registry_stays_data_driven_and_correctly_scoped() -> None:
    """The registry names real files; the documented exclusions (standalone-by-design
    scripts and the partially-one-sourced catalog script) are real files too and are
    never accidentally promoted into the strict thin-wrapper registry."""
    for name in _THIN_WRAPPER_SCRIPTS:
        assert (_SCRIPTS_DIR / name).is_file(), f"registry names a missing file: {name}"

    for name in _STANDALONE_BY_DESIGN | _PARTIALLY_ONE_SOURCED:
        assert (_SCRIPTS_DIR / name).is_file(), f"exclusion names a missing file: {name}"
        assert name not in _THIN_WRAPPER_SCRIPTS, (
            f"{name} is documented as excluded from the thin-wrapper contract but is "
            "also present in _THIN_WRAPPER_SCRIPTS — scope drift, fix the registry."
        )

    # Every *.py under public/scripts/ is accounted for by exactly one bucket, so a
    # brand-new script cannot silently sit outside this contract's reasoning.
    all_scripts = {p.name for p in _SCRIPTS_DIR.glob("*.py")}
    # v0.4.5 FR5 (scan-test-vacuity-guard): a mis-rooted _SCRIPTS_DIR would degrade
    # this to an empty set, under which `unaccounted` below is trivially empty too.
    assert_populated(all_scripts, sentinel="lint-memory-atoms.py")
    known = set(_THIN_WRAPPER_SCRIPTS) | _STANDALONE_BY_DESIGN | _PARTIALLY_ONE_SOURCED
    unaccounted = all_scripts - known
    assert not unaccounted, (
        f"public/scripts/ gained new .py file(s) not classified by this contract: "
        f"{sorted(unaccounted)} — add each to _THIN_WRAPPER_SCRIPTS (if its logic "
        "moved into the package), _PARTIALLY_ONE_SOURCED, or _STANDALONE_BY_DESIGN."
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


@pytest.mark.parametrize("script", _owner_scripts(), ids=lambda p: f"{p.parents[1].name}/{p.name}")
def test_skill_owner_script_meets_the_contract(script: Path) -> None:
    """FR1: every skill script is a self-contained stdlib owner — ≤ 150 lines, no
    import into the library, executable, and (for an entry point) `--help` exits 0.

    The ceiling is per FILE: a script whose verb set outgrows it splits into `_`-prefixed
    sibling modules in the same folder, imported through the script's own directory on
    `sys.path` (or a sibling skill's, projected beside it). A sibling is a module, not an entry point, so only the non-`_` scripts
    answer `--help`; everything else applies to every file under `scripts/`.
    """
    loc = _line_count(script)
    ceiling = _OWNER_SCRIPT_CEILINGS.get(script.name, _OWNER_SCRIPT_MAX_LINES)
    assert loc <= ceiling, (
        f"{script.name} has grown to {loc} lines, over the owner-script ceiling of "
        f"{ceiling} — a skill script that no longer fits is logic that "
        "belongs behind a narrower interface, not a raised ceiling."
    )
    siblings = {module.stem for module in script.parent.glob("*.py")}
    # A `_` module of a sibling skill is projected beside this one (SPEC D6: one decider).
    siblings |= {module.stem for module in script.parents[2].glob("*/scripts/_*.py")}
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
