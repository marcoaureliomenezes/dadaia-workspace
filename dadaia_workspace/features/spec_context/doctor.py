"""DoctorService — diagnose and repair workspace state invariants (v2 model: ALIVE/DEAD)."""

import fnmatch
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.lock_liveness import is_stale
from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.features.spec_context import lease, session_identity
from dadaia_workspace.features.spec_context.locking import (  # noqa: PLC2701
    _audit_log_path,
    context_lock,
    workspace_lock,
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

# Sentinel files older than this are orphans (process SIGKILLed mid-CAS).
_SENTINEL_ORPHAN_AGE = 30.0

# Sessions expired beyond this age are graveyard entries eligible for GC.
_SESSION_GC_TTL_FIELD = "ttl_seconds"
_SESSION_HEARTBEAT_FIELD = "last_seen_at"


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
        pid_probe: Callable[[int], bool] | None = None,
    ) -> None:
        self._store = context_store
        self._git = git_client
        self._workspace_root = workspace_root
        # Injected PID-liveness probe (composition-root seam, like the gate's; T-011-02).
        # ``None`` ⇒ TTL-only LOCK-GC verdict (Windows-safe / legacy-record-safe). A live
        # holder is never reclaimed; ``features`` never imports the adapter — the container
        # (or a caller) supplies the probe built from ``OsProcessProbe``.
        self._pid_probe = pid_probe

    def _repos_dir(self) -> Path:
        return self._workspace_root / "repos"

    def _sessions_dir(self) -> Path:
        return self._workspace_root / ".dadaia" / "sessions"

    def _ctx_locks_dir(self) -> Path:
        return self._workspace_root / ".dadaia" / "states" / "ctx_locks"

    # ------------------------------------------------------------------
    # Helper: read lock data dict (None on error)
    # ------------------------------------------------------------------

    @staticmethod
    def _read_lock(path: Path) -> dict[str, object] | None:
        try:
            result: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
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
    # LOCK-NEW: single-record lease check
    # ------------------------------------------------------------------

    def _check_lease_records(self) -> list[DoctorIssue]:
        """LOCK-NEW: scan ctx_locks/*.lock.json for invalid records.

        - Invalid JSON / missing required fields → warn; --fix deletes it.

        Staleness/reclaim is no longer reported here — that moved to ``_check_lock_gc``
        (LOCK-GC, T-011-02), which honours the pid-liveness veto so a TTL-expired but
        still-running holder is never flagged or reclaimed. LOCK-NEW now covers only the
        structural-corruption cases (a stale-but-valid record is a LOCK-GC concern).
        """
        issues: list[DoctorIssue] = []
        ctx_locks_dir = self._ctx_locks_dir()
        if not ctx_locks_dir.exists():
            return issues

        required_fields = {
            "context",
            "release",
            "session_id",
            "mode",
            "acquired_at",
            "heartbeat",
            "ttl",
        }
        for lock_file in sorted(ctx_locks_dir.iterdir()):
            if not lock_file.name.endswith(".lock.json"):
                continue
            data = self._read_lock(lock_file)
            if data is None:
                issues.append(
                    DoctorIssue(
                        code="LOCK-NEW",
                        description=(
                            f"[invalid-record] {lock_file}: unreadable or invalid JSON. "
                            "Run 'dadaia doctor --fix' to delete it."
                        ),
                        fixable=True,
                    )
                )
                continue
            missing = required_fields - set(data.keys())
            if missing:
                issues.append(
                    DoctorIssue(
                        code="LOCK-NEW",
                        description=(
                            f"[invalid-record] {lock_file}: missing required fields "
                            f"{sorted(missing)}. Run 'dadaia doctor --fix' to delete it."
                        ),
                        fixable=True,
                    )
                )
                continue
        return issues

    # ------------------------------------------------------------------
    # LOCK-GC: stale-lease garbage collection with the pid-liveness veto
    # ------------------------------------------------------------------

    def _check_lock_gc(self) -> list[DoctorIssue]:
        """LOCK-GC: report TTL-expired lease records that are safe to reclaim (T-011-02).

        A record is reclaimable (per ``lease.reclaim`` / the pid-liveness veto) when it is
        TTL-expired AND its holder is demonstrably dead, OR it predates the ``pid`` field
        (legacy/pre-pid — the ``doctor-stale-lease-misdiagnosed-as-forgery`` case, which was
        previously permanently un-reclaimable). A record whose holder pid is still ALIVE is
        NEVER reported, regardless of how far past TTL it is. ``--fix`` deletes the reported
        records; an invalid/corrupt record stays under ``LOCK-NEW`` (a separate concern).
        """
        issues: list[DoctorIssue] = []
        ctx_locks_dir = self._ctx_locks_dir()
        if not ctx_locks_dir.exists():
            return issues
        for lock_file in sorted(ctx_locks_dir.iterdir()):
            if not lock_file.name.endswith(".lock.json"):
                continue
            data = self._read_lock(lock_file)
            if data is None:
                continue  # corrupt/unreadable — owned by LOCK-NEW, not LOCK-GC.
            if not lease.reclaim(data, pid_probe=self._pid_probe):
                continue
            ctx_name = str(data.get("context", lock_file.stem.replace(".lock", "")))
            session_id = str(data.get("session_id", "unknown"))
            pidless = "pid" not in data
            qualifier = "pre-pid record" if pidless else "holder dead/unprobeable"
            issues.append(
                DoctorIssue(
                    code="LOCK-GC",
                    description=(
                        f"[stale-lease] {lock_file}: lease for context '{ctx_name}' is a "
                        f"stale lease from a dead session ({qualifier}; session={session_id}, "
                        f"heartbeat={data.get('heartbeat', 'none')}) — safe to reclaim. "
                        "Run 'dadaia doctor --fix' or 'dadaia lock steal "
                        f"{ctx_name}' to reclaim it."
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

        # LOCK-4: production-write event in lock-events.jsonl missing task_id (NO AUTO-FIX)
        audit_path = _audit_log_path(self._workspace_root)
        if audit_path.exists():
            try:
                lines = [
                    ln for ln in audit_path.read_text(encoding="utf-8").splitlines() if ln.strip()
                ]
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
                lines = [
                    ln for ln in audit_path.read_text(encoding="utf-8").splitlines() if ln.strip()
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

        # ---- ROOT invariants (T-SANI-05) ----
        exc_globs = self._root_exception_globs()
        issues.extend(self._check_root_1(exc_globs))
        issues.extend(self._check_root_2())
        issues.extend(self._check_root_3(exc_globs))
        issues.extend(self._check_root_4())

        # ---- Single-record lease check ----
        issues.extend(self._check_lease_records())

        # ---- Stale-lease GC (probe-aware reclaim; T-011-02) ----
        issues.extend(self._check_lock_gc())

        return issues

    def fix(self) -> list[str]:
        """Fix detected issues.

        INV-5: remove stale repos for DEAD contexts.
        LOCK-NEW (--fix): delete stale/invalid ctx_locks/*.lock.json records.
        Graveyard GC: delete TTL-expired .dadaia/sessions/*.json files.
        Sentinel GC: delete orphan ctx_locks/*.lock.sentinel files (mtime > 30s).

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

            # INV-5: remove stale repos for DEAD contexts.
            # Acquire Lock 2 per slug so alive()'s filesystem ops (which hold
            # Lock 2 while they run) cannot race with this rmtree.
            for ctx in all_contexts:
                if ctx.state == ContextState.DEAD:
                    repo_path = self._repos_dir() / ctx.repo_slug
                    if repo_path.exists():
                        with context_lock(self._workspace_root, ctx.repo_slug):
                            # Re-confirm still DEAD after acquiring Lock 2.
                            ctx_recheck = self._store.get(ctx.name)
                            if ctx_recheck is None or ctx_recheck.state != ContextState.DEAD:
                                continue
                            shutil.rmtree(repo_path)
                        actions.append(
                            f"Removed stale repo '{ctx.repo_slug}' for dead context '{ctx.name}'"
                        )

        # LOCK-NEW: delete stale/invalid lease records (outside workspace_lock —
        # lease files are independent of spec_contexts.json).
        ctx_locks_dir = self._ctx_locks_dir()
        required_fields = {
            "context",
            "release",
            "session_id",
            "mode",
            "acquired_at",
            "heartbeat",
            "ttl",
        }
        if ctx_locks_dir.exists():
            for lock_file in sorted(ctx_locks_dir.iterdir()):
                if not lock_file.name.endswith(".lock.json"):
                    continue
                data = self._read_lock(lock_file)
                code_label = "LOCK-NEW"
                reason_label = ""
                should_delete = False
                if data is None:
                    should_delete = True
                    reason_label = "invalid JSON"
                elif required_fields - set(data.keys()):
                    should_delete = True
                    reason_label = "missing required fields"
                elif lease.reclaim(data, pid_probe=self._pid_probe):
                    # Probe-aware reclaim (T-011-02): TTL-expired + dead/pre-pid holder.
                    # A live-pid holder is NEVER reclaimed regardless of TTL.
                    should_delete = True
                    code_label = "LOCK-GC"
                    reason_label = (
                        "stale lease from dead session (pre-pid record)"
                        if "pid" not in data
                        else "stale lease from dead session"
                    )
                if should_delete:
                    lock_file.unlink(missing_ok=True)
                    actions.append(
                        f"{code_label}: deleted lease record '{lock_file.name}' ({reason_label})"
                    )

        # Graveyard GC: delete TTL-expired session files from .dadaia/sessions/
        sessions_dir = self._sessions_dir()
        if sessions_dir.exists():
            for sess_file in sorted(sessions_dir.iterdir()):
                if not sess_file.name.endswith(".json"):
                    continue
                if sess_file.parent.name == "runtime":
                    continue
                # Read the session record through its single owner (FR-R3-01).
                sess_id = sess_file.name[: -len(".json")]
                sess_data = session_identity.read_session(self._workspace_root, sess_id)
                if sess_data is None:
                    continue
                # Build a TTL-check-compatible dict using session fields
                gc_check: dict[str, object] = {
                    "heartbeat": sess_data.get(_SESSION_HEARTBEAT_FIELD, ""),
                    "ttl": sess_data.get(_SESSION_GC_TTL_FIELD, 300),
                }
                if is_stale(gc_check):
                    sess_file.unlink(missing_ok=True)
                    actions.append(f"GRAVEYARD-GC: deleted expired session file '{sess_file.name}'")

        # Sentinel GC: delete orphan *.lock.sentinel files older than 30 s
        if ctx_locks_dir.exists():
            now_ts = datetime.now(tz=UTC).timestamp()
            for sentinel_file in sorted(ctx_locks_dir.iterdir()):
                if not sentinel_file.name.endswith(".lock.sentinel"):
                    continue
                try:
                    mtime = sentinel_file.stat().st_mtime
                except OSError:
                    continue
                if (now_ts - mtime) > _SENTINEL_ORPHAN_AGE:
                    sentinel_file.unlink(missing_ok=True)
                    actions.append(f"SENTINEL-GC: deleted orphan sentinel '{sentinel_file.name}'")

        # Stable-identity .ptr GC (D1 soul-fold): delete orphan .ptr files where
        # the corresponding .lock.json does not exist or is expired (is_stale).
        # .ptr is a hint, not a lock; orphans must not persist after the lease expires.
        # Iterate the pointer namespace through its single owner (FR-R3-01).
        for ptr_file in session_identity.iter_ptr_files(self._workspace_root):
            ctx_name = ptr_file.name[: -len(".ptr")]
            lock_file = ctx_locks_dir / f"{ctx_name}.lock.json"
            is_orphan = False
            if not lock_file.exists():
                is_orphan = True
            else:
                lock_data = self._read_lock(lock_file)
                if lock_data is None or is_stale(lock_data):
                    is_orphan = True
            if is_orphan:
                ptr_file.unlink(missing_ok=True)
                actions.append(f"PTR-GC: deleted orphan session pointer '{ptr_file.name}'")

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

        return actions
