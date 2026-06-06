"""DoctorService — diagnose and repair workspace state invariants (v2 model: ALIVE/DEAD)."""

import fnmatch
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.features.spec_context.locking import (  # noqa: PLC2701
    _LOCK_TTL_DEFAULT,
    LockState,
    _append_audit_event,
    _audit_log_path,
    check_lock_state,
    context_lock,
    workspace_lock,
)
from dadaia_workspace.features.spec_context.semaphore import (
    _is_stale,
    read_semaphore,
)

# Note: INV-1, INV-2, INV-3, INV-6 have been removed in v2. INV-4 and INV-5
# are renamed for the ALIVE/DEAD semantics.

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

# ---------------------------------------------------------------------------
# ROOT-* invariant constants
# ---------------------------------------------------------------------------

#: Directories allowed at workspace root (exact names, no wildcards).
_ROOT_ALLOWED_DIRS: frozenset[str] = frozenset(
    {".agents", ".claude", ".codex", ".dadaia", ".opencode", "repos"}
)

#: Files allowed at workspace root (exact names, no wildcards).
_ROOT_ALLOWED_FILES: frozenset[str] = frozenset({"AGENTS.md"})

#: Caches and tool outputs that are forbidden at workspace root (ROOT-2).
#: These are safe to delete — they regenerate.
_ROOT_FORBIDDEN_CACHES: frozenset[str] = frozenset(
    {
        ".ruff_cache",
        ".pytest_cache",
        ".mypy_cache",
        ".hypothesis",
        ".coverage",
        ".playwright-mcp",
        "test-results",
    }
)

#: Tool config files that have canonical homes elsewhere but are currently
#: tolerated at root with a WARN (ROOT-3, lenient).
_ROOT_TOOL_CONFIGS: frozenset[str] = frozenset({".mcp.json", "opencode.json", "CLAUDE.md"})

#: Canonical top-level subdirectories allowed inside `.dadaia/` (ROOT-4).
_DADAIA_ALLOWED_SUBDIRS: frozenset[str] = frozenset(
    {
        "agentic",
        "mcps",
        "scripts",
        "tmp",
        "reports",
        "dev-report",
        "states",
        "logs",
        "locks",
        "sessions",
        "handoff",
        ".cache",
        ".venv",
        # Additional dirs observed in practice
        "academy",
        "bugs",
        "dist",
        "figma-bridge",
        "imgs",
        "references",
        "runs",
        "src",
    }
)


def _semaphore_audit_log_path(workspace_root: Path) -> Path:
    """Path to the semaphore-specific audit log (separate from lock-events.jsonl)."""
    return workspace_root / ".dadaia" / "states" / "audit" / "semaphore-reclaims.jsonl"


def _append_semaphore_audit(
    workspace_root: Path,
    *,
    event: str,
    context: str,
    session_id: str,
    reason: str,
) -> None:
    """Append one audit record to semaphore-reclaims.jsonl atomically via O_APPEND."""
    audit_path = _semaphore_audit_log_path(workspace_root)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {
        "ts": datetime.now(tz=UTC).isoformat(),
        "event": event,
        "context": context,
        "session_id": session_id,
        "reason": reason,
    }
    line = json.dumps(record) + "\n"
    encoded = line.encode("utf-8")
    fd = os.open(str(audit_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, encoded)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class DoctorIssue:
    code: str
    description: str
    fixable: bool


class DoctorService:
    def __init__(
        self,
        context_store: ContextStore,
        git_client: GitClient,
        workspace_root: Path,
    ) -> None:
        self._store = context_store
        self._git = git_client
        self._workspace_root = workspace_root

    def _repos_dir(self) -> Path:
        return self._workspace_root / "repos"

    def _locks_dir(self) -> Path:
        return self._workspace_root / ".dadaia" / "locks" / "implementation"

    def _sessions_dir(self) -> Path:
        return self._workspace_root / ".dadaia" / "sessions"

    def _ctx_locks_dir(self) -> Path:
        return self._workspace_root / ".dadaia" / "states" / "ctx_locks"

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

    # ------------------------------------------------------------------
    # Helper: load operator exception allowlist from .dadaia/states/root_exceptions.txt
    # Returns a list of fnmatch glob patterns (one per non-empty line).
    # File is optional — returns empty list when absent.
    # ------------------------------------------------------------------

    def _root_exception_globs(self) -> list[str]:
        exc_path = self._workspace_root / ".dadaia" / "states" / "root_exceptions.txt"
        if not exc_path.exists():
            return []
        lines = exc_path.read_text(encoding="utf-8").splitlines()
        return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]

    @staticmethod
    def _matches_any_glob(name: str, globs: list[str]) -> bool:
        return any(fnmatch.fnmatch(name, g) for g in globs)

    # ------------------------------------------------------------------
    # ROOT-* check helpers
    # ------------------------------------------------------------------

    def _check_root_1(self, exc_globs: list[str]) -> list[DoctorIssue]:
        """ROOT-1 — workspace root contains only whitelisted entries."""
        issues: list[DoctorIssue] = []
        offenders: list[str] = []
        try:
            entries = list(self._workspace_root.iterdir())
        except OSError:
            return issues
        for entry in sorted(entries):
            name = entry.name
            # Skip git internals
            if name == ".git":
                continue
            if entry.is_dir():
                if name in _ROOT_ALLOWED_DIRS:
                    continue
            else:
                if name in _ROOT_ALLOWED_FILES:
                    continue
                # gitignore is operator-owned; always allow it
                if name == ".gitignore":
                    continue
            # Check operator exception allowlist
            if self._matches_any_glob(name, exc_globs):
                continue
            offenders.append(name)
        if offenders:
            listed = ", ".join(repr(o) for o in offenders)
            issues.append(
                DoctorIssue(
                    code="ROOT-1",
                    description=(
                        f"Workspace root contains non-whitelisted entries: {listed}. "
                        "Relocate under .dadaia/<subdir> or add to "
                        ".dadaia/states/root_exceptions.txt"
                    ),
                    fixable=False,
                )
            )
        return issues

    def _check_root_2(self) -> list[DoctorIssue]:
        """ROOT-2 — no forbidden caches/outputs at workspace root."""
        issues: list[DoctorIssue] = []
        found: list[str] = []
        for name in _ROOT_FORBIDDEN_CACHES:
            if (self._workspace_root / name).exists():
                found.append(name)
        if found:
            listed = ", ".join(repr(n) for n in sorted(found))
            issues.append(
                DoctorIssue(
                    code="ROOT-2",
                    description=(
                        f"Forbidden cache/output dirs at workspace root: {listed}. "
                        "Run 'dadaia doctor --fix' to delete them (they regenerate under .dadaia/)."
                    ),
                    fixable=True,
                )
            )
        return issues

    def _check_root_3(self, exc_globs: list[str]) -> list[DoctorIssue]:
        """ROOT-3 — tool configs in canonical homes or documented exception list (WARN)."""
        issues: list[DoctorIssue] = []
        found: list[str] = []
        for name in _ROOT_TOOL_CONFIGS:
            entry = self._workspace_root / name
            if entry.exists() and not self._matches_any_glob(name, exc_globs):
                found.append(name)
        if found:
            listed = ", ".join(repr(n) for n in sorted(found))
            issues.append(
                DoctorIssue(
                    code="ROOT-3",
                    description=(
                        f"Tool config file(s) at workspace root not in exception list: {listed}. "
                        "Add to .dadaia/states/root_exceptions.txt or relocate under .dadaia/. "
                        "(T-SANI-02 will resolve canonical placement.)"
                    ),
                    fixable=False,
                )
            )
        return issues

    def _check_root_4(self) -> list[DoctorIssue]:
        """ROOT-4 — .dadaia/ contains only canonical top-level subdirs."""
        issues: list[DoctorIssue] = []
        dadaia_dir = self._workspace_root / ".dadaia"
        if not dadaia_dir.exists():
            return issues
        unknown: list[str] = []
        try:
            entries = list(dadaia_dir.iterdir())
        except OSError:
            return issues
        for entry in sorted(entries):
            name = entry.name
            # Allow dotfiles at the .dadaia level (e.g. .gitkeep, .DS_Store)
            if name.startswith(".") and not entry.is_dir():
                continue
            if entry.is_dir() and name not in _DADAIA_ALLOWED_SUBDIRS:
                unknown.append(name)
        if unknown:
            listed = ", ".join(repr(u) for u in sorted(unknown))
            issues.append(
                DoctorIssue(
                    code="ROOT-4",
                    description=(
                        f"Unknown top-level subdirectory/ies inside .dadaia/: {listed}. "
                        "Relocate or register in the canonical .dadaia/ layout."
                    ),
                    fixable=False,
                )
            )
        return issues

    # ------------------------------------------------------------------
    # SEM-1 invariant helpers
    # ------------------------------------------------------------------

    def _check_sem_1(self, alive_names: frozenset[str]) -> list[DoctorIssue]:
        """SEM-1: scan ctx_locks/*.semaphore.json for orphan or stale entries.

        Orphan: the semaphore's context name is NOT in the set of alive contexts.
        Stale:  the semaphore IS for an alive context, but _is_stale() returns True
                (dead PID, missing session file, or TTL exceeded).

        Both are fixable via fix().
        """
        issues: list[DoctorIssue] = []
        ctx_locks_dir = self._ctx_locks_dir()
        if not ctx_locks_dir.exists():
            return issues

        for sem_file in sorted(ctx_locks_dir.iterdir()):
            if not sem_file.name.endswith(".semaphore.json"):
                continue
            # Derive context name: strip ".semaphore.json" suffix
            context = sem_file.name[: -len(".semaphore.json")]
            data = read_semaphore(self._workspace_root, context)
            if data is None:
                # Unreadable file — cannot assess; skip silently
                continue

            if context not in alive_names:
                # Orphan: context not alive (unknown or dead)
                issues.append(
                    DoctorIssue(
                        code="SEM-1",
                        description=(
                            f"[orphan-semaphore] {sem_file}: context '{context}' is not in "
                            "the alive context set. The semaphore was left by a gone/dead context. "
                            "Run 'dadaia doctor --fix' to reclaim."
                        ),
                        fixable=True,
                    )
                )
            elif _is_stale(data, workspace_root=self._workspace_root):
                # Stale: alive context but dead holder
                owner = str(data.get("owner", "unknown"))
                issues.append(
                    DoctorIssue(
                        code="SEM-1",
                        description=(
                            f"[stale-semaphore] {sem_file}: semaphore for alive context "
                            f"'{context}' is stale (owner={owner}, "
                            f"pid={data.get('pid', 'none')}, "
                            f"heartbeat={data.get('heartbeat', 'none')}). "
                            "Run 'dadaia doctor --fix' to reclaim."
                        ),
                        fixable=True,
                    )
                )
        return issues

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
                lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
                for i, line in enumerate(lines, start=1):
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get("event") in _PRODUCTION_WRITE_EVENTS and not record.get(
                        "task_id"
                    ):
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
                lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
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

        # LOCK-7: orphan lock — implementation lock file exists but the owning
        # session file is absent from .dadaia/sessions/. Distinct from:
        #   LOCK-2 (lock for DEAD context — skipped here)
        #   LOCK-3 (lock stale by TTL — may co-occur; LOCK-7 fires on session absence)
        # Scenario: session file deleted manually/by bug; lock remains; owner is gone.
        # AUTO-FIX: delete orphan lock file + append audit event.
        if locks_dir.exists():
            for f in sorted(locks_dir.iterdir()):
                if f.suffix != ".json":
                    continue
                lock_data = self._read_lock(f)
                if lock_data is None:
                    continue
                ctx_name, release = self._parse_key(f.stem)
                # Skip DEAD-context locks — those are LOCK-2
                if ctx_name in dead_names:
                    continue
                session_id = self._str(lock_data, "session_id")
                if not session_id:
                    continue
                session_file = sessions_dir / f"{session_id}.json"
                if not session_file.exists():
                    issues.append(
                        DoctorIssue(
                            code="LOCK-7",
                            description=(
                                f"Orphan lock '{f.name}': session file for "
                                f"'{session_id}' is absent "
                                f"(context={ctx_name}, release={release}). "
                                "The owning session is gone; lock can be safely reclaimed."
                            ),
                            fixable=True,
                        )
                    )

        # ---- ROOT invariants (T-SANI-05) ----
        exc_globs = self._root_exception_globs()
        issues.extend(self._check_root_1(exc_globs))
        issues.extend(self._check_root_2())
        issues.extend(self._check_root_3(exc_globs))
        issues.extend(self._check_root_4())

        # ---- SEM-1 invariant (T-SEMA-02) ----
        alive_names: frozenset[str] = frozenset(
            ctx.name for ctx in contexts if ctx.state == ContextState.ALIVE
        )
        issues.extend(self._check_sem_1(alive_names))

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

            # LOCK-7: reclaim orphan locks (session file absent, context ALIVE, NOT stale).
            # Only applies when the lock is NOT already handled by LOCK-3 (stale by TTL):
            # if check_lock_state returns STALE the lock goes through LOCK-3 (mark STALE,
            # no delete). LOCK-7 in fix() only deletes locks that appear HELD by TTL
            # (fresh timestamp + live pid) but whose session file is absent.
            sessions_dir = self._sessions_dir()
            if locks_dir.exists():
                for f in sorted(locks_dir.iterdir()):
                    if f.suffix != ".json":
                        continue
                    lock7_data: dict[str, object] | None = self._read_lock(f)
                    if lock7_data is None:
                        continue
                    ctx_name, release = self._parse_key(f.stem)
                    # Skip DEAD-context locks (LOCK-2 handles those)
                    if ctx_name in dead_names:
                        continue
                    # Skip locks that are stale by TTL/dead-pid — LOCK-3 handles those
                    lock7_state = check_lock_state(self._workspace_root, ctx_name, release)
                    if lock7_state == LockState.STALE:
                        continue
                    session_id = self._str(lock7_data, "session_id")
                    if not session_id:
                        continue
                    session_file = sessions_dir / f"{session_id}.json"
                    if not session_file.exists():
                        _append_audit_event(
                            self._workspace_root,
                            event="LOCK_ORPHAN_RECLAIMED",
                            context=ctx_name,
                            release=release,
                            session_id=session_id,
                            runtime=self._str(lock7_data, "runtime", "doctor"),
                            pid=self._int(lock7_data, "pid", 0),
                            reason=(
                                f"LOCK-7: orphan lock '{f.name}' reclaimed — "
                                f"session file for '{session_id}' is absent"
                            ),
                        )
                        f.unlink(missing_ok=True)
                        actions.append(
                            f"LOCK-7: reclaimed orphan lock '{f.name}' "
                            f"(session '{session_id}' file absent, context={ctx_name})"
                        )

        # ROOT-2: delete forbidden caches/outputs at workspace root (safe to delete)
        for cache_name in sorted(_ROOT_FORBIDDEN_CACHES):
            target = self._workspace_root / cache_name
            if target.exists():
                try:
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                    actions.append(
                        f"ROOT-2: deleted forbidden cache/output '{cache_name}' from workspace root"
                    )
                except OSError as exc:
                    actions.append(f"ROOT-2: failed to delete '{cache_name}': {exc}")

        # SEM-1: reclaim orphan and stale semaphores (T-SEMA-02).
        # Runs outside the workspace_lock because:
        #   a) semaphore files live in ctx_locks/, distinct from impl locks,
        #   b) semaphore acquire/release already uses atomic tmp→os.replace,
        #   c) adding Lock 1 here would risk a deadlock when the caller holds the
        #      semaphore and also requests fix() — keep it lightweight.
        all_contexts = self._store.list_all()
        alive_names: frozenset[str] = frozenset(
            ctx.name for ctx in all_contexts if ctx.state == ContextState.ALIVE
        )
        ctx_locks_dir = self._ctx_locks_dir()
        if ctx_locks_dir.exists():
            for sem_file in sorted(ctx_locks_dir.iterdir()):
                if not sem_file.name.endswith(".semaphore.json"):
                    continue
                context = sem_file.name[: -len(".semaphore.json")]
                data = read_semaphore(self._workspace_root, context)
                if data is None:
                    continue
                reclaim = False
                reason = ""
                if context not in alive_names:
                    reclaim = True
                    reason = f"SEM-1: orphan semaphore — context '{context}' not in alive set"
                elif _is_stale(data, workspace_root=self._workspace_root):
                    reclaim = True
                    owner = str(data.get("owner", "unknown"))
                    reason = f"SEM-1: stale semaphore for alive context '{context}' (owner={owner})"
                if reclaim:
                    session_id = str(data.get("owner", "unknown"))
                    _append_semaphore_audit(
                        self._workspace_root,
                        event="SEMAPHORE_RECLAIMED",
                        context=context,
                        session_id=session_id,
                        reason=reason,
                    )
                    sem_file.unlink(missing_ok=True)
                    actions.append(f"SEM-1: reclaimed semaphore '{sem_file.name}' — {reason}")

        return actions
