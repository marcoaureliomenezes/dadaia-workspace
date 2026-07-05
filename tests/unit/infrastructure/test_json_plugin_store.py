"""Unit tests for JsonPluginStore — the A-seam infra adapter (v0.1.60 FR2, AC-2).

The stateless JSON adapter for the ``PluginStore`` port: round-trip write→read, absent-file
→ ``None`` (empty-ledger convention), idempotent write (no rewrite when the bytes match),
and the exact on-disk shape ``{"schema_version": "1", "plugins": [...]}`` the ``dadaia
plugin`` CLI and the W2 ``public_assets`` projection-precedence read depend on.

**Mutation-sanity AC-11(0b) (W1, born falsifiable):** dropping a ledger field from
``JsonPluginStore._to_dict`` (e.g. removing ``"plugins"``) makes
:func:`test_write_then_read_round_trips` FAIL — the read back loses the pack set. That is the
discriminating proof the adapter genuinely persists the ledger shape.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.plugin_pack import InstalledPlugins
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore


def _states(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    return states


def test_read_absent_returns_none(tmp_path: Path) -> None:
    assert JsonPluginStore().read(_states(tmp_path)) is None


def test_write_then_read_round_trips(tmp_path: Path) -> None:
    states = _states(tmp_path)
    store = JsonPluginStore()
    store.write(states, InstalledPlugins(schema_version="1", plugins=("frontend-design", "devops")))
    assert store.read(states) == InstalledPlugins(
        schema_version="1", plugins=("frontend-design", "devops")
    )


def test_write_produces_canonical_shape(tmp_path: Path) -> None:
    states = _states(tmp_path)
    JsonPluginStore().write(states, InstalledPlugins.of(("frontend-design",)))
    data = json.loads((states / "installed_plugins.json").read_text(encoding="utf-8"))
    assert data == {"schema_version": "1", "plugins": ["frontend-design"]}


def test_write_creates_states_dir_if_absent(tmp_path: Path) -> None:
    """The adapter provisions ``.dadaia/states/`` on first write (fresh-workspace path)."""
    states = tmp_path / ".dadaia" / "states"  # deliberately not created
    JsonPluginStore().write(states, InstalledPlugins.of(("devops",)))
    assert (states / "installed_plugins.json").is_file()


def test_write_is_idempotent_no_rewrite_when_bytes_match(tmp_path: Path) -> None:
    states = _states(tmp_path)
    store = JsonPluginStore()
    store.write(states, InstalledPlugins.of(("frontend-design",)))
    path = states / "installed_plugins.json"
    first_mtime = path.stat().st_mtime_ns

    store.write(states, InstalledPlugins.of(("frontend-design",)))

    assert path.stat().st_mtime_ns == first_mtime


def test_write_overwrites_on_changed_set(tmp_path: Path) -> None:
    states = _states(tmp_path)
    store = JsonPluginStore()
    store.write(states, InstalledPlugins.of(("frontend-design",)))
    store.write(states, InstalledPlugins.of(("frontend-design", "devops")))
    assert store.read(states) == InstalledPlugins(
        schema_version="1", plugins=("frontend-design", "devops")
    )
