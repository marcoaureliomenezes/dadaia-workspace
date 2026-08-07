"""Panel feature package.

Provides the Dadaia Workspace Panel — a local single-page web UI surfacing
running dev servers, active Spec Context Project memories, and (in Release-2)
the agents catalog.

Layer note: features/panel/ is a read-only orchestrator that fans out to
ServerRegistryService and SpecContextService. It never writes to the stores
those services manage.
"""
