"""SpecContextService — full Spec Context Project lifecycle."""

import shutil
from pathlib import Path

from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    GitOperationError,
)
from dadaia_workspace.core.models.spec_context import (
    ContextRepositoryRef,
    ContextState,
    RepoRole,
    SpecContextProject,
    detect_source_kind,
    derive_repo_slug,
)
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.core.protocols.repositories import SpecContextRepository


class SpecContextService:
    def __init__(
        self,
        repo: SpecContextRepository,
        git: GitClient,
        workspace_root: Path,
    ) -> None:
        self._repo = repo
        self._git = git
        self._workspace_root = workspace_root

    def _contexts_dir(self) -> Path:
        return self._workspace_root / ".dadaia" / "contexts"

    def _make_repo_ref(self, repo_ref: str, role: RepoRole) -> ContextRepositoryRef:
        source_kind = detect_source_kind(repo_ref)
        slug = derive_repo_slug(repo_ref)
        return ContextRepositoryRef(
            repo_ref=repo_ref,
            role=role,
            source_kind=source_kind,
            repo_slug=slug,
        )

    # ------------------------------------------------------------------ create

    def create(
        self,
        name: str,
        primary_ref: str,
        secondary_refs: list[str] | None = None,
    ) -> SpecContextProject:
        if self._repo.get_by_name(name) is not None:
            raise ContextAlreadyExistsError(
                f"Context '{name}' already exists. Use a different name."
            )
        primary = self._make_repo_ref(primary_ref, RepoRole.PRIMARY)
        secondaries = tuple(
            self._make_repo_ref(ref, RepoRole.SECONDARY)
            for ref in (secondary_refs or [])
        )
        ctx = SpecContextProject(
            name=name,
            state=ContextState.INATIVO,
            primary_repo=primary,
            secondary_repos=secondaries,
        )
        self._repo.save(ctx)
        return ctx

    # ------------------------------------------------------------------ list / show

    def list_all(self) -> list[SpecContextProject]:
        return self._repo.list_all()

    def show(self, name: str | None = None) -> SpecContextProject | None:
        if name is not None:
            return self._repo.get_by_name(name)
        return self._repo.get_active()

    # ------------------------------------------------------------------ activate

    def activate(self, name: str) -> SpecContextProject:
        ctx = self._repo.get_by_name(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")

        context_dir = self._contexts_dir() / name
        all_repos = [ctx.primary_repo, *ctx.secondary_repos]

        if ctx.state == ContextState.INATIVO:
            # Materialize: clone all repos
            context_dir.mkdir(parents=True, exist_ok=True)
            repos_dir = context_dir / "repos"
            materialized_repos: list[ContextRepositoryRef] = []
            for repo in all_repos:
                target = repos_dir / repo.repo_slug
                self._git.clone(repo.repo_ref, target)
                specs_dir_candidate = target / "specs"
                has_specs = specs_dir_candidate.exists()
                materialized_repos.append(ContextRepositoryRef(
                    repo_ref=repo.repo_ref,
                    role=repo.role,
                    source_kind=repo.source_kind,
                    repo_slug=repo.repo_slug,
                    materialized_path=target,
                    has_specs_dir=has_specs,
                ))
        else:
            # STANDBY: repos already have materialized_path persisted in db
            materialized_repos = list(all_repos)
            # Reconcile context_dir from persisted value if available
            context_dir = ctx.context_dir if ctx.context_dir else context_dir

        primary_mat = next(r for r in materialized_repos if r.role == RepoRole.PRIMARY)
        specs_dir = (
            primary_mat.materialized_path / "specs"
            if primary_mat.materialized_path and primary_mat.has_specs_dir
            else None
        )

        # Warn if specs directory is missing or incomplete
        if specs_dir and specs_dir.exists():
            if not (specs_dir / "constitution.md").exists():
                import warnings
                warnings.warn(
                    f"Context '{name}': specs/ directory is missing constitution.md",
                    stacklevel=2,
                )
        elif specs_dir:
            import warnings
            warnings.warn(
                f"Context '{name}': primary repo has no specs/ directory",
                stacklevel=2,
            )

        # Move current ATIVO → STANDBY atomically
        current_active = self._repo.get_active()
        if current_active is not None and current_active.name != name:
            standby = SpecContextProject(
                name=current_active.name,
                state=ContextState.STANDBY,
                primary_repo=current_active.primary_repo,
                secondary_repos=current_active.secondary_repos,
                context_dir=current_active.context_dir,
                specs_dir=current_active.specs_dir,
            )
            self._repo.update(standby)

        new_ctx = SpecContextProject(
            name=name,
            state=ContextState.ATIVO,
            primary_repo=materialized_repos[0],
            secondary_repos=tuple(materialized_repos[1:]),
            context_dir=context_dir,
            specs_dir=specs_dir,
        )
        self._repo.update(new_ctx)
        return new_ctx

    # ------------------------------------------------------------------ deactivate

    def deactivate(self) -> SpecContextProject:
        ctx = self._repo.get_active()
        if ctx is None:
            raise ContextStateError(
                "No context is currently active. Use 'dadaia context list' to see available contexts."
            )
        standby = SpecContextProject(
            name=ctx.name,
            state=ContextState.STANDBY,
            primary_repo=ctx.primary_repo,
            secondary_repos=ctx.secondary_repos,
            context_dir=ctx.context_dir,
            specs_dir=ctx.specs_dir,
        )
        self._repo.update(standby)
        return standby

    # ------------------------------------------------------------------ delete

    def delete(self, name: str) -> None:
        ctx = self._repo.get_by_name(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state == ContextState.ATIVO:
            raise ContextStateError(
                f"Context '{name}' is active. Run 'dadaia context deactivate' before deleting."
            )
        if ctx.state == ContextState.STANDBY:
            self._sync_and_remove(ctx)
        else:
            # INATIVO: just remove metadata
            self._repo.delete(name)

    def _sync_and_remove(self, ctx: SpecContextProject) -> None:
        all_repos = [ctx.primary_repo, *ctx.secondary_repos]
        errors: list[str] = []
        for repo in all_repos:
            if repo.materialized_path is None or not repo.materialized_path.exists():
                continue
            try:
                if self._git.has_changes(repo.materialized_path):
                    self._git.commit_all(repo.materialized_path, f"chore: sync before delete context '{ctx.name}'")
                if self._git.has_remote(repo.materialized_path):
                    self._git.push(repo.materialized_path)
            except GitOperationError as e:
                errors.append(str(e))

        if errors:
            raise GitOperationError(
                f"Context '{ctx.name}' sync failed — local files preserved.\n"
                + "\n".join(errors)
            )

        # Only remove after all syncs succeeded
        if ctx.context_dir and ctx.context_dir.exists():
            shutil.rmtree(ctx.context_dir)
        self._repo.delete(ctx.name)

    # ------------------------------------------------------------------ add/remove repo

    def add_repo(self, name: str, repo_ref: str) -> SpecContextProject:
        ctx = self._repo.get_by_name(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        all_refs = {ctx.primary_repo.repo_ref} | {r.repo_ref for r in ctx.secondary_repos}
        if repo_ref in all_refs:
            raise ContextAlreadyExistsError(
                f"Repo '{repo_ref}' is already associated with context '{name}'."
            )
        new_secondary = self._make_repo_ref(repo_ref, RepoRole.SECONDARY)
        updated = SpecContextProject(
            name=ctx.name,
            state=ctx.state,
            primary_repo=ctx.primary_repo,
            secondary_repos=(*ctx.secondary_repos, new_secondary),
            context_dir=ctx.context_dir,
            specs_dir=ctx.specs_dir,
        )
        self._repo.update(updated)
        return updated

    def remove_repo(self, name: str, repo_ref: str) -> SpecContextProject:
        ctx = self._repo.get_by_name(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.primary_repo.repo_ref == repo_ref:
            raise ContextStateError(
                f"Cannot remove the primary repo from context '{name}'."
            )
        new_secondaries = tuple(r for r in ctx.secondary_repos if r.repo_ref != repo_ref)
        updated = SpecContextProject(
            name=ctx.name,
            state=ctx.state,
            primary_repo=ctx.primary_repo,
            secondary_repos=new_secondaries,
            context_dir=ctx.context_dir,
            specs_dir=ctx.specs_dir,
        )
        self._repo.update(updated)
        return updated
