"""Tests for GET /api/academy — module catalog browse source (T-013-07).

The Academy tab browses the shipped ``knowledge_basis`` module catalog (not the
user-created course copies). Golden pins the happy-path bytes; this file keeps
one merged param covering the real decisions: academy=None -> {modules: []},
empty catalog, populated catalog passthrough, kwargs ignored.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api_academy import render_api_academy

pytestmark = pytest.mark.unit


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


@pytest.mark.parametrize(
    ("academy", "extra_kwargs", "expected_modules"),
    [
        pytest.param(None, {}, [], id="academy-none-empty-modules"),
        pytest.param(None, {"extra_kwarg": "ignored"}, [], id="unexpected-kwargs-ignored"),
        pytest.param(_FakeAcademy([]), {}, [], id="empty-catalog"),
        pytest.param(
            _FakeAcademy([_make_module()]), {}, [_make_module()], id="populated-catalog-passthrough"
        ),
        pytest.param(
            _FakeAcademy(
                [
                    _make_module(
                        module="00_dadaia_workspace", module_number=0, title="A", lessons=[]
                    ),
                    _make_module(
                        module="01_spec_driven_development", module_number=1, title="B", lessons=[]
                    ),
                ]
            ),
            {},
            [
                _make_module(module="00_dadaia_workspace", module_number=0, title="A", lessons=[]),
                _make_module(
                    module="01_spec_driven_development", module_number=1, title="B", lessons=[]
                ),
            ],
            id="multiple-modules-passthrough",
        ),
    ],
)
def test_academy_view(
    academy: object | None,
    extra_kwargs: dict[str, str],
    expected_modules: list[dict[str, object]],
) -> None:
    service = _make_service(academy=academy)
    view = render_api_academy(service)
    status, content_type, body = view(**extra_kwargs)

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert "modules" in data
    assert isinstance(data["modules"], list)
    assert data["modules"] == expected_modules
