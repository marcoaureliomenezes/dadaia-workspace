"""Architecture-diagram drift-guard (v0.1.55 FR7 / AC-5 / AC-7(f)).

The canonical UML diagrams of the post-decomposition shape live as fenced ```mermaid blocks
**inside `specs/memory/ARCHITECTURE.md`** (v6 canon, FR1/T-050-06: `specs/assets/` retired —
the three diagram files formerly under `specs/assets/architecture/` folded in as subsections
of this atom's "## Architecture Diagrams" section). Nothing structurally stops a future
rename/split/merge of a decomposed class or module from silently stranding those diagrams.

This contract is that guard. It derives the live class / module / package names **by importing
the decomposed modules and introspecting them** — a hardcoded expectation list is FORBIDDEN
(else the AC-7(f) sabotage — rename a diagrammed class without touching the code, or vice
versa — would stay green). It then parses each diagram's mermaid block (located by its own
subsection heading, in document order) and asserts, in both directions:

* **Forward** — every live decomposed name IS mentioned in its diagram (catches a code rename
  the diagram was not updated for, and a live symbol the diagram never listed).
* **Reverse** — every diagram node that *claims* to be a decomposed class/module IS a live
  importable name (catches a diagram node renamed to a stale name).

It also fails if the atom or one of the three subsections/mermaid blocks goes missing.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ARCHITECTURE_MD = _REPO_ROOT / "specs" / "memory" / "ARCHITECTURE.md"

# Subsection headings (the diagram's own H3, verbatim) — NOT a name-expectation list; every
# class/module/package NAME asserted below is derived by introspection, never hardcoded.
_DOCTOR_HEADING = "### `features/specs/doctor` — SpecsDoctor coordinator + validator siblings"
_FEATURES_HEADING = "### `dadaia_workspace/features` — package map (26 packages)"
_PANEL_HEADING = "### `features/panel/views` — per-domain API view modules"

_MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CLASS_DECL_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)


# --------------------------------------------------------------------------- diagram parsing


def _architecture_md_text() -> str:
    assert _ARCHITECTURE_MD.is_file(), (
        f"the v6 canon memory atom is missing: {_ARCHITECTURE_MD.relative_to(_REPO_ROOT)}"
    )
    return _ARCHITECTURE_MD.read_text(encoding="utf-8")


def _mermaid_block_under_heading(text: str, heading: str) -> str:
    """Return the sole fenced ```mermaid block that follows *heading* (up to the next H2/H3)."""
    start = text.find(heading)
    assert start != -1, f"{_ARCHITECTURE_MD.name} is missing the subsection: {heading!r}"
    body_start = start + len(heading)
    next_heading = re.search(r"\n#{2,3}\s", text[body_start:])
    section = (
        text[body_start : body_start + next_heading.start()] if next_heading else text[body_start:]
    )
    blocks = _MERMAID_BLOCK_RE.findall(section)
    assert len(blocks) == 1, (
        f"subsection {heading!r} must carry exactly ONE fenced ```mermaid block "
        f"(found {len(blocks)})."
    )
    return blocks[0]


def _tokens(mermaid: str) -> set[str]:
    return set(_IDENT_RE.findall(mermaid))


def _declared_classes(mermaid: str) -> set[str]:
    return set(_CLASS_DECL_RE.findall(mermaid))


# ------------------------------------------------------------------- live-name introspection


def _iter_package_modules(package: str) -> list[tuple[str, bool]]:
    pkg = importlib.import_module(package)
    return [(name, ispkg) for _finder, name, ispkg in pkgutil.iter_modules(pkg.__path__)]


def _classes_defined_in(module: ModuleType) -> set[str]:
    return {
        name
        for name, obj in inspect.getmembers(module, inspect.isclass)
        if obj.__module__ == module.__name__
    }


def _public_functions_defined_in(module: ModuleType) -> set[str]:
    return {
        name
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if obj.__module__ == module.__name__ and not name.startswith("_")
    }


def _live_doctor_coordinator() -> set[str]:
    doctor = importlib.import_module("dadaia_workspace.features.specs.doctor")
    return _classes_defined_in(doctor)


def _live_validator_classes() -> set[str]:
    classes: set[str] = set()
    for name, _ispkg in _iter_package_modules("dadaia_workspace.features.specs"):
        if not name.startswith("doctor_"):
            continue
        mod = importlib.import_module(f"dadaia_workspace.features.specs.{name}")
        classes |= {c for c in _classes_defined_in(mod) if c.endswith("Validator")}
    return classes


def _live_api_modules() -> set[str]:
    return {
        name
        for name, _ispkg in _iter_package_modules("dadaia_workspace.features.panel.views")
        if name.startswith("api_")
    }


def _live_api_render_functions() -> set[str]:
    functions: set[str] = set()
    for name in _live_api_modules():
        mod = importlib.import_module(f"dadaia_workspace.features.panel.views.{name}")
        functions |= _public_functions_defined_in(mod)
    return functions


def _live_feature_packages() -> set[str]:
    return {name for name, ispkg in _iter_package_modules("dadaia_workspace.features") if ispkg}


def _live_reports_submodules() -> set[str]:
    return {name for name, _ispkg in _iter_package_modules("dadaia_workspace.features.reports")}


# ------------------------------------------------------------------------------------ tests


def test_architecture_diagrams_present_and_match_live_names() -> None:
    """Each canonical diagram subsection exists inside ARCHITECTURE.md, carries one mermaid
    block, and both directions (forward: every live name is diagrammed; reverse: no diagrammed
    node is stale) hold for doctor classes, panel view modules, and feature packages."""
    text = _architecture_md_text()

    # doctor subsection: SpecsDoctor coordinator + the six validator siblings.
    mermaid = _mermaid_block_under_heading(text, _DOCTOR_HEADING)
    declared = _declared_classes(mermaid)
    coordinator = _live_doctor_coordinator()
    validators = _live_validator_classes()
    assert validators, "introspection found no *Validator classes — imports broken?"
    required = coordinator | validators
    missing = required - declared
    assert not missing, (
        f"{_DOCTOR_HEADING!r} does not diagram live doctor class(es): {sorted(missing)}. "
        "Regenerate the diagram (v0.1.55 FR7 regeneration law)."
    )
    stale = {c for c in declared if c.endswith("Validator")} - validators
    assert not stale, (
        f"{_DOCTOR_HEADING!r} diagrams stale validator node(s): {sorted(stale)} "
        "(no such live class). Fix the diagram or the code (AC-7(f) drift-guard)."
    )

    # panel subsection: the per-domain api_* view modules + render functions.
    mermaid = _mermaid_block_under_heading(text, _PANEL_HEADING)
    tokens = _tokens(mermaid)
    declared = _declared_classes(mermaid)
    modules = _live_api_modules()
    render_fns = _live_api_render_functions()
    assert modules, "introspection found no api_* view modules — imports broken?"
    assert render_fns, "introspection found no public render functions — imports broken?"
    missing = (modules | render_fns) - tokens
    assert not missing, (
        f"{_PANEL_HEADING!r} does not diagram live panel name(s): {sorted(missing)}. "
        "Regenerate the diagram (v0.1.55 FR7 regeneration law)."
    )
    stale = {c for c in declared if c.startswith("api_")} - modules
    assert not stale, (
        f"{_PANEL_HEADING!r} diagrams stale api module node(s): {sorted(stale)} "
        "(no such live module). Fix the diagram or the code (AC-7(f) drift-guard)."
    )

    # features subsection: the post-merge feature packages + merged reports submodules.
    mermaid = _mermaid_block_under_heading(text, _FEATURES_HEADING)
    tokens = _tokens(mermaid)
    packages = _live_feature_packages()
    reports_submodules = _live_reports_submodules()
    assert packages, "introspection found no feature packages — imports broken?"
    assert reports_submodules, "introspection found no reports submodules — imports broken?"
    missing = (packages | reports_submodules) - tokens
    assert not missing, (
        f"{_FEATURES_HEADING!r} does not diagram live package(s)/submodule(s): "
        f"{sorted(missing)}. Regenerate the diagram (v0.1.55 FR7 regeneration law)."
    )
