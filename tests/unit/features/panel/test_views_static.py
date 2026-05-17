"""Unit tests for views/static.py — T-3.6.

Covers:
  - panel.css served with correct content-type
  - panel.js served with correct content-type
  - Returned bytes equal PANEL_CSS / PANEL_JS encoded as UTF-8
  - Unknown name returns 404
  - Traversal-like names ("../etc/passwd") return 404 (impossible by dict lookup)
"""

from dadaia_workspace.features.panel.views._assets import PANEL_CSS, PANEL_JS
from dadaia_workspace.features.panel.views.static import render_static


def _view(name: str) -> tuple[int, str, bytes]:
    view = render_static()
    return view(name=name)


def test_static_css_status_and_content_type() -> None:
    """panel.css returns 200 with text/css; charset=utf-8."""
    status, ct, _ = _view("panel.css")
    assert status == 200
    assert ct == "text/css; charset=utf-8"


def test_static_css_body_equals_constant() -> None:
    """panel.css body must equal PANEL_CSS.encode('utf-8')."""
    _, _, body = _view("panel.css")
    assert body == PANEL_CSS.encode("utf-8")


def test_static_js_status_and_content_type() -> None:
    """panel.js returns 200 with application/javascript; charset=utf-8."""
    status, ct, _ = _view("panel.js")
    assert status == 200
    assert ct == "application/javascript; charset=utf-8"


def test_static_js_body_equals_constant() -> None:
    """panel.js body must equal PANEL_JS.encode('utf-8')."""
    _, _, body = _view("panel.js")
    assert body == PANEL_JS.encode("utf-8")


def test_static_unknown_name_returns_404() -> None:
    """Unknown asset name must return 404."""
    status, _, _ = _view("favicon.ico")
    assert status == 404


def test_static_traversal_returns_404() -> None:
    """Traversal-like names must return 404 (dict lookup, no filesystem access)."""
    status, _, _ = _view("../etc/passwd")
    assert status == 404


def test_static_empty_name_returns_404() -> None:
    """Empty name must return 404."""
    status, _, _ = _view("")
    assert status == 404


def test_static_css_is_nonempty() -> None:
    """PANEL_CSS constant must be non-empty."""
    assert len(PANEL_CSS.strip()) > 0


def test_static_js_is_nonempty() -> None:
    """PANEL_JS constant must be non-empty."""
    assert len(PANEL_JS.strip()) > 0


def test_static_returns_bytes() -> None:
    """View must return bytes, not str."""
    _, _, body = _view("panel.css")
    assert isinstance(body, bytes)
