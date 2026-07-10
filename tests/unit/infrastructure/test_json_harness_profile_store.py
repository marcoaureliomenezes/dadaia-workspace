"""Unit tests for JsonHarnessProfileStore — the A1 infra adapter (v0.1.58 FR2).

The stateless JSON adapter for the ``HarnessProfileStore`` port: round-trip write→read,
absent-file → ``None`` (all-four convention), idempotent write (no rewrite when the bytes
match), and the exact on-disk shape ``{"schema_version": "1", "harnesses": [...]}`` the
W3 ``public_assets`` read side and the inline ``WorkspaceService.init`` write depend on.

The generic read/write-store contract (absent->None/roundtrip/canonical-shape/
idempotent-mtime/overwrite) is asserted once via the shared
``_store_contract.assert_read_write_store_contract`` helper — this file carries no
store-specific logic beyond that template.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore

from ._store_contract import assert_read_write_store_contract


def _states(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    return states


def test_harness_profile_store_contract(tmp_path: Path) -> None:
    assert_read_write_store_contract(
        JsonHarnessProfileStore(),
        _states(tmp_path),
        "harness_profile.json",
        first_value=HarnessProfile(schema_version="1", harnesses=("claude", "codex")),
        second_value=HarnessProfile(schema_version="1", harnesses=("claude", "codex", "pi")),
        canonical_shape={"schema_version": "1", "harnesses": ["claude", "codex"]},
    )
