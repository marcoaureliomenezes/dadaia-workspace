"""Panel API view — GET /api/panel-status (server registry, grouped by context).

/api/panel-status response:
  {
    "groups": [
      {
        "group_label": str,          # repo slug or "Outros"
        "context_name": str | null,  # human-readable context name, or null
        "rows": [
          {
            "port":       int,
            "project":    str,
            "url":        str,
            "status":     "active" | "stale",
            "pid":        int | null,
            "expires_at": str,       # ISO-8601 expiry timestamp
            "description": str | null
          }
        ]
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


def render_api_servers(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serialises list_servers_grouped() as JSON."""

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        groups = service.list_servers_grouped()
        payload = {
            "groups": [
                {
                    "group_label": g.group_label,
                    "context_name": g.context_name,
                    "rows": [
                        {
                            "port": r.port,
                            "project": r.project,
                            "url": r.url,
                            "status": str(r.status),
                            "pid": r.pid,
                            "expires_at": r.expires_at,
                            "description": r.description,
                        }
                        for r in g.rows
                    ],
                }
                for g in groups
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view
