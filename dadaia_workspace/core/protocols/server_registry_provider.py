"""ServerRegistryProvider Protocol — read-only server-entry enumeration for the panel."""

from typing import Protocol

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus


class ServerRegistryProvider(Protocol):
    """Minimum read surface that PanelService requires from the server registry."""

    def list_entries(
        self,
        project: str | None = None,
        include_stale: bool = True,
    ) -> list[tuple[PortEntry, PortStatus]]: ...
