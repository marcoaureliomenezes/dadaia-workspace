"""Pure decision logic for the W1 chokepoint git-hook gates (v0.1.14; v0.1.76 FR3).

This module is business logic: it imports ``core`` and reads presence/handoff files, but
NEVER imports ``infrastructure`` and NEVER spawns a subprocess or calls ``os.kill``. The CLI
(``cli/commands/ci.py``) wires the container's :class:`ProcessAncestry` adapter and the pid
probe; the unit tests inject synthetic fakes.

Two gates, one shared shape (:class:`Decision`):

* :func:`pre_commit_decision` — NO-LOCKS WARN-only: ALWAYS returns ``allowed=True`` and
  reads only advisory presence records.
* :func:`push_gate_decision` — FR-W1-02 / DP-5 security-verdict-per-pushed-sha check
  (UNCHANGED by v0.1.76 — quality gates are not concurrency locks and stay), PLUS the
  v0.9.0 FR1/FR2 range-scoped denylist scan: every non-deletion ref (tags included) is
  scanned for the objects the push would newly publish, via an injected
  :class:`~dadaia_workspace.core.protocols.git_object_reader.GitObjectReader` — never a
  direct subprocess call from this module (FR7/A7.1).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.protocols.git_object_reader import (
    ZERO_SHA,
    GitObjectReader,
    GitObjectReadError,
    ScannedObject,
)
from dadaia_workspace.core.protocols.process_ancestry import Ancestry
from dadaia_workspace.features.chokepoints.denylist_scan import (
    BaselinePatternLike,
    Hit,
    scan_objects,
)
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
        return self.local_sha == ZERO_SHA or not self.local_sha

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
    # PATCH >= 1: patch 0 is feature-release territory (the retired CI
    # hotfix-branch-name job's knowledge, relocated per SPEC FR5.2).
    re.compile(r"^hotfix/v\d+\.\d+\.[1-9]\d*$"),
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


def parse_push_stdin(stdin_text: str) -> tuple[list[PushRef], int]:
    """Parse pre-push stdin into :class:`PushRef` rows plus a malformed-line count.

    A non-empty line that does not split into exactly four fields is counted, not
    silently dropped — the gate FAILS CLOSED on any malformed line (T-060-07 finding 1:
    a policy gate that skips what it cannot parse is a policy gate that can be
    disabled without a trace; ``git push --no-verify`` is the sanctioned bypass).
    """
    refs: list[PushRef] = []
    malformed = 0
    for raw in stdin_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 4:
            malformed += 1
            continue
        refs.append(PushRef(parts[0], parts[1], parts[2], parts[3]))
    return refs, malformed


def parse_push_refs(stdin_text: str) -> list[PushRef]:
    """Back-compat wrapper over :func:`parse_push_stdin` (refs only)."""
    return parse_push_stdin(stdin_text)[0]


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


#: The law this scan enforces (SPEC v0.9.0 FR5) — quoted verbatim in every refusal.
_DENYLIST_LAW = "DADAIA.md §7 — private names never enter public/pushed material"

#: FR5/A5.4 — at most this many offending objects are listed before a remainder count.
_MAX_LISTED_HITS = 10


def _annotate_skip(decision: Decision, skipped_binary_count: int) -> Decision:
    """Attach the FR6 row-3 skip count to *decision* — reported either way (allow/refuse)."""
    if skipped_binary_count <= 0:
        return decision
    note = (
        f"[pre-push] {skipped_binary_count} binary blob(s) skipped by the denylist "
        "scan (not text-decodable)."
    )
    warn = f"{decision.warn}\n{note}" if decision.warn else note
    return Decision(allowed=decision.allowed, message=decision.message, warn=warn)


def _compose_denylist_refusal(hits: list[tuple[PushRef, Hit]]) -> str:
    """FR5: ref, path:line, short blob sha, masked term + source layer, the law, the
    edit + rewrite-before-push remediation, ``--no-verify``, capped at 10 hits."""
    lines = [
        f"[pre-push] BLOCKED: the pushed range publishes {len(hits)} object(s) carrying "
        f"a denylisted term ({_DENYLIST_LAW})."
    ]
    shown = hits[:_MAX_LISTED_HITS]
    remainder = len(hits) - len(shown)
    for ref, hit in shown:
        lines.append(
            f"  {ref.local_ref} -> {ref.remote_ref}: {hit.path}:{hit.line} "
            f"(blob {hit.sha[:12]}) — masked term '{hit.masked_term}' ({hit.source_layer})"
        )
    if remainder > 0:
        lines.append(f"  ... and {remainder} more offending object(s).")
    lines.append(
        "  Fix: edit the file(s) to remove the term, then rewrite the offending "
        "commit(s) (--amend / interactive rebase / cherry-pick) so no pushed object "
        "carries it, and push again — the range scope means already-published history "
        "never needs a rewrite."
    )
    lines.append(
        "  If this push is a genuine emergency, git's sanctioned, traceable bypass is "
        "`git push --no-verify` (discouraged; leaves a reflog trace)."
    )
    return "\n".join(lines)


def _dedup_new_objects(
    object_source: GitObjectReader,
    repo: Path,
    ref: PushRef,
    seen_shas: set[str],
) -> Iterator[ScannedObject]:
    """Yield each object new to *ref*'s range that has not already been seen earlier in
    this scan, recording it into *seen_shas* as it is yielded (A1.4 cross-ref dedupe).

    Streamed straight into :func:`scan_objects` by the caller rather than materialized
    into a list first (code-reviewer MEDIUM performance finding: building the full
    ``fresh`` list before scanning measured ~129 MB resident over a large fallback
    range) — ``scan_objects`` already consumes its ``objects`` argument lazily, one
    object at a time, so nothing downstream needs the list shape.
    """
    for obj in object_source.new_objects(repo, ref.local_sha, ref.remote_sha):
        if obj.sha in seen_shas:
            continue
        seen_shas.add(obj.sha)
        yield obj


def _run_denylist_scan(
    scan_refs: list[PushRef],
    object_source: GitObjectReader,
    repo: Path,
    terms: Iterable[tuple[str, str]],
    patterns: Iterable[BaselinePatternLike],
    slugs: Iterable[str],
) -> tuple[Decision | None, int]:
    """Run the FR1/FR2 scan over *scan_refs* — every non-deletion ref, tags included.

    Returns ``(refusal_or_None, skipped_binary_count)``. A git object-read failure
    refuses immediately, naming the failure (FR6 row 2) — never a silent empty scan.
    """
    if not scan_refs:
        return None, 0
    term_list = list(terms)
    pattern_list = list(patterns)
    slug_list = list(slugs)
    seen_shas: set[str] = set()
    per_ref_hits: list[tuple[PushRef, Hit]] = []
    skipped_total = 0
    try:
        for ref in scan_refs:
            fresh = _dedup_new_objects(object_source, repo, ref, seen_shas)
            outcome = scan_objects(fresh, term_list, pattern_list, slug_list)
            skipped_total += outcome.skipped_binary_count
            per_ref_hits.extend((ref, hit) for hit in outcome.hits)
    except GitObjectReadError as exc:
        return (
            Decision(
                allowed=False,
                message=(
                    f"[pre-push] BLOCKED: reading the pushed-range git objects failed "
                    f"({exc}) — a policy gate never skips what it cannot evaluate (fail "
                    "closed).\n"
                    "  If this push is a genuine emergency, git's sanctioned, traceable "
                    "bypass is `git push --no-verify` (discouraged; leaves a reflog "
                    "trace)."
                ),
            ),
            0,
        )
    if not per_ref_hits:
        return None, skipped_total
    return Decision(allowed=False, message=_compose_denylist_refusal(per_ref_hits)), skipped_total


def push_gate_decision(
    handoff_root: Path,
    refs: list[PushRef],
    *,
    object_source: GitObjectReader,
    repo: Path,
    malformed_lines: int = 0,
    denylist_terms: Iterable[tuple[str, str]] = (),
    baseline_patterns: Iterable[BaselinePatternLike] = (),
    foreign_slugs: Iterable[str] = (),
) -> Decision:
    """Decide whether a push may proceed (FR-W1-02 / DP-5 / v0.6.0 FR4 / v0.9.0 FR1-FR6).

    Policy order, first refusal wins:

    1. **Branch policy** — every non-deletion, non-tag ref must be
       ``refs/heads/develop``: ``main`` advances via PR only; feature/hotfix branches
       are local-only; names outside the four permitted patterns are refused outright.
    2. **Range-scoped denylist scan** (v0.9.0 FR1/FR2) — every non-deletion ref, tags
       included, is scanned via *object_source* for new objects carrying a denylisted
       term. Runs AFTER branch policy (free and pure) and BEFORE the security verdict —
       a leaking push is refused for the leak, not for a missing handoff.
    3. **Diff-based security verdict** — the pushed ``develop`` tip must carry an
       APPROVED security-reviewer handoff whose ``metrics.commit_sha`` equals it. The
       tip sha anchors the reviewed range ``origin/develop..develop``; a stale approval
       (different/older tip) does not cover the delta.

    Deletions (zero sha) are never scanned and pass with no verdict. Tag pushes ARE
    scanned but keep their DP-5 verdict carve-out (publishing depends on tag pushes).
    Commits are never review-blocked — push only. A malformed stdin line fails CLOSED
    (finding 1) and the REMOTE side of every review ref must also be
    ``refs/heads/develop`` (finding 2: ``push develop:main``).

    *object_source* and *repo* are REQUIRED — FR7/A7.2: the decision function always
    takes the object source as a parameter; an unwired production call site is a CLI
    defect, never a bypass (FR6 row 4), so there is no default that would silently skip
    the scan.
    """
    if malformed_lines > 0:
        return Decision(
            allowed=False,
            message=(
                f"[pre-push] BLOCKED: {malformed_lines} unparseable pre-push stdin "
                "line(s) — a policy gate never skips what it cannot parse (fail "
                "closed).\n"
                "  If this push is a genuine emergency, git's sanctioned, traceable "
                "bypass is `git push --no-verify` (discouraged; leaves a reflog trace)."
            ),
        )

    review_refs = [r for r in refs if not r.is_deletion and not r.is_tag]

    for ref in review_refs:
        if not ref.local_ref.startswith(_HEADS_PREFIX):
            return Decision(
                allowed=False,
                message=(
                    f"[pre-push] BLOCKED: local ref '{ref.local_ref}' is not a branch "
                    "head — only 'refs/heads/develop' may be pushed (gitflow law, "
                    "DADAIA.md §5).\n"
                    "  Fix: check out 'develop' (git checkout develop) and push it "
                    "directly instead of pushing a detached or symbolic ref."
                ),
            )
        branch = ref.local_ref[len(_HEADS_PREFIX) :]
        if branch != _PUSHABLE_BRANCH:
            return _refuse_branch(branch, ref.local_ref)
        if ref.remote_ref != f"{_HEADS_PREFIX}{_PUSHABLE_BRANCH}":
            return Decision(
                allowed=False,
                message=(
                    f"[pre-push] BLOCKED: refspec aims local 'develop' at remote "
                    f"'{ref.remote_ref}' — only refs/heads/develop → refs/heads/develop "
                    "is pushable (gitflow law, DADAIA.md §5; 'main' advances via PR "
                    "from develop only).\n"
                    "  Fix: push develop to develop (git push origin develop) and open "
                    "the PR develop → main for anything aimed at main."
                ),
            )

    # v0.9.0 FR1/FR2: scan every non-deletion ref (tags included) — computed
    # independently of `review_refs`, which excludes tags. Runs after branch policy
    # (free and pure, already checked above) and before the security verdict below.
    scan_refs = [r for r in refs if not r.is_deletion]
    scan_refusal, skipped_binary_count = _run_denylist_scan(
        scan_refs, object_source, repo, denylist_terms, baseline_patterns, foreign_slugs
    )
    if scan_refusal is not None:
        return _annotate_skip(scan_refusal, skipped_binary_count)

    if not review_refs:
        return _annotate_skip(
            Decision(allowed=True, message="[pre-push] no review-gated refs; allow."),
            skipped_binary_count,
        )

    approved_shas = {a.commit_sha for a in iter_security_approvals(handoff_root)}
    missing = [r for r in review_refs if r.local_sha not in approved_shas]
    if not missing:
        return _annotate_skip(
            Decision(
                allowed=True,
                message=(
                    "[pre-push] develop push carries a security-reviewer APPROVE "
                    "covering its delta; allow."
                ),
            ),
            skipped_binary_count,
        )

    found = (
        ", ".join(sorted(approved_shas))
        if approved_shas
        else "(no security-reviewer APPROVE found)"
    )
    wanted = ", ".join(f"{r.local_ref}@{r.local_sha[:12]}" for r in missing)
    return _annotate_skip(
        Decision(
            allowed=False,
            message=(
                "[pre-push] BLOCKED: no security-reviewer APPROVE covers the "
                f"origin/develop..develop delta being pushed ({wanted}).\n"
                f"  APPROVE shas on disk: {found}\n"
                "  Fix: dispatch a security-reviewer DIFF review of "
                "origin/develop..develop and emit an APPROVED handoff with "
                "metrics.commit_sha == the pushed develop tip sha, then push again."
            ),
        ),
        skipped_binary_count,
    )
