"""`dadaia export` — one record per spec context, written to `.dadaia/dist/spec-contexts.json`."""

import json
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core import clock
from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.models.spec_context import (
    EXPORT_SCHEMA_VERSION,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.provider_version import provider_version


@dataclass(frozen=True)
class ExportResult:
    path: Path
    contexts: int


def _dadaia_version() -> str:
    return provider_version() or "editable"


def _record(ctx: SpecContextProject, last_sync_at: str | None) -> dict[str, object]:
    return {
        "slug": ctx.repo_slug,
        "name": ctx.name,
        "state": ctx.state.name,
        "repo_url": ctx.repo_url,
        "associated_repos": [{"slug": r.slug, "url": r.url} for r in ctx.associated_repos],
        "last_sync_at": last_sync_at,
    }


class ExportService:
    def __init__(
        self, context_store: JsonContextStore, git_client: GitSubprocessClient, workspace_root: Path
    ) -> None:
        self._store = context_store
        self._git = git_client
        self._workspace_root = workspace_root

    def _on_disk(self, ctx: SpecContextProject) -> bool:
        return (self._workspace_root / "repos" / ctx.repo_slug).is_dir()

    def run(self) -> ExportResult:
        now = clock.now_iso()
        rows = [
            (ctx, now if ctx.state is ContextState.ALIVE and self._on_disk(ctx) else ctx.dead_since)
            for ctx in self._store.list_all()
        ]
        payload = {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "exported_at": now,
            "dadaia_version": _dadaia_version(),
            "contexts": [_record(ctx, synced_at) for ctx, synced_at in rows],
        }
        path = self._workspace_root / ".dadaia" / "dist" / "spec-contexts.json"
        atomic_write(path, json.dumps(payload, indent=2) + "\n", ensure_parent=True)
        return ExportResult(path=path, contexts=len(rows))
