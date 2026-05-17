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


@dataclass(frozen=True)
class UnregisteredListener:
    """A TCP listener detected on the host that is NOT in the registry.

    Surfaced by ``dadaia server scan`` and by the panel's "Unregistered"
    section to make orphan dev servers observable (v0.1.1 / Bug D).
    """

    port: int
    bind: str  # "127.0.0.1" / "0.0.0.0" / "::" / "::1" / other IP
    pid: int | None
    cmdline: str  # truncated full command line
    cwd: str  # working dir of pid; "" if not readable
    lan_exposed: bool  # True iff bind in {"0.0.0.0", "::"} (reachable from LAN)
