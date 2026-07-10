"""Unit tests for dadaia_workspace.infrastructure.runtime_transforms.model_mapping.

Covers:
- Cross-table key/value-equality contract: MODEL_MAP keys == registry claude_ids and
  MODEL_MAP values == registry codex_ids (derived-view contract). These two
  assertions SUBSUME every individual per-model mapping pin (sonnet/haiku/opus/
  opus-4-8/fable-5/sonnet-5 all fall out of the registry equality, so the registry
  is the single source and no manual expansion can drift silently).
- ValueError on an unknown Claude identifier, naming the identifier.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.model_registry import REGISTRY
from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import (
    MODEL_MAP,
    map_model,
)


def test_model_map_is_a_derived_view_over_the_registry() -> None:
    """Cross-table contract: MODEL_MAP is a derived view over the registry — its
    keys are exactly the registry's claude_ids and each value is the matching
    registry codex_id. This subsumes every individual mapping pin (no manual
    expansion, no drift)."""
    assert set(MODEL_MAP) == {entry.claude_id for entry in REGISTRY}
    for entry in REGISTRY:
        assert MODEL_MAP[entry.claude_id] == entry.codex_id


def test_unknown_identifier_raises_value_error() -> None:
    unknown = "claude-unknown-9-9"
    with pytest.raises(ValueError) as exc_info:
        map_model(unknown)
    assert unknown in str(exc_info.value)
