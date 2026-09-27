"""Intent: CONTRACT — sa-specs-upgrade-writes-through-symlinks (0.5.0 WP-14, sa-specs-upgrade-writes-through-symlinks#B4).

No file write in ``features/migrate`` or ``features/specs`` happens outside
``core.atomic_write`` (the one symlink-refusing writer): no ``write_text``/``write_bytes``,
no ``open(..., "w"/"a"/"x")``, no ``os.replace``/``os.open``. AST scan of the source.
Size: SMALL.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_FEATURES = Path(__file__).resolve().parents[1].parent / "dadaia_workspace" / "features"


def _raw_writes(path: Path) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        name, owner = node.func.attr, node.func.value
        is_os = isinstance(owner, ast.Name) and owner.id == "os"
        if name in {"write_text", "write_bytes"} or (is_os and name in {"replace", "open"}):
            hits.append(f"{path.name}:{node.lineno}:{name}")
        elif name == "open" and any(
            isinstance(a, ast.Constant) and str(a.value)[:1] in {"w", "a", "x"} for a in node.args
        ):
            hits.append(f"{path.name}:{node.lineno}:open")
    return hits


def test_b4_every_specs_and_migrate_write_goes_through_atomic_write() -> None:
    files = sorted((_FEATURES / "migrate").glob("*.py")) + sorted(
        (_FEATURES / "specs").glob("*.py")
    )
    assert [hit for f in files for hit in _raw_writes(f)] == []
