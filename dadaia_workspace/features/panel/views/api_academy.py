"""Panel API view — GET /api/academy (shipped course-module catalog).

Lists the ``knowledge_basis`` modules that ship with the package (the browse
source for the Academy tab), NOT the user-created course copies under
``.dadaia/academy``.

Security (R3-A): json.dumps() handles JSON-string escaping; no HTML escaping needed here.
Content-Type is always set to application/json; charset=utf-8.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from dadaia_workspace.features.panel.service import PanelService


def render_api_academy(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return ``GET /api/academy`` view — list the shipped course catalog.

    Lists the ``knowledge_basis`` modules that ship with the package (the browse
    source for the Academy tab), NOT the user-created course copies under
    ``.dadaia/academy``. Each module carries its title, lesson count, and lessons so
    the panel can expand a module to its lessons and open each lesson via
    ``GET /academy/<module>/<lesson>``.

    Returns 200 with an empty list when ``service.academy`` is None.

    Response shape::

        {"modules": [
            {"module": "07_codex", "module_number": 7, "title": "...",
             "lesson_count": 9,
             "lessons": [{"lesson": "01_codex_mental_model.md", "title": "..."}]}
        ]}
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        if service.academy is None:
            body = json.dumps({"modules": []}).encode("utf-8")
            return (200, "application/json; charset=utf-8", body)
        catalog = service.academy.list_module_catalog()
        body = json.dumps({"modules": catalog}).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view
