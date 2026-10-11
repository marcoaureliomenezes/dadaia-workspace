"""The one loader of a packaged skill-script owner (ADR 0135, ADR 0246).

Each owner runs from its absolute path and is registered in ``sys.modules`` under its
import name before it executes, so a package caller and a sibling ``import _atomic``
inside a script share one module object and one set of exception classes. The skills'
``scripts/`` folders sit at the FRONT of ``sys.path`` for function-level sibling imports;
the absolute-path load plus the registration is what defeats a cwd shadow (CWE-427).
"""

from __future__ import annotations

import importlib.util
import sys
from functools import cache
from pathlib import Path
from types import ModuleType

__all__ = ["load_owner"]

_SKILLS = Path(__file__).resolve().parents[1] / "public" / "skills"


@cache
def load_owner(skill: str, module: str) -> ModuleType:
    """The packaged ``<skill>/scripts/<module>.py`` as ONE module; no bytecode lands beside it."""
    for name in (skill, "dd-bug-resolution"):
        folder = str(_SKILLS / name / "scripts")
        if folder not in sys.path:
            sys.path.insert(0, folder)
    if module in sys.modules:
        return sys.modules[module]
    path = _SKILLS / skill / "scripts" / f"{module}.py"
    spec = importlib.util.spec_from_file_location(module, path)
    assert spec is not None and spec.loader is not None
    owner = importlib.util.module_from_spec(spec)
    sys.modules[module] = owner
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(owner)
    except BaseException:
        del sys.modules[module]
        raise
    finally:
        sys.dont_write_bytecode = keep
    return owner
