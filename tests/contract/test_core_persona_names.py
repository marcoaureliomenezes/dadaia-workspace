"""Intent: CONTRACT — AC3.2 / T-047-56: the three personas carry their dd- names everywhere.

The roster and the persona files agree; the retired-name greps are rows of
test_public_source_hygiene::test_public_source_names_no_retired_surface.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.model_registry import CORE_AGENTS

pytestmark = pytest.mark.contract

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"


def test_core_agents_roster_is_the_dd_named_trio() -> None:
    assert CORE_AGENTS == ("dd-product-engineer", "dd-software-engineer", "dd-code-reviewer")


def test_every_persona_file_is_dd_named_and_declares_that_name() -> None:
    agents = sorted((_PUBLIC / "agents").glob("*.md"))
    assert [p.stem for p in agents] == sorted(CORE_AGENTS)
    for path in agents:
        assert f"\nname: {path.stem}\n" in path.read_text(encoding="utf-8")
