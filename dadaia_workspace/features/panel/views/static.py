"""Static asset view — serves panel.css and panel.js from Python string constants.

R1 (asset packaging — decision locked):
  Assets are Python string constants imported from _assets.py. No filesystem reads,
  no importlib.resources, no pyproject.toml package-data. The dict lookup is the
  entire validation surface — path traversal is structurally impossible because
  only exact key names map to content.

Serving panel.css or panel.js via /static/<name> gives the browser a stable URL
for caching, separate from the per-page HTML render.
"""

from __future__ import annotations

from collections.abc import Callable

from dadaia_workspace.features.panel.views._assets import PANEL_CSS, PANEL_JS

_ASSETS: dict[str, tuple[str, str]] = {
    "panel.css": ("text/css; charset=utf-8", PANEL_CSS),
    "panel.js": ("application/javascript; charset=utf-8", PANEL_JS),
}


def render_static() -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves named static assets."""

    def _view(name: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        entry = _ASSETS.get(name)
        if entry is None:
            return (
                404,
                "text/plain; charset=utf-8",
                b"Static asset not found.",
            )
        content_type, content = entry
        return (200, content_type, content.encode("utf-8"))

    return _view
