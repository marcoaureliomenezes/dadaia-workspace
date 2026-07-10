"""Unit tests for the _security_headers helper in handler.py (T-AM-14).

Uses a minimal harness that calls _security_headers() and inspects
what headers would be sent, avoiding the need to spin up a real HTTP server
for this unit test.

Three survivors:
  1. ``_security_headers`` matrix (HTML -> CSP hardened no-unsafe-inline+sha256;
     JSON -> nosniff, no CSP; other -> none) — merged param.
  2. CSP hash W1 equality lock — kept as-is (catches edit-with-recompute).
  3. Every inline script on served index covered by a CSP hash (count==2) —
     kept as-is (falsifiable golden).
"""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _make_handler_with_spy():
    """Return a PanelHandler-like instance with a tracked send_header."""
    from dadaia_workspace.features.panel.handler import make_handler_class

    # Minimal stub views — only "index" key required for make_handler_class.
    stub_views: dict = {
        "index": lambda **kw: (200, "text/html; charset=utf-8", b"<html></html>"),
        "api_panel_status": lambda **kw: (200, "application/json", b"{}"),
        "api_contexts": lambda **kw: (200, "application/json", b"{}"),
        "memory": lambda **kw: (200, "text/html; charset=utf-8", b"ok"),
        "memory_view": lambda **kw: (200, "text/html; charset=utf-8", b"ok"),
        "static": lambda **kw: (200, "text/plain", b"ok"),
    }
    HandlerClass = make_handler_class(stub_views)
    handler = HandlerClass.__new__(HandlerClass)
    headers_sent: list[tuple[str, str]] = []
    handler.send_header = lambda k, v: headers_sent.append((k, v))  # type: ignore[assignment]
    return handler, headers_sent


# ---------------------------------------------------------------------------
# 1. _security_headers matrix — merged param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content_type",
    ["text/html; charset=utf-8", "text/html", "application/json", "text/plain"],
    ids=["html-charset", "html-bare", "json", "other-text-plain"],
)
def test_security_headers_matrix(content_type: str) -> None:
    """HTML -> hardened CSP (no unsafe-inline, sha256 tokens present) + no nosniff.
    JSON -> nosniff, no CSP. Any other content type -> neither header."""
    handler, headers_sent = _make_handler_with_spy()
    handler._security_headers(content_type)  # type: ignore[attr-defined]

    csp_values = [v for k, v in headers_sent if k == "Content-Security-Policy"]
    nosniff_values = [v for k, v in headers_sent if k == "X-Content-Type-Options"]

    if content_type.startswith("text/html"):
        assert csp_values, "CSP header must be sent for HTML responses"
        csp = csp_values[0]
        assert "default-src 'self'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp
        directives = {d.strip().split(None, 1)[0]: d.strip() for d in csp.split(";") if d.strip()}
        assert "script-src" in directives, "script-src directive must be present in CSP"
        script_src = directives["script-src"]
        assert "'unsafe-inline'" not in script_src, (
            "script-src must not contain 'unsafe-inline' — use SHA-256 hashes instead"
        )
        assert "sha256-" in script_src, "script-src must contain at least one 'sha256-...' token"

        from dadaia_workspace.features.panel.handler import (
            _CSP_SCRIPT_HASH_1,
            _CSP_SCRIPT_HASH_2,
        )

        assert _CSP_SCRIPT_HASH_1 in script_src, (
            f"Theme-switcher hash {_CSP_SCRIPT_HASH_1} missing from script-src"
        )
        assert _CSP_SCRIPT_HASH_2 in script_src, (
            f"Runtime-switcher hash {_CSP_SCRIPT_HASH_2} missing from script-src"
        )
        assert not nosniff_values, "HTML responses should not include X-Content-Type-Options"
    elif content_type == "application/json":
        assert nosniff_values, "X-Content-Type-Options header must be sent for JSON responses"
        assert nosniff_values[0] == "nosniff"
        assert not csp_values, "JSON responses should not include Content-Security-Policy"
    else:
        assert not csp_values
        assert not nosniff_values


# ---------------------------------------------------------------------------
# 2. CSP zero-touch equality lock (v0.1.59 W1 / T-59-10, AC-2 / Q4).
#
# ``TestInlineScriptCspCoverage`` (below) recomputes each inline-script hash and
# asserts CSP covers it — but it PASSES when a script and its hash change TOGETHER
# (edit-with-recompute). The v0.1.59 overhaul declares the two pre-paint inline
# scripts a ZERO-TOUCH invariant (Ruling B): they must stay byte-identical and
# ``_CSP_SCRIPT_HASH_1/2`` must NOT be recomputed. This equality lock freezes both
# hashes to their hardcoded W1 baseline values, so an edit-WITH-recompute (which
# changes the constant) is caught here even though coverage would still pass.
# ---------------------------------------------------------------------------

# Hardcoded W1 baseline values (handler.py:111,116 as of the v0.1.59 branch point).
# Do NOT update these during v0.1.59 — a change here is a Ruling-B violation, not a fix.
_W1_BASELINE_CSP_HASH_1 = "'sha256-GRTndW6m1zCm5uxB5kEDoOXw05c1c9MDdem3TFqSMfQ='"
_W1_BASELINE_CSP_HASH_2 = "'sha256-rrb6m84iyHOhA+A1XebxK17XtUkbhWfR95KsYvJgmpA='"


def test_csp_script_hashes_frozen_to_w1_baseline() -> None:
    """Freeze _CSP_SCRIPT_HASH_1/2 to their W1 baseline (catches edit-with-recompute)."""
    from dadaia_workspace.features.panel.handler import (
        _CSP_SCRIPT_HASH_1,
        _CSP_SCRIPT_HASH_2,
    )

    assert _CSP_SCRIPT_HASH_1 == _W1_BASELINE_CSP_HASH_1, (
        "_CSP_SCRIPT_HASH_1 moved off its W1 baseline — the theme pre-paint inline "
        "script was edited and its hash recomputed. v0.1.59 Ruling B forbids this "
        "(the two pre-paint scripts stay byte-identical). Revert the script edit."
    )
    assert _CSP_SCRIPT_HASH_2 == _W1_BASELINE_CSP_HASH_2, (
        "_CSP_SCRIPT_HASH_2 moved off its W1 baseline — the runtime pre-paint inline "
        "script was edited and its hash recomputed. v0.1.59 Ruling B forbids this "
        "(the two pre-paint scripts stay byte-identical). Revert the script edit."
    )


# ---------------------------------------------------------------------------
# 3. Falsifiable CSP coverage: every inline <script> on the served index page
# must be covered by a sha256 hash in script-src (zero CSP-blocked scripts).
# ---------------------------------------------------------------------------

# <script ...>BODY</script> where the opening tag carries no src= attribute.
_INLINE_SCRIPT_RE = re.compile(
    r"<script(?P<attrs>(?:(?!>).)*)>(?P<body>.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)


def _render_index_html() -> str:
    from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
    from dadaia_workspace.core.models.spec_context import SpecContextProject
    from dadaia_workspace.features.panel.service import PanelService
    from dadaia_workspace.features.panel.views.index import render_index

    class _FakeRegistry:
        def list_entries(
            self, project: str | None = None, include_stale: bool = True
        ) -> list[tuple[PortEntry, PortStatus]]:
            return []

    class _FakeSpecContext:
        def list_all(self) -> list[SpecContextProject]:
            return []

    service = PanelService(
        registry=_FakeRegistry(),  # type: ignore[arg-type]
        spec_context=_FakeSpecContext(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
    )
    status, content_type, body = render_index(service)()
    assert status == 200
    return body.decode("utf-8")


def _script_src_from_handler() -> str:
    handler, headers_sent = _make_handler_with_spy()
    handler._security_headers("text/html; charset=utf-8")  # type: ignore[attr-defined]
    csp = next(v for k, v in headers_sent if k == "Content-Security-Policy")
    return next(d.strip() for d in csp.split(";") if d.strip().startswith("script-src"))


def test_every_inline_script_is_covered_by_a_csp_hash() -> None:
    """Recompute each emitted inline-script hash and assert CSP covers it."""
    html = _render_index_html()
    script_src = _script_src_from_handler()

    inline_bodies = [
        m.group("body")
        for m in _INLINE_SCRIPT_RE.finditer(html)
        if "src=" not in m.group("attrs").lower()
    ]
    # The served index page carries exactly two inline scripts
    # (theme pre-paint + runtime pre-paint). A new un-hashed inline
    # script would be CSP-blocked in the browser — fail loudly here.
    assert len(inline_bodies) == 2, (
        f"expected 2 inline scripts on the index page, found {len(inline_bodies)}; "
        "a new inline <script> needs its sha256 added to _CSP_SCRIPT_HASH_*"
    )

    for body in inline_bodies:
        digest = base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode()
        token = f"'sha256-{digest}'"
        assert token in script_src, (
            f"inline script not covered by CSP script-src (would be blocked): "
            f"computed {token} absent. Script body:\n{body}"
        )
