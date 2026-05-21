"""Static frontend assets for the Dadaia Workspace Panel — logo path constants.

T-P5-01: PANEL_CSS, PANEL_JS, and PALETTE have been removed from this module.
CSS slices live in views/assets/css/*.py and are assembled in static.py.
JS files are served directly from views/assets/js/ via static.py.

LOGO_RHINO_24 / LOGO_RHINO_16 — inline SVG for the rhino logomark, loaded at
import time from assets/. currentColor only; zero hardcoded hex.
(spec: dadaia-workspace-brand-identity-v1 T-BR-03/04/05)

Phase B will migrate these constants into static.py (T-P5-02).
"""

from pathlib import Path

_ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_RHINO_24: str = (_ASSETS_DIR / "logo-rhino-24.svg").read_text(encoding="utf-8")
LOGO_RHINO_16: str = (_ASSETS_DIR / "logo-rhino-16.svg").read_text(encoding="utf-8")
