"""Panel API views — JSON endpoints for /api/servers and /api/contexts.

JSON shapes (stable contract — if changed, panel.js must be updated in lockstep):

/api/servers response:
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

/api/contexts response:
  {
    "contexts": [
      {
        "slug":          str,
        "name":          str,
        "repo_path":     str,
        "branch":        str | null,
        "is_primary":    bool
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
            ]
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


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
                    "is_primary": c.is_primary,
                }
                for c in contexts
            ]
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view
