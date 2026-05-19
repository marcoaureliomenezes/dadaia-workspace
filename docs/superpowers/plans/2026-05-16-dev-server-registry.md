# Dev Server Port Registry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `dadaia server` CLI commands, a JSON port registry, and a bookmarkable web dashboard so AI agents and the operator always know which project is running on which port.

**Architecture:** Pure 4-layer pattern (CLI → Features → Core ← Infrastructure) with no new dependencies. State lives in `.dadaia/states/server_registry.json`, written atomically via `os.replace()`. Staleness detection uses `os.kill(pid, 0)` and TTL expiry. A `ProcessProbe` abstraction keeps all tests CI-safe (no real ports needed).

**Tech Stack:** Python 3.12+, Typer, Rich, `http.server` (stdlib dashboard), pytest + `typer.testing.CliRunner`.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| CREATE | `dadaia_workspace/core/models/server_registry.py` | `PortEntry` frozen dataclass, `PortStatus` StrEnum |
| AMEND | `dadaia_workspace/core/exceptions.py` | `PortConflictError`, `PortNotRegisteredError` |
| CREATE | `dadaia_workspace/core/protocols/server_registry_store.py` | `ServerRegistryStore` Protocol |
| CREATE | `dadaia_workspace/core/protocols/process_probe.py` | `ProcessProbe` Protocol |
| CREATE | `dadaia_workspace/infrastructure/json_server_registry_store.py` | Atomic JSON CRUD |
| AMEND | `tests/fakes.py` | `FakeServerRegistryStore`, `FakeProcessProbe` |
| CREATE | `dadaia_workspace/features/server_registry/__init__.py` | Package marker |
| CREATE | `dadaia_workspace/features/server_registry/service.py` | `ServerRegistryService` |
| CREATE | `dadaia_workspace/features/server_registry/dashboard.py` | `DashboardHandler`, `render_html()` |
| AMEND | `dadaia_workspace/features/workspace/service.py` | Init `server_registry.json` on `dadaia init` |
| CREATE | `dadaia_workspace/cli/commands/server.py` | `dadaia server` Typer group (7 subcommands) |
| AMEND | `dadaia_workspace/cli/main.py` | Register `server` sub-app |
| AMEND | `dadaia_workspace/container.py` | `build_server_registry_service()` |
| CREATE | `dadaia_workspace/public/skills/dev-server-registry/SKILL.md` | Agent protocol skill |
| CREATE | `tests/unit/test_json_server_registry_store.py` | Store unit tests |
| CREATE | `tests/unit/test_server_registry_service.py` | Service unit tests |
| CREATE | `tests/unit/test_dashboard.py` | Dashboard render unit tests |
| CREATE | `tests/integration/test_cli_server.py` | CLI integration tests |
| CREATE | `tests/e2e/features/test_server_port_registry.py` | E2E acceptance tests |

---

## Task 1: Domain Models and Exceptions

**Files:**
- Create: `dadaia_workspace/core/models/server_registry.py`
- Modify: `dadaia_workspace/core/exceptions.py`

No tests needed — pure data definitions. Validate by importing in the Python REPL.

- [ ] **Step 1.1: Create `dadaia_workspace/core/models/server_registry.py`**

```python
"""Server registry domain models."""

from dataclasses import dataclass
from enum import StrEnum


class PortStatus(StrEnum):
    ACTIVE = "active"
    STALE = "stale"


@dataclass(frozen=True)
class PortEntry:
    port: int
    project: str
    reserved_at: str
    expires_at: str
    url: str = ""
    pid: int | None = None
    description: str | None = None
```

- [ ] **Step 1.2: Add exceptions to `dadaia_workspace/core/exceptions.py`**

Append at the end of the file:

```python
class PortConflictError(DadaiaError):
    """Raised when a port is already registered as active by a different project."""


class PortNotRegisteredError(DadaiaError):
    """Raised when an operation targets a port not present in the registry."""
```

- [ ] **Step 1.3: Verify import**

```bash
cd /home/marco/workspace/dadaia/repos/dadaia-workspace
poetry run python -c "
from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.exceptions import PortConflictError, PortNotRegisteredError
e = PortEntry(port=3000, project='portifolio', reserved_at='2026-01-01T00:00:00Z', expires_at='2026-01-01T08:00:00Z')
print(e, PortStatus.ACTIVE, PortStatus.STALE)
print('OK')
"
```

Expected: prints `PortEntry(...)` then `OK`.

- [ ] **Step 1.4: Commit**

```bash
git add dadaia_workspace/core/models/server_registry.py dadaia_workspace/core/exceptions.py
git commit -m "feat(server-registry): add PortEntry model and conflict exceptions"
```

---

## Task 2: Protocols

**Files:**
- Create: `dadaia_workspace/core/protocols/server_registry_store.py`
- Create: `dadaia_workspace/core/protocols/process_probe.py`

- [ ] **Step 2.1: Create `dadaia_workspace/core/protocols/server_registry_store.py`**

```python
"""ServerRegistryStore Protocol — port registry CRUD."""

from typing import Protocol

from dadaia_workspace.core.models.server_registry import PortEntry


class ServerRegistryStore(Protocol):
    def save(self, entry: PortEntry) -> None: ...
    def update(self, entry: PortEntry) -> None: ...
    def get(self, port: int) -> PortEntry | None: ...
    def list_all(self) -> list[PortEntry]: ...
    def delete(self, port: int) -> None: ...
```

- [ ] **Step 2.2: Create `dadaia_workspace/core/protocols/process_probe.py`**

```python
"""ProcessProbe Protocol — PID liveness check abstraction."""

import os
from typing import Protocol


class ProcessProbe(Protocol):
    def is_pid_alive(self, pid: int) -> bool: ...


class OsProcessProbe:
    """Production implementation using os.kill(pid, 0)."""

    def is_pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False
```

`PermissionError` means the process exists but belongs to another user — treat as alive.

- [ ] **Step 2.3: Verify import**

```bash
poetry run python -c "
from dadaia_workspace.core.protocols.server_registry_store import ServerRegistryStore
from dadaia_workspace.core.protocols.process_probe import ProcessProbe, OsProcessProbe
probe = OsProcessProbe()
import os
print('self alive:', probe.is_pid_alive(os.getpid()))
print('dead pid:', probe.is_pid_alive(999999999))
"
```

Expected: `self alive: True`, `dead pid: False`.

- [ ] **Step 2.4: Commit**

```bash
git add dadaia_workspace/core/protocols/server_registry_store.py dadaia_workspace/core/protocols/process_probe.py
git commit -m "feat(server-registry): add ServerRegistryStore and ProcessProbe protocols"
```

---

## Task 3: Fakes

**Files:**
- Modify: `tests/fakes.py`

- [ ] **Step 3.1: Add `FakeServerRegistryStore` and `FakeProcessProbe` to `tests/fakes.py`**

Add these two classes at the end of `tests/fakes.py`:

```python
from dadaia_workspace.core.models.server_registry import PortEntry


class FakeServerRegistryStore:
    """In-memory ServerRegistryStore — keyed by port number."""

    def __init__(self) -> None:
        self._store: dict[int, PortEntry] = {}

    def save(self, entry: PortEntry) -> None:
        self._store[entry.port] = entry

    def update(self, entry: PortEntry) -> None:
        self._store[entry.port] = entry

    def get(self, port: int) -> PortEntry | None:
        return self._store.get(port)

    def list_all(self) -> list[PortEntry]:
        return sorted(self._store.values(), key=lambda e: e.port)

    def delete(self, port: int) -> None:
        self._store.pop(port, None)

    def count(self) -> int:
        return len(self._store)


class FakeProcessProbe:
    """Controllable probe — add PIDs to _alive_pids to simulate live processes."""

    def __init__(self) -> None:
        self._alive_pids: set[int] = set()

    def is_pid_alive(self, pid: int) -> bool:
        return pid in self._alive_pids
```

- [ ] **Step 3.2: Verify fakes import cleanly**

```bash
poetry run python -c "
from tests.fakes import FakeServerRegistryStore, FakeProcessProbe
from dadaia_workspace.core.models.server_registry import PortEntry
s = FakeServerRegistryStore()
e = PortEntry(port=3000, project='p', reserved_at='t', expires_at='t')
s.save(e)
assert s.get(3000) == e
probe = FakeProcessProbe()
probe._alive_pids.add(99)
assert probe.is_pid_alive(99)
assert not probe.is_pid_alive(1)
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3.3: Commit**

```bash
git add tests/fakes.py
git commit -m "test(server-registry): add FakeServerRegistryStore and FakeProcessProbe"
```

---

## Task 4: Infrastructure Store + Unit Tests (TDD)

**Files:**
- Create: `dadaia_workspace/infrastructure/json_server_registry_store.py`
- Create: `tests/unit/test_json_server_registry_store.py`

- [ ] **Step 4.1: Write failing tests first**

Create `tests/unit/test_json_server_registry_store.py`:

```python
"""Unit tests for JsonServerRegistryStore."""

from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore


def _entry(port: int = 3000, project: str = "portifolio") -> PortEntry:
    return PortEntry(
        port=port,
        project=project,
        reserved_at="2026-05-16T10:00:00Z",
        expires_at="2026-05-16T18:00:00Z",
    )


def test_list_all_empty_when_no_file(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    assert store.list_all() == []


def test_get_returns_none_when_missing(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    assert store.get(8000) is None


def test_save_and_get_roundtrip(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    entry = _entry(3000)
    store.save(entry)
    fetched = store.get(3000)
    assert fetched is not None
    assert fetched.port == 3000
    assert fetched.project == "portifolio"


def test_save_persists_to_disk(tmp_path: Path) -> None:
    JsonServerRegistryStore(tmp_path).save(_entry(3000))
    store2 = JsonServerRegistryStore(tmp_path)
    assert store2.get(3000) is not None


def test_update_replaces_entry(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3000, "old-project"))
    store.update(_entry(3000, "new-project"))
    assert store.get(3000).project == "new-project"  # type: ignore[union-attr]


def test_delete_removes_entry(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3000))
    store.delete(3000)
    assert store.get(3000) is None
    assert store.list_all() == []


def test_delete_nonexistent_is_noop(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.delete(9999)  # must not raise


def test_list_all_sorted_by_port(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3002))
    store.save(_entry(3000))
    store.save(_entry(3001))
    ports = [e.port for e in store.list_all()]
    assert ports == [3000, 3001, 3002]


def test_optional_fields_preserved(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    entry = PortEntry(
        port=3000,
        project="portifolio",
        reserved_at="2026-05-16T10:00:00Z",
        expires_at="2026-05-16T18:00:00Z",
        url="http://0.0.0.0:3000",
        pid=12345,
        description="Vite dev server",
    )
    store.save(entry)
    fetched = store.get(3000)
    assert fetched is not None
    assert fetched.url == "http://0.0.0.0:3000"
    assert fetched.pid == 12345
    assert fetched.description == "Vite dev server"


def test_atomic_write_no_tmp_file_remains(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3000))
    tmp_file = tmp_path / "server_registry.tmp"
    assert not tmp_file.exists()


def test_version_field_written_to_disk(tmp_path: Path) -> None:
    import json
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3000))
    raw = json.loads((tmp_path / "server_registry.json").read_text())
    assert raw["version"] == "1"
```

- [ ] **Step 4.2: Run tests — verify they all fail**

```bash
poetry run pytest tests/unit/test_json_server_registry_store.py -v
```

Expected: `ImportError` — `json_server_registry_store` does not exist yet.

- [ ] **Step 4.3: Implement `dadaia_workspace/infrastructure/json_server_registry_store.py`**

```python
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
            _to_dict(entry) if e["port"] == entry.port else e
            for e in data["entries"]
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
```

- [ ] **Step 4.4: Run tests — verify they all pass**

```bash
poetry run pytest tests/unit/test_json_server_registry_store.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 4.5: Commit**

```bash
git add dadaia_workspace/infrastructure/json_server_registry_store.py tests/unit/test_json_server_registry_store.py
git commit -m "feat(server-registry): JsonServerRegistryStore with atomic write + unit tests"
```

---

## Task 5: Service + Unit Tests (TDD)

**Files:**
- Create: `dadaia_workspace/features/server_registry/__init__.py`
- Create: `dadaia_workspace/features/server_registry/service.py`
- Create: `tests/unit/test_server_registry_service.py`

- [ ] **Step 5.1: Create empty `__init__.py`**

```bash
touch dadaia_workspace/features/server_registry/__init__.py
```

- [ ] **Step 5.2: Write failing service tests**

Create `tests/unit/test_server_registry_service.py`:

```python
"""Unit tests for ServerRegistryService."""

import pytest

from dadaia_workspace.core.exceptions import PortConflictError, PortNotRegisteredError
from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.features.server_registry.service import ServerRegistryService
from tests.fakes import FakeProcessProbe, FakeServerRegistryStore


def _svc(store: FakeServerRegistryStore | None = None, probe: FakeProcessProbe | None = None) -> ServerRegistryService:
    return ServerRegistryService(
        store=store or FakeServerRegistryStore(),
        probe=probe or FakeProcessProbe(),
    )


def _entry(port: int = 3000, project: str = "portifolio", pid: int | None = None) -> PortEntry:
    return PortEntry(
        port=port,
        project=project,
        reserved_at="2026-05-16T10:00:00Z",
        expires_at="2099-12-31T23:59:59Z",  # far future — not stale by TTL
        pid=pid,
    )


# ------------------------------------------------------------------ register

def test_register_saves_entry() -> None:
    store = FakeServerRegistryStore()
    svc = _svc(store)
    svc.register(port=3000, project="portifolio")
    assert store.get(3000) is not None
    assert store.get(3000).project == "portifolio"  # type: ignore[union-attr]


def test_register_sets_url_default() -> None:
    store = FakeServerRegistryStore()
    svc = _svc(store)
    svc.register(port=3000, project="portifolio")
    entry = store.get(3000)
    assert entry is not None
    assert entry.url == "http://localhost:3000"


def test_register_conflict_raises_port_conflict_error() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3000, "portifolio", pid=99))
    svc = _svc(store, probe)
    with pytest.raises(PortConflictError, match="portifolio"):
        svc.register(port=3000, project="portifolio-wave6")


def test_register_same_project_same_port_is_idempotent() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3000, "portifolio", pid=99))
    svc = _svc(store, probe)
    svc.register(port=3000, project="portifolio")  # must not raise
    assert store.count() == 1


def test_register_stale_entry_can_be_overwritten() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    # pid=99 is NOT in alive_pids → stale
    store.save(_entry(3000, "portifolio", pid=99))
    svc = _svc(store, probe)
    svc.register(port=3000, project="portifolio-wave6")
    assert store.get(3000).project == "portifolio-wave6"  # type: ignore[union-attr]


def test_register_expired_ttl_entry_can_be_overwritten() -> None:
    store = FakeServerRegistryStore()
    expired = PortEntry(
        port=3000,
        project="portifolio",
        reserved_at="2020-01-01T00:00:00Z",
        expires_at="2020-01-01T08:00:00Z",  # expired
    )
    store.save(expired)
    svc = _svc(store)
    svc.register(port=3000, project="portifolio-wave6")
    assert store.get(3000).project == "portifolio-wave6"  # type: ignore[union-attr]


# ------------------------------------------------------------------ release

def test_release_removes_entry() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "portifolio"))
    svc = _svc(store)
    svc.release(port=3000)
    assert store.get(3000) is None


def test_release_with_wrong_project_raises() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "portifolio"))
    svc = _svc(store)
    with pytest.raises(PortConflictError, match="portifolio"):
        svc.release(port=3000, project="portifolio-wave6")


def test_release_nonexistent_port_raises() -> None:
    svc = _svc()
    with pytest.raises(PortNotRegisteredError):
        svc.release(port=9999)


def test_release_all_for_project() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "portifolio"))
    store.save(_entry(3001, "portifolio"))
    store.save(_entry(3002, "other"))
    svc = _svc(store)
    svc.release_all(project="portifolio")
    assert store.get(3000) is None
    assert store.get(3001) is None
    assert store.get(3002) is not None


# ------------------------------------------------------------------ list_entries

def test_list_entries_returns_with_status() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3000, "portifolio", pid=99))
    svc = _svc(store, probe)
    result = svc.list_entries()
    assert len(result) == 1
    entry, status = result[0]
    assert entry.port == 3000
    assert status == PortStatus.ACTIVE


def test_list_entries_marks_dead_pid_as_stale() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()  # pid=99 NOT in alive_pids
    store.save(_entry(3000, "portifolio", pid=99))
    svc = _svc(store, probe)
    result = svc.list_entries()
    _, status = result[0]
    assert status == PortStatus.STALE


def test_list_entries_empty_registry() -> None:
    assert _svc().list_entries() == []


def test_list_entries_filter_by_project() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "portifolio"))
    store.save(_entry(3001, "dadaia-bots"))
    svc = _svc(store)
    result = svc.list_entries(project="portifolio")
    assert len(result) == 1
    assert result[0][0].project == "portifolio"


# ------------------------------------------------------------------ clean

def test_clean_removes_stale_pid_entries() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()  # pid=99 dead
    store.save(_entry(3000, "portifolio", pid=99))
    svc = _svc(store, probe)
    removed = svc.clean()
    assert len(removed) == 1
    assert removed[0].port == 3000
    assert store.get(3000) is None


def test_clean_removes_expired_ttl_entries() -> None:
    store = FakeServerRegistryStore()
    expired = PortEntry(
        port=3000,
        project="portifolio",
        reserved_at="2020-01-01T00:00:00Z",
        expires_at="2020-01-01T08:00:00Z",
    )
    store.save(expired)
    svc = _svc(store)
    removed = svc.clean()
    assert len(removed) == 1


def test_clean_dry_run_does_not_modify_store() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    store.save(_entry(3000, "portifolio", pid=99))
    svc = _svc(store, probe)
    removed = svc.clean(dry_run=True)
    assert len(removed) == 1
    assert store.get(3000) is not None  # not actually removed


def test_clean_keeps_alive_entries() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3000, "portifolio", pid=99))
    svc = _svc(store, probe)
    removed = svc.clean()
    assert removed == []
    assert store.get(3000) is not None


# ------------------------------------------------------------------ next_port

def test_next_port_returns_base_hash_port_when_free() -> None:
    svc = _svc()
    port, is_base = svc.next_port("dadaia-bots")
    assert port == 3537  # hash("dadaia-bots") % 1000 + 3000
    assert is_base is True


def test_next_port_returns_existing_if_already_registered() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3537, "dadaia-bots", pid=99))
    svc = _svc(store, probe)
    port, is_base = svc.next_port("dadaia-bots")
    assert port == 3537
    assert is_base is True


def test_next_port_increments_when_base_occupied_by_other() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    # Occupy dadaia-bots base port (3537) with a different project
    store.save(PortEntry(
        port=3537, project="other",
        reserved_at="2026-05-16T10:00:00Z",
        expires_at="2099-12-31T23:59:59Z",
        pid=99,
    ))
    svc = _svc(store, probe)
    port, is_base = svc.next_port("dadaia-bots")
    assert port != 3537
    assert port >= 3000
    assert port <= 3999
    assert is_base is False


def test_next_port_respects_custom_range() -> None:
    svc = _svc()
    port, _ = svc.next_port("dadaia-bots", min_port=4000, max_port=4099)
    assert 4000 <= port <= 4099
```

- [ ] **Step 5.3: Run tests — verify they fail**

```bash
poetry run pytest tests/unit/test_server_registry_service.py -v 2>&1 | head -20
```

Expected: `ImportError` — `service` module not found.

- [ ] **Step 5.4: Implement `dadaia_workspace/features/server_registry/service.py`**

```python
"""ServerRegistryService — port registry business logic."""

import hashlib
from datetime import UTC, datetime

from dadaia_workspace.core.exceptions import PortConflictError, PortNotRegisteredError
from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.protocols.process_probe import ProcessProbe
from dadaia_workspace.core.protocols.server_registry_store import ServerRegistryStore

_DEFAULT_TTL_HOURS = 8
_DEFAULT_MIN_PORT = 3000
_DEFAULT_MAX_PORT = 3999


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _fmt_dt(dt: datetime) -> str:
    return dt.isoformat()


def _base_port(project: str, min_port: int, max_port: int) -> int:
    digest = hashlib.md5(project.encode()).digest()
    offset = int.from_bytes(digest[:2], "big") % (max_port - min_port + 1)
    return min_port + offset


def _is_stale(entry: PortEntry, probe: ProcessProbe) -> bool:
    try:
        if _parse_dt(entry.expires_at) < _now_utc():
            return True
    except ValueError:
        pass
    if entry.pid is not None and not probe.is_pid_alive(entry.pid):
        return True
    return False


class ServerRegistryService:
    def __init__(self, store: ServerRegistryStore, probe: ProcessProbe) -> None:
        self._store = store
        self._probe = probe

    # ------------------------------------------------------------------ internal

    def _sweep(self) -> list[PortEntry]:
        """Remove stale entries; return list of swept entries."""
        stale = [e for e in self._store.list_all() if _is_stale(e, self._probe)]
        for e in stale:
            self._store.delete(e.port)
        return stale

    # ------------------------------------------------------------------ register

    def register(
        self,
        port: int,
        project: str,
        url: str = "",
        pid: int | None = None,
        ttl_hours: int = _DEFAULT_TTL_HOURS,
        description: str | None = None,
    ) -> PortEntry:
        self._sweep()
        existing = self._store.get(port)
        if existing is not None:
            if existing.project == project:
                return existing  # idempotent
            raise PortConflictError(
                f"Port {port} is already registered by project '{existing.project}'. "
                f"URL: {existing.url or f'http://localhost:{port}'}"
            )
        now = _now_utc()
        entry = PortEntry(
            port=port,
            project=project,
            reserved_at=_fmt_dt(now),
            expires_at=_fmt_dt(now.replace(hour=(now.hour + ttl_hours) % 24)
                               if ttl_hours < 24
                               else now.__class__(
                                   now.year, now.month, now.day + ttl_hours // 24,
                                   now.hour, now.minute, now.second, tzinfo=UTC
                               )),
            url=url or f"http://localhost:{port}",
            pid=pid,
            description=description,
        )
        # Use simple timedelta for expires_at
        from datetime import timedelta
        entry = PortEntry(
            port=port,
            project=project,
            reserved_at=_fmt_dt(now),
            expires_at=_fmt_dt(now + timedelta(hours=ttl_hours)),
            url=url or f"http://localhost:{port}",
            pid=pid,
            description=description,
        )
        self._store.save(entry)
        return entry

    # ------------------------------------------------------------------ release

    def release(self, port: int, project: str | None = None) -> None:
        entry = self._store.get(port)
        if entry is None:
            raise PortNotRegisteredError(f"Port {port} is not registered.")
        if project is not None and entry.project != project:
            raise PortConflictError(
                f"Port {port} belongs to project '{entry.project}', not '{project}'."
            )
        self._store.delete(port)

    def release_all(self, project: str) -> list[PortEntry]:
        entries = [e for e in self._store.list_all() if e.project == project]
        for e in entries:
            self._store.delete(e.port)
        return entries

    # ------------------------------------------------------------------ list / show

    def list_entries(
        self,
        project: str | None = None,
        include_stale: bool = True,
    ) -> list[tuple[PortEntry, PortStatus]]:
        entries = self._store.list_all()
        if project:
            entries = [e for e in entries if e.project == project]
        result = []
        for e in entries:
            status = PortStatus.STALE if _is_stale(e, self._probe) else PortStatus.ACTIVE
            if not include_stale and status == PortStatus.STALE:
                continue
            result.append((e, status))
        return result

    def show_project(self, project: str) -> list[tuple[PortEntry, PortStatus]]:
        return self.list_entries(project=project)

    # ------------------------------------------------------------------ clean

    def clean(self, dry_run: bool = False) -> list[PortEntry]:
        stale = [e for e in self._store.list_all() if _is_stale(e, self._probe)]
        if not dry_run:
            for e in stale:
                self._store.delete(e.port)
        return stale

    # ------------------------------------------------------------------ next_port

    def next_port(
        self,
        project: str,
        min_port: int = _DEFAULT_MIN_PORT,
        max_port: int = _DEFAULT_MAX_PORT,
    ) -> tuple[int, bool]:
        """Return (port, is_base_port). Idempotent if project already registered."""
        # If project already has a live entry, return its port
        active = [
            e for e in self._store.list_all()
            if e.project == project and not _is_stale(e, self._probe)
        ]
        if active:
            return active[0].port, True

        occupied = {
            e.port for e in self._store.list_all()
            if not _is_stale(e, self._probe)
        }
        base = _base_port(project, min_port, max_port)

        if base not in occupied:
            return base, True

        for port in range(min_port, max_port + 1):
            if port not in occupied:
                return port, False

        raise PortNotRegisteredError(
            f"No free ports in range [{min_port}, {max_port}]. "
            "Run 'dadaia server clean' to free stale entries."
        )
```

Note the `register` method has a redundant calculation — simplify it to use `timedelta` from the start. The final version:

```python
    def register(
        self,
        port: int,
        project: str,
        url: str = "",
        pid: int | None = None,
        ttl_hours: int = _DEFAULT_TTL_HOURS,
        description: str | None = None,
    ) -> PortEntry:
        from datetime import timedelta
        self._sweep()
        existing = self._store.get(port)
        if existing is not None:
            if existing.project == project:
                return existing
            raise PortConflictError(
                f"Port {port} is already registered by project '{existing.project}'. "
                f"URL: {existing.url or f'http://localhost:{port}'}"
            )
        now = _now_utc()
        entry = PortEntry(
            port=port,
            project=project,
            reserved_at=_fmt_dt(now),
            expires_at=_fmt_dt(now + timedelta(hours=ttl_hours)),
            url=url or f"http://localhost:{port}",
            pid=pid,
            description=description,
        )
        self._store.save(entry)
        return entry
```

Use this clean version in the actual file (do not duplicate the old `register` body).

- [ ] **Step 5.5: Run tests — verify they all pass**

```bash
poetry run pytest tests/unit/test_server_registry_service.py -v
```

Expected: all 22 tests PASS.

- [ ] **Step 5.6: Commit**

```bash
git add dadaia_workspace/features/server_registry/__init__.py dadaia_workspace/features/server_registry/service.py tests/unit/test_server_registry_service.py
git commit -m "feat(server-registry): ServerRegistryService with register/release/list/clean/next_port"
```

---

## Task 6: Dashboard + Unit Tests (TDD)

**Files:**
- Create: `dadaia_workspace/features/server_registry/dashboard.py`
- Create: `tests/unit/test_dashboard.py`

- [ ] **Step 6.1: Write failing dashboard tests**

Create `tests/unit/test_dashboard.py`:

```python
"""Unit tests for dashboard.render_html()."""

import json
from pathlib import Path

from dadaia_workspace.features.server_registry.dashboard import render_html


def _write_registry(path: Path, entries: list[dict]) -> None:  # type: ignore[type-arg]
    registry = {
        "version": "1",
        "range": {"min_port": 3000, "max_port": 3999},
        "entries": entries,
    }
    (path / "server_registry.json").write_text(json.dumps(registry))


def test_render_html_shows_project_name(tmp_path: Path) -> None:
    _write_registry(tmp_path, [
        {
            "port": 3000,
            "project": "portifolio",
            "url": "http://localhost:3000",
            "status": "active",
            "pid": None,
            "reserved_at": "2026-05-16T10:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
            "description": None,
        }
    ])
    html = render_html(tmp_path)
    assert "portifolio" in html


def test_render_html_shows_clickable_url(tmp_path: Path) -> None:
    _write_registry(tmp_path, [
        {
            "port": 3000,
            "project": "portifolio",
            "url": "http://localhost:3000",
            "status": "active",
            "pid": None,
            "reserved_at": "2026-05-16T10:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
            "description": None,
        }
    ])
    html = render_html(tmp_path)
    assert 'href="http://localhost:3000"' in html
    assert "http://localhost:3000" in html


def test_render_html_empty_registry_shows_message(tmp_path: Path) -> None:
    _write_registry(tmp_path, [])
    html = render_html(tmp_path)
    assert "No servers registered" in html


def test_render_html_no_file_shows_message(tmp_path: Path) -> None:
    html = render_html(tmp_path)
    assert "No servers registered" in html


def test_render_html_includes_auto_refresh(tmp_path: Path) -> None:
    _write_registry(tmp_path, [])
    html = render_html(tmp_path)
    assert 'http-equiv="refresh"' in html
    assert 'content="5"' in html


def test_render_html_shows_description_when_present(tmp_path: Path) -> None:
    _write_registry(tmp_path, [
        {
            "port": 3000,
            "project": "portifolio",
            "url": "http://localhost:3000",
            "status": "active",
            "pid": None,
            "reserved_at": "2026-05-16T10:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
            "description": "Vite dev server",
        }
    ])
    html = render_html(tmp_path)
    assert "Vite dev server" in html
```

- [ ] **Step 6.2: Run tests — verify they fail**

```bash
poetry run pytest tests/unit/test_dashboard.py -v 2>&1 | head -10
```

Expected: `ImportError` — `dashboard` not found.

- [ ] **Step 6.3: Implement `dadaia_workspace/features/server_registry/dashboard.py`**

```python
"""Dashboard HTTP handler for the server registry."""

import http.server
import json
from pathlib import Path


def render_html(states_dir: Path) -> str:
    """Read server_registry.json and return a full HTML page."""
    registry_path = states_dir / "server_registry.json"
    entries: list[dict] = []  # type: ignore[type-arg]
    if registry_path.exists():
        try:
            data = json.loads(registry_path.read_text())
            entries = data.get("entries", [])
        except (json.JSONDecodeError, OSError):
            entries = []

    if entries:
        rows = "\n".join(
            f"""
            <tr>
              <td><strong>{e.get("project", "—")}</strong></td>
              <td><a href="{e.get("url", "#")}" target="_blank">{e.get("url", "—")}</a></td>
              <td>{"● running" if e.get("status") == "active" else "○ stale"}</td>
              <td>{e.get("description") or "—"}</td>
              <td>{e.get("reserved_at", "—")[:19].replace("T", " ")}</td>
            </tr>"""
            for e in entries
        )
        body = f"""
        <table>
          <thead>
            <tr>
              <th>Project</th><th>URL</th><th>Status</th>
              <th>Description</th><th>Since</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""
    else:
        body = "<p class='empty'>No servers registered.</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="5">
  <title>dadaia server registry</title>
  <style>
    body {{ font-family: monospace; padding: 2rem; background: #111; color: #eee; }}
    h1 {{ color: #7ec8e3; margin-bottom: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ text-align: left; padding: 0.5rem 1rem; border-bottom: 1px solid #333; }}
    th {{ color: #aaa; font-weight: normal; text-transform: uppercase; font-size: 0.8rem; }}
    a {{ color: #7ec8e3; }}
    .empty {{ color: #666; }}
  </style>
</head>
<body>
  <h1>dadaia · server registry</h1>
  {body}
</body>
</html>"""


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    states_dir: Path  # set as class attribute before serving

    def do_GET(self) -> None:
        html = render_html(self.states_dir)
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # suppress per-request logs
```

- [ ] **Step 6.4: Run tests — verify they all pass**

```bash
poetry run pytest tests/unit/test_dashboard.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 6.5: Commit**

```bash
git add dadaia_workspace/features/server_registry/dashboard.py tests/unit/test_dashboard.py
git commit -m "feat(server-registry): DashboardHandler with render_html and auto-refresh"
```

---

## Task 7: Workspace Init Update + Tests

**Files:**
- Modify: `dadaia_workspace/features/workspace/service.py`

The `WorkspaceService.init()` must create `server_registry.json` if absent.

- [ ] **Step 7.1: Write the failing test**

Add to `tests/unit/test_workspace_service.py` (existing file — append this test):

```python
def test_init_creates_server_registry_json(tmp_path: Path) -> None:
    WorkspaceService(
        public_assets=FakePublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    ).init(tmp_path)
    registry = tmp_path / ".dadaia" / "states" / "server_registry.json"
    assert registry.exists()
    import json
    data = json.loads(registry.read_text())
    assert data["version"] == "1"
    assert data["entries"] == []
```

- [ ] **Step 7.2: Run — verify it fails**

```bash
poetry run pytest tests/unit/test_workspace_service.py::test_init_creates_server_registry_json -v
```

Expected: FAIL — `server_registry.json` not created.

- [ ] **Step 7.3: Update `dadaia_workspace/features/workspace/service.py`**

Add the constant near `_EMPTY_CONTEXTS`:

```python
_EMPTY_SERVER_REGISTRY = {
    "version": "1",
    "range": {"min_port": 3000, "max_port": 3999},
    "entries": [],
}
```

In the `init()` method, after the existing `_init_json_file` calls, add:

```python
        self._init_json_file(workspace.states_dir / "server_registry.json", _EMPTY_SERVER_REGISTRY)
```

- [ ] **Step 7.4: Run — verify it passes**

```bash
poetry run pytest tests/unit/test_workspace_service.py -v
```

Expected: all tests PASS.

- [ ] **Step 7.5: Commit**

```bash
git add dadaia_workspace/features/workspace/service.py tests/unit/test_workspace_service.py
git commit -m "feat(server-registry): dadaia init creates server_registry.json"
```

---

## Task 8: Container Wiring

**Files:**
- Modify: `dadaia_workspace/container.py`

- [ ] **Step 8.1: Add `build_server_registry_service()` to `container.py`**

Add imports at the top of `container.py`:

```python
from dadaia_workspace.features.server_registry.service import ServerRegistryService
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore
from dadaia_workspace.core.protocols.process_probe import OsProcessProbe
```

Add function at the end of `container.py`:

```python
def build_server_registry_service(workspace_root: Path) -> ServerRegistryService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return ServerRegistryService(
        store=JsonServerRegistryStore(states),
        probe=OsProcessProbe(),
    )
```

- [ ] **Step 8.2: Verify import**

```bash
poetry run python -c "
from dadaia_workspace import container
from pathlib import Path
import tempfile, os
# just test the import — don't call it (needs initialized workspace)
print('container.build_server_registry_service:', container.build_server_registry_service)
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 8.3: Commit**

```bash
git add dadaia_workspace/container.py
git commit -m "feat(server-registry): wire ServerRegistryService in container"
```

---

## Task 9: CLI Commands

**Files:**
- Create: `dadaia_workspace/cli/commands/server.py`
- Modify: `dadaia_workspace/cli/main.py`

- [ ] **Step 9.1: Create `dadaia_workspace/cli/commands/server.py`**

```python
"""dadaia server subcommands — port registry management."""

import json
import webbrowser
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import (
    PortConflictError,
    PortNotRegisteredError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.models.server_registry import PortStatus
from dadaia_workspace.features.server_registry.service import ServerRegistryService

app = typer.Typer(help="Manage the dev server port registry.")
console = Console()
err_console = Console(stderr=True)


def _resolve_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".dadaia").exists():
            return parent
    return cwd


def _svc() -> ServerRegistryService:
    try:
        return container.build_server_registry_service(_resolve_workspace())
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(1) from None


# ------------------------------------------------------------------ list

@app.command(name="list")
def list_servers(
    project: str | None = typer.Option(None, "--project", help="Filter by project name"),
    status: str = typer.Option("active", "--status", help="Filter: active | stale | all"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON array"),
) -> None:
    """List registered dev servers."""
    include_stale = status in ("stale", "all")
    entries = _svc().list_entries(project=project, include_stale=True)

    if status == "active":
        entries = [(e, s) for e, s in entries if s == PortStatus.ACTIVE]
    elif status == "stale":
        entries = [(e, s) for e, s in entries if s == PortStatus.STALE]

    if json_output:
        data = [
            {
                "port": e.port,
                "project": e.project,
                "url": e.url or f"http://localhost:{e.port}",
                "status": s.value,
                "pid": e.pid,
                "reserved_at": e.reserved_at,
                "expires_at": e.expires_at,
                "description": e.description,
            }
            for e, s in entries
        ]
        print(json.dumps(data, indent=2))
        return

    if not entries:
        console.print("[dim]No servers registered.[/dim]")
        return

    table = Table(title="Server Registry")
    table.add_column("Port", style="bold")
    table.add_column("Project")
    table.add_column("URL")
    table.add_column("Status")
    table.add_column("Description")

    status_style = {
        PortStatus.ACTIVE: "[green]● running[/green]",
        PortStatus.STALE: "[dim]○ stale[/dim]",
    }

    for e, s in entries:
        table.add_row(
            str(e.port),
            e.project,
            e.url or f"http://localhost:{e.port}",
            status_style.get(s, s.value),
            e.description or "—",
        )
    console.print(table)


# ------------------------------------------------------------------ next

@app.command()
def next(
    project: str = typer.Option(..., "--project", help="Project name"),
    min_port: int = typer.Option(3000, "--min-port"),
    max_port: int = typer.Option(3999, "--max-port"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Suggest the next available port for a project (deterministic, does not register)."""
    try:
        port, is_base = _svc().next_port(project, min_port=min_port, max_port=max_port)
    except PortNotRegisteredError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    url = f"http://localhost:{port}"
    if json_output:
        print(json.dumps({"port": port, "url": url, "is_base_port": is_base}, indent=2))
        return

    if not is_base:
        console.print(f"[yellow]Note:[/yellow] base port for '{project}' was occupied; using next free port.")
    console.print(f"[green]►[/green] Port [bold]{port}[/bold]  →  {url}")


# ------------------------------------------------------------------ register

@app.command()
def register(
    port: int = typer.Option(..., "--port"),
    project: str = typer.Option(..., "--project"),
    url: str = typer.Option("", "--url"),
    pid: int | None = typer.Option(None, "--pid"),
    ttl: int = typer.Option(8, "--ttl", help="Hours until entry expires"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Register a port for a project."""
    try:
        entry = _svc().register(
            port=port, project=project, url=url, pid=pid,
            ttl_hours=ttl, description=description,
        )
        console.print(
            f"[green]✓[/green] Port [bold]{entry.port}[/bold] registered for '{entry.project}'  →  {entry.url}"
        )
    except PortConflictError as e:
        err_console.print(f"[red]Conflict:[/red] {e}")
        raise typer.Exit(1) from None


# ------------------------------------------------------------------ release

@app.command()
def release(
    port: int | None = typer.Option(None, "--port"),
    project: str | None = typer.Option(None, "--project"),
) -> None:
    """Release a port (or all ports for a project)."""
    svc = _svc()
    if port is None and project is None:
        err_console.print("[red]Error:[/red] Provide --port and/or --project.")
        raise typer.Exit(1) from None

    try:
        if project is not None and port is None:
            released = svc.release_all(project=project)
            if not released:
                console.print(f"[dim]No registered ports for project '{project}'.[/dim]")
            else:
                for e in released:
                    console.print(f"[green]✓[/green] Released port {e.port} ('{e.project}')")
        else:
            svc.release(port=port, project=project)  # type: ignore[arg-type]
            console.print(f"[green]✓[/green] Port [bold]{port}[/bold] released")
    except (PortConflictError, PortNotRegisteredError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


# ------------------------------------------------------------------ show

@app.command()
def show(
    project: str = typer.Option(..., "--project"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show registered servers for a project."""
    entries = _svc().show_project(project)
    if not entries:
        console.print(f"[dim]No servers registered for '{project}'.[/dim]")
        console.print(
            f"  Tip: run [bold]dadaia server next --project {project}[/bold] to get a port."
        )
        return

    if json_output:
        data = [
            {
                "port": e.port,
                "project": e.project,
                "url": e.url or f"http://localhost:{e.port}",
                "status": s.value,
                "pid": e.pid,
                "reserved_at": e.reserved_at,
                "expires_at": e.expires_at,
                "description": e.description,
            }
            for e, s in entries
        ]
        print(json.dumps(data, indent=2))
        return

    for e, s in entries:
        status_label = "[green]● running[/green]" if s == PortStatus.ACTIVE else "[dim]○ stale[/dim]"
        console.print(f"  Port [bold]{e.port}[/bold]  {e.url or f'http://localhost:{e.port}'}  {status_label}")
        if e.description:
            console.print(f"  [dim]{e.description}[/dim]")


# ------------------------------------------------------------------ clean

@app.command()
def clean(
    dry_run: bool = typer.Option(False, "--dry-run", help="List stale entries without removing"),
) -> None:
    """Remove stale port entries (dead PID or expired TTL)."""
    removed = _svc().clean(dry_run=dry_run)
    if not removed:
        console.print("[dim]No stale entries found.[/dim]")
        return
    verb = "Would remove" if dry_run else "Removed"
    for e in removed:
        console.print(f"[yellow]{verb}:[/yellow] port {e.port} ('{e.project}')")


# ------------------------------------------------------------------ dashboard

@app.command()
def dashboard(
    port: int = typer.Option(4999, "--port", help="Dashboard HTTP port"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open browser automatically"),
) -> None:
    """Start the server registry dashboard (bookmarkable URL)."""
    import http.server

    from dadaia_workspace.features.server_registry.dashboard import DashboardHandler

    ws = _resolve_workspace()
    states_dir = ws / ".dadaia" / "states"
    DashboardHandler.states_dir = states_dir

    url = f"http://localhost:{port}"
    console.print(f"[green]►[/green] Serving registry dashboard at [bold]{url}[/bold]")
    console.print("  Press [bold]Ctrl+C[/bold] to stop.")

    if not no_open:
        webbrowser.open(url)

    server = http.server.HTTPServer(("localhost", port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        console.print("\n[dim]Dashboard stopped.[/dim]")
```

- [ ] **Step 9.2: Register the sub-app in `dadaia_workspace/cli/main.py`**

Add import:

```python
from dadaia_workspace.cli.commands import server
```

Add line after the last `app.add_typer`:

```python
app.add_typer(server.app, name="server")
```

- [ ] **Step 9.3: Smoke-test CLI**

```bash
poetry run dadaia server --help
```

Expected: shows list of 7 subcommands (`list`, `next`, `register`, `release`, `show`, `clean`, `dashboard`).

- [ ] **Step 9.4: Commit**

```bash
git add dadaia_workspace/cli/commands/server.py dadaia_workspace/cli/main.py
git commit -m "feat(server-registry): dadaia server CLI with 7 subcommands"
```

---

## Task 10: Integration Tests

**Files:**
- Create: `tests/integration/test_cli_server.py`

- [ ] **Step 10.1: Write integration tests**

```python
"""dadaia server CLI — integration tests using a real initialized workspace."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_server_list_empty_registry(workspace: Path) -> None:
    result = _runner.invoke(app, ["server", "list"])
    assert result.exit_code == 0, result.output
    assert "No servers registered" in result.output


def test_server_register_creates_entry(workspace: Path) -> None:
    result = _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "portifolio"])
    assert result.exit_code == 0, result.output
    assert "3000" in result.output
    assert "portifolio" in result.output


def test_server_list_shows_registered_entry(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "portifolio"])
    result = _runner.invoke(app, ["server", "list"])
    assert result.exit_code == 0, result.output
    assert "portifolio" in result.output
    assert "3000" in result.output


def test_server_list_json_returns_valid_array(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "portifolio"])
    result = _runner.invoke(app, ["server", "list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["port"] == 3000
    assert data[0]["project"] == "portifolio"
    assert "status" in data[0]


def test_server_register_conflict_exits_nonzero(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "portifolio", "--pid", "1"])
    result = _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "portifolio-wave6"])
    assert result.exit_code != 0


def test_server_release_removes_entry(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "portifolio"])
    result = _runner.invoke(app, ["server", "release", "--port", "3000"])
    assert result.exit_code == 0, result.output
    list_result = _runner.invoke(app, ["server", "list"])
    assert "portifolio" not in list_result.output


def test_server_release_nonexistent_exits_nonzero(workspace: Path) -> None:
    result = _runner.invoke(app, ["server", "release", "--port", "9999"])
    assert result.exit_code != 0


def test_server_next_returns_json(workspace: Path) -> None:
    result = _runner.invoke(app, ["server", "next", "--project", "dadaia-bots", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["port"] == 3537
    assert data["url"] == "http://localhost:3537"
    assert data["is_base_port"] is True


def test_server_next_idempotent_when_already_registered(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3537", "--project", "dadaia-bots"])
    result = _runner.invoke(app, ["server", "next", "--project", "dadaia-bots", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["port"] == 3537


def test_server_show_no_entry_prints_tip(workspace: Path) -> None:
    result = _runner.invoke(app, ["server", "show", "--project", "portifolio"])
    assert result.exit_code == 0, result.output
    assert "No servers registered" in result.output
    assert "dadaia server next" in result.output


def test_server_show_json_returns_entries(workspace: Path) -> None:
    _runner.invoke(app, ["server", "register", "--port", "3000", "--project", "portifolio"])
    result = _runner.invoke(app, ["server", "show", "--project", "portifolio", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["port"] == 3000


def test_server_clean_dry_run_reports_stale_without_removing(workspace: Path) -> None:
    import json as _json
    registry_path = workspace / ".dadaia" / "states" / "server_registry.json"
    data = _json.loads(registry_path.read_text())
    data["entries"].append({
        "port": 3000, "project": "portifolio", "url": "http://localhost:3000",
        "status": "active", "pid": None,
        "reserved_at": "2020-01-01T00:00:00Z",
        "expires_at": "2020-01-01T08:00:00Z",  # expired
        "description": None,
    })
    registry_path.write_text(_json.dumps(data))
    result = _runner.invoke(app, ["server", "clean", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "3000" in result.output
    data_after = _json.loads(registry_path.read_text())
    assert len(data_after["entries"]) == 1  # not removed


def test_server_clean_removes_expired_entries(workspace: Path) -> None:
    import json as _json
    registry_path = workspace / ".dadaia" / "states" / "server_registry.json"
    data = _json.loads(registry_path.read_text())
    data["entries"].append({
        "port": 3000, "project": "portifolio", "url": "http://localhost:3000",
        "status": "active", "pid": None,
        "reserved_at": "2020-01-01T00:00:00Z",
        "expires_at": "2020-01-01T08:00:00Z",
        "description": None,
    })
    registry_path.write_text(_json.dumps(data))
    result = _runner.invoke(app, ["server", "clean"])
    assert result.exit_code == 0, result.output
    data_after = _json.loads(registry_path.read_text())
    assert data_after["entries"] == []


def test_server_uninitialized_workspace_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["server", "list"])
    assert result.exit_code != 0
```

- [ ] **Step 10.2: Run integration tests**

```bash
poetry run pytest tests/integration/test_cli_server.py -v
```

Expected: all 14 tests PASS. If any fail, diagnose via the output — most failures will be in service logic or CLI wiring.

- [ ] **Step 10.3: Commit**

```bash
git add tests/integration/test_cli_server.py
git commit -m "test(server-registry): CLI integration tests for all 7 subcommands"
```

---

## Task 11: E2E Acceptance Tests

**Files:**
- Create: `tests/e2e/features/test_server_port_registry.py`

- [ ] **Step 11.1: Write E2E tests (one per user story)**

```python
"""E2E acceptance tests — Dev Server Port Registry (US-REG-001 to US-REG-007)."""

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import PortConflictError, PortNotRegisteredError
from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.features.server_registry.service import ServerRegistryService
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.fakes import FakeProcessProbe


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _build_svc(workspace: Path, probe: FakeProcessProbe) -> ServerRegistryService:
    states = workspace / ".dadaia" / "states"
    return ServerRegistryService(
        store=JsonServerRegistryStore(states),
        probe=probe,
    )


# ------------------------------------------------------------------ US-REG-001

def test_us1_agent_registers_port_before_starting_server(tmp_path: Path) -> None:
    """US-REG-001: Reservar porta antes de subir servidor."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    svc = _build_svc(ws, probe)

    entry = svc.register(port=3000, project="portifolio", pid=11111, description="Flask")
    probe._alive_pids.add(11111)

    assert entry.port == 3000
    assert entry.project == "portifolio"
    assert entry.url == "http://localhost:3000"
    assert entry.pid == 11111

    entries = svc.list_entries()
    assert len(entries) == 1
    _, status = entries[0]
    assert status == PortStatus.ACTIVE

    registry_file = ws / ".dadaia" / "states" / "server_registry.json"
    assert registry_file.exists()


def test_us1_conflict_raises_when_port_occupied(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(11111)
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=11111)
    with pytest.raises(PortConflictError) as exc_info:
        svc.register(port=3000, project="portifolio-wave6", pid=22222)
    assert "portifolio" in str(exc_info.value)

    entries = svc.list_entries()
    assert len(entries) == 1  # no partial write


# ------------------------------------------------------------------ US-REG-002

def test_us2_next_port_returns_deterministic_base(tmp_path: Path) -> None:
    """US-REG-002: Obter próxima porta de forma determinística."""
    ws = _init_workspace(tmp_path)
    svc = _build_svc(ws, FakeProcessProbe())

    port, is_base = svc.next_port("dadaia-bots")
    assert port == 3537
    assert is_base is True


def test_us2_next_port_idempotent_when_registered(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    svc = _build_svc(ws, probe)

    svc.register(port=3537, project="dadaia-bots", pid=99)
    probe._alive_pids.add(99)

    port1, _ = svc.next_port("dadaia-bots")
    port2, _ = svc.next_port("dadaia-bots")
    assert port1 == port2 == 3537


def test_us2_next_port_increments_when_base_occupied(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(88)
    svc = _build_svc(ws, probe)

    svc.register(port=3537, project="other-project", pid=88)
    port, is_base = svc.next_port("dadaia-bots")
    assert port != 3537
    assert is_base is False


# ------------------------------------------------------------------ US-REG-003

def test_us3_list_all_registered_servers(tmp_path: Path) -> None:
    """US-REG-003: Consultar registro completo de portas."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.update([1, 2, 3])
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=1)
    svc.register(port=3001, project="portifolio", pid=2, description="Vite")
    svc.register(port=3537, project="dadaia-bots", pid=3)

    entries = svc.list_entries()
    assert len(entries) == 3
    projects = {e.project for e, _ in entries}
    assert projects == {"portifolio", "dadaia-bots"}

    _, s = entries[0]
    assert s == PortStatus.ACTIVE


def test_us3_list_empty_returns_empty_list(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    svc = _build_svc(ws, FakeProcessProbe())
    assert svc.list_entries() == []


# ------------------------------------------------------------------ US-REG-004

def test_us4_release_port_on_shutdown(tmp_path: Path) -> None:
    """US-REG-004: Liberar porta ao encerrar servidor."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.update([1, 2])
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=1)
    svc.register(port=3001, project="portifolio", pid=2)

    svc.release(port=3000)

    entries = svc.list_entries()
    assert len(entries) == 1
    assert entries[0][0].port == 3001

    with pytest.raises(PortNotRegisteredError):
        svc.release(port=3000)  # already gone


# ------------------------------------------------------------------ US-REG-005

def test_us5_show_project_url(tmp_path: Path) -> None:
    """US-REG-005: Consultar URL de projeto específico."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    svc = _build_svc(ws, probe)

    svc.register(port=3003, project="dd-chain-explorer", pid=99)
    result = svc.show_project("dd-chain-explorer")

    assert len(result) == 1
    entry, status = result[0]
    assert entry.url == "http://localhost:3003"
    assert status == PortStatus.ACTIVE


def test_us5_show_project_empty_returns_empty_list(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    svc = _build_svc(ws, FakeProcessProbe())
    assert svc.show_project("dd-chain-explorer") == []


# ------------------------------------------------------------------ US-REG-006

def test_us6_clean_removes_stale_entries(tmp_path: Path) -> None:
    """US-REG-006: Limpar entradas obsoletas."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()  # no alive PIDs
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=99)
    removed = svc.clean()
    assert len(removed) == 1
    assert removed[0].port == 3000
    assert svc.list_entries() == []


def test_us6_clean_dry_run_does_not_remove(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=99)
    removed = svc.clean(dry_run=True)
    assert len(removed) == 1
    assert len(svc.list_entries()) == 1  # still there


# ------------------------------------------------------------------ US-REG-007

def test_us7_skill_file_exists_in_public(tmp_path: Path) -> None:
    """US-REG-007: Skill file exists in public/skills/dev-server-registry/."""
    from pathlib import Path as _Path
    import dadaia_workspace
    pkg_dir = _Path(dadaia_workspace.__file__).parent
    skill_file = pkg_dir / "public" / "skills" / "dev-server-registry" / "SKILL.md"
    assert skill_file.exists(), f"Missing: {skill_file}"
    content = skill_file.read_text()
    assert "dadaia server list" in content
    assert "dadaia server next" in content
    assert "dadaia server register" in content
    assert "dadaia server release" in content


# ------------------------------------------------------------------ Persistence

def test_registry_persists_across_service_restarts(tmp_path: Path) -> None:
    """Registry survives process restart (reads from disk)."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)

    svc_a = _build_svc(ws, probe)
    svc_a.register(port=3000, project="portifolio", pid=99)

    svc_b = _build_svc(ws, probe)
    entries = svc_b.list_entries()
    assert len(entries) == 1
    assert entries[0][0].port == 3000
```

- [ ] **Step 11.2: Run E2E tests**

```bash
poetry run pytest tests/e2e/features/test_server_port_registry.py -v
```

Expected: all tests PASS (including `test_us7_skill_file_exists_in_public`, which needs Task 12 to pass).

- [ ] **Step 11.3: Commit**

```bash
git add tests/e2e/features/test_server_port_registry.py
git commit -m "test(server-registry): E2E acceptance tests for all 7 user stories"
```

---

## Task 12: Skill File

**Files:**
- Create: `dadaia_workspace/public/skills/dev-server-registry/SKILL.md`

- [ ] **Step 12.1: Create skill directory and file**

```bash
mkdir -p dadaia_workspace/public/skills/dev-server-registry
```

Create `dadaia_workspace/public/skills/dev-server-registry/SKILL.md`:

```markdown
# Skill: dev-server-registry

Use this skill whenever you need to start, stop, or check a local dev server for any project in this workspace.

## Invariant

**Never start a server without registering its port first.** The registry at `.dadaia/states/server_registry.json` is the single source of truth.

## Protocol (4 steps)

### Step 1 — Inspect current state

```bash
dadaia server list
```

Shows all active servers across all projects. If your project already has an entry, use that port — do not start a second server.

### Step 2 — Get a safe port

```bash
dadaia server next --project <project-name> --json
```

Returns `{"port": N, "url": "http://localhost:N", "is_base_port": true|false}`.

- If `is_base_port: false`, the canonical port was occupied; use the returned port instead.
- Do NOT skip this step and pick a port manually.

### Step 3 — Start the server and register

Start the server on the port returned by `next`, then register:

```bash
dadaia server register --port <N> --project <project-name> --pid <pid> [--description "Vite dev server"]
```

`--pid` is optional but strongly recommended — enables automatic stale detection.

### Step 4 — Release when done

When stopping the server:

```bash
dadaia server release --port <N>
```

Or to release all ports for a project at once:

```bash
dadaia server release --project <project-name>
```

## Dashboard

To see all active servers in the browser (bookmarkable URL `http://localhost:4999`):

```bash
dadaia server dashboard
```

## Conflict handling

If `register` returns a `PortConflictError`:
1. Check `dadaia server list` — another agent may have registered first.
2. Run `dadaia server next` again to get the next available port.
3. If the conflict entry looks stale: `dadaia server clean` first, then retry.

## Quick reference

| Command | Purpose |
|---|---|
| `dadaia server list [--json]` | Show all registered servers |
| `dadaia server next --project <name>` | Get safe port (does not register) |
| `dadaia server register --port N --project <name>` | Register a port |
| `dadaia server release --port N` | Release a port |
| `dadaia server show --project <name>` | Show URL for a project |
| `dadaia server clean [--dry-run]` | Remove stale entries |
| `dadaia server dashboard` | Open browser index at http://localhost:4999 |
```

- [ ] **Step 12.2: Run the full test suite including E2E skill test**

```bash
poetry run pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests PASS, including `test_us7_skill_file_exists_in_public`.

- [ ] **Step 12.3: Run type and lint checks**

```bash
poetry run mypy dadaia_workspace/ --ignore-missing-imports && poetry run ruff check dadaia_workspace/ && poetry run ruff format --check dadaia_workspace/
```

Fix any issues before committing.

- [ ] **Step 12.4: Commit skill + full suite**

```bash
git add dadaia_workspace/public/skills/dev-server-registry/SKILL.md
git commit -m "feat(server-registry): add dev-server-registry skill for agent protocol"
```

---

## Task 13: Final Verification

- [ ] **Step 13.1: Run full test suite**

```bash
poetry run pytest tests/ -v --tb=short
```

Expected: all tests PASS. No regressions.

- [ ] **Step 13.2: Smoke-test CLI end-to-end in a real workspace**

```bash
# From the workspace root (where .dadaia/ exists)
dadaia server list
dadaia server next --project portifolio --json
dadaia server register --port 3000 --project portifolio --description "test"
dadaia server list
dadaia server show --project portifolio --json
dadaia server release --port 3000
dadaia server list
```

Expected: each command produces the correct output and no errors.

- [ ] **Step 13.3: Propagate skill to runtime projections**

```bash
dadaia public stage && dadaia public install --target all
dadaia public doctor
```

Expected: `[ok] skills/dev-server-registry` in all targets.

- [ ] **Step 13.4: Final commit**

```bash
git add -A
git commit -m "chore(server-registry): propagate dev-server-registry skill to runtime projections"
```

---

## Self-Review

**Spec coverage check:**

| User Story | Task |
|---|---|
| US-REG-001: Register port before starting server | Task 5 (service.register) + Task 9 (CLI register) + Task 11 (E2E) |
| US-REG-002: Deterministic next port | Task 5 (service.next_port) + Task 9 (CLI next) + Task 11 (E2E) |
| US-REG-003: List full registry | Task 5 (service.list_entries) + Task 9 (CLI list) + Task 11 (E2E) |
| US-REG-004: Release port on shutdown | Task 5 (service.release) + Task 9 (CLI release) + Task 11 (E2E) |
| US-REG-005: Show project URL | Task 5 (service.show_project) + Task 9 (CLI show) + Task 11 (E2E) |
| US-REG-006: Clean stale entries | Task 5 (service.clean) + Task 9 (CLI clean) + Task 11 (E2E) |
| US-REG-007: Skill for agents | Task 12 (SKILL.md) + Task 11 E2E test |
| US-REG-008: Dashboard web URL | Task 6 (DashboardHandler) + Task 9 (CLI dashboard) |
| FR-REG-002: init creates registry | Task 7 (workspace service) |
| FR-REG-023: No new dependencies | stdlib only confirmed throughout |

**No gaps found.**
