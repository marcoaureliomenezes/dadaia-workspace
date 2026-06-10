"""Unit tests for dadaia_workspace.infrastructure.runtime_transforms.model_mapping.

Covers:
- All five canonical Claude → Codex mappings (ADR-5 table).
- ValueError on an unknown Claude identifier.
- Guard that MODEL_MAP has exactly 5 entries (prevents accidental expansion without
  a corresponding test update and ADR amendment).
"""

from __future__ import annotations

import pytest

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


def test_unknown_identifier_raises_value_error() -> None:
    unknown = "claude-unknown-9-9"
    with pytest.raises(ValueError) as exc_info:
        map_model(unknown)
    assert unknown in str(exc_info.value)


def test_model_map_is_complete() -> None:
    """Guard: MODEL_MAP must have exactly 5 entries.

    If a new Claude model is added to agent frontmatter, the install pipeline
    will raise ValueError (by design). This test ensures no entry is silently
    added or removed from MODEL_MAP without a deliberate update to ADR-5.
    """
    assert len(MODEL_MAP) == 5
