"""JSON adapter for ``.dadaia/states/harness_profile.json`` — its ONE writer; stateless."""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.core.models.harness_profile import HarnessProfile

_FILENAME = "harness_profile.json"


def _profile_path(states_dir: Path) -> Path:
    return states_dir / _FILENAME


def _to_dict(profile: HarnessProfile) -> dict[str, object]:
    return {"schema_version": profile.schema_version, "harnesses": list(profile.harnesses)}


def _from_dict(data: dict[str, object]) -> HarnessProfile:
    raw = data.get("harnesses", [])
    harnesses = tuple(raw) if isinstance(raw, list) else ()
    version = data.get("schema_version")
    return HarnessProfile(str(version) if version is not None else "1", harnesses)


class JsonHarnessProfileStore:
    @staticmethod
    def path(states_dir: Path) -> Path:
        """Where the profile lives under *states_dir* — the doctor's ``missing`` target."""
        return _profile_path(states_dir)

    def read(self, states_dir: Path) -> HarnessProfile | None:
        """The persisted profile, or ``None`` when the file is absent."""
        path = _profile_path(states_dir)
        return _from_dict(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else None

    def resolve(self, states_dir: Path, workspace_root: Path) -> HarnessProfile:
        """The persisted profile; without one, the registered harness directories present."""
        persisted = self.read(states_dir)
        if persisted is not None:
            return persisted
        return HarnessProfile.of(
            tuple(
                name
                for name, record in HARNESS_RECORDS.items()
                if record.directory is not None and (workspace_root / record.directory).is_dir()
            )
        )

    def write(self, states_dir: Path, profile: HarnessProfile) -> None:
        """Persist *profile* atomically; a no-op when the on-disk bytes already match."""
        path = _profile_path(states_dir)
        new_text = json.dumps(_to_dict(profile), indent=2)
        if path.exists() and path.read_text(encoding="utf-8") == new_text:
            return
        atomic_write(path, new_text)
