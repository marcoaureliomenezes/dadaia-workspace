"""`dadaia export` — the `export-v1` artifact of the registry, read-only: soft is
`.dadaia/dist/spec-contexts.json`, hard is `.dadaia/dist/workspace-export.tar.gz` (the JSON plus
a bundle of each open lane and `wt-rc` tree and each pause bundle)."""

import io
import json
import os
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.spec_context import EXPORT_SCHEMA_VERSION, SpecContextProject
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.ledger_scripts import worktree_rows
from dadaia_workspace.infrastructure.provider_version import provider_version

_names = load_owner("dd-gitflow-default", "_worktree_names")
_flow = load_owner("dd-gitflow-default", "_worktree_git")
_end = load_owner("dd-gitflow-default", "_worktree_end")
_pause = load_owner("dd-gitflow-default", "_worktree_pause")
_REFUSED = (
    load_owner("dd-bug-resolution", "_refusal").Refusal,
    load_owner("dd-bug-resolution", "_git").GitError,
)


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
        dist = self._workspace_root / ".dadaia" / "dist"
        states = self._workspace_root / ".dadaia" / "states"
        payload = {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "dadaia_version": provider_version() or "editable",
            "harnesses": list(
                JsonHarnessProfileStore().resolve(states, self._workspace_root).harnesses
            ),
            "contexts": [_record(ctx) for ctx in contexts],
        }
        text = json.dumps(payload, indent=2) + "\n"
        if hard:
            slugs = {
                r.slug
                for ctx in contexts
                for r in ctx.all_repos()
                if (self._workspace_root / "repos" / r.slug).is_dir()
            }
            return ExportResult(self._archive(text, slugs, dist), len(contexts))
        path = dist / "spec-contexts.json"
        atomic_write(path, text, ensure_parent=True)
        return ExportResult(path=path, contexts=len(contexts))

    def _bundles(self, slugs: set[str], dist: Path, scratch: Path) -> dict[str, Path]:
        """`<repo>/<name>.bundle` -> file: pause's bundles as they sit, and a commits-only bundle,
        made in *scratch*, of each open lane and `wt-rc` tree that holds a commit origin lacks."""
        rows, failed, fix = worktree_rows(self._workspace_root, slugs) if slugs else ([], "", "")
        if failed:
            raise DadaiaError(f"export cannot read the worktrees: {failed}", fix=fix)
        home, found = (self._workspace_root / "worktrees").resolve(), {}
        for row in rows:
            tree = Path(row["path"])
            arc = f"{tree.resolve().relative_to(home).as_posix()}.bundle"
            if row["state"] == "paused":
                found[arc] = dist / arc
            elif row["kind"] in ("backlog", "hotfix", "rc") and row["state"] in ("ready", "open"):
                repo, ref = self._workspace_root / "repos" / row["repo"], _names.branch(row["name"])
                _end._refuse_dirty(tree)
                if (
                    _flow.git(repo, "rev-list", "--count", ref, "--not", "--remotes=origin").strip()
                    != "0"
                ):
                    _pause.write_bundle(repo, ref, scratch / arc)
                    found[arc] = scratch / arc
        return found

    def _archive(self, text: str, slugs: set[str], dist: Path) -> Path:
        tmp = self._workspace_root / ".dadaia" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp, prefix="export-") as scratch:
            try:
                bundles = self._bundles(slugs, dist, Path(scratch))
            except _REFUSED as exc:
                raise DadaiaError(str(exc), fix=getattr(exc, "fix", "")) from exc
            built = Path(scratch) / "workspace-export.tar.gz"
            with tarfile.open(built, "w:gz") as tar:
                data = text.encode()
                member = tarfile.TarInfo("spec-contexts.json")
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
                for arc, file in sorted(bundles.items()):
                    tar.add(file, arcname=arc)
            dist.mkdir(parents=True, exist_ok=True)
            os.replace(built, dist / built.name)
        return dist / "workspace-export.tar.gz"
