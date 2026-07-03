"""Architecture-diagram drift-guard (v0.1.55 FR7 / AC-5 / AC-7(f)).

The canonical UML diagrams of the post-decomposition shape live as fenced ```mermaid blocks
inside Markdown files under ``specs/assets/architecture/``. Nothing structurally stops a future
rename/split/merge of a decomposed class or module from silently stranding those diagrams.

This contract is that guard. It derives the live class / module / package names **by importing
the decomposed modules and introspecting them** — a hardcoded expectation list is FORBIDDEN
(else the AC-7(f) sabotage — rename a diagrammed class without touching the code, or vice
versa — would stay green). It then parses each diagram's mermaid block and asserts, in both
directions:

* **Forward** — every live decomposed name IS mentioned in its diagram (catches a code rename
  the diagram was not updated for, and a live symbol the diagram never listed).
* **Reverse** — every diagram node that *claims* to be a decomposed class/module IS a live
  importable name (catches a diagram node renamed to a stale name).

It also fails if a diagram file goes missing.
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
_ARCH_DIR = _REPO_ROOT / "specs" / "assets" / "architecture"

# Deliverable asset paths (the diagram files this release commits). These are file locations,
# NOT a name-expectation list — every class/module/package NAME asserted below is derived by
# introspection, never hardcoded.
_DOCTOR_DIAGRAM = _ARCH_DIR / "doctor-decomposition.md"
_PANEL_DIAGRAM = _ARCH_DIR / "panel-views-decomposition.md"
_FEATURES_DIAGRAM = _ARCH_DIR / "feature-packages.md"

_MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CLASS_DECL_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)


# --------------------------------------------------------------------------- diagram parsing


def _sole_mermaid_block(path: Path) -> str:
    assert path.is_file(), f"architecture diagram is missing: {path.relative_to(_REPO_ROOT)}"
    blocks = _MERMAID_BLOCK_RE.findall(path.read_text(encoding="utf-8"))
    assert len(blocks) == 1, (
        f"{path.relative_to(_REPO_ROOT)} must carry exactly ONE fenced ```mermaid block "
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


def test_all_architecture_diagrams_present() -> None:
    """Each canonical diagram file exists and carries exactly one mermaid block."""
    for path in (_DOCTOR_DIAGRAM, _PANEL_DIAGRAM, _FEATURES_DIAGRAM):
        _sole_mermaid_block(path)


def test_doctor_diagram_matches_live_classes() -> None:
    """SpecsDoctor coordinator + the six validator siblings — both directions."""
    mermaid = _sole_mermaid_block(_DOCTOR_DIAGRAM)
    declared = _declared_classes(mermaid)

    coordinator = _live_doctor_coordinator()
    validators = _live_validator_classes()
    assert validators, "introspection found no *Validator classes — imports broken?"

    # Forward: every live coordinator + validator is a declared class node in the diagram.
    required = coordinator | validators
    missing = required - declared
    assert not missing, (
        f"{_DOCTOR_DIAGRAM.name} does not diagram live doctor class(es): {sorted(missing)}. "
        "Regenerate the diagram (v0.1.55 FR7 regeneration law)."
    )

    # Reverse: any declared node that looks like a validator must be a live validator class.
    stale = {c for c in declared if c.endswith("Validator")} - validators
    assert not stale, (
        f"{_DOCTOR_DIAGRAM.name} diagrams stale validator node(s): {sorted(stale)} "
        "(no such live class). Fix the diagram or the code (AC-7(f) drift-guard)."
    )


def test_panel_diagram_matches_live_view_modules() -> None:
    """The eight per-domain api_* view modules + their render functions — both directions."""
    mermaid = _sole_mermaid_block(_PANEL_DIAGRAM)
    tokens = _tokens(mermaid)
    declared = _declared_classes(mermaid)

    modules = _live_api_modules()
    render_fns = _live_api_render_functions()
    assert modules, "introspection found no api_* view modules — imports broken?"
    assert render_fns, "introspection found no public render functions — imports broken?"

    # Forward: every live module name + render function appears in the diagram.
    missing = (modules | render_fns) - tokens
    assert not missing, (
        f"{_PANEL_DIAGRAM.name} does not diagram live panel name(s): {sorted(missing)}. "
        "Regenerate the diagram (v0.1.55 FR7 regeneration law)."
    )

    # Reverse: any declared node named like an api module must be a live api module.
    stale = {c for c in declared if c.startswith("api_")} - modules
    assert not stale, (
        f"{_PANEL_DIAGRAM.name} diagrams stale api module node(s): {sorted(stale)} "
        "(no such live module). Fix the diagram or the code (AC-7(f) drift-guard)."
    )


def test_feature_packages_diagram_matches_live_packages() -> None:
    """The 23 post-merge feature packages + the merged reports submodules."""
    mermaid = _sole_mermaid_block(_FEATURES_DIAGRAM)
    tokens = _tokens(mermaid)

    packages = _live_feature_packages()
    reports_submodules = _live_reports_submodules()
    assert packages, "introspection found no feature packages — imports broken?"
    assert reports_submodules, "introspection found no reports submodules — imports broken?"

    missing = (packages | reports_submodules) - tokens
    assert not missing, (
        f"{_FEATURES_DIAGRAM.name} does not diagram live package(s)/submodule(s): "
        f"{sorted(missing)}. Regenerate the diagram (v0.1.55 FR7 regeneration law)."
    )
