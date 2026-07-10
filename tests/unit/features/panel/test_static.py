"""Unit tests for the /static/<name> route (consolidates test_views_static.py).

Three survivors:
  1. Asset serve param: css/js/svg/map x status+MIME+nonempty, incl. runtime.js
     and the two logo SVGs.
  2. 404/400 param: unknown ext, unknown file, empty, no-ext, agentic-tab assets
     unregistered, traversal (`../` + backslash) -> 400.
  3. runtime.js-before-dependents load order (`_ASSETS` ordering — real init-
     order bug).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.panel.views.static import _MIME_BY_EXT, render_static

pytestmark = pytest.mark.unit


def _view(name: str) -> tuple[int, str, bytes]:
    view = render_static()
    return view(name=name)


# ---------------------------------------------------------------------------
# 1. Asset serve param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected_ct"),
    [
        pytest.param("tokens.css", "text/css; charset=utf-8", id="tokens-css"),
        pytest.param("structure.css", "text/css; charset=utf-8", id="structure-css"),
        pytest.param("workflows.css", "text/css; charset=utf-8", id="workflows-css"),
        pytest.param("core.js", "application/javascript; charset=utf-8", id="core-js"),
        pytest.param("themes.js", "application/javascript; charset=utf-8", id="themes-js"),
        pytest.param(
            "workflow-policy.js", "application/javascript; charset=utf-8", id="workflow-policy-js"
        ),
        pytest.param("runtime.js", "application/javascript; charset=utf-8", id="runtime-js"),
        pytest.param("logo-rhino-24.svg", "image/svg+xml; charset=utf-8", id="logo-rhino-24"),
        pytest.param("logo-rhino-16.svg", "image/svg+xml; charset=utf-8", id="logo-rhino-16"),
    ],
)
def test_asset_served_with_status_mime_and_nonempty_body(name: str, expected_ct: str) -> None:
    status, ct, body = _view(name)
    assert status == 200
    assert ct == expected_ct
    assert isinstance(body, bytes)
    assert len(body) > 0

    if name != "tokens.css":
        return
    # The MIME map has exactly the four registered extensions (checked once).
    assert set(_MIME_BY_EXT.keys()) == {".css", ".js", ".svg", ".map"}
    assert _MIME_BY_EXT[".css"] == "text/css; charset=utf-8"
    assert _MIME_BY_EXT[".js"] == "application/javascript; charset=utf-8"
    assert _MIME_BY_EXT[".svg"] == "image/svg+xml; charset=utf-8"
    assert _MIME_BY_EXT[".map"] == "application/json; charset=utf-8"


# ---------------------------------------------------------------------------
# 2. 404/400 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected_status"),
    [
        pytest.param("missing.png", 404, id="unknown-ext-png"),
        pytest.param("missing.ico", 404, id="unknown-ext-ico"),
        pytest.param("missing.woff", 404, id="unknown-ext-woff"),
        pytest.param("noextension", 404, id="no-extension"),
        pytest.param("", 404, id="empty-name"),
        pytest.param("nonexistent.css", 404, id="known-ext-unregistered-file-css"),
        pytest.param("nonexistent.js", 404, id="known-ext-unregistered-file-js"),
        pytest.param("nonexistent.map", 404, id="known-ext-unregistered-file-map"),
        pytest.param("favicon.ico", 404, id="unregistered-favicon"),
        pytest.param("agents.css", 404, id="agentic-tab-css-unregistered"),
        pytest.param("kanban.css", 404, id="agentic-tab-kanban-css-unregistered"),
        pytest.param("agents.js", 404, id="agentic-tab-agents-js-unregistered"),
        pytest.param("workflows.js", 404, id="agentic-tab-workflows-js-unregistered"),
        pytest.param("kanban.js", 404, id="agentic-tab-kanban-js-unregistered"),
        pytest.param("../etc/passwd", 400, id="traversal-parent-dir"),
        pytest.param("../../etc/passwd", 400, id="traversal-double-parent-dir"),
        pytest.param("../tokens.css", 400, id="traversal-one-up-known-file"),
        pytest.param("subdir/tokens.css", 400, id="traversal-subdir"),
        pytest.param("tokens.css/../../etc/passwd", 400, id="traversal-embedded-escape"),
        pytest.param("..\\etc\\passwd", 400, id="backslash-traversal"),
        pytest.param("tokens.css\\..\\..\\etc\\passwd", 400, id="backslash-embedded-escape"),
        pytest.param("subdir\\tokens.css", 400, id="backslash-subdir"),
    ],
)
def test_error_paths(name: str, expected_status: int) -> None:
    status, _, _ = _view(name)
    assert status == expected_status


# ---------------------------------------------------------------------------
# 3. runtime.js-before-dependents load order (real init-order bug)
# ---------------------------------------------------------------------------


def test_runtime_js_registered_before_dependents() -> None:
    """runtime.js must be registered before modules that depend on window.Runtime.

    The _ASSETS dict insertion order mirrors static-serving registration.
    """
    from dadaia_workspace.features.panel.views.static import _ASSETS

    keys = list(_ASSETS.keys())
    idx_runtime = keys.index("runtime.js")
    for dependent in ("workflow-policy.js", "sessions.js"):
        assert idx_runtime < keys.index(dependent), (
            f"runtime.js ({idx_runtime}) must precede {dependent} ({keys.index(dependent)}) in _ASSETS"
        )
