"""Model registry public-resolution contract.

This is intentionally a behavior test, not a source-wide residue grep. The current
boundary is that legacy model aliases must not resolve through the public registry index.
Historical names may appear in documentation or lineage comments, but they must not be
accepted as active runtime choices.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract

LEGACY_MODEL_IDS = ("claude-haiku-3-5",)


def test_retired_ids_do_not_resolve_in_the_registry() -> None:
    """Legacy model ids must not be reachable through the public registry index."""
    from dadaia_workspace.core.model_registry import registry_by_claude_id

    index = registry_by_claude_id()
    leaked = [mid for mid in LEGACY_MODEL_IDS if mid in index]
    assert not leaked, f"legacy model id(s) resolve in the registry index: {leaked}"
