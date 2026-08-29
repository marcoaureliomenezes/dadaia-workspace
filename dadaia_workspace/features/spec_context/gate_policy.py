"""Path classifier and decision policy for the merged SDD PreToolUse gate.

Races between sessions are surfaced through advisory presence and never prevented.
The only mutating-mode denial is the caller's own explicit READ mode. Protected CLI
session records remain fail-closed against file-tool writes.

**The MEMORY path class covers dotfiles, by decision (v0.4.3 FR13, software-architect
ruling, handoff 2026-08-17T161500Z-software-architect-v0.4.3-fr13-fr14).**
``_MEMORY_PREFIX``'s bare-prefix match classifies EVERY path under ``specs/memory/`` —
dotfiles included — as MEMORY. No dotfile carve-out exists and none is added: a
carve-out would open an always-writable hole under the MEMORY prefix through which
memory content could mutate mid-implementation, the exact stale-layer pattern the gate
exists to prevent. Second, a SPEC may NOT assign a memory-class write to a
non-``DEFINITION``/``CLOSURE`` task: the gate reads no SDD artifacts by design and
gains no SPEC-override channel — ``[RULE A]`` (``evaluate``, below) keeps blocking
unconditionally by phase regardless of what any SPEC schedules; a SPEC that needs a
memory-class write outside a ``DEFINITION``/``CLOSURE`` window is an
architecture-fidelity defect caught at review, not something this gate accommodates.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.features.spec_context import presence

__all__ = ["Decision", "PathClass", "classify_path", "evaluate"]

#: Throttle window (seconds) for the advisory concurrency warning (v0.1.76 FR1). A
#: second write inside this window from the same session emits no repeat warning — the
#: throttle marker lives at ``.dadaia/tmp/presence-warn-<sid>-<ctx>`` (mtime-based).
_ADVISORY_THROTTLE_SECONDS = 300

#: Ordered ADDITIVE prefixes — always allowed.
#: Parallel audit sessions use collision-safe directories, named per the single home
#: ``core.workspace_layout.AUDIT_DIR_NAME_RE`` (v0.5.0 T-050-25A — this comment used to
#: repeat that shape in prose; one fact, one place now).
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
# Single authority in core (also consumed by the public doctor's foreign scan) —
# the local name is kept for the module's existing readers.
_DADAIA_ADDITIVE_PREFIXES: tuple[str, ...] = workspace_layout.DADAIA_ADDITIVE_PREFIXES
#: v0.4.3 FR13 (ratified): bare-prefix match — dotfiles included, by decision; no
#: carve-out; no SPEC override of the phase rule (see the module docstring above).
_MEMORY_PREFIX = "specs/memory/"
#: A path under ``repos/<slug>/`` whose context-relative remainder matches one of these
#: ``specs/`` class prefixes is classified by that class. Every other in-repo remainder —
#: production source AND unlisted ``specs/<other>`` files (e.g. ``specs/constitution.md``)
#: — is MUTATING (FR-R1-04): a ``ctx_rel`` matching no class NEVER falls through to UNGATED.
#: .dadaia/sessions/ holds protected, caller-owned bind records. Agents must not write
#: these via file tools; only the CLI/bootstrap may write them.
_PROTECTED_PREFIX = ".dadaia/sessions/"
#: SEC-01 block reason emitted by the Python hook ``dadaia_workspace.hooks.sdd_gate``,
#: which delegates here so PROTECTED has a single message source.
_PROTECTED_MESSAGE = (
    "[GATE] .dadaia/sessions/ is protected CLI-owned bind state. Agents must not write "
    "here via file tools; use dadaia context commands. Blocked to preserve caller session "
    "identity integrity (SEC-01 / CWE-284)."
)
#: Projected LAW files. ``DADAIA.md`` is the workspace system prompt and the sole
#: always-on rule file the library ships; the ``AGENTS.md``/``CLAUDE.md`` pair is its
#: scoped/bridge counterpart. In an INSTANTIATED workspace these are human-only: an agent
#: changes the law by editing ``dadaia_workspace/public/`` and re-projecting, never by
#: writing the projection. Matched as exact relative paths (workspace root, harness dirs,
#: and each ``repos/<slug>/`` root) so library sources and test fixtures — which live
#: deeper — are never caught.
_LAW_BASENAMES: frozenset[str] = workspace_layout.LAW_BASENAMES
_LAW_HARNESS_DIRS: frozenset[str] = workspace_layout.LAW_HARNESS_DIRS
_LAW_MESSAGE = (
    "[GATE] '{path}' is a projected law file (the workspace system prompt / scoped "
    "AGENTS.md). In an instantiated workspace only a human operator edits it by hand. "
    "To change the law, edit the source under dadaia_workspace/public/ and re-project: "
    "`dadaia public stage && dadaia public install --target all && dadaia public doctor`."
)

#: Phases in which product-engineer may write memory atoms (FR-P1-13).
_MEMORY_WRITE_PHASES: frozenset[str] = frozenset({"DEFINITION", "CLOSURE"})

#: READ-resolved mode tokens. READ is opt-in self-protection; all other modes permit
#: mutating writes and record advisory presence.
_READ_MODES: frozenset[str] = frozenset({"READ", "BOUND_READ"})

#: BLOCK message for a READ-resolved session attempting a MUTATING write. It names the
#: documented path to write rights (``bind --mode implementation``) WITHOUT any banned
#: auto-rebind nag: it states a fact about the session's bound mode and the one-time
#: operator action that grants write rights, never instructing a mid-flow relaunch.
_READ_BLOCK_MESSAGE = (
    "[RULE READ] '{rel_path}' is a MUTATING write, but this session is bound in read "
    "(observe) mode. "
    "Additive paths (specs/backlog, specs/bugs, specs/audits, .dadaia/reports, "
    ".dadaia/handoff, .dadaia/tmp) remain writable. To gain write rights, the operator "
    "binds implementation mode once: `dadaia context bind {ctx} --mode implementation`."
)

#: The default session id when no harness-native id resolves (``hooks/sdd_gate.py``'s
#: ``resolve_session_id(payload, default="anon-session")``). FR5: an anonymous identity
#: never creates a presence record — it degrades presence accuracy only, never the write
#: (v0.1.76, kills the anon-session dual-writer facet of the CRITICAL bug at the root).
_ANON_SESSION_ID = "anon-session"


def _is_read_mode(mode: str) -> bool:
    """True iff ``mode`` resolves to a non-acquiring READ binding (case-insensitive)."""
    return mode.strip().upper() in _READ_MODES


def _advisory_marker_name(session_id: str, ctx: str) -> str:
    """The advisory throttle marker's filename — validated by :func:`presence.throttled`/
    :func:`presence.stamp_throttle` themselves (release 0.5.1 K2: the ONE
    mtime-throttle-marker idiom, replacing this module's own copy)."""
    return f"presence-warn-{session_id}-{ctx}"


def _advisory_message(ctx: str, rel_path: str, others: list[presence.PresenceRecord]) -> str:
    """Build the one-line advisory naming every other live session (FR1).

    Names each other session's id, runtime, and last-seen timestamp; states plainly that
    the write was ALLOWED — this is a signal, never a block.
    """
    parts = [
        f"{rec.session_id!r} (runtime={rec.runtime}, last seen at {rec.last_seen_at or 'unknown'})"
        for rec in others
    ]
    names = "; ".join(parts)
    return (
        f"[PRESENCE] '{rel_path}' write ALLOWED in context {ctx!r}. Other live session(s) "
        f"present: {names}. Races between sessions are accepted and surfaced, never "
        "blocked — no action required."
    )


class PathClass(Enum):
    ADDITIVE = "ADDITIVE"
    MEMORY = "MEMORY"
    MUTATING = "MUTATING"
    PROTECTED = "PROTECTED"
    LAW = "LAW"
    UNGATED = "UNGATED"


class Decision(Enum):
    ALLOW = "allow"
    BLOCK = "block"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _classify_specs_relative(spec_rel: str) -> PathClass | None:
    """Apply the ordered ``specs/`` class taxonomy to a root- or context-relative path.

    Returns the matched ``PathClass`` (ADDITIVE/MEMORY), or ``None`` when no
    ``specs/`` class prefix matched — the caller decides the no-match verdict (MUTATING
    for in-repo, the release/protected/ungated tail for workspace-root paths).
    """
    for prefix in _SPECS_ADDITIVE_PREFIXES:
        if spec_rel.startswith(prefix):
            return PathClass.ADDITIVE
    if spec_rel.startswith(_MEMORY_PREFIX):
        return PathClass.MEMORY
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


def _is_law_path(rel_path: str) -> bool:
    """True when *rel_path* sits at a structurally fixed LAW origin (see ``_LAW_BASENAMES``).

    Static, ORIGIN-only floor (v0.4.5 FR1): the workspace root or a fixed harness dir
    (``_LAW_HARNESS_DIRS``). ``repos/<slug>/`` never matches either shape, so a repo's
    own AGENTS.md/CLAUDE.md is never LAW (closes sdd-gate-blocks-fresh-repo-root-agents-md
    + repo-agents-md-law-gate-contradicts-template) — never reads the manifest (CWE-284).
    """
    parts = rel_path.split("/")
    if len(parts) == 1:
        return parts[0] in _LAW_BASENAMES
    parent = "/".join(parts[:-1])
    return parent in _LAW_HARNESS_DIRS and parts[-1] in _LAW_BASENAMES


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
    if _is_law_path(p):
        return PathClass.LAW

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
    runtime: str = "unknown",
    pid: int | None = None,
) -> tuple[Decision, str]:
    """Return the gate decision for one write target — the fail-safe contract.

    Guarantees (AC-04): the return is always one of {ALLOW, BLOCK-with-actionable-
    message}; never an unhandled exception.

    NO-LOCKS DOCTRINE (v0.1.76): a MUTATING write is NEVER blocked on another session.
    Instead it upserts an advisory :mod:`presence` record for this ``(ctx, session_id)``
    and, when another live session's presence is visible on the same context, ALLOWS
    with a one-line advisory warning (throttled — see
    ``gate_policy._advisory_throttled``). Presence I/O never raises (FR2); this function
    remains fail-safe regardless of the presence subsystem's health.

    ``mode`` (WS-R4 FR-R4-03) selects the MUTATING sub-policy. A READ-resolved mode
    (``READ``/``BOUND_READ``, case-insensitive) is **non-acquiring**: a MUTATING write is
    BLOCKed with the documented-path message — this is the ONLY MUTATING block that
    survives the doctrine, and it is strictly self-scoped (Decision D-3 / v0.1.76 FR4):
    it fires only when THIS session's own mode resolved READ, never a foreign session's.
    Every other mode (missing, IMPLEMENTATION, BOUND_IMPLEMENTATION, BOUND_REVIEW) is
    presence-upserting. ADDITIVE/UNGATED ignore mode entirely; PROTECTED stays
    fail-closed regardless of mode.

    ``runtime``/``pid`` (v0.1.76 FR2) are recorded into the presence record so the
    advisory and the panel can name a session's harness and process. An anonymous
    session id (``anon-session`` — no harness-native id resolved) never creates a
    presence record (FR5): its write is still allowed, but there is nothing to be
    advisory about.
    """
    cls = classify_path(rel_path)

    # PROTECTED is the sole fail-closed path and is evaluated before fail-open branches.
    if cls == PathClass.LAW:
        return Decision.BLOCK, _LAW_MESSAGE.format(path=rel_path)
    if cls == PathClass.PROTECTED:
        return Decision.BLOCK, _PROTECTED_MESSAGE

    if cls in (PathClass.ADDITIVE, PathClass.UNGATED):
        return Decision.ALLOW, ""

    if cls == PathClass.MEMORY:
        if phase in _MEMORY_WRITE_PHASES:
            return Decision.ALLOW, ""
        return Decision.BLOCK, (
            f"[RULE A] memory writes are allowed only in DEFINITION or CLOSURE phase "
            f"(current phase={phase})."
        )

    # MUTATING + READ-resolved session: opt-in self-protection only. It can
    # NEVER fire because of a foreign session's mode; mode resolution itself is
    # strictly self-scoped (see hooks/sdd_gate._resolve_mode). No presence record is
    # written on this branch — a read session creates no advisory-relevant presence.
    if _is_read_mode(mode):
        return Decision.BLOCK, _READ_BLOCK_MESSAGE.format(rel_path=rel_path, ctx=ctx or "<ctx>")

    # MUTATING mode: advisory presence, never a peer-session block.
    # anon-session (no harness-native id resolved, FR5) creates no presence record — the
    # write is still allowed, there is simply nothing to be advisory about. The whole
    # block is wrapped fail-safe (AC-04 defense-in-depth): ``presence`` already swallows
    # its own errors internally, but a MUTATING write must NEVER be able to raise out of
    # this function regardless of what future presence code does.
    try:
        if session_id and session_id != _ANON_SESSION_ID and ctx:
            presence.upsert(workspace, ctx, session_id, runtime=runtime, pid=pid or 0)
            others = presence.others_alive(workspace, ctx, session_id)
            marker = _advisory_marker_name(session_id, ctx)
            now = time.time()
            if others and not presence.throttled(
                workspace, marker, window_seconds=_ADVISORY_THROTTLE_SECONDS, now=now
            ):
                presence.stamp_throttle(workspace, marker)
                message = _advisory_message(ctx, rel_path, others)
                return Decision.ALLOW, message
    except Exception:  # noqa: BLE001 — fail-safe contract (AC-04): never fail-dead.
        return Decision.ALLOW, ""
    return Decision.ALLOW, ""
