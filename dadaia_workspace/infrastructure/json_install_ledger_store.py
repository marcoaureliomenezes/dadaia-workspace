"""JsonInstallLedgerStore — JSON adapter for the projection install ledger (schema v1).

Stateless, per-call ``states_dir``, atomic write,
idempotent no-op on identical bytes. Persists to
``.dadaia/states/install_ledger.json``:

    {"schema_version": "1",
     "entries": [{"relpath": ".codex/AGENTS.md", "sha256": "…", "family": "law",
                  "kind": "file"}]}

``kind`` distinguishes a projected file from a symlink into the authored ``.agents/``
set (and from that link's copy fallback); an entry persisted before ``kind`` existed
migrates as ``"file"`` on read.

A malformed/unreadable ledger reads as ``None`` — reconciliation then runs bootstrap
semantics (record everything, prune nothing): a corrupt record must degrade to inaction,
never to deletion.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.models.install_ledger import InstallLedger

_FILENAME = "install_ledger.json"


def _ledger_path(states_dir: Path) -> Path:
    return states_dir / _FILENAME


class JsonInstallLedgerStore:
    @staticmethod
    def path(states_dir: Path) -> Path:
        """Where the ledger lives under *states_dir* — the doctor's ``missing`` target."""
        return _ledger_path(states_dir)

    def read(self, states_dir: Path) -> InstallLedger | None:
        """The persisted ledger, or ``None`` when absent OR unreadable (fail to inaction)."""
        path = _ledger_path(states_dir)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return None
            return InstallLedger.from_dict(data)
        except (OSError, ValueError):
            return None

    def write(self, states_dir: Path, ledger: InstallLedger) -> None:
        """Persist *ledger* atomically; a no-op when the on-disk bytes already match."""
        path = _ledger_path(states_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        new_text = json.dumps(ledger.to_dict(), indent=2)
        if path.exists():
            try:
                if path.read_text(encoding="utf-8") == new_text:
                    return
            except OSError:
                pass
        atomic_write(path, new_text)
