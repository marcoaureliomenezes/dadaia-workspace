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

import shlex
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.gitflow import Gitflow
from dadaia_workspace.core.models.git_scan import GitObjectReadError, ScannedObject
from dadaia_workspace.features.chokepoints.branch_policy import (
    HEADS_PREFIX,
    ZERO_SHA,
    Decision,
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

    def publishes_nothing(self, repo: Path, sha: str) -> bool: ...


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


def _rewrite_fix(ref: PushRef, gitflow: Gitflow) -> str:
    """Squash the refused range onto what the remote already has — non-interactive."""
    base = (
        ref.remote_sha
        if ref.remote_sha != ZERO_SHA
        else f"refs/remotes/origin/{gitflow.integration}"
    )
    reset = shlex.join(["git", "reset", "--soft", base])
    return f"{reset} && " + shlex.join(
        ["git", "commit", "-m", "chore: republish without the refused content"]
    )


def _compose_denylist_refusal(
    hits: list[tuple[PushRef, Hit]], path_masker: PathMasker, gitflow: Gitflow
) -> str:
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
        "  The range scope means already-published history never needs a rewrite. If "
        "this push is a genuine emergency, git's sanctioned, traceable bypass is "
        "`git push --no-verify` (discouraged; leaves a reflog trace)."
    )
    lines.append(
        "Remove the term from the listed file(s), then squash the pushed range and push "
        f"again:\nfix: {_rewrite_fix(hits[0][0], gitflow)}"
    )
    return "\n".join(lines)


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

    Streamed straight into :func:`~dadaia_workspace.features.chokepoints.denylist_scan.
    scan_objects` by the caller rather than materialized into a list first
    (code-reviewer MEDIUM performance finding: building the full ``fresh`` list before
    scanning measured ~129 MB resident over a large fallback range) —
    ``scan_objects`` already consumes its ``objects`` argument lazily, one object at a
    time, so nothing downstream needs the list shape.
    """
    for obj in object_source.new_objects(repo, ref.local_sha, ref.remote_sha):
        if obj.sha in seen_shas:
            continue
        seen_shas.add(obj.sha)
        yield obj


@dataclass(frozen=True)
class _RangeScan:
    """The outcome of the ONE streaming pass over the pushed-range objects.

    ``read_failed`` is the typed discriminator the decision keys on (never the refusal
    prose): True means git could not be read and ``refusal`` names that failure; False
    with a ``refusal`` means denylist hits; False without one means clean.
    ``specs_paths_by_ref`` (operator ruling 2026-09-13, bug
    ``pre-push-canon-scan-not-range-scoped``) is every ``specs/`` path the range
    introduces or rewrites, per local sha — the canon scan's input, recorded from the
    SAME pass instead of a second whole-tree listing.
    """

    refusal: Decision | None
    read_failed: bool
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
    gitflow: Gitflow,
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

    code-reviewer MEDIUM finding (v0.11.0 pre-PR review): *terms* and *patterns* are
    each materialized EXACTLY ONCE, right here, before either the
    :class:`PathMasker` or the scan loop below touches them. A one-shot Iterable
    (e.g. a generator) consumed a second time yields nothing — building the masker from
    the raw parameter and separately re-``list()``-ing it later silently emptied the
    second consumption's term set, a latent fail-open. The materialized lists are the
    ONLY thing passed onward from here.
    """
    term_list = list(terms)
    pattern_list = list(patterns)
    path_masker = PathMasker(term_list, pattern_list)
    specs_paths_by_ref: dict[str, list[str]] = {}
    if not scan_refs:
        return _RangeScan(None, False, 0, (), path_masker, specs_paths_by_ref)
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
                    "Repair the object store first (git fsck), then push again.\n"
                    f"fix: git fetch origin && {shlex.join(['git', 'push', 'origin', gitflow.work_pattern])}"
                ),
            ),
            True,
            0,
            (),
            path_masker,
            specs_paths_by_ref,
        )
    oversized_notes = tuple(oversized_all)
    refusal = (
        Decision(
            allowed=False, message=_compose_denylist_refusal(per_ref_hits, path_masker, gitflow)
        )
        if per_ref_hits
        else None
    )
    return _RangeScan(
        refusal, False, skipped_total, oversized_notes, path_masker, specs_paths_by_ref
    )


def _compose_specs_canon_refusal(violations: list[tuple[PushRef, str]], gitflow: Gitflow) -> str:
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
    lines.append(
        "git rm the listed specs/ path(s), then squash the pushed range and push again:\n"
        f"fix: {_rewrite_fix(violations[0][0], gitflow)}"
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
    gitflow: Gitflow,
) -> Decision | None:
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
    if not violations:
        return None
    return Decision(allowed=False, message=_compose_specs_canon_refusal(violations, gitflow))


def push_gate_decision(
    refs: list[PushRef],
    *,
    object_source: ObjectSource,
    repo: Path,
    canon_violations_fn: Callable[[Sequence[str]], Sequence[str]],
    gitflow: Gitflow,
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

    *object_source*, *repo*, *canon_violations_fn* and *gitflow* are
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
                f"fix: {shlex.join(['git', 'push', 'origin', gitflow.work_pattern])}"
            ),
        )

    branch_policy_refs = [r for r in refs if not r.is_deletion and not r.is_tag]
    births = frozenset(
        r.local_sha
        for r in branch_policy_refs
        if r.remote_sha == ZERO_SHA
        and gitflow.role_of(r.remote_ref.removeprefix(HEADS_PREFIX)) in ("principal", "integration")
        and object_source.publishes_nothing(repo, r.local_sha)
    )
    branch_refusal = check_branch_policy(branch_policy_refs, gitflow, births)
    if branch_refusal is not None:
        return branch_refusal

    # Every non-deletion ref (tags included) — computed independently of
    # `branch_policy_refs`, which excludes tags. Runs after branch policy (free and
    # pure, already checked above); shared by both the specs-canon scan (step 2) and
    # the denylist scan (step 3, A3.4).
    scan_refs = [r for r in refs if not r.is_deletion]

    # One streaming pass over the pushed-range objects feeds BOTH step 2 (specs canon,
    # range-scoped, operator ruling 2026-09-13) and step 3 (denylist); step 2's refusal
    # still takes precedence over step 3's.
    scan = _run_denylist_scan(
        scan_refs, object_source, repo, denylist_terms, baseline_patterns, gitflow
    )
    if scan.read_failed and scan.refusal is not None:
        # Nothing was streamed, so the canon scan has no input either — fail closed
        # on the read error itself.
        return _annotate_skip(
            scan.refusal, scan.skipped_binary_count, scan.oversized_notes, scan.path_masker
        )

    canon_refusal = _run_specs_canon_scan(
        scan_refs,
        scan.specs_paths_by_ref,
        canon_violations_fn,
        gitflow,
    )
    if canon_refusal is not None:
        return _annotate_skip(
            canon_refusal, scan.skipped_binary_count, scan.oversized_notes, scan.path_masker
        )

    if scan.refusal is not None:
        return _annotate_skip(
            scan.refusal, scan.skipped_binary_count, scan.oversized_notes, scan.path_masker
        )

    return _annotate_skip(
        Decision(
            allowed=True,
            message="[pre-push] branch policy + specs-canon scan + denylist scan passed; allow.",
        ),
        scan.skipped_binary_count,
        scan.oversized_notes,
        scan.path_masker,
    )
