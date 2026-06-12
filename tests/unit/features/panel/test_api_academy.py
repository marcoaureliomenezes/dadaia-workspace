"""Tests for GET /api/academy — module catalog browse source (T-013-07).

The Academy tab browses the shipped ``knowledge_basis`` module catalog (not the
user-created course copies). Covers:
  - render_api_academy returns 200 with empty modules list when service.academy is None.
  - render_api_academy returns 200 with the module catalog when academy provides one.
  - Content-Type is application/json; charset=utf-8.
  - Response shape: {"modules": [{module, module_number, title, lesson_count, lessons}]}.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api import render_api_academy

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeRegistry:
    def list_entries(self, project: str | None = None, include_stale: bool = True) -> list[Any]:
        return []


class _FakeSpecContext:
    def list_all(self) -> list[Any]:
        return []


class _FakeAcademy:
    def __init__(self, catalog: list[dict[str, object]]) -> None:
        self._catalog = catalog

    def list_module_catalog(self) -> list[dict[str, object]]:
        return list(self._catalog)


def _make_service(academy: object | None = None) -> PanelService:
    return PanelService(
        registry=_FakeRegistry(),  # type: ignore[arg-type]
        spec_context=_FakeSpecContext(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
        academy=academy,
    )


def _make_module(
    module: str = "07_codex",
    module_number: int = 7,
    title: str = "Codex for dadaia-workspace",
    lessons: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    if lessons is None:
        lessons = [
            {"lesson": "01_codex_mental_model.md", "title": "01. Codex Mental Model"},
            {"lesson": "README.md", "title": "Codex for dadaia-workspace"},
        ]
    return {
        "module": module,
        "module_number": module_number,
        "title": title,
        "lesson_count": len(lessons),
        "lessons": lessons,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_render_api_academy_none_returns_empty_modules() -> None:
    service = _make_service(academy=None)
    view = render_api_academy(service)
    status, content_type, body = view()

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    assert json.loads(body) == {"modules": []}


def test_render_api_academy_with_modules() -> None:
    service = _make_service(academy=_FakeAcademy([_make_module()]))
    view = render_api_academy(service)
    status, content_type, body = view()

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert len(data["modules"]) == 1
    mod = data["modules"][0]
    assert mod["module"] == "07_codex"
    assert mod["module_number"] == 7
    assert mod["title"] == "Codex for dadaia-workspace"
    assert mod["lesson_count"] == 2
    assert mod["lessons"][0]["lesson"] == "01_codex_mental_model.md"
    assert mod["lessons"][0]["title"] == "01. Codex Mental Model"


def test_render_api_academy_multiple_modules() -> None:
    catalog = [
        _make_module(module="00_dadaia_workspace", module_number=0, title="A", lessons=[]),
        _make_module(module="01_spec_driven_development", module_number=1, title="B", lessons=[]),
    ]
    service = _make_service(academy=_FakeAcademy(catalog))
    view = render_api_academy(service)
    _, _, body = view()

    data = json.loads(body)
    assert len(data["modules"]) == 2
    names = {m["module"] for m in data["modules"]}
    assert names == {"00_dadaia_workspace", "01_spec_driven_development"}


def test_render_api_academy_empty_catalog() -> None:
    service = _make_service(academy=_FakeAcademy([]))
    view = render_api_academy(service)
    _, _, body = view()
    assert json.loads(body) == {"modules": []}


def test_render_api_academy_content_type() -> None:
    service = _make_service(academy=None)
    view = render_api_academy(service)
    _, content_type, _ = view()
    assert content_type == "application/json; charset=utf-8"


def test_render_api_academy_top_level_key_is_modules() -> None:
    service = _make_service(academy=None)
    view = render_api_academy(service)
    _, _, body = view()
    data = json.loads(body)
    assert "modules" in data
    assert isinstance(data["modules"], list)


def test_render_api_academy_kwargs_ignored() -> None:
    service = _make_service(academy=None)
    view = render_api_academy(service)
    status, _, body = view(extra_kwarg="ignored")
    assert status == 200
    assert json.loads(body) == {"modules": []}
