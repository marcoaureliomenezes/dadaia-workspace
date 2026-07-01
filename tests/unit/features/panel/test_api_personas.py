"""Unit tests for the read-only /api/personas endpoint (v0.1.45 / T-45-04).

The panel reads the 8 non-PM Layer-2 personas via ``PersonaLoader`` and surfaces EXACTLY
the real ``Persona`` fields ``{id, role, summary, source_agent, harness_universal}`` plus
a constant ``layer = "Layer-2"``. The ``Persona`` dataclass has NO ``model`` and NO
``tier`` (arch finding #1) — the endpoint must never fabricate them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dadaia_workspace.features.lifecycle.personas.loader import Persona, PersonaLoader
from dadaia_workspace.features.panel.views.api import render_api_personas


def _call(loader: Any) -> tuple[int, dict[str, Any]]:
    view = render_api_personas(loader)
    status, ctype, body = view()
    assert "application/json" in ctype
    return status, json.loads(body)


def _fake_persona(role: str) -> Persona:
    return Persona(
        id=f"persona:{role}",
        role=role,
        summary=f"{role} summary",
        source_agent=f"agents/{role}.md",
        harness_universal=True,
        body="body",
        path=Path(f"/x/{role}.md"),
    )


class _FakeLoader:
    def __init__(self, personas: list[Persona]) -> None:
        self._personas = personas

    def list_personas(self) -> list[Persona]:
        return self._personas


def test_personas_payload_shape_and_constant_layer() -> None:
    status, data = _call(_FakeLoader([_fake_persona("software-engineer")]))
    assert status == 200
    assert data["layer"] == "Layer-2"
    assert "generated_at" in data
    assert len(data["personas"]) == 1
    p = data["personas"][0]
    assert p == {
        "id": "persona:software-engineer",
        "role": "software-engineer",
        "summary": "software-engineer summary",
        "source_agent": "agents/software-engineer.md",
        "harness_universal": True,
        "layer": "Layer-2",
    }


def test_personas_never_fabricate_model_or_tier() -> None:
    """The Persona entity has no model/tier — the payload must not invent them."""
    _status, data = _call(_FakeLoader([_fake_persona("qa-engineer")]))
    for p in data["personas"]:
        assert "model" not in p, "persona payload must NOT carry a fabricated model key"
        assert "tier" not in p, "persona payload must NOT carry a fabricated tier key"


def test_personas_loader_failure_degrades_to_empty_roster() -> None:
    """A loader failure yields a generic 200 empty roster, never a 500/leak (A06)."""

    class _BoomLoader:
        def list_personas(self) -> list[Persona]:
            raise RuntimeError("disk gone")

    status, data = _call(_BoomLoader())
    assert status == 200
    assert data["personas"] == []
    assert data["layer"] == "Layer-2"


def test_personas_real_loader_returns_the_eight_non_pm_roles() -> None:
    """Against the packaged personas, the roster is the 8 non-PM Layer-2 roles."""
    status, data = _call(PersonaLoader())
    assert status == 200
    roles = {p["role"] for p in data["personas"]}
    expected = {
        "ai-engineer",
        "code-reviewer",
        "product-engineer",
        "project-auditor",
        "qa-engineer",
        "security-reviewer",
        "software-architect",
        "software-engineer",
    }
    assert expected.issubset(roles)
    assert "project-manager" not in roles
    # No fabricated model/tier on any real persona either.
    for p in data["personas"]:
        assert "model" not in p
        assert "tier" not in p
        assert p["layer"] == "Layer-2"
