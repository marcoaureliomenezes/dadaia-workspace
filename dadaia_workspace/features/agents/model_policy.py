"""Panel-facing L1 agent-model-policy service (v0.1.65 FR8 / T-65-10).

The feature seam between the panel views and the agent-model governance stack:

- the overlay **store** (concrete: ``infrastructure/json_agent_model_policy_store.py``)
  is injected through the :class:`AgentModelPolicyStorePort` protocol — this module
  never imports infrastructure (D-4, ``features-no-infrastructure``);
- the **re-render callable** (the agents-only ``public install`` path — G-2 Apply
  semantics) is injected by the composition root (``container.build_panel_views``);
- the **plugin pack defaults** provider returns ``{agent_name: pack_default_model}``
  for the installed packs, so the resolved roster covers the 9 core agents plus every
  installed plugin agent (G-4/D-5).

All precedence goes through the single resolver
(:func:`~dadaia_workspace.core.agent_model_templates.resolve_agent_model` — FR4); this
service never re-implements precedence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from dadaia_workspace.core.agent_model_templates import (
    CORE_AGENTS,
    list_templates,
    resolve_agent_model,
)
from dadaia_workspace.core.model_registry import registry_by_claude_id
from dadaia_workspace.core.models.agent_model_policy import (
    _SCHEMA_VERSION,
    CLAUDE_EFFORTS,
    AgentModelPolicyOverlay,
)

#: G-2 per-harness pickup instructions, surfaced verbatim by the post-apply pop-up.
PICKUP_INSTRUCTIONS: dict[str, str] = {
    "claude": (
        "Claude Code: live sessions pick up the new model within seconds on the next "
        "delegation. Exception: a brand-new agents directory created mid-session "
        "requires a session restart."
    ),
    "codex": "Codex: restart the session to pick up the re-rendered agent TOMLs.",
}


class AgentModelPolicyStorePort(Protocol):
    """The overlay store surface this service consumes (concrete store: infrastructure)."""

    def load(self) -> AgentModelPolicyOverlay | None: ...

    def parse(self, raw: object) -> AgentModelPolicyOverlay: ...

    def save(self, overlay: AgentModelPolicyOverlay) -> None: ...


class AgentModelPolicyService:
    """Validate, persist, re-render, and resolve the L1 agent-model policy."""

    def __init__(
        self,
        store: AgentModelPolicyStorePort,
        rerender: Callable[[], list[str]],
        plugin_pack_defaults: Callable[[], dict[str, str]] | None = None,
    ) -> None:
        self._store = store
        self._rerender = rerender
        self._plugin_pack_defaults = plugin_pack_defaults or (lambda: {})

    # -- read ---------------------------------------------------------------

    def get_policy(self) -> dict[str, object]:
        """The FR8 GET payload: ``{exists, policy, resolved}``.

        Raises:
            AgentModelPolicyStoreError: when a present overlay file is invalid
                (missing != invalid — the view maps this to 409).
        """
        overlay = self._store.load()
        policy = overlay.to_dict() if overlay is not None else {"schema_version": _SCHEMA_VERSION}
        return {
            "exists": overlay is not None,
            "policy": policy,
            "resolved": self._resolved_roster(overlay),
        }

    def resolved_roster(self) -> dict[str, dict[str, object]]:
        """The full resolved roster (core + installed plugin agents), source-tagged."""
        return self._resolved_roster(self._store.load())

    def templates_payload(self) -> dict[str, object]:
        """The FR8 templates payload: 3 built-ins + selectable models + effort vocab."""
        templates: list[dict[str, object]] = []
        for template in list_templates():
            templates.append(
                {
                    "id": template.id,
                    "label": template.label,
                    "default": template.default,
                    "assignments": {
                        agent: {"model": a.model, "effort": a.effort}
                        for agent, a in sorted(template.assignments.items())
                    },
                }
            )
        return {
            "templates": templates,
            "models": sorted(registry_by_claude_id()),
            "efforts": list(CLAUDE_EFFORTS),
        }

    # -- mutate ---------------------------------------------------------------

    def validate(self, raw: object) -> AgentModelPolicyOverlay:
        """Dry-run validation of a candidate overlay document (no write).

        Raises:
            AgentModelPolicyStoreError: with the distinct FR3/AC-4 message on any
                rejection (unknown agent/model/effort/template, Fable-on-security).
        """
        return self._store.parse(raw)

    def apply(self, raw: object) -> dict[str, object]:
        """Validate → save (atomic + last-good) → re-render BOTH projections (G-2).

        Returns the applied policy, the resolved roster, the re-render summary lines,
        and the per-harness pickup instructions for the post-apply pop-up.

        Raises:
            AgentModelPolicyStoreError: on an invalid candidate — nothing is saved and
                the re-render callable is never invoked.
        """
        overlay = self.validate(raw)
        self._store.save(overlay)
        rerendered = self._rerender()
        return {
            "policy": overlay.to_dict(),
            "resolved": self._resolved_roster(overlay),
            "rerendered": rerendered,
            "instructions": dict(PICKUP_INSTRUCTIONS),
        }

    # -- internals ------------------------------------------------------------

    def _resolved_roster(
        self, overlay: AgentModelPolicyOverlay | None
    ) -> dict[str, dict[str, object]]:
        roster: dict[str, dict[str, object]] = {}
        for agent in CORE_AGENTS:
            resolved = resolve_agent_model(agent, overlay)
            roster[agent] = {
                "model": resolved.model,
                "effort": resolved.effort,
                "source": resolved.source,
            }
        for agent, pack_default in sorted(self._plugin_pack_defaults().items()):
            resolved = resolve_agent_model(agent, overlay, pack_default=pack_default)
            roster[agent] = {
                "model": resolved.model,
                "effort": resolved.effort,
                "source": resolved.source,
            }
        return roster


__all__ = [
    "PICKUP_INSTRUCTIONS",
    "AgentModelPolicyService",
    "AgentModelPolicyStorePort",
]
