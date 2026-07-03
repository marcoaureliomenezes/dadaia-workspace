"""Anti-erosion module-size ratchet (v0.1.55 FR1 / AC-1).

The 2,830-line ``features/specs/doctor.py`` god module and the 1,279-line
``features/panel/views/api.py`` module were the erosion this release decomposes. Once split,
nothing structurally prevents a future edit from re-growing a single module back toward a god
module — the layering law (import-linter) constrains *edges*, not *line counts*.

This contract pins per-module **line-count ceilings** as a ratchet:

* No ``features/specs/doctor*.py`` module exceeds **700 lines** (the FR1 coordinator + validator
  siblings + leaves).
* No ``features/panel/views/api*.py`` module exceeds **450 lines** (the FR2 per-domain view
  modules; ``api.py`` is deleted, so the monolith can never re-form).

Lowering a ceiling after a further split is welcome — lower the constant here in the same commit.
Raising one requires a same-commit justification (a module legitimately grew past the ratchet),
so the erosion only ever happens on purpose, never by accident.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPECS_DIR = _REPO_ROOT / "dadaia_workspace" / "features" / "specs"
_PANEL_VIEWS_DIR = _REPO_ROOT / "dadaia_workspace" / "features" / "panel" / "views"

# Recorded ceilings (ratchet). Lowering is welcome; raising needs same-commit justification.
_DOCTOR_CEILING = 700
_API_CEILING = 450


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_doctor_module_exceeds_ceiling() -> None:
    """Every features/specs/doctor*.py module stays under the 700-line ratchet (AC-1)."""
    modules = sorted(_SPECS_DIR.glob("doctor*.py"))
    assert modules, f"no doctor*.py modules found under {_SPECS_DIR}"
    offenders = {p.name: _line_count(p) for p in modules if _line_count(p) > _DOCTOR_CEILING}
    assert not offenders, (
        f"doctor module(s) exceed the {_DOCTOR_CEILING}-line ceiling: {offenders}. "
        "Split further and lower the ceiling, or justify the growth in the same commit "
        "(AC-1 anti-erosion ratchet)."
    )


def test_no_api_module_exceeds_ceiling() -> None:
    """Every features/panel/views/api*.py module stays under the 450-line ratchet (FR2 AC-1)."""
    modules = sorted(_PANEL_VIEWS_DIR.glob("api*.py"))
    assert modules, f"no api*.py modules found under {_PANEL_VIEWS_DIR}"
    # The monolithic api.py is DELETED by FR2 — its re-appearance is itself a regression.
    assert not any(p.name == "api.py" for p in modules), (
        "features/panel/views/api.py must stay deleted (FR2 per-domain decomposition; no facade)."
    )
    offenders = {p.name: _line_count(p) for p in modules if _line_count(p) > _API_CEILING}
    assert not offenders, (
        f"panel api module(s) exceed the {_API_CEILING}-line ceiling: {offenders}. "
        "Split further and lower the ceiling, or justify the growth in the same commit "
        "(AC-1 anti-erosion ratchet)."
    )
