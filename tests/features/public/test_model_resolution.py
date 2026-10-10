"""`dadaia public doctor` reports the active template in one line (AC4.4)."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.model_registry import (
    DEFAULT_TEMPLATE_ID,
    TEMPLATES,
    AgentModelPolicyOverlay,
)
from dadaia_workspace.features.public.model_resolution import check_model_resolution


def _rendered(lines: list) -> list[str]:
    return [line.render() for line in lines]


def test_no_overlay_names_the_default_template() -> None:
    assert _rendered(check_model_resolution()) == [
        f"[ok] model-resolution: template {DEFAULT_TEMPLATE_ID}"
    ]
    assert _rendered(check_model_resolution(overlay=AgentModelPolicyOverlay())) == [
        f"[ok] model-resolution: template {DEFAULT_TEMPLATE_ID}"
    ]


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
def test_applied_template_is_named(template_id: str) -> None:
    overlay = AgentModelPolicyOverlay(applied_template=template_id)

    assert _rendered(check_model_resolution(overlay=overlay)) == [
        f"[ok] model-resolution: template {template_id}"
    ]
