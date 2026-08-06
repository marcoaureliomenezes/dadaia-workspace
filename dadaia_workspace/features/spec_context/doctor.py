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
from dadaia_workspace.core.execute_bit import PLATFORM_HAS_EXECUTE_BIT
from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.core.record_liveness import is_stale
from dadaia_workspace.core.rule_corpus import CITER_GLOBS, RULES_DIR, scan_rule_corpus
from dadaia_workspace.features.spec_context import presence, session_identity

# Note: INV-1, INV-2, INV-3, INV-6 have been removed in v2. INV-4 and INV-5
# are renamed for the ALIVE/DEAD semantics.

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
    {".agents", ".claude", ".codex", ".dadaia", ".kimi-code", ".pi", "repos"}
)

#: Files allowed at workspace root (exact names, no wildcards). Mirrors the Workspace
#: Root Law and ``hooks/root_whitelist.py``: ``CLAUDE.md`` is the required Claude Code
#: bridge, ``prompt.md`` the optional operator long-prompt file (bug
#: doctor-root-whitelist-contradicts-root-law).
_ROOT_ALLOWED_FILES: frozenset[str] = frozenset({"AGENTS.md", "CLAUDE.md", "prompt.md"})

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
#: tolerated at root with a WARN (ROOT-3, lenient). ``CLAUDE.md`` is NOT here — it is
#: root-law-allowed (see ``_ROOT_ALLOWED_FILES``).
_ROOT_TOOL_CONFIGS: frozenset[str] = frozenset({".mcp.json"})

#: Canonical top-level subdirectories allowed inside `.dadaia/` (ROOT-4).
# The canonical .dadaia/ subdirs. Each has ONE architectural purpose, documented in
# the projected .dadaia/AGENTS.md canonical-folder table. This set is the enforcement
# half of that law: anything else is slop and flags ROOT-4. Do NOT re-add a folder here
# to silence the check — route the concern into the zone that owns it (bug
# doctor-whitelist-legitimizes-slop-dirs, 2026-07-15; the retired junk-drawer entries
# figma-bridge/imgs/references were removed — MCP state -> mcps/, evidence ->
# tmp/<agent>/<date>/).
_DADAIA_ALLOWED_SUBDIRS: frozenset[str] = frozenset(
    {
        # ── Projections (lib-originated; regen via `dadaia public install`) ──
        "agentic",  # staged public assets + manifest.json (projection source-of-truth)
        "hooks",  # projected Python governance hook entrypoints (v0.1.47 W1-9)
        "scripts",  # projected runtime/git-hook scripts
        # ── Runtime working areas ──
        "mcps",  # per-MCP-server working dirs (mcps/<server>/)
        "runtime",  # long-lived local runtime working area for tooling
        # ── CLI/service-owned state ──
        "states",  # machine-readable runtime state JSON
        "sessions",  # per-session identity/bind records (PROTECTED)
        # ── Outputs ──
        "handoff",  # machine-readable agent handoffs (handoff/<context>/)
        "reports",  # human-readable HTML reports (reports/<context>/<agent>/)
        "academy",  # durable agent study/mastery notes + validation ledgers
        # ── Ephemeral (disposable, GC'd) ──
        "tmp",  # scratch + evidence, tmp/<agent>/<YYYYMMDD>/
        "logs",  # telemetry/event logs
        "runs",  # workflow run transcripts
        "dev-report",  # generated developer diagnostic reports
        # ── Artifacts / managed environments ──
        "dist",  # built wheels + local exports
        ".venv",  # managed workspace Python environment
        ".cache",  # redirected tool caches (ruff/coverage), kept out of repos
    }
)

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
        # Kept as a compatibility constructor seam. Session/presence expiry is TTL-only;
        # process liveness never grants blocking authority.
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
    # RETIRED-LOCK-STATE: pre-doctrine cleanup
    # ------------------------------------------------------------------

    def _check_retired_lock_state(self) -> list[DoctorIssue]:
        """Report pre-doctrine context-lock/pointer directories as removable stale state."""
        ctx_locks_dir = self._ctx_locks_dir()
        pointer_dir = self._sessions_dir() / "runtime"
        stale = [path for path in (ctx_locks_dir, pointer_dir) if path.exists()]
        if not stale:
            return []
        return [
            DoctorIssue(
                code="RETIRED-LOCK-STATE",
                description=(
                    "Retired context-global concurrency state exists: "
                    f"{', '.join(str(path) for path in stale)}. Run 'dadaia doctor --fix' "
                    "to remove it; its contents have no authority."
                ),
                fixable=True,
            )
        ]

    # ------------------------------------------------------------------
    # PRESENCE-GC: stale/corrupt advisory presence-record GC (v0.1.76 T-4, FR7)
    # ------------------------------------------------------------------

    def _check_presence_gc(self) -> list[DoctorIssue]:
        """PRESENCE-GC: report stale/corrupt advisory presence records (FR7).

        ``features/spec_context/presence.py`` (``.dadaia/states/presence/<ctx>/<sid>.json``)
        is the only concurrency signal. Presence is advisory-only, so every reported record is
        always ``fixable``: ``--fix`` sweeps them via ``presence.sweep()``, the same
        predicate ``presence.stale_records()`` reports (single source of truth — check()
        and --fix can never disagree).
        """
        issues: list[DoctorIssue] = []
        for ref in presence.stale_records(self._workspace_root):
            issues.append(
                DoctorIssue(
                    code="PRESENCE-GC",
                    description=(
                        f"[stale-presence] context '{ref.context}': advisory presence record "
                        f"for session '{ref.session_id}' is stale or corrupt — safe to reclaim. "
                        "Run 'dadaia doctor --fix' to garbage-collect it."
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
        if PLATFORM_HAS_EXECUTE_BIT and not os.access(entry, os.X_OK):
            return [
                DoctorIssue(
                    code="VENV-1",
                    description=(
                        f"Workspace venv entrypoint not executable: '{entry}'. "
                        f"Restore the exec bit with:  chmod +x {entry}"
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

    def _check_rule_corpus(self) -> list[DoctorIssue]:
        """RULE-1: a by-name law citation that resolves to no rule file.

        Bug ``r9-doctor-omits-rule-corpus-reachable``: this check existed only in
        ``dadaia public doctor``, so the workspace-state doctor reported "All invariants
        OK" for a tree whose agent cited a rule that does not exist. An agent following
        that citation gets no law and no error.

        Not fixable: dadaia cannot invent the missing rule. Either the citation is a typo
        or the rule was never written — both are the author's call. Dead-law (uncited
        rules) stays a ``public doctor`` ``[warn]``; it is hygiene, not a broken
        invariant, and must not turn ``dadaia doctor`` red.
        """
        root = self._workspace_root
        rules_dir = root / RULES_DIR
        available = {p.stem for p in rules_dir.glob("*.md")} if rules_dir.is_dir() else set()
        texts: list[str] = []
        for pattern in CITER_GLOBS:
            for artifact in sorted(root.glob(pattern)):
                try:
                    texts.append(artifact.read_text(encoding="utf-8"))
                except OSError:
                    continue
        scan = scan_rule_corpus(texts, available)
        return [
            DoctorIssue(
                code="RULE-1",
                description=(
                    f"by-name rule '{name}' is cited by an agent, skill or rule but has "
                    f"no reachable surface at .claude/rules/{name}.md — an agent that "
                    "follows the citation gets no law"
                ),
                fixable=False,
            )
            for name in scan.unreachable
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

        # ---- ROOT invariants (T-SANI-05) ----
        exc_globs = self._root_exception_globs()
        issues.extend(self._check_root_1(exc_globs))
        issues.extend(self._check_root_2())
        issues.extend(self._check_root_3(exc_globs))
        issues.extend(self._check_root_4())

        issues.extend(self._check_retired_lock_state())

        # ---- Stale/corrupt advisory presence-record GC (v0.1.76 T-4, FR7) ----
        issues.extend(self._check_presence_gc())

        # ---- Venv health (FR-W3-02, T-014-13) ----
        issues.extend(self._check_venv_health())

        # ---- Efficiency-audit staleness (EFF-1, v0.1.60 FR7) ----
        issues.extend(self._check_efficiency_audit())

        # ---- By-name rule-law reachability (RULE-1) ----
        issues.extend(self._check_rule_corpus())

        return issues

    def fix(self) -> list[str]:
        """Fix detected issues.

        INV-5: remove stale repos for DEAD contexts.
        RETIRED-LOCK-STATE: remove the entire pre-doctrine context-lock directory.
        Graveyard GC: delete TTL-expired .dadaia/sessions/*.json files.
        """
        actions: list[str] = []

        for ctx in self._store.list_all():
            if ctx.state != ContextState.DEAD:
                continue
            repo_path = self._repos_dir() / ctx.repo_slug
            if not repo_path.exists():
                continue
            ctx_recheck = self._store.get(ctx.name)
            if ctx_recheck is None or ctx_recheck.state != ContextState.DEAD:
                continue
            shutil.rmtree(repo_path)
            actions.append(f"Removed stale repo '{ctx.repo_slug}' for dead context '{ctx.name}'")

        ctx_locks_dir = self._ctx_locks_dir()
        if ctx_locks_dir.exists():
            shutil.rmtree(ctx_locks_dir)
            actions.append("RETIRED-LOCK-STATE: removed .dadaia/states/ctx_locks")
        pointer_dir = self._sessions_dir() / "runtime"
        if pointer_dir.exists():
            shutil.rmtree(pointer_dir)
            actions.append("RETIRED-LOCK-STATE: removed .dadaia/sessions/runtime")

        # PRESENCE-GC (v0.1.76 T-4, FR7): sweep stale/corrupt advisory presence records.
        # presence.sweep() deletes exactly what presence.stale_records() (check()) reports —
        # single source of truth, so --fix can never disagree with what check() flagged.
        for sess_id in presence.sweep(self._workspace_root):
            actions.append(f"PRESENCE-GC: deleted stale presence record for session '{sess_id}'")

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
