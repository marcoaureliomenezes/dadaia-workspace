"""JsonServerRegistryStore — atomic CRUD over server_registry.json."""

import json
import os
from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry

_VERSION = "1"
_DEFAULT_RANGE = {"min_port": 3000, "max_port": 3999}


def _load(path: Path) -> dict:  # type: ignore[type-arg]
    if not path.exists():
        return {"version": _VERSION, "range": _DEFAULT_RANGE, "entries": []}
    with path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def _dump(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def _to_dict(entry: PortEntry) -> dict:  # type: ignore[type-arg]
    return {
        "port": entry.port,
        "project": entry.project,
        "url": entry.url or f"http://localhost:{entry.port}",
        "status": "active",
        "pid": entry.pid,
        "reserved_at": entry.reserved_at,
        "expires_at": entry.expires_at,
        "description": entry.description,
    }


def _from_dict(d: dict) -> PortEntry:  # type: ignore[type-arg]
    return PortEntry(
        port=d["port"],
        project=d["project"],
        reserved_at=d["reserved_at"],
        expires_at=d["expires_at"],
        url=d.get("url", ""),
        pid=d.get("pid"),
        description=d.get("description"),
    )


class JsonServerRegistryStore:
    def __init__(self, states_dir: Path) -> None:
        self._path = states_dir / "server_registry.json"

    def save(self, entry: PortEntry) -> None:
        data = _load(self._path)
        data["entries"].append(_to_dict(entry))
        _dump(self._path, data)

    def update(self, entry: PortEntry) -> None:
        data = _load(self._path)
        data["entries"] = [
            _to_dict(entry) if e["port"] == entry.port else e for e in data["entries"]
        ]
        _dump(self._path, data)

    def get(self, port: int) -> PortEntry | None:
        data = _load(self._path)
        for e in data["entries"]:
            if e["port"] == port:
                return _from_dict(e)
        return None

    def list_all(self) -> list[PortEntry]:
        data = _load(self._path)
        entries = [_from_dict(e) for e in data["entries"]]
        return sorted(entries, key=lambda e: e.port)

    def delete(self, port: int) -> None:
        data = _load(self._path)
        data["entries"] = [e for e in data["entries"] if e["port"] != port]
        _dump(self._path, data)
