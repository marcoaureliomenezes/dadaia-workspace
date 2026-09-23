"""Canonical machine-readable dadaia-workspace capability contract."""

from __future__ import annotations

from collections.abc import Collection
from importlib import metadata
from typing import Any

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.spec_status import CANONICAL_STATUS
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION

CAPABILITY_SCHEMA_VERSION = "dadaia-capabilities-v3"


def distribution_version() -> str:
    """The installed provider version — what ``reconcile`` checks after an upgrade."""
    try:
        return metadata.version("dadaia-workspace")
    except metadata.PackageNotFoundError:
        return "0+source"


def build_capabilities(command_paths: Collection[tuple[str, ...]]) -> dict[str, Any]:
    """Return the public provider contract for agent consumers.

    Every advertised verb is derived from *command_paths* — the live command tree, handed
    in by the CLI composition — and every harness from the harness registry, so the
    payload cannot name what the installation does not ship.
    """
    groups: dict[str, list[str]] = {}
    for path in sorted(command_paths):
        if len(path) == 1:
            groups.setdefault(path[0], [])
        elif len(path) == 2:
            groups.setdefault(path[0], []).append(path[1])
    return {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "provider": {
            "name": "dadaia-workspace",
            "distribution_version": distribution_version(),
        },
        "specs": {
            "pattern_version": CANONICAL_SPECS_VERSION,
            # Derived from the doctor's own canon, never a second copy.
            "status_tokens": sorted(CANONICAL_STATUS),
            "commands": [f"dadaia specs {verb}" for verb in groups.get("specs", [])],
        },
        "contexts": {
            "states": ["alive", "dead"],
            "commands": groups.get("context", []),
            "selection_contract": "explicit-or-caller-owned-bind",
        },
        "harnesses": {"layer_1": list(L1_ENTRY_HARNESSES)},
        "surfaces": groups,
        "consumer_requirements": {
            "exact_provider_version": True,
            "reconcile_public_projections_after_upgrade": True,
            "load_scoped_context_after_bind": True,
            "preserve_complete_diagnostics": True,
            "credentials_location": "workspace-root-.env-only",
        },
        "certification": {
            "command": "dadaia certify --json",
            "schema_version": "dadaia-certification-v1",
        },
    }
