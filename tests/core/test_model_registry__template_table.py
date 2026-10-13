"""The template table is the one pin of every persona's model alias and effort."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.model_registry import (
    CORE_AGENTS,
    DEFAULT_TEMPLATE_ID,
    TEMPLATES,
    template_by_id,
)

_PERSONAS = (
    "dd-product-engineer",
    "dd-code-reviewer",
    "dd-sw-engineer-sr",
    "dd-sw-engineer-jr",
    "dd-researcher",
)

_TABLE = {
    "balanced": {
        "dd-product-engineer": ("opus", "high"),
        "dd-code-reviewer": ("opus", "high"),
        "dd-sw-engineer-sr": ("sonnet", "medium"),
        "dd-sw-engineer-jr": ("haiku", "medium"),
        "dd-researcher": ("haiku", "medium"),
    },
    "max-quality": {
        "dd-product-engineer": ("fable", "high"),
        "dd-code-reviewer": ("opus", "xhigh"),
        "dd-sw-engineer-sr": ("opus", "medium"),
        "dd-sw-engineer-jr": ("sonnet", "medium"),
        "dd-researcher": ("sonnet", "medium"),
    },
    "economy": {
        "dd-product-engineer": ("sonnet", "medium"),
        "dd-code-reviewer": ("sonnet", "high"),
        "dd-sw-engineer-sr": ("sonnet", "medium"),
        "dd-sw-engineer-jr": ("haiku", "low"),
        "dd-researcher": ("haiku", "low"),
    },
}


@pytest.mark.parametrize("template", _TABLE)
@pytest.mark.parametrize("persona", _PERSONAS)
def test_cell_equals_the_spec_table(template: str, persona: str) -> None:
    cell = template_by_id(template)[persona]
    assert (cell.model, cell.effort) == _TABLE[template][persona]


def test_templates_are_the_three_ids_with_five_personas_each() -> None:
    assert list(TEMPLATES) == ["balanced", "max-quality", "economy"]
    for cells in TEMPLATES.values():
        assert set(cells) == set(_PERSONAS)


def test_core_agents_are_the_template_keys_and_the_five_names() -> None:
    assert tuple(TEMPLATES[DEFAULT_TEMPLATE_ID]) == CORE_AGENTS
    assert sorted(CORE_AGENTS) == sorted(_PERSONAS)
