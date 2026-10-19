"""`dadaia export` — the `export-v1` artifact of the registry, read-only: soft is
`.dadaia/dist/spec-contexts.json`, hard is `.dadaia/dist/workspace-export.tar.gz` (the JSON plus
a bundle of each open lane and `wt-rc` tree and each pause bundle)."""

import io
import json
import tarfile
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core import platform
from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.spec_context import EXPORT_SCHEMA_VERSION, SpecContextProject
from dadaia_workspace.core.platform import act
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.ledger_scripts import worktree_rows
from dadaia_workspace.infrastructure.provider_version import provider_version

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


_CARRIED = ("backlog", "hotfix", "rc")
"""The kinds of tree an export carries: the lanes and the `wt-rc`; a job or task tree is not."""

ScanBundle = Callable[[Path, Path], dict[str, str]]
"""``(bundle, repo)`` -> one masked finding per offending path of the objects the bundle adds."""


class ExportService:
    def __init__(
        self, context_store: JsonContextStore, workspace_root: Path, scan_bundle: ScanBundle
    ) -> None:
        self._scan = scan_bundle
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
            owners = {r.slug: ctx.name for ctx in contexts for r in ctx.all_repos()}
            return ExportResult(self._archive(text, owners, dist), len(contexts))
        path = dist / "spec-contexts.json"
        atomic_write(path, text, ensure_parent=True)
        return ExportResult(path=path, contexts=len(contexts))

    def _bundles(self, owners: dict[str, str], dist: Path, scratch: Path) -> dict[str, Path]:
        """`<repo>/<name>.bundle` -> file, from the owner's rows alone: pause's bundles as they sit,
        and a commits-only bundle, made in *scratch*, of each lane and `wt-rc` tree."""
        rows, failed, fix = worktree_rows(self._workspace_root, set(owners))
        if failed:
            raise DadaiaError(f"export cannot read the worktrees: {failed}", fix=fix)
        found: dict[str, Path] = {}
        for row in (r for r in rows if r["repo"] in owners):
            name = row.get("name")
            if row["state"] == "paused":
                member = _pause.member(row["repo"], name)
                found[member] = dist / member
            elif row.get("kind") in _CARRIED and row["state"] in ("ready", "open", "empty"):
                repo = self._workspace_root / "repos" / row["repo"]
                if bundled := _pause.carry(repo, Path(row["path"]), name, scratch):
                    found[bundled] = scratch / bundled
        return found

    def _scanned(self, bundles: dict[str, Path], owners: dict[str, str]) -> list[str]:
        """One masked finding per offending path of *bundles*; a symlink, or a bundle whose repo
        is not checked out (nothing to scan it against), refuses."""
        hits = []
        for arc, file in sorted(bundles.items()):
            repo = self._workspace_root / "repos" / arc.split("/")[0]
            if file.is_symlink():
                raise DadaiaError(
                    f"{arc} is a symlink; an archive carries bundle files only",
                    fix=act("agent", f"replace {file} with the bundle file itself, then export"),
                )
            if not repo.is_dir():
                raise DadaiaError(
                    f"{arc} cannot be scanned: its repo is not checked out",
                    fix=fix_line(
                        self._workspace_root, "context", "alive", owners[arc.split("/")[0]]
                    ),
                )
            hits += [f"{arc}: {path}: {why}" for path, why in self._scan(file, repo).items()]
        return hits

    def _archive(self, text: str, owners: dict[str, str], dist: Path) -> Path:
        tmp = self._workspace_root / ".dadaia" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp, prefix="export-") as scratch:
            try:
                bundles = self._bundles(owners, dist, Path(scratch))
            except _REFUSED as exc:
                raise DadaiaError(str(exc), fix=getattr(exc, "fix", "")) from exc
            if hits := self._scanned(bundles, owners):
                raise DadaiaError(
                    "export blocked, no archive written: a bundle holds a secret or a denylisted "
                    "term (values redacted):\n" + "\n".join(hits),
                    fix=act(
                        "agent", "remove each value from its commit, then run the export again"
                    ),
                )
            built = Path(scratch) / "workspace-export.tar.gz"
            with tarfile.open(built, "w:gz") as tar:
                data = text.encode()
                head = tarfile.TarInfo("spec-contexts.json")
                head.size = len(data)
                tar.addfile(head, io.BytesIO(data))
                for arc, file in sorted(bundles.items()):
                    tar.add(file, arcname=arc)
            dist.mkdir(parents=True, exist_ok=True)
            platform.replace(built, dist / built.name)
        return dist / "workspace-export.tar.gz"
