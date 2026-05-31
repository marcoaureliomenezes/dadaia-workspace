"""SpecContextService — full Spec Context Project lifecycle."""

import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextLockedError,
    ContextNotFoundError,
    ContextStateError,
    GitSyncError,
)
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.core.protocols.primary_context_store import PrimaryContextStore
from dadaia_workspace.features.spec_context.locking import (
    context_lock,
    has_implementation_lock,
    workspace_lock,
)

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

    def _has_implementation_lock(self, name: str) -> bool:
        """Return True if any HELD implementation lock exists for the named context.

        T-11: delegates to locking.has_implementation_lock() which checks state machine.
        """
        return has_implementation_lock(self._workspace_root, name)

    # ------------------------------------------------------------------ create

    def create(self, name: str, repo_slug: str, repo_url: str) -> SpecContextProject:
        with workspace_lock(self._workspace_root):
            if self._store.get(name) is not None:
                raise ContextAlreadyExistsError(
                    f"Context '{name}' already exists. Use a different name."
                )
            ctx = SpecContextProject(
                name=name,
                state=ContextState.DEAD,
                repo_slug=repo_slug,
                repo_url=repo_url,
                created_at=_now(),
                alive_since=None,
                dead_since=None,
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

    # ------------------------------------------------------------------ alive (T-10b / T-11)

    def alive(self, name: str) -> SpecContextProject:
        """Transition a context from DEAD to ALIVE; clone repo if absent.

        Idempotent: calling alive() on an already-ALIVE context is a no-op (no error).
        Sets alive_since=now, clears dead_since=None.

        Lock 2 (context_lock) wraps ALL per-repo filesystem operations: git clone,
        branch checkout, branch read, scaffold copytree/mkdir, and AGENTS.md copy.
        Lock 2 is released BEFORE Lock 1 is acquired — never held simultaneously
        (no AB-BA deadlock possible with doctor.fix() which nests L2 inside L1).

        Lock 1 (workspace_lock) wraps only the JSON load→mutate→dump.
        """
        # Pre-flight read (no lock) to get repo_slug for Lock 2 acquisition
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")

        # Idempotent: already ALIVE — no-op (no lock needed)
        if ctx.state == ContextState.ALIVE:
            return ctx

        repo_slug = ctx.repo_slug
        repo_path = self._repo_path(repo_slug)

        # Lock 2: serialize ALL per-repo filesystem ops for this slug.
        # Released before Lock 1 is requested — no simultaneous L1+L2 hold here.
        actual_branch: str | None = None
        with context_lock(self._workspace_root, repo_slug):
            # Re-read ctx inside Lock 2 so we use the freshest repo_url / current_branch.
            ctx_l2 = self._store.get(name)
            if ctx_l2 is None:
                raise ContextNotFoundError(f"Context '{name}' not found.")

            # Clone if repo absent
            if not repo_path.exists():
                self._git.clone(ctx_l2.repo_url, repo_path)

            # Checkout target branch if stored in context
            if ctx_l2.current_branch:
                try:
                    self._git.checkout(repo_path, ctx_l2.current_branch)
                except Exception as exc:
                    print(
                        f"WARNING: could not checkout branch {ctx_l2.current_branch!r}: {exc}",
                        file=sys.stderr,
                    )

            # Read actual branch from disk
            try:
                actual_branch = self._git.current_branch(repo_path)
            except Exception:
                actual_branch = None

            # Scaffold specs/ if absent
            specs_dir = self._specs_dir(repo_slug)
            if not specs_dir.exists():
                if _SCAFFOLD_SRC.exists():
                    shutil.copytree(_SCAFFOLD_SRC, specs_dir)
                else:
                    for subdir in ("", "memory", "features"):
                        (specs_dir / subdir).mkdir(parents=True, exist_ok=True)

            # Copy repo-AGENTS.md template if not already present
            repo_agents_dst = repo_path / "AGENTS.md"
            repo_agents_src = _PUBLIC_DIR / "templates" / "repo-AGENTS.md"
            if not repo_agents_dst.exists() and repo_agents_src.exists():
                shutil.copy2(repo_agents_src, repo_agents_dst)
        # Lock 2 released here — before acquiring Lock 1.

        # Lock 1: load → mutate → dump
        with workspace_lock(self._workspace_root):
            # Re-read inside lock in case another thread updated the state
            ctx_fresh = self._store.get(name)
            if ctx_fresh is None:
                raise ContextNotFoundError(f"Context '{name}' not found.")
            if ctx_fresh.state == ContextState.ALIVE:
                return ctx_fresh  # another thread already transitioned

            alive_ctx = SpecContextProject(
                name=ctx_fresh.name,
                state=ContextState.ALIVE,
                repo_slug=ctx_fresh.repo_slug,
                repo_url=ctx_fresh.repo_url,
                created_at=ctx_fresh.created_at,
                alive_since=_now(),
                dead_since=None,
                current_branch=actual_branch,
            )
            self._store.update(alive_ctx)

        return alive_ctx

    # ------------------------------------------------------------------ dead (T-10b / T-11)

    def dead(self, name: str) -> SpecContextProject:
        """Transition a context from ALIVE to DEAD; sets dead_since, removes repo.

        Raises ContextLockedError if an implementation lock exists for this context.

        Lock 1 wraps the JSON write (spec_contexts.json update).
        Lock 2 wraps git push and shutil.rmtree (OUTSIDE Lock 1).
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state != ContextState.ALIVE:
            raise ContextStateError(f"Context '{name}' is not ALIVE. It cannot be made DEAD.")

        # Block if an implementation lock is held for this context (T-10b AC-T10b-4 / T-11 AC-T11-9)
        if self._has_implementation_lock(name):
            raise ContextLockedError(
                f"Context '{name}' has an active implementation lock. "
                "Release the implementation session before calling dead()."
            )

        repo_path = self._repo_path(ctx.repo_slug)
        branch_before_sync: str | None = None

        # Git sync + rmtree under Lock 2 (OUTSIDE Lock 1)
        if repo_path.exists():
            import contextlib
            import os

            with context_lock(self._workspace_root, ctx.repo_slug):
                with contextlib.suppress(Exception):
                    branch_before_sync = self._git.current_branch(repo_path)
                if self._git.is_git_root(repo_path):
                    if self._git.is_dirty(repo_path):
                        try:
                            self._git.commit_all(repo_path, "chore: auto-sync before dead")
                        except GitSyncError as exc:
                            raise GitSyncError(
                                f"Git sync failed for context '{name}' at '{repo_path}'. "
                                "Resolve the issue and retry dead()."
                            ) from exc
                    if self._git.has_remote(repo_path):
                        try:
                            self._git.push(repo_path)
                        except GitSyncError as exc:
                            raise GitSyncError(
                                f"Git push failed for context '{name}' at '{repo_path}'. "
                                "Resolve the issue and retry dead()."
                            ) from exc
                # Detect non-writable files before calling rmtree
                non_writable = [
                    str(f)
                    for f in repo_path.rglob("*")
                    if f.is_file() and not os.access(f, os.W_OK)
                ]
                if non_writable:
                    sample = non_writable[:3]
                    raise GitSyncError(
                        f"Cannot remove '{repo_path}': {len(non_writable)} non-writable "
                        f"file(s) found (e.g. {sample}). "
                        f"Run: sudo chown -R $USER '{repo_path}'"
                    )
                shutil.rmtree(repo_path)

        # Lock 1: load → mutate → dump (JSON write only)
        with workspace_lock(self._workspace_root):
            dead_ctx = SpecContextProject(
                name=ctx.name,
                state=ContextState.DEAD,
                repo_slug=ctx.repo_slug,
                repo_url=ctx.repo_url,
                created_at=ctx.created_at,
                alive_since=None,
                dead_since=_now(),
                current_branch=branch_before_sync,
            )
            self._store.update(dead_ctx)

        return dead_ctx

    # ------------------------------------------------------------------ delete

    def delete(self, name: str) -> None:
        with workspace_lock(self._workspace_root):
            ctx = self._store.get(name)
            if ctx is None:
                raise ContextNotFoundError(f"Context '{name}' not found.")
            if ctx.state == ContextState.ALIVE:
                raise ContextStateError(
                    f"Context '{name}' is active. Run 'dadaia context dead {name}' before deleting."
                )
            self._store.delete(name)
