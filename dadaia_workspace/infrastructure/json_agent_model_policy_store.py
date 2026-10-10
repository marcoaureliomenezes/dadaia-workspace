"""JSON-backed agent-model-policy overlay store (schema ``agent-model-policy-v1``).

Reads/writes the operator-editable overlay at ``.dadaia/states/agent_model_policy.json``
(``public/schemas/agent-model-policy-v1.schema.json``): atomic temp+rename write and a
``.last-good.json`` backup of the prior valid file. The overlay carries ``applied_template`` only.

Missing file => :meth:`load` returns ``None`` (library default template). Present but invalid =>
the typed :class:`AgentModelPolicyStoreError`: corrupt JSON, non-object root, unknown key
(``overrides`` included, with a runnable ``fix``), wrong schema version, unknown template id.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.model_registry import (
    _SCHEMA_VERSION,
    DEFAULT_TEMPLATE_ID,
    TEMPLATES,
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
    template_by_id,
)

_FILENAME = "agent_model_policy.json"

_ALLOWED_TOP_LEVEL = frozenset({"schema_version", "applied_template"})


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
        return self._parse(raw)

    def save(self, overlay: AgentModelPolicyOverlay) -> None:
        """Atomically persist the overlay, backing up the prior valid file first."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            # Snapshot the PRIOR valid file verbatim before overwriting (NFR-1).
            atomic_write(self.last_good_path, self._path.read_bytes(), ensure_parent=True)
        atomic_write(
            self._path,
            json.dumps(overlay.to_dict(), indent=2, sort_keys=True) + "\n",
            ensure_parent=True,
        )

    def _parse(self, raw: object) -> AgentModelPolicyOverlay:
        path = self._path
        if not isinstance(raw, dict):
            raise AgentModelPolicyStoreError(
                "corrupt agent-model-policy overlay; root is not an object", path
            )
        unknown = set(raw) - _ALLOWED_TOP_LEVEL
        if unknown:
            template = raw.get("applied_template")
            if not (isinstance(template, str) and template in TEMPLATES):
                template = DEFAULT_TEMPLATE_ID
            raise AgentModelPolicyStoreError(
                f"unknown top-level field(s) in agent-model-policy overlay: "
                f"{', '.join(sorted(unknown))}",
                path,
                fix_line(self._workspace_root, "public", "install", "--template", template),
            )
        if raw.get("schema_version") != _SCHEMA_VERSION:
            raise AgentModelPolicyStoreError(
                f"unsupported agent-model-policy schema version "
                f"{raw.get('schema_version')!r}; expected {_SCHEMA_VERSION!r}",
                path,
            )
        value = raw.get("applied_template")
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise AgentModelPolicyStoreError(
                    "agent-model-policy 'applied_template' must be a non-empty template id", path
                )
            try:
                template_by_id(value)
            except ValueError as exc:
                raise AgentModelPolicyStoreError(
                    f"unknown agent-model template {value!r} in 'applied_template'; {exc}", path
                ) from exc
        return AgentModelPolicyOverlay(applied_template=value)


__all__ = [
    "JsonAgentModelPolicyStore",
]
