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
* ``generate-memory-catalog.py`` — only PARTIALLY one-sourced (A16.3): its duplicated
  ``estimate_tokens`` formula is deleted in favour of importing
  ``features/specs/catalog.py:estimate_tokens``, but its ``generate_catalog``/
  ``generate_index_md`` functions and its ``--memory-dir``/``--out``/``--index-out``/
  ``--context`` CLI surface stay LOCAL BY DESIGN — they are pinned by
  ``tests/contract/test_memory_catalog_render_contract.py`` (F-84) with a signature
  that differs from ``features/specs/catalog.py``'s own ``specs_dir``-rooted,
  context-derived public API. It is intentionally NOT in the thin-wrapper registry.
* ``lint-dadaia-cli-reachability.py`` — standalone by design (its own ``--self-test``);
  it has no package canonical to mirror at all, so it is outside this contract's scope
  entirely, not merely excluded. ``lint-skill-collisions.py`` was the same shape and is
  RETIRED (FR9/T-044-15, v0.4.4): its logic is ported into
  ``tests/contract/test_rules_skills_map.py``, the one deterministic enforcer that
  replaces it — no projected script mirrors it any more.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts"

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
    }
)
_PARTIALLY_ONE_SOURCED: frozenset[str] = frozenset({"generate-memory-catalog.py"})


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
    known = set(_THIN_WRAPPER_SCRIPTS) | _STANDALONE_BY_DESIGN | _PARTIALLY_ONE_SOURCED
    unaccounted = all_scripts - known
    assert not unaccounted, (
        f"public/scripts/ gained new .py file(s) not classified by this contract: "
        f"{sorted(unaccounted)} — add each to _THIN_WRAPPER_SCRIPTS (if its logic "
        "moved into the package), _PARTIALLY_ONE_SOURCED, or _STANDALONE_BY_DESIGN."
    )
