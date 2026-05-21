"""Static asset view — serves panel CSS slices and JS files from views/assets/.

R3 (PR3-02 activation):
  Assets are keyed by filename (e.g. "tokens.css", "core.js") in _ASSETS, an
  in-memory dict built at import time from Python string constants (CSS) and
  filesystem reads (JS / SVG).

  Extension-to-MIME mapping is frozen per SPEC §6. Unknown extensions return 404.
  Path traversal detection (any "/" or ".." in the name) returns 400 before the
  dict lookup, as defence-in-depth per architect review note in SPEC §5.2.

  Cache-Control is set in the handler layer (handler.py) for the /static/ prefix.

T-P5-02: LOGO_RHINO_24 and LOGO_RHINO_16 module-level constants added here so
that index.py can import logo content from this module instead of _assets.py.
_assets.py will be deleted once all imports are migrated (Phase B).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS
from dadaia_workspace.features.panel.views.assets.css.projects import PROJECTS_CSS
from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS
from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

_ASSETS_DIR = Path(__file__).parent / "assets"
_JS_DIR = _ASSETS_DIR / "js"

# ---------------------------------------------------------------------------
# Logo constants — loaded once at import time for inline HTML embedding.
# T-P5-02: moved from _assets.py to this module. Import from here instead.
# ---------------------------------------------------------------------------
LOGO_RHINO_24: str = (_ASSETS_DIR / "logo-rhino-24.svg").read_text(encoding="utf-8")
LOGO_RHINO_16: str = (_ASSETS_DIR / "logo-rhino-16.svg").read_text(encoding="utf-8")

_MIME_BY_EXT: dict[str, str] = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml; charset=utf-8",
    ".map": "application/json; charset=utf-8",
}

_ASSETS: dict[str, tuple[str, bytes]] = {
    "tokens.css": ("text/css; charset=utf-8", TOKENS_CSS.encode("utf-8")),
    "structure.css": ("text/css; charset=utf-8", STRUCTURE_CSS.encode("utf-8")),
    "agents.css": ("text/css; charset=utf-8", AGENTS_CSS.encode("utf-8")),
    "projects.css": ("text/css; charset=utf-8", PROJECTS_CSS.encode("utf-8")),
    "workflows.css": ("text/css; charset=utf-8", WORKFLOWS_CSS.encode("utf-8")),
    "sessions.css": ("text/css; charset=utf-8", SESSIONS_CSS.encode("utf-8")),
    "core.js": (
        "application/javascript; charset=utf-8",
        (_JS_DIR / "core.js").read_bytes(),
    ),
    "themes.js": (
        "application/javascript; charset=utf-8",
        (_JS_DIR / "themes.js").read_bytes(),
    ),
    # runtime.js MUST be registered before agents.js, workflows.js, and
    # sessions.js (load-order invariant, PR5-D7).  window.Runtime must be
    # defined before any module calls Runtime.get() or subscribes to
    # dadaia:runtime-change.  The dict insertion order here mirrors the
    # <script> order enforced in index.py.
    "runtime.js": (
        "application/javascript; charset=utf-8",
        (_JS_DIR / "runtime.js").read_bytes(),
    ),
    "agents.js": (
        "application/javascript; charset=utf-8",
        (_JS_DIR / "agents.js").read_bytes(),
    ),
    "workflows.js": (
        "application/javascript; charset=utf-8",
        (_JS_DIR / "workflows.js").read_bytes(),
    ),
    "sessions.js": (
        "application/javascript; charset=utf-8",
        (_JS_DIR / "sessions.js").read_bytes(),
    ),
    "academy.js": (
        "application/javascript; charset=utf-8",
        (_JS_DIR / "academy.js").read_bytes(),
    ),
    "logo-rhino-24.svg": (
        "image/svg+xml; charset=utf-8",
        (_ASSETS_DIR / "logo-rhino-24.svg").read_bytes(),
    ),
    "logo-rhino-16.svg": (
        "image/svg+xml; charset=utf-8",
        (_ASSETS_DIR / "logo-rhino-16.svg").read_bytes(),
    ),
}


def _is_traversal(name: str) -> bool:
    return "/" in name or "\\" in name or ".." in name


def render_static() -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves named static assets per SPEC §6."""

    def _view(name: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        if not name:
            return (404, "text/plain; charset=utf-8", b"Static asset not found.")

        if _is_traversal(name):
            return (400, "text/plain; charset=utf-8", b"Bad request.")

        ext = Path(name).suffix
        if ext not in _MIME_BY_EXT:
            return (404, "text/plain; charset=utf-8", b"Static asset not found.")

        entry = _ASSETS.get(name)
        if entry is None:
            return (404, "text/plain; charset=utf-8", b"Static asset not found.")

        content_type, body = entry
        return (200, content_type, body)

    return _view
