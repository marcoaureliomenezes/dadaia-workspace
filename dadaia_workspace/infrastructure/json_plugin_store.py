"""JsonPluginStore — JSON read/write over installed_plugins.json (schema v1).

The ``infrastructure`` adapter for the :class:`~dadaia_workspace.core.protocols.
plugin_store.PluginStore` port, mirroring ``json_harness_profile_store.py``'s read/write
style (atomic write via ``_atomic_write_text``, explicit ``_to_dict``/``_from_dict``
shaping). It persists the enabled plugin packs a workspace has installed to
``.dadaia/states/installed_plugins.json``:

    {"schema_version": "1", "plugins": ["frontend-design"]}

Consumed same-layer by the ``dadaia plugin`` CLI (v0.1.60 FR2) and, in W2, by
``public_assets`` install projection-precedence (FR3) to decide which agent stubs are
overwritten by a pack body.

The adapter is stateless — the ``states_dir`` is supplied per call, matching the per-call
workspace-root style the rest of the public-asset pipeline already uses.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.plugin_pack import InstalledPlugins
from dadaia_workspace.infrastructure.public_assets_common import _atomic_write_text

_FILENAME = "installed_plugins.json"


def _ledger_path(states_dir: Path) -> Path:
    return states_dir / _FILENAME


def _to_dict(installed: InstalledPlugins) -> dict[str, object]:
    return {
        "schema_version": installed.schema_version,
        "plugins": list(installed.plugins),
    }


def _from_dict(data: dict[str, object]) -> InstalledPlugins:
    raw = data.get("plugins", [])
    plugins = tuple(str(entry) for entry in raw) if isinstance(raw, list) else ()
    version = data.get("schema_version")
    return InstalledPlugins(
        schema_version=str(version) if version is not None else "1",
        plugins=plugins,
    )


class JsonPluginStore:
    def read(self, states_dir: Path) -> InstalledPlugins | None:
        """Return the persisted ledger, or ``None`` when the file is absent."""
        path = _ledger_path(states_dir)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return _from_dict(data)

    def write(self, states_dir: Path, installed: InstalledPlugins) -> None:
        """Persist *installed* atomically; a no-op when the on-disk bytes already match."""
        path = _ledger_path(states_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        new_text = json.dumps(_to_dict(installed), indent=2)
        if path.exists() and path.read_text(encoding="utf-8") == new_text:
            return
        _atomic_write_text(path, new_text)
