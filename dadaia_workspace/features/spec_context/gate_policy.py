"""Path-classifier + decision policy for the SDD gate (single source of truth).

The enforced gate is the Python hook package ``dadaia_workspace.hooks``. Since
v0.1.14 (FR-W4-01) a SINGLE merged PreToolUse entrypoint ``pre_gate`` reads stdin
once and runs the registered policies in order (root-whitelist → venv-guard → SDD
gate); the standalone ``sdd_gate`` / ``root_whitelist`` entrypoints retain their
``main()`` one release for back-compat but their pure ``evaluate_payload`` policy
surfaces are what ``pre_gate`` reuses. ``sdd_post_gate`` (PostToolUse heartbeat) and
``ctx_inject`` (session bootstrap) stay separate. All are wired as ``<python> -m
dadaia_workspace.hooks.<name>`` commands across every harness (Claude
``settings.json``, Codex ``hooks.json``). The legacy bash hook quartet was retired in
v0.1.10 (Decision D-1); the only remaining shell asset is
``public/scripts/pre-push-ci-gate.sh`` (a real git hook, deliberately shell).

This module is the gate's path-classifier and decision policy: the fail-safe
property table (AC-04) and the activity-class exemption matrix (AC-05) are
unit-tested against it, and ``hooks.sdd_gate`` delegates here so there is no
second classifier implementation to keep in byte-parity.

For the MUTATING class the gate is the single acquisition point: it delegates to
:func:`lease.acquire` (O_EXCL CAS). This module does the same, so the Python tests
exercise the real lease code path, not a stand-in.

The PROTECTED class (SEC-01, F-07) is the sole fail-CLOSED path: writes to
``.dadaia/sessions/`` (the CLI-owned lease-identity store) are blocked unconditionally
and evaluated BEFORE any fail-open branch, protecting the ``.ptr`` from forgery
(confused-deputy / CWE-284). The Python hook ``dadaia_workspace.hooks.sdd_gate``
delegates here — PROTECTED flows through without reimplementation in the hook.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from dadaia_workspace.core.exceptions import LockHeldError
from dadaia_workspace.features.spec_context import lease

__all__ = ["Decision", "PathClass", "classify_path", "evaluate"]

#: Ordered ADDITIVE prefixes — always allowed (never blocked, never locked).
#: specs/audits/ is ADDITIVE (FR-P1-14/D2): parallel audit sessions write here
#: without a MUTATING lease. Audit dirs use collision-safe naming per FR-P1-16:
#:   specs/audits/<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/
#:
#: WS-R1 split (FR-R1-01/05): the ``specs/`` ADDITIVE classes apply both at the
#: workspace root *and* relative to a context root (``repos/<slug>/``). The ``.dadaia/``
#: classes are workspace-root-only — ``.dadaia/`` is forbidden inside any repo working
#: tree (root AGENTS.md repo-cleanliness law), so there is no in-repo ``.dadaia/``
#: ADDITIVE class to honor.
_SPECS_ADDITIVE_PREFIXES: tuple[str, ...] = (
    "specs/backlog/",
    "specs/bugs/",
    "specs/audits/",
)
#: Per-artifact ``_archive`` subdirs (v0.1.46 AC-4). These are FROZEN (read-only for
#: file-write tools) and MUST be matched BEFORE ``_SPECS_ADDITIVE_PREFIXES`` in
#: ``_classify_specs_relative`` — otherwise ``specs/bugs/`` (ADDITIVE) is checked first
#: and swallows ``specs/bugs/_archive/`` as ADDITIVE (the R-2 ordering bug). The trailing
#: ``/`` is load-bearing: only ``_archive/`` is FROZEN, never a ``_archive``-prefixed
#: sibling like ``specs/bugs/_archivefoo.jsonl`` (which stays ADDITIVE). Archive MOVES run
#: via ``git mv`` (Bash), outside the file-tool gate envelope — FROZEN only blocks
#: Write/Edit *into* the archive, not the move that lands files there.
_ARCHIVE_SUBDIR_PREFIXES: tuple[str, ...] = (
    "specs/backlog/_archive/",
    "specs/audits/_archive/",
    "specs/bugs/_archive/",
)
_DADAIA_ADDITIVE_PREFIXES: tuple[str, ...] = (
    ".dadaia/reports/",
    ".dadaia/handoff/",
    ".dadaia/tmp/",
)
_MEMORY_PREFIX = "specs/memory/"
_FROZEN_PREFIX = "specs/_archive/"
#: A path under ``repos/<slug>/`` whose context-relative remainder matches one of these
#: ``specs/`` class prefixes is classified by that class. Every other in-repo remainder —
#: production source AND unlisted ``specs/<other>`` files (e.g. ``specs/constitution.md``)
#: — is MUTATING (FR-R1-04): a ``ctx_rel`` matching no class NEVER falls through to UNGATED.
#: SEC-01 (CWE-284): .dadaia/sessions/ holds CLI-owned runtime session state, incl. the
#: single-session lease identity pointer (.dadaia/sessions/runtime/<ctx>.ptr). Agents must
#: NOT write these via Write/Edit — only the dadaia CLI/bootstrap may (it writes via Python,
#: outside the tool gate). This is the SOLE fail-CLOSED class: it blocks unconditionally,
#: evaluated BEFORE the fail-open branches below.
_PROTECTED_PREFIX = ".dadaia/sessions/"
#: SEC-01 block reason emitted by the Python hook ``dadaia_workspace.hooks.sdd_gate``,
#: which delegates here so PROTECTED has a single message source.
_PROTECTED_MESSAGE = (
    "[GATE] .dadaia/sessions/ is CLI-owned runtime state, incl. the single-session lease "
    "identity pointer .dadaia/sessions/runtime/<ctx>.ptr. Agents must not write here via "
    "Write/Edit — only the dadaia CLI/bootstrap may. Blocked to protect lease-identity "
    "integrity (the sole deterministic lock); forging the .ptr would let a second session "
    "steal a Spec Context binding (SEC-01 / CWE-284)."
)
#: Phases in which product-engineer may write memory atoms (FR-P1-13).
_MEMORY_WRITE_PHASES: frozenset[str] = frozenset({"DEFINITION", "CLOSURE"})

#: Non-acquiring (READ-resolved) mode tokens (WS-R4 FR-R4-03 / Decision D-3). A session
#: whose resolved mode is one of these is **non-acquiring**: a MUTATING write is BLOCKed
#: WITHOUT touching the lease (no acquire, no lease-record write). The bind CLI persists
#: ``READ`` (operator aliases ``read``/``spec`` both map here); ``BOUND_READ`` is accepted
#: as a defensive synonym. Comparison is case-insensitive against the upper-cased token.
#:
#: Only explicit READ blocks MUTATING (Decision D-3): every other mode — missing,
#: ``IMPLEMENTATION``, ``BOUND_IMPLEMENTATION``, ``BOUND_REVIEW`` — is lease-taking and may
#: acquire a *free* lease. ``BOUND_REVIEW`` is treated exactly like implementation at the
#: gate: the spec grants review no gate rights distinct from implementation (FR-R4-03
#: scopes READ as the only blocking mode), so review keeps the simple lease-taking path.
_READ_MODES: frozenset[str] = frozenset({"READ", "BOUND_READ"})

#: BLOCK message for a READ-resolved session attempting a MUTATING write. It names the
#: documented path to write rights (``bind --mode implementation``) WITHOUT any banned
#: auto-rebind nag: it states a fact about the session's bound mode and the one-time
#: operator action that grants write rights, never instructing a mid-flow relaunch.
_READ_BLOCK_MESSAGE = (
    "[RULE READ] '{rel_path}' is a MUTATING write, but this session is bound in read "
    "(observe) mode — read sessions are non-acquiring and never take or modify a lease. "
    "Additive paths (specs/backlog, specs/bugs, specs/audits, .dadaia/reports, "
    ".dadaia/handoff, .dadaia/tmp) remain writable. To gain write rights, the operator "
    "binds implementation mode once: `dadaia context bind {ctx} --mode implementation`."
)


def _is_read_mode(mode: str) -> bool:
    """True iff ``mode`` resolves to a non-acquiring READ binding (case-insensitive)."""
    return mode.strip().upper() in _READ_MODES


class PathClass(Enum):
    ADDITIVE = "ADDITIVE"
    MEMORY = "MEMORY"
    FROZEN = "FROZEN"
    MUTATING = "MUTATING"
    PROTECTED = "PROTECTED"
    UNGATED = "UNGATED"


class Decision(Enum):
    ALLOW = "allow"
    BLOCK = "block"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _classify_specs_relative(spec_rel: str) -> PathClass | None:
    """Apply the ordered ``specs/`` class taxonomy to a root- or context-relative path.

    Returns the matched ``PathClass`` (ADDITIVE/MEMORY/FROZEN), or ``None`` when no
    ``specs/`` class prefix matched — the caller decides the no-match verdict (MUTATING
    for in-repo, the release/protected/ungated tail for workspace-root paths).
    """
    # R-2 ordering fix (v0.1.46 AC-4): the per-artifact ``_archive/`` subdirs are FROZEN
    # and MUST be checked BEFORE the ADDITIVE prefixes, or ``specs/bugs/`` would swallow
    # ``specs/bugs/_archive/`` as ADDITIVE. Trailing-slash match keeps ``_archivefoo``
    # siblings ADDITIVE.
    for prefix in _ARCHIVE_SUBDIR_PREFIXES:
        if spec_rel.startswith(prefix):
            return PathClass.FROZEN
    for prefix in _SPECS_ADDITIVE_PREFIXES:
        if spec_rel.startswith(prefix):
            return PathClass.ADDITIVE
    if spec_rel.startswith(_MEMORY_PREFIX):
        return PathClass.MEMORY
    if spec_rel.startswith(_FROZEN_PREFIX):
        return PathClass.FROZEN
    return None


def _context_relative(p: str) -> str | None:
    """Return the remainder of ``p`` after a ``repos/<slug>/`` prefix, else ``None``.

    ``repos/`` alone or ``repos/<slug>`` with no trailing remainder yields ``""`` (still
    in-repo, so the caller classifies it MUTATING). A non-``repos/`` path yields ``None``.
    """
    if not p.startswith("repos/"):
        return None
    rest = p[len("repos/") :]
    slash = rest.find("/")
    if slash == -1:
        return ""  # 'repos/<slug>' with no remainder — in-repo, no class match
    return rest[slash + 1 :]


def classify_path(rel_path: str) -> PathClass:
    """Classify a workspace-relative path. Ordered; first match wins (FR-P1-05).

    WS-R1 re-root (FR-R1-01..05): a path under ``repos/<slug>/`` is classified by its
    **context-relative** remainder using the same ordered ``specs/`` class rules that
    govern workspace-root paths. An in-repo remainder matching no class is MUTATING
    (FR-R1-04) — it NEVER falls through to UNGATED. Workspace-root paths keep their
    pre-change behavior exactly (FR-R1-05): root ``.dadaia/`` ADDITIVE prefixes, the
    fail-closed PROTECTED class, and the UNGATED fall-through are all preserved.
    """
    p = rel_path.lstrip("/")

    ctx_rel = _context_relative(p)
    if ctx_rel is not None:
        # In-repo: re-root the taxonomy at the context. Unmatched ⇒ MUTATING (never UNGATED).
        return _classify_specs_relative(ctx_rel) or PathClass.MUTATING

    # Workspace-root path: specs class set + .dadaia/ additive + PROTECTED + UNGATED tail.
    specs_class = _classify_specs_relative(p)
    if specs_class is not None:
        return specs_class
    for prefix in _DADAIA_ADDITIVE_PREFIXES:
        if p.startswith(prefix):
            return PathClass.ADDITIVE
    if p.startswith("specs/releases/"):
        return PathClass.MUTATING
    if p.startswith(_PROTECTED_PREFIX):
        return PathClass.PROTECTED
    return PathClass.UNGATED


def evaluate(
    workspace: Path,
    rel_path: str,
    *,
    ctx: str,
    phase: str,
    session_id: str,
    release: str,
    mode: str,
    clock: Callable[[], datetime] = _utcnow,
    pid_probe: lease.PidProbe | None = None,
    holder_pid: int | None = None,
    veto_release: str | None = lease._UNSET_RELEASE,
) -> tuple[Decision, str]:
    """Return the gate decision for one write target — the fail-safe contract.

    Guarantees (AC-04): the return is always one of {ALLOW, BLOCK-with-actionable-
    message}; never an unhandled exception.

    MUTATING paths are BLOCKed on a live foreign lease (yield-iff-live-foreign,
    FR-P1-15): the block message is always actionable (never "bind --mode write",
    never "relaunch"). A relaunched session with a matching ``.ptr`` is recognised
    as the incumbent and RENEWs (never blocks). The flow only stops on a genuinely
    concurrent foreign live session — and even then, additive writes are unblocked.

    ``mode`` (WS-R4 FR-R4-03) selects the MUTATING sub-policy. A READ-resolved mode
    (``READ``/``BOUND_READ``, case-insensitive) is **non-acquiring**: a MUTATING write is
    BLOCKed with the documented-path message BEFORE any lease call, so a read session never
    writes a lease record. Every other mode (missing, IMPLEMENTATION, BOUND_IMPLEMENTATION,
    BOUND_REVIEW) is lease-taking — only explicit READ blocks MUTATING (Decision D-3).
    ADDITIVE/UNGATED ignore mode entirely; PROTECTED stays fail-closed regardless of mode.

    ``pid_probe`` (WS-R2 FR-R2-03) is threaded straight into :func:`lease.acquire` so a
    TTL-expired-but-still-running foreign holder is BLOCKed (not taken over). It is
    injected by the hook layer (``hooks/sdd_gate.py`` sources the container's
    ``OsProcessProbe``); ``None`` ⇒ TTL-only fallback. This module imports no adapter.

    ``holder_pid`` (WS-R2 FR-R2-03, NF-1 fix) is the pid stamped into the lease record so a
    *foreign* probe can later confirm this holder is alive. It MUST be a **long-lived**
    process id, not the ephemeral gate subprocess's own: the hook layer passes
    ``os.getppid()`` (the harness process that spawned the hook) — the hook child dies
    milliseconds after acquire, so recording its pid would make the no-steal veto probe a
    dead pid and inert. ``None`` ⇒ :func:`lease.acquire` defaults to ``os.getpid()`` (correct
    for a long-lived direct-API caller).
    """
    cls = classify_path(rel_path)

    # PROTECTED is the SOLE fail-CLOSED class (SEC-01). It is evaluated FIRST — before any
    # fail-open branch — so an agent write to .dadaia/sessions/ is blocked unconditionally,
    # protecting the lease-identity .ptr from forgery (confused-deputy / CWE-284).
    if cls == PathClass.PROTECTED:
        return Decision.BLOCK, _PROTECTED_MESSAGE

    if cls in (PathClass.ADDITIVE, PathClass.UNGATED):
        return Decision.ALLOW, ""

    if cls == PathClass.FROZEN:
        return Decision.BLOCK, f"[RULE B] '{rel_path}' is a frozen archive path (read-only)."

    if cls == PathClass.MEMORY:
        if phase in _MEMORY_WRITE_PHASES:
            return Decision.ALLOW, ""
        return Decision.BLOCK, (
            f"[RULE A] memory writes are allowed only in DEFINITION or CLOSURE phase "
            f"(current phase={phase})."
        )

    # MUTATING + READ-resolved session (WS-R4 FR-R4-03 / D-3): non-acquiring BLOCK. This
    # is evaluated BEFORE lease.acquire so NO lease file is written or modified — a read
    # session can never take, renew, or steal a lease. Only explicit READ reaches here;
    # missing/IMPLEMENTATION/BOUND_REVIEW fall through to the lease-taking path below.
    if _is_read_mode(mode):
        return Decision.BLOCK, _READ_BLOCK_MESSAGE.format(rel_path=rel_path, ctx=ctx or "<ctx>")

    # MUTATING — the gate is the single acquisition point (O_EXCL CAS in lease).
    try:
        lease.acquire(
            workspace,
            ctx,
            session_id,
            release,
            mode,
            clock=clock,
            pid_probe=pid_probe,
            pid=holder_pid,
            # v0.1.50 FR1: the liveness-veto release, decoupled from the record
            # release — None when ACTIVE.md was UNREADABLE (I/O failure ⇒ the
            # pid-veto must hold); defaults to ``release`` (legacy coupling).
            active_release=veto_release,
        )
    except LockHeldError as exc:
        # Genuine live-foreign conflict — BLOCK with the informative yield message.
        return Decision.BLOCK, str(exc)
    except Exception:  # noqa: BLE001 — fail-safe contract (AC-04): never fail-dead
        # Any unexpected lease-subsystem error (OSError, corrupt record, ValueError,
        # …) must NOT freeze the flow. Fail OPEN (heal-and-allow), matching the shell
        # gate's fail-open exit path — the guarantee holds for direct API callers too.
        return Decision.ALLOW, ""
    return Decision.ALLOW, ""
