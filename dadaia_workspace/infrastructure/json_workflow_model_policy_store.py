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

Per-context inheritance (v0.1.30 / WS-OVERLAYS, replacing the D-2 collapse): a non-
``default`` context overlay is now honored. Each context may declare an ``extends`` parent;
resolution walks ``context → extends… → default`` and returns the first level that defines
the requested step/workflow value (``default`` is the inheritance root). The ``extends``
graph is validated **at parse time** (L7 back-compat is preserved — an overlay with no
``extends`` key parses and resolves byte-identically to v0.1.28/29):

- a **missing** ``extends`` parent is a hard validation error (never a silent fallthrough);
- an ``extends`` **cycle** is rejected at parse time;
- ``default`` is the root and may not declare ``extends``.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.protocols.workflow_model_policy_store import (
    DEFAULT_CONTEXT,
    WorkflowModelPolicyOverlay,
)
from dadaia_workspace.core.protocols.workflow_model_policy_store import (
    WorkflowModelPolicyStoreError as CoreWorkflowModelPolicyStoreError,
)

_SCHEMA_VERSION = "workflow-model-policy-v1"
_FILENAME = "workflow_model_policy.json"

#: Allowed top-level keys in the overlay file (unknown key ⇒ hard error).
_ALLOWED_TOP_LEVEL = frozenset({"schema_version", "policy_id", "contexts"})
#: Allowed keys inside one context overlay (v0.1.30 adds the optional ``extends`` parent).
_ALLOWED_CONTEXT_KEYS = frozenset({"workflows", "extends"})
#: Allowed keys inside one workflow overlay (v0.1.29 adds the optional harness fields).
_ALLOWED_WORKFLOW_KEYS = frozenset({"steps", "default_harness", "harnesses"})
#: The Layer-2 worker harnesses an overlay may name (LAW 1). ``claude``/``opencode`` are
#: rejected at parse time so an invalid harness never persists (mirrors the schema enum).
_LAYER2_HARNESSES = frozenset({"codex", "pi"})


@dataclass(frozen=True)
class WorkflowModelPolicyStoreError(CoreWorkflowModelPolicyStoreError):
    """Actionable workflow-model-policy overlay failure."""

    message: str
    path: Path | None = None

    def __str__(self) -> str:
        if self.path is None:
            return self.message
        return f"{self.message}: {self.path}"


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
        default_harness: dict[str, dict[str, str]] = {}
        step_harness: dict[str, dict[str, dict[str, str]]] = {}
        extends: dict[str, str] = {}
        for ctx_name, ctx_value in contexts_raw.items():
            ctx_key = str(ctx_name)
            steps_map, default_h, step_h, parent = self._parse_context(
                ctx_key, ctx_value, path=path
            )
            contexts[ctx_key] = steps_map
            if default_h:
                default_harness[ctx_key] = default_h
            if step_h:
                step_harness[ctx_key] = step_h
            if parent is not None:
                extends[ctx_key] = parent
        # WS-OVERLAYS: validate the `extends` graph at parse time (every parent present,
        # no cycles, default declares no parent) so the accessors can walk it safely.
        self._validate_extends(extends, contexts, path=path)
        return WorkflowModelPolicyOverlay(
            policy_id=policy_id,
            contexts=contexts,
            default_harness_overlay=default_harness,
            step_harness_overlay=step_harness,
            extends=extends,
        )

    def _validate_extends(
        self,
        extends: dict[str, str],
        contexts: dict[str, dict[str, dict[str, str]]],
        *,
        path: Path | None,
    ) -> None:
        """Reject a missing ``extends`` parent (hard error) or any ``extends`` cycle.

        A parent must be a context key that exists in the overlay (the inheritance-root
        ``default`` is an implicit valid parent even when it carries no overrides). A cycle
        anywhere in the chain — including a context that (transitively) extends itself — is
        rejected. ``default`` may not declare a parent (it is the root).
        """
        for child, parent in extends.items():
            if child == DEFAULT_CONTEXT:
                raise WorkflowModelPolicyStoreError(
                    f"context {DEFAULT_CONTEXT!r} is the inheritance root and may not "
                    "declare an 'extends' parent",
                    path,
                )
            if parent != DEFAULT_CONTEXT and parent not in contexts:
                raise WorkflowModelPolicyStoreError(
                    f"context {child!r} extends unknown parent context {parent!r}; "
                    "the parent must be a declared context or the 'default' root",
                    path,
                )
        # Cycle detection: walk every context's chain; a repeated node is a cycle.
        for start in extends:
            seen: set[str] = set()
            current: str | None = start
            while current is not None:
                if current in seen:
                    raise WorkflowModelPolicyStoreError(
                        f"'extends' cycle detected starting at context {start!r} "
                        f"(revisited {current!r})",
                        path,
                    )
                seen.add(current)
                current = extends.get(current)

    def _parse_context(
        self, ctx_name: str, value: object, *, path: Path | None
    ) -> tuple[dict[str, dict[str, str]], dict[str, str], dict[str, dict[str, str]], str | None]:
        if not isinstance(value, dict):
            raise WorkflowModelPolicyStoreError(
                "workflow-model-policy context overlay must be an object", path
            )
        unknown = set(value) - _ALLOWED_CONTEXT_KEYS
        if unknown:
            raise WorkflowModelPolicyStoreError(
                f"unknown field(s) in context overlay: {', '.join(sorted(unknown))}", path
            )
        parent = self._parse_extends_value(value.get("extends"), ctx_name=ctx_name, path=path)
        workflows_raw = value.get("workflows", {})
        if not isinstance(workflows_raw, dict):
            raise WorkflowModelPolicyStoreError(
                "context overlay 'workflows' must be an object", path
            )
        workflows: dict[str, dict[str, str]] = {}
        default_harness: dict[str, str] = {}
        step_harness: dict[str, dict[str, str]] = {}
        for wf_name, wf_value in workflows_raw.items():
            wf_key = str(wf_name)
            steps, default_h, step_h = self._parse_workflow(wf_value, path=path)
            workflows[wf_key] = steps
            if default_h is not None:
                default_harness[wf_key] = default_h
            if step_h:
                step_harness[wf_key] = step_h
        return workflows, default_harness, step_harness, parent

    def _parse_extends_value(
        self, value: object, *, ctx_name: str, path: Path | None
    ) -> str | None:
        """Validate an optional ``extends`` parent name (a non-empty string or absent)."""
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise WorkflowModelPolicyStoreError(
                f"context {ctx_name!r} 'extends' must be a non-empty parent context name",
                path,
            )
        if value == ctx_name:
            raise WorkflowModelPolicyStoreError(f"context {ctx_name!r} cannot extend itself", path)
        return value

    def _parse_workflow(
        self, value: object, *, path: Path | None
    ) -> tuple[dict[str, str], str | None, dict[str, str]]:
        if not isinstance(value, dict):
            raise WorkflowModelPolicyStoreError("workflow overlay must be an object", path)
        unknown = set(value) - _ALLOWED_WORKFLOW_KEYS
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

        default_harness = self._parse_harness_value(
            value.get("default_harness"), what="default_harness", path=path
        )

        harnesses_raw = value.get("harnesses", {})
        if not isinstance(harnesses_raw, dict):
            raise WorkflowModelPolicyStoreError(
                "workflow overlay 'harnesses' must be an object", path
            )
        step_harness: dict[str, str] = {}
        for step_label, harness in harnesses_raw.items():
            if harness is None:
                raise WorkflowModelPolicyStoreError(
                    f"workflow overlay harnesses[{step_label!r}] must name a harness, not null",
                    path,
                )
            resolved = self._parse_harness_value(
                harness, what=f"harnesses[{step_label!r}]", path=path
            )
            assert resolved is not None  # guarded by the explicit null check above
            step_harness[str(step_label)] = resolved
        return steps, default_harness, step_harness

    def _parse_harness_value(self, value: object, *, what: str, path: Path | None) -> str | None:
        """Validate an optional harness string against the Layer-2 allow-set (codex|pi)."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise WorkflowModelPolicyStoreError(
                f"workflow overlay {what} must be a harness string", path
            )
        if value not in _LAYER2_HARNESSES:
            raise WorkflowModelPolicyStoreError(
                f"workflow overlay {what} names harness {value!r}; "
                f"Layer-2 workers are codex or pi only (claude/opencode are not Layer-2)",
                path,
            )
        return value

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
