"""Integration tests for the Academy panel routes (T-013-07).

Exercises the live HTTP surface end-to-end against a real ``AcademyService`` wired
into the panel handler:

  - ``GET /academy/<module>/<lesson>`` renders a real lesson to HTML (200 + fragment).
  - ``GET /academy/<module>/<lesson>`` with a traversal attempt → 404 (the handler
    contract is no-information-disclosure; ``[^/]+`` route segments + the service guard
    both deny). We do NOT weaken the handler to a 400 — 404 is the documented contract.
  - ``GET /academy/<module>/<lesson>`` for an unknown lesson → 404.
  - ``GET /api/academy`` lists ALL shipped knowledge_basis modules with titles and
    lesson counts (acceptance: "ALL knowledge_basis modules with titles and lesson
    counts"), including 07_codex.

The panel serves every route without a credential (operator no-auth decision
2026-06-11), so these tests use a bare GET.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.academy.service import AcademyService
from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.views.academy import render_academy_lesson
from dadaia_workspace.features.panel.views.api import render_api_academy
from dadaia_workspace.features.panel.views.static import render_static

# Known shipped modules — the catalog must list at least this set (it ships more, but
# these are the stable anchors the acceptance phrase pins).
_KNOWN_MODULES = {"00_dadaia_workspace", "07_codex"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(url: str) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, headers, resp.read()
    except urllib.error.HTTPError as exc:
        headers = {k.lower(): v for k, v in exc.headers.items()}
        return exc.code, headers, exc.read()


class _FakeCourseStore:
    def save(self, course: Any) -> None: ...
    def update(self, course: Any) -> None: ...
    def get(self, slug: str) -> Any | None:
        return None

    def list_all(self) -> list[Any]:
        return []

    def delete(self, slug: str) -> None: ...


class _PanelServiceStub:
    """Minimal PanelService surface for render_api_academy: exposes ``.academy``."""

    def __init__(self, academy: AcademyService) -> None:
        self.academy = academy


def _build_academy_server() -> ThreadingHTTPServer:
    academy = AcademyService(_FakeCourseStore(), Path("/workspace"))
    panel_service = _PanelServiceStub(academy)

    def _stub_html(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "text/html; charset=utf-8", b"<html>ok</html>")

    views: dict[str, Any] = {
        "index": _stub_html,
        "static": render_static(),
        "academy_lesson": render_academy_lesson(academy),
        "api_academy": render_api_academy(panel_service),  # type: ignore[arg-type]
    }
    HandlerClass = make_handler_class(views, telemetry=None)
    return ThreadingHTTPServer(("127.0.0.1", 0), HandlerClass)


@pytest.fixture(scope="module")
def academy_server() -> Any:
    server = _build_academy_server()
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
    thread.start()
    yield base_url
    server.shutdown()


# ---------------------------------------------------------------------------
# GET /academy/<module>/<lesson> — happy path
# ---------------------------------------------------------------------------


class TestAcademyLessonRender:
    def test_real_lesson_renders_html(self, academy_server: str) -> None:
        """GET a real lesson → 200, text/html, with rendered Markdown content."""
        status, headers, body = _get(f"{academy_server}/academy/07_codex/README.md")
        assert status == 200
        assert "text/html" in headers.get("content-type", "")
        text = body.decode("utf-8")
        assert "<!DOCTYPE html>" in text
        # README.md H1 "# Codex for dadaia-workspace" renders to an <h1>.
        assert "<h1" in text
        assert "Codex" in text

    def test_numbered_lesson_renders_html(self, academy_server: str) -> None:
        status, _, body = _get(f"{academy_server}/academy/07_codex/01_codex_mental_model.md")
        assert status == 200
        assert b"<!DOCTYPE html>" in body


# ---------------------------------------------------------------------------
# GET /academy/<module>/<lesson> — negatives (no information disclosure: 404)
# ---------------------------------------------------------------------------


class TestAcademyLessonNegatives:
    def test_unknown_lesson_returns_404(self, academy_server: str) -> None:
        status, _, _ = _get(f"{academy_server}/academy/07_codex/nonexistent.md")
        assert status == 404

    def test_unknown_module_returns_404(self, academy_server: str) -> None:
        status, _, _ = _get(f"{academy_server}/academy/99_does_not_exist/README.md")
        assert status == 404

    def test_non_md_lesson_returns_404(self, academy_server: str) -> None:
        status, _, _ = _get(f"{academy_server}/academy/07_codex/README")
        assert status == 404

    def test_url_encoded_slash_traversal_returns_404(self, academy_server: str) -> None:
        """``..%2f`` decodes to ``../`` → segment contains '/', route ``[^/]+`` fails → 404.

        Contract is no-information-disclosure: the response is a plain 404, never a 200
        leaking a sibling/out-of-bounds file.
        """
        status, _, body = _get(f"{academy_server}/academy/07_codex/..%2f06_claude_code%2fREADME.md")
        assert status == 404
        assert b"06_claude_code" not in body  # no content leak

    def test_sibling_escape_in_module_returns_404(self, academy_server: str) -> None:
        """A ``..%2f``-style module escape is denied (404), not served."""
        status, _, _ = _get(f"{academy_server}/academy/..%2f07_codex/README.md")
        assert status == 404

    def test_absolute_path_injection_returns_404(self, academy_server: str) -> None:
        status, _, _ = _get(f"{academy_server}/academy/07_codex/%2fetc%2fpasswd.md")
        assert status == 404


# ---------------------------------------------------------------------------
# GET /api/academy — module catalog
# ---------------------------------------------------------------------------


class TestApiAcademyCatalog:
    def test_lists_all_known_modules_with_titles_and_counts(self, academy_server: str) -> None:
        """GET /api/academy → 200 JSON listing every knowledge_basis module.

        Acceptance: "ALL knowledge_basis modules with titles and lesson counts".
        """
        status, headers, body = _get(f"{academy_server}/api/academy")
        assert status == 200
        assert "application/json" in headers.get("content-type", "")
        data = json.loads(body)
        modules = data["modules"]
        names = {m["module"] for m in modules}
        # The shipped catalog must include at least the known stable module set.
        assert _KNOWN_MODULES.issubset(names), names
        # Every module carries a non-empty title and a lesson_count consistent with lessons.
        for mod in modules:
            assert mod["title"]
            assert isinstance(mod["lesson_count"], int)
            assert mod["lesson_count"] == len(mod["lessons"])
            assert mod["lesson_count"] >= 1

    def test_07_codex_has_expected_title_and_lessons(self, academy_server: str) -> None:
        status, _, body = _get(f"{academy_server}/api/academy")
        data = json.loads(body)
        codex = next(m for m in data["modules"] if m["module"] == "07_codex")
        assert codex["module_number"] == 7
        assert codex["title"]  # README H1 or humanized name
        lesson_files = {lsn["lesson"] for lsn in codex["lessons"]}
        assert "01_codex_mental_model.md" in lesson_files
        assert "README.md" in lesson_files
