"""Panel API view — GET /health (public liveness probe, no auth, agent-friendly)."""

from __future__ import annotations

import json
from collections.abc import Callable


def render_health() -> Callable[..., tuple[int, str, bytes]]:
    """Return a view callable for GET /health — public, no auth, agent-friendly."""
    import importlib.metadata

    try:
        version = importlib.metadata.version("dadaia-workspace")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"

    body = json.dumps({"status": "ok", "version": version}).encode()

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        return (200, "application/json", body)

    return _view
