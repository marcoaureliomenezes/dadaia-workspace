"""Panel static assets package (CSS and JS slices).

Combines all CSS slices and exposes PANEL_CSS / PANEL_JS. Each slice lives in its own
module so specialists can write into separate files in parallel without merge conflicts
(PLAN §4 ownership map). (The legacy ``_assets.py`` re-export shim was removed in v0.1.53.)
"""

from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS

__all__ = [
    "TOKENS_CSS",
    "STRUCTURE_CSS",
]
