"""DoctorService — diagnose and repair workspace state invariants (v2 model: ALIVE/DEAD)."""

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.core.protocols.primary_context_store import PrimaryContextStore
from dadaia_workspace.features.spec_context.locking import (  # noqa: PLC2701
    _LOCK_TTL_DEFAULT,
    LockState,
    _append_audit_event,
    _audit_log_path,
    check_lock_state,
    context_lock,
    workspace_lock,
)

# Note: INV-1, INV-2, INV-3, INV-6 have been removed in v2 — they guarded
# is_primary logic that no longer exists.  INV-4 and INV-5 are renamed for
# the ALIVE/DEAD semantics.

# Production-write event types that must carry task_id (LOCK-4).
# Note: T-13 wires task_id into gate events. Until then the set of
# "production-write" events is the forward-declared list; we scan for it
# gracefully and flag any that are missing the field.
_PRODUCTION_WRITE_EVENTS: frozenset[str] = frozenset(
    {
        "PRODUCTION_WRITE",
        "GATE_WRITE",
        "WRITE",
    }
)


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

    def _locks_dir(self) -> Path:
        return self._workspace_root / ".dadaia" / "locks" / "implementation"

    def _sessions_dir(self) -> Path:
        return self._workspace_root / ".dadaia" / "sessions"

    # ------------------------------------------------------------------
    # Helper: read all lock files grouped by <context>__<release> key
    # ------------------------------------------------------------------

    def _grouped_lock_files(self) -> dict[str, list[Path]]:
        """Return a mapping of <context>__<release> key → list of .json files."""
        locks_dir = self._locks_dir()
        grouped: dict[str, list[Path]] = {}
        if not locks_dir.exists():
            return grouped
        for f in sorted(locks_dir.iterdir()):
            if f.suffix != ".json":
                continue
            key = f.stem  # e.g. "myctx__v1"
            grouped.setdefault(key, []).append(f)
        return grouped

    # ------------------------------------------------------------------
    # Helper: parse last_seen_at from a lock file (returns 0 if missing)
    # ------------------------------------------------------------------

    @staticmethod
    def _last_seen_epoch(path: Path) -> float:
        try:
            data = json.loads(path.read_text())
            raw = data.get("last_seen_at", "")
            if not raw:
                return 0.0
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Helper: read lock data dict (None on error)
    # ------------------------------------------------------------------

    @staticmethod
    def _read_lock(path: Path) -> dict[str, object] | None:
        try:
            result: dict[str, object] = json.loads(path.read_text())
            return result
        except Exception:
            return None

    @staticmethod
    def _str(d: dict[str, object], key: str, default: str = "") -> str:
        return str(d.get(key, default) or default)

    @staticmethod
    def _int(d: dict[str, object], key: str, default: int = 0) -> int:
        v = d.get(key, default)
        if isinstance(v, int):
            return v
        try:
            return int(str(v))
        except (TypeError, ValueError):
            return default

    # ------------------------------------------------------------------
    # Helper: parse context name and release from a lock file stem
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_key(key: str) -> tuple[str, str]:
        """Split '<context>__<release>' into (context, release)."""
        parts = key.split("__", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return key, ""

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

        # ---- LOCK invariants (T-12) ----

        # LOCK-1: ≥2 .json files for the same <ctx>__<release> key
        for key, files in self._grouped_lock_files().items():
            if len(files) >= 2:
                issues.append(
                    DoctorIssue(
                        code="LOCK-1",
                        description=(
                            f"Multiple lock files for key '{key}': "
                            + ", ".join(str(f.name) for f in files)
                            + " — keeping freshest; others renamed .conflicted; requires human review"
                        ),
                        fixable=True,  # semi-auto: rename + audit but flag for human review
                    )
                )

        # LOCK-2: impl lock exists for a DEAD context
        dead_names = {ctx.name for ctx in contexts if ctx.state == ContextState.DEAD}
        locks_dir = self._locks_dir()
        if locks_dir.exists():
            for f in sorted(locks_dir.iterdir()):
                if f.suffix != ".json":
                    continue
                ctx_name, _ = self._parse_key(f.stem)
                if ctx_name in dead_names:
                    issues.append(
                        DoctorIssue(
                            code="LOCK-2",
                            description=(
                                f"Implementation lock '{f.name}' exists for DEAD context '{ctx_name}'"
                            ),
                            fixable=True,
                        )
                    )

        # LOCK-3: HELD lock with last_seen_at older than ttl
        if locks_dir.exists():
            for f in sorted(locks_dir.iterdir()):
                if f.suffix != ".json":
                    continue
                data = self._read_lock(f)
                if data is None:
                    continue
                if data.get("state") == "STALE":
                    continue  # already marked stale, skip
                ctx_name, release = self._parse_key(f.stem)
                state = check_lock_state(self._workspace_root, ctx_name, release)
                if state == LockState.STALE and data.get("state") != LockState.STALE:
                    last_seen = data.get("last_seen_at", "unknown")
                    ttl = data.get("ttl_seconds", _LOCK_TTL_DEFAULT)
                    owner_runtime = data.get("runtime", "unknown")
                    owner_session = data.get("session_id", "unknown")
                    issues.append(
                        DoctorIssue(
                            code="LOCK-3",
                            description=(
                                f"HELD lock '{f.name}' is expired (last_seen_at={last_seen}, "
                                f"ttl={ttl}s, runtime={owner_runtime}, session_id={owner_session})"
                            ),
                            fixable=True,
                        )
                    )

        # LOCK-4: production-write event in lock-events.jsonl missing task_id (NO AUTO-FIX)
        audit_path = _audit_log_path(self._workspace_root)
        if audit_path.exists():
            try:
                lines = [
                    ln for ln in audit_path.read_text().splitlines() if ln.strip()
                ]
                for i, line in enumerate(lines, start=1):
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get("event") in _PRODUCTION_WRITE_EVENTS and not record.get("task_id"):
                            issues.append(
                                DoctorIssue(
                                    code="LOCK-4",
                                    description=(
                                        f"Production-write event on line {i} of lock-events.jsonl "
                                        f"is missing 'task_id' field (event={record.get('event')}, "
                                        f"session_id={record.get('session_id', 'unknown')})"
                                    ),
                                    fixable=False,
                                )
                            )
            except OSError:
                pass

        # LOCK-5: BLOCKED_ATTEMPT event in audit log — surface as signal (NO AUTO-FIX)
        if audit_path.exists():
            try:
                lines = [
                    ln for ln in audit_path.read_text().splitlines() if ln.strip()
                ]
                for i, line in enumerate(lines, start=1):
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get("event") == "BLOCKED_ATTEMPT":
                        issues.append(
                            DoctorIssue(
                                code="LOCK-5",
                                description=(
                                    f"BLOCKED_ATTEMPT recorded on line {i} of lock-events.jsonl "
                                    f"(session_id={record.get('session_id', 'unknown')}, "
                                    f"reason={record.get('reason', '')})"
                                ),
                                fixable=False,
                            )
                        )
            except OSError:
                pass

        # LOCK-6: BOUND_REVIEW session file for a DEAD context (AUTO-FIX)
        sessions_dir = self._sessions_dir()
        if sessions_dir.exists():
            for f in sorted(sessions_dir.iterdir()):
                if f.suffix != ".json":
                    continue
                try:
                    data = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                if data.get("mode") != "BOUND_REVIEW":
                    continue
                ctx_name = data.get("context", "")
                if ctx_name in dead_names:
                    issues.append(
                        DoctorIssue(
                            code="LOCK-6",
                            description=(
                                f"BOUND_REVIEW session file '{f.name}' belongs to "
                                f"DEAD context '{ctx_name}'"
                            ),
                            fixable=True,
                        )
                    )

        return issues

    def fix(self) -> list[str]:
        """Fix detected issues.

        INV-5: remove stale repos for DEAD contexts.
        LOCK-1: keep freshest lock file; rename others .conflicted + append audit.
        LOCK-2: delete impl lock for DEAD context + append audit.
        LOCK-3: set state=STALE on expired HELD lock (do NOT delete).
        LOCK-6: delete BOUND_REVIEW session for DEAD context + append audit.

        NO-FIX invariants (LOCK-4, LOCK-5) are only reported in check().

        Lock ordering (ADR D-4 / T-11):
          Lock 1 (workspace_lock) wraps the spec_contexts.json load and all JSON
          mutations so concurrent alive()/dead() JSON writes are serialised.
          Lock 2 (context_lock per slug) is nested INSIDE Lock 1 for the rmtree
          step.  alive()/dead() always RELEASE Lock 2 before requesting Lock 1,
          so the only nesting direction that exists is fix()'s L1→L2 — there is
          no AB-BA cycle and therefore no deadlock.
          Before calling rmtree, fix() re-confirms the context is still DEAD
          (alive() could have won the race and transitioned it to ALIVE while
          fix() was waiting for Lock 1).  If the context is now ALIVE, the
          rmtree is skipped.
        """
        actions: list[str] = []

        with workspace_lock(self._workspace_root):
            all_contexts = self._store.list_all()
            dead_names = {ctx.name for ctx in all_contexts if ctx.state == ContextState.DEAD}

            # INV-5: remove stale repos for DEAD contexts.
            # Acquire Lock 2 per slug so alive()'s filesystem ops (which hold
            # Lock 2 while they run) cannot race with this rmtree.
            for ctx in all_contexts:
                if ctx.state == ContextState.DEAD:
                    repo_path = self._repos_dir() / ctx.repo_slug
                    if repo_path.exists():
                        with context_lock(self._workspace_root, ctx.repo_slug):
                            # Re-confirm still DEAD after acquiring Lock 2.
                            # alive() may have completed its FS work and is now
                            # waiting for Lock 1 (which we hold).  The JSON has
                            # not been updated yet (alive() updates JSON under
                            # Lock 1), so we must check via the store — which
                            # reads from disk and will still show DEAD at this
                            # point.  Safe to rmtree only if still DEAD.
                            ctx_recheck = self._store.get(ctx.name)
                            if ctx_recheck is None or ctx_recheck.state != ContextState.DEAD:
                                # Context transitioned — skip rmtree.
                                continue
                            shutil.rmtree(repo_path)
                        actions.append(
                            f"Removed stale repo '{ctx.repo_slug}' for dead context '{ctx.name}'"
                        )

            # LOCK-1: keep freshest; rename stale duplicates to .conflicted
            for key, files in self._grouped_lock_files().items():
                if len(files) < 2:
                    continue
                # Sort descending by last_seen_at epoch (freshest first)
                sorted_files = sorted(files, key=self._last_seen_epoch, reverse=True)
                freshest = sorted_files[0]
                for stale_file in sorted_files[1:]:
                    conflicted = stale_file.with_suffix(".conflicted")
                    stale_file.rename(conflicted)
                    ctx_name, release = self._parse_key(key)
                    freshest_data: dict[str, object] = self._read_lock(freshest) or {}
                    _append_audit_event(
                        self._workspace_root,
                        event="LOCK_CONFLICT_RENAMED",
                        context=ctx_name,
                        release=release,
                        session_id=self._str(freshest_data, "session_id", "unknown"),
                        runtime=self._str(freshest_data, "runtime", "doctor"),
                        pid=self._int(freshest_data, "pid", 0),
                        reason=f"LOCK-1: duplicate lock file renamed to {conflicted.name}; requires human review",
                    )
                    actions.append(
                        f"LOCK-1: renamed conflicting lock '{stale_file.name}' → '{conflicted.name}' "
                        f"(kept '{freshest.name}'); REQUIRES HUMAN REVIEW"
                    )

            # LOCK-2: delete impl lock for DEAD context
            locks_dir = self._locks_dir()
            if locks_dir.exists():
                for f in sorted(locks_dir.iterdir()):
                    if f.suffix != ".json":
                        continue
                    ctx_name, release = self._parse_key(f.stem)
                    if ctx_name in dead_names:
                        lock_data: dict[str, object] = self._read_lock(f) or {}
                        _append_audit_event(
                            self._workspace_root,
                            event="LOCK_DELETED_DEAD_CTX",
                            context=ctx_name,
                            release=release,
                            session_id=self._str(lock_data, "session_id", "unknown"),
                            runtime=self._str(lock_data, "runtime", "doctor"),
                            pid=self._int(lock_data, "pid", 0),
                            reason=f"LOCK-2: implementation lock deleted for DEAD context '{ctx_name}'",
                        )
                        f.unlink(missing_ok=True)
                        actions.append(
                            f"LOCK-2: deleted implementation lock '{f.name}' for DEAD context '{ctx_name}'"
                        )

            # LOCK-3: mark expired HELD locks as STALE (do NOT delete)
            if locks_dir.exists():
                for f in sorted(locks_dir.iterdir()):
                    if f.suffix != ".json":
                        continue
                    lock3_data = self._read_lock(f)
                    if lock3_data is None:
                        continue
                    if lock3_data.get("state") == LockState.STALE:
                        continue  # already marked
                    ctx_name, release = self._parse_key(f.stem)
                    state = check_lock_state(self._workspace_root, ctx_name, release)
                    if state == LockState.STALE:
                        lock3_data["state"] = LockState.STALE
                        tmp = f.with_suffix(".tmp")
                        tmp.write_text(json.dumps(lock3_data, indent=2))
                        os.replace(tmp, f)
                        actions.append(
                            f"LOCK-3: marked lock '{f.name}' as STALE "
                            f"(last_seen_at={self._str(lock3_data, 'last_seen_at', 'unknown')})"
                        )

            # LOCK-6: delete BOUND_REVIEW session files for DEAD contexts
            sessions_dir = self._sessions_dir()
            if sessions_dir.exists():
                for f in sorted(sessions_dir.iterdir()):
                    if f.suffix != ".json":
                        continue
                    sess_data: dict[str, object] | None = self._read_lock(f)
                    if sess_data is None:
                        continue
                    if sess_data.get("mode") != "BOUND_REVIEW":
                        continue
                    ctx_name = self._str(sess_data, "context")
                    if ctx_name in dead_names:
                        release = self._str(sess_data, "release")
                        _append_audit_event(
                            self._workspace_root,
                            event="REVIEW_SESSION_DELETED_DEAD_CTX",
                            context=ctx_name,
                            release=release,
                            session_id=self._str(sess_data, "session_id", "unknown"),
                            runtime=self._str(sess_data, "runtime", "doctor"),
                            pid=self._int(sess_data, "pid", 0),
                            reason=f"LOCK-6: BOUND_REVIEW session deleted for DEAD context '{ctx_name}'",
                        )
                        f.unlink(missing_ok=True)
                        actions.append(
                            f"LOCK-6: deleted BOUND_REVIEW session '{f.name}' for DEAD context '{ctx_name}'"
                        )

        return actions
