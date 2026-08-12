"""Pure decision logic for the W1 chokepoint git-hook gates (v0.1.14; v0.1.76 FR3).

This module is business logic: it imports ``core`` and reads presence/handoff files, but
NEVER imports ``infrastructure`` and NEVER spawns a subprocess or calls ``os.kill``. The CLI
(``cli/commands/ci.py``) wires the container's :class:`ProcessAncestry` adapter and the pid
probe; the unit tests inject synthetic fakes.

Two gates, one shared shape (:class:`Decision`):

* :func:`pre_commit_decision` — NO-LOCKS WARN-only: ALWAYS returns ``allowed=True`` and
  reads only advisory presence records.
* :func:`push_gate_decision` — FR-W1-02 / DP-5 security-verdict-per-pushed-sha check
  (UNCHANGED by v0.1.76 — quality gates are not concurrency locks and stay).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.protocols.process_ancestry import Ancestry
from dadaia_workspace.features.spec_context import presence

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


# ── Branch policy (v0.6.0 FR4 / T-060-04) ───────────────────────────────────────
#
# The gitflow law (DADAIA.md §5, operator ruling 2026-08-12): exactly four branch
# patterns exist, and ``develop`` is the ONLY pushable branch. This tuple is the ONE
# pattern source — the pre-push hook and the CI pr-source-guard both encode the model,
# and any second regex copy is drift.
_PERMITTED_BRANCH_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"^main$"),
    re.compile(r"^develop$"),
    re.compile(r"^feature/v\d+\.\d+\.\d+$"),
    re.compile(r"^hotfix/v\d+\.\d+\.\d+$"),
)

_PUSHABLE_BRANCH = "develop"
_HEADS_PREFIX = "refs/heads/"


def branch_name_is_permitted(branch: str) -> bool:
    """True when *branch* matches one of the four permitted patterns.

    ``main`` | ``develop`` | ``feature/vM.m.p`` | ``hotfix/vM.m.p`` — the version part
    follows the release-id canon (leading ``v``, three numeric fields, no suffix:
    pre-release suffixes are release-id territory, never branch names).
    """
    return any(pattern.match(branch) for pattern in _PERMITTED_BRANCH_RES)


def _refuse_branch(branch: str, local_ref: str) -> Decision:
    """Actionable refusal for a non-``develop`` ref (A4.2: rule + permitted + fix)."""
    if branch == "main":
        return Decision(
            allowed=False,
            message=(
                "[pre-push] BLOCKED: 'main' is never pushed directly — it advances only "
                "via a PR from 'develop' (gitflow law, DADAIA.md §5).\n"
                "  Fix: merge your work into 'develop', push 'develop', then open the "
                "PR develop → main."
            ),
        )
    if branch_name_is_permitted(branch):
        kind = "feature" if branch.startswith("feature/") else "hotfix"
        return Decision(
            allowed=False,
            message=(
                f"[pre-push] BLOCKED: '{branch}' is a {kind} branch — {kind} branches "
                "are local-only and are never pushed (gitflow law, DADAIA.md §5). Only "
                "'develop' is pushable.\n"
                "  Fix: merge the branch into local 'develop', obtain the diff-based "
                "security APPROVE, then push 'develop'."
            ),
        )
    return Decision(
        allowed=False,
        message=(
            f"[pre-push] BLOCKED: ref '{local_ref}' is outside the four permitted branch "
            "patterns — main, develop, feature/vM.m.p, hotfix/vM.m.p (gitflow law, "
            "DADAIA.md §5).\n"
            "  Fix: rebuild the work on a permitted branch (git checkout -b "
            "feature/vM.m.p or hotfix/vM.m.p from develop), merge it into 'develop', "
            "and push 'develop'."
        ),
    )


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
    component — derived from the path, never from the first-ALIVE registry entry. Returns ``None`` when
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
    """The advisory WARN line for another live presence record.

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

    NO-LOCKS DOCTRINE: this ALWAYS returns ``allowed=True``. Advisory detection reads the
    same fail-soft presence records as the write gate. Retired lease files have no effect.
    Legacy probe parameters remain accepted so installed git-hook callers do not break.
    """
    clock = now or datetime.now(tz=UTC)

    # Out of scope: not a recognized Spec Context repo — nothing to detect either.
    if ctx is None:
        return Decision(allowed=True, message="[pre-commit] not a Spec Context repo; allow.")

    own_sid = env_sid or "pre-commit-anonymous"
    others = presence.others_alive(workspace, ctx, own_sid)
    if not others:
        return Decision(
            allowed=True,
            message=f"[pre-commit] no other live presence on '{ctx}'; allow.",
        )

    other = others[0]
    age = _age_seconds(other.last_seen_at, now=clock)
    return Decision(
        allowed=True,
        message="[pre-commit] commit allowed.",
        warn=_advisory_message(ctx, other.session_id, age),
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
    """Decide whether a push may proceed (FR-W1-02 / DP-5 / v0.6.0 FR4).

    Policy order, first refusal wins:

    1. **Branch policy** — every non-deletion, non-tag ref must be
       ``refs/heads/develop``: ``main`` advances via PR only; feature/hotfix branches
       are local-only; names outside the four permitted patterns are refused outright.
    2. **Diff-based security verdict** — the pushed ``develop`` tip must carry an
       APPROVED security-reviewer handoff whose ``metrics.commit_sha`` equals it. The
       tip sha anchors the reviewed range ``origin/develop..develop``; a stale approval
       (different/older tip) does not cover the delta.

    Deletions (zero sha) and tag pushes pass with no verdict (DP-5 carve-out —
    publishing depends on tag pushes). Commits are never review-blocked — push only.
    """
    review_refs = [r for r in refs if not r.is_deletion and not r.is_tag]
    if not review_refs:
        return Decision(allowed=True, message="[pre-push] no review-gated refs; allow.")

    for ref in review_refs:
        if not ref.local_ref.startswith(_HEADS_PREFIX):
            return _refuse_branch(ref.local_ref, ref.local_ref)
        branch = ref.local_ref[len(_HEADS_PREFIX) :]
        if branch != _PUSHABLE_BRANCH:
            return _refuse_branch(branch, ref.local_ref)

    approved_shas = {a.commit_sha for a in iter_security_approvals(handoff_root)}
    missing = [r for r in review_refs if r.local_sha not in approved_shas]
    if not missing:
        return Decision(
            allowed=True,
            message=(
                "[pre-push] develop push carries a security-reviewer APPROVE covering "
                "its delta; allow."
            ),
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
            "[pre-push] BLOCKED: no security-reviewer APPROVE covers the "
            f"origin/develop..develop delta being pushed ({wanted}).\n"
            f"  APPROVE shas on disk: {found}\n"
            "  Fix: dispatch a security-reviewer DIFF review of origin/develop..develop "
            "and emit an APPROVED handoff with metrics.commit_sha == the pushed develop "
            "tip sha, then push again."
        ),
    )
