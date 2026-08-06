"""Every asset the page requests must be served.

Deleting ``workflow-policy.css`` while the page still ``<link>``-ed it turned every
console-error and 4xx e2e guard red — a whole Playwright run to learn something a string
comparison could have said in milliseconds. The same shape as the dead ROUTES: an entry
that outlives the thing it points at (bug panel-dead-workflow-routes-500-after-demolition).

Both directions matter, so both are asserted: a request with no asset 404s in the
browser, and an asset nobody requests is dead weight in the served set.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.features.panel.views.static import _ASSETS

_VIEWS = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "features" / "panel" / "views"


def _requested() -> set[str]:
    """Every /static/<name> any rendered view asks for — index and sub-views alike.

    Scanning only index.py would call a stylesheet the memory or reports document view
    links "orphaned", so the scan follows the whole view tree. static.py is excluded: it
    is the server side of the question, not a request.
    """
    asked: set[str] = set()
    for module in sorted(_VIEWS.rglob("*.py")):
        if module.name == "static.py":
            continue
        asked |= set(re.findall(r"/static/([A-Za-z0-9._-]+)", module.read_text(encoding="utf-8")))
    for asset in sorted((_VIEWS / "assets" / "js").glob("*.js")):
        asked |= set(re.findall(r"/static/([A-Za-z0-9._-]+)", asset.read_text(encoding="utf-8")))
    return asked


def test_every_requested_asset_is_served() -> None:
    missing = sorted(_requested() - set(_ASSETS))

    assert missing == [], (
        f"these are requested but not served, so each is a 404 in the browser: {missing}"
    )


# Inlined into the markup as a Python constant rather than fetched by URL, so they are
# legitimately served without any /static/ reference. logo-rhino-16 and -24 have no
# reference of EITHER kind — pre-existing dead weight, not demolition rot, tracked in
# specs/backlog/20260806-panel-unused-logo-assets.md rather than deleted in a release
# that is about something else.
_INLINED_OR_EMBEDDED = {"logo-rhino-16.svg", "logo-rhino-24.svg", "logo-rhino-36.svg"}


def test_no_asset_is_served_that_nothing_requests() -> None:
    orphans = sorted(set(_ASSETS) - _requested() - _INLINED_OR_EMBEDDED)

    assert orphans == [], (
        "these assets are served but nothing asks for them — dead weight left behind by a "
        f"removed surface: {orphans}"
    )
