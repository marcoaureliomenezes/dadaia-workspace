"""InstallLedgerStore protocol — read/write the persisted projection install ledger.

The ``core.protocols`` port for ``.dadaia/states/install_ledger.json`` persistence,
mirroring :class:`~dadaia_workspace.core.protocols.plugin_store.PluginStore`. The
concrete adapter is ``infrastructure/json_install_ledger_store.py``.

Read semantics: ``read`` returns ``None`` when the ledger file is absent — a workspace
that has never installed under a ledgered library bootstraps (record everything, prune
nothing on the first run).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.models.install_ledger import InstallLedger


class InstallLedgerStore(Protocol):
    def read(self, states_dir: Path) -> InstallLedger | None:
        """Return the persisted ledger under *states_dir*, or ``None`` when absent."""
        ...

    def write(self, states_dir: Path, ledger: InstallLedger) -> None:
        """Persist *ledger* under *states_dir*, idempotently (no spurious rewrite)."""
        ...
