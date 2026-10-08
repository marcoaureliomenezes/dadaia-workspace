"""`dadaia import` — registers every unknown context of a `spec-contexts.json` as DEAD (FR13)."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.exceptions import (
    AssociatedRepoConflictError,
    ContextAlreadyExistsError,
    InvalidContextNameError,
    RepoUrlMissingError,
    SchemaVersionError,
)
from dadaia_workspace.core.models.spec_context import (
    EXPORT_SCHEMA_VERSION,
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)


@dataclass(frozen=True)
class ImportResult:
    registered: tuple[str, ...]
    #: ``(name, reason)`` — ``"exists"`` for a known name, else the registry guard's refusal.
    skipped: tuple[tuple[str, str], ...]


class ContextRegistry(Protocol):
    """The guarded registry insert — ``SpecContextService.register``, wired by the container
    (features compose there, never by sibling import). Import never writes the store itself,
    so an imported record is refused exactly as ``context create`` refuses it."""

    def register(self, ctx: SpecContextProject) -> SpecContextProject: ...


def _require(file: Path, record: object, *keys: str) -> None:
    absent = [k for k in keys if not isinstance(record, dict) or k not in record]
    if absent:
        raise SchemaVersionError(
            f"'{file.name}' has a record missing {', '.join(absent)}.",
            fix_line(None, "export"),
        )


def _read(file: Path) -> list[dict[str, object]]:
    if not file.is_file():
        raise ValueError(
            f"Export file not found: '{file}'. Generate it with '{fix_line(None, 'export')}'."
        )
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"'{file.name}' is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != EXPORT_SCHEMA_VERSION:
        raise ValueError(
            f"'{file.name}' does not carry schema_version {EXPORT_SCHEMA_VERSION!r}; "
            f"only '{fix_line(None, 'export')}' output is supported."
        )
    contexts = payload.get("contexts")
    if not isinstance(contexts, list) or not all(isinstance(c, dict) for c in contexts):
        raise ValueError(f"'{file.name}' has no 'contexts' list.")
    for c in contexts:
        _require(file, c, "name", "slug", "repo_url")
        for r in c.get("associated_repos") or []:
            _require(file, r, "slug", "url")
    return contexts


def _dead_context(record: dict[str, object], now: str) -> SpecContextProject:
    branch = record.get("branch")
    repos = record.get("associated_repos")
    return SpecContextProject(
        name=str(record["name"]),
        state=ContextState.DEAD,
        repo_slug=str(record["slug"]),
        repo_url=str(record["repo_url"]),
        created_at=now,
        dead_since=now,
        current_branch=None if branch is None else str(branch),
        associated_repos=tuple(
            AssociatedRepo(slug=str(r["slug"]), url=str(r["url"]))
            for r in (repos if isinstance(repos, list) else [])
        ),
    )


class ImportService:
    def __init__(self, registry: ContextRegistry) -> None:
        self._registry = registry

    def run(self, file: Path) -> ImportResult:
        now = datetime.now(tz=UTC).isoformat()
        registered: list[str] = []
        skipped: list[tuple[str, str]] = []
        for record in _read(file):
            ctx = _dead_context(record, now)
            try:
                self._registry.register(ctx)
            except ContextAlreadyExistsError:
                skipped.append((ctx.name, "exists"))
            except (
                InvalidContextNameError,
                AssociatedRepoConflictError,
                RepoUrlMissingError,
            ) as exc:
                skipped.append((ctx.name, str(exc)))
            else:
                registered.append(ctx.name)
        return ImportResult(registered=tuple(registered), skipped=tuple(skipped))
