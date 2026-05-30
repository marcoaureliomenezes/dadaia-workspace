"""DoctorService — diagnose and repair workspace state invariants (v2 model: ALIVE/DEAD)."""

import shutil
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.core.protocols.primary_context_store import PrimaryContextStore
from dadaia_workspace.features.spec_context.locking import workspace_lock

# Note: INV-1, INV-2, INV-3, INV-6 have been removed in v2 — they guarded
# is_primary logic that no longer exists.  INV-4 and INV-5 are renamed for
# the ALIVE/DEAD semantics.


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

        # INV-4 (v2): ALIVE context must have repo on disk
        for ctx in contexts:
            if ctx.state == ContextState.ALIVE:
                repo_path = self._repos_dir() / ctx.repo_slug
                if not repo_path.exists():
                    issues.append(
                        DoctorIssue(
                            code="INV-4",
                            description=f"Context '{ctx.name}' is alive but repo '{ctx.repo_slug}' not on disk",
                            fixable=False,
                        )
                    )

        # INV-5 (v2): DEAD context must not have repo on disk
        for ctx in contexts:
            if ctx.state == ContextState.DEAD:
                repo_path = self._repos_dir() / ctx.repo_slug
                if repo_path.exists():
                    issues.append(
                        DoctorIssue(
                            code="INV-5",
                            description=f"Context '{ctx.name}' is dead but repo '{ctx.repo_slug}' is on disk",
                            fixable=True,
                        )
                    )

        return issues

    def fix(self) -> list[str]:
        """Fix detected issues.

        INV-5: remove stale repos for DEAD contexts.

        Lock 1 wraps the spec_contexts.json load (to confirm state) and the
        rmtree + update sequence so concurrent alive() calls cannot race with fix().
        Per SPEC T-11: the JSON write is inside Lock 1; rmtree is also inside Lock 1
        for the doctor fix path (doctor fixes are infrequent; we accept the slightly
        wider lock window for correctness).
        """
        actions: list[str] = []

        with workspace_lock(self._workspace_root):
            for ctx in self._store.list_all():
                if ctx.state == ContextState.DEAD:
                    repo_path = self._repos_dir() / ctx.repo_slug
                    if repo_path.exists():
                        shutil.rmtree(repo_path)
                        actions.append(
                            f"Removed stale repo '{ctx.repo_slug}' for dead context '{ctx.name}'"
                        )

        return actions
