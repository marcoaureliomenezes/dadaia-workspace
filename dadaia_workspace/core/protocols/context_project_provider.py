"""ContextProjectProvider Protocol — read-only context enumeration for the panel."""

from typing import Protocol

from dadaia_workspace.core.models.spec_context import SpecContextProject


class ContextProjectProvider(Protocol):
    """Minimum read surface that PanelService requires from the spec-context feature."""

    def list_all(self) -> list[SpecContextProject]: ...
