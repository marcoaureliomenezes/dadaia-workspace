"""SpecContextService — full Spec Context Project lifecycle."""

import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    GitSyncError,
)
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.core.protocols.primary_context_store import PrimaryContextStore

# Canonical scaffold source — lives inside the installed package
_PUBLIC_DIR = Path(__file__).parent.parent.parent / "public"
_SCAFFOLD_SRC = _PUBLIC_DIR / "scaffold"


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


class SpecContextService:
    def __init__(
        self,
        context_store: ContextStore,
        primary_store: PrimaryContextStore,
        git_client: GitClient,
        workspace_root: Path,
    ) -> None:
        self._store = context_store
        self._primary = primary_store
        self._git = git_client
        self._workspace_root = workspace_root

    def _repos_dir(self) -> Path:
        return self._workspace_root / "repos"

    def _repo_path(self, repo_slug: str) -> Path:
        return self._repos_dir() / repo_slug

    def _specs_dir(self, repo_slug: str) -> Path:
        return self._repo_path(repo_slug) / "specs"

    def _has_primary(self) -> bool:
        return any(c.is_primary for c in self._store.list_all())

    # ------------------------------------------------------------------ create

    def create(self, name: str, repo_slug: str, repo_url: str) -> SpecContextProject:
        if self._store.get(name) is not None:
            raise ContextAlreadyExistsError(
                f"Context '{name}' already exists. Use a different name."
            )
        ctx = SpecContextProject(
            name=name,
            state=ContextState.INATIVO,
            repo_slug=repo_slug,
            repo_url=repo_url,
            is_primary=False,
            created_at=_now(),
            activated_at=None,
        )
        self._store.save(ctx)
        return ctx

    # ------------------------------------------------------------------ list / show

    def list_all(self) -> list[SpecContextProject]:
        return self._store.list_all()

    def show(self, name: str) -> SpecContextProject:
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        return ctx

    # ------------------------------------------------------------------ activate

    def activate(self, name: str) -> SpecContextProject:
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")

        # Clone if repo not on disk
        repo_path = self._repo_path(ctx.repo_slug)
        if not repo_path.exists():
            self._git.clone(ctx.repo_url, repo_path)

        # Checkout target branch if stored in context
        if ctx.current_branch:
            try:
                self._git.checkout(repo_path, ctx.current_branch)
            except Exception as exc:
                print(
                    f"WARNING: could not checkout branch {ctx.current_branch!r}: {exc}",
                    file=sys.stderr,
                )

        # Read actual branch from disk
        try:
            actual_branch: str | None = self._git.current_branch(repo_path)
        except Exception:
            actual_branch = None

        # Scaffold specs/ if absent
        specs_dir = self._specs_dir(ctx.repo_slug)
        if not specs_dir.exists():
            if _SCAFFOLD_SRC.exists():
                shutil.copytree(_SCAFFOLD_SRC, specs_dir)
            else:
                for subdir in ("", "memory", "features", "foundation"):
                    (specs_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Copy repo-AGENTS.md template if not already present
        repo_agents_dst = repo_path / "AGENTS.md"
        repo_agents_src = _PUBLIC_DIR / "templates" / "repo-AGENTS.md"
        if not repo_agents_dst.exists() and repo_agents_src.exists():
            shutil.copy2(repo_agents_src, repo_agents_dst)

        activated = SpecContextProject(
            name=ctx.name,
            state=ContextState.ATIVO,
            repo_slug=ctx.repo_slug,
            repo_url=ctx.repo_url,
            is_primary=ctx.is_primary,
            created_at=ctx.created_at,
            activated_at=_now(),
            current_branch=actual_branch,
        )
        self._store.update(activated)

        # Auto-promote if no primary exists yet
        if not self._has_primary():
            self._promote_to_primary(activated)
            ctx_after = self._store.get(name)
            if ctx_after is not None:
                return ctx_after

        return activated

    # ------------------------------------------------------------------ deactivate

    def deactivate(self, name: str) -> SpecContextProject:
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state != ContextState.ATIVO:
            raise ContextStateError(f"Context '{name}' is not active. It cannot be deactivated.")
        if ctx.is_primary:
            raise ContextStateError(
                f"Context '{name}' is the primary context and cannot be deactivated. "
                "Promote another context first with 'dadaia context promote <name>'."
            )

        repo_path = self._repo_path(ctx.repo_slug)
        branch_before_sync: str | None = None
        if repo_path.exists():
            try:
                branch_before_sync = self._git.current_branch(repo_path)
            except Exception:
                pass
            if self._git.is_git_root(repo_path):
                if self._git.is_dirty(repo_path):
                    try:
                        self._git.commit_all(repo_path, "chore: auto-sync before deactivate")
                    except GitSyncError as exc:
                        raise GitSyncError(
                            f"Git sync failed for context '{name}' at '{repo_path}'. "
                            "Resolve the issue and retry deactivate."
                        ) from exc
                if self._git.has_remote(repo_path):
                    try:
                        self._git.push(repo_path)
                    except GitSyncError as exc:
                        raise GitSyncError(
                            f"Git push failed for context '{name}' at '{repo_path}'. "
                            "Resolve the issue and retry deactivate."
                        ) from exc
            shutil.rmtree(repo_path)

        inactive = SpecContextProject(
            name=ctx.name,
            state=ContextState.INATIVO,
            repo_slug=ctx.repo_slug,
            repo_url=ctx.repo_url,
            is_primary=False,
            created_at=ctx.created_at,
            activated_at=None,
            current_branch=branch_before_sync,
        )
        self._store.update(inactive)
        return inactive

    # ------------------------------------------------------------------ promote

    def promote(self, name: str) -> SpecContextProject:
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state != ContextState.ATIVO:
            raise ContextStateError(
                f"Context '{name}' must be active before it can be promoted. "
                "Run 'dadaia context activate {name}' first."
            )
        if ctx.is_primary:
            return ctx  # already primary — idempotent

        # Demote current primary (if any)
        for existing in self._store.list_all():
            if existing.is_primary:
                demoted = SpecContextProject(
                    name=existing.name,
                    state=existing.state,
                    repo_slug=existing.repo_slug,
                    repo_url=existing.repo_url,
                    is_primary=False,
                    created_at=existing.created_at,
                    activated_at=existing.activated_at,
                    current_branch=existing.current_branch,
                )
                self._store.update(demoted)

        return self._promote_to_primary(ctx)

    def _promote_to_primary(self, ctx: SpecContextProject) -> SpecContextProject:
        promoted = SpecContextProject(
            name=ctx.name,
            state=ctx.state,
            repo_slug=ctx.repo_slug,
            repo_url=ctx.repo_url,
            is_primary=True,
            created_at=ctx.created_at,
            activated_at=ctx.activated_at,
            current_branch=ctx.current_branch,
        )
        self._store.update(promoted)
        self._primary.write(
            name=promoted.name,
            repo_slug=promoted.repo_slug,
            specs_dir=self._specs_dir(promoted.repo_slug),
        )
        return promoted

    # ------------------------------------------------------------------ delete

    def delete(self, name: str) -> None:
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state == ContextState.ATIVO:
            raise ContextStateError(
                f"Context '{name}' is active. Run 'dadaia context deactivate {name}' before deleting."
            )
        self._store.delete(name)
