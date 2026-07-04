"""PluginStore protocol — read/write the persisted installed-plugins ledger.

The ``core.protocols`` port for ``.dadaia/states/installed_plugins.json`` persistence,
mirroring the ``HarnessProfileStore`` precedent. The concrete adapter is
``infrastructure/json_plugin_store.py`` (JSON on disk); consumers depend on this Protocol,
never on the adapter directly.

Read semantics: ``read`` returns ``None`` when the ledger file is absent — a workspace with
no packs installed has no ledger, and the convention is that an absent ledger is treated as
the empty install set by every consumer (the ``dadaia plugin`` CLI and, in W2, the
``public_assets`` projection-precedence read).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.models.plugin_pack import InstalledPlugins


class PluginStore(Protocol):
    def read(self, states_dir: Path) -> InstalledPlugins | None:
        """Return the persisted ledger under *states_dir*, or ``None`` when absent."""
        ...

    def write(self, states_dir: Path, installed: InstalledPlugins) -> None:
        """Persist *installed* under *states_dir*, idempotently (no spurious rewrite)."""
        ...
