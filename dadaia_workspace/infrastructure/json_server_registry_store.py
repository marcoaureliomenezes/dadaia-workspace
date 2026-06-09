"""JsonServerRegistryStore — atomic CRUD over server_registry.json.

Resilience contract (v0.1.1 / Bug B fix):
    - Malformed JSON file → empty registry returned, warning logged. Never raise.
    - Malformed individual entry (missing key, wrong type) → entry skipped,
      warning logged. Other valid entries are returned.
    - Unknown extra keys on an entry → accepted (forward-compat).

The invariant is "one bad entry must not blank the entire registry."
"""

import json
import logging
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.server_registry import PortEntry
from dadaia_workspace.infrastructure.public_assets_common import _atomic_write_text

logger = logging.getLogger(__name__)

_VERSION = "1"
_DEFAULT_RANGE = {"min_port": 3000, "max_port": 3999}


def _empty_registry() -> dict[str, Any]:
    return {"version": _VERSION, "range": _DEFAULT_RANGE, "entries": []}


def _load(path: Path) -> dict[str, Any]:
    """Read the registry file, returning an empty registry on any structural problem.

    On `JSONDecodeError`, `OSError`, or missing top-level keys: log a warning
    citing the path + reason, return a fresh empty registry. Never raise — the
    panel and CLI must continue to function even when the file is corrupt.
    """
    if not path.exists():
        return _empty_registry()
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        logger.warning(
            "registry_file_malformed: path=%s reason=%s — returning empty registry",
            path,
            exc,
        )
        return _empty_registry()
    except OSError as exc:
        logger.warning(
            "registry_file_unreadable: path=%s reason=%s — returning empty registry",
            path,
            exc,
        )
        return _empty_registry()

    if not isinstance(raw, dict):
        logger.warning(
            "registry_file_wrong_root_type: path=%s got=%s — returning empty registry",
            path,
            type(raw).__name__,
        )
        return _empty_registry()

    # Ensure required top-level keys are present (forward-compat: extras are fine).
    if "entries" not in raw or not isinstance(raw["entries"], list):
        logger.warning(
            "registry_file_missing_entries_list: path=%s — returning empty registry",
            path,
        )
        return _empty_registry()
    raw.setdefault("version", _VERSION)
    raw.setdefault("range", _DEFAULT_RANGE)
    return raw


def _to_dict(entry: PortEntry) -> dict[str, Any]:
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


def _from_dict(d: dict[str, Any]) -> PortEntry | None:
    """Parse a single entry dict.

    Returns ``None`` on malformed input (missing required key, wrong type)
    after logging a warning. Callers must filter out ``None``.
    """
    try:
        port = d["port"]
        project = d["project"]
        reserved_at = d["reserved_at"]
        expires_at = d["expires_at"]
    except KeyError as exc:
        logger.warning(
            "registry_entry_malformed: missing_key=%s entry=%r — skipping",
            exc,
            d,
        )
        return None
    except TypeError as exc:
        # e.g. `d` was a list or int instead of a dict
        logger.warning(
            "registry_entry_malformed: wrong_type=%s entry=%r — skipping",
            exc,
            d,
        )
        return None

    if not isinstance(port, int) or isinstance(port, bool):
        logger.warning(
            "registry_entry_malformed: port_not_int port=%r entry=%r — skipping",
            port,
            d,
        )
        return None
    if not isinstance(project, str):
        logger.warning(
            "registry_entry_malformed: project_not_str project=%r entry=%r — skipping",
            project,
            d,
        )
        return None

    try:
        return PortEntry(
            port=port,
            project=project,
            reserved_at=reserved_at,
            expires_at=expires_at,
            url=d.get("url", ""),
            pid=d.get("pid"),
            description=d.get("description"),
        )
    except (TypeError, ValueError) as exc:
        logger.warning(
            "registry_entry_malformed: construction_failed reason=%s entry=%r — skipping",
            exc,
            d,
        )
        return None


class JsonServerRegistryStore:
    def __init__(self, states_dir: Path) -> None:
        self._path = states_dir / "server_registry.json"

    def save(self, entry: PortEntry) -> None:
        data = _load(self._path)
        data["entries"].append(_to_dict(entry))
        _atomic_write_text(self._path, json.dumps(data, indent=2))

    def update(self, entry: PortEntry) -> None:
        data = _load(self._path)
        data["entries"] = [
            _to_dict(entry) if e.get("port") == entry.port else e for e in data["entries"]
        ]
        _atomic_write_text(self._path, json.dumps(data, indent=2))

    def get(self, port: int) -> PortEntry | None:
        data = _load(self._path)
        for e in data["entries"]:
            if not isinstance(e, dict):
                continue
            if e.get("port") == port:
                return _from_dict(e)
        return None

    def list_all(self) -> list[PortEntry]:
        data = _load(self._path)
        parsed = [_from_dict(e) for e in data["entries"]]
        entries = [e for e in parsed if e is not None]
        return sorted(entries, key=lambda e: e.port)

    def delete(self, port: int) -> None:
        data = _load(self._path)
        data["entries"] = [
            e for e in data["entries"] if not (isinstance(e, dict) and e.get("port") == port)
        ]
        _atomic_write_text(self._path, json.dumps(data, indent=2))
