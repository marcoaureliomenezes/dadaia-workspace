"""DoctorService — diagnose and repair workspace state invariants."""

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.core.protocols.primary_context_store import PrimaryContextStore


@dataclass(frozen=True)
class DoctorIssue:
    code: str
    description: str
    fixable: bool


class DoctorService:
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

    def check(self) -> list[DoctorIssue]:
        issues: list[DoctorIssue] = []
        contexts = self._store.list_all()

        # INV-1: at most one is_primary=True
        primaries = [c for c in contexts if c.is_primary]
        if len(primaries) > 1:
            issues.append(
                DoctorIssue(
                    code="INV-1",
                    description=f"Multiple primary contexts: {[p.name for p in primaries]}",
                    fixable=True,
                )
            )

        # INV-2: is_primary only allowed on ativo context
        for ctx in contexts:
            if ctx.is_primary and ctx.state != ContextState.ATIVO:
                issues.append(
                    DoctorIssue(
                        code="INV-2",
                        description=f"Context '{ctx.name}' is primary but not ativo",
                        fixable=True,
                    )
                )

        # INV-3: primary_context.json must match the is_primary context
        stored_primary = self._primary.read()
        if stored_primary is not None:
            if len(primaries) == 1 and stored_primary.get("name") != primaries[0].name:
                issues.append(
                    DoctorIssue(
                        code="INV-3",
                        description=(
                            f"primary_context.json points to '{stored_primary.get('name')}' "
                            f"but is_primary context is '{primaries[0].name}'"
                        ),
                        fixable=True,
                    )
                )
        elif len(primaries) == 1:
            issues.append(
                DoctorIssue(
                    code="INV-3",
                    description="primary_context.json is missing but a primary context exists",
                    fixable=True,
                )
            )

        # INV-4: ativo context must have repo on disk
        for ctx in contexts:
            if ctx.state == ContextState.ATIVO:
                repo_path = self._repos_dir() / ctx.repo_slug
                if not repo_path.exists():
                    issues.append(
                        DoctorIssue(
                            code="INV-4",
                            description=f"Context '{ctx.name}' is ativo but repo '{ctx.repo_slug}' not on disk",
                            fixable=False,
                        )
                    )

        # INV-5: inativo context must not have repo on disk
        for ctx in contexts:
            if ctx.state == ContextState.INATIVO:
                repo_path = self._repos_dir() / ctx.repo_slug
                if repo_path.exists():
                    issues.append(
                        DoctorIssue(
                            code="INV-5",
                            description=f"Context '{ctx.name}' is inativo but repo '{ctx.repo_slug}' is on disk",
                            fixable=True,
                        )
                    )

        # INV-6: primary_context.json present but no is_primary context
        if stored_primary is not None and len(primaries) == 0:
            issues.append(
                DoctorIssue(
                    code="INV-6",
                    description="primary_context.json exists but no context has is_primary=True",
                    fixable=True,
                )
            )

        return issues

    def fix(self) -> list[str]:
        actions: list[str] = []
        contexts = self._store.list_all()

        # Fix INV-1: keep first primary, demote rest
        primaries = [c for c in contexts if c.is_primary]
        if len(primaries) > 1:
            for ctx in primaries[1:]:
                demoted = SpecContextProject(
                    name=ctx.name,
                    state=ctx.state,
                    repo_slug=ctx.repo_slug,
                    repo_url=ctx.repo_url,
                    is_primary=False,
                    created_at=ctx.created_at,
                    activated_at=ctx.activated_at,
                )
                self._store.update(demoted)
                actions.append(f"Demoted '{ctx.name}' (kept '{primaries[0].name}' as primary)")

        # Fix INV-2: clear is_primary on inativo contexts
        for ctx in self._store.list_all():
            if ctx.is_primary and ctx.state != ContextState.ATIVO:
                cleared = SpecContextProject(
                    name=ctx.name,
                    state=ctx.state,
                    repo_slug=ctx.repo_slug,
                    repo_url=ctx.repo_url,
                    is_primary=False,
                    created_at=ctx.created_at,
                    activated_at=ctx.activated_at,
                )
                self._store.update(cleared)
                actions.append(f"Cleared is_primary on inativo context '{ctx.name}'")

        # Fix INV-3 / INV-6: reconcile primary_context.json
        contexts = self._store.list_all()
        primaries = [c for c in contexts if c.is_primary]
        stored_primary = self._primary.read()
        if len(primaries) == 1:
            p = primaries[0]
            specs_dir = self._repos_dir() / p.repo_slug / "specs"
            self._primary.write(p.name, p.repo_slug, specs_dir)
            actions.append(f"Wrote primary_context.json → '{p.name}'")
        elif stored_primary is not None:
            self._primary.clear()
            actions.append("Cleared stale primary_context.json (no primary context)")

        # Fix INV-5: remove stale repos for inativo contexts
        for ctx in self._store.list_all():
            if ctx.state == ContextState.INATIVO:
                repo_path = self._repos_dir() / ctx.repo_slug
                if repo_path.exists():
                    import shutil

                    shutil.rmtree(repo_path)
                    actions.append(
                        f"Removed stale repo '{ctx.repo_slug}' for inativo context '{ctx.name}'"
                    )

        return actions
