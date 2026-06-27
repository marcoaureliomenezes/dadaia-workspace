"""JSON-backed operator-local model-profile store — ``infrastructure``.

Reads the operator-editable, **workspace-local** profile store at
``.dadaia/states/workflow_model_profiles.local.json`` (Item 4 / WS-PROFILES). The store
lets an operator register their own Layer-2 model profiles (PI-scoped this release) that a
governed workflow step can select alongside the built-in recommended profiles.

This adapter is the concrete :class:`LocalModelProfileStorePort`. It mirrors the
:class:`JsonWorkflowModelPolicyStore` resilience posture — atomic temp+rename writes and the
two distinct load paths (L3 — "missing != invalid"):

- **Missing file** ⇒ :meth:`load` returns ``()`` ⇒ the feature layer surfaces the built-in
  profiles only (default-first: a workflow is runnable before any operator profile exists).
- **Present-but-invalid** (corrupt JSON, non-object root, unknown top-level/profile field,
  wrong schema version, a profile with ``harness != "pi"`` per **L1**, or any
  API-key-bearing field per **L8**) ⇒ :meth:`load` raises
  :class:`LocalModelProfileStoreError`. The caller fails closed before the first model call.

**Privacy (L8).** The store MUST NEVER carry a secret. Any field whose name looks like an
API key / token / secret (:data:`_FORBIDDEN_SECRET_NAME_PARTS`) is rejected at parse time —
on the root, on a profile, and recursively inside any nested object — and the error names
only the offending field, never its value (OWASP A06/A09). The store is **never projected**
into ``public/`` (its filename is not a packaged asset; see the never-projected guarantee
test) and lives only under workspace-local ``.dadaia/states/``.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from dadaia_workspace.core.models.workflow_execution import WorkflowModelProfile
from dadaia_workspace.core.protocols.local_model_profile_store import (
    LocalModelProfileStoreError,
)

_SCHEMA_VERSION = "workflow-model-profiles-local-v1"
_FILENAME = "workflow_model_profiles.local.json"

#: The only harness an operator-added profile may declare this release (L1 — PI-scoped).
_OPERATOR_HARNESS = "pi"

#: Allowed top-level keys in the local store (unknown key ⇒ hard error).
_ALLOWED_TOP_LEVEL = frozenset({"schema_version", "profiles"})

#: Allowed keys inside one operator profile object. Mirrors the ``WorkflowModelProfile``
#: serialization surface; ``source``/``availability`` default in the model. No field here
#: carries a credential — and any credential-shaped extra key is rejected (L8).
_ALLOWED_PROFILE_KEYS = frozenset(
    {
        "id",
        "harness",
        "label",
        "model_id",
        "effort",
        "purpose",
        "availability",
        "source",
        "deprecated",
        "replacement",
    }
)

#: Substrings that mark a field name as credential-bearing (L8). Matched case-insensitively
#: against every key, recursively, so no secret can be smuggled into the local store.
_FORBIDDEN_SECRET_NAME_PARTS = (
    "api_key",
    "apikey",
    "api-key",
    "secret",
    "token",
    "password",
    "passwd",
    "credential",
    "private_key",
    "private-key",
    "access_key",
    "access-key",
    "bearer",
    "auth",
)


def _names_a_secret(field_name: str) -> bool:
    lowered = field_name.lower()
    return any(part in lowered for part in _FORBIDDEN_SECRET_NAME_PARTS)


def _assert_no_secret_fields(value: object, *, where: str) -> None:
    """Recursively reject any credential-shaped key in *value* (L8).

    Walks dicts and lists so a secret nested under an unexpected object is still caught.
    The error names the field path, never the value (A06/A09).
    """
    if isinstance(value, dict):
        for key, child in value.items():
            key_str = str(key)
            if _names_a_secret(key_str):
                raise LocalModelProfileStoreError(
                    f"operator-local model-profile store carries a forbidden "
                    f"credential-shaped field {where}.{key_str!r}; the store must never "
                    "hold an API key, token, or secret (L8)"
                )
            _assert_no_secret_fields(child, where=f"{where}.{key_str}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_secret_fields(child, where=f"{where}[{index}]")


class JsonLocalModelProfileStore:
    """Persist operator-registered model profiles under canonical workspace state."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve()
        self._path = self._workspace_root / ".dadaia" / "states" / _FILENAME

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> tuple[WorkflowModelProfile, ...]:
        """Load operator profiles; empty tuple when absent, raise when invalid (L3)."""
        if not self._path.exists():
            return ()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LocalModelProfileStoreError(
                f"corrupt operator-local model-profile store; invalid JSON ({exc.msg}): "
                f"{self._path}"
            ) from exc
        except OSError as exc:
            raise LocalModelProfileStoreError(
                f"cannot read operator-local model-profile store: {self._path}"
            ) from exc
        return self.parse(raw)

    def parse(self, raw: object) -> tuple[WorkflowModelProfile, ...]:
        """Validate and parse an in-memory store dict (no I/O).

        Raises:
            LocalModelProfileStoreError: on any structural / harness / secret violation.
        """
        if not isinstance(raw, dict):
            raise LocalModelProfileStoreError(
                "operator-local model-profile store root is not an object"
            )
        # L8: reject any credential-shaped key anywhere in the document up front.
        _assert_no_secret_fields(raw, where="$")

        unknown = set(raw) - _ALLOWED_TOP_LEVEL
        if unknown:
            raise LocalModelProfileStoreError(
                "unknown top-level field(s) in operator-local model-profile store: "
                f"{', '.join(sorted(unknown))}"
            )
        if raw.get("schema_version") != _SCHEMA_VERSION:
            raise LocalModelProfileStoreError(
                "unsupported operator-local model-profile store schema version "
                f"{raw.get('schema_version')!r}; expected {_SCHEMA_VERSION!r}"
            )
        profiles_raw = raw.get("profiles", [])
        if not isinstance(profiles_raw, list):
            raise LocalModelProfileStoreError(
                "operator-local model-profile store 'profiles' must be an array"
            )
        profiles: list[WorkflowModelProfile] = []
        seen_ids: set[str] = set()
        for index, entry in enumerate(profiles_raw):
            profiles.append(self._parse_profile(entry, index=index, seen_ids=seen_ids))
        return tuple(profiles)

    def save(self, profiles: tuple[WorkflowModelProfile, ...]) -> None:
        """Atomically persist *profiles* (validated re-parse first, then temp+rename).

        Re-parsing the serialized form guarantees a saved store is always a loadable store
        (no write of a profile that ``load`` would later reject), and re-runs the L1/L8
        guards on the way out.
        """
        document = {
            "schema_version": _SCHEMA_VERSION,
            "profiles": [p.to_dict() for p in profiles],
        }
        # Validate before writing — a save must never persist an unloadable store.
        self.parse(document)
        self._atomic_write(self._path, json.dumps(document, indent=2, sort_keys=True))

    # -- validation -------------------------------------------------------

    def _parse_profile(
        self, entry: object, *, index: int, seen_ids: set[str]
    ) -> WorkflowModelProfile:
        where = f"profiles[{index}]"
        if not isinstance(entry, dict):
            raise LocalModelProfileStoreError(f"{where} must be an object")
        unknown = set(entry) - _ALLOWED_PROFILE_KEYS
        if unknown:
            raise LocalModelProfileStoreError(
                f"unknown field(s) in {where}: {', '.join(sorted(str(k) for k in unknown))}"
            )
        for required in ("id", "harness", "label", "model_id", "effort", "purpose"):
            if required not in entry:
                raise LocalModelProfileStoreError(f"{where} is missing required field {required!r}")
            if not isinstance(entry[required], str) or not str(entry[required]).strip():
                raise LocalModelProfileStoreError(f"{where}.{required} must be a non-empty string")
        profile_id = str(entry["id"])
        if profile_id in seen_ids:
            raise LocalModelProfileStoreError(
                f"{where} duplicates operator profile id {profile_id!r}"
            )
        seen_ids.add(profile_id)
        harness = str(entry["harness"])
        # L1: an operator profile may name only the PI Layer-2 harness this release.
        if harness != _OPERATOR_HARNESS:
            raise LocalModelProfileStoreError(
                f"{where} (id {profile_id!r}) names harness {harness!r}; operator-added "
                f"profiles must declare harness {_OPERATOR_HARNESS!r} this release (L1)"
            )
        # ``source`` is forced to a stable, inspectable provenance marker so a merged
        # operator profile is always distinguishable from a built-in (never spoofable as
        # "built-in").
        data = dict(entry)
        data["source"] = "operator-local"
        try:
            return WorkflowModelProfile.from_dict(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise LocalModelProfileStoreError(
                f"{where} is not a valid model profile: {exc}"
            ) from exc

    def _atomic_write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write((content + "\n").encode("utf-8"))
            os.replace(tmp_path, path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise


__all__ = [
    "JsonLocalModelProfileStore",
]
