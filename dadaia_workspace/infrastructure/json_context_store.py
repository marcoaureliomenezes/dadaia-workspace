"""JsonContextStore — atomic CRUD over spec_contexts.json (schema v2).

NOTE: _load must NOT be called outside SpecContextService methods.
Calling it directly bypasses the fcntl lock (introduced in T-11) and re-opens
the concurrent-write race R-1.
"""

import json
from pathlib import Path

from dadaia_workspace.core.exceptions import SchemaVersionError
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.infrastructure.public_assets_common import _atomic_write_text

_VERSION = "2"

# Legacy state values that indicate a v1 file (used only by the migration path — T-10c)
_LEGACY_STATES: frozenset[str] = frozenset({"ativo", "inativo"})


def _load(path: Path) -> dict:  # type: ignore[type-arg]
    """Load spec_contexts.json.  Raises SchemaVersionError on v1 files.

    Must NOT be called outside SpecContextService methods — see module docstring.
    """
    if not path.exists():
        return {"schema_version": _VERSION, "contexts": []}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    # Detect v1 by explicit schema_version field
    schema_ver = data.get("schema_version") or data.get("version")
    if schema_ver == "1":
        raise SchemaVersionError(
            "[MIGRATION REQUIRED] This workspace uses spec_contexts.json v1.\n"
            "Run: dadaia migrate\n"
            "After migration, all v2 commands will work normally."
        )

    # Detect v1 by legacy state values in context rows
    for ctx in data.get("contexts", []):
        if ctx.get("state") in _LEGACY_STATES:
            raise SchemaVersionError(
                "[MIGRATION REQUIRED] This workspace uses spec_contexts.json v1.\n"
                "Run: dadaia migrate\n"
                "After migration, all v2 commands will work normally."
            )

    # Unknown schema version — fail loudly
    if schema_ver not in (None, _VERSION):
        raise SchemaVersionError(
            f"[MIGRATION REQUIRED] Unknown schema_version '{schema_ver}' in spec_contexts.json.\n"
            "Run: dadaia migrate\n"
            "After migration, all v2 commands will work normally."
        )

    return data  # type: ignore[no-any-return]


def _to_dict(ctx: SpecContextProject) -> dict:  # type: ignore[type-arg]
    return {
        "name": ctx.name,
        "state": ctx.state.value,
        "repo_slug": ctx.repo_slug,
        "repo_url": ctx.repo_url,
        "created_at": ctx.created_at,
        "alive_since": ctx.alive_since,
        "dead_since": ctx.dead_since,
        "current_branch": ctx.current_branch,
    }


def _from_dict(d: dict) -> SpecContextProject:  # type: ignore[type-arg]
    return SpecContextProject(
        name=d["name"],
        state=ContextState(d["state"]),
        repo_slug=d["repo_slug"],
        repo_url=d["repo_url"],
        created_at=d["created_at"],
        alive_since=d.get("alive_since"),
        dead_since=d.get("dead_since"),
        current_branch=d.get("current_branch"),
    )


class JsonContextStore:
    def __init__(self, states_dir: Path) -> None:
        self._path = states_dir / "spec_contexts.json"

    def save(self, ctx: SpecContextProject) -> None:
        data = _load(self._path)
        data["contexts"].append(_to_dict(ctx))
        _atomic_write_text(self._path, json.dumps(data, indent=2))

    def update(self, ctx: SpecContextProject) -> None:
        data = _load(self._path)
        data["contexts"] = [_to_dict(ctx) if c["name"] == ctx.name else c for c in data["contexts"]]
        _atomic_write_text(self._path, json.dumps(data, indent=2))

    def get(self, name: str) -> SpecContextProject | None:
        data = _load(self._path)
        for c in data["contexts"]:
            if c["name"] == name:
                return _from_dict(c)
        return None

    def list_all(self) -> list[SpecContextProject]:
        data = _load(self._path)
        return [_from_dict(c) for c in data["contexts"]]

    def delete(self, name: str) -> None:
        data = _load(self._path)
        data["contexts"] = [c for c in data["contexts"] if c["name"] != name]
        _atomic_write_text(self._path, json.dumps(data, indent=2))
