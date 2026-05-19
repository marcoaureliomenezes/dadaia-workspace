"""Panel static assets package (CSS and JS slices).

Phase 1 re-export shim: combine all CSS slices and expose PANEL_CSS / PANEL_JS
for backward-compatible import from _assets.py. Each slice lives in its own
module so specialists can write into separate files in parallel without merge
conflicts (PLAN §4 ownership map).
"""

from dadaia_workspace.features.panel.views.assets.css.agents import AGENTS_CSS
from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS
from dadaia_workspace.features.panel.views.assets.css.workflows import WORKFLOWS_CSS

__all__ = [
    "TOKENS_CSS",
    "STRUCTURE_CSS",
    "AGENTS_CSS",
    "WORKFLOWS_CSS",
]
