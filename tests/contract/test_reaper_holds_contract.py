"""The reaper's holds die only at their TTL — text and source contracts.

Intent: CONTRACT — sa-reaper-destroys-its-own-hold-before-ttl#B6, #B8. Size: SMALL.
"""

from __future__ import annotations

import ast
from pathlib import Path

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_DELETERS = frozenset({"remove", "rmtree", "unlink", "rmdir"})


def test_the_cli_skill_never_claims_expired_only_spares_slop() -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B6."""
    text = (_PKG / "public" / "skills" / "dd-cli-library" / "SKILL.md").read_text(encoding="utf-8")
    assert "without touching slop" not in text
    assert "`--expired-only` narrows only the report" in text


def test_no_function_that_names_the_reaped_zone_deletes() -> None:
    """sa-reaper-destroys-its-own-hold-before-ttl#B8: a function that names the reaped
    zone never calls a deleter — holds are deleted only by the doctor's EXPIRED lane,
    which judges every TTL zone alike and never names ``reaped``."""
    offenders: list[str] = []
    for path in sorted(_PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            names_reaped = any(
                (isinstance(n, ast.Constant) and n.value == "reaped")
                or (isinstance(n, ast.Name) and n.id == "REAPED_ZONE")
                for n in ast.walk(fn)
            )
            deletes = any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute | ast.Name)
                and (n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id) in _DELETERS
                for n in ast.walk(fn)
            )
            if names_reaped and deletes:
                offenders.append(f"{path.relative_to(_PKG)}:{fn.name}")
    assert offenders == []
