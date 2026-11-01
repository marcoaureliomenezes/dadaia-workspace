"""D-CX-7 reads a projected Codex persona as UTF-8: bytes that are not raise Undecodable."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.codex_doctor import dcx7_codex_skill_refs
from tests.helpers.oslib import Undecodable


def test_a_codex_persona_that_is_not_utf8_is_undecodable_not_a_codec_error(tmp_path: Path) -> None:
    agents = tmp_path / ".codex" / "agents"
    agents.mkdir(parents=True)
    (agents / "a.toml").write_bytes(b'developer_instructions = "caf\xe9"\n')

    with pytest.raises(Undecodable) as refused:
        dcx7_codex_skill_refs(tmp_path)

    assert refused.value.path == agents / "a.toml"
