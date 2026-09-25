"""Intent: CONTRACT — P-18 module line-count ceiling (doctor*)

Anti-erosion module-size ratchet (v0.1.55 FR1 / AC-1): the 2,830-line
``features/specs/doctor.py`` god module was split; the layering law constrains *edges*,
not *line counts*, so this pins no ``features/specs/doctor*.py`` module above the ceiling.

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

# Recorded ceilings (ratchet). Lowering is welcome; raising needs same-commit justification.
_DOCTOR_CEILING = 699


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


@pytest.mark.parametrize(
    ("glob", "ceiling", "directory"),
    [
        pytest.param("doctor*.py", _DOCTOR_CEILING, _SPECS_DIR, id="doctor"),
    ],
)
def test_no_module_exceeds_ceiling(glob: str, ceiling: int, directory: Path) -> None:
    """Every module matching *glob* under *directory* stays under its line-count
    ratchet (AC-1)."""
    modules = sorted(directory.glob(glob))
    assert modules, f"no {glob} modules found under {directory}"
    offenders = {p.name: _line_count(p) for p in modules if _line_count(p) > ceiling}
    assert not offenders, (
        f"module(s) matching {glob} exceed the {ceiling}-line ceiling: {offenders}. "
        "Split further and lower the ceiling, or justify the growth in the same commit "
        "(AC-1 anti-erosion ratchet)."
    )
