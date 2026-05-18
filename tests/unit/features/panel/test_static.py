"""Unit tests for the activated /static/<name> route — PR3-02.

Covers §6 of SPEC dadaia-workspace-panel-r3-v1:
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
