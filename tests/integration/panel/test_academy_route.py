"""Integration tests for the Academy panel routes (T-013-07).

Exercises the live HTTP surface end-to-end against a real ``AcademyService`` wired
into the panel handler:

  - ``GET /academy/<module>/<lesson>`` renders a real lesson to HTML (200 + fragment);
    ``GET /api/academy`` catalog shape folds in as a second phase of the happy fn.
  - Negatives (unknown lesson/module, non-md, encoded-slash traversal, module/absolute
    escapes) are a no-information-disclosure table: always 404, never a content leak.

The panel serves every route without a credential (operator no-auth decision
2026-06-11), so these tests use a bare GET.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.academy.service import AcademyService
from dadaia_workspace.features.panel.views.academy import render_academy_lesson
from dadaia_workspace.features.panel.views.api_academy import render_api_academy
from tests.integration.panel.conftest import get

_KNOWN_MODULES = {"00_dadaia_workspace", "07_codex"}


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


@pytest.fixture(scope="module")
def academy_server(panel_server_factory) -> str:
    academy = AcademyService(_FakeCourseStore(), Path("/workspace"))
    panel_service = _PanelServiceStub(academy)
    return panel_server_factory(
        {
            "academy_lesson": render_academy_lesson(academy),
            "api_academy": render_api_academy(panel_service),  # type: ignore[arg-type]
        }
    )


class TestAcademyLessonRenderAndCatalog:
    def test_real_lesson_renders_and_catalog_lists_all_modules(self, academy_server: str) -> None:
        """A real lesson renders to HTML; /api/academy lists all knowledge_basis modules."""
        status, headers, body = get(f"{academy_server}/academy/07_codex/README.md")
        assert status == 200
        assert "text/html" in headers.get("content-type", "")
        text = body.decode("utf-8")
        assert "<!DOCTYPE html>" in text
        assert "<h1" in text
        assert "Codex" in text

        status, _, body = get(f"{academy_server}/academy/07_codex/01_codex_mental_model.md")
        assert status == 200
        assert b"<!DOCTYPE html>" in body

        status, headers, body = get(f"{academy_server}/api/academy")
        assert status == 200
        assert "application/json" in headers.get("content-type", "")
        import json

        data = json.loads(body)
        modules = data["modules"]
        names = {m["module"] for m in modules}
        assert _KNOWN_MODULES.issubset(names), names
        for mod in modules:
            assert mod["title"]
            assert isinstance(mod["lesson_count"], int)
            assert mod["lesson_count"] == len(mod["lessons"])
            assert mod["lesson_count"] >= 1

        codex = next(m for m in modules if m["module"] == "07_codex")
        assert codex["module_number"] == 7
        assert codex["title"]
        lesson_files = {lsn["lesson"] for lsn in codex["lessons"]}
        assert "01_codex_mental_model.md" in lesson_files
        assert "README.md" in lesson_files


class TestAcademyNegativesTable:
    """No-information-disclosure contract: always 404, never a content leak."""

    @pytest.mark.parametrize(
        "path",
        [
            "/academy/07_codex/nonexistent.md",  # unknown lesson
            "/academy/99_does_not_exist/README.md",  # unknown module
            "/academy/07_codex/README",  # non-.md
            "/academy/07_codex/..%2f06_claude_code%2fREADME.md",  # encoded-slash traversal
            "/academy/..%2f07_codex/README.md",  # module escape
            "/academy/07_codex/%2fetc%2fpasswd.md",  # absolute path injection
        ],
    )
    def test_negatives_return_404_no_leak(self, academy_server: str, path: str) -> None:
        status, _, body = get(f"{academy_server}{path}")
        assert status == 404
        assert b"06_claude_code" not in body
