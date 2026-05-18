"""Static frontend assets for the Dadaia Workspace Panel — thin re-export shim.

Phase 1 (PR3-01): CSS slices have been moved to views/assets/css/*.py.
PANEL_CSS is now assembled from those slices. PANEL_JS is read from
views/assets/js/core.js (SE-owned; also contains FE-owned Agents/Workflows
blocks as temporary placeholders during Phase 1 transition — FE will replace
them via agents.js / workflows.js in Phase 4/5).

LOGO_RHINO_24 / LOGO_RHINO_16 — inline SVG for the rhino logomark, loaded at
import time from assets/. currentColor only; zero hardcoded hex.
(spec: dadaia-workspace-brand-identity-v1 T-BR-03/04/05)
"""

from pathlib import Path

from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS
from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

_ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_RHINO_24: str = (_ASSETS_DIR / "logo-rhino-24.svg").read_text(encoding="utf-8")
LOGO_RHINO_16: str = (_ASSETS_DIR / "logo-rhino-16.svg").read_text(encoding="utf-8")

PALETTE: dict[str, str] = {
    "accent": "#9cddc8",
    "accent_secondary": "#bfd8ad",
    "warning_bg": "#ddd9ab",
    "alert": "#f7af63",
    "cost": "#633d2e",
}
"""Canonical brand palette (spec: dadaia-workspace-brand-identity-v1 SPEC.md)."""

# CSS assembled from slice modules (no inline CSS string literals remain here).
PANEL_CSS: str = TOKENS_CSS + STRUCTURE_CSS + AGENTS_CSS + WORKFLOWS_CSS

# JS read from core.js (SE-owned, contains full IIFE including FE-owned blocks
# as Phase 1 placeholders until FE fills agents.js / workflows.js).
_JS_DIR = Path(__file__).parent / "assets" / "js"
PANEL_JS: str = (_JS_DIR / "core.js").read_text(encoding="utf-8")
