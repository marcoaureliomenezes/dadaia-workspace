"""JsonContextStore — atomic CRUD over spec_contexts.json."""

import json
import os
from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject

_VERSION = "1"


def _load(path: Path) -> dict:  # type: ignore[type-arg]
    if not path.exists():
        return {"version": _VERSION, "contexts": []}
    with path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def _dump(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def _to_dict(ctx: SpecContextProject) -> dict:  # type: ignore[type-arg]
    return {
        "name": ctx.name,
        "state": ctx.state.value,
        "repo_slug": ctx.repo_slug,
        "repo_url": ctx.repo_url,
        "is_primary": ctx.is_primary,
        "created_at": ctx.created_at,
        "activated_at": ctx.activated_at,
    }


def _from_dict(d: dict) -> SpecContextProject:  # type: ignore[type-arg]
    return SpecContextProject(
        name=d["name"],
        state=ContextState(d["state"]),
        repo_slug=d["repo_slug"],
        repo_url=d["repo_url"],
        is_primary=d["is_primary"],
        created_at=d["created_at"],
        activated_at=d.get("activated_at"),
    )


class JsonContextStore:
    def __init__(self, states_dir: Path) -> None:
        self._path = states_dir / "spec_contexts.json"

    def save(self, ctx: SpecContextProject) -> None:
        data = _load(self._path)
        data["contexts"].append(_to_dict(ctx))
        _dump(self._path, data)

    def update(self, ctx: SpecContextProject) -> None:
        data = _load(self._path)
        data["contexts"] = [_to_dict(ctx) if c["name"] == ctx.name else c for c in data["contexts"]]
        _dump(self._path, data)

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
        _dump(self._path, data)
