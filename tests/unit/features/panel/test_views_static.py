"""Unit tests for views/static.py — T-3.6 (updated for PR3-02 activation).

Covers:
  - tokens.css served with correct content-type (replaces panel.css)
  - core.js served with correct content-type (replaces panel.js)
  - Returned bytes are non-empty
  - Unknown name returns 404
  - Traversal-like names ("../etc/passwd") return 400 (path traversal guard, PR3-02)
"""

from dadaia_workspace.features.panel.views.static import render_static


def _view(name: str) -> tuple[int, str, bytes]:
    view = render_static()
    return view(name=name)


def test_static_css_status_and_content_type() -> None:
    """tokens.css returns 200 with text/css; charset=utf-8."""
    status, ct, _ = _view("tokens.css")
    assert status == 200
    assert ct == "text/css; charset=utf-8"


def test_static_css_body_is_nonempty() -> None:
    """tokens.css body must be non-empty bytes."""
    _, _, body = _view("tokens.css")
    assert isinstance(body, bytes)
    assert len(body) > 0


def test_static_js_status_and_content_type() -> None:
    """core.js returns 200 with application/javascript; charset=utf-8."""
    status, ct, _ = _view("core.js")
    assert status == 200
    assert ct == "application/javascript; charset=utf-8"


def test_static_js_body_is_nonempty() -> None:
    """core.js body must be non-empty bytes."""
    _, _, body = _view("core.js")
    assert isinstance(body, bytes)
    assert len(body) > 0


def test_static_unknown_name_returns_404() -> None:
    """Unknown asset name must return 404."""
    status, _, _ = _view("favicon.ico")
    assert status == 404


def test_static_traversal_returns_400() -> None:
    """Traversal-like names must return 400 (path traversal guard per SPEC §5.2)."""
    status, _, _ = _view("../etc/passwd")
    assert status == 400


def test_static_empty_name_returns_404() -> None:
    """Empty name must return 404."""
    status, _, _ = _view("")
    assert status == 404


def test_static_css_is_nonempty() -> None:
    """CSS slice must be non-empty."""
    _, _, body = _view("tokens.css")
    assert len(body) > 0


def test_static_js_is_nonempty() -> None:
    """JS file must be non-empty."""
    _, _, body = _view("core.js")
    assert len(body) > 0


def test_static_returns_bytes() -> None:
    """View must return bytes, not str."""
    _, _, body = _view("tokens.css")
    assert isinstance(body, bytes)


# ---------------------------------------------------------------------------
# PR5-D7 — runtime.js registered in _ASSETS
# ---------------------------------------------------------------------------


def test_static_runtime_js_status_and_content_type() -> None:
    """PR5-D7: runtime.js must return 200 with application/javascript; charset=utf-8."""
    status, ct, _ = _view("runtime.js")
    assert status == 200
    assert ct == "application/javascript; charset=utf-8"


def test_static_runtime_js_body_is_nonempty() -> None:
    """PR5-D7: runtime.js body must be non-empty bytes."""
    _, _, body = _view("runtime.js")
    assert isinstance(body, bytes)
    assert len(body) > 0


def test_static_runtime_js_load_order() -> None:
    """PR5-D7: load-order invariant — runtime.js must appear in _ASSETS before agents.js.

    The _ASSETS dict insertion order mirrors the intended static-serving
    registration. runtime.js must be registered before agents.js, workflows.js,
    and sessions.js because window.Runtime must be defined before those modules
    subscribe to dadaia:runtime-change or call Runtime.get().
    """
    from dadaia_workspace.features.panel.views.static import _ASSETS

    keys = list(_ASSETS.keys())
    idx_runtime = keys.index("runtime.js")
    for dependent in ("agents.js", "workflows.js", "sessions.js"):
        assert idx_runtime < keys.index(dependent), (
            f"runtime.js ({idx_runtime}) must precede {dependent} ({keys.index(dependent)}) in _ASSETS"
        )
