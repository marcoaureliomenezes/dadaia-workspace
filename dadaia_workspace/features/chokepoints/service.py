"""Pure decision logic for the W1 chokepoint git-hook gates (v0.1.14).

This module is business logic: it imports ``core`` (the ``Ancestry`` port and the lease
staleness predicate) and reads the lease/handoff files through plain ``pathlib`` reads, but
NEVER imports ``infrastructure`` and NEVER spawns a subprocess or calls ``os.kill``. The CLI
(``cli/commands/ci.py``) wires the container's :class:`ProcessAncestry` adapter and the pid
probe; the unit tests inject synthetic fakes.

Two gates, one shared shape (:class:`Decision`):

* :func:`pre_commit_decision` — FR-W1-01 / DP-4 holder-identity probe chain.
* :func:`push_gate_decision` — FR-W1-02 / DP-5 security-verdict-per-pushed-sha check.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.kernel_tunables import LEASE_TTL_SECONDS
from dadaia_workspace.core.lock_liveness import is_stale
from dadaia_workspace.core.protocols.process_ancestry import Ancestry

__all__ = [
    "Decision",
    "PushRef",
    "context_slug_for_path",
    "iter_security_approvals",
    "pre_commit_decision",
    "push_gate_decision",
]

#: The ``"verdict"`` value a security-reviewer handoff must carry to authorize a push.
_APPROVED = "APPROVED"

#: The handoff ``"agent"`` whose verdict the push gate honors.
_SECURITY_REVIEWER = "security-reviewer"

#: A zero sha in a pre-push stdin ref line — a branch deletion, never review-gated.
_ZERO_SHA = "0" * 40


@dataclass(frozen=True)
class Decision:
    """Outcome of a chokepoint gate.

    ``allowed`` is the only thing the git hook keys its exit code on. ``warn`` carries an
    advisory line that is logged/printed but never blocks (the DP-4 degradation path).
    ``message`` is the human-facing block/allow explanation.
    """

    allowed: bool
    message: str = ""
    warn: str | None = None


@dataclass(frozen=True)
class PushRef:
    """One parsed pre-push stdin ref line.

    git feeds the pre-push hook lines of ``<local-ref> <local-sha> <remote-ref>
    <remote-sha>`` on stdin. The push gate keys ONLY on ``local_sha`` (never
    ``git rev-parse HEAD``): a zero ``local_sha`` is a branch deletion.
    """

    local_ref: str
    local_sha: str
    remote_ref: str
    remote_sha: str

    @property
    def is_deletion(self) -> bool:
        """True when this ref is being deleted (zero local sha) — passes with no verdict."""
        return self.local_sha == _ZERO_SHA or not self.local_sha

    @property
    def is_tag(self) -> bool:
        """True when this ref is a tag push — passes with no verdict (DP-5)."""
        return self.local_ref.startswith("refs/tags/")


def parse_push_refs(stdin_text: str) -> list[PushRef]:
    """Parse pre-push stdin into :class:`PushRef` rows. Malformed lines are skipped."""
    refs: list[PushRef] = []
    for raw in stdin_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 4:
            continue
        refs.append(PushRef(parts[0], parts[1], parts[2], parts[3]))
    return refs


# ---------------------------------------------------------------------------------------
# Context resolution — derive the slug from the repo path, NEVER first-ALIVE.
# ---------------------------------------------------------------------------------------
def context_slug_for_path(workspace: Path, repo_root: Path) -> str | None:
    """Return the context slug for a repo at ``repo_root`` under ``workspace``.

    A Spec Context repo lives at ``<workspace>/repos/<slug>``. The slug is that single path
    component — derived from the path, never from the first-ALIVE registry entry (the
    cross-context-contamination class the lease kernel forbids). Returns ``None`` when
    ``repo_root`` is not directly under ``<workspace>/repos/`` (e.g. the library repo run
    standalone, or the workspace root itself).
    """
    try:
        rel = repo_root.resolve().relative_to((workspace / "repos").resolve())
    except (ValueError, OSError):
        return None
    parts = rel.parts
    if len(parts) != 1:
        return None
    return parts[0]


def _lease_record(workspace: Path, ctx: str) -> dict[str, object] | None:
    """Read the lease record for ``ctx`` (pure read; ``None`` if absent/unparseable)."""
    path = workspace / ".dadaia" / "states" / "ctx_locks" / f"{ctx}.lock.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _age_seconds(heartbeat: object, *, now: datetime) -> int | None:
    """Whole-second age of ``heartbeat`` (for the block message); ``None`` if unparseable."""
    if not isinstance(heartbeat, str) or not heartbeat:
        return None
    try:
        hb = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
    except ValueError:
        return None
    if hb.tzinfo is None:
        hb = hb.replace(tzinfo=UTC)
    return int((now - hb).total_seconds())


def _block_message(ctx: str, holder_sid: str, age: int | None) -> str:
    """The actionable block message — never instructs a manual unblock ceremony.

    Per the forbidden-law canon (architecture "the message never instructs the operator to
    rebind, relaunch, or steal"), it states who holds the lease and that the lease frees
    itself; it must NOT contain "rebind", "relaunch", or "lock steal".
    """
    age_part = f" (last heartbeat ~{age}s ago)" if age is not None else ""
    return (
        f"[pre-commit] BLOCKED: context '{ctx}' is held by another session "
        f"'{holder_sid}'{age_part}.\n"
        f"This commit is not from the lease holder. The lease frees itself after "
        f"~{LEASE_TTL_SECONDS}s without a heartbeat, or when the holder finishes — "
        f"no manual action is needed; retry then."
    )


def pre_commit_decision(
    workspace: Path,
    ctx: str | None,
    *,
    caller_pid: int,
    env_sid: str | None,
    pid_probe: Callable[[int], bool] | None,
    ancestry: Callable[[int, int], Ancestry],
    now: datetime | None = None,
) -> Decision:
    """Decide whether a commit into ``ctx`` may proceed (FR-W1-01 / DP-4 probe chain).

    Probe order (first match wins):

    1. ``ctx`` is ``None`` (not a Spec Context repo) ⇒ **allow** — out of scope.
    2. No lease record, or a stale-dead record (``is_stale`` with the pid probe) ⇒
       **allow** — ADDITIVE work / a finished holder commits freely (zero-false-block).
    3. ``env_sid`` equals the holder sid ⇒ **allow** (the holder, eval-flow).
    4. The holder pid is an ancestor of ``caller_pid`` (``Ancestry.ANCESTOR``) ⇒ **allow**
       (the holder's own ``git commit`` is a Bash descendant of the harness pid).
    5. Ancestry ``UNKNOWN``/indeterminate ⇒ **allow + WARN** — zero-false-block dominates;
       the chokepoint degrades to advisory on that platform (documented honestly).
    6. Ancestry ``NOT_ANCESTOR`` but the holder pid is **demonstrably dead** ⇒ **allow + WARN**
       — the relaunch window (FR-W4 / ADR-G1). ``is_stale`` keeps a fresh-heartbeat record
       live, and ``renew_heartbeat`` never refreshes ``pid``, so a same-sid relaunch (new pid,
       same ``.ptr``) leaves a dead pid in the record while the heartbeat stays fresh. You
       cannot be a descendant of a dead process, so ``NOT_ANCESTOR`` against a dead holder is
       not a positive foreign-live identity; the kernel pid-veto canon protects only a *live*
       holder, so the gate degrades to advisory rather than falsely block.
    7. A **live** foreign holder with ``Ancestry.NOT_ANCESTOR`` ⇒ **block** with the actionable
       message.

    Consults the lease ONLY — never a handoff verdict (G6: a holder with zero security
    handoffs still commits freely; review-gating happens at push, not commit).
    """
    clock = now or datetime.now(tz=UTC)

    # (1) Out of scope: not a recognized Spec Context repo.
    if ctx is None:
        return Decision(allowed=True, message="[pre-commit] not a Spec Context repo; allow.")

    record = _lease_record(workspace, ctx)

    # (2) No lease, or stale-dead lease ⇒ allow. ``is_stale`` returns True for an absent or
    # corrupt record and for a TTL-expired record whose holder pid is dead/absent; a live
    # foreign holder (pid-veto) is NOT stale and falls through to the identity checks.
    # T-43-10 NOTE: ``active_release`` is intentionally left default (``None``, legacy
    # release-agnostic behavior) here. This is a pure decision function with injected seams and
    # no ACTIVE.md read; the archived-release deadlock is broken at its root by the MUTATING
    # acquire + ``lock steal`` paths (which reclaim the archived lease on the first write/steal),
    # after which this record's holder identity is the new session and the commit path self-heals.
    if is_stale(record, clock=lambda: clock, pid_probe=pid_probe):
        return Decision(allowed=True, message=f"[pre-commit] no live lease on '{ctx}'; allow.")

    assert record is not None  # is_stale(None) is True, so a non-stale record exists here.
    holder_sid = str(record.get("session_id", ""))
    holder_pid_raw = record.get("pid")
    holder_pid = holder_pid_raw if isinstance(holder_pid_raw, int) and holder_pid_raw > 0 else None
    age = _age_seconds(record.get("heartbeat"), now=clock)

    # (3) env-sid match ⇒ the holder itself (eval flow with DADAIA_SESSION_ID exported).
    if env_sid and holder_sid and env_sid == holder_sid:
        return Decision(allowed=True, message=f"[pre-commit] session holds '{ctx}'; allow.")

    # (4)/(5) ancestry probe — the harness-real allow path for the holder's own commits.
    if holder_pid is not None:
        try:
            verdict = ancestry(holder_pid, caller_pid)
        except Exception:  # noqa: BLE001 — a probe bug must degrade to advisory, never block.
            verdict = Ancestry.UNKNOWN
        if verdict is Ancestry.ANCESTOR:
            return Decision(
                allowed=True,
                message="[pre-commit] commit is from the lease holder's process tree; allow.",
            )
        if verdict is Ancestry.UNKNOWN:
            return Decision(
                allowed=True,
                message=f"[pre-commit] lease '{ctx}' held; ancestry indeterminate — allowing.",
                warn=(
                    f"[pre-commit] WARN: could not confirm this commit belongs to the holder "
                    f"of '{ctx}' (held by '{holder_sid}'); allowing (advisory degradation, "
                    f"DP-4 zero-false-block)."
                ),
            )
    else:
        # No holder pid recorded (legacy record): cannot probe ancestry ⇒ advisory allow.
        return Decision(
            allowed=True,
            message=f"[pre-commit] lease '{ctx}' held but holder pid unknown — allowing.",
            warn=(
                f"[pre-commit] WARN: lease '{ctx}' held by '{holder_sid}' has no recorded "
                f"pid; cannot verify ancestry — allowing (advisory degradation)."
            ),
        )

    # (6) Relaunch window (FR-W4 / ADR-G1): NOT_ANCESTOR against a DEAD holder pid is not a
    # positive foreign-live identity. ``is_stale`` kept this fresh-heartbeat record live, and
    # ``renew_heartbeat`` never refreshes ``pid``, so a same-sid relaunch (new pid, same .ptr)
    # leaves a dead pid in the record. Only a LIVE holder is protected by the pid-veto canon;
    # a dead holder ⇒ indeterminate identity ⇒ allow + WARN (advisory degradation), never block.
    if pid_probe is not None and holder_pid is not None:
        try:
            holder_alive = pid_probe(holder_pid)
        except Exception:  # noqa: BLE001 — a probe bug must degrade to advisory, never block.
            holder_alive = True  # cannot confirm dead ⇒ keep the block decision conservative.
        if not holder_alive:
            return Decision(
                allowed=True,
                message=(
                    f"[pre-commit] lease '{ctx}' held by '{holder_sid}' but its recorded "
                    f"holder pid {holder_pid} is dead — allowing (relaunch window)."
                ),
                warn=(
                    f"[pre-commit] WARN: lease '{ctx}' records a dead holder pid {holder_pid} "
                    f"(session '{holder_sid}') with a fresh heartbeat — the relaunched incumbent; "
                    f"allowing (advisory degradation, DP-4 zero-false-block)."
                ),
            )

    # (7) Live foreign holder, positive non-ancestor ⇒ block.
    return Decision(allowed=False, message=_block_message(ctx, holder_sid, age))


# ---------------------------------------------------------------------------------------
# Push gate — security-reviewer verdict per pushed sha (FR-W1-02 / DP-5).
# ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class _Approval:
    """A security-reviewer APPROVE covering one commit sha."""

    commit_sha: str
    source: str  # handoff file name, for the block listing.


def iter_security_approvals(handoff_root: Path) -> list[_Approval]:
    """All ``security-reviewer`` APPROVE handoffs under ``handoff_root`` (recursive).

    ``handoff_root`` is ``<workspace>/.dadaia/handoff`` (all contexts). A handoff qualifies
    when ``agent == "security-reviewer"``, ``verdict == "APPROVED"``, and
    ``metrics.commit_sha`` is a non-empty string — the single canonical field (no ``scope``
    fallback). Unreadable/malformed files are skipped (never crash the push hook).
    """
    approvals: list[_Approval] = []
    if not handoff_root.is_dir():
        return approvals
    for path in sorted(handoff_root.rglob("*.handoff.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("agent") != _SECURITY_REVIEWER:
            continue
        if data.get("verdict") != _APPROVED:
            continue
        metrics = data.get("metrics")
        if not isinstance(metrics, dict):
            continue
        sha = metrics.get("commit_sha")
        if isinstance(sha, str) and sha:
            approvals.append(_Approval(commit_sha=sha, source=path.name))
    return approvals


def push_gate_decision(
    handoff_root: Path,
    refs: list[PushRef],
) -> Decision:
    """Decide whether a push may proceed (FR-W1-02 / DP-5).

    For every ref being pushed that is NOT a deletion and NOT a tag, an APPROVED
    security-reviewer handoff whose ``metrics.commit_sha`` equals that ref's ``local_sha``
    must exist. Deletions (zero sha) and tag-only refs pass with no verdict. A stale
    approval (an APPROVE for a different/older sha) does not satisfy a ref. Commits are
    never review-blocked — this runs at push only.
    """
    approved_shas = {a.commit_sha for a in iter_security_approvals(handoff_root)}

    review_refs = [r for r in refs if not r.is_deletion and not r.is_tag]
    if not review_refs:
        return Decision(allowed=True, message="[pre-push] no review-gated refs; allow.")

    missing = [r for r in review_refs if r.local_sha not in approved_shas]
    if not missing:
        return Decision(
            allowed=True,
            message="[pre-push] every pushed commit carries a security-reviewer APPROVE; allow.",
        )

    found = (
        ", ".join(sorted(approved_shas))
        if approved_shas
        else "(no security-reviewer APPROVE found)"
    )
    wanted = ", ".join(f"{r.local_ref}@{r.local_sha[:12]}" for r in missing)
    return Decision(
        allowed=False,
        message=(
            "[pre-push] BLOCKED: no security-reviewer APPROVE handoff covers "
            f"{wanted}.\n"
            f"  APPROVE shas on disk: {found}\n"
            "  A security-reviewer must emit an APPROVED handoff with "
            "metrics.commit_sha == the pushed commit sha before this push can proceed."
        ),
    )
