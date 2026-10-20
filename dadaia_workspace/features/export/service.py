"""`dadaia export` — the `export-v1` artifact of the registry, read-only: soft is
`.dadaia/dist/spec-contexts.json`, hard is `.dadaia/dist/workspace-export.tar.gz` (the JSON plus
a bundle of each open lane and `wt-rc` tree and each pause bundle)."""

import io
import json
import re
import tarfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core import clock, harness_registry, platform
from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.cli_line import cli_words, fix_line
from dadaia_workspace.core.exceptions import DadaiaError, SchemaVersionError
from dadaia_workspace.core.models.spec_context import (
    EXPORT_SCHEMA_VERSION,
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.core.platform import act
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.features.export.scan import new_scratch
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


@dataclass(frozen=True)
class Artifact:
    """A read `export-v1` artifact: its harness names, every context as a DEAD record (a null
    url read as ``""``), and the names that were ALIVE where it was written."""

    harnesses: tuple[str, ...]
    contexts: tuple[SpecContextProject, ...]
    alive: tuple[str, ...]

    def slugs(self) -> set[str]:
        """The repo slugs the artifact's contexts own: the only folders its bundles may fill."""
        return {r.slug for c in self.contexts for r in c.all_repos()}


#: A hard artifact's only members besides the JSON: `<repo>/<name>.bundle`, never a `.`/`..` step.
_BUNDLE = re.compile(r"[A-Za-z0-9][\w.-]*(/[\w.-]+)+\.bundle")
_JSON_MEMBER = "spec-contexts.json"
_JSON_CAP = 8 << 20
_ledger = load_owner("dd-bug-resolution", "_ledger")


def _refuse(why: str, fix: str = "") -> SchemaVersionError:
    return SchemaVersionError(
        why, fix or act("agent", "re-export the artifact with the current dadaia-workspace")
    )


def _members(
    tar: tarfile.TarFile, name: str, slugs: set[str] | None = None
) -> list[tarfile.TarInfo]:
    """The bundle members of *tar*, each checked: the JSON once and within its cap, every other a
    regular `<repo>/<name>.bundle` file named once and, when *slugs* is given, of one of those
    repos. Raises `SchemaVersionError` on the first member that is not."""
    seen: set[str] = set()
    bundles = []
    for member in tar.getmembers():
        if member.name in seen:
            raise _refuse(f"'{name}' has a duplicate member {member.name!r}.")
        seen.add(member.name)
        if member.name == _JSON_MEMBER:
            if member.isfile() and member.size > _JSON_CAP:
                raise _refuse(f"'{name}' has a {_JSON_MEMBER} larger than {_JSON_CAP} bytes.")
        elif not (
            member.isfile()
            and _BUNDLE.fullmatch(member.name)
            and not {".", ".."} & set(member.name.split("/"))
        ):
            raise _refuse(f"'{name}' has an unsafe member: {member.name!r}.")
        elif slugs is not None and member.name.split("/")[0] not in slugs:
            raise _refuse(f"'{name}' has {member.name!r}, which no context of the artifact owns.")
        else:
            bundles.append(member)
    return bundles


def _free(dist: Path, bundles: list[tarfile.TarInfo]) -> None:
    """Refuses the first bundle that already sits in *dist*: a file there can be the only copy."""
    if taken := next((dist / m.name for m in bundles if (dist / m.name).exists()), None):
        raise _refuse(
            f"{taken} already exists.", act("agent", f"move {taken} out of {dist}, then run again")
        )


def _text(path: Path) -> str:
    """The artifact's JSON text; a hard artifact's members are all checked first."""
    if not path.is_file():
        export = platform.inline(*cli_words(None, "export"))
        raise _refuse(
            f"Export file not found: '{path}'.", act("agent", f"pass a file written by `{export}`")
        )
    try:
        if not tarfile.is_tarfile(path):
            return platform.read_text(path)
        with tarfile.open(path) as tar:
            _members(tar, path.name)
            head = tar.extractfile(_JSON_MEMBER) if _JSON_MEMBER in tar.getnames() else None
            if head is None:
                raise _refuse(f"'{path.name}' has no {_JSON_MEMBER}.")
            return head.read().decode()
    except (tarfile.TarError, OSError, UnicodeDecodeError) as exc:
        raise _refuse(f"'{path.name}' is not readable ({type(exc).__name__}).") from exc


ScanBundle = Callable[[Path, Path], dict[str, str]]
"""``(bundle, repo)`` -> one masked finding per offending path of the objects the bundle adds."""


class ExportService:
    def __init__(
        self, context_store: JsonContextStore, workspace_root: Path, scan_bundle: ScanBundle
    ) -> None:
        self._scan = scan_bundle
        self._store = context_store
        self._workspace_root = workspace_root

    @staticmethod
    def read(path: Path, into: Path | None = None) -> Artifact:
        """The artifact at *path*, soft or hard, checked and written nowhere. Raises
        `SchemaVersionError` (one fix line) on a missing or unreadable file, anything
        `export-v1.schema.json` refuses, an unknown harness, or a member that is unsafe,
        repeated, oversized or owned by no context, or (with *into*, a workspace root) a bundle
        already in its `dist`. A null url reads as `""`."""
        try:
            payload = json.loads(_text(path))
        except json.JSONDecodeError as exc:
            raise _refuse(f"'{path.name}' is not valid JSON: {exc}") from exc
        schema = _ledger.load_schema("export-v1")
        if problems := list(_ledger.validate(payload, schema, schema, "export")):
            raise _refuse(
                f"'{path.name}' is not an {EXPORT_SCHEMA_VERSION} artifact: " + "; ".join(problems)
            )
        try:
            harnesses = tuple(harness_registry.parse_harness_name(n) for n in payload["harnesses"])
        except ValueError as exc:
            raise _refuse(f"'{path.name}' names an unknown harness: {exc}") from exc
        now = clock.now_iso()
        contexts = tuple(
            SpecContextProject(
                name=r["name"],
                state=ContextState.DEAD,
                repo_slug=r["slug"],
                repo_url=r["repo_url"] or "",
                created_at=now,
                dead_since=now,
                associated_repos=tuple(
                    AssociatedRepo(a["slug"], a["url"] or "") for a in r["associated_repos"]
                ),
            )
            for r in payload["contexts"]
        )
        alive = tuple(r["name"] for r in payload["contexts"] if r["state"] == "alive")
        artifact = Artifact(harnesses, contexts, alive)
        if tarfile.is_tarfile(path):
            with tarfile.open(path) as tar:
                bundles = _members(tar, path.name, artifact.slugs())
            if into:
                _free(into / ".dadaia" / "dist", bundles)
        return artifact

    def restore(self, path: Path, artifact: Artifact) -> None:
        """Extracts a hard artifact's bundles to `.dadaia/dist/<repo>/<name>.bundle`, where
        `worktree resume` finds them; a soft artifact has none. Members are checked as `read`
        checks them and extracted with `filter="data"`, streamed to disk; a file already in
        `dist` refuses, before any write, and is never overwritten."""
        if not tarfile.is_tarfile(path):
            return
        dist = self._workspace_root / ".dadaia" / "dist"
        try:
            with tarfile.open(path) as tar:
                bundles = _members(tar, path.name, artifact.slugs())
                _free(dist, bundles)
                dist.mkdir(parents=True, exist_ok=True)
                tar.extractall(dist, bundles, filter="data")
        except (tarfile.TarError, OSError) as exc:
            raise _refuse(f"'{path.name}' cannot be extracted ({type(exc).__name__}).") from exc

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
            elif row["state"] in ("ready", "open", "empty"):
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
        with new_scratch(self._workspace_root / ".dadaia" / "tmp", "export-") as scratch:
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
