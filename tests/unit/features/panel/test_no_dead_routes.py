"""A registered route with no view answers 500; an absent route answers 404.

The demolition removed the workflow-catalog views but left their entries in the panel's
route table and in the handler's own advertised path list. Route compilation registers a
name it cannot resolve with a ``None`` callable, and dispatch then does
``views[route_name]`` — a KeyError, swallowed by the generic handler into
``500 internal server error``. A path that does not exist must 404
(bug panel-dead-workflow-routes-500-after-demolition).

This is a ratchet over the whole table, not a list of the four names that happened to
rot: any future route whose view is deleted fails here rather than in a browser. It reads
the mapping's keys statically, because building it for real needs an initialized
workspace — and the question here is which names exist, not what they return.
"""

from __future__ import annotations

import ast
from pathlib import Path

from dadaia_workspace.features.panel.handler import _ROUTE_TABLE

_CONTAINER = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "container.py"

# Names dispatch resolves through an explicit inline branch rather than the mapping, so
# their absence from it is by design.
_INLINE_DISPATCHED = {"api_telemetry", "api_telemetry_flush", "api_agent_sessions"}


def _view_names() -> set[str]:
    """Keys of the dict literal ``build_panel_views`` returns."""
    tree = ast.parse(_CONTAINER.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_panel_views":
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
                    return {
                        k.value
                        for k in stmt.value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                    }
    raise AssertionError("build_panel_views does not return a dict literal any more")


def test_every_registered_route_resolves_to_a_view() -> None:
    registered = {name for _, name, _ in _ROUTE_TABLE}

    orphans = sorted(registered - _view_names() - _INLINE_DISPATCHED)

    assert orphans == [], (
        "these routes are registered but no view implements them, so requesting one "
        f"answers 500 instead of 404: {orphans}"
    )
