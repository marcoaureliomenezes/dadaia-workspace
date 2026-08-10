"""JSON-backed Layer-1 agent-model-policy overlay store (v0.1.65 FR3/D-7).

Reads/writes the operator-editable overlay at
``.dadaia/states/agent_model_policy.json`` (schema ``agent-model-policy-v1`` —
``public/schemas/agent-model-policy-v1.schema.json``):
atomic temp+rename write (``tempfile.mkstemp`` in the target dir → ``os.replace``) and a
``.last-good.json`` backup of the prior valid file.

Two load paths, deliberately distinct (NFR-4, "missing != invalid"):

- **Missing file** ⇒ :meth:`load` returns ``None`` ⇒ the resolver falls back to the
  library default template (``balanced``).
- **Present but invalid** ⇒ :meth:`load` raises the typed
  :class:`AgentModelPolicyStoreError` with a distinct, actionable message per FR3
  rejection: corrupt JSON, non-object root, unknown top-level/override key, wrong
  schema version, unknown ``applied_template`` id, unknown agent name (valid names =
  the 9 core agents), a model not in the registry, an
  effort outside the D-3 vocabulary, an empty override, and — D-7 — any combination
  that resolves ``claude-fable-5`` onto ``security-reviewer``.

:meth:`parse` is the shared no-I/O validation path (consumed by :meth:`load` and by the
panel validate endpoint in Wave 4).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from dadaia_workspace.core.agent_model_templates import (
    CORE_AGENTS,
    resolve_agent_model,
    template_by_id,
)
from dadaia_workspace.core.model_registry import registry_by_claude_id
from dadaia_workspace.core.models.agent_model_policy import (
    _SCHEMA_VERSION,
    CLAUDE_EFFORTS,
    AgentModelOverride,
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
    ClaudeEffort,
)

_FILENAME = "agent_model_policy.json"

#: Allowed top-level keys in the overlay file (unknown key ⇒ hard error).
_ALLOWED_TOP_LEVEL = frozenset({"schema_version", "applied_template", "overrides"})
#: Allowed keys inside one per-agent override (per-field: model, effort, or both).
_ALLOWED_OVERRIDE_KEYS = frozenset({"model", "effort"})

#: The agent that must never resolve to claude-fable-5 (G-1/D-7).
_FABLE_FORBIDDEN_AGENT = "security-reviewer"
_FABLE_MODEL = "claude-fable-5"


class JsonAgentModelPolicyStore:
    """Persist the L1 agent-model-policy overlay under canonical workspace state."""

    def __init__(
        self,
        workspace_root: Path,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._path = self._workspace_root / ".dadaia" / "states" / _FILENAME

    @property
    def path(self) -> Path:
        return self._path

    @property
    def last_good_path(self) -> Path:
        return self._path.with_suffix(".json.last-good.json")

    def load(self) -> AgentModelPolicyOverlay | None:
        """Load the overlay; ``None`` when absent (defaults), raise when invalid."""
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AgentModelPolicyStoreError(
                f"corrupt agent-model-policy overlay; invalid JSON ({exc.msg})",
                self._path,
            ) from exc
        except OSError as exc:
            raise AgentModelPolicyStoreError(
                "cannot read agent-model-policy overlay", self._path
            ) from exc
        return self._parse(raw, path=self._path)

    def parse(self, raw: object) -> AgentModelPolicyOverlay:
        """Validate and parse an in-memory overlay document (no I/O).

        Shared by :meth:`load` and callers validating a candidate before writing it
        (the panel ``POST /api/agent-model-policy/validate`` route, Wave 4).
        """
        return self._parse(raw, path=None)

    def save(self, overlay: AgentModelPolicyOverlay) -> None:
        """Atomically persist the overlay, backing up the prior valid file first."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            # Snapshot the PRIOR valid file verbatim before overwriting (NFR-1).
            self._atomic_write_bytes(self.last_good_path, self._path.read_bytes())
        self._atomic_write(self._path, json.dumps(overlay.to_dict(), indent=2, sort_keys=True))

    # -- validation -------------------------------------------------------

    def _parse(self, raw: object, *, path: Path | None) -> AgentModelPolicyOverlay:
        if not isinstance(raw, dict):
            raise AgentModelPolicyStoreError(
                "corrupt agent-model-policy overlay; root is not an object", path
            )
        unknown = set(raw) - _ALLOWED_TOP_LEVEL
        if unknown:
            raise AgentModelPolicyStoreError(
                f"unknown top-level field(s) in agent-model-policy overlay: "
                f"{', '.join(sorted(unknown))}",
                path,
            )
        if raw.get("schema_version") != _SCHEMA_VERSION:
            raise AgentModelPolicyStoreError(
                f"unsupported agent-model-policy schema version "
                f"{raw.get('schema_version')!r}; expected {_SCHEMA_VERSION!r}",
                path,
            )
        applied_template = self._parse_applied_template(raw.get("applied_template"), path=path)
        overrides = self._parse_overrides(raw.get("overrides", {}), path=path)
        overlay = AgentModelPolicyOverlay(applied_template=applied_template, overrides=overrides)
        self._assert_never_fable_on_security(overlay, path=path)
        return overlay

    def _parse_applied_template(self, value: object, *, path: Path | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise AgentModelPolicyStoreError(
                "agent-model-policy 'applied_template' must be a non-empty template id",
                path,
            )
        try:
            template_by_id(value)
        except ValueError as exc:
            raise AgentModelPolicyStoreError(
                f"unknown agent-model template {value!r} in 'applied_template'; {exc}",
                path,
            ) from exc
        return value

    def _parse_overrides(
        self, value: object, *, path: Path | None
    ) -> dict[str, AgentModelOverride]:
        if not isinstance(value, dict):
            raise AgentModelPolicyStoreError(
                "agent-model-policy 'overrides' must be an object keyed by agent name", path
            )
        valid_agents = set(CORE_AGENTS)
        overrides: dict[str, AgentModelOverride] = {}
        for agent_name, override_value in value.items():
            agent = str(agent_name)
            if agent not in valid_agents:
                raise AgentModelPolicyStoreError(
                    f"unknown agent {agent!r} in 'overrides'; valid agents: "
                    f"{', '.join(sorted(valid_agents))}",
                    path,
                )
            overrides[agent] = self._parse_override(agent, override_value, path=path)
        return overrides

    def _parse_override(
        self, agent: str, value: object, *, path: Path | None
    ) -> AgentModelOverride:
        if not isinstance(value, dict):
            raise AgentModelPolicyStoreError(
                f"override for agent {agent!r} must be an object", path
            )
        unknown = set(value) - _ALLOWED_OVERRIDE_KEYS
        if unknown:
            raise AgentModelPolicyStoreError(
                f"unknown field(s) in override for agent {agent!r}: {', '.join(sorted(unknown))}",
                path,
            )
        if not value:
            raise AgentModelPolicyStoreError(
                f"override for agent {agent!r} must carry 'model', 'effort', or both",
                path,
            )
        model = self._parse_model(agent, value.get("model"), path=path)
        effort = self._parse_effort(agent, value.get("effort"), path=path)
        return AgentModelOverride(model=model, effort=effort)

    def _parse_model(self, agent: str, value: object, *, path: Path | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or value not in registry_by_claude_id():
            raise AgentModelPolicyStoreError(
                f"unknown model {value!r} in override for agent {agent!r}; valid models: "
                f"{', '.join(sorted(registry_by_claude_id()))}",
                path,
            )
        return value

    def _parse_effort(self, agent: str, value: object, *, path: Path | None) -> ClaudeEffort | None:
        if value is None:
            return None
        if not isinstance(value, str) or value not in CLAUDE_EFFORTS:
            raise AgentModelPolicyStoreError(
                f"invalid effort {value!r} in override for agent {agent!r}; valid: "
                f"{', '.join(CLAUDE_EFFORTS)}",
                path,
            )
        # ``value`` is provably a member of the ClaudeEffort literal now.
        return value

    def _assert_never_fable_on_security(
        self, overlay: AgentModelPolicyOverlay, *, path: Path | None
    ) -> None:
        """D-7: reject any overlay that RESOLVES Fable onto security-reviewer.

        Uses the single resolver (FR4) so the check covers every combination
        (override model, template interplay), not just the literal override value.
        """
        resolved = resolve_agent_model(_FABLE_FORBIDDEN_AGENT, overlay)
        if resolved.model == _FABLE_MODEL:
            raise AgentModelPolicyStoreError(
                f"policy resolves {_FABLE_MODEL!r} onto {_FABLE_FORBIDDEN_AGENT!r}; "
                "Fable is never assigned to security-reviewer (operator ruling G-1)",
                path,
            )

    # -- atomic write -------------------------------------------------------

    def _atomic_write(self, path: Path, content: str) -> None:
        self._atomic_write_bytes(path, (content + "\n").encode("utf-8"))

    def _atomic_write_bytes(self, path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
            os.replace(tmp_path, path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise


__all__ = [
    "JsonAgentModelPolicyStore",
]
