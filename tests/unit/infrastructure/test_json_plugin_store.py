"""Unit tests for JsonPluginStore — the A-seam infra adapter (v0.1.60 FR2, AC-2).

The stateless JSON adapter for the ``PluginStore`` port: round-trip write→read, absent-file
→ ``None`` (empty-ledger convention), idempotent write (no rewrite when the bytes match),
and the exact on-disk shape ``{"schema_version": "1", "plugins": [...]}`` the ``dadaia
plugin`` CLI and the W2 ``public_assets`` projection-precedence read depend on.

**Mutation-sanity AC-11(0b) (W1, born falsifiable):** dropping a ledger field from
``JsonPluginStore._to_dict`` (e.g. removing ``"plugins"``) makes the shared store-contract
round-trip assertion FAIL — the read back loses the pack set. That is the discriminating
proof the adapter genuinely persists the ledger shape.

The generic read/write-store contract (absent->None/roundtrip/canonical-shape/
idempotent-mtime/overwrite) is asserted once via the shared
``_store_contract.assert_read_write_store_contract`` helper.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.plugin_pack import InstalledPlugins
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore

from ._store_contract import assert_read_write_store_contract


def _states(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    return states


def test_plugin_store_contract(tmp_path: Path) -> None:
    assert_read_write_store_contract(
        JsonPluginStore(),
        _states(tmp_path),
        "installed_plugins.json",
        first_value=InstalledPlugins(schema_version="1", plugins=("frontend-design", "devops")),
        second_value=InstalledPlugins(schema_version="1", plugins=("frontend-design",)),
        canonical_shape={"schema_version": "1", "plugins": ["frontend-design", "devops"]},
    )


def test_write_creates_states_dir_if_absent(tmp_path: Path) -> None:
    """The adapter provisions ``.dadaia/states/`` on first write (fresh-workspace path)."""
    states = tmp_path / ".dadaia" / "states"  # deliberately not created
    JsonPluginStore().write(states, InstalledPlugins.of(("devops",)))
    assert (states / "installed_plugins.json").is_file()
