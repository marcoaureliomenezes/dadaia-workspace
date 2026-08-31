"""F001 (20260830-design-bug-surface-audit): no orphaned factories.

The container centralizes wiring, so a consumer can die without its factory dying —
build_process_ancestry was the THIRD occurrence of the class (after the dead
token-estimate normalizer and the orphaned catalog-regenerator factory). This
contract pins: every top-level def/class in container.py is referenced by PRODUCTION
code outside the container, or by another container definition that is. A
test-only consumer does not count — that is exactly how an orphan hides.

Intent: contract; size: unit.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO = Path(__file__).resolve().parents[2]
_PKG = _REPO / "dadaia_workspace"


def _name_used_in(text: str, name: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text) is not None


def test_every_container_def_has_a_production_consumer() -> None:
    container_src = (_PKG / "container.py").read_text(encoding="utf-8")
    defs = re.findall(r"^(?:def|class) ([A-Za-z_][A-Za-z0-9_]*)", container_src, re.M)
    assert defs, "container.py defines nothing? the scan is broken"

    prod_texts = [
        p.read_text(encoding="utf-8")
        for p in sorted(_PKG.rglob("*.py"))
        if p.name != "container.py" and "__pycache__" not in p.parts
    ]

    externally_used = {n for n in defs if any(_name_used_in(t, n) for t in prod_texts)}
    orphans: list[str] = []
    for name in defs:
        if name in externally_used:
            continue
        # Internal reference from ANOTHER container definition (helper / return type)
        # counts only when some externally-used definition reaches it.
        body_without_def = re.sub(
            rf"^(?:def|class) {re.escape(name)}\b", "", container_src, flags=re.M
        )
        internally_referenced = _name_used_in(body_without_def, name)
        if not internally_referenced:
            orphans.append(name)
    assert orphans == [], (
        f"container.py definitions with no production consumer (orphaned factories): {orphans}"
    )
