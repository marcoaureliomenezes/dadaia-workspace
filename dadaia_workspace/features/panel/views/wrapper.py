"""Memory wrapper view — thin chrome wrapper around a memory HTML iframe.

Renders a 40px back-bar (fixed) + full-viewport iframe pointing at
``/memory/<slug>/<path>``.  The memory HTML body is NEVER mutated (NFR-2).
The back-bar lives in this wrapper's DOM, not in the iframe's body.

Security (R3-A / OWASP A03): slug and path are passed through html.escape()
before insertion into the wrapper HTML.
"""

from __future__ import annotations

import html
from collections.abc import Callable
from pathlib import Path


def render_memory_wrapper(
    workspace_root: Path,  # noqa: ARG001  # reserved for future use
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that renders the memory wrapper page."""

    def _view(slug: str = "", path: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        safe_slug = html.escape(slug)
        safe_path = html.escape(path)
        iframe_src = f"/memory/{safe_slug}/{safe_path}"
        title = f"Memory — {safe_slug} · {safe_path}"

        body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <script>(function(){{var t=localStorage.getItem('dadaia-panel-theme');if(t&&(t==='mint'||t==='sage'||t==='warm')){{document.documentElement.dataset.theme=t;}}}})();</script>
  <link rel="stylesheet" href="/static/tokens.css">
  <style>
    :root {{
      --topbar-h: 40px;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ height: 100%; overflow: hidden; }}
    body {{ font-family: var(--font-stack); background: var(--color-bg);
            color: var(--color-heading); display: flex; flex-direction: column; }}
    .back-bar {{
      height: var(--topbar-h); background: var(--color-surface);
      border-bottom: 1px solid var(--color-border-strong);
      display: flex; align-items: center; padding: 0 1rem; gap: 1rem;
      flex-shrink: 0; z-index: 200;
    }}
    .back-link {{
      display: inline-flex; align-items: center; gap: 0.4rem;
      font-size: 0.88rem; font-weight: 600; color: var(--color-accent-dark);
      text-decoration: none; padding: 0.25rem 0.5rem; border-radius: 4px;
      border: 1px solid var(--color-border); background: var(--color-surface);
    }}
    .back-link:hover {{ background: var(--color-code-bg); border-color: var(--color-accent); }}
    .back-link:focus-visible {{ outline: 2px solid var(--color-accent); outline-offset: 2px; }}
    .breadcrumb {{ font-size: 0.83rem; color: var(--color-muted); }}
    .breadcrumb strong {{ color: var(--color-heading); }}
    .memory-frame {{ flex: 1; width: 100%; border: none; display: block; }}
  </style>
</head>
<body>
  <div class="back-bar" role="navigation" aria-label="Memory navigation">
    <a class="back-link" href="/" aria-label="Back to Dadaia Workspace Panel">
      &#8592; Voltar ao Painel
    </a>
    <div class="breadcrumb">
      <strong>{safe_slug}</strong> &rsaquo; {safe_path}
    </div>
  </div>
  <iframe
    class="memory-frame"
    src="{iframe_src}"
    title="{title}"
    sandbox="allow-scripts allow-same-origin"
    loading="eager"
  ></iframe>
</body>
</html>"""
        return (200, "text/html; charset=utf-8", body.encode("utf-8"))

    return _view
