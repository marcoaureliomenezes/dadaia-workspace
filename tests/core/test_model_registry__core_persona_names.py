"""The roster and the persona files agree; the retired-name greps are rows of
test_public_source_hygiene::test_public_source_names_no_retired_surface.
"""

from __future__ import annotations

from dadaia_workspace.core.model_registry import CORE_AGENTS


def test_core_agents_roster_is_the_five_dd_named_personas() -> None:
    assert CORE_AGENTS == (
        "dd-product-engineer",
        "dd-code-reviewer",
        "dd-sw-engineer-sr",
        "dd-sw-engineer-jr",
        "dd-researcher",
    )
