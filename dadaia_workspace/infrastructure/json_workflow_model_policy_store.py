"""JSON-backed workflow-model-policy overlay store.

Reads/writes the operator-editable policy overlay at
``.dadaia/states/workflow_model_policy.json`` (schema ``workflow-model-policy-v1``).
Reuses the :class:`JsonLifecycleRunStore` atomic temp+rename pattern
(``tempfile.mkstemp`` in the target dir → ``os.replace``) and keeps a
``.last-good.json`` backup of the prior valid file.

Two load paths, deliberately distinct (LAW 4 / SPEC §1, "missing != invalid"):

- **Missing file** ⇒ :meth:`load` returns ``None`` ⇒ the resolver falls back to library
  defaults (a workflow is runnable before any overlay exists).
- **Present but invalid** (corrupt JSON, unknown top-level field, wrong schema version,
  non-object root) ⇒ :meth:`load` raises :class:`WorkflowModelPolicyStoreError`. The
  caller (resolver/runner) must fail before the first model call; the ``.last-good.json``
  backup is left untouched.

D-2: only the ``default`` context overlay is honored. The ``contexts`` map reserves the
per-context shape, but :meth:`WorkflowModelPolicyOverlay.step_profile` only resolves the
``default`` context — a non-``default`` key is inert.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCHEMA_VERSION = "workflow-model-policy-v1"
_FILENAME = "workflow_model_policy.json"

#: Allowed top-level keys in the overlay file (unknown key ⇒ hard error).
_ALLOWED_TOP_LEVEL = frozenset({"schema_version", "policy_id", "contexts"})
#: The only context honored this release (D-2).
DEFAULT_CONTEXT = "default"


@dataclass(frozen=True)
class WorkflowModelPolicyStoreError(Exception):
    """Actionable workflow-model-policy overlay failure."""

    message: str
    path: Path | None = None

    def __str__(self) -> str:
        if self.path is None:
            return self.message
        return f"{self.message}: {self.path}"


@dataclass(frozen=True)
class WorkflowModelPolicyOverlay:
    """Parsed, validated overlay (in-memory).

    ``contexts`` maps a context name to ``{workflow_id -> {step_label -> profile_id}}``.
    Only the ``default`` context is honored (D-2); other context keys are retained for
    round-trip fidelity but :meth:`step_profile` ignores them.
    """

    policy_id: str
    contexts: dict[str, dict[str, dict[str, str]]]

    def step_profile(self, context: str, workflow_id: str, step: str) -> str | None:
        """Return the overridden profile id for a step, or ``None`` when not overridden.

        D-2: only the ``default`` context resolves; any other context yields ``None``.
        """
        if context != DEFAULT_CONTEXT:
            return None
        return self.contexts.get(context, {}).get(workflow_id, {}).get(step)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "policy_id": self.policy_id,
            "contexts": {
                ctx: {"workflows": {wf: {"steps": dict(steps)} for wf, steps in workflows.items()}}
                for ctx, workflows in self.contexts.items()
            },
        }


class JsonWorkflowModelPolicyStore:
    """Persist the workflow-model-policy overlay under canonical workspace state."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve()
        self._path = self._workspace_root / ".dadaia" / "states" / _FILENAME

    @property
    def path(self) -> Path:
        return self._path

    @property
    def last_good_path(self) -> Path:
        return self._path.with_suffix(".json.last-good.json")

    def load(self) -> WorkflowModelPolicyOverlay | None:
        """Load the overlay; ``None`` when absent (defaults), raise when invalid."""
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise WorkflowModelPolicyStoreError(
                f"corrupt workflow-model-policy overlay; invalid JSON ({exc.msg})",
                self._path,
            ) from exc
        except OSError as exc:
            raise WorkflowModelPolicyStoreError(
                "cannot read workflow-model-policy overlay", self._path
            ) from exc
        return self._parse(raw, path=self._path)

    def parse(self, raw: dict[str, object]) -> WorkflowModelPolicyOverlay:
        """Validate and parse an in-memory overlay dict (no I/O).

        Shared by :meth:`load` and callers that validate a candidate before writing it
        (e.g. the panel validate route in Wave C).
        """
        return self._parse(raw, path=None)

    def save(self, overlay: WorkflowModelPolicyOverlay) -> None:
        """Atomically persist the overlay, backing up the prior valid file first."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            # Back up the PRIOR valid file before overwriting (last-good safety, LAW 5).
            # Copy the bytes verbatim so the backup is a faithful snapshot of the prior file.
            self._atomic_write_bytes(self.last_good_path, self._path.read_bytes())
        self._atomic_write(self._path, json.dumps(overlay.to_dict(), indent=2, sort_keys=True))

    # -- validation -------------------------------------------------------

    def _parse(self, raw: object, *, path: Path | None) -> WorkflowModelPolicyOverlay:
        if not isinstance(raw, dict):
            raise WorkflowModelPolicyStoreError(
                "corrupt workflow-model-policy overlay; root is not an object", path
            )
        unknown = set(raw) - _ALLOWED_TOP_LEVEL
        if unknown:
            raise WorkflowModelPolicyStoreError(
                f"unknown top-level field(s) in workflow-model-policy overlay: "
                f"{', '.join(sorted(unknown))}",
                path,
            )
        if raw.get("schema_version") != _SCHEMA_VERSION:
            raise WorkflowModelPolicyStoreError(
                f"unsupported workflow-model-policy schema version "
                f"{raw.get('schema_version')!r}; expected {_SCHEMA_VERSION!r}",
                path,
            )
        policy_id = str(raw.get("policy_id", DEFAULT_CONTEXT))
        contexts_raw = raw.get("contexts", {})
        if not isinstance(contexts_raw, dict):
            raise WorkflowModelPolicyStoreError(
                "workflow-model-policy 'contexts' must be an object", path
            )
        contexts: dict[str, dict[str, dict[str, str]]] = {}
        for ctx_name, ctx_value in contexts_raw.items():
            contexts[str(ctx_name)] = self._parse_context(ctx_value, path=path)
        return WorkflowModelPolicyOverlay(policy_id=policy_id, contexts=contexts)

    def _parse_context(self, value: object, *, path: Path | None) -> dict[str, dict[str, str]]:
        if not isinstance(value, dict):
            raise WorkflowModelPolicyStoreError(
                "workflow-model-policy context overlay must be an object", path
            )
        unknown = set(value) - {"workflows"}
        if unknown:
            raise WorkflowModelPolicyStoreError(
                f"unknown field(s) in context overlay: {', '.join(sorted(unknown))}", path
            )
        workflows_raw = value.get("workflows", {})
        if not isinstance(workflows_raw, dict):
            raise WorkflowModelPolicyStoreError(
                "context overlay 'workflows' must be an object", path
            )
        workflows: dict[str, dict[str, str]] = {}
        for wf_name, wf_value in workflows_raw.items():
            workflows[str(wf_name)] = self._parse_workflow(wf_value, path=path)
        return workflows

    def _parse_workflow(self, value: object, *, path: Path | None) -> dict[str, str]:
        if not isinstance(value, dict):
            raise WorkflowModelPolicyStoreError("workflow overlay must be an object", path)
        unknown = set(value) - {"steps"}
        if unknown:
            raise WorkflowModelPolicyStoreError(
                f"unknown field(s) in workflow overlay: {', '.join(sorted(unknown))}", path
            )
        steps_raw = value.get("steps", {})
        if not isinstance(steps_raw, dict):
            raise WorkflowModelPolicyStoreError("workflow overlay 'steps' must be an object", path)
        steps: dict[str, str] = {}
        for step_label, profile_id in steps_raw.items():
            if not isinstance(profile_id, str):
                raise WorkflowModelPolicyStoreError(
                    f"step {step_label!r} profile must be a string profile id", path
                )
            steps[str(step_label)] = profile_id
        return steps

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
    "DEFAULT_CONTEXT",
    "JsonWorkflowModelPolicyStore",
    "WorkflowModelPolicyOverlay",
    "WorkflowModelPolicyStoreError",
]
