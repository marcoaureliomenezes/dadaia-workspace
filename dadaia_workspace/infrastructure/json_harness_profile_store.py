"""JsonHarnessProfileStore — JSON read/write over harness_profile.json (schema v1).

The ``infrastructure`` adapter for the :class:`~dadaia_workspace.core.protocols.
harness_profile_store.HarnessProfileStore` port, mirroring ``json_context_store.py``'s
read/write style (atomic write via ``_atomic_write_text``, explicit ``_to_dict``/
``_from_dict`` shaping). It persists the harness-selection profile a workspace was
scaffolded for to ``.dadaia/states/harness_profile.json``:

    {"schema_version": "1", "harnesses": ["claude"]}

Consumed same-layer by ``public_assets`` install/doctor (v0.1.58 W3) to scope which
runtime projections a single-harness workspace expects; the init-time write path in
``features/workspace/service.py`` inlines an identical payload (the allowed
``_init_json_file``-style bootstrap), so the two writers never fork on shape.

The adapter is stateless — the ``states_dir`` is supplied per call, matching the per-call
workspace-root style ``WorkspaceService`` already uses for its ``PublicAssetManager``.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.infrastructure.public_assets_common import _atomic_write_text

_FILENAME = "harness_profile.json"


def _profile_path(states_dir: Path) -> Path:
    return states_dir / _FILENAME


def _to_dict(profile: HarnessProfile) -> dict[str, object]:
    return {
        "schema_version": profile.schema_version,
        "harnesses": list(profile.harnesses),
    }


def _from_dict(data: dict[str, object]) -> HarnessProfile:
    raw = data.get("harnesses", [])
    harnesses = tuple(raw) if isinstance(raw, list) else ()
    version = data.get("schema_version")
    return HarnessProfile(
        schema_version=str(version) if version is not None else "1",
        harnesses=harnesses,
    )


class JsonHarnessProfileStore:
    def read(self, states_dir: Path) -> HarnessProfile | None:
        """Return the persisted profile, or ``None`` when the file is absent."""
        path = _profile_path(states_dir)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return _from_dict(data)

    def write(self, states_dir: Path, profile: HarnessProfile) -> None:
        """Persist *profile* atomically; a no-op when the on-disk bytes already match."""
        path = _profile_path(states_dir)
        new_text = json.dumps(_to_dict(profile), indent=2)
        if path.exists() and path.read_text(encoding="utf-8") == new_text:
            return
        _atomic_write_text(path, new_text)
