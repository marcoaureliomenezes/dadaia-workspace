"""The roster and the persona files agree; the retired-name greps are rows of
test_public_source_hygiene::test_public_source_names_no_retired_surface.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.model_registry import CORE_AGENTS

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"


def test_core_agents_roster_is_the_five_dd_named_personas() -> None:
    assert CORE_AGENTS == (
        "dd-product-engineer",
        "dd-code-reviewer",
        "dd-sw-engineer-sr",
        "dd-sw-engineer-jr",
        "dd-researcher",
    )


def test_every_persona_file_is_dd_named_and_declares_that_name() -> None:
    agents = sorted((_PUBLIC / "agents").glob("*.md"))
    assert [p.stem for p in agents] == sorted(CORE_AGENTS)
    for path in agents:
        assert f"\nname: {path.stem}\n" in path.read_text(encoding="utf-8")
