"""Backward-compatibility shim — do not import from this module in new code.

T-P5-01: PANEL_CSS, PANEL_JS, PALETTE removed.
T-P5-02: LOGO_RHINO_24 and LOGO_RHINO_16 moved to static.py.

This module is retained only to avoid breaking any external code that still
imports the logo constants by their old path. It will be deleted once all
import sites are migrated. Import from static.py instead:

    from dadaia_workspace.features.panel.views.static import LOGO_RHINO_24
"""

from dadaia_workspace.features.panel.views.static import LOGO_RHINO_16, LOGO_RHINO_24

__all__ = ["LOGO_RHINO_24", "LOGO_RHINO_16"]
