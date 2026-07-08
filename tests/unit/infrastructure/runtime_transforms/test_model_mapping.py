"""Unit tests for dadaia_workspace.infrastructure.runtime_transforms.model_mapping.

Covers:
- All canonical Claude → Codex mappings (ADR-5 table), as a DERIVED view over
  ``core.model_registry``.
- ValueError on an unknown Claude identifier.
- Cross-table key-equality contract: MODEL_MAP keys == registry claude_ids
  (the standalone ``len(MODEL_MAP) == 5`` pin was removed — it contradicted the
  pricing-table content and broke the moment the registry grew; the registry is
  now the single source and the key-set is asserted against it).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.model_registry import REGISTRY
from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import (
    MODEL_MAP,
    map_model,
)


def test_sonnet_maps_to_gpt53_codex() -> None:
    assert map_model("claude-sonnet-4-6") == "gpt-5.3-codex"


def test_haiku_maps_to_gpt54_mini() -> None:
    assert map_model("claude-haiku-4-5-20251001") == "gpt-5.4-mini"


def test_opus_maps_to_gpt55() -> None:
    assert map_model("claude-opus-4-7") == "gpt-5.5"


def test_opus_4_8_maps_to_gpt55() -> None:
    assert map_model("claude-opus-4-8") == "gpt-5.5"


def test_fable_5_maps_to_gpt55() -> None:
    assert map_model("claude-fable-5") == "gpt-5.5"


def test_sonnet_5_maps_to_gpt53_codex() -> None:
    """FR6/D-2 (v0.1.65): sonnet-5 shares sonnet-4-6's codex mapping."""
    assert map_model("claude-sonnet-5") == "gpt-5.3-codex"


def test_unknown_identifier_raises_value_error() -> None:
    unknown = "claude-unknown-9-9"
    with pytest.raises(ValueError) as exc_info:
        map_model(unknown)
    assert unknown in str(exc_info.value)


def test_model_map_keys_equal_registry_claude_ids() -> None:
    """Cross-table contract: MODEL_MAP is a derived view over the registry, so
    its keys must be exactly the registry's claude_ids (no drift, no manual
    expansion). Replaces the old brittle ``len(MODEL_MAP) == 5`` pin.
    """
    assert set(MODEL_MAP) == {entry.claude_id for entry in REGISTRY}


def test_model_map_values_match_registry_codex_ids() -> None:
    """Derived-view correctness: each MODEL_MAP value is the registry codex_id."""
    for entry in REGISTRY:
        assert MODEL_MAP[entry.claude_id] == entry.codex_id
