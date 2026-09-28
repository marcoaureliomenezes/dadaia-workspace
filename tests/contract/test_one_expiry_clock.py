"""One expiry clock: the zone registry's TTL, applied by the one zone walk.

Intent: CONTRACT — sa-expiry-has-two-clocks#45.3. Size: SMALL (AST over the package).
"""

from __future__ import annotations

import ast
from pathlib import Path

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"
#: SESSION_GC_TTL* is the session record's own documented clock (the zone row);
#: RECONCILER_THROTTLE_TTL_SECONDS is a throttle window, not an expiry.
_ALLOWED = {"SESSION_GC_TTL_SECONDS", "SESSION_GC_TTL_FIELD", "RECONCILER_THROTTLE_TTL_SECONDS"}


def test_no_ttl_constant_outside_the_zone_registry_and_no_unlink_in_markers() -> None:
    """sa-expiry-has-two-clocks#45.3."""
    found = []
    for path in sorted(_PKG.rglob("*.py")):
        if "public" in path.relative_to(_PKG).parts or path.name == "workspace_layout.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else ([node.target] if isinstance(node, ast.AnnAssign) else [])
            )
            for target in targets:
                name = target.id if isinstance(target, ast.Name) else ""
                if "_TTL" in name and name not in _ALLOWED:
                    found.append(f"{path.relative_to(_PKG)}:{name}")
    assert found == []
    markers = (_PKG / "features" / "spec_context" / "markers.py").read_text(encoding="utf-8")
    assert "unlink" not in markers and "sweep.remove" not in markers
