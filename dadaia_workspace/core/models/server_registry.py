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
