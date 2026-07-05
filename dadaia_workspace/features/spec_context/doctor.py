"""DoctorService — diagnose and repair workspace state invariants (v2 model: ALIVE/DEAD)."""

import fnmatch
import json
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.core.lock_liveness import is_stale
from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.core.platform import PLATFORM
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
# EFF-1 — recurring efficiency-audit staleness marker (v0.1.60 FR7)
# ---------------------------------------------------------------------------

#: Days after which the recorded efficiency audit is considered stale (EFF-1 fires).
EFFICIENCY_AUDIT_STALE_DAYS = 30

#: The marker file the ``dadaia reports mark-efficiency-audit`` writer produces and this
#: check reads. Kept in sync with ``cli/commands/reports.py`` by the writer→doctor
#: round-trip test (``AC-8``); a divergence there would break the production clear path.
_EFFICIENCY_AUDIT_MARKER = "last_efficiency_audit.json"

# ---------------------------------------------------------------------------
# ROOT-* invariant constants
# ---------------------------------------------------------------------------

#: Directories allowed at workspace root (exact names, no wildcards).
_ROOT_ALLOWED_DIRS: frozenset[str] = frozenset(
    {".agents", ".claude", ".codex", ".dadaia", ".pi", "repos"}
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
_ROOT_TOOL_CONFIGS: frozenset[str] = frozenset({".mcp.json", "CLAUDE.md"})

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
        # Python governance hooks projected under .dadaia/hooks/ (workspace-init) — a
        # canonical subdir, not a ROOT-4 violation (v0.1.47 W1-9, bug
        # workspace-doctor-root4-false-positive-dadaia-hooks).
        "hooks",
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

# Sentinel files older than this are orphans (process SIGKILLed mid-CAS). DP-1 (v0.1.14):
# value sourced from ``core.kernel_tunables`` so the doctor's SENTINEL-GC and the lease's
# inline cleanup measure against the identical threshold (no drift).
_SENTINEL_ORPHAN_AGE = kernel_tunables.SENTINEL_ORPHAN_AGE_SECONDS

# Sessions expired beyond this age are graveyard entries eligible for GC. The field names
# are owned by ``session_identity`` (the single owner of the session-record schema); the
# GC liveness clock is resolved via ``session_identity.liveness_timestamp`` (last_seen_at,
# with TTL-from-creation fallback for pre-heartbeat records — T-011-04 / FR-W1-04 / ADR-8).
_SESSION_GC_TTL_FIELD = session_identity.SESSION_GC_TTL_FIELD


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
        # Session-store path via the single owner (T-011-05 / FR-W1-05, ADR-12) — the
        # doctor no longer constructs ``.dadaia/sessions`` itself.
        return session_identity.sessions_dir(self._workspace_root)

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

    def _check_venv_health(self) -> list[DoctorIssue]:
        """VENV-1 — the workspace venv exists with an executable ``dadaia`` entrypoint.

        FR-W3-02 (ADR-G4). The workspace law requires ``dadaia`` / ``pip`` / ``python -m
        dadaia_workspace`` to run from ``<ws>/.dadaia/.venv/bin/`` (the W3 Bash gate
        enforces this for agents). This invariant surfaces a broken venv before an agent
        hits the gate: the venv dir is absent, or its ``dadaia`` entrypoint is missing or
        non-executable. Windows-safe — the scripts dir / exe suffix come from ``PLATFORM``
        and the exec check uses ``os.access`` (the platform-correct probe). Not fixable:
        rebuilding a venv is an operator action (``dadaia init`` / re-bootstrap), never an
        auto-repair.
        """
        venv_bin = self._workspace_root / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
        if not venv_bin.is_dir():
            return [
                DoctorIssue(
                    code="VENV-1",
                    description=(
                        f"Workspace venv missing: '{venv_bin}' does not exist. Workspace "
                        "tooling (dadaia/pip/python -m dadaia_workspace) must run from this "
                        "venv. Re-bootstrap it (e.g. 'dadaia init' or the documented "
                        "venv setup)."
                    ),
                    fixable=False,
                )
            ]
        entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
        if not entry.is_file():
            return [
                DoctorIssue(
                    code="VENV-1",
                    description=(
                        f"Workspace venv entrypoint missing: '{entry}' not found. "
                        "Re-bootstrap the workspace venv."
                    ),
                    fixable=False,
                )
            ]
        if not os.access(entry, os.X_OK):
            return [
                DoctorIssue(
                    code="VENV-1",
                    description=(
                        f"Workspace venv entrypoint not executable: '{entry}'. "
                        "Restore the exec bit (chmod +x) or re-bootstrap the venv."
                    ),
                    fixable=False,
                )
            ]
        return []

    def _check_efficiency_audit(self) -> list[DoctorIssue]:
        """EFF-1 (FR7) — flag a stale or malformed efficiency-audit marker.

        Reads ``.dadaia/states/last_efficiency_audit.json`` (schema
        ``{schema_version, last_efficiency_audit, by, report}``) and emits a
        ``DoctorIssue(code="EFF-1", fixable=False, ...)`` — NOT a ``[warn]`` token, and the
        bare ``dadaia doctor`` exit stays 0 (the service never raises on issues). 4-case
        matrix: *absent* ⇒ no issue (fresh-workspace happy path unchanged); *fresh* (≤
        :data:`EFFICIENCY_AUDIT_STALE_DAYS`) ⇒ no issue; *stale* (> threshold) ⇒ EFF-1;
        *malformed* (invalid JSON / missing ``last_efficiency_audit`` / unparseable
        timestamp) ⇒ EFF-1 "malformed marker" — **never a crash**.
        """
        clear = "run: dadaia reports mark-efficiency-audit --report <report-path>"
        marker = self._workspace_root / ".dadaia" / "states" / _EFFICIENCY_AUDIT_MARKER
        if not marker.exists():
            return []

        def _malformed(reason: str) -> list[DoctorIssue]:
            return [
                DoctorIssue(
                    code="EFF-1",
                    description=f"efficiency-audit marker is malformed ({reason}) — {clear}",
                    fixable=False,
                )
            ]

        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return _malformed("invalid JSON")
        if not isinstance(data, dict):
            return _malformed("not a JSON object")
        raw = data.get("last_efficiency_audit")
        if not isinstance(raw, str) or not raw.strip():
            return _malformed("missing 'last_efficiency_audit'")
        try:
            recorded = datetime.fromisoformat(raw)
        except ValueError:
            return _malformed("unparseable 'last_efficiency_audit' timestamp")
        if recorded.tzinfo is None:
            recorded = recorded.replace(tzinfo=UTC)

        age = datetime.now(tz=UTC) - recorded
        if age <= timedelta(days=EFFICIENCY_AUDIT_STALE_DAYS):
            return []
        return [
            DoctorIssue(
                code="EFF-1",
                description=(
                    f"efficiency audit is {age.days} day(s) old "
                    f"(threshold {EFFICIENCY_AUDIT_STALE_DAYS}d) — {clear}"
                ),
                fixable=False,
            )
        ]

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

        # CTX-URL-1 (T-011-08 / FR-W2-03 d): an ALIVE context with an empty repo_url is
        # un-portable — an export/import + ``context alive`` on another machine would
        # ``git clone ""`` and fail. Surface it so the operator can repair via
        # ``dadaia context update <name> --url <url>`` (or re-run ``alive`` while the
        # on-disk origin remote is present, which back-fills automatically).
        for ctx in contexts:
            if ctx.state == ContextState.ALIVE and not ctx.repo_url:
                issues.append(
                    DoctorIssue(
                        code="CTX-URL-1",
                        description=(
                            f"Context '{ctx.name}' is alive but has an empty repo_url "
                            "(un-portable). Run 'dadaia context update "
                            f"{ctx.name} --url <url>' to set it, or re-run "
                            f"'dadaia context alive {ctx.name}' while the repo's origin "
                            "remote is on disk to back-fill it automatically."
                        ),
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

        # ---- Venv health (FR-W3-02, T-014-13) ----
        issues.extend(self._check_venv_health())

        # ---- Efficiency-audit staleness (EFF-1, v0.1.60 FR7) ----
        issues.extend(self._check_efficiency_audit())

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
                # Build a TTL-check-compatible dict. The liveness clock is the
                # heartbeat-renewed ``last_seen_at`` (T-011-04 / FR-W1-04, ADR-8 amended),
                # with TTL-from-creation fallback for pre-heartbeat records — resolved by
                # the single owner. The session-record pid is NOT passed (no pid_probe): the
                # bind-CLI pid is dead by construction, so bind GC is pure last_seen_at TTL.
                gc_check: dict[str, object] = {
                    "heartbeat": session_identity.liveness_timestamp(sess_data),
                    "ttl": sess_data.get(
                        _SESSION_GC_TTL_FIELD, kernel_tunables.SESSION_GC_TTL_SECONDS
                    ),
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
