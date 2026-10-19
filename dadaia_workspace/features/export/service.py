"""`dadaia export` — the `export-v1` artifact of the registry, read-only: `.dadaia/dist/spec-contexts.json`."""

import json
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.models.spec_context import EXPORT_SCHEMA_VERSION, SpecContextProject
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.provider_version import provider_version


@dataclass(frozen=True)
class ExportResult:
    path: Path
    contexts: int


def _record(ctx: SpecContextProject) -> dict[str, object]:
    return {
        "slug": ctx.repo_slug,
        "name": ctx.name,
        "state": ctx.state.value,
        "repo_url": ctx.repo_url or None,
        "associated_repos": [{"slug": r.slug, "url": r.url or None} for r in ctx.associated_repos],
    }


class ExportService:
    def __init__(self, context_store: JsonContextStore, workspace_root: Path) -> None:
        self._store = context_store
        self._workspace_root = workspace_root

    def run(self, hard: bool = False) -> ExportResult:
        """Writes the artifact and returns its path; the registry is only read."""
        contexts = self._store.list_all()
        states = self._workspace_root / ".dadaia" / "states"
        payload = {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "dadaia_version": provider_version() or "editable",
            "harnesses": list(
                JsonHarnessProfileStore().resolve(states, self._workspace_root).harnesses
            ),
            "contexts": [_record(ctx) for ctx in contexts],
        }
        path = self._workspace_root / ".dadaia" / "dist" / "spec-contexts.json"
        atomic_write(path, json.dumps(payload, indent=2) + "\n", ensure_parent=True)
        return ExportResult(path=path, contexts=len(contexts))
