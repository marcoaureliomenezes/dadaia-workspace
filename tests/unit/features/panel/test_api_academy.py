"""Tests for GET /api/academy — T-P5-25.

Covers:
  - render_api_academy returns 200 with empty list when service.academy is None.
  - render_api_academy returns 200 with courses when academy.list_all() has data.
  - Content-Type is application/json; charset=utf-8.
  - Response shape: {"courses": [{slug, name, module_number, module_name, created_at}]}.
  - course_dir is NOT included in the response (only the 5 specified fields).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.course import Course
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
    def __init__(self, courses: list[Course]) -> None:
        self._courses = courses

    def list_all(self) -> list[Course]:
        return list(self._courses)


def _make_service(academy: object | None = None) -> PanelService:
    return PanelService(
        registry=_FakeRegistry(),  # type: ignore[arg-type]
        spec_context=_FakeSpecContext(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
        academy=academy,
    )


def _make_course(
    slug: str = "python-101",
    name: str = "Python 101",
    module_number: int = 1,
    module_name: str = "01_introduction",
    created_at: str = "2026-01-01T00:00:00+00:00",
    course_dir: str = "/workspace/.dadaia/academy/python-101",
) -> Course:
    return Course(
        slug=slug,
        name=name,
        module_number=module_number,
        module_name=module_name,
        created_at=created_at,
        course_dir=course_dir,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_render_api_academy_none_returns_empty_list() -> None:
    """When service.academy is None, returns 200 with courses: []."""
    service = _make_service(academy=None)
    view = render_api_academy(service)
    status, content_type, body = view()

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert data == {"courses": []}


def test_render_api_academy_with_courses() -> None:
    """When academy has courses, returns them in the response."""
    course = _make_course()
    service = _make_service(academy=_FakeAcademy([course]))
    view = render_api_academy(service)
    status, content_type, body = view()

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert len(data["courses"]) == 1
    item = data["courses"][0]
    assert item["slug"] == "python-101"
    assert item["name"] == "Python 101"
    assert item["module_number"] == 1
    assert item["module_name"] == "01_introduction"
    assert item["created_at"] == "2026-01-01T00:00:00+00:00"


def test_render_api_academy_does_not_include_course_dir() -> None:
    """course_dir must not appear in the API response (not part of the contract)."""
    course = _make_course()
    service = _make_service(academy=_FakeAcademy([course]))
    view = render_api_academy(service)
    _, _, body = view()

    data = json.loads(body)
    assert "course_dir" not in data["courses"][0]


def test_render_api_academy_multiple_courses() -> None:
    """Multiple courses are all returned in the response."""
    courses = [
        _make_course(slug="c1", name="C1", module_number=1),
        _make_course(slug="c2", name="C2", module_number=2),
    ]
    service = _make_service(academy=_FakeAcademy(courses))
    view = render_api_academy(service)
    _, _, body = view()

    data = json.loads(body)
    assert len(data["courses"]) == 2
    slugs = {c["slug"] for c in data["courses"]}
    assert slugs == {"c1", "c2"}


def test_render_api_academy_empty_academy_returns_empty_list() -> None:
    """When academy exists but list_all() returns [], courses key is []."""
    service = _make_service(academy=_FakeAcademy([]))
    view = render_api_academy(service)
    _, _, body = view()

    data = json.loads(body)
    assert data == {"courses": []}


def test_render_api_academy_content_type() -> None:
    """Content-Type header is always application/json; charset=utf-8."""
    service = _make_service(academy=None)
    view = render_api_academy(service)
    _, content_type, _ = view()
    assert content_type == "application/json; charset=utf-8"


def test_render_api_academy_shape_when_none() -> None:
    """Top-level key must be 'courses' (not 'items', 'data', etc.)."""
    service = _make_service(academy=None)
    view = render_api_academy(service)
    _, _, body = view()
    data = json.loads(body)
    assert "courses" in data
    assert isinstance(data["courses"], list)


def test_render_api_academy_kwargs_ignored() -> None:
    """View accepts and ignores extra kwargs forwarded by the handler."""
    service = _make_service(academy=None)
    view = render_api_academy(service)
    # extra_kwarg simulates what the handler might pass
    status, _, body = view(extra_kwarg="ignored")
    assert status == 200
    data = json.loads(body)
    assert data == {"courses": []}
