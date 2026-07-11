"""Pure decision logic for the W1 chokepoint git-hook gates (v0.1.14; v0.1.76 FR3).

This module is business logic: it imports ``core`` (the ``Ancestry`` port and the lease
staleness predicate) and reads the lease/handoff files through plain ``pathlib`` reads, but
NEVER imports ``infrastructure`` and NEVER spawns a subprocess or calls ``os.kill``. The CLI
(``cli/commands/ci.py``) wires the container's :class:`ProcessAncestry` adapter and the pid
probe; the unit tests inject synthetic fakes.

Two gates, one shared shape (:class:`Decision`):

* :func:`pre_commit_decision` — v0.1.76 FR3 (NO-LOCKS DOCTRINE, WARN-only): ALWAYS returns
  ``allowed=True``. It keeps the live-lease DETECTION (a residual/legacy lease record naming
  another session may still exist — e.g. from ``adopt_if_own_lineage`` — or a foreign presence
  record) so it can print exactly ONE advisory line naming the other session; it never blocks
  a commit for that reason. The old DP-4 BLOCK verdict (rung 7) is deleted along with its
  probe-chain degradation ladder; the identity signal survives purely as an advisory.
* :func:`push_gate_decision` — FR-W1-02 / DP-5 security-verdict-per-pushed-sha check
  (UNCHANGED by v0.1.76 — quality gates are not concurrency locks and stay).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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


def _advisory_message(ctx: str, holder_sid: str, age: int | None) -> str:
    """The advisory WARN line for a live foreign-looking lease record (v0.1.76 FR3).

    Per the forbidden-law canon (architecture "the message never instructs the operator to
    rebind, relaunch, or steal"), it states who else appears active and that the commit was
    allowed regardless; it must NOT contain "rebind", "relaunch", or "lock steal".
    """
    age_part = f" (last heartbeat ~{age}s ago)" if age is not None else ""
    return (
        f"[pre-commit] WARN: context '{ctx}' shows another session '{holder_sid}'{age_part} — "
        "commit allowed (NO-LOCKS DOCTRINE: races between sessions are accepted and surfaced, "
        "never blocked; no action required)."
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
    """Decide whether a commit into ``ctx`` may proceed (v0.1.76 FR3, WARN-only).

    NO-LOCKS DOCTRINE: this ALWAYS returns ``allowed=True`` — a commit is never blocked
    because of another session. The former DP-4 probe chain (env-sid / ancestry / pid-veto)
    is kept ONLY as advisory DETECTION: when a lease record (legacy/residual — nothing
    production writes fresh ones anymore, but ``adopt_if_own_lineage`` and pre-doctrine
    installs may still leave one) names a session that is neither ``env_sid`` nor in the
    caller's process ancestry, and whose pid is demonstrably alive, one advisory WARN line
    is emitted naming that other session; the commit still proceeds unconditionally.

    Consults the lease ONLY — never a handoff verdict (G6: a holder with zero security
    handoffs still commits freely; review-gating happens at push, not commit).
    """
    clock = now or datetime.now(tz=UTC)

    # Out of scope: not a recognized Spec Context repo — nothing to detect either.
    if ctx is None:
        return Decision(allowed=True, message="[pre-commit] not a Spec Context repo; allow.")

    record = _lease_record(workspace, ctx)

    # No lease, or stale-dead lease ⇒ allow, no advisory. ``is_stale`` returns True for an
    # absent/corrupt record and for a TTL-expired record whose holder pid is dead/absent.
    if is_stale(record, clock=lambda: clock, pid_probe=pid_probe):
        return Decision(allowed=True, message=f"[pre-commit] no live lease on '{ctx}'; allow.")

    assert record is not None  # is_stale(None) is True, so a non-stale record exists here.
    holder_sid = str(record.get("session_id", ""))
    holder_pid_raw = record.get("pid")
    holder_pid = holder_pid_raw if isinstance(holder_pid_raw, int) and holder_pid_raw > 0 else None
    age = _age_seconds(record.get("heartbeat"), now=clock)

    # env-sid match ⇒ this commit IS the recorded session — no advisory needed.
    if env_sid and holder_sid and env_sid == holder_sid:
        return Decision(allowed=True, message=f"[pre-commit] session holds '{ctx}'; allow.")

    # Ancestry probe: the holder's own commit (same process tree) needs no advisory either.
    if holder_pid is not None:
        try:
            verdict = ancestry(holder_pid, caller_pid)
        except Exception:  # noqa: BLE001 — a probe bug must never block; treat as indeterminate.
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
                    f"of '{ctx}' (held by '{holder_sid}'); allowing (advisory, NO-LOCKS "
                    "DOCTRINE)."
                ),
            )
    else:
        # No holder pid recorded (legacy record): cannot verify identity ⇒ advisory allow.
        return Decision(
            allowed=True,
            message=f"[pre-commit] lease '{ctx}' held but holder pid unknown — allowing.",
            warn=(
                f"[pre-commit] WARN: lease '{ctx}' held by '{holder_sid}' has no recorded "
                f"pid; cannot verify identity — allowing (advisory, NO-LOCKS DOCTRINE)."
            ),
        )

    # holder pid is demonstrably dead ⇒ no genuinely-live other session to advise about.
    if pid_probe is not None and holder_pid is not None:
        try:
            holder_alive = pid_probe(holder_pid)
        except Exception:  # noqa: BLE001 — a probe bug must never block; assume indeterminate.
            holder_alive = True
        if not holder_alive:
            return Decision(
                allowed=True,
                message=(
                    f"[pre-commit] lease '{ctx}' held by '{holder_sid}' but its recorded "
                    f"holder pid {holder_pid} is dead — allowing."
                ),
                warn=(
                    f"[pre-commit] WARN: lease '{ctx}' records a dead holder pid {holder_pid} "
                    f"(session '{holder_sid}') with a fresh heartbeat — the relaunched "
                    "incumbent; allowing (advisory, NO-LOCKS DOCTRINE)."
                ),
            )

    # A demonstrably OTHER, demonstrably LIVE session appears active on this context: commit
    # still ALLOWS (v0.1.76 FR3) — this is the sole remaining advisory line, naming who else
    # is active, never a block.
    return Decision(
        allowed=True,
        message="[pre-commit] commit allowed.",
        warn=_advisory_message(ctx, holder_sid, age),
    )


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
