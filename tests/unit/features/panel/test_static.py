"""Unit tests for the /static/<name> route.

Covers static asset serving contracts:
  - .css  → 200, Content-Type: text/css; charset=utf-8
  - .js   → 200, Content-Type: application/javascript; charset=utf-8
  - .svg  → 200, Content-Type: image/svg+xml; charset=utf-8
  - .map  → 200, Content-Type: application/json; charset=utf-8
  - unknown extension (.png, .ico, empty) → 404
  - path traversal attempt → 400
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.panel.views.static import render_static


def _view(name: str) -> tuple[int, str, bytes]:
    view = render_static()
    return view(name=name)


# ---------------------------------------------------------------------------
# CSS slice — tokens.css
# ---------------------------------------------------------------------------


def test_tokens_css_status_200() -> None:
    status, _, _ = _view("tokens.css")
    assert status == 200


def test_tokens_css_content_type() -> None:
    _, ct, _ = _view("tokens.css")
    assert ct == "text/css; charset=utf-8"


def test_tokens_css_body_is_nonempty_bytes() -> None:
    _, _, body = _view("tokens.css")
    assert isinstance(body, bytes)
    assert len(body) > 0


# ---------------------------------------------------------------------------
# CSS slice — structure.css
# ---------------------------------------------------------------------------


def test_structure_css_content_type() -> None:
    status, ct, _ = _view("structure.css")
    assert status == 200
    assert ct == "text/css; charset=utf-8"


def test_agents_css_content_type() -> None:
    status, ct, _ = _view("agents.css")
    assert status == 200
    assert ct == "text/css; charset=utf-8"


def test_workflows_css_content_type() -> None:
    status, ct, _ = _view("workflows.css")
    assert status == 200
    assert ct == "text/css; charset=utf-8"


# ---------------------------------------------------------------------------
# JS files
# ---------------------------------------------------------------------------


def test_core_js_content_type() -> None:
    status, ct, _ = _view("core.js")
    assert status == 200
    assert ct == "application/javascript; charset=utf-8"


def test_themes_js_content_type() -> None:
    status, ct, _ = _view("themes.js")
    assert status == 200
    assert ct == "application/javascript; charset=utf-8"


def test_agents_js_content_type() -> None:
    status, ct, _ = _view("agents.js")
    assert status == 200
    assert ct == "application/javascript; charset=utf-8"


def test_workflows_js_content_type() -> None:
    status, ct, _ = _view("workflows.js")
    assert status == 200
    assert ct == "application/javascript; charset=utf-8"


# ---------------------------------------------------------------------------
# SVG assets
# ---------------------------------------------------------------------------


def test_svg_asset_content_type() -> None:
    status, ct, _ = _view("logo-rhino-24.svg")
    assert status == 200
    assert ct == "image/svg+xml; charset=utf-8"


# ---------------------------------------------------------------------------
# Unknown extension → 404
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["missing.png", "missing.ico", "missing.woff", "missing.txt"])
def test_unknown_extension_returns_404(name: str) -> None:
    status, _, _ = _view(name)
    assert status == 404


def test_unknown_name_with_no_extension_returns_404() -> None:
    status, _, _ = _view("noextension")
    assert status == 404


def test_empty_name_returns_404() -> None:
    status, _, _ = _view("")
    assert status == 404


# ---------------------------------------------------------------------------
# Known extension but file not registered → 404
# ---------------------------------------------------------------------------


def test_nonexistent_css_file_returns_404() -> None:
    status, _, _ = _view("nonexistent.css")
    assert status == 404


def test_nonexistent_js_file_returns_404() -> None:
    status, _, _ = _view("nonexistent.js")
    assert status == 404


# ---------------------------------------------------------------------------
# Path traversal → 400
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "../etc/passwd",
        "../../etc/passwd",
        "../tokens.css",
        "subdir/tokens.css",
        "tokens.css/../../etc/passwd",
    ],
)
def test_path_traversal_returns_400(name: str) -> None:
    status, _, _ = _view(name)
    assert status == 400


# ---------------------------------------------------------------------------
# Body is bytes for all 200 responses
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["tokens.css", "structure.css", "agents.css", "workflows.css", "core.js"],
)
def test_body_is_bytes(name: str) -> None:
    _, _, body = _view(name)
    assert isinstance(body, bytes)


# ---------------------------------------------------------------------------
# .map MIME type — Content-Type: application/json; charset=utf-8
# ---------------------------------------------------------------------------


def test_map_extension_returns_404_when_no_map_file_registered() -> None:
    """A .map filename with an unknown name returns 404 (known ext, unknown file)."""
    status, _, _ = _view("nonexistent.map")
    assert status == 404


def test_map_extension_content_type_in_mime_map() -> None:
    """The .map extension is registered in the MIME map (application/json)."""
    from dadaia_workspace.features.panel.views.static import _MIME_BY_EXT

    assert ".map" in _MIME_BY_EXT
    assert _MIME_BY_EXT[".map"] == "application/json; charset=utf-8"


# ---------------------------------------------------------------------------
# logo-rhino-16.svg — second SVG asset
# ---------------------------------------------------------------------------


def test_logo_rhino_16_content_type() -> None:
    """logo-rhino-16.svg returns 200 with image/svg+xml content type."""
    status, ct, _ = _view("logo-rhino-16.svg")
    assert status == 200
    assert ct == "image/svg+xml; charset=utf-8"


def test_logo_rhino_16_body_is_nonempty_bytes() -> None:
    """logo-rhino-16.svg body is non-empty bytes."""
    _, _, body = _view("logo-rhino-16.svg")
    assert isinstance(body, bytes)
    assert len(body) > 0


# ---------------------------------------------------------------------------
# Backslash traversal → 400
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "..\\etc\\passwd",
        "tokens.css\\..\\..\\etc\\passwd",
        "subdir\\tokens.css",
    ],
)
def test_backslash_traversal_returns_400(name: str) -> None:
    """Backslash path separators are treated as traversal attempts → 400."""
    status, _, _ = _view(name)
    assert status == 400


# ---------------------------------------------------------------------------
# MIME map coverage — verify all registered extensions
# ---------------------------------------------------------------------------


def test_css_mime_in_map() -> None:
    """The .css extension is registered with correct MIME type."""
    from dadaia_workspace.features.panel.views.static import _MIME_BY_EXT

    assert ".css" in _MIME_BY_EXT
    assert _MIME_BY_EXT[".css"] == "text/css; charset=utf-8"


def test_js_mime_in_map() -> None:
    """The .js extension is registered with correct MIME type."""
    from dadaia_workspace.features.panel.views.static import _MIME_BY_EXT

    assert ".js" in _MIME_BY_EXT
    assert _MIME_BY_EXT[".js"] == "application/javascript; charset=utf-8"


def test_svg_mime_in_map() -> None:
    """The .svg extension is registered with correct MIME type."""
    from dadaia_workspace.features.panel.views.static import _MIME_BY_EXT

    assert ".svg" in _MIME_BY_EXT
    assert _MIME_BY_EXT[".svg"] == "image/svg+xml; charset=utf-8"


def test_mime_map_has_exactly_four_entries() -> None:
    """The MIME map contains exactly four extension entries (.css, .js, .svg, .map)."""
    from dadaia_workspace.features.panel.views.static import _MIME_BY_EXT

    assert set(_MIME_BY_EXT.keys()) == {".css", ".js", ".svg", ".map"}
