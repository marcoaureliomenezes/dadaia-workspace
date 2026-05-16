"""ServerRegistryService — port registry business logic."""

import hashlib
from datetime import UTC, datetime, timedelta

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

    def _sweep(self) -> list[PortEntry]:
        stale = [e for e in self._store.list_all() if _is_stale(e, self._probe)]
        for e in stale:
            self._store.delete(e.port)
        return stale

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

    def clean(self, dry_run: bool = False) -> list[PortEntry]:
        stale = [e for e in self._store.list_all() if _is_stale(e, self._probe)]
        if not dry_run:
            for e in stale:
                self._store.delete(e.port)
        return stale

    def next_port(
        self,
        project: str,
        min_port: int = _DEFAULT_MIN_PORT,
        max_port: int = _DEFAULT_MAX_PORT,
    ) -> tuple[int, bool]:
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
