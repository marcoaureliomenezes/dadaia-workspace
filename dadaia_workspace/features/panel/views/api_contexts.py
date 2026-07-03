"""Panel API view — GET /api/contexts (active Spec Context Projects).

/api/contexts response:
  {
    "contexts": [
      {
        "slug":          str,
        "name":          str,
        "repo_path":     str,
        "branch":        str | null,
        "status":        "alive"
      }
    ]
  }

Security (R3-A): json.dumps() handles JSON-string escaping; no HTML escaping needed here.
Content-Type is always set to application/json; charset=utf-8.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from dadaia_workspace.features.panel.service import PanelService


def render_api_contexts(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serialises list_active_contexts() as JSON."""

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        contexts = service.list_active_contexts()
        payload = {
            "contexts": [
                {
                    "slug": c.slug,
                    "name": c.name,
                    "repo_path": str(c.repo_path),
                    "branch": c.branch,
                    "status": c.status,
                }
                for c in contexts
            ]
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view
