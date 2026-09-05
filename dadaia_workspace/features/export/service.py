"""`dadaia export` — one record per spec context, written to `.dadaia/dist/spec-contexts.json`."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.models.export import SCHEMA_VERSION, ExportResult
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore


def _dadaia_version() -> str:
    try:
        return version("dadaia-workspace")
    except PackageNotFoundError:
        return "editable"


def _record(ctx: SpecContextProject, last_sync_at: str | None) -> dict[str, object]:
    return {
        "slug": ctx.repo_slug,
        "name": ctx.name,
        "state": ctx.state.name,
        "repo_url": ctx.repo_url,
        "branch": ctx.current_branch,
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

    def _refresh_branches(self, now: str) -> list[tuple[SpecContextProject, str | None]]:
        """Re-read the checked-out branch of every ALIVE repo on disk and write it through
        the store with ``dataclasses.replace`` — a field-by-field rebuild once dropped
        ``associated_repos`` from the live store (T-044-29). Returns each context with the
        instant it was synced: ``now`` when refreshed, else its ``dead_since``."""
        rows: list[tuple[SpecContextProject, str | None]] = []
        for ctx in self._store.list_all():
            repo = self._workspace_root / "repos" / ctx.repo_slug
            if ctx.state is ContextState.ALIVE and repo.is_dir():
                ctx = replace(ctx, current_branch=self._git.current_branch(repo))
                self._store.update(ctx)
                rows.append((ctx, now))
            else:
                rows.append((ctx, ctx.dead_since))
        return rows

    def run(self) -> ExportResult:
        now = datetime.now(tz=UTC).isoformat()
        rows = self._refresh_branches(now)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "exported_at": now,
            "dadaia_version": _dadaia_version(),
            "contexts": [_record(ctx, synced_at) for ctx, synced_at in rows],
        }
        path = self._workspace_root / ".dadaia" / "dist" / "spec-contexts.json"
        atomic_write(path, json.dumps(payload, indent=2) + "\n", ensure_parent=True)
        return ExportResult(path=path, contexts=len(rows))
