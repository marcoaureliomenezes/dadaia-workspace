"""Intent: CONTRACT — sa-context-dead-removes-repos-outside-the-reaper (0.5.0 WP-03 #C8).

No raw ``rmtree`` may target ``repos/<slug>``: a repo leaves the working tree only
through ``sweep.hold``. The one exception is ``create``'s rollback of the clones the same
call just made. The spec_context feature (the only owner of ``repos/``) is scanned by
AST: its rmtree call sites are exactly the listed ones.
Size: SMALL (AST over source, no I/O beyond reading it).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_FEATURE = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "features" / "spec_context"

#: ``file:function`` -> why that rmtree may run.
_ALLOWED = {
    "service.py:create": "rollback of the clones this same call created",
    "sweep.py:remove": "the TTL primitive's own delete (tmp/reaped zones, never repos/)",
}


def _rmtree_sites() -> set[str]:
    sites: set[str] = set()
    for path in sorted(_FEATURE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for call in ast.walk(fn):
                if isinstance(call, ast.Call):
                    name = getattr(call.func, "attr", getattr(call.func, "id", ""))
                    if name == "rmtree" and fn.name != "rmtree":
                        sites.add(f"{path.name}:{fn.name}")
    return sites


def test_c8_no_rmtree_targets_a_repo_outside_the_create_rollback() -> None:
    assert _rmtree_sites() == set(_ALLOWED)
