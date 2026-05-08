"""SQLite implementations of WorkspaceRepository and SpecContextRepository."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dadaia_workspace.core.models.spec_context import (
    ContextRepositoryRef,
    ContextState,
    RepoRole,
    RepoSourceKind,
    SpecContextProject,
)
from dadaia_workspace.core.models.workspace import Workspace
from dadaia_workspace.infrastructure.database import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteWorkspaceRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def save(self, workspace: Workspace) -> None:
        now = _now()
        conn = self._conn()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO workspaces(root_path, created_at, updated_at) VALUES(?,?,?)",
                (str(workspace.root), now, now),
            )
        conn.close()

    def load(self, root: Path) -> Workspace | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT root_path FROM workspaces WHERE root_path = ?", (str(root),)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return Workspace.from_root(Path(row["root_path"]))


class SQLiteSpecContextRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def _build_ctx(self, row: sqlite3.Row, repo_rows: list[sqlite3.Row]) -> SpecContextProject:
        repos = [
            ContextRepositoryRef(
                repo_ref=r["repo_ref"],
                role=RepoRole(r["role"]),
                source_kind=RepoSourceKind(r["source_kind"]),
                repo_slug=r["repo_slug"],
                materialized_path=Path(r["materialized_path"]) if r["materialized_path"] else None,
                has_specs_dir=bool(r["has_specs_dir"]),
            )
            for r in repo_rows
        ]
        primary = next(r for r in repos if r.role == RepoRole.PRIMARY)
        secondaries = tuple(r for r in repos if r.role == RepoRole.SECONDARY)
        return SpecContextProject(
            name=row["name"],
            state=ContextState(row["state"]),
            primary_repo=primary,
            secondary_repos=secondaries,
            context_dir=Path(row["context_dir"]) if row["context_dir"] else None,
            specs_dir=Path(row["specs_dir"]) if row["specs_dir"] else None,
        )

    def _load_repos(self, conn: sqlite3.Connection, context_id: int) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT * FROM spec_context_repositories WHERE context_id = ? ORDER BY role, id",
            (context_id,),
        ).fetchall()

    def save(self, ctx: SpecContextProject) -> None:
        now = _now()
        conn = self._conn()
        with conn:
            cur = conn.execute(
                """INSERT INTO spec_context_projects
                   (name, state, context_dir, specs_dir, created_at, updated_at)
                   VALUES(?,?,?,?,?,?)""",
                (
                    ctx.name,
                    ctx.state.value,
                    str(ctx.context_dir) if ctx.context_dir else None,
                    str(ctx.specs_dir) if ctx.specs_dir else None,
                    now,
                    now,
                ),
            )
            ctx_id = cur.lastrowid
            self._save_repos(conn, ctx_id, ctx, now)
        conn.close()

    def _save_repos(
        self,
        conn: sqlite3.Connection,
        ctx_id: int | None,
        ctx: SpecContextProject,
        now: str,
    ) -> None:
        all_repos = [ctx.primary_repo, *ctx.secondary_repos]
        for repo in all_repos:
            conn.execute(
                """INSERT OR REPLACE INTO spec_context_repositories
                   (context_id, role, repo_ref, source_kind, repo_slug,
                    materialized_path, has_specs_dir, created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    ctx_id,
                    repo.role.value,
                    repo.repo_ref,
                    repo.source_kind.value,
                    repo.repo_slug,
                    str(repo.materialized_path) if repo.materialized_path else None,
                    int(repo.has_specs_dir),
                    now,
                    now,
                ),
            )

    def update(self, ctx: SpecContextProject) -> None:
        now = _now()
        conn = self._conn()
        with conn:
            conn.execute(
                """UPDATE spec_context_projects
                   SET state=?, context_dir=?, specs_dir=?, updated_at=?, activated_at=?
                   WHERE name=?""",
                (
                    ctx.state.value,
                    str(ctx.context_dir) if ctx.context_dir else None,
                    str(ctx.specs_dir) if ctx.specs_dir else None,
                    now,
                    now if ctx.state == ContextState.ATIVO else None,
                    ctx.name,
                ),
            )
            row = conn.execute(
                "SELECT id FROM spec_context_projects WHERE name=?", (ctx.name,)
            ).fetchone()
            if row:
                conn.execute(
                    "DELETE FROM spec_context_repositories WHERE context_id=?", (row["id"],)
                )
                self._save_repos(conn, row["id"], ctx, now)
        conn.close()

    def get_by_name(self, name: str) -> SpecContextProject | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM spec_context_projects WHERE name=?", (name,)
        ).fetchone()
        if row is None:
            conn.close()
            return None
        repos = self._load_repos(conn, row["id"])
        conn.close()
        return self._build_ctx(row, repos)

    def get_active(self) -> SpecContextProject | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM spec_context_projects WHERE state='ativo'"
        ).fetchone()
        if row is None:
            conn.close()
            return None
        repos = self._load_repos(conn, row["id"])
        conn.close()
        return self._build_ctx(row, repos)

    def list_all(self) -> list[SpecContextProject]:
        conn = self._conn()
        rows = conn.execute("SELECT * FROM spec_context_projects ORDER BY name").fetchall()
        result = []
        for row in rows:
            repos = self._load_repos(conn, row["id"])
            result.append(self._build_ctx(row, repos))
        conn.close()
        return result

    def delete(self, name: str) -> None:
        conn = self._conn()
        with conn:
            conn.execute("DELETE FROM spec_context_projects WHERE name=?", (name,))
        conn.close()
