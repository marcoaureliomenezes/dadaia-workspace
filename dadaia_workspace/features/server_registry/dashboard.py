"""DEPRECATED — removed in a future release. New code in features/panel/. See specs/releases/dadaia-workspace-panel-v1/."""

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path


def render_html(states_dir: Path) -> str:
    """Read server_registry.json and return a full HTML page."""
    registry_path = states_dir / "server_registry.json"
    entries: list[dict] = []  # type: ignore[type-arg]
    if registry_path.exists():
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            entries = data.get("entries", [])
        except (json.JSONDecodeError, OSError):
            entries = []

    if entries:
        rows = "\n".join(
            f"""
            <tr>
              <td><strong>{e.get("project", "—")}</strong></td>
              <td><a href="{e.get("url", "#")}" target="_blank">{e.get("url", "—")}</a></td>
              <td>{"● running" if e.get("status") == "active" else "○ stale"}</td>
              <td>{e.get("description") or "—"}</td>
              <td>{e.get("reserved_at", "—")[:19].replace("T", " ")}</td>
            </tr>"""
            for e in entries
        )
        body = f"""
        <table>
          <thead>
            <tr>
              <th>Project</th><th>URL</th><th>Status</th>
              <th>Description</th><th>Since</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""
    else:
        body = "<p class='empty'>No servers registered.</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="5">
  <title>dadaia server registry</title>
  <style>
    body {{ font-family: monospace; padding: 2rem; background: #111; color: #eee; }}
    h1 {{ color: #7ec8e3; margin-bottom: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ text-align: left; padding: 0.5rem 1rem; border-bottom: 1px solid #333; }}
    th {{ color: #aaa; font-weight: normal; text-transform: uppercase; font-size: 0.8rem; }}
    a {{ color: #7ec8e3; }}
    .empty {{ color: #666; }}
  </style>
</head>
<body>
  <h1>dadaia · server registry</h1>
  {body}
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    states_dir: Path  # set as class attribute before serving

    def do_GET(self) -> None:
        html = render_html(self.states_dir)
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # suppress per-request logs
