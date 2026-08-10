"""Unit tests for the simple read/write JSON adapters — JsonHarnessProfileStore
(v0.1.58 FR2, A1) and JsonPluginStore (v0.1.60 FR2, AC-2). Merged file (T-8, v0.1.75
FR3 squeeze): both adapters share the identical stateless read/write-store contract
(absent->None/roundtrip/canonical-shape/idempotent-mtime/overwrite), asserted once via
the shared ``_store_contract.assert_read_write_store_contract`` helper through one
parametrized sweep across both stores.

**Mutation-sanity AC-11(0b) (W1, born falsifiable) — JsonPluginStore:** dropping a
ledger field from ``JsonPluginStore._to_dict`` (e.g. removing ``"plugins"``) makes the
shared store-contract round-trip assertion FAIL — the read back loses the pack set.
That is the discriminating proof the adapter genuinely persists the ledger shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.models.plugin_pack import InstalledPlugins
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore

from ._store_contract import assert_read_write_store_contract


def _states(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    return states


@pytest.mark.parametrize(
    ("store", "filename", "first_value", "second_value", "canonical_shape"),
    [
        pytest.param(
            JsonHarnessProfileStore(),
            "harness_profile.json",
            HarnessProfile(schema_version="1", harnesses=("claude", "codex")),
            HarnessProfile(schema_version="1", harnesses=("claude", "codex", "kimi-code")),
            {"schema_version": "1", "harnesses": ["claude", "codex"]},
            id="harness-profile-store",
        ),
        pytest.param(
            JsonPluginStore(),
            "installed_plugins.json",
            InstalledPlugins(schema_version="1", plugins=("frontend-design", "devops")),
            InstalledPlugins(schema_version="1", plugins=("frontend-design",)),
            {"schema_version": "1", "plugins": ["frontend-design", "devops"]},
            id="plugin-store",
        ),
    ],
)
def test_readwrite_store_contract(
    tmp_path: Path,
    store: Any,
    filename: str,
    first_value: Any,
    second_value: Any,
    canonical_shape: dict[str, object],
) -> None:
    assert_read_write_store_contract(
        store,
        _states(tmp_path),
        filename,
        first_value=first_value,
        second_value=second_value,
        canonical_shape=canonical_shape,
    )


def test_plugin_store_write_creates_states_dir_if_absent(tmp_path: Path) -> None:
    """The plugin-store adapter provisions ``.dadaia/states/`` on first write
    (fresh-workspace path) — the only store-specific behavior beyond the shared
    contract above."""
    states = tmp_path / ".dadaia" / "states"  # deliberately not created
    JsonPluginStore().write(states, InstalledPlugins.of(("devops",)))
    assert (states / "installed_plugins.json").is_file()
