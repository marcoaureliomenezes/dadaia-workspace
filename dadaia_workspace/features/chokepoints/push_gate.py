"""Push-gate orchestration.

:func:`push_gate_decision` is the pre-push half of the chokepoint contract: branch
policy (:mod:`~dadaia_workspace.features.chokepoints.branch_policy`) first, then the
specs/ canon scan, then the range-scoped denylist scan
(:mod:`~dadaia_workspace.features.chokepoints.denylist_scan`) — first refusal wins.
Security review is the reviewer's lens before each PR, never a step here.

This module is business logic: it imports ``core`` only, NEVER ``infrastructure``, and
never spawns a subprocess. The canon predicate (``canon_violations_fn``) and the injected :class:`ObjectSource` are parameters, wired
by the CLI composition root (``cli/commands/ci.py``) — an unwired production call site
is a CLI defect, never a bypass.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.cli_line import git_line
from dadaia_workspace.core.gitflow import Gitflow
from dadaia_workspace.core.models.git_scan import ZERO_SHA, GitObjectReadError, ScannedObject
from dadaia_workspace.features.chokepoints.branch_policy import (
    HEADS_PREFIX,
    Decision,
    GateFixes,
    PushRef,
    check_branch_policy,
)
from dadaia_workspace.features.chokepoints.denylist_scan import (
    BaselinePatternLike,
    Hit,
    OversizedNote,
    PathMasker,
    scan_objects,
)

__all__ = ["push_gate_decision"]

#: The law this scan enforces (SPEC v0.9.0 FR5) — quoted verbatim in every refusal.
_DENYLIST_LAW = "dd-release-implementation §2a — private names never enter public/pushed material"

#: FR5/A5.4 — at most this many offending objects are listed before a remainder count.
_MAX_LISTED_HITS = 10

#: The fix hint every specs-canon refusal line carries (operator, 2026-08-28) — a
#: canon or verdict violation has exactly one remediation: remove the offending path.
_SPECS_CANON_FIX_HINT = "delete the path; canon: specs/AGENTS.md"


#: The one remediation of a range refusal (R13, N3): every range, a root-reaching one
#: included, is uncommitted to its oldest unpublished commit and amended.
_REWRITE = (
    "Uncommit the unpublished range down to its oldest commit (origin's history is never "
    "rewritten), remove what is listed, `git commit --amend` and push:"
)


class ObjectSource(Protocol):
    """Feature-local structural port over the push-range object reader (ADR-0001: no
    ``core/protocols`` port — the concrete adapter, ``GitSubprocessObjectReader``, is
    the only implementer; this module still never imports ``infrastructure`` or
    spawns a subprocess itself — the CLI composition root (``cli/commands/ci.py``)
    constructs the real adapter and injects it here, exactly as before).
    """

    def new_objects(
        self, repo: Path, local_sha: str, remote_sha: str
    ) -> Iterable[ScannedObject]: ...

    def unpublished(self, repo: Path, sha: str) -> list[str]: ...

    def remote_branch(self, repo: Path, branch: str) -> bool: ...


def _annotate_skip(
    decision: Decision,
    skipped_binary_count: int,
    oversized_notes: tuple[OversizedNote, ...] = (),
    path_masker: PathMasker | None = None,
) -> Decision:
    """Attach the FR6 row-3 skip count AND the v0.11.0 FR4 oversized-blob notes to
    *decision* — reported either way (allow/refuse), and kept honestly DISTINCT: the
    binary count means "not text-decodable at all"; an oversized note means "the first
    N bytes were scanned, the rest genuinely never was — verify it by hand" (grill P13).

    v0.11.0 A6.3: the oversized note's path is masked through *path_masker* — the SAME
    class-wide rule FR6 applies to the denylist refusal, since the note itself began
    naming a path in T-110-06 and is the second channel of the same CWE-532 class
    entry #23 already found once.
    """
    lines: list[str] = []
    if skipped_binary_count > 0:
        lines.append(
            f"[pre-push] {skipped_binary_count} binary blob(s) skipped by the denylist "
            "scan (not text-decodable)."
        )
    for note in oversized_notes:
        masked_path = path_masker.mask_path(note.path) if path_masker is not None else note.path
        lines.append(
            f"[pre-push] {masked_path} is {note.size_bytes} byte(s) — only its first "
            f"{note.scanned_bytes} byte(s) were scanned by the denylist scan; the "
            "remainder was NOT scanned. Verify the rest by hand."
        )
    if not lines:
        return decision
    note_text = "\n".join(lines)
    warn = f"{decision.warn}\n{note_text}" if decision.warn else note_text
    return Decision(allowed=decision.allowed, message=decision.message, warn=warn)


def _compose_denylist_refusal(hits: list[tuple[PushRef, Hit]], path_masker: PathMasker) -> str:
    """FR5: ref, path:line, short blob sha, masked term + source layer, the law, the
    edit + rewrite-before-push remediation, ``--no-verify``, capped at 10 hits.

    v0.11.0 FR6(b): the blob path itself is masked through *path_masker* before
    rendering (entry #23 resolution A) — only offending segments change; the line
    number and short sha stay exactly as today.
    """
    lines = [
        f"[pre-push] BLOCKED: the pushed range publishes {len(hits)} object(s) carrying "
        f"a denylisted term ({_DENYLIST_LAW})."
    ]
    shown = hits[:_MAX_LISTED_HITS]
    remainder = len(hits) - len(shown)
    for ref, hit in shown:
        masked_path = path_masker.mask_path(hit.path)
        lines.append(
            f"  {ref.local_ref} -> {ref.remote_ref}: {masked_path}:{hit.line} "
            f"(blob {hit.sha[:12]}) — masked term '{hit.masked_term}' ({hit.source_layer})"
        )
    if remainder > 0:
        lines.append(f"  ... and {remainder} more offending object(s).")
    lines.append(
        "  A test fixture that needs a secret shape composes it at runtime (string "
        "concatenation), never as a tracked literal. "
        "The range scope means already-published history never needs a rewrite. If "
        "this push is a genuine emergency, git's sanctioned, traceable bypass is "
        "`git push --no-verify` (discouraged; leaves a reflog trace)."
    )
    return "\n".join(lines)


def _rewrite_fix(ref: PushRef, object_source: ObjectSource, repo: Path, fixes: GateFixes) -> str:
    """The one fix for the first refused ref (R13: origin is never rewritten): a branch
    HEAD is not on is switched to first; HEAD's range is uncommitted down to its OLDEST
    unpublished commit, which the operator then amends — a root commit included."""
    if ref.is_tag or not fixes.head:
        return "Operator action: a tag or a detached HEAD has no branch to amend; push a branch."
    branch = ref.local_ref.removeprefix(HEADS_PREFIX)
    if branch != ref.local_ref and branch != fixes.head:
        return f"fix: {git_line(fixes.repo, 'switch', branch)}"
    oldest = object_source.unpublished(repo, ref.local_sha)[-1]
    return f"fix: {git_line(fixes.repo, 'reset', '--soft', oldest)}"


def _render_git_read_error(exc: GitObjectReadError, path_masker: PathMasker) -> str:
    """SPEC v0.4.2 FR4/A4.2: render a caught :class:`GitObjectReadError`'s detail with
    its structured ``path`` (if any) masked through *path_masker* — the single render
    boundary for this failure channel. Never ``repr(exc)``, and the path never reaches
    the message unmasked: ``str(exc)`` is the message text the raise site composed
    (already path-free — the path lives on ``exc.path``, not embedded in the string),
    and the masked path is appended structurally here, once.
    """
    detail = str(exc)
    if exc.path is not None:
        detail = f"{detail} (path: {path_masker.mask_path(exc.path)})"
    return detail


def _dedup_new_objects(
    object_source: ObjectSource,
    repo: Path,
    ref: PushRef,
    seen_shas: set[str],
) -> Iterator[ScannedObject]:
    """Yield each object new to *ref*'s range that has not already been seen earlier in
    this scan, recording it into *seen_shas* as it is yielded (A1.4 cross-ref dedupe).
    Streamed, never listed: a materialized range measured ~129 MB resident."""
    for obj in object_source.new_objects(repo, ref.local_sha, ref.remote_sha):
        if obj.sha in seen_shas:
            continue
        seen_shas.add(obj.sha)
        yield obj


@dataclass(frozen=True)
class _RangeScan:
    """The outcome of the ONE streaming pass over the pushed-range objects.

    ``read_failure`` is set only when git could not be read; ``hits`` are the denylist
    hits, each with the ref that introduced it.
    ``specs_paths_by_ref`` (operator ruling 2026-09-13, bug
    ``pre-push-canon-scan-not-range-scoped``) is every ``specs/`` path the range
    introduces or rewrites, per local sha — the canon scan's input, recorded from the
    SAME pass instead of a second whole-tree listing.
    """

    read_failure: Decision | None
    hits: list[tuple[PushRef, Hit]]
    skipped_binary_count: int
    oversized_notes: tuple[OversizedNote, ...]
    path_masker: PathMasker
    specs_paths_by_ref: dict[str, list[str]]


def _run_denylist_scan(
    scan_refs: list[PushRef],
    object_source: ObjectSource,
    repo: Path,
    terms: Iterable[tuple[str, str]],
    patterns: Iterable[BaselinePatternLike],
) -> _RangeScan:
    """Run the FR1/FR2 scan over *scan_refs* — every non-deletion ref, tags included.

    A git object-read failure refuses immediately, naming the failure (FR6 row 2) —
    never a silent empty scan. ``oversized_notes`` is deduplicated for free — it is
    built from ``scan_objects`` runs over :func:`_dedup_new_objects`, which shares
    ``seen_shas`` across every ref in this scan, so a blob reachable from two refs
    contributes at most one note (mirrors the existing hit/skip dedup). The returned
    ``path_masker`` (v0.11.0 FR6(b)) is built from the SAME term sources and is
    reused by the caller for every subsequently rendered oversized note, so a repeated
    offending path segment gets one stable ordinal across the whole invocation.
    *terms* and *patterns* are materialized once, here: a one-shot Iterable consumed
    twice silently empties the term set (a fail-open).
    """
    term_list = list(terms)
    pattern_list = list(patterns)
    path_masker = PathMasker(term_list, pattern_list)
    specs_paths_by_ref: dict[str, list[str]] = {}
    if not scan_refs:
        return _RangeScan(None, [], 0, (), path_masker, specs_paths_by_ref)
    seen_shas: set[str] = set()
    per_ref_hits: list[tuple[PushRef, Hit]] = []
    skipped_total = 0
    oversized_all: list[OversizedNote] = []
    try:
        for ref in scan_refs:
            fresh = _record_specs_paths(
                _dedup_new_objects(object_source, repo, ref, seen_shas),
                specs_paths_by_ref.setdefault(ref.local_sha, []),
            )
            outcome = scan_objects(fresh, term_list, pattern_list)
            skipped_total += outcome.skipped_binary_count
            oversized_all.extend(outcome.oversized_notes)
            per_ref_hits.extend((ref, hit) for hit in outcome.hits)
    except GitObjectReadError as exc:
        return _RangeScan(
            Decision(
                allowed=False,
                message=(
                    f"[pre-push] BLOCKED: reading the pushed-range git objects failed "
                    f"({_render_git_read_error(exc, path_masker)}) — a policy gate never "
                    "skips what it cannot evaluate (fail closed). The sanctioned, "
                    "traceable emergency bypass is `git push --no-verify` "
                    "(discouraged; leaves a reflog trace).\n"
                    "Repair the object store, then push again.\nfix: git fsck"
                ),
            ),
            [],
            0,
            (),
            path_masker,
            specs_paths_by_ref,
        )
    return _RangeScan(
        None, per_ref_hits, skipped_total, tuple(oversized_all), path_masker, specs_paths_by_ref
    )


def _compose_specs_canon_refusal(violations: list[tuple[PushRef, str]]) -> str:
    """FR2 (v0.5.0 specs-canon closure): ref, the offending ``specs/``-relative path,
    the law, one fix hint per offending path, ``--no-verify``, capped at 10 hits —
    the SAME shape :func:`_compose_denylist_refusal` uses."""
    lines = [
        f"[pre-push] BLOCKED: the pushed range publishes {len(violations)} specs/ "
        "path(s) violating the v6 canon or the verdict rule (specs/AGENTS.md)."
    ]
    shown = violations[:_MAX_LISTED_HITS]
    remainder = len(violations) - len(shown)
    for ref, path in shown:
        lines.append(
            f"  {ref.local_ref} -> {ref.remote_ref}: specs/{path} — {_SPECS_CANON_FIX_HINT}"
        )
    if remainder > 0:
        lines.append(f"  ... and {remainder} more offending path(s).")
    lines.append(
        "  If this push is a genuine emergency, git's sanctioned, traceable bypass is "
        "`git push --no-verify` (discouraged; leaves a reflog trace)."
    )
    return "\n".join(lines)


def _record_specs_paths(
    objects: Iterator[ScannedObject], sink: list[str]
) -> Iterator[ScannedObject]:
    """Stream *objects* through unchanged, recording each ``specs/`` path into *sink*.

    Bug ``pre-push-canon-scan-not-range-scoped`` (operator ruling 2026-09-13): the
    canon scan reads the SAME pushed-range objects the denylist scan streams — one
    pass over ``new_objects``, never the whole tree at the tip. A path no commit in
    the range touches is already published, so it never blocks a push (the principle
    the denylist refusal text has always stated: the range scope means published
    history never needs a rewrite).
    """
    for obj in objects:
        if obj.path.startswith("specs/"):
            sink.append(obj.path)
        yield obj


def _run_specs_canon_scan(
    scan_refs: list[PushRef],
    specs_paths_by_ref: dict[str, list[str]],
    canon_violations_fn: Callable[[Sequence[str]], Sequence[str]],
) -> list[tuple[PushRef, str]]:
    """SPEC v0.5.0 specs-canon closure (operator ruling 2026-08-28), range-scoped since
    2026-09-13: every ``specs/`` path the pushed range introduces or rewrites
    (*specs_paths_by_ref*, recorded by :func:`_record_specs_paths`) is checked against
    the v6 canon via the INJECTED predicate (v0.5.1 K7: the SAME predicate the doctor's
    TREE-8 check uses, never a second, hand-kept member list — injected rather than
    imported at module scope so this module carries no ``chokepoints -> specs.canon``
    edge).
    """
    violations: list[tuple[PushRef, str]] = []
    for ref in scan_refs:
        range_rel = sorted({p[len("specs/") :] for p in specs_paths_by_ref.get(ref.local_sha, [])})
        bad = set(canon_violations_fn(range_rel))
        violations.extend((ref, path) for path in sorted(bad))
    return violations


def push_gate_decision(
    refs: list[PushRef],
    *,
    object_source: ObjectSource,
    repo: Path,
    canon_violations_fn: Callable[[Sequence[str]], Sequence[str]],
    gitflow: Gitflow,
    fixes: GateFixes,
    malformed_lines: int = 0,
    denylist_terms: Iterable[tuple[str, str]] = (),
    baseline_patterns: Iterable[BaselinePatternLike] = (),
) -> Decision:
    """Decide whether a push may proceed.

    Policy order, first refusal wins:

    1. **Branch policy** (:func:`~dadaia_workspace.features.chokepoints.branch_policy.
       check_branch_policy`, reading *gitflow*) — every non-deletion, non-tag ref must
       be a work branch pushed to the SAME remote name; the principal and integration
       branches advance by PR only.
    2. **specs/ canon scan** (v0.5.0 specs-canon closure, operator ruling 2026-08-28)
       — every ``specs/`` path the pushed range introduces or rewrites is checked
       against the canon (range-scoped: a path no commit in the range touches never
       blocks), through the injected *canon_violations_fn*.
    3. **Range-scoped denylist scan** (v0.9.0 FR1/FR2) — every non-deletion ref, tags
       included, is scanned via *object_source* for new objects carrying a denylisted
       term. Steps 2 and 3 share ONE object walk (the walk runs once, after branch
       policy; step 2's refusal is decided first) — a work-branch push is the
       first publication to ``origin``.

    There is no fourth step: security review is the reviewer's lens before each PR,
    never a pre-push step.

    Deletions (zero sha) are never scanned. Tag pushes ARE scanned but were never
    branch-policy-gated (publishing depends on tag pushes). A malformed stdin line
    fails CLOSED (finding 1) and the REMOTE side of every branch-policy ref must
    match its LOCAL branch name (finding 2: a work branch aimed at the integration branch).

    The refusals are exactly: a malformed stdin line; a branch-policy refusal (a ref
    outside the gitflow, a mismatched refspec, a direct principal/integration push, a
    principal/integration birth publishing new objects on an origin that already holds
    a gitflow branch); a specs/ canon violation; a denylisted term; an unreadable object
    store. Each carries one fix; *fixes* names the repo and the live work branch.

    *object_source*, *repo*, *canon_violations_fn*, *gitflow* and *fixes* are
    REQUIRED — FR7/A7.2 (extended at v0.5.1 K7 to the canon predicates): the decision
    function always takes every external capability it needs as a parameter; an
    unwired production call site is a CLI defect, never a bypass (FR6 row 4), so there
    is no default that would silently skip a step.
    """
    if malformed_lines > 0:
        return Decision(
            allowed=False,
            message=(
                f"[pre-push] BLOCKED: {malformed_lines} unparseable pre-push stdin "
                "line(s) — a policy gate never skips what it cannot parse (fail "
                "closed). The sanctioned, traceable emergency bypass is "
                "`git push --no-verify` (discouraged; leaves a reflog trace).\n"
                "Push one explicit refspec.\n"
                f"fix: {git_line(fixes.repo, 'push', 'origin', gitflow.work_pattern)}"
            ),
        )

    branch_policy_refs = [r for r in refs if not r.is_deletion and not r.is_tag]
    roles = (gitflow.principal, gitflow.integration)
    unborn = [
        r
        for r in branch_policy_refs
        if r.remote_sha == ZERO_SHA and r.remote_ref.removeprefix(HEADS_PREFIX) in roles
    ]
    bootstrap = bool(unborn) and not any(object_source.remote_branch(repo, b) for b in roles)
    births = frozenset(
        r.local_sha for r in unborn if bootstrap or not object_source.unpublished(repo, r.local_sha)
    )
    branch_refusal = check_branch_policy(branch_policy_refs, gitflow, fixes, births)
    if branch_refusal is not None:
        return branch_refusal

    # Every non-deletion ref (tags included) — computed independently of
    # `branch_policy_refs`, which excludes tags. Runs after branch policy (free and
    # pure, already checked above); shared by both the specs-canon scan (step 2) and
    # the denylist scan (step 3, A3.4).
    scan_refs = [r for r in refs if not r.is_deletion]

    # One streaming pass over the pushed-range objects feeds BOTH step 2 (specs canon,
    # range-scoped, operator ruling 2026-09-13) and step 3 (denylist); step 2's refusal
    # takes precedence, and the one rewrite fix names the first refused ref (git lists
    # the refs in refspec order; each re-run's fix names the next).
    scan = _run_denylist_scan(scan_refs, object_source, repo, denylist_terms, baseline_patterns)
    decision = scan.read_failure
    if decision is None:
        violations = _run_specs_canon_scan(scan_refs, scan.specs_paths_by_ref, canon_violations_fn)
        refused = [ref for ref, _ in violations or scan.hits]
        if refused:
            message = (
                _compose_specs_canon_refusal(violations)
                if violations
                else _compose_denylist_refusal(scan.hits, scan.path_masker)
            )
            fix = _rewrite_fix(refused[0], object_source, repo, fixes)
            decision = Decision(allowed=False, message=f"{message}\n{_REWRITE}\n{fix}")
        else:
            decision = Decision(
                allowed=True,
                message="[pre-push] branch policy + specs-canon scan + denylist scan passed; allow.",
            )
    return _annotate_skip(
        decision, scan.skipped_binary_count, scan.oversized_notes, scan.path_masker
    )
