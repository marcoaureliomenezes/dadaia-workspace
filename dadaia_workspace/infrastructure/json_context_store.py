"""JsonContextStore — atomic CRUD over spec_contexts.json (schema v3).

Every write goes through ``atomic_write``; there is no lock. A v2 file reads like a v3
one — v3 only adds ``associated_repos``, which ``_from_dict`` defaults to empty.
"""

import json
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.exceptions import SchemaVersionError
from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)

_VERSION = 3

# Legacy state values that mark a v1 row — the rows ``migrate`` rewrites.
LEGACY_STATES: frozenset[str] = frozenset({"ativo", "inativo"})


def parse_schema_version(data: dict, path: Path) -> int:  # type: ignore[type-arg]
    """THE registry-version grammar (the store, ``migrate``, the doctor): 1 while any row
    is v1 or the stamp (int or digit string; absent = current) is below 2, else the stamp.
    A stamp no dadaia verb can migrate — non-numeric or newer — raises."""
    raw = data.get("schema_version", data.get("version"))
    text = str(_VERSION if raw is None else raw)
    if isinstance(raw, bool) or not text.isdigit():
        problem = f"spec_contexts.json schema_version {raw!r} is not a number."
        raise SchemaVersionError(problem, f"Operator action: set it to {_VERSION} in {path}")
    if int(text) > _VERSION:
        problem = f"spec_contexts.json schema_version {text} is newer than this dadaia."
        raise SchemaVersionError(
            problem, f"Operator action: upgrade dadaia-workspace to read {path}"
        )
    legacy = any(c.get("state") in LEGACY_STATES for c in data.get("contexts", []))
    return 1 if legacy or int(text) < 2 else int(text)


def _load(path: Path) -> dict:  # type: ignore[type-arg]
    """Load spec_contexts.json; a v1 registry refuses with the one ``migrate --yes`` fix."""
    if not path.exists():
        return {"schema_version": str(_VERSION), "contexts": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if parse_schema_version(data, path) < 2:
        problem = "spec_contexts.json holds v1 rows (ativo/inativo or schema_version < 2)."
        raise SchemaVersionError(problem, fix_line(path.parents[2], "migrate", "--yes"))
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
        "associated_repos": [{"slug": r.slug, "url": r.url} for r in ctx.associated_repos],
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
        associated_repos=tuple(
            AssociatedRepo(slug=r["slug"], url=r["url"]) for r in d.get("associated_repos") or []
        ),
    )


class JsonContextStore:
    def __init__(self, states_dir: Path) -> None:
        self._path = states_dir / "spec_contexts.json"

    def save(self, ctx: SpecContextProject) -> None:
        data = _load(self._path)
        data["contexts"].append(_to_dict(ctx))
        atomic_write(self._path, json.dumps(data, indent=2))

    def update(self, ctx: SpecContextProject) -> None:
        data = _load(self._path)
        data["contexts"] = [_to_dict(ctx) if c["name"] == ctx.name else c for c in data["contexts"]]
        atomic_write(self._path, json.dumps(data, indent=2))

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
        atomic_write(self._path, json.dumps(data, indent=2))
