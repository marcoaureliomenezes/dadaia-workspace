"""Canonical machine-readable dadaia-workspace capability contract."""

from __future__ import annotations

from importlib import metadata
from typing import Any

from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION

CAPABILITY_SCHEMA_VERSION = "dadaia-capabilities-v1"


def _distribution_version() -> str:
    try:
        return metadata.version("dadaia-workspace")
    except metadata.PackageNotFoundError:
        return "0+source"


def build_capabilities() -> dict[str, Any]:
    """Return the stable public provider contract for agent consumers."""
    return {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "provider": {
            "name": "dadaia-workspace",
            "distribution_version": _distribution_version(),
        },
        "specs": {
            "pattern_version": CANONICAL_SPECS_VERSION,
            "status_tokens": ["Draft", "Em revisão", "Aprovado"],
            "commands": [
                "dadaia specs init",
                "dadaia specs doctor --json",
                "dadaia specs upgrade",
            ],
        },
        "contexts": {
            "states": ["alive", "dead"],
            "modes": ["read", "spec", "implementation", "review"],
            "commands": [
                "create",
                "list --json",
                "show --json",
                "alive",
                "baseline",
                "dead",
                "delete",
                "update",
                "bind",
                "release",
                "heartbeat",
            ],
            "selection_contract": "explicit-or-caller-owned-bind",
        },
        "workflows": [
            {
                "id": "backlog_definition",
                "command": "dadaia lifecycle backlog-definition",
            },
            {
                "id": "release_definition",
                "command": "dadaia lifecycle release-definition",
            },
            {
                "id": "implementation_reviews",
                "command": "dadaia lifecycle implementation-reviews",
            },
            {"id": "audit", "command": "dadaia lifecycle audit"},
        ],
        "harnesses": {
            "layer_1": ["claude-code", "codex", "pi", "kimi-code"],
            "layer_2_workers": ["codex", "pi", "fake"],
            "claude_layer_2_supported": False,
        },
        "surfaces": {
            "workspace": ["init", "export", "import", "doctor", "clean"],
            "public_projections": ["stage", "install", "doctor", "list"],
            "panel": ["panel", "server registry", "workflow catalog"],
            "evidence": ["reports", "handoff validation", "workflow state"],
            "knowledge": ["memory", "academy", "projected skills", "rules"],
            "governance": ["bugs", "backlog", "releases", "ci preflight"],
            "extensions": ["plugins", "repository catalog"],
        },
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
            "deterministic_fake_workflows": True,
            "live_harness_canaries_required_for_release": True,
        },
    }
