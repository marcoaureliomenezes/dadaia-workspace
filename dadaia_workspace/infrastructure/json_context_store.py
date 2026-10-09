"""JsonContextStore — atomic CRUD over spec_contexts.json (schema v3).

Every write goes through ``atomic_write``; there is no lock. A v2 file reads like a v3
one — v3 only adds ``associated_repos``, which ``_from_dict`` defaults to empty.
"""

import json
from pathlib import Path
from typing import Any, cast

from dadaia_workspace.core import context_registry
from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.exceptions import SchemaVersionError
from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)

_VERSION = 3

# The keys every row carries: :func:`_from_dict` builds the model from them.
ROW_KEYS = ("name", "state", "repo_slug", "repo_url", "created_at")

# Legacy state values that mark a v1 row — the rows ``migrate`` rewrites.
LEGACY_STATES: frozenset[str] = frozenset({"ativo", "inativo"})


def parse_schema_version(data: dict, path: Path) -> int:  # type: ignore[type-arg]
    """THE registry version: 1 while any row is v1 or the stamp is below 2, else the stamp.

    A non-numeric or newer stamp raises."""
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
    """Load spec_contexts.json through the one parse; a v1 registry refuses with the one
    ``migrate --yes`` fix, a row missing a :data:`ROW_KEYS` key with an ``Operator action``."""
    data = context_registry.read(path)
    if parse_schema_version(data, path) < 2:
        problem = "spec_contexts.json holds v1 rows (ativo/inativo or schema_version < 2)."
        raise SchemaVersionError(problem, fix_line(path.parents[2], "migrate", "--yes"))
    for row in cast(
        "list[dict[str, object]]", data["contexts"]
    ):  # THE row check: every method reads through here
        if missing := [k for k in ROW_KEYS if k not in row]:
            raise SchemaVersionError(
                f"{path}: context row {row.get('name')!r} has no {', '.join(missing)}.",
                f"Operator action: add {', '.join(missing)} to that row of {path}",
            )
    return data


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
        self.states_dir = states_dir
        self._path = states_dir / "spec_contexts.json"

    def exists(self) -> bool:
        return self._path.exists()

    def read_raw(self) -> dict[str, Any]:
        return cast("dict[str, Any]", json.loads(self._path.read_text(encoding="utf-8")))

    def replace_raw(self, data: dict, *, newline: str | None = "") -> None:  # type: ignore[type-arg]
        atomic_write(self._path, json.dumps(data, indent=2), newline=newline)

    def snapshot(self) -> bytes | None:
        return self._path.read_bytes() if self._path.is_file() else None

    def restore(self, content: bytes | None) -> None:
        atomic_write(self._path, content)

    def save(self, ctx: SpecContextProject) -> None:
        data = _load(self._path)
        data["contexts"].append(_to_dict(ctx))
        self.replace_raw(data)

    def update(self, ctx: SpecContextProject) -> None:
        data = _load(self._path)
        data["contexts"] = [_to_dict(ctx) if c["name"] == ctx.name else c for c in data["contexts"]]
        self.replace_raw(data)

    def get(self, name: str) -> SpecContextProject | None:
        return next(
            (_from_dict(c) for c in _load(self._path)["contexts"] if c["name"] == name),
            None,
        )

    def list_all(self) -> list[SpecContextProject]:
        return [_from_dict(c) for c in _load(self._path)["contexts"]]

    def delete(self, name: str) -> None:
        data = _load(self._path)
        data["contexts"] = [c for c in data["contexts"] if c["name"] != name]
        self.replace_raw(data)
