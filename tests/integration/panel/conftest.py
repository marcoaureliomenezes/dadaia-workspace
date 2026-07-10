"""Shared panel-server fixtures for tests/integration/panel/ (T-7, v0.1.75 FR4).

Replaces six near-identical ``ThreadingHTTPServer`` module fixtures with:
  - one package-scoped ``staged_root`` (stage canonical public/ assets once)
  - one package-scoped ``panel_server_factory`` that boots/tracks servers and
    shuts them all down at package teardown
  - one shared ``_get``/``get`` HTTP helper

The panel serves every route without a credential (no-auth decision,
2026-06-11); ``make_handler_class``'s ``token`` parameter is deprecated/ignored,
kept only for call-site compatibility.
"""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

View = Callable[..., tuple[int, str, bytes]]


def get(url: str, token: str | None = None) -> tuple[int, dict[str, str], bytes]:
    """GET *url*, return (status, lowercase-keyed headers, body).

    Handles HTTPError without raising. ``token`` is accepted for call-site
    compatibility with pre-no-auth tests but is never required by the server.
    """
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310 — loopback test server
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, headers, resp.read()
    except urllib.error.HTTPError as exc:
        headers = {k.lower(): v for k, v in exc.headers.items()}
        return exc.code, headers, exc.read()


def _stub_html(**_kw: Any) -> tuple[int, str, bytes]:
    return (200, "text/html; charset=utf-8", b"<html>ok</html>")


def _stub_json(**_kw: Any) -> tuple[int, str, bytes]:
    return (200, "application/json; charset=utf-8", b"{}")


#: Baseline stub views satisfying every route ``make_handler_class`` requires.
#: Callers override specific keys with real view callables.
BASE_STUB_VIEWS: dict[str, View] = {
    "index": _stub_html,
    "api_panel_status": _stub_json,
    "api_servers": _stub_json,
    "api_contexts": _stub_json,
    "api_agents": _stub_json,
    "api_agent_prompt": _stub_json,
    "api_workflows": _stub_json,
    "api_workflow_detail": _stub_json,
    "memory": _stub_html,
    "memory_view": _stub_html,
    "static": lambda **kw: (200, "text/plain; charset=utf-8", b"ok"),
}


@pytest.fixture(scope="package")
def staged_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Stage canonical (tracked) public/ assets into a hermetic tmp workspace_root.

    Independent of any pre-existing on-disk .dadaia/agentic/ staging (gitignored,
    absent on a clean checkout). Built once per test-package run.
    """
    root = tmp_path_factory.mktemp("panel-staged-ws")
    FileSystemPublicAssetManager().stage(root)
    return root


@pytest.fixture(scope="package")
def panel_server_factory() -> Iterator[Callable[..., str]]:
    """``make(views, *, telemetry=None, token=None) -> base_url``.

    Boots a real ``ThreadingHTTPServer`` wired with ``make_handler_class`` and
    the given view mapping, tracks it, and shuts every server it created down
    at package teardown. Views not supplied fall back to ``BASE_STUB_VIEWS``.
    """
    servers: list[ThreadingHTTPServer] = []

    def make(
        views: dict[str, View],
        *,
        telemetry: Any = None,
        token: str | None = None,
    ) -> str:
        merged: dict[str, View] = {**BASE_STUB_VIEWS, **views}
        handler_cls = make_handler_class(merged, token=token, telemetry=telemetry)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        servers.append(server)
        port = server.server_address[1]
        thread = threading.Thread(
            target=lambda: server.serve_forever(poll_interval=0.05), daemon=True
        )
        thread.start()
        return f"http://127.0.0.1:{port}"

    yield make

    for server in servers:
        server.shutdown()
        server.server_close()
