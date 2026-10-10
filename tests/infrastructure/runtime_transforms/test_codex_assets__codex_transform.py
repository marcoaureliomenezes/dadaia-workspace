"""The Codex model map (AC1.2): ``codex_model`` answers a tier alias from ``TIER_CODEX``,
an unknown alias raises.
"""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("alias", "codex_id"),
    [
        pytest.param("fable", "gpt-5.6-sol", id="fable"),
        pytest.param("opus", "gpt-5.6-sol", id="opus"),
        pytest.param("sonnet", "gpt-5.6-terra", id="sonnet"),
        pytest.param("haiku", "gpt-5.3-codex-spark", id="haiku"),
    ],
)
def test_codex_model_answers_a_tier_alias(alias: str, codex_id: str) -> None:
    # Imported per test so a module that cannot load fails each test, not collection.
    from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import codex_model

    assert codex_model(alias) == codex_id


def test_an_unmapped_claude_model_id_raises() -> None:
    from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import codex_model

    with pytest.raises(ValueError, match="claude-unknown-9-9"):
        codex_model("claude-unknown-9-9")
