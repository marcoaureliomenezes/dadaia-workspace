"""Unit tests for the server-rendered Layer-2 personas roster (v0.1.45 / T-45-05).

The Agentic tab's second roster (keyed by role) is server-rendered and CSP-clean: each
of the 8 non-PM personas with role, summary, source_agent, the constant ``Layer-2``
label (NO per-persona model column), and the governed workflow steps referencing its
role. Any model shown is derived ONLY from those step bindings.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.lifecycle.personas.loader import Persona
from dadaia_workspace.features.panel.views.agents import render_personas_subsection


class _FakeLoader:
    def __init__(self, personas: list[Persona]) -> None:
        self._personas = personas

    def list_personas(self) -> list[Persona]:
        return self._personas


def _persona(role: str) -> Persona:
    return Persona(
        id=f"persona:{role}",
        role=role,
        summary=f"{role} does things",
        source_agent=f"agents/{role}.md",
        harness_universal=True,
        body="b",
        path=Path(f"/x/{role}.md"),
    )


def test_personas_subsection_structure_and_constant_layer() -> None:
    html = render_personas_subsection(_FakeLoader([_persona("software-engineer")]))
    assert 'id="ops-subsection-personas"' in html
    assert "Layer-2 personas" in html
    assert 'class="persona-card"' in html
    assert 'data-role="software-engineer"' in html
    # Constant Layer-2 badge, no per-persona model column.
    assert "persona-layer-badge" in html
    assert ">Layer-2<" in html


def test_persona_where_used_lists_governed_steps_for_a_referenced_role() -> None:
    """software-engineer is referenced by the implementation ladder (implement step)."""
    html = render_personas_subsection(_FakeLoader([_persona("software-engineer")]))
    assert "persona-step-list" in html
    # The implementation workflow's implement step is bound to software-engineer.
    assert "implement" in html
    assert "not referenced by any governed step" not in html


def test_persona_where_used_empty_renders_explicit_line() -> None:
    """A role that maps to zero catalog steps renders the explicit 'not referenced' line."""
    html = render_personas_subsection(_FakeLoader([_persona("nonexistent-role")]))
    assert "not referenced by any governed step" in html


def test_persona_binding_model_derives_from_step_only() -> None:
    """Any model shown for a persona comes from a step binding (harness · model)."""
    html = render_personas_subsection(_FakeLoader([_persona("software-engineer")]))
    # The binding column carries a concrete harness (codex/pi), from the STEP default.
    assert "persona-step-binding" in html
    assert ("codex" in html) or ("pi" in html)


def test_personas_loader_failure_degrades_to_empty_state() -> None:
    class _Boom:
        def list_personas(self) -> list[Persona]:
            raise RuntimeError("no disk")

    html = render_personas_subsection(_Boom())
    assert 'id="ops-subsection-personas"' in html
    assert "No Layer-2 personas found." in html


def test_persona_text_is_html_escaped() -> None:
    evil = Persona(
        id="persona:x",
        role="r<script>",
        summary="<b>hi</b>",
        source_agent="agents/x.md",
        harness_universal=True,
        body="b",
        path=Path("/x.md"),
    )
    html = render_personas_subsection(_FakeLoader([evil]))
    assert "<script>" not in html
    assert "<b>hi</b>" not in html
