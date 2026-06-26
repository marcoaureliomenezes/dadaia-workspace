"""Workspace export feature — packages durable state into a portable .tar.gz."""

import io
import json
import sys
import tarfile
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.models.export import ExportManifest, ExportOptions, ExportResult
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient

_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {".npm", ".npm-global", ".cache", ".local", "linuxbrew", ".venv", "tmp", "contexts"}
)


def _exclude_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
    parts = Path(tarinfo.name).parts
    if any(p in _EXCLUDED_DIR_NAMES for p in parts):
        return None
    if tarinfo.name.endswith(".env"):
        return None
    return tarinfo


def _dadaia_version() -> str:
    try:
        from importlib.metadata import version

        return version("dadaia-workspace")
    except Exception:
        return "unknown"


class ExportService:
    def __init__(
        self, context_store: ContextStore, git_client: GitClient, workspace_root: Path
    ) -> None:
        self._store = context_store
        self._git = git_client
        self._workspace_root = workspace_root

    def resolve_includes(self, options: ExportOptions) -> list[tuple[Path, str]]:
        root = self._workspace_root
        dadaia = root / ".dadaia"
        includes: list[tuple[Path, str]] = []

        def _add_if_exists(src: Path, arc: str) -> None:
            if src.exists():
                if src.is_file() and src.name.endswith(".env"):
                    print(f"WARNING: skipping .env file: {src}", file=sys.stderr)
                    return
                includes.append((src, arc))

        _add_if_exists(dadaia / "states", ".dadaia/states")
        _add_if_exists(dadaia / "academy", ".dadaia/academy")

        if options.include_reports:
            _add_if_exists(dadaia / "reports", ".dadaia/reports")

        for name in ("CLAUDE.md", "AGENTS.md"):
            _add_if_exists(root / name, name)

        _add_if_exists(root / ".agents" / "skills", ".agents/skills")

        claude = root / ".claude"
        _add_if_exists(claude / "settings.json", ".claude/settings.json")
        _add_if_exists(claude / "settings.local.json", ".claude/settings.local.json")
        _add_if_exists(claude / "rules", ".claude/rules")

        codex = root / ".codex"
        _add_if_exists(codex / "config.toml", ".codex/config.toml")
        _add_if_exists(codex / "hooks.json", ".codex/hooks.json")
        _add_if_exists(codex / "rules", ".codex/rules")

        mnt = root / "mnt"
        if not options.exclude_mnt and mnt.exists():
            includes.append((mnt, "mnt"))

        return includes

    def _refresh_branches(self) -> None:
        for ctx in self._store.list_all():
            if ctx.state != ContextState.ALIVE:
                continue
            repo_path = self._workspace_root / "repos" / ctx.repo_slug
            if not repo_path.exists():
                continue
            try:
                branch = self._git.current_branch(repo_path)
                updated = SpecContextProject(
                    name=ctx.name,
                    state=ctx.state,
                    repo_slug=ctx.repo_slug,
                    repo_url=ctx.repo_url,
                    created_at=ctx.created_at,
                    alive_since=ctx.alive_since,
                    dead_since=ctx.dead_since,
                    current_branch=branch,
                )
                self._store.update(updated)
            except Exception:
                pass

    def build_manifest(
        self, includes: list[tuple[Path, str]], options: ExportOptions
    ) -> ExportManifest:
        try:
            contexts: tuple[dict[str, object], ...] = tuple(
                {
                    "name": ctx.name,
                    "repo_url": ctx.repo_url,
                    "state": ctx.state,
                    "current_branch": ctx.current_branch,
                }
                for ctx in self._store.list_all()
            )
        except Exception:
            print(
                "WARNING: could not read spec_contexts.json — contexts list will be empty",
                file=sys.stderr,
            )
            contexts = ()

        arc_names = tuple(arc for _, arc in includes)
        mnt_included = any(arc == "mnt" or arc.startswith("mnt/") for arc in arc_names)

        return ExportManifest(
            version="1",
            exported_at=datetime.now(tz=UTC).isoformat(),
            workspace_root=str(self._workspace_root),
            dadaia_version=_dadaia_version(),
            contexts=contexts,
            includes=arc_names,
            mnt_included=mnt_included,
            reports_included=options.include_reports,
            total_size_bytes=0,
        )

    def create_archive(
        self,
        includes: list[tuple[Path, str]],
        manifest: ExportManifest,
        output_dir: Path,
    ) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        archive_path = output_dir / f"workspace-{timestamp}.tar.gz"

        manifest_bytes = json.dumps(asdict(manifest), indent=2).encode()

        with tarfile.open(archive_path, "w:gz") as tar:
            manifest_info = tarfile.TarInfo(name="export-manifest.json")
            manifest_info.size = len(manifest_bytes)
            tar.addfile(manifest_info, io.BytesIO(manifest_bytes))

            for src, arc_name in includes:
                tar.add(src, arcname=arc_name, recursive=True, filter=_exclude_filter)

        return archive_path

    def run(self, options: ExportOptions) -> ExportResult:
        output_dir = (
            options.output
            if options.output is not None
            else self._workspace_root / ".dadaia" / "dist"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        self._refresh_branches()
        includes = self.resolve_includes(options)
        manifest = self.build_manifest(includes, options)

        if options.list_only:
            print(json.dumps(asdict(manifest), indent=2))
            return ExportResult(path=None, size=0, manifest=manifest)

        archive_path = self.create_archive(includes, manifest, output_dir)
        final_size = archive_path.stat().st_size
        manifest = replace(manifest, total_size_bytes=final_size)
        return ExportResult(path=archive_path, size=final_size, manifest=manifest)
