"""PreToolUse SDD gate (the canonical, cross-platform gate surface).

This hook is the enforcement entrypoint the harness invokes as
``python -m dadaia_workspace.hooks.sdd_gate``. It does NOT re-derive the gate policy:
it delegates classification + decision to :func:`gate_policy.classify_path` and
:func:`gate_policy.evaluate`, which is the single source of truth (avoids a third
drifting copy alongside the bash gate).

Parity invariants preserved verbatim from the rc-4 shell gate:

1. **PATH-first context slug.** The context is derived from the write-target path
   (``repos/<slug>/...``); ``DADAIA_CONTEXT`` is consulted only as an override when the
   path is under no repo. A write under ``repos/B/...`` therefore never acquires
   ``repos/A``'s lease (fixes gate-cross-context-lock-contamination).
2. **PROTECTED is the sole fail-CLOSED path.** ``.dadaia/sessions/`` writes are blocked
   unconditionally (SEC-01); every other class fails OPEN.
3. **Fail-open posture.** Only a genuine live-foreign ``LockHeldError`` BLOCKs (surfaced
   by ``gate_policy.evaluate``); any other error → ALLOW. The hook never deadlocks.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dadaia_workspace.core import lock_liveness
from dadaia_workspace.features.spec_context import gate_policy, lease, session_identity
from dadaia_workspace.hooks import _common

_SLUG_STRIP = re.compile(r"[^A-Za-z0-9_-]")

#: Default mode when neither the env override nor a session record resolves one. Missing-mode
#: sessions stay IMPLEMENTATION-capable (free-lease acquire OK) — Decision D-3 / FR-R4-04.
_DEFAULT_MODE = "IMPLEMENTATION"


def _build_pid_probe() -> lease.PidProbe | None:
    """Build the PID-liveness probe injected into the lease (WS-R2 FR-R2-03).

    Sources the container's ``OsProcessProbe`` and adapts it to the lease's
    ``(pid) -> alive?`` callable. The hook layer owns this wiring so ``features/lease.py``
    never imports ``infrastructure/process_probe_adapter`` (no new import-linter ignore).

    Returns ``None`` if the probe cannot be constructed — the lease then degrades to
    TTL-only (Windows-safe). Any construction error fails open (probe absent ⇒ TTL
    fallback), never blocks the gate. ``OsProcessProbe`` is itself platform-seamed
    (``PLATFORM.has_os_kill_liveness`` selects ``os.kill`` vs the Windows ``OpenProcess``
    existence check), so a single probe instance is correct on every host.

    The container (``dadaia_workspace.container``) is the canonical composition root that
    binds ``OsProcessProbe`` for the app; the hook imports the same adapter here so the
    feature layer (``features/lease.py``) never imports infrastructure (import-linter law).
    """
    try:
        from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe

        probe = OsProcessProbe()
        return lambda pid: probe.is_pid_alive(pid)
    except Exception:  # noqa: BLE001 — never let probe wiring break the gate; TTL fallback.
        return None


def _resolve_holder_pid(payload: dict[str, object]) -> int:
    """Resolve the LONG-LIVED holder pid to stamp into the lease record (WS-R2, NF-1 fix).

    The gate runs as a short-lived ``python -m dadaia_workspace.hooks.sdd_gate`` child that
    exits milliseconds after acquiring the lease. Recording ``os.getpid()`` (this child's
    own pid) makes the no-steal pid-veto inert: a foreign session later probes a pid that is
    already dead, so it always reclaims — the exact lease-theft incident. We therefore record
    a pid that **outlives the hook**:

    1. If the harness stdin payload carries an explicit harness pid (``harness_pid`` /
       ``parent_pid`` / ``ppid``), prefer it — it names the long-lived harness process most
       precisely. (No current harness sends one; this is forward-compatible and lets tests
       pin a known-alive pid.)
    2. Otherwise ``os.getppid()`` — the parent that spawned this hook child, i.e. the harness
       process. It stays alive for the whole session, so a foreign probe sees the holder as
       genuinely running and the no-steal veto fires while the harness is busy (even across a
       single >120 s tool call), and only releases once the harness process truly dies.

    A non-positive or unparseable payload pid falls back to ``os.getppid()``.
    """
    for key in ("harness_pid", "parent_pid", "ppid"):
        raw = payload.get(key)
        if isinstance(raw, int) and raw > 0:
            return raw
        if isinstance(raw, str):
            try:
                value = int(raw.strip())
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    return os.getppid()


def _resolve_workspace() -> Path:
    """Resolve the workspace root: ``WORKSPACE_ROOT`` env wins, else walk up from cwd."""
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def _context_slug(workspace: Path, fpath: Path) -> str:
    """Derive the context slug PATH-first from the write target.

    A target under ``<ws>/repos/<slug>/...`` belongs to context ``<slug>`` regardless of
    which context is first-ALIVE in the registry. ``DADAIA_CONTEXT`` is honored only as an
    explicit override when the path is under no repo. The result is sanitized to
    ``[A-Za-z0-9_-]`` (CWE-22).
    """
    repos = workspace / "repos"
    slug = ""
    try:
        rel = fpath.resolve().relative_to(repos.resolve())
        parts = rel.parts
        if parts:
            slug = parts[0]
    except (ValueError, OSError):
        slug = ""
    if not slug:
        slug = os.environ.get("DADAIA_CONTEXT", "")  # explicit override only
    return _SLUG_STRIP.sub("", slug or "")


def _resolve_mode(
    workspace: Path,
    session_id: str,
    ctx: str = "",
    pid_probe: lease.PidProbe | None = None,
    active_release: str | None = None,
) -> str:
    """Resolve the session's bind mode (WS-R4 FR-R4-02/03/04 + NF-2 fix). First hit wins:

    1. ``DADAIA_MODE`` env fast-path override — an operator-shell escape (the harness never
       sets this; it is honored only when the operator deliberately exports it).
    2. The CLI-owned session record keyed by the **resolved harness session id**
       (``session_identity.read_session``). A session that bound *itself* (its own harness sid
       reached the bind CLI) is found here; this record **wins over the incumbent pointer**
       so a live implementation session is never downgraded by another session's stale
       read-bind on the same context.
    3. **CONTEXT-INCUMBENT record** (NF-2 fix): the mode of the session named by the
       context's incumbent pointer ``sessions/runtime/<ctx>.ptr`` via
       ``session_identity.resolve_identity(ctx)``. This is the harness-real path for the
       default ``dadaia context bind`` flow: the bind CLI mints a fresh sid the running
       harness never reports, but it also refreshes the context incumbent pointer at bind
       time, so the operator's bind binds the **CONTEXT**. A different harness sid in the
       same context then resolves the bound mode through the incumbent pointer — even with no
       env var and no self-keyed record. Empty ``ctx`` skips this step (no context to key on).

       **Anti-downgrade guard:** the incumbent is honored only when it does NOT contradict a
       live lease holder. If a lease record exists and its ``session_id`` differs from the
       incumbent pointer (a different session legitimately took implementation after a stale
       read-bind), the incumbent is treated as stale and ignored — a live implementation
       holder is never downgraded to READ by another session's leftover read-bind.
    4. Default ``IMPLEMENTATION`` (FR-R4-04 / D-3): no env, no self record, no incumbent
       binding ⇒ lease-capable; may acquire a *free* lease.

    Fail-soft: every lookup returns ``None`` on missing/malformed input, so mode resolution
    never raises and never blocks the gate by accident.
    """
    env_mode = os.environ.get("DADAIA_MODE")
    if env_mode:
        return env_mode
    rec = session_identity.read_session(workspace, session_id)
    if rec is not None:
        raw = rec.get("mode")
        if raw:
            return str(raw)
    if ctx:
        incumbent = session_identity.resolve_identity(workspace, ctx)
        incumbent_sid = incumbent.get("incumbent")
        incumbent_mode = incumbent.get("mode")
        if (
            incumbent_sid
            and incumbent_mode
            and not _incumbent_is_stale(
                workspace, ctx, str(incumbent_sid), pid_probe, active_release
            )
        ):
            return str(incumbent_mode)
    return _DEFAULT_MODE


def _incumbent_is_stale(
    workspace: Path,
    ctx: str,
    incumbent_sid: str,
    pid_probe: lease.PidProbe | None,
    active_release: str | None = None,
) -> bool:
    """True if a **live** lease record names a session OTHER than the incumbent pointer.

    A read-bind sets the incumbent pointer but takes no lease. If a *different* session then
    legitimately acquires the implementation lease and is still **live**, the live holder must
    not be downgraded to the read-bind's mode — the incumbent is stale and ignored
    (anti-downgrade, NF-2).

    Liveness uses the canonical kernel predicate ``core.lock_liveness.is_stale`` — the same
    TTL + pid-probe definition the MUTATING gate path uses (NF-4 fix). A *dead* leftover record
    (TTL-stale heartbeat and dead/absent pid) — the normal residue after an implementation
    session ends, which nothing deletes until takeover or doctor GC — does NOT defeat the
    incumbent: a fresh ``bind --mode read`` is honored. Absence of a record (no holder yet) is
    likewise not stale: the read-bind still governs.
    """
    holder = lease.read_record(workspace, ctx)
    if holder is None:
        return False
    holder_sid = holder.get("session_id")
    if not holder_sid or str(holder_sid) == incumbent_sid:
        return False
    # A divergent holder defeats the incumbent only when it is genuinely LIVE (TTL-fresh, or
    # TTL-stale but its pid is still alive). A dead/TTL-stale leftover does not. ``active_release``
    # (T-43-10): a holder pinned to a closed/archived release is semantically dead and never
    # defeats the incumbent, regardless of its pid liveness.
    return not lock_liveness.is_stale(holder, pid_probe=pid_probe, active_release=active_release)


def _active_field(specs_dir: Path, field: str) -> str | None:
    """Read a ``<field>: <value>`` line from ``releases/ACTIVE.md`` (tri-state).

    v0.1.50 FR1 (audit F-3): the return distinguishes three outcomes —
    ``str`` (readable; ``""`` when the field is missing), ``""`` when the file does
    not exist (a fresh context legitimately has no ACTIVE.md — "no release" truth),
    and ``None`` when the file exists but could NOT be read (a genuine I/O failure).
    Callers must treat ``None`` as UNKNOWN, never as "none": an unreadable ACTIVE.md
    must not weaken the lease pid-veto via the release-mismatch reclaim.
    """
    active = specs_dir / "releases" / "ACTIVE.md"
    try:
        text = active.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError:
        return None
    pat = re.compile(rf"^{re.escape(field)}:\s*(.+?)\s*$", re.MULTILINE)
    m = pat.search(text)
    return m.group(1) if m else ""


def _evaluate_target(
    payload: dict[str, object], workspace: Path, raw_path: str
) -> tuple[gate_policy.Decision, str]:
    """Evaluate ONE write-target path through the gate policy.

    Returns ``(ALLOW, "")`` for any allow path and ``(BLOCK, reason)`` for a blocked one.
    Fail-open: an unresolvable/unattributable MUTATING write yields ALLOW (matches shell).
    The caller (``main``) iterates every ``apply_patch`` file header and lets the most
    restrictive verdict win (FR-W4-04) — the first BLOCK short-circuits the whole patch.
    """
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = workspace / fpath

    # Workspace-relative path for the policy classifier (POSIX-style separators).
    try:
        rel_path = fpath.resolve().relative_to(workspace.resolve()).as_posix()
    except (ValueError, OSError):
        rel_path = fpath.as_posix()

    cls = gate_policy.classify_path(rel_path)

    # PROTECTED short-circuit (sole fail-CLOSED path): no context/lease work needed.
    if cls == gate_policy.PathClass.PROTECTED:
        return gate_policy.evaluate(
            workspace,
            rel_path,
            ctx="",
            phase="",
            session_id="",
            release="",
            mode="",
        )

    ctx = _context_slug(workspace, fpath)
    specs_dir = workspace / "repos" / ctx / "specs" if ctx else workspace / "specs"
    phase = _active_field(specs_dir, "phase") or ""
    # Tri-state release read (v0.1.50 FR1): a readable ACTIVE.md that says none (or
    # an absent file) yields the legitimate "none" — release-aware reclaim applies;
    # an UNREADABLE ACTIVE.md (I/O failure) yields veto_release=None so the pid-veto
    # is preserved (an I/O failure never makes a live holder stealable).
    release_raw = _active_field(specs_dir, "release")
    release = release_raw or "none"
    veto_release: str | None = None if release_raw is None else release
    session_id = _common.resolve_session_id(payload, default="anon-session")
    # Single probe construction point (R8 dedup): the PID-liveness probe is built once here
    # and threaded into both the incumbent-staleness check (via ``_resolve_mode``) and the
    # final ``gate_policy.evaluate`` call below — never re-instantiated per call site.
    pid_probe = _build_pid_probe()
    # Mode resolution order (WS-R4 + NF-2): DADAIA_MODE env override → self-keyed session
    # record → context-incumbent record → default. Passing ``ctx`` enables the incumbent
    # fallback so a default `dadaia context bind --mode read` (which mints a sid the harness
    # never reports) still binds the CONTEXT and is honored without any env var.
    # ``active_release`` (T-43-10): a lease pinned to a non-ACTIVE (closed/archived) release is
    # treated as reclaimable in the liveness verdict. ``release`` here is ACTIVE.md's release
    # (``"none"`` when archived), so any release-pinned stale holder on a different release is
    # no longer a live incumbent that downgrades this session's mode.
    mode = _resolve_mode(workspace, session_id, ctx, pid_probe, active_release=veto_release)

    # MUTATING with no resolvable context → fail open (UNGATED, no lease), matching shell.
    # NOTE: a READ-bound session that *does* resolve a context is still blocked below by
    # gate_policy.evaluate (non-acquiring); the no-context fail-open only covers MUTATING
    # writes the gate cannot attribute to any context (no slug, no DADAIA_CONTEXT).
    if cls == gate_policy.PathClass.MUTATING and not ctx:
        return gate_policy.Decision.ALLOW, ""

    return gate_policy.evaluate(
        workspace,
        rel_path,
        ctx=ctx,
        phase=phase,
        session_id=session_id,
        release=release,
        veto_release=veto_release,
        mode=mode,
        pid_probe=pid_probe,
        # NF-1: record a LONG-LIVED pid (the harness, via getppid / payload), never this
        # ephemeral hook child's own — otherwise the no-steal veto probes a dead pid.
        holder_pid=_resolve_holder_pid(payload),
    )


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """Pure SDD-gate policy over an ALREADY-PARSED hook payload.

    Returns a block reason string when the write must be BLOCKed, else ``None`` (ALLOW).
    This is the reusable policy surface the merged ``pre_gate`` entrypoint drives (it reads
    stdin once and dispatches). ``main`` is a thin wrapper kept one release for back-compat
    direct wiring (``python -m dadaia_workspace.hooks.sdd_gate``).

    FR-W4-04: classify EVERY write target. A multi-file apply_patch surfaces every file
    header; the most restrictive verdict wins — the first BLOCK stops the whole patch.
    """
    name = _common.tool_name(payload)
    if not _common.is_write_tool(name):
        return None

    raw_paths = _common.target_paths(payload)
    if not raw_paths:
        # Fail-safe: unparseable target → ALLOW (never deadlock on a parse miss).
        return None

    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open: unresolved workspace must not block
        return None

    for raw_path in raw_paths:
        decision, reason = _evaluate_target(payload, workspace, raw_path)
        if decision == gate_policy.Decision.BLOCK:
            return reason
    return None
